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
# Convert a score JSON to a single-row CSV.
#
# Reference impl:
#   1. Python None -> CSV string "NULL" (not empty string).
#   2. Fixed fieldnames per task_type (DETECTION_FIELDS / REPAIR_FIELDS) —
#      do not derive fieldnames dynamically from the first score JSON;
#      cross-case schema divergence would misalign columns.
#   3. inf float -> "inf" string (legacy behavior preserved).
#   4. Append row if header matches; rewrite (with WARN) if header diverges.
#
# Usage:
#     python3 evaluator/write_score_csv.py <score_json> <output_csv> <case_name>

import csv
import json
import sys


# fixed fieldnames aligned with the full-schema invariant
DETECTION_FIELDS = [
    "case_name", "valid_detection", "invalid_reason",
    "sum_precision", "sum_recall", "sum_f1",
    "total_predicted_violations", "total_golden_violations",
    "total_rules_predicted", "total_rules_golden", "total_rules_union",
    "sum_tp", "sum_fp", "sum_fn",
    "sanity_passed", "connectivity_passed",
    "agent_status", "runtime_seconds",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
]

REPAIR_FIELDS = [
    "case_name", "valid_repair", "invalid_reason",
    "repair_rate", "new_violation_rate",
    "original_violations", "final_violations",
    "removed_violations", "new_violations",
    "original_rules_violated", "final_rules_violated",
    "sanity_passed", "connectivity_passed",
    "agent_status", "runtime_seconds",
    "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
]


def _normalize(v):
    """None -> 'NULL'; inf float -> 'inf' (legacy)."""
    if v is None:
        return "NULL"
    if isinstance(v, float) and v == float("inf"):
        return "inf"
    return v


def _pick_fields(data):
    """Choose task_type fieldnames based on the valid_* key in the score JSON."""
    if "valid_detection" in data:
        return DETECTION_FIELDS
    elif "valid_repair" in data:
        return REPAIR_FIELDS
    else:
        # Should not happen (write_invalid_score.py / score_*.py both set
        # the valid_* key); fallback: use the keys that appeared, but still
        # put case_name in the first column.
        return ["case_name"] + sorted(k for k in data.keys() if k != "case_name")


def write_csv(score_json_path, csv_path, case_name):
    with open(score_json_path) as f:
        data = json.load(f)

    fields = _pick_fields(data)
    row = {"case_name": case_name}
    for k in fields:
        if k == "case_name":
            continue
        row[k] = _normalize(data.get(k))

    # Header matches -> append; mismatch or missing -> rewrite (with WARN).
    write_header = False
    try:
        with open(csv_path) as f:
            existing_header = f.readline().rstrip("\n").rstrip("\r")
            existing_fields = existing_header.split(",")
            if existing_fields != fields:
                sys.stderr.write(
                    "WARN: CSV header mismatch for {}; rewriting\n".format(csv_path)
                )
                write_header = True
                # First version simply truncates the old rows; if production
                # needs to preserve old rows, read them into memory, fill
                # missing columns, then rewrite.
    except FileNotFoundError:
        write_header = True

    mode = "w" if write_header else "a"
    with open(csv_path, mode, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    print(f"  CSV saved to: {csv_path}")


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python3 write_score_csv.py <score_json> <output_csv> <case_name>",
            file=sys.stderr,
        )
        sys.exit(1)

    score_json = sys.argv[1]
    score_csv = sys.argv[2]
    case_name = sys.argv[3]

    write_csv(score_json, score_csv, case_name)


if __name__ == "__main__":
    main()
