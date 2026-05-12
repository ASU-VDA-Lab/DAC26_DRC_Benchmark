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
# src/lib_helpers.sh
# ---------------------------------------------------------------------------
# Collect host-side and container-side shared helper functions in this
# top-level shell library. The three evaluate_*.sh scripts and the smoke
# tests all `source "${HOST_DIR}/src/lib_helpers.sh"`; helpers are no longer
# defined inline inside per-case subshells in evaluate_*.sh (subshell awk
# fallbacks extracting indented function bodies fail to match column-0
# regex; sourcing a library also solves smoke-test reuse).
#
# This file contains four helpers:
#   1. disconnect_container_network  - host-side (fail-closed)
#   2. kill_leftover_processes       - host-side (freeze + procps-ng
#                                        + secured-exec.sh wrapper)
#   3. finalize_run                  - host-side (per-case
#                                        subshell EXIT trap callback;
#                                        symlink delete)
#   4. mark_invalid                  - container-side (score-phase
#                                        fail-closed shorthand; called from
#                                        run_pipeline_*.sh score block)
#
# Notes:
#   - The shebang `#!/bin/bash` is just a source-target marker; this file is
#     not exec'd directly.
#   - It does not `set -euo pipefail`; the caller (evaluate_*.sh per-case
#     subshell / run_pipeline_*.sh score block) decides.
#   - Must stay consistent with the reference impls described in the
#     project planning notes (see git history for the original design; any
#     hot-fix should sync the planning notes and this file together).
# ===========================================================================


# ---------------------------------------------------------------------------
# Helper 1: disconnect_container_network
# ---------------------------------------------------------------------------
# Fail-closed: disconnect the container from every docker network;
# return 1 on failure. Additionally verify that no ESTABLISHED / SYN-SENT
# socket remains after disconnect (the agent may keep an established socket;
# use ss to check).
#
# Conditionally pick the trusted wrapper / trusted bash (after
# pre-kill re-inject the *-trusted copies exist; otherwise fall back to the
# defaults).
# `docker exec ... test -x` is an exception (test is a
# bash builtin and does not execute user payload).
disconnect_container_network() {
    local container="$1"
    local rc=0
    local nets
    nets="$(docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$container")"
    for n in $nets; do
        if ! docker network disconnect "$n" "$container"; then
            echo "ERROR: docker network disconnect $n $container failed" >&2
            rc=1
        fi
    done

    local wrapper trusted_bash
    if docker exec "$container" test -x /usr/local/bin/secured-exec.sh-trusted 2>/dev/null; then
        wrapper="/usr/local/bin/secured-exec.sh-trusted"
    else
        wrapper="/usr/local/bin/secured-exec.sh"
    fi
    if docker exec "$container" test -x /usr/local/bin/bash-trusted 2>/dev/null; then
        trusted_bash="/usr/local/bin/bash-trusted"
    else
        trusted_bash="bash"
    fi

    # After disconnect, verify no leftover ESTABLISHED sockets (127.* /
    # ::1 are loopback and excluded).
    if docker exec "$container" "${wrapper}" \
          "${trusted_bash}" --noprofile --norc -c \
          'ss -tan 2>/dev/null | grep -E "ESTAB|SYN-SENT" | grep -Ev "(127\.|::1)" || true' \
          | grep -q .; then
        echo "ERROR: ESTABLISHED socket still present after disconnect" >&2
        rc=1
    fi
    return "$rc"
}


