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
# Unified LLM agent dispatcher.
#
# Selects a backend (claude / codex / cursor) and forwards the formatted
# prompt + arguments to its ``call_agent()`` entry point. The pipeline shell
# scripts always invoke this dispatcher; backend modules are NOT entry points
# of their own. The dispatcher emits ``STATUS=`` / ``TOKENS_JSON=`` /
# ``RUNTIME_SECONDS=`` markers on stderr for the shell wrapper to parse, and
# always exits 0 (the host wrapper keys off STATUS, not exit code).
#
# Usage:
#     python3 agent/agent.py --backend claude \
#         <formatted_prompt.md> <output_file> --model NAME \
#         [--workspace DIR] [--effort high|medium|low] \
#         [--task_type repair|detection] [--temp_dir DIR] \
#         [--fallback PATH] [--raw-json-out PATH]
#
# ``--backend`` is required in the hardened evaluation path. As a manual-debug
# convenience the env var ``AGENT_BACKEND`` is honored when ``--backend`` is
# omitted; production pipelines must always set the flag explicitly.

import argparse
import importlib
import json
import os
import shutil
import sys

# bootstrap sys.path so ``agent.backends.*`` resolves
# whether the dispatcher is launched from /workspace, /workspace/agent, or
# elsewhere. We insert the parent directory of this file (typically
# ``/workspace``) at index 0 so the explicit ``agent/__init__.py`` package
# wins over any shadow ``agent`` packages on PYTHONPATH.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)


_VALID_BACKENDS = ("claude", "codex", "cursor")


def _zero_tokens():
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
    }


def _resolve_backend(cli_value):
    # Prefer the explicit --backend flag. Fall back to the
    # AGENT_BACKEND env var only when the flag is absent (manual debug).
    # Anything else is an error.
    if cli_value:
        return cli_value
    env_value = os.environ.get("AGENT_BACKEND", "").strip().lower()
    if env_value:
        return env_value
    return None


def _emit_markers(stderr, status, tokens, runtime_seconds):
    stderr.write("STATUS={}\n".format(status))
    stderr.write("TOKENS_JSON={}\n".format(json.dumps(tokens)))
    stderr.write("RUNTIME_SECONDS={:.3f}\n".format(runtime_seconds))


