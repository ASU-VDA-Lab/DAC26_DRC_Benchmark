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
# src/agent_backend/per_call_writer_helpers.py
#
# Single source of truth for per-call token recording shared across the
# claude / codex / cursor backends. Layout-mandatory recording: the host
# pipeline fails closed when STATUS=success but ${score_dir}/calls/ has
# zero files for the case (see write_invalid_score.py and
# evaluator/aggregate_call_tokens.py).
#
# Public API:
#   - next_call_id(case_name, session_id) -> str
#   - build_call_payload(case_name, call_id, model_name, by_model_usage,
#                       started_at=None, finished_at=None) -> dict
#   - write_call(calls_dir, call_id, payload) -> str | None
#
# Stdlib-only.

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional


# Module-level monotonic call counter. Starts at 0; first call_id has
# call_seq=0001 after the first increment in next_call_id().
_CALL_SEQ = 0


TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)


def _zero_tokens() -> Dict[str, int]:
    return {k: 0 for k in TOKEN_KEYS}


def _fallback_sid8(case_name: str, call_seq: int) -> str:
    """Derive a deterministic 8-hex-char short session id when the CLI
    doesn't expose one. Inputs include pid + a high-resolution monotonic
    timestamp so two backend processes in the same case don't collide.
    Uses int(time.monotonic() * 1e9) for Python 3.6 compatibility
    (time.monotonic_ns() is 3.7+)."""
    blob = "{}|{}|{}|{}".format(
        case_name, call_seq, os.getpid(), int(time.monotonic() * 1e9)
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:8]


def next_call_id(case_name: str, session_id: Optional[str]) -> str:
    """Increment _CALL_SEQ and return a new call_id.

    Format: ``${case_name}_${call_seq:04d}_${short_session_id8}``.

    Constraint: total length is held to ``<= 64`` so the canonical
    ``CALL_ID_RE = ^[A-Za-z0-9_-]{1,64}$`` at
    ``evaluator/aggregate_call_tokens.py`` continues to match without
    a regex change. If the case_name pushes the total past 64 chars
    the sid8 is silently truncated (defensive only — typical case
    names are under 50 chars).
    """
    global _CALL_SEQ
    _CALL_SEQ += 1
    seq_str = "{:04d}".format(_CALL_SEQ)

    if session_id:
        # First 8 hex chars; strip non-hex characters defensively.
        s = "".join(c for c in str(session_id) if c in "0123456789abcdefABCDEF")
        if len(s) >= 8:
            sid8 = s[:8].lower()
        else:
            sid8 = _fallback_sid8(case_name or "unknown", _CALL_SEQ)
    else:
        sid8 = _fallback_sid8(case_name or "unknown", _CALL_SEQ)

    case = case_name if case_name else "unknown"
    call_id = "{}_{}_{}".format(case, seq_str, sid8)

    if len(call_id) > 64:
        # Truncate the sid suffix to keep the total at 64; minimum 1
        # char of suffix preserved (defensive only — typical case
        # names are far under 50 chars).
        budget = 64 - len("{}_{}_".format(case, seq_str))
        if budget < 1:
            budget = 1
        sid8 = sid8[:budget]
        call_id = "{}_{}_{}".format(case, seq_str, sid8)

    return call_id


def build_call_payload(
    case_name: str,
    call_id: str,
    model_name: str,
    by_model_usage: Dict[str, Dict[str, int]],
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the per-call JSON schema.

    ``by_model_usage`` is a dict keyed by model id, each value a dict with
    the four canonical snake_case token keys. Top-level four-key totals
    are computed as sum over by_model.

    Raises ``TypeError`` / ``ValueError`` on malformed input.
    """
    if not isinstance(by_model_usage, dict):
        raise TypeError("by_model_usage must be dict, got {!r}".format(
            type(by_model_usage).__name__))
    if not by_model_usage:
        raise ValueError("by_model_usage must be non-empty")

    # Sanitize and sum.
    sanitized: Dict[str, Dict[str, int]] = {}
    totals = _zero_tokens()
    for model, usage in by_model_usage.items():
        if not isinstance(usage, dict):
            raise TypeError(
                "by_model_usage[{!r}] must be dict, got {!r}".format(
                    model, type(usage).__name__))
        entry = {}
        for k in TOKEN_KEYS:
            try:
                v = int(usage.get(k, 0) or 0)
            except (TypeError, ValueError):
                v = 0
            if v < 0:
                v = 0
            entry[k] = v
            totals[k] += v
        sanitized[str(model)] = entry

    payload: Dict[str, Any] = {
        "call_id": str(call_id),
        "case_name": str(case_name) if case_name else "unknown",
        "model": str(model_name) if model_name else "",
        "schema_version": "1",
    }
    for k in TOKEN_KEYS:
        payload[k] = totals[k]
    payload["by_model"] = sanitized

    if started_at is not None:
        payload["started_at"] = str(started_at)
    if finished_at is not None:
        payload["finished_at"] = str(finished_at)

    return payload


def write_call(calls_dir: str, call_id: str, payload: Dict[str, Any]) -> Optional[str]:
    """Write payload to ``${calls_dir}/${call_id}.json`` via O_CREAT|O_EXCL.

    Returns absolute path written on success, ``None`` on any non-collision
    failure. ``FileExistsError`` is re-raised — the caller is expected to
    increment _CALL_SEQ via a fresh ``next_call_id`` and retry once
    (per the policy in CUSTOM_AGENT.md).
    """
    target = os.path.abspath(os.path.join(calls_dir, "{}.json".format(call_id)))
    # Use 'x' mode = O_CREAT | O_EXCL — atomic, no overwrite.
    with open(target, "x") as f:
        json.dump(payload, f, indent=2)
    return target
