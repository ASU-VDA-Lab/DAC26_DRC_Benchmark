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
# Rewrite layout.write(...) path in LLM output script for GDS rendering.
#
# Usage:
#     python3 evaluator/prepare_render_script.py <input_script> <render_script> <output_gds>

import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python3 prepare_render_script.py <input_script> <render_script> <output_gds>",
            file=sys.stderr,
        )
        sys.exit(1)

    script_path = Path(sys.argv[1])
    render_script_path = Path(sys.argv[2])
    output_gds = sys.argv[3]

    if not script_path.exists():
        raise FileNotFoundError(f"LLM output script not found: {script_path}")

    script_text = script_path.read_text()
    replacement = f"layout.write({json.dumps(output_gds)})"
    updated_text, count = re.subn(
        r"layout\.write\(\s*(['\"]).*?\1\s*\)",
        replacement,
        script_text,
    )

    if count == 0:
        if updated_text and not updated_text.endswith("\n"):
            updated_text += "\n"
        updated_text += f"\n{replacement}\n"

    render_script_path.write_text(updated_text)
    print(f"  Prepared render script: {render_script_path}")
    print(f"  Target GDS path       : {output_gds}")


if __name__ == "__main__":
    main()
