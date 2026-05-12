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
# Append a row to the runtime CSV log.
#
# Usage:
#     python3 evaluator/log_runtime.py <csv_path> <model> <effort> <task_type> <design_type> \
#         <case_name> <agent_status> <agent_runtime> \
#         <tokens_json> <timestamp>
#
# <tokens_json> is either a JSON string or a path to a JSON file containing
# the four token fields (input_tokens, output_tokens, cache_read_tokens,
# cache_write_tokens).

import csv
import json
import os
import sys


FIELDNAMES = [
    "model", "effort", "task_type", "design_type", "case_name",
    "agent_status",
    "agent_runtime_seconds",
    "input_tokens", "output_tokens",
    "cache_read_tokens", "cache_write_tokens",
    "timestamp",
]


def main():
    if len(sys.argv) != 11:
        print(
            "Usage: python3 log_runtime.py <csv_path> <model> <effort> <task_type> "
            "<design_type> <case_name> <agent_status> <agent_runtime> "
            "<tokens_json> <timestamp>",
            file=sys.stderr,
        )
        sys.exit(1)

    (csv_path, model, effort, task_type, design_type, case_name,
     agent_status, agent_rt, tokens_raw, ts) = sys.argv[1:]

    try:
        tokens = json.loads(tokens_raw)
    except json.JSONDecodeError:
        with open(tokens_raw) as f:
            tokens = json.load(f)

    write_header = not os.path.exists(csv_path)

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
        })

    print(f"  Runtime logged: {csv_path}")


if __name__ == "__main__":
    main()
