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
# src/lib_helpers.sh — shared host/container helpers. Sourced by
# evaluate_*.sh and smoke tests. Not directly executed; no `set -e`.
# ===========================================================================


# disconnect_container_network: fail-closed; verify no ESTABLISHED socket after disconnect.
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

    if docker exec "$container" "${wrapper}" \
          "${trusted_bash}" --noprofile --norc -c \
          'ss -tan 2>/dev/null | grep -E "ESTAB|SYN-SENT" | grep -Ev "(127\.|::1)" || true' \
          | grep -q .; then
        echo "ERROR: ESTABLISHED socket still present after disconnect" >&2
        rc=1
    fi
    return "$rc"
}


# kill_leftover_processes: pause -> host docker top snapshot -> TERM/KILL -> verify -> unpause. PID list is host-trusted; agent ps tampering has no effect.
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


# finalize_run: per-case EXIT trap. Deletes symlinks, cp -a staging -> official dirs, rm -rf runtime_root (sealed_audit_dir kept).
finalize_run() {
    local rc="${1:-0}"
    # 1. Delete symlinks first to avoid cp -a following links and
    #    copying out host-side sensitive files.
    find "${staging_result:-/dev/null}" \
         "${staging_task:-/dev/null}"   \
         "${staging_logs:-/dev/null}"   \
         "${staging_score:-/dev/null}"  \
         -type l -print -delete 2>/dev/null || true
    mkdir -p "${host_dir}/result" "${host_dir}/score" \
             "${host_dir}/logs"   "${host_dir}/task"
    cp -a "${staging_result}/." "${host_dir}/result/" 2>/dev/null || true
    cp -a "${staging_score}/."  "${host_dir}/score/"  2>/dev/null || true
    cp -a "${staging_logs}/."   "${host_dir}/logs/"   2>/dev/null || true
    cp -a "${staging_task}/."   "${host_dir}/task/"   2>/dev/null || true
    # Backstop: drop +i if any file got immutable; cap-drop=LINUX_IMMUTABLE is the primary defense.
    if command -v chattr >/dev/null 2>&1; then
        chattr -R -i "${runtime_root}" 2>/dev/null || true
    fi
    # rm runtime_root; sealed_audit_dir is forensic (manual cleanup elsewhere).
    rm -rf "${runtime_root}"
    return "${rc}"
}


# mark_invalid: score-phase fail-closed; relies on vars set by caller (PY, evaluator_dir, task_type, score_json, score_csv, case_name, design_type, model_name, agent_meta_path). Always exit 0 with valid_*=false.
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


# parse_agent_stderr: emit shell-eval-safe assignments for agent_status / agent_runtime_seconds / tokens_json. Output is single-quoted; tokens_json is ASCII JSON with no quote chars.
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

    printf "agent_status='%s'\n"          "${agent_status}"
    printf "agent_runtime_seconds='%s'\n" "${agent_runtime_seconds}"
    printf "tokens_json='%s'\n"           "${tokens_json}"
}


