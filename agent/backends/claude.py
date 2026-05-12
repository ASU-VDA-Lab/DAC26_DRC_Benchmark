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

import json
import os
import shutil
import subprocess
import tempfile
import time

AGENT_CMD = "claude"
LONG_PROMPT_THRESHOLD = 100000


def _zero_tokens():
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
    }


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
    usage = data["usage"]

    tokens = {
        "input_tokens":       int(usage["input_tokens"]),
        "output_tokens":      int(usage["output_tokens"]),
        "cache_read_tokens":  int(usage.get("cache_read_input_tokens", 0)),
        "cache_write_tokens": int(usage.get("cache_creation_input_tokens", 0)),
    }

    raw_data = dict(data)
    raw_data.pop("result", None)

    return tokens, raw_data


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

    t_start = time.monotonic()
    try:
        tokens, raw_data = _invoke_cli(
            prompt_text, model,
            workspace=workspace, effort=effort,
        )
        elapsed = time.monotonic() - t_start
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
