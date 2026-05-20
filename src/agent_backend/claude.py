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
# Claude Code CLI backend for the unified agent dispatcher.
#
# This module is loaded by ``agent/agent.py`` via ``importlib.import_module``;
# it is no longer a standalone script. The single public entry point is
# ``call_agent(prompt_text, output_path, model, workspace=None, effort=None)``
# which returns a dict with ``status``, ``runtime_seconds``, ``tokens``,
# ``raw_data``, and ``error`` keys for the dispatcher to forward.

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    from per_call_writer_helpers import (
        next_call_id, build_call_payload, write_call,
    )
except Exception as _exc:
    next_call_id = None
    build_call_payload = None
    write_call = None

AGENT_CMD = "claude"
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


def _claude_top_level_usage(usage):
    """Map claude top-level snake_case usage dict -> our four keys."""
    if not isinstance(usage, dict):
        return _zero_tokens()
    return {
        "input_tokens":       int(usage.get("input_tokens", 0) or 0),
        "output_tokens":      int(usage.get("output_tokens", 0) or 0),
        "cache_read_tokens":  int(usage.get("cache_read_input_tokens", 0) or 0),
        "cache_write_tokens": int(usage.get("cache_creation_input_tokens", 0) or 0),
    }


def _claude_model_usage(per_model):
    """Map claude modelUsage camelCase dict -> {model: snake-case usage}.

    cache_write_tokens <- cacheCreationInputTokens (NOT cacheWriteTokens;
    Anthropic billing event is "creation"; we use the semantic name "write").
    """
    out = {}
    if not isinstance(per_model, dict):
        return out
    for model, mu in per_model.items():
        if not isinstance(mu, dict):
            continue
        out[str(model)] = {
            "input_tokens":       int(mu.get("inputTokens", 0) or 0),
            "output_tokens":      int(mu.get("outputTokens", 0) or 0),
            "cache_read_tokens":  int(mu.get("cacheReadInputTokens", 0) or 0),
            "cache_write_tokens": int(mu.get("cacheCreationInputTokens", 0) or 0),
        }
    return out


def _record_call(case_name, model_name, session_id, by_model_usage,
                 started_at=None, finished_at=None):
    """Write one ${AGENT_CALLS_DIR}/<ID>.json via the shared helper.

    All failures are WARN+skip; never raises. Retries once on O_EXCL
    collision with a bumped _CALL_SEQ.
    """
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
    try:
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


def _invoke_cli(prompt_text, model_name, workspace=None, effort=None):
    # Invoke the Claude Code CLI with --output-format json and no timeout.
    #
    # Returns a tuple (tokens, raw_data):
    #   tokens:   dict with normalized snake_case token keys.
    #   raw_data: the full parsed CLI JSON with the "result" key popped.

    base_cmd = [
        AGENT_CMD,
        "--model", model_name,
        "--output-format", "json",
        "--allowedTools", "Bash(*)", "Read", "Write", "Edit",
            "Glob", "Grep", "Agent", "NotebookEdit",
        "-p",                           # print mode (non-interactive)
    ]
    if effort:
        base_cmd.extend(["--effort", effort])

    # Claude Code does not have a --workspace flag; use cwd instead.
    cwd = workspace if workspace else None

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
                    cwd=cwd,
                )
                stdout, stderr = proc.communicate()
        else:
            cmd = base_cmd + [prompt_text]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
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

    # Parse stdout JSON and extract token usage.
    data = json.loads(stdout_text)
    usage = data.get("usage", {})

    tokens = _claude_top_level_usage(usage)

    # Per-model breakdown (claude exposes modelUsage in camelCase).
    by_model = _claude_model_usage(data.get("modelUsage", {}))
    # If modelUsage is absent, synthesize a single-entry breakdown
    # keyed by the primary model name so the per-call payload still
    # has a non-empty by_model.
    if not by_model:
        by_model = {"": tokens}

    # Backend's CLI-exposed session id (forwarded to next_call_id).
    session_id = data.get("session_id") if isinstance(data, dict) else None

    raw_data = dict(data)
    raw_data.pop("result", None)

    return tokens, raw_data, by_model, session_id


def call_agent(prompt_text, output_path, model, workspace=None, effort=None):
    # Unified backend entry point. Invokes the Claude Code CLI and reports
    # status / runtime / tokens / raw_data via a single dict so the
    # dispatcher can emit stderr markers without backend-specific knowledge.
    #
    # ``output_path`` is accepted for API uniformity. Claude Code is told to
    # write the file directly via the prompt; this module does not touch the
    # path itself (the dispatcher pre-populates fallbacks before calling).

    if shutil.which(AGENT_CMD) is None:
        return {
            "status": "fail",
            "runtime_seconds": 0.0,
            "tokens": _zero_tokens(),
            "raw_data": None,
            "error": (
                "'{}' command not found. Install the Claude Code CLI and "
                "ensure it is on PATH.".format(AGENT_CMD)
            ),
        }

    started_at = _iso_utc()
    t_start = time.monotonic()
    try:
        tokens, raw_data, by_model, session_id = _invoke_cli(
            prompt_text, model,
            workspace=workspace, effort=effort,
        )
        elapsed = time.monotonic() - t_start
        finished_at = _iso_utc()
        # Substitute the actual model name for any empty by_model key
        # (single-entry synthesized fallback).
        if "" in by_model:
            by_model = {str(model): by_model.pop("")}
        case_name = os.environ.get("AGENT_CASE_NAME", "").strip() or None
        _record_call(
            case_name=case_name,
            model_name=model,
            session_id=session_id,
            by_model_usage=by_model,
            started_at=started_at,
            finished_at=finished_at,
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
