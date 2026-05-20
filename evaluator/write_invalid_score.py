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
#write_invalid_score.py - emit fail-closed invalid score JSON.
#
#Invariants:
#1. Always exit 0 (a fail-closed handler must not propagate a fatal error).
#2. When ``--agent-meta`` is missing / malformed, tokens are all 0 + stderr
#   WARN (fail-soft, no raise).
#3. The detection / repair schema aligns with the full-schema
#   invariant (same key count / names / types as the successful outputs of
#   score_detection.py / score_repair.py).
#4. ``--null-metrics``: emit JSON ``null`` for every task metric field.
#5. ``--fail-closed-zero-metrics``: emit 0 for metric fields
#   (or ``new_violation_rate="inf"``).
#6. ``--null-tokens``: emit null for the 4 token fields (overriding trusted
#   meta); otherwise tokens come from trusted meta (``agent_failed`` uses
#   ``--null-tokens``; other invalid cases do not).
#7. ``--null-metrics`` and ``--fail-closed-zero-metrics`` are mutually
#   exclusive; if neither is given, the default is treated as
#   ``--fail-closed-zero-metrics``.

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Repair task metric key sets
# ---------------------------------------------------------------------------
REPAIR_METRIC_KEYS_ZERO: Dict[str, Any] = {
    "repair_rate": 0,
    "new_violation_rate": "inf",
    "original_violations": 0,
    "final_violations": 0,
    "removed_violations": 0,
    "new_violations": 0,
    "original_rules_violated": 0,
    "final_rules_violated": 0,
    "sanity_passed": None,
    "connectivity_passed": None,
}

REPAIR_METRIC_KEYS_NULL: Dict[str, Any] = {
    "repair_rate": None,
    "new_violation_rate": None,
    "original_violations": None,
    "final_violations": None,
    "removed_violations": None,
    "new_violations": None,
    "original_rules_violated": None,
    "final_rules_violated": None,
    "sanity_passed": None,
    "connectivity_passed": None,
}


# ---------------------------------------------------------------------------
# Detection task metric key sets
# ---------------------------------------------------------------------------
DETECTION_METRIC_KEYS_ZERO: Dict[str, Any] = {
    "sum_precision": 0,
    "sum_recall": 0,
    "sum_f1": 0,
    "total_predicted_violations": 0,
    "total_golden_violations": 0,
    "total_rules_predicted": 0,
    "total_rules_golden": 0,
    "total_rules_union": 0,
    "sum_tp": 0,
    "sum_fp": 0,
    "sum_fn": 0,
    "sanity_passed": None,        # detection does not run sanity
    "connectivity_passed": None,  # detection does not run connectivity
}

DETECTION_METRIC_KEYS_NULL: Dict[str, Any] = {
    "sum_precision": None,
    "sum_recall": None,
    "sum_f1": None,
    "total_predicted_violations": None,
    "total_golden_violations": None,
    "total_rules_predicted": None,
    "total_rules_golden": None,
    "total_rules_union": None,
    "sum_tp": None,
    "sum_fp": None,
    "sum_fn": None,
    "sanity_passed": None,
    "connectivity_passed": None,
}


def _read_agent_meta(path_str: Optional[str]) -> Dict[str, Any]:
    """Read the trusted agent_meta JSON. Missing / malformed file returns a
    dummy (tokens=0, status=fail).

    fail-soft: never raises; any IO / JSON failure is stderr WARN'd and the
    fallback is returned.
    """
    fallback: Dict[str, Any] = {
        "agent_status": "fail",
        "agent_runtime_seconds": 0.0,
        "tokens": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        },
    }
    if not path_str:
        sys.stderr.write(
            "WARN: --agent-meta not provided; tokens=0\n"
        )
        return fallback
    p = Path(path_str)
    if not p.is_file():
        sys.stderr.write(
            "WARN: agent meta not found: {}; tokens=0\n".format(path_str)
        )
        return fallback
    try:
        with p.open("r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(
            "WARN: agent meta unreadable ({}); tokens=0\n".format(exc)
        )
        return fallback
    if not isinstance(data, dict):
        sys.stderr.write(
            "WARN: agent meta is not a JSON object; tokens=0\n"
        )
        return fallback
    # Fill in default fields to avoid KeyError
    data.setdefault("agent_status", "fail")
    data.setdefault("agent_runtime_seconds", 0.0)
    tokens = data.get("tokens") or {}
    if not isinstance(tokens, dict):
        tokens = {}
    for k in ("input_tokens", "output_tokens",
              "cache_read_tokens", "cache_write_tokens"):
        tokens.setdefault(k, 0)
    data["tokens"] = tokens
    return data


