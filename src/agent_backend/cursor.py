#!/usr/bin/env python3
#BSD 3-Clause License
#
#Copyright (c) 2026, ASU-VDA-Lab
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#
#1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#3. Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#################################################################################
# Cursor Agent CLI backend for the unified agent dispatcher.
#
# This module is loaded by ``agent/agent.py`` via ``importlib.import_module``;
# it is not a standalone script. The single public entry point is
# ``call_agent(prompt_text, output_path, model, workspace=None, effort=None,
# call_id=None, temp_dir=None)`` which returns a dict with ``status``,
# ``runtime_seconds``, ``tokens``, ``raw_data``, and ``error`` keys for the
# dispatcher to forward. ``call_id`` / ``temp_dir`` are optional per-leaf
# dispatch hooks; omitting them keeps the reference single-shot behaviour.

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    from .per_call_writer_helpers import (
        next_call_id, build_call_payload, write_call,
    )
except Exception as _exc:
    next_call_id = None
    build_call_payload = None
    write_call = None

AGENT_CMD = "agent"
LONG_PROMPT_THRESHOLD = 100000


def _zero_tokens():
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
    }


def _iso_utc():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _record_call(case_name, model_name, session_id, by_model_usage,
                 started_at=None, finished_at=None, external_call_id=None):
    """Write one ${AGENT_CALLS_DIR}/<ID>.json via the shared helper.

    Opt-in: skipped silently when RECORD_TOKENS != "1". All failures are
    WARN+skip; never raises.

    When ``external_call_id`` is supplied (per-leaf dispatch), it is used
    verbatim as the call_id / filename and MUST be unique per case; on the
    (by-construction near-impossible) O_EXCL collision we WARN+skip rather
    than bump a shared counter, so parallel dispatch never races the
    module-level _CALL_SEQ. When ``external_call_id`` is None (the
    reference single-shot path) the id is derived from
    ``next_call_id(case, session_id)`` and a single O_EXCL collision is
    retried with a fresh next_call_id -- byte-identical to prior behaviour.
    """
    if os.environ.get("RECORD_TOKENS", "0") != "1":
        return None

    if next_call_id is None or build_call_payload is None or write_call is None:
        sys.stderr.write(
            "WARN: per_call_writer_helpers import failed; skipping "
            "per-call recording\n")
        return None

    calls_dir = os.environ.get("AGENT_CALLS_DIR", "").strip()
    if not calls_dir:
        sys.stderr.write(
            "WARN: AGENT_CALLS_DIR unset; skipping per-call recording\n")
        return None

    try:
        os.makedirs(calls_dir, exist_ok=True)
    except OSError as exc:
        sys.stderr.write(
            "WARN: cannot mkdir AGENT_CALLS_DIR={!r}: {!r}\n".format(
                calls_dir, exc))
        return None

    case = case_name or "unknown"
    use_external = bool(external_call_id)
    try:
        if use_external:
            cid = str(external_call_id)
        else:
            cid = next_call_id(case, session_id)
        payload = build_call_payload(
            case_name=case,
            call_id=cid,
            model_name=model_name,
            by_model_usage=by_model_usage,
            started_at=started_at,
            finished_at=finished_at,
        )
    except (TypeError, ValueError) as exc:
        sys.stderr.write(
            "WARN: per-call payload build failed: {!r}\n".format(exc))
        return None

    try:
        return write_call(calls_dir, cid, payload)
    except FileExistsError:
        if use_external:
            # External id is unique by construction; a collision means the
            # call was already recorded. Do NOT bump the shared counter.
            sys.stderr.write(
                "WARN: per-call file {!r} already exists; skipping\n".format(
                    cid))
            return None
        try:
            cid = next_call_id(case, session_id)
            payload["call_id"] = cid
            return write_call(calls_dir, cid, payload)
        except FileExistsError:
            sys.stderr.write(
                "WARN: O_EXCL collision on retry; skipping per-call\n")
            return None
        except OSError as exc:
            sys.stderr.write(
                "WARN: per-call write retry failed: {!r}\n".format(exc))
            return None
    except OSError as exc:
        sys.stderr.write(
            "WARN: per-call write failed: {!r}\n".format(exc))
        return None


