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
# Merge sanity check fields into a score JSON file.
#
# Usage:
#     python3 evaluator/merge_score_sanity.py <score_json> <sanity_json>

import json
import sys


STRUCTURAL_KEYS = [
    "top_cell_exists",
    "gds_not_empty",
    "critical_layers_preserved",
    "cell_structure_intact",
    "outline_boundary_respected",
    "instance_placements_unchanged",
    "polygon_shape_counts_ok",
]

OPTIONAL_DETAIL_KEYS = [
    "protruding_layers",
    "missing_instances",
    "extra_instances",
    "shape_count_mismatches",
]


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python3 merge_score_sanity.py <score_json> <sanity_json>",
            file=sys.stderr,
        )
        sys.exit(1)

    score_path = sys.argv[1]
    sanity_path = sys.argv[2]

    with open(score_path) as f:
        score_data = json.load(f)

    with open(sanity_path) as f:
        sanity_data = json.load(f)

    score_data["sanity_passed"]  = sanity_data.get("passed")
    score_data["sanity_details"] = sanity_data.get("details")

    for key in STRUCTURAL_KEYS:
        if key in sanity_data:
            score_data[key] = sanity_data[key]

    for key in OPTIONAL_DETAIL_KEYS:
        if sanity_data.get(key):
            score_data[key] = sanity_data[key]

    with open(score_path, "w") as f:
        json.dump(score_data, f, indent=2)

    print("  Sanity fields merged into score JSON.")


if __name__ == "__main__":
    main()
