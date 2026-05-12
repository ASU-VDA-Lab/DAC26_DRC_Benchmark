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

"""Parse info.json and output shell variable assignments for key fields."""

import argparse
import json
import shlex
import sys


REQUIRED_KEYS = ["task_type", "model_name", "case_name", "design_type"]


def main():
    parser = argparse.ArgumentParser(
        description="Parse info.json and emit shell variable assignments."
    )
    parser.add_argument("info_json", help="Path to info.json")
    args = parser.parse_args()

    try:
        with open(args.info_json, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {args.info_json}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {args.info_json}: {exc}", file=sys.stderr)
        sys.exit(1)

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        print(
            f"Error: missing keys in {args.info_json}: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    for key in REQUIRED_KEYS:
        print(f"{key}={shlex.quote(str(data[key]))}")


if __name__ == "__main__":
    main()
