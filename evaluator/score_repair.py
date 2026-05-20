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
# score_repair.py - Scoring script for DRC repair evaluation.
#
# Compares before (original) and after (repaired) DRC reports and computes
# repair_rate and new_violation_rate metrics.
#
# Supports KLayout DRC reports (.lyrpt XML) and processed JSON (.drc.json).

import argparse
import json
import os
import sys
import xml.etree.ElementTree as et


def parse_drc_report(report_path: str) -> dict:
    # Parse a DRC report, auto-detecting format by file extension.
    #
    # - .drc.json: Processed DRC JSON (structured)
    # - .lyrpt: KLayout DRC report (XML)
    #
    # Returns {rule_name: violation_count}.
    if report_path.endswith(".drc.json"):
        return _parse_drc_json(report_path)
    else:
        # Default: treat as KLayout XML (.lyrpt or unknown extension)
        return _parse_klayout_report(report_path)


def _parse_drc_json(report_path: str) -> dict:
    # Parse a processed DRC JSON report. Returns {rule_name: violation_count}.
    with open(report_path) as f:
        data = json.load(f)
    return {rule: info["violation_count"]
            for rule, info in data.get("rules", {}).items()}


def _parse_klayout_report(report_path: str) -> dict:
    # Parse a KLayout DRC report (.lyrpt XML file).
    #
    # Returns {rule_name: violation_count} where violation_count is the number
    # of <value> entries under each <item> element.
    tree = et.parse(report_path)
    root = tree.getroot()

    rule_violations = {}

    items = root.find("items")
    if items is None:
        return rule_violations

    for item in items.findall("item"):
        category_el = item.find("category")
        if category_el is None or category_el.text is None:
            continue

        # Category text may be wrapped in single quotes, e.g. 'RULE.NAME'
        rule_name = category_el.text.strip().strip("'")

        values_el = item.find("values")
        if values_el is None:
            violation_count = 0
        else:
            violation_count = len(values_el.findall("value"))

        # Accumulate counts if the same rule appears in multiple items
        rule_violations[rule_name] = rule_violations.get(rule_name, 0) + violation_count

    return rule_violations


def score_repair(original_report_path: str, repaired_report_path: str) -> dict:
    # Compare original and repaired DRC reports and compute evaluation metrics.
    #
    # Metrics returned:
    #     repair_rate          - fraction of original violations that were removed
    #     new_violation_rate   - fraction of new violations introduced relative to original
    original = parse_drc_report(original_report_path)
    repaired = parse_drc_report(repaired_report_path)

    original_violations = sum(original.values())
    final_violations = sum(repaired.values())

    # --- repair_rate ---
    if original_violations == 0:
        repair_rate = 1.0
        removed_violations = 0
    else:
        removed_violations = 0
        for rule, orig_count in original.items():
            repaired_count = repaired.get(rule, 0)
            removed_violations += max(0, orig_count - repaired_count)
        repair_rate = removed_violations / original_violations

    # --- new_violation_rate ---
    new_violations = 0
    for rule, repaired_count in repaired.items():
        orig_count = original.get(rule, 0)
        new_violations += max(0, repaired_count - orig_count)

    if original_violations == 0:
        if new_violations > 0:
            new_violation_rate = float("inf")
        else:
            new_violation_rate = 0.0
    else:
        new_violation_rate = new_violations / original_violations

    original_rules_violated = sum(1 for v in original.values() if v > 0)
    final_rules_violated = sum(1 for v in repaired.values() if v > 0)

    return {
        "repair_rate": repair_rate,
        "new_violation_rate": new_violation_rate,
        "original_violations": original_violations,
        "final_violations": final_violations,
        "removed_violations": removed_violations,
        "new_violations": new_violations,
        "original_rules_violated": original_rules_violated,
        "final_rules_violated": final_rules_violated,
    }


def _serialize_result(result: dict) -> dict:
    # Convert non-JSON-serializable values (e.g. inf) to strings for output.
    serializable = {}
    for key, value in result.items():
        if value == float("inf"):
            serializable[key] = "inf"
        else:
            serializable[key] = value
    return serializable


def _zero_repair_result() -> dict:
    # Placeholder result for runs where no repaired report exists (e.g. the
    # repair failed to render a GDS).  Mirrors the legacy inline JSON that
    # the shell pipeline used to emit in that situation.
    return {
        "repair_rate": 0,
        "new_violation_rate": "inf",
        "original_violations": 0,
        "final_violations": 0,
        "removed_violations": 0,
        "new_violations": 0,
        "original_rules_violated": 0,
        "final_rules_violated": 0,
    }


def main():
    # align the CLI with the caller.
    # token / runtime / status are always read from the trusted agent_meta
    # JSON, no longer via CLI flags.
    parser = argparse.ArgumentParser(description="Score DRC repair")
    parser.add_argument("--original-drc",  required=True,
                        help="trusted original DRC report path")
    parser.add_argument("--new-drc",       required=True,
                        help="DRC report after rendering repaired script")
    parser.add_argument("--output",        required=True,
                        help="score JSON output path")
    parser.add_argument("--agent-meta",    required=True,
                        help="trusted agent_meta JSON path")
    args = parser.parse_args()

    # ----- token / runtime / status always read from trusted meta -----
    with open(args.agent_meta) as f:
        meta = json.load(f)
    agent_status        = meta.get("agent_status", "fail")
    agent_runtime_secs  = float(meta.get("agent_runtime_seconds") or 0.0)
    tokens              = meta.get("tokens") or {}

    # ----- main scoring logic -----
    if not args.new_drc or not os.path.isfile(args.new_drc):
        result = _zero_repair_result()
    else:
        result = score_repair(args.original_drc, args.new_drc)

    # ----- Attach shared fields (shared score schema) -----
    # repair score happy-path marks valid_repair=True so
    # write_score_csv._pick_fields can detect the REPAIR_FIELDS schema.
    result["valid_repair"]          = True
    result["agent_status"]          = agent_status
    result["runtime_seconds"]       = agent_runtime_secs
    result["input_tokens"]          = int(tokens.get("input_tokens", 0))
    result["output_tokens"]         = int(tokens.get("output_tokens", 0))
    result["cache_read_tokens"]     = int(tokens.get("cache_read_tokens", 0))
    result["cache_write_tokens"]    = int(tokens.get("cache_write_tokens", 0))

    # ----- Embed evaluator_hash (sha256sum-style over evaluator/*.py + *.sh).
    # Pipeline invokes us as `python3 ${evaluator_dir}/score_repair.py ...`
    # so sys.path[0] is the evaluator directory and the sibling import
    # resolves. Wrap in try/except so a future import bug does not kill
    # the whole score; an empty string makes the failure visible to
    # readers without losing the rest of the record.
    try:
        from compute_evaluator_hash import compute_evaluator_hash
        result["evaluator_hash"] = compute_evaluator_hash(
            os.path.dirname(os.path.abspath(__file__)))
    except Exception as _exc:
        sys.stderr.write(
            "WARN: evaluator_hash compute failed: {!r}\n".format(_exc))
        result["evaluator_hash"] = ""

    # ----- write output file (no longer prints to stdout) -----
    with open(args.output, "w") as f:
        json.dump(_serialize_result(result), f, indent=2)


if __name__ == "__main__":
    main()
