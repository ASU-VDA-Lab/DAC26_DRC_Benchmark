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
#################################################################################
# scripts/build_seccomp_profile.sh
#
# takes docker's official v24.0.7 default seccomp
# profile as base, merges docker/seccomp-extra-rules.json on the host using
# jq, and produces docker/seccomp-no-iptables.json.
#
# When this must be run:
#   1. After first clone of the repo (together with scripts/build_trusted_bin.sh).
#   2. After docker/seccomp-extra-rules.json changes.
#   3. After docker/seccomp-default.json is upgraded (tracking new docker
#      default profile semantics).
#
# Dependencies: jq, sha256sum.
#   dnf install -y jq    # RHEL/Rocky/AlmaLinux
#   apt install -y jq    # Debian/Ubuntu
#
# Source for docker/seccomp-default.json (one-time setup):
#   curl -fsSL -o docker/seccomp-default.json \
#       https://raw.githubusercontent.com/moby/moby/v24.0.7/profiles/seccomp/default.json
#   sha256sum docker/seccomp-default.json > docker/seccomp-default.json.sha256
# Reason for pinning v24.0.7: moby main branch keeps patching the syscall
# list; pinning the tag keeps the plan's syscall set consistent with the base
# profile. Upgrading requires a separate review round to sync extra rules.
#
# If docker/seccomp-default.json is missing, this script fails and prompts to
# download it first.

set -euo pipefail

cd "$(dirname "$0")/.."

DEFAULT_JSON="docker/seccomp-default.json"
EXTRA_JSON="docker/seccomp-extra-rules.json"
OUT_JSON="docker/seccomp-no-iptables.json"
DEFAULT_SHA="docker/seccomp-default.json.sha256"

if [[ ! -f "${DEFAULT_JSON}" ]]; then
    echo "[seccomp] ERROR: ${DEFAULT_JSON} not found." >&2
    echo "[seccomp] One-time setup:" >&2
    echo "    curl -fsSL -o ${DEFAULT_JSON} \\" >&2
    echo "        https://raw.githubusercontent.com/moby/moby/v24.0.7/profiles/seccomp/default.json" >&2
    echo "    sha256sum ${DEFAULT_JSON} > ${DEFAULT_SHA}" >&2
    exit 1
fi

if [[ ! -f "${EXTRA_JSON}" ]]; then
    echo "[seccomp] ERROR: ${EXTRA_JSON} not found." >&2
    exit 1
fi

# If the default sha file exists, verify the base profile has not been swapped.
if [[ -f "${DEFAULT_SHA}" ]]; then
    if ! sha256sum -c "${DEFAULT_SHA}" >/dev/null 2>&1; then
        echo "[seccomp] FATAL: ${DEFAULT_JSON} sha256 mismatch." >&2
        echo "[seccomp]        Re-download from moby v24.0.7 or update ${DEFAULT_SHA}." >&2
        exit 1
    fi
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "[seccomp] ERROR: jq not installed." >&2
    echo "[seccomp]   dnf install -y jq    # RHEL/Rocky/AlmaLinux" >&2
    echo "[seccomp]   apt install -y jq    # Debian/Ubuntu" >&2
    exit 1
fi

# Merge: take default as base and append extra's syscall rules into the
# syscalls array. defaultAction is preserved as the base profile's
# SCMP_ACT_ERRNO; extra rules also use SCMP_ACT_ERRNO (must not be overridden
# to SCMP_ACT_ALLOW or the attack surface grows).
jq -s '.[0] * {syscalls: (.[0].syscalls + .[1].extra)}' \
    "${DEFAULT_JSON}" "${EXTRA_JSON}" \
    > "${OUT_JSON}"

# Sanity check: the output JSON must be a valid seccomp profile (defaultAction
# + non-empty syscalls array).
python3 -c "
import json, sys
prof = json.load(open('${OUT_JSON}'))
assert prof.get('defaultAction'), 'missing defaultAction'
assert isinstance(prof.get('syscalls'), list) and prof['syscalls'], 'syscalls empty'
"

echo "[seccomp] generated ${OUT_JSON}"