def _dump_raw(raw_json_out, status, raw_data, error):
    if not raw_json_out:
        return
    if status == "success" and raw_data is not None:
        payload = raw_data
    else:
        payload = {"status": "fail", "error": error or "unknown"}
    try:
        os.makedirs(os.path.dirname(os.path.abspath(raw_json_out)),
                    exist_ok=True)
        with open(raw_json_out, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        sys.stderr.write("WARNING: failed to dump raw JSON to {}: {}\n".format(
            raw_json_out, exc))


def main():
    parser = argparse.ArgumentParser(
        description="Unified LLM agent dispatcher (claude / codex / cursor)")
    parser.add_argument("prompt_file",
                        help="Path to formatted prompt file (already rendered "
                             "by agent/prompt_format.py)")
    parser.add_argument("output_file",
                        help="Expected output file path. The agent writes here "
                             "directly; used for fallback population and "
                             "post-run verification.")
    parser.add_argument("--backend", choices=_VALID_BACKENDS, default=None,
                        help="Backend to dispatch to. Required in hardened "
                             "path; AGENT_BACKEND env honored only when this "
                             "flag is omitted (manual debug only).")
    parser.add_argument("--model", required=True,
                        help="Model name forwarded to the backend CLI.")
    parser.add_argument("--task_type", default="repair",
                        choices=["repair", "detection"],
                        help="Task type. Drives fallback content and "
                             "expectations of the output file.")
    parser.add_argument("--fallback", default=None,
                        help="For repair: original layout script copied to "
                             "output_file before the agent runs.")
    parser.add_argument("--workspace", default=None,
                        help="Workspace directory passed through to the "
                             "backend (cwd for Claude, --cd for Codex, "
                             "--workspace for Cursor).")
    parser.add_argument("--effort", default=None,
                        help="Reasoning-effort level (high/medium/low). "
                             "Single source of truth -- agent.py does NOT "
                             "consult CLAUDE_EFFORT / CODEX_EFFORT env.")
    parser.add_argument("--temp_dir", default=None,
                        help="Directory for intermediate / scratch files. "
                             "Created before the agent runs.")
    parser.add_argument("--raw-json-out", dest="raw_json_out", default=None,
                        help="Path to dump raw backend JSON / JSONL events "
                             "for out-of-band token / metric inspection.")
    args = parser.parse_args()

    backend_name = _resolve_backend(args.backend)
    if backend_name is None:
        sys.stderr.write(
            "ERROR: --backend is required (claude|codex|cursor); "
            "AGENT_BACKEND env may be used only as a manual-debug fallback.\n"
        )
        # Emit fail markers so the host wrapper's STATUS parser still sees a
        # value, even though the dispatcher exits 0.
        _emit_markers(sys.stderr, "fail", _zero_tokens(), 0.0)
        sys.exit(0)

    if backend_name not in _VALID_BACKENDS:
        sys.stderr.write(
            "ERROR: unknown backend '{}'. Valid: {}\n".format(
                backend_name, ", ".join(_VALID_BACKENDS))
        )
        _emit_markers(sys.stderr, "fail", _zero_tokens(), 0.0)
        sys.exit(0)

    # -- Ensure temp directory exists -----------------------------------------
    if args.temp_dir:
        os.makedirs(args.temp_dir, exist_ok=True)
        sys.stdout.write("Temp dir: {}\n".format(args.temp_dir))

    # -- Pre-populate output with fallback (repair) or empty list (detection)
    if args.task_type == "repair" and args.fallback:
        if os.path.isfile(args.fallback):
            shutil.copy2(args.fallback, args.output_file)
            sys.stdout.write("Fallback: copied original script to {}\n".format(
                args.output_file))
        else:
            sys.stderr.write("WARNING: fallback file not found: {}\n".format(
                args.fallback))
    elif args.task_type == "detection":
        try:
            os.makedirs(os.path.dirname(os.path.abspath(args.output_file)),
                        exist_ok=True)
        except Exception:
            pass
        with open(args.output_file, "w") as f:
            f.write("[]")
        sys.stdout.write("Fallback: wrote empty detection JSON to {}\n".format(
            args.output_file))

    # -- Read formatted prompt -------------------------------------------------
    with open(args.prompt_file) as f:
        prompt_text = f.read()

    sys.stdout.write("Backend: {}\n".format(backend_name))
    sys.stdout.write("Calling model: {}\n".format(args.model))
    if args.effort:
        sys.stdout.write("Reasoning effort: {}\n".format(args.effort))

    # -- Lazy import the backend module ---------------------------------------
    try:
        backend = importlib.import_module("agent.backends." + backend_name)
    except Exception as exc:
        sys.stderr.write("ERROR: failed to import backend '{}': {}\n".format(
            backend_name, exc))
        _emit_markers(sys.stderr, "fail", _zero_tokens(), 0.0)
        sys.exit(0)

    if not hasattr(backend, "call_agent"):
        sys.stderr.write("ERROR: backend '{}' has no call_agent().\n".format(
            backend_name))
        _emit_markers(sys.stderr, "fail", _zero_tokens(), 0.0)
        sys.exit(0)

    # -- Dispatch -------------------------------------------------------------
    result = backend.call_agent(
        prompt_text,
        args.output_file,
        args.model,
        workspace=args.workspace,
        effort=args.effort,
    )

    status = result.get("status", "fail")
    tokens = result.get("tokens") or _zero_tokens()
    runtime_seconds = float(result.get("runtime_seconds", 0.0) or 0.0)
    raw_data = result.get("raw_data")
    error = result.get("error")

    if error:
        sys.stderr.write("ERROR: {}\n".format(error))

    _emit_markers(sys.stderr, status, tokens, runtime_seconds)
    _dump_raw(args.raw_json_out, status, raw_data, error)

    # -- Verify the output file landed (advisory only) ------------------------
    if os.path.isfile(args.output_file):
        sys.stdout.write("Output file exists: {}\n".format(args.output_file))
    else:
        sys.stdout.write("WARNING: Output file not found: {}\n".format(
            args.output_file))

    # Always exit 0 -- the host wrapper keys off the STATUS= marker.
    sys.exit(0)


if __name__ == "__main__":
    main()