def _invoke_cli(prompt_text, model_name, workspace=None, call_id=None):
    # Invoke the Cursor Agent CLI with --output-format json and no timeout.
    #
    # The heavy "result" key is popped from raw_data ONLY when ``call_id`` is
    # None (reference single-shot path); when ``call_id`` is supplied (per-leaf
    # dispatch) "result" is RETAINED so clear_next/patch_parser can extract the
    # fenced ```json patch envelope from it.

    base_cmd = [
        AGENT_CMD,
        "--model", model_name,
        "--output-format", "json",
        "--trust",              # trust workspace without prompting
        "-p",                   # print mode (non-interactive)
    ]
    if workspace:
        base_cmd.extend(["--workspace", workspace])

    tmp_path = None
    try:
        if len(prompt_text) > LONG_PROMPT_THRESHOLD:
            fd, tmp_path = tempfile.mkstemp(suffix=".txt", prefix="agent_prompt_")
            with os.fdopen(fd, "w") as tmp:
                tmp.write(prompt_text)
            with open(tmp_path) as stdin_fh:
                proc = subprocess.Popen(
                    base_cmd,
                    stdin=stdin_fh,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = proc.communicate()
        else:
            cmd = base_cmd + [prompt_text]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = proc.communicate()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        raise RuntimeError(
            "Agent CLI exited with code {}.\nstderr: {}\nstdout: {}".format(
                proc.returncode, stderr_text.strip(), stdout_text.strip())
        )

    data = json.loads(stdout_text)
    usage = data["usage"]

    tokens = {
        "input_tokens":       int(usage["inputTokens"]),
        "output_tokens":      int(usage["outputTokens"]),
        "cache_read_tokens":  int(usage.get("cacheReadTokens", 0)),
        "cache_write_tokens": int(usage.get("cacheWriteTokens", 0)),
    }

    raw_data = dict(data)
    # Keep "result" for per-leaf dispatch (call_id supplied) so patch_parser
    # can read the fenced patch; pop it for the reference single-shot path
    # (call_id None) to stay byte-identical with prior --raw-json-out output.
    if call_id is None:
        raw_data.pop("result", None)

    return tokens, raw_data


def call_agent(prompt_text, output_path, model, workspace=None, effort=None,
               call_id=None, temp_dir=None):
    # Unified backend entry point. Invokes the Cursor Agent CLI and reports
    # status / runtime / tokens / raw_data via a single dict so the dispatcher
    # can emit stderr markers without backend-specific knowledge.
    #
    # ``effort`` is accepted for API uniformity; the Cursor Agent CLI does not
    # expose a reasoning-effort flag and the value is ignored. ``output_path``
    # is similarly accepted for uniformity (the CLI writes the file itself).
    #
    # ``call_id`` (per-leaf dispatch): when supplied, it is used verbatim as
    # the deterministic per-call filename for the single canonical write at
    # ${AGENT_CALLS_DIR}/<call_id>.json. When None, the id is derived from
    # next_call_id(...) -- byte-identical to the reference single-shot path.
    # ``temp_dir`` is accepted for API/back-compat but is advisory only;
    # this backend performs exactly ONE canonical per-call write.

    del effort  # unused
    del temp_dir  # advisory only; single canonical write is AGENT_CALLS_DIR

    if shutil.which(AGENT_CMD) is None:
        return {
            "status": "fail",
            "runtime_seconds": 0.0,
            "tokens": _zero_tokens(),
            "raw_data": None,
            "error": (
                "'{}' command not found. Install the Cursor Agent CLI and "
                "ensure it is on PATH.".format(AGENT_CMD)
            ),
        }

    started_at = _iso_utc()
    t_start = time.monotonic()
    try:
        tokens, raw_data = _invoke_cli(
            prompt_text, model,
            workspace=workspace,
            call_id=call_id,
        )
        elapsed = time.monotonic() - t_start
        finished_at = _iso_utc()
        # cursor CLI does not expose per-model usage; emit a single-entry
        # by_model keyed by the --model arg.
        by_model = {str(model): tokens}
        case_name = os.environ.get("AGENT_CASE_NAME", "").strip() or None
        _record_call(
            case_name=case_name,
            model_name=model,
            session_id=None,
            by_model_usage=by_model,
            started_at=started_at,
            finished_at=finished_at,
            external_call_id=call_id,
        )
        return {
            "status": "success",
            "runtime_seconds": elapsed,
            "tokens": tokens,
            "raw_data": raw_data,
            "error": None,
        }
    except Exception as exc:
        elapsed = time.monotonic() - t_start
        return {
            "status": "fail",
            "runtime_seconds": elapsed,
            "tokens": _zero_tokens(),
            "raw_data": None,
            "error": str(exc),
        }
