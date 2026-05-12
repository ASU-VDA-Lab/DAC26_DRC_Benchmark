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
# Build the info.json for a specific test case.
#
# Used by evaluate_cursor.sh to reproduce the paper's experiment table.
# To run a single case, prepare your own info.json (see agent/README.md
# "Example info.json" section, or testcase/<design>/<case>/ fixtures)
# and call run_pipeline_cursor.sh directly.
#
# Usage (named args -- used by evaluate_cursor.sh on the host):
#     python3 src/build_case_info.py \\
#         --model_name claude-opus-4-6 \\
#         --case_name Cell100 \\
#         --design_type cell \\
#         --task_type repair \\
#         --output_path /path/to/output \\
#         --path_to_layout_script /path/to/Cell100.py \\
#         --path_to_layout_screenshot /path/to/Cell100/Cell100.png \\
#         --path_to_drc_report /path/to/Cell100.drc.json \\
#         --path_to_design_rule /path/to/asap7_cell.lydrc \\
#         --path_to_drm_jpg /path/to/drm_jpg \\
#         --path_to_skill /path/to/skill.md \\
#         --temp_dir temp/... \\
#         --json_output_path /path/to/info.json

import argparse
import json


def main():
    parser = argparse.ArgumentParser(
        description="Build info.json for a DRC benchmark test case",
    )
    parser.add_argument("--model_name", required=True,
                        help="Model name (e.g. claude-opus-4-6)")
    parser.add_argument("--case_name", required=True,
                        help="Test case name (e.g. Cell100)")
    parser.add_argument("--design_type", required=True,
                        choices=["cell", "polygon", "block"])
    parser.add_argument("--task_type", required=True,
                        choices=["repair", "detection"])
    parser.add_argument("--output_path", required=True,
                        help="Path where agent should write output")
    parser.add_argument("--path_to_layout_script", required=True)
    parser.add_argument("--path_to_layout_screenshot", required=True)
    parser.add_argument("--path_to_drc_report", required=True,
                        help="Path to golden DRC report")
    parser.add_argument("--path_to_design_rule", required=True)
    parser.add_argument("--path_to_drm_jpg", default="",
                        help="Path to DRM JPG directory")
    parser.add_argument("--path_to_skill", default="",
                        help="Path to skill.md")
    parser.add_argument("--temp_dir", default="",
                        help="Temp directory for intermediate files")
    parser.add_argument("--json_output_path", required=True,
                        help="Where to write the generated info.json")
    args = parser.parse_args()

    info = {
        "model_name": args.model_name,
        "case_name": args.case_name,
        "design_type": args.design_type,
        "task_type": args.task_type,
        "path_to_skill": args.path_to_skill,
        "path_to_layout_script": args.path_to_layout_script,
        "path_to_layout_screenshot": args.path_to_layout_screenshot,
        "path_to_drc_report": args.path_to_drc_report,
        "path_to_design_rule": args.path_to_design_rule,
        "path_to_drm_jpg": args.path_to_drm_jpg,
        "output_path": args.output_path,
        "temp_dir": args.temp_dir,
    }

    # Add connectivity file path for cell and block designs (not polygon)
    if args.design_type in ("cell", "block"):
        info["path_to_connectivity_file"] = (
            f"testcase/asap7/{args.design_type}/connectivity/{args.case_name}.json"
        )

    # For detection, clear the DRC report path so the agent cannot see golden answers
    if args.task_type == "detection":
        info["path_to_drc_report"] = ""

    with open(args.json_output_path, "w") as f:
        json.dump(info, f, indent=2)


if __name__ == "__main__":
    main()