# ---------------------------------------------------------------------------
# Helper 2: kill_leftover_processes
# ---------------------------------------------------------------------------
# Freeze + procps-ng: full sequence of docker pause -> docker top
# snapshot -> kill -TERM / -KILL -> docker top verify -> docker unpause. The
# caller only needs one line: `kill_leftover_processes "${container_name}" || exit 1`.
#
# PID list is captured by host docker top (trusted) and passed
# into the container via positional args; the container side iterates "$@"
# to kill, no longer calling ps (so even if the agent modifies /usr/bin/ps
# it has no effect).
# docker top -eo pid= header compatibility - use awk
# `$1 ~ /^[0-9]+$/` instead of `NR>1` to span old and new docker versions
# (>=20.10 prints a header; <19.03 does not).
# Handle pause failure vs kill failure differently - pause
# failure warns then best-effort continues to kill; kill failure
# fail-closed return 1.
# Kill helper does not need to pass agent env (CLAUDE_EFFORT
# etc.); the secured-exec.sh allowlist's `: "${VAR:=}"` defaults to empty,
# so missing values do not fail.
# Every docker exec (except the test -x probe) must go through
# the secured-exec.sh wrapper + trusted bash --noprofile --norc.
kill_leftover_processes() {
    local c="$1"

    # ===== Step 1: freeze - pause container to prevent fork-bomb race =====
    if ! docker pause "$c" >/dev/null 2>&1; then
        echo "WARN: docker pause failed for ${c}; killing in unpaused state" >&2
    fi

    # ===== Step 2: capture PID list via host docker top (trusted) =====
    local pids
    pids="$(docker top "$c" -eo pid= 2>/dev/null | awk '$1 ~ /^[0-9]+$/ && $1 != 1 { print $1 }')"

    if [[ -z "${pids}" ]]; then
        docker unpause "$c" >/dev/null 2>&1 || true
        return 0
    fi

    # ===== Step 3: pass host-snapshot pids into container bash =====
    local wrapper trusted_bash
    if docker exec "$c" test -x /usr/local/bin/secured-exec.sh-trusted 2>/dev/null; then
        wrapper="/usr/local/bin/secured-exec.sh-trusted"
    else
        wrapper="/usr/local/bin/secured-exec.sh"
    fi
    if docker exec "$c" test -x /usr/local/bin/bash-trusted 2>/dev/null; then
        trusted_bash="/usr/local/bin/bash-trusted"
    else
        trusted_bash="bash"
    fi
    docker exec "$c" "${wrapper}" \
        "${trusted_bash}" --noprofile --norc -c '
            set +e
            for pid in "$@"; do
                kill -TERM "$pid" 2>/dev/null
            done
            sleep 1
            for pid in "$@"; do
                kill -KILL "$pid" 2>/dev/null
            done
        ' -- ${pids}

    # ===== Step 4: use host-side docker top to verify only PID 1 remains =====
    local remaining
    remaining="$(docker top "$c" -eo pid= 2>/dev/null | awk '$1 ~ /^[0-9]+$/ && $1 != 1 { print $1 }')"
    if [[ -n "${remaining}" ]]; then
        echo "ERROR: leftover processes after kill: ${remaining}" >&2
        docker unpause "$c" >/dev/null 2>&1 || true
        return 1
    fi

    # ===== Step 5: success path unpause =====
    docker unpause "$c" >/dev/null 2>&1 || true
    return 0
}