# write_trusted_agent_meta: combine sanitized status/runtime/tokens into trusted JSON. Fail-soft on tokens_str parse: substitutes zero JSON.
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
# aggregate_call_tokens_for_case
# ---------------------------------------------------------------------------
# Wrapper around evaluator/aggregate_call_tokens.py. Echoes:
#     <tokens_json>|<num_calls>|<source>
# Reads the aggregator's --output FILE (never eval stdout).
# Appends marker-vs-per-call delta WARN to <report_path> when source==per_call_files
# and any delta is nonzero. cp -aP of the per-call files is the CALLER's job.
# Fail-soft: any error -> <fallback_tokens_json>|1|fallback_tokens. Always returns 0.
#
# Args (6):
#   1. calls_dir        - ${score_dir}/calls (flat, shared across cases)
#   2. case_name        - case name; aggregator scopes by ${case_name}_*.json
#   3. out_path         - aggregator --output target
#   4. fallback_tokens  - marker tokens JSON (fail-soft path)
#   5. report_path      - aggregator --report target
#   6. require_flag     - "--require-files" or "" (mandatory recording)
#
# Exit-code convention with the aggregator:
#   exit 0  -> success (n_valid > 0 OR --require-files not set)
#   exit 4  -> mandatory recording required + n_valid == 0 (host emits
#              fail-closed null score; the source field in the triple
#              becomes "mandatory_calls_recording_missing").
#   other   -> aggregator crash; helper falls through to marker_fallback.
aggregate_call_tokens_for_case() {
    local calls_dir="$1"
    local case_name="$2"
    local out_path="$3"
    local fallback_tokens="$4"
    local report_path="$5"
    local require_flag="${6:-}"

    # Allow AGGREGATE_CALL_TOKENS_PY override for smoke tests.
    local agg_script="${AGGREGATE_CALL_TOKENS_PY:-${host_dir:-.}/evaluator/aggregate_call_tokens.py}"
    if [[ ! -f "${agg_script}" ]]; then
        printf '%s|1|fallback_tokens\n' "${fallback_tokens}"
        return 0
    fi

    mkdir -p "$(dirname "${out_path}")" 2>/dev/null || true
    mkdir -p "$(dirname "${report_path}")" 2>/dev/null || true

    # Stdout discarded; --output file is the canonical channel.
    local agg_rc=0
    if [[ -n "${require_flag}" ]]; then
        python3 "${agg_script}" \
            --calls-dir "${calls_dir}" \
            --case-name "${case_name}" \
            --output   "${out_path}" \
            --fallback-tokens-json "${fallback_tokens}" \
            --report   "${report_path}" \
            ${require_flag} \
            >/dev/null 2>&1 || agg_rc=$?
    else
        python3 "${agg_script}" \
            --calls-dir "${calls_dir}" \
            --case-name "${case_name}" \
            --output   "${out_path}" \
            --fallback-tokens-json "${fallback_tokens}" \
            --report   "${report_path}" \
            >/dev/null 2>&1 || agg_rc=$?
    fi

    # Mandatory recording: aggregator exit 4 => no valid per-call files
    # under --require-files. Caller must invoke write_invalid_score.py
    # with invalid_reason=mandatory_calls_recording_missing instead of
    # the normal scorer.
    if [[ "${agg_rc}" -eq 4 ]]; then
        printf '%s|0|mandatory_calls_recording_missing\n' "${fallback_tokens}"
        return 0
    fi

    # Read result via python3 -c (NEVER eval the aggregator stdout).
    local triple
    triple="$(python3 -c '
import json, sys
out_path = sys.argv[1]
fallback = sys.argv[2]
try:
    with open(out_path, "r") as f:
        data = json.load(f)
    tokens = data.get("tokens", {})
    if not isinstance(tokens, dict):
        raise ValueError("tokens not dict")
    sanitized = {k: int(tokens.get(k, 0) or 0) for k in
                 ("input_tokens", "output_tokens",
                  "cache_read_tokens", "cache_write_tokens")}
    source = data.get("source", "")
    if not isinstance(source, str):
        source = ""
    n_valid = int(data.get("n_call_ids_valid", 0) or 0)
    if source == "per_call_files" and n_valid >= 1:
        tokens_out = json.dumps(sanitized)
        # num_calls reflects valid count.
        print(f"{tokens_out}|{n_valid}|{source}")
    else:
        # Fail-soft: emit the marker fallback verbatim so byte-identical
        # agent_meta.json is guaranteed for legacy single-call agents.
        # num_calls=1 (legacy convention: one agent invocation).
        print(f"{fallback}|1|{source or 'marker_fallback'}")
except Exception:
    print(f"{fallback}|1|fallback_tokens")
' "${out_path}" "${fallback_tokens}" 2>/dev/null)" || triple=""

    if [[ -z "${triple}" ]]; then
        triple="${fallback_tokens}|1|fallback_tokens"
    fi

    # Delta WARN only when source==per_call_files (else delta is zero by construction).
    local source_field
    source_field="$(printf '%s' "${triple}" | awk -F'|' '{print $3}')"
    if [[ "${source_field}" == "per_call_files" ]]; then
        python3 -c '
import json, sys
out_path, fallback, report_path = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(out_path, "r") as f:
        data = json.load(f)
    tokens = data.get("tokens", {})
    try:
        marker = json.loads(fallback)
        if not isinstance(marker, dict):
            marker = {}
    except Exception:
        marker = {}
    keys = ("input_tokens", "output_tokens",
            "cache_read_tokens", "cache_write_tokens")
    deltas = {}
    any_nonzero = False
    for k in keys:
        try:
            a = int(tokens.get(k, 0) or 0)
        except Exception:
            a = 0
        try:
            m = int(marker.get(k, 0) or 0)
        except Exception:
            m = 0
        d = a - m
        deltas[k] = d
        if d != 0:
            any_nonzero = True
    if any_nonzero:
        parts = []
        for k in keys:
            sign = "+" if deltas[k] >= 0 else ""
            parts.append(f"{k}={sign}{deltas[k]}")
        line = "WARN: marker vs per-call delta: " + ", ".join(parts)
        try:
            with open(report_path, "a") as fr:
                fr.write(line + "\n")
        except Exception:
            pass
except Exception:
    pass
' "${out_path}" "${fallback_tokens}" "${report_path}" 2>/dev/null || true
    fi

    printf '%s\n' "${triple}"
    return 0
}


# reinject_critical_binaries: copy trusted bash/python3/sha256sum/secured-exec.sh into container *-trusted paths (pre-kill) and default paths (post-kill).
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
        # Post-kill: default paths are safe to overwrite (agent gone).
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

    return "${rc}"
}
