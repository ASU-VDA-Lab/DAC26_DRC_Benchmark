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
# scripts/build_trusted_bin.sh
#
# One-time / on-Dockerfile-change setup: extract trusted critical binaries
# (bash / python3 / sha256sum) from the hardened detection / repair docker
# images and place them under evaluator/trusted_bin/.
#
# Score phase
# docker cp these binaries into the container as
#   /usr/local/bin/{bash,python3,sha256sum}-trusted
# so that score-phase docker exec no longer relies on the (potentially
# tampered) on-disk copies that agent phase root could have rewritten.
#
# Idempotency: re-running this script overwrites the previous binaries with
# bit-identical bytes when the source image is unchanged, so .hash stays
# stable across runs.
#
# Reference: project planning notes (see git history).

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve image tags. Defaults match evaluate_*.sh ${DETECTION_IMAGE:-...} /
# ${REPAIR_IMAGE:-...}; CI / dev can override via env.
# ---------------------------------------------------------------------------
IMAGE_DETECTION="${DETECTION_IMAGE:-drc-benchmark-detection:hardened}"
IMAGE_REPAIR="${REPAIR_IMAGE:-drc-benchmark-repair:hardened}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${REPO_ROOT}/evaluator/trusted_bin"

mkdir -p "${OUT_DIR}"

# ---------------------------------------------------------------------------
# Helper: extract a single set of binaries from one image.
#   $1 = image tag
#   $2 = output directory
# bash / python3 / sha256sum should be bit-identical between detection &
# repair images (same base image). We extract from detection by default and
# expose a second pass to verify equality.
# ---------------------------------------------------------------------------
extract_from_image() {
  local image="$1"
  local out_dir="$2"
  local cid

  echo "[build_trusted_bin] creating throwaway container from ${image}"
  cid="$(docker create "${image}")"
  # shellcheck disable=SC2064
  trap "docker rm -f '${cid}' >/dev/null 2>&1 || true" RETURN

  # Use -L to follow symlinks: /usr/bin/python3 in AlmaLinux 8 is a symlink
  # chain /usr/bin/python3 -> /etc/alternatives/python3 ->
  # /usr/libexec/platform-python3.6. Without -L the host gets a dangling
  # symlink and chmod fails. /usr/bin/sha256sum is a tiny coreutils-prog-shebang
  # wrapper script that is intentionally copied as-is (it dispatches to
  # /usr/bin/coreutils, which is present in the score-phase container too).

  echo "[build_trusted_bin] copying /bin/bash"
  docker cp -L "${cid}:/bin/bash"          "${out_dir}/bash"

  echo "[build_trusted_bin] copying /usr/bin/python3"
  docker cp -L "${cid}:/usr/bin/python3"   "${out_dir}/python3"

  echo "[build_trusted_bin] copying /usr/bin/sha256sum"
  docker cp -L "${cid}:/usr/bin/sha256sum" "${out_dir}/sha256sum"

  docker rm -f "${cid}" >/dev/null 2>&1 || true
  trap - RETURN
}

# ---------------------------------------------------------------------------
# Primary extraction: detection image.
# ---------------------------------------------------------------------------
extract_from_image "${IMAGE_DETECTION}" "${OUT_DIR}"

chmod +x "${OUT_DIR}/bash" \
         "${OUT_DIR}/python3" \
         "${OUT_DIR}/sha256sum"

# ---------------------------------------------------------------------------
# Optional sanity check: also extract from repair image into a temp dir and
# compare hashes; warn if they differ. This is informational only — score
# phase docker cp uses one bundle for both image types.
# ---------------------------------------------------------------------------
if docker image inspect "${IMAGE_REPAIR}" >/dev/null 2>&1; then
  tmp_repair="$(mktemp -d)"
  # shellcheck disable=SC2064
  trap "rm -rf '${tmp_repair}'" EXIT
  extract_from_image "${IMAGE_REPAIR}" "${tmp_repair}"
  for b in bash python3 sha256sum; do
    h_det="$(sha256sum "${OUT_DIR}/${b}" | awk '{print $1}')"
    h_rep="$(sha256sum "${tmp_repair}/${b}" | awk '{print $1}')"
    if [[ "${h_det}" != "${h_rep}" ]]; then
      echo "[build_trusted_bin] WARNING: ${b} differs between detection (${h_det}) and repair (${h_rep}) images" >&2
    fi
  done
else
  echo "[build_trusted_bin] note: ${IMAGE_REPAIR} not present locally; skipping cross-image hash check" >&2
fi

# ---------------------------------------------------------------------------
# Record sha256 manifest (used by smoke test 12 + CI).
# ---------------------------------------------------------------------------
(
  cd "${OUT_DIR}"
  sha256sum bash python3 sha256sum > .hash
)

echo "[build_trusted_bin] populated ${OUT_DIR}:"
ls -l "${OUT_DIR}"
echo "[build_trusted_bin] manifest:"
cat "${OUT_DIR}/.hash"