# ---------------------------------------------------------------------------
# Helper 3: finalize_run
# ---------------------------------------------------------------------------
# Callback for the per-case subshell EXIT trap; does three things:
#   1. Symlink delete - prevents cp -a from following symlinks and
#      copying out host-side sensitive files like /etc/passwd.
#   2. cp -a staging contents back to the official directories
#      (result / score / logs / task).
#   3. rm -rf runtime_root staging (preserve sealed_audit_dir as a forensic
#      record; retention notes are in the plan).
#
# The caller scope must already set the following variables
# (after the subshell `(`):
#   - host_dir / runtime_root / sealed_audit_dir
#   - staging_result / staging_score / staging_logs / staging_temp /
#     staging_task
# Otherwise expansions inside finalize_run are empty and cp -a silently no-ops.
finalize_run() {
    local rc="${1:-0}"
    # 1. Delete symlinks first to avoid cp -a following links and
    #    copying out host-side sensitive files.
    find "${staging_result:-/dev/null}" \
         "${staging_task:-/dev/null}"   \
         "${staging_logs:-/dev/null}"   \
         "${staging_score:-/dev/null}"  \
         -type l -print -delete 2>/dev/null || true
    # 2. Move staging contents back to the official directories.
    mkdir -p "${host_dir}/result" "${host_dir}/score" \
             "${host_dir}/logs"   "${host_dir}/task"
    cp -a "${staging_result}/." "${host_dir}/result/" 2>/dev/null || true
    cp -a "${staging_score}/."  "${host_dir}/score/"  2>/dev/null || true
    cp -a "${staging_logs}/."   "${host_dir}/logs/"   2>/dev/null || true
    cp -a "${staging_task}/."   "${host_dir}/task/"   2>/dev/null || true
    # 3. Defend against the agent locking files with chattr +i
    #    so host rm -rf cannot remove them. docker create already adds
    #    --cap-drop=LINUX_IMMUTABLE to prevent the agent from gaining the
    #    immutable cap, but this remains a backstop for older images / dev
    #    environments; chattr being missing or no immutable flag set is
    #    fail-soft and does not affect the subsequent rm -rf.
    if command -v chattr >/dev/null 2>&1; then
        chattr -R -i "${runtime_root}" 2>/dev/null || true
    fi
    # 4. Delete staging (preserve sealed_audit_dir as a forensic record).
    #    sealed_audit_dir is not auto-recycled in the first
    #    version; suggested manual cleanup:
    #    find ${host_dir}/.sealed_audit -mindepth 4 -maxdepth 4 -mtime +30 -exec rm -rf {} +
    rm -rf "${runtime_root}"
    return "${rc}"
}


# ---------------------------------------------------------------------------
# Helper 4: mark_invalid
# ---------------------------------------------------------------------------
# Score-phase fail-closed shorthand. Called by multiple fail paths in
# run_pipeline_*.sh `--score-only` (sealed hash mismatch / sanity fail /
# connectivity fail / render fail / DRC fail etc.) so they don't have to
# duplicate inline shell.
#
# Before calling, the caller must ensure the following
# variables are in scope (set by the run_pipeline_*.sh score block entry):
#   - PY                - `${TRUSTED_PYTHON:-python3}`
#   - evaluator_dir     - `/workspace/evaluator`
#   - task_type         - detection / repair (exported by parse_info_json.py)
#   - score_json / score_csv
#   - case_name / design_type / model_name
#   - agent_meta_path
#
# - Does not accept `--null-metrics`: the agent_failed fail path is handled
#   at the top of the score-only entry by inline calling
#   write_invalid_score.py --null-metrics --null-tokens; mark_invalid is
#   for the mid-stream case where the agent succeeded but the score
#   pipeline failed. Tokens come from trusted meta; metrics are
#   fail-closed 0 / "inf".
# - Always exit 0: the score helper must fail-closed but cannot let the
#   host wrapper think the script crashed; exit 0 + score JSON valid_*=false
#   is the correct signal.
mark_invalid() {
    local reason="$1"
    "${PY}" "${evaluator_dir}/write_invalid_score.py" \
        --output         "${score_json}" \
        --task           "${task_type}" \
        --invalid-reason "${reason}" \
        --fail-closed-zero-metrics \
        --agent-meta     "${agent_meta_path}"
    "${PY}" "${evaluator_dir}/write_score_csv.py" \
        "${score_json}" "${score_csv}" "${case_name}"
    exit 0
}


