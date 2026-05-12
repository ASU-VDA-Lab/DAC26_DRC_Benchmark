#!/bin/bash
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
# ===========================================================================
# evaluator/verify_evaluator_bundle.sh
# ---------------------------------------------------------------------------
# in-container score-phase entry verification of the
# evaluator bundle.
#
# This script runs **inside the container** and is invoked at the top of
# the score-only block in run_pipeline_*.sh; it verifies two things about
# the *.py / *.sh under `${EVALUATOR_DIR:-/workspace/evaluator}` against the
# manifest (evaluator.sha256):
#   1. file-set diff: the filename set listed in the manifest ==
#      the actual *.py / *.sh set under evaluator/. Both extra and missing
#      files cause fail.
#   2. sha256sum -c: each file's hash matches the manifest.
#
# Behavior:
#   - HARDENED_EVALUATION=1: fail-closed; any verification failure -> exit 1.
#     Uses the trusted binary /usr/local/bin/sha256sum-trusted (docker cp'd
#     in by host; standard GNU coreutils output format).
#   - Otherwise legacy mode: missing manifest is just a stderr WARN exit 0;
#     if present, verify with the default `sha256sum -c`.
#
# Invariant: sha256sum output format is consistent across
# binaries - two-space separator. The host-side generate_evaluator_manifest
# must emit standard GNU format; otherwise `-c` silently skips every line ->
# false-positive.
#
# No dependency on lib_helpers.sh: this script runs inside the container,
# whose fs has no host-side src/ tree (only the docker-cp'd evaluator/).
# ===========================================================================

set -u

evaluator_dir="${EVALUATOR_DIR:-/workspace/evaluator}"
manifest="${evaluator_dir}/evaluator.sha256"

if [[ "${HARDENED_EVALUATION:-0}" == "1" ]]; then
    if [[ ! -f "${manifest}" ]]; then
        echo "ERROR: hardened mode but evaluator manifest missing: ${manifest}" >&2
        exit 1
    fi

    # File-set diff (do this first; confirm filename set matches before
    # hash check).
    # M4: $2 truncates paths with whitespace; use the "drop $1 (hash) and
    # print the rest" awk pattern to extract the path field.
    expected="$(awk '{ $1=""; sub(/^ +/,""); print }' "${manifest}" | LC_ALL=C sort)"
    actual="$( (cd "${evaluator_dir}" && LC_ALL=C find . -type f \
                  \( -name '*.py' -o -name '*.sh' \) \
                  -not -name 'evaluator.sha256') | LC_ALL=C sort )"
    if [[ "${expected}" != "${actual}" ]]; then
        echo "ERROR: evaluator file set diverges from manifest" >&2
        diff <(echo "${expected}") <(echo "${actual}") >&2 || true
        exit 1
    fi

    # sha256sum -c (trusted binary)
    if ! ( cd "${evaluator_dir}" && \
           /usr/local/bin/sha256sum-trusted -c evaluator.sha256 ); then
        echo "ERROR: evaluator manifest hash verify failed" >&2
        exit 1
    fi
else
    # legacy / non-hardened mode
    if [[ ! -f "${manifest}" ]]; then
        echo "WARNING: evaluator manifest not found (legacy mode): ${manifest}" >&2
        exit 0
    fi
    if ! ( cd "${evaluator_dir}" && sha256sum -c evaluator.sha256 ); then
        echo "ERROR: evaluator manifest hash verify failed (legacy mode)" >&2
        exit 1
    fi
fi

exit 0
