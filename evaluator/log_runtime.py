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
# Append a row to runtime.csv. Adds num_calls column (appended at end).
#
# Usage:
#   python3 log_runtime.py <csv> <model> <effort> <task> <design> <case> \
#     <status> <runtime_s> <tokens_json> <ts> [--num-calls N]
#
# Legacy CSVs (12-col header, no num_calls) are migrated in place on first append.

import csv
import json
import os
import sys


FIELDNAMES = [
    "model", "effort", "task_type", "design_type", "case_name",
    "agent_status", "agent_runtime_seconds",
    "input_tokens", "output_tokens",
    "cache_read_tokens", "cache_write_tokens",
    "timestamp", "num_calls",
]


def _extract_num_calls(argv):
    """Pop --num-calls N out of argv. Default 0 on absent / malformed."""
    out = []
    num_calls = 0
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--num-calls":
            if i + 1 < len(argv):
                try:
                    num_calls = int(argv[i + 1])
                except (TypeError, ValueError):
                    num_calls = 0
                i += 2
                continue
            i += 1
            continue
        if tok.startswith("--num-calls="):
            try:
                num_calls = int(tok.split("=", 1)[1])
            except (TypeError, ValueError):
                num_calls = 0
            i += 1
            continue
        out.append(tok)
        i += 1
    if num_calls < 0:
        num_calls = 0
    return out, num_calls


def main():
    argv, num_calls = _extract_num_calls(sys.argv[1:])
    if len(argv) != 10:
        print(
            "Usage: python3 log_runtime.py <csv_path> <model> <effort> <task_type> "
            "<design_type> <case_name> <agent_status> <agent_runtime> "
            "<tokens_json> <timestamp> [--num-calls N]",
            file=sys.stderr,
        )
        sys.exit(1)

    (csv_path, model, effort, task_type, design_type, case_name,
     agent_status, agent_rt, tokens_raw, ts) = argv

    try:
        tokens = json.loads(tokens_raw)
    except json.JSONDecodeError:
        with open(tokens_raw) as f:
            tokens = json.load(f)

    write_header = (not os.path.exists(csv_path)) or os.path.getsize(csv_path) == 0

    # Migrate pre-upgrade CSVs (header missing num_calls) so column widths stay aligned.
    # Skipped when write_header is True (covers fresh-file AND 0-byte cases).
    if not write_header:
        try:
            with open(csv_path, "r", newline="") as f:
                existing_header = next(csv.reader(f), [])
        except OSError:
            existing_header = list(FIELDNAMES)
        if existing_header and existing_header != FIELDNAMES:
            with open(csv_path, "r", newline="") as f:
                rows = list(csv.DictReader(f))
            tmp_path = csv_path + ".tmp"
            with open(tmp_path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=FIELDNAMES)
                w.writeheader()
                for r in rows:
                    r.setdefault("num_calls", "0")
                    w.writerow({k: r.get(k, "") for k in FIELDNAMES})
            os.rename(tmp_path, csv_path)

    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "model": model,
            "effort": effort,
            "task_type": task_type,
            "design_type": design_type,
            "case_name": case_name,
            "agent_status": agent_status,
            "agent_runtime_seconds": agent_rt,
            "input_tokens":       int(tokens.get("input_tokens", 0)),
            "output_tokens":      int(tokens.get("output_tokens", 0)),
            "cache_read_tokens":  int(tokens.get("cache_read_tokens", 0)),
            "cache_write_tokens": int(tokens.get("cache_write_tokens", 0)),
            "timestamp": ts,
            "num_calls": num_calls,
        })

    print(f"  Runtime logged: {csv_path}")


if __name__ == "__main__":
    main()
