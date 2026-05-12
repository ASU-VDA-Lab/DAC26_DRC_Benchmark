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
# run_klayout_drc.py - Run KLayout DRC checks via command line.
#
# KLayout is invoked in batch mode with a .lydrc rule file and produces a
# .lyrpt XML report.
#
# Usage:
#     python run_klayout_drc.py <gds_path> <drc_rule_path> <report_output_path>
#
# For ASAP7 designs:
#     - Cell-type designs:              testcase/asap7/asap7_cell.lydrc
#     - Polygon- and block-type designs: testcase/asap7/asap7.lydrc

import subprocess
import sys


def run_klayout_drc(gds_path: str, drc_rule_path: str, report_output_path: str) -> int:
    # Run KLayout DRC check on a GDS file.
    #
    # Executes KLayout in batch mode (-b) with the supplied rule file (-r),
    # passing the input GDS and output report paths as runtime defines (-rd).
    #
    # Args:
    #     gds_path:           Path to the input GDS file.
    #     drc_rule_path:      Path to the KLayout DRC rule file (.lydrc).
    #     report_output_path: Destination path for the DRC report (.lyrpt).
    #
    # Returns:
    #     The subprocess return code (0 on success, non-zero on failure).
    cmd = [
        "klayout",
        "-b",
        "-r", drc_rule_path,
        "-rd", f"in_gds={gds_path}",
        "-rd", f"report_file={report_output_path}",
    ]

    print(f"Running KLayout DRC:")
    print(f"  GDS:    {gds_path}")
    print(f"  Rules:  {drc_rule_path}")
    print(f"  Report: {report_output_path}")

    result = subprocess.run(cmd, universal_newlines=True)
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            f"Usage: python {sys.argv[0]} <gds_path> <drc_rule_path> <report_output_path>",
            file=sys.stderr,
        )
        sys.exit(1)

    gds_path = sys.argv[1]
    drc_rule_path = sys.argv[2]
    report_output_path = sys.argv[3]

    return_code = run_klayout_drc(gds_path, drc_rule_path, report_output_path)

    if return_code == 0:
        print(f"DRC complete. Return code: {return_code}")
        print(f"Report written to: {report_output_path}")
    else:
        print(f"DRC failed. Return code: {return_code}", file=sys.stderr)

    sys.exit(return_code)
