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
# Codex CLI backend for the unified agent dispatcher.
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
import time

try:
    from .per_call_writer_helpers import (
        next_call_id, build_call_payload, write_call,
    )
except Exception as _exc:
    next_call_id = None
    build_call_payload = None
    write_call = None

AGENT_CMD = "codex"


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


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_int(data, keys):
    for key in keys:
        if isinstance(data, dict) and key in data:
            value = _as_int(data.get(key))
            if value is not None:
                return value
    return None


def _update_tokens_from_dict(tokens, data):
    # Codex JSONL event schemas can evolve. Accept the common snake_case,
    # camelCase, and OpenAI API-style usage names.
    input_tokens = _first_int(data, [
        "input_tokens", "inputTokens", "prompt_tokens", "promptTokens",
        "total_input_tokens", "totalInputTokens",
    ])
    output_tokens = _first_int(data, [
        "output_tokens", "outputTokens", "completion_tokens",
        "completionTokens", "total_output_tokens", "totalOutputTokens",
    ])
    cache_read_tokens = _first_int(data, [
        "cache_read_tokens", "cacheReadTokens", "cache_read_input_tokens",
        "cacheReadInputTokens", "cached_input_tokens", "cachedInputTokens",
    ])
    cache_write_tokens = _first_int(data, [
        "cache_write_tokens", "cacheWriteTokens",
        "cache_creation_input_tokens", "cacheCreationInputTokens",
    ])

    if input_tokens is not None:
        tokens["input_tokens"] = max(tokens["input_tokens"], input_tokens)
    if output_tokens is not None:
        tokens["output_tokens"] = max(tokens["output_tokens"], output_tokens)
    if cache_read_tokens is not None:
        tokens["cache_read_tokens"] = max(
            tokens["cache_read_tokens"], cache_read_tokens)
    if cache_write_tokens is not None:
        tokens["cache_write_tokens"] = max(
            tokens["cache_write_tokens"], cache_write_tokens)


def _walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            for nested in _walk_json(child):
                yield nested
    elif isinstance(value, list):
        for child in value:
            for nested in _walk_json(child):
                yield nested


def parse_codex_jsonl(stdout_text):
    events = []
    tokens = _zero_tokens()

    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            event = {"raw": line}
        events.append(event)
        for obj in _walk_json(event):
            _update_tokens_from_dict(tokens, obj)

    return tokens, {"events": events}


def _invoke_cli(prompt_text, model_name, workspace=None, effort=None):
    # Invoke Codex non-interactively. Prompt text is always provided on stdin so
    # large benchmark prompts do not hit argv length limits.

    base_cmd = [
        AGENT_CMD,
        "exec",
        "--model", model_name,
        "--json",
        "--ephemeral",
        "--skip-git-repo-check",
        # Docker already provides the benchmark isolation boundary. Codex's
        # workspace-write sandbox may require user namespaces that are often
        # disabled inside containers.
        "--sandbox", os.environ.get("CODEX_SANDBOX", "danger-full-access"),
        "-c", 'approval_policy="{}"'.format(
            os.environ.get("CODEX_APPROVAL_POLICY", "never")),
        "-c", 'web_search="disabled"',
        "-c", 'sandbox_workspace_write.network_access=false',
        "--color", "never",
    ]

    if workspace:
        base_cmd.extend(["--cd", workspace])
    if effort:
        base_cmd.extend(["-c", 'model_reasoning_effort="{}"'.format(effort)])

    cmd = base_cmd + ["-"]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate(prompt_text.encode("utf-8"))

    stdout_text = stdout.decode("utf-8", errors="replace")
    stderr_text = stderr.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        raise RuntimeError(
            "Agent CLI exited with code {}.\nstderr: {}\nstdout: {}".format(
                proc.returncode, stderr_text.strip(), stdout_text.strip())
        )

    tokens, raw_data = parse_codex_jsonl(stdout_text)
    return tokens, raw_data


def call_agent(prompt_text, output_path, model, workspace=None, effort=None):
    # Unified backend entry point. Invokes the Codex CLI and reports status /
    # runtime / tokens / raw_data via a single dict so the dispatcher can emit
    # stderr markers without backend-specific knowledge.
    #
    # ``output_path`` is accepted for API uniformity; Codex writes its output
    # file directly per the prompt and the dispatcher handles fallbacks.

    if shutil.which(AGENT_CMD) is None:
        return {
            "status": "fail",
            "runtime_seconds": 0.0,
            "tokens": _zero_tokens(),
            "raw_data": None,
            "error": (
                "'{}' command not found. Install the Codex CLI and ensure "
                "it is on PATH.".format(AGENT_CMD)
            ),
        }

    started_at = _iso_utc()
    t_start = time.monotonic()
    try:
        tokens, raw_data = _invoke_cli(
            prompt_text, model,
            workspace=workspace, effort=effort,
        )
        elapsed = time.monotonic() - t_start
        finished_at = _iso_utc()
        # codex CLI does not expose per-model usage; emit a single-entry
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
