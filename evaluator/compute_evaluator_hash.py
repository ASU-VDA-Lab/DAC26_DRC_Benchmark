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
# evaluator/compute_evaluator_hash.py
#
# Compute a deterministic multi-line sha256sum-style string over
# evaluator/*.py + evaluator/*.sh (non-recursive). The string is embedded
# in every per-case score JSON via the ``evaluator_hash`` field by the three
# score writers (score_repair.py, score_detection.py, write_invalid_score.py).
#
# Output format matches GNU sha256sum: ``<hex>  <basename>\n`` (two spaces).
# Sort order: ASCII (LC_ALL=C-equivalent) on basename. LF only. ASCII
# basenames required.
#
# Stdlib-only. Self-contained so it can be invoked as
# ``python3 evaluator/compute_evaluator_hash.py`` for CLI smoke testing.

import hashlib
import os
import sys


def compute_evaluator_hash(evaluator_dir):
    """Compute multi-line sha256sum-style hash for evaluator/*.py + *.sh.

    Args:
        evaluator_dir: absolute path to the evaluator directory.

    Returns:
        Multi-line string of ``<hex>  <basename>\\n`` lines, sorted ASCII,
        ending with ``\\n``.

    Raises:
        FileNotFoundError: evaluator_dir does not exist.
        ValueError: a basename is not ASCII-safe.
    """
    if not os.path.isdir(evaluator_dir):
        raise FileNotFoundError(
            "evaluator_dir does not exist: {!r}".format(evaluator_dir)
        )

    # Non-recursive enumeration: only top-level *.py and *.sh.
    # Skip subdirs (trusted_bin/, __pycache__/, etc.) by checking isfile.
    names = []
    for entry in os.listdir(evaluator_dir):
        full = os.path.join(evaluator_dir, entry)
        if not os.path.isfile(full):
            continue
        if not (entry.endswith(".py") or entry.endswith(".sh")):
            continue
        # ASCII basename check (encode raises UnicodeEncodeError on non-ASCII).
        try:
            entry.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError(
                "non-ASCII basename not allowed: {!r}".format(entry)
            )
        names.append(entry)

    # Deterministic ASCII sort (LC_ALL=C-equivalent).
    names.sort(key=lambda s: s.encode("ascii"))

    lines = []
    for name in names:
        full = os.path.join(evaluator_dir, name)
        try:
            with open(full, "rb") as f:
                content = f.read()
        except OSError as exc:
            sys.stderr.write(
                "WARN: cannot read {!r}: {!r}; skipped\n".format(full, exc)
            )
            continue
        h = hashlib.sha256(content).hexdigest()  # lowercase hex
        # Two-space separator matches GNU sha256sum output format.
        lines.append("{}  {}\n".format(h, name))

    return "".join(lines)


def main():
    if len(sys.argv) > 2:
        sys.stderr.write(
            "Usage: python3 compute_evaluator_hash.py [<evaluator_dir>]\n"
        )
        sys.exit(2)
    if len(sys.argv) == 2:
        eval_dir = sys.argv[1]
    else:
        eval_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        out = compute_evaluator_hash(eval_dir)
    except FileNotFoundError as exc:
        sys.stderr.write("ERROR: {}\n".format(exc))
        sys.exit(1)
    except ValueError as exc:
        sys.stderr.write("ERROR: {}\n".format(exc))
        sys.exit(1)
    sys.stdout.write(out)
    sys.exit(0)


if __name__ == "__main__":
    main()