def _build_record(
    task: str,
    invalid_reason: str,
    null_metrics: bool,
    null_tokens: bool,
    agent_meta: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the fail-closed result dict from task and flags."""
    if task == "repair":
        valid_key = "valid_repair"
        metric_block = (
            REPAIR_METRIC_KEYS_NULL if null_metrics else REPAIR_METRIC_KEYS_ZERO
        )
    elif task == "detection":
        valid_key = "valid_detection"
        metric_block = (
            DETECTION_METRIC_KEYS_NULL if null_metrics else DETECTION_METRIC_KEYS_ZERO
        )
    else:
        # argparse already restricts via choices=["detection", "repair"], so
        # this is theoretically unreachable; function-level fallback in case
        # a caller bypasses argparse and calls _build_record directly.
        raise AssertionError(
            "unreachable: task must be detection|repair, got {!r}".format(task)
        )

    record: Dict[str, Any] = {
        valid_key: False,
        "invalid_reason": invalid_reason,
    }
    record.update(metric_block)
    record["agent_status"] = agent_meta.get("agent_status", "fail")
    if null_metrics:
        record["runtime_seconds"] = None
    else:
        try:
            record["runtime_seconds"] = float(
                agent_meta.get("agent_runtime_seconds") or 0.0
            )
        except (TypeError, ValueError):
            record["runtime_seconds"] = 0.0

    if null_tokens:
        record["input_tokens"] = None
        record["output_tokens"] = None
        record["cache_read_tokens"] = None
        record["cache_write_tokens"] = None
    else:
        tokens = agent_meta.get("tokens", {}) or {}
        if not isinstance(tokens, dict):
            tokens = {}
        for key in ("input_tokens", "output_tokens",
                    "cache_read_tokens", "cache_write_tokens"):
            try:
                record[key] = int(tokens.get(key, 0) or 0)
            except (TypeError, ValueError):
                record[key] = 0
    return record


def main() -> int:
    ap = argparse.ArgumentParser(
        description="emit fail-closed invalid score JSON",
    )
    ap.add_argument("--output", required=True,
                    help="invalid score JSON output path")
    ap.add_argument("--task", required=True,
                    choices=["detection", "repair"],
                    help="task type (detection|repair)")
    ap.add_argument("--invalid-reason", required=True,
                    help="machine-readable invalid reason tag")
    ap.add_argument("--agent-meta", default="",
                    help="trusted agent_meta JSON path (fail-soft if missing)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--null-metrics", action="store_true",
                   help="emit null for all task metric fields")
    g.add_argument("--fail-closed-zero-metrics", action="store_true",
                   help="emit 0 (or 'inf') for all task metric fields")
    ap.add_argument("--null-tokens", action="store_true",
                    help="emit null for all 4 token fields")
    args = ap.parse_args()

    # Default behaves like --fail-closed-zero-metrics (when neither
    # member of the mutually-exclusive group is selected, treat as zero).
    null_metrics = bool(args.null_metrics)

    agent_meta = _read_agent_meta(args.agent_meta)
    record = _build_record(
        task=args.task,
        invalid_reason=args.invalid_reason,
        null_metrics=null_metrics,
        null_tokens=args.null_tokens,
        agent_meta=agent_meta,
    )

    # ----- Embed evaluator_hash (sha256sum-style over evaluator/*.py + *.sh).
    # Sibling import works because the pipeline invokes us positionally
    # (python3 ${evaluator_dir}/write_invalid_score.py ...), placing the
    # evaluator directory at sys.path[0]. Try/except so an import bug
    # never kills the fail-closed handler — semantic-empty hash makes
    # the failure visible without losing the rest of the record.
    try:
        from compute_evaluator_hash import compute_evaluator_hash
        record["evaluator_hash"] = compute_evaluator_hash(
            os.path.dirname(os.path.abspath(__file__)))
    except Exception as _exc:
        sys.stderr.write(
            "WARN: evaluator_hash compute failed: {!r}\n".format(_exc))
        record["evaluator_hash"] = ""

    out_path = Path(args.output)
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w") as f:
            json.dump(record, f, indent=2)
    except OSError as exc:
        sys.stderr.write(
            "WARN: failed to write {}: {}\n".format(out_path, exc)
        )
        # Still exit 0; the fail-closed handler itself must not propagate
        # a fatal error.
    return 0


if __name__ == "__main__":
    sys.exit(main())
