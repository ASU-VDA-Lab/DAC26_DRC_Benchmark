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
#Post-process info.json by filling in resolved paths for the pipeline.

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Post-process info.json with resolved paths."
    )
    parser.add_argument("--input", required=True, help="Input info.json path")
    parser.add_argument("--output", required=True, help="Output info.json path")
    parser.add_argument("--skill_file", required=True, help="Path to skill file")
    parser.add_argument("--testcase_dir", required=True, help="Testcase directory")
    parser.add_argument("--case_name", required=True, help="Case name")
    parser.add_argument("--golden_report", required=True, help="Golden DRC report path")
    parser.add_argument("--design_rule", required=True, help="Design rule file path")
    parser.add_argument("--drm_jpg", default="", help="Path to DRM JPG directory")
    parser.add_argument("--output_path", required=True, help="Output path for results")
    parser.add_argument("--temp_dir", required=True, help="Temporary directory path")
    parser.add_argument("--task_type", required=True, help="Task type (detection/repair)")

    args = parser.parse_args()

    try:
        with open(args.input, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {args.input}: {exc}", file=sys.stderr)
        sys.exit(1)

    data["path_to_skill"] = args.skill_file
    data["path_to_layout_script"] = (
        f"{args.testcase_dir}/layout_script/{args.case_name}.py"
    )
    data["path_to_layout_screenshot"] = (
        f"{args.testcase_dir}/layout_screenshot/{args.case_name}/{args.case_name}.png"
    )
    data["path_to_drc_report"] = (
        args.golden_report if args.task_type == "repair" else ""
    )
    data["path_to_design_rule"] = args.design_rule
    data["path_to_drm_jpg"] = args.drm_jpg
    # Remap connectivity file path if present (cell and block designs only)
    if "path_to_connectivity_file" in data:
        data["path_to_connectivity_file"] = (
            f"{args.testcase_dir}/connectivity/{args.case_name}.json"
        )
    data["output_path"] = args.output_path
    data["temp_dir"] = args.temp_dir

    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