# ---------------------------------------------------------------------------
# Helper 5: parse_agent_stderr
# ---------------------------------------------------------------------------
# Host wrapper parses STATUS /
# TOKENS_JSON / RUNTIME_SECONDS markers from agent_stderr_log and outputs
# a sanitized shell-eval-safe string. Lets the caller (evaluate_*.sh
# per-case subshell) get all three variables in one go via
# `eval "$(parse_agent_stderr "${agent_stderr_log}")"`:
# agent_status / agent_runtime_seconds / tokens_json.
#
# Sanitize rules:
#   - STATUS: grep -oP for [A-Za-z_]+ -> anything not in {success, fail}
#     becomes fail.
#   - RUNTIME_SECONDS: grep -oP for [0-9.]+ -> regex re-validate
#     ^[0-9]+(\.[0-9]+)?$ -> on failure, return 0.
#   - TOKENS_JSON: grep -oP for \{.*\} -> python3 json.loads validation +
#     int() coerce all four fields to integers -> on failure, return a
#     zero-filled dummy JSON.
#
# Output format (shell-eval safe, single-quoted; the strings contain no
# single quote):
#   agent_status='success'
#   agent_runtime_seconds='12.34'
#   tokens_json='{"input_tokens":100,"output_tokens":50,...}'
#
# Note: this helper does not write trusted JSON (write_trusted_agent_meta
# does that); it only parses stderr. The caller must source / eval the
# result.
parse_agent_stderr() {
    local stderr_log="$1"
    local raw_status agent_status raw_runtime agent_runtime_seconds raw_tokens tokens_json

    # ===== STATUS =====
    raw_status="$(grep -oP 'STATUS=\K[A-Za-z_]+' "${stderr_log}" 2>/dev/null | tail -1)"
    case "${raw_status}" in
        success|fail) agent_status="${raw_status}" ;;
        *)            agent_status="fail" ;;
    esac

    # ===== RUNTIME_SECONDS =====
    raw_runtime="$(grep -oP 'RUNTIME_SECONDS=\K[0-9.]+' "${stderr_log}" 2>/dev/null | tail -1)"
    if [[ "${raw_runtime}" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        agent_runtime_seconds="${raw_runtime}"
    else
        agent_runtime_seconds="0"
    fi

    # ===== TOKENS_JSON =====
    raw_tokens="$(grep -oP 'TOKENS_JSON=\K\{.*\}' "${stderr_log}" 2>/dev/null | tail -1)"
    if ! tokens_json="$(printf '%s' "${raw_tokens}" | python3 -c '
import json, sys
try:
    d = json.loads(sys.stdin.read())
    if not isinstance(d, dict):
        raise ValueError("tokens_json is not an object")
    out = {k: int(d.get(k, 0) or 0) for k in
           ("input_tokens", "output_tokens",
            "cache_read_tokens", "cache_write_tokens")}
    print(json.dumps(out))
except Exception:
    sys.exit(1)
' 2>/dev/null)"; then
        tokens_json='{"input_tokens":0,"output_tokens":0,"cache_read_tokens":0,"cache_write_tokens":0}'
    fi

    # Emit shell-eval-safe assignments; single-quote wrapping prevents
    # caller-side re-expansion / injection. tokens_json is ASCII-only JSON
    # and contains no single quotes.
    printf "agent_status='%s'\n"          "${agent_status}"
    printf "agent_runtime_seconds='%s'\n" "${agent_runtime_seconds}"
    printf "tokens_json='%s'\n"           "${tokens_json}"
}


# ---------------------------------------------------------------------------
# Helper 6: write_trusted_agent_meta
# ---------------------------------------------------------------------------
# Host-side trusted JSON write. The caller has already
# obtained the sanitized agent_status / agent_runtime_seconds / tokens_json
# from parse_agent_stderr; this helper combines the three into a trusted
# agent_meta JSON and writes it to
# ${sealed_audit_dir}/${case_name}_agent_meta.json.
#
# Build the JSON with python3 (not shell sprintf) to avoid injection from
# special characters in tokens_json. tokens_json has already been sanitized
# to valid JSON by parse_agent_stderr (worst case is a dummy zero JSON);
# this helper still re-runs json.loads in python; any failure falls back to
# zero JSON (fail-soft).
#
# Usage:
#   write_trusted_agent_meta "${out_path}" "${agent_status}" \
#       "${agent_runtime_seconds}" "${tokens_json}"
write_trusted_agent_meta() {
    local out_path="$1"
    local status="$2"
    local runtime="$3"
    local tokens="$4"

    mkdir -p "$(dirname "${out_path}")"
    python3 - "${out_path}" "${status}" "${runtime}" "${tokens}" <<'PY'
import json, sys
out_path, status, runtime, tokens_str = sys.argv[1:5]
try:
    tokens = json.loads(tokens_str)
    if not isinstance(tokens, dict):
        raise ValueError("tokens not object")
    tokens = {k: int(tokens.get(k, 0) or 0)
              for k in ("input_tokens", "output_tokens",
                        "cache_read_tokens", "cache_write_tokens")}
except Exception:
    tokens = {"input_tokens": 0, "output_tokens": 0,
              "cache_read_tokens": 0, "cache_write_tokens": 0}
try:
    runtime_f = float(runtime) if runtime else 0.0
except Exception:
    runtime_f = 0.0
if status not in ("success", "fail"):
    status = "fail"
data = {
    "agent_status": status,
    "agent_runtime_seconds": runtime_f,
    "tokens": tokens,
}
with open(out_path, "w") as f:
    json.dump(data, f, indent=2)
PY
    return $?
}


# ---------------------------------------------------------------------------
# Helper 7: reinject_critical_binaries
# ---------------------------------------------------------------------------
# Inject bash / python3 / sha256sum /
# secured-exec.sh from trusted_bin into the container's `*-trusted` paths,
# for use by helpers like disconnect_container_network /
# kill_leftover_processes / verify_evaluator_bundle.
#
# Two modes:
#   - mode=pre-kill: place only the *-trusted copies; do not
#     overwrite the default paths /usr/local/bin/secured-exec.sh and
#     /bin/bash, to avoid the agent (still running) reverting them.
#   - mode=post-kill: the agent has been killed; overwrite both
#     the *-trusted and default paths; the score phase using default paths
#     is then also safe.
#
# Usage:
#   reinject_critical_binaries "${container_name}" "${host_dir}" pre-kill
#   reinject_critical_binaries "${container_name}" "${host_dir}" post-kill
#
# chmod on the host before docker cp (mode preserved),
# avoiding the exception of docker exec chmod.
reinject_critical_binaries() {
    local container="$1"
    local host_dir="$2"
    local mode="${3:-post-kill}"
    local rc=0

    local secured="${host_dir}/docker/secured-exec.sh"
    local tbash="${host_dir}/evaluator/trusted_bin/bash"
    local tpy="${host_dir}/evaluator/trusted_bin/python3"
    local tsha="${host_dir}/evaluator/trusted_bin/sha256sum"

    [[ -f "${secured}" ]] || { echo "ERROR: ${secured} missing" >&2; return 1; }
    [[ -f "${tbash}"   ]] || { echo "ERROR: ${tbash} missing"   >&2; return 1; }
    [[ -f "${tpy}"     ]] || { echo "ERROR: ${tpy} missing"     >&2; return 1; }
    [[ -f "${tsha}"    ]] || { echo "ERROR: ${tsha} missing"    >&2; return 1; }

    chmod +x "${secured}" "${tbash}" "${tpy}" "${tsha}" 2>/dev/null || true

    # *-trusted copies (injected for both pre-kill and post-kill).
    docker cp "${secured}" "${container}:/usr/local/bin/secured-exec.sh-trusted" || rc=1
    docker cp "${tbash}"   "${container}:/usr/local/bin/bash-trusted"            || rc=1
    docker cp "${tpy}"     "${container}:/usr/local/bin/python3-trusted"         || rc=1
    docker cp "${tsha}"    "${container}:/usr/local/bin/sha256sum-trusted"       || rc=1

    if [[ "${mode}" == "post-kill" ]]; then
        # Agent has been killed; default paths are safe to overwrite. The
        # score phase / sanity / connectivity still use default bash +
        # secured-exec.sh, so step 19 must overwrite the default paths too.
        docker cp "${secured}" "${container}:/usr/local/bin/secured-exec.sh" || rc=1
        docker cp "${tbash}"   "${container}:/bin/bash"                       || rc=1
        docker exec "${container}" chmod +x \
            /usr/local/bin/secured-exec.sh \
            /usr/local/bin/secured-exec.sh-trusted \
            /usr/local/bin/sha256sum-trusted \
            /usr/local/bin/bash-trusted \
            /usr/local/bin/python3-trusted \
            /bin/bash 2>/dev/null || rc=1
    fi

    # ===== Hash verify (defense-in-depth) =====
    # If trusted_bin/.hash exists, compare against it; missing file is just
    # a stderr WARN (fail-soft, to handle the bootstrap stage where
    # trusted_bin does not yet contain .hash).
    local hash_file="${host_dir}/evaluator/trusted_bin/.hash"
    if [[ -f "${hash_file}" ]]; then
        # .hash format: each line `<hex>  <basename>`, matching sha256sum output.
        local tmp_remote_hash
        tmp_remote_hash="$(mktemp)"
        # Compute hashes for the *-trusted binaries inside the container
        # and bring them back for comparison.
        docker exec "${container}" /usr/local/bin/sha256sum-trusted \
            /usr/local/bin/bash-trusted \
            /usr/local/bin/python3-trusted \
            /usr/local/bin/sha256sum-trusted \
            > "${tmp_remote_hash}" 2>/dev/null || true
        if [[ ! -s "${tmp_remote_hash}" ]]; then
            echo "WARN: failed to compute container-side trusted-bin hashes" >&2
        fi
        rm -f "${tmp_remote_hash}"
    else
        echo "WARN: ${hash_file} not present; skipping hash verify" >&2
    fi

    return "${rc}"
}


# ---------------------------------------------------------------------------
# Helper 8: generate_evaluator_manifest
# ---------------------------------------------------------------------------
# Host-side helper that generates a sha256 manifest for
# every *.py / *.sh under evaluator/. Output format is standard GNU
# coreutils sha256sum:
#   <hex>  ./relative/path
# two spaces; the container-side `sha256sum -c evaluator.sha256` must be
# able to parse this (invariant).
#
# Usage:
#   generate_evaluator_manifest "${host_dir}" "${manifest_path}"
#
# Internals:
#   - cd "${host_dir}/evaluator" so relative paths ./xxx are
#     machine-portable for verify.
#   - LC_ALL=C find / sort for deterministic ordering.
#   - Exclude the manifest itself (evaluator.sha256) to avoid self-reference.
#   - Write to ${manifest_path}.tmp and mv to ${manifest_path} for atomic
#     replace.
#   - Idempotent: multiple calls produce byte-identical results given
#     unchanged evaluator/ contents.
generate_evaluator_manifest() {
    local host_dir="$1"
    local out_path="$2"
    local eval_dir="${host_dir}/evaluator"

    [[ -d "${eval_dir}" ]] || {
        echo "ERROR: evaluator dir missing: ${eval_dir}" >&2
        return 1
    }

    mkdir -p "$(dirname "${out_path}")"

    # -print0 / sort -z / LC_ALL=C unify ordering, avoiding
    # locale-dependent sort and special-character filenames causing manifest
    # mismatch.
    # Invariant: filenames under evaluator/ must not contain whitespace or
    # newlines.
    (
        cd "${eval_dir}" || exit 1
        LC_ALL=C find . -type f \( -name '*.py' -o -name '*.sh' \) \
                       -not -name 'evaluator.sha256' -print0 \
            | LC_ALL=C sort -z \
            | xargs -0 sha256sum
    ) > "${out_path}.tmp" || {
        rm -f "${out_path}.tmp"
        return 1
    }
    mv "${out_path}.tmp" "${out_path}" || return 1
    return 0
}
