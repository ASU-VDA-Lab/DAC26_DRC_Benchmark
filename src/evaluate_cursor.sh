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
# evaluate_cursor.sh -- Batch experiment runner for reproducing the paper's results
#
# Iterates over model_name x case_entry (case_entry embeds design|task|case)
# and runs the full Docker-based pipeline for each combination sequentially.
#
# This script is used to reproduce the experiment table in the paper.
# To run a single case, use run_pipeline_cursor.sh with your own info.json instead.
#
# IMPORTANT: Run this script from the DAC26_DRC_Benchmarks/ project root:
#   cd DAC26_DRC_Benchmarks/
#   bash src/evaluate_cursor.sh
#
# Prerequisites:
#   - Two Docker images must be built first:
#       docker build -f Dockerfile.repair    -t drc-benchmark-repair    .
#       docker build -f Dockerfile.detection -t drc-benchmark-detection .
#     (Detection uses a locked-down image with no KLayout and an iptables
#     blocklist to prevent the agent from installing / invoking KLayout.)
#   - Cursor CLI must be logged in on the host:
#       curl https://cursor.com/install -fsS | bash
#       agent login

set -euo pipefail

# ===========================================================================
# Configuration -- edit these lists to control which runs to execute
# ===========================================================================
#
# CASES uses a 3-field pipe-separated format
#   "<design_type>|<task_type>|<case_name>"
# No more outer `for task_type in detection repair` loop.

MODEL_NAMES=(
    claude-4.6-opus-high
    claude-4.6-sonnet-medium
    gpt-5.4-high
    gemini-3.1-pro
    grok-4-20
    kimi-k2.5
)

CASES=(
    "polygon|repair|Polygon69"
    "polygon|repair|Polygon263"
    "cell|repair|Cell1"
    "cell|repair|Cell228"
    "block|repair|Block5"
    "block|repair|Block7"
    "polygon|detection|Polygon69"
    "polygon|detection|Polygon263"
    "cell|detection|Cell1"
    "cell|detection|Cell228"
    "block|detection|Block5"
    "block|detection|Block7"
)

# Parse --case <name> / --task <detection|repair> to
# restrict the CASES matrix to a single entry for debugging or single-
# case orchestration. When --case or --task is given, MODEL_NAMES is
# kept as-is; CASES is filtered. If both flags are given and no matching
# entry exists, the script exits 1 fail-closed.
FILTER_CASE=""
FILTER_TASK=""
while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --case) FILTER_CASE="$2"; shift 2 ;;
        --task) FILTER_TASK="$2"; shift 2 ;;
        *) echo "ERROR: unknown evaluate_cursor.sh flag '$1'" >&2; exit 1 ;;
    esac
done
if [[ -n "${FILTER_CASE}" || -n "${FILTER_TASK}" ]]; then
    filtered=()
    for entry in "${CASES[@]}"; do
        IFS='|' read -r _dt _tt _cn <<< "${entry}"
        if [[ -n "${FILTER_CASE}" && "${_cn}" != "${FILTER_CASE}" ]]; then continue; fi
        if [[ -n "${FILTER_TASK}" && "${_tt}" != "${FILTER_TASK}" ]]; then continue; fi
        filtered+=("${entry}")
    done
    if [[ "${#filtered[@]}" -eq 0 ]]; then
        echo "ERROR: --case='${FILTER_CASE}' --task='${FILTER_TASK}' matched zero entries in CASES" >&2
        exit 1
    fi
    CASES=("${filtered[@]}")
fi

# ===========================================================================
# Host-side bootstrap (three-directory cwd check / lib_helpers source)
# ===========================================================================

host_dir="$(pwd)"

# cwd three-directory check
if [[ ! -d "${host_dir}/src" ]] || [[ ! -d "${host_dir}/agent" ]] || [[ ! -d "${host_dir}/evaluator" ]]; then
    echo "FATAL: must run from repo root with src/, agent/, evaluator/ all present" >&2
    echo "  Hint: cd to repo root and run 'bash src/evaluate_*.sh'." >&2
    exit 1
fi

# Source lib_helpers.sh to get shared helpers.
# shellcheck disable=SC1091
source "${host_dir}/src/lib_helpers.sh"

# Docker images:
#   - drc-benchmark-detection : no klayout, runtime iptables blocklist (prevents
#                               the detection agent from invoking / installing
#                               klayout to leak the golden DRC answer).
#   - drc-benchmark-repair    : full klayout image (repair legitimately runs
#                               KLayout DRC to verify its own output).
DETECTION_IMAGE="${DETECTION_IMAGE:-drc-benchmark-detection}"
REPAIR_IMAGE="${REPAIR_IMAGE:-drc-benchmark-repair}"
testcase_base="${host_dir}/testcase/asap7"
skill_file="${host_dir}/agent/skill.md"
evaluator_dir="${host_dir}/evaluator"

# Host-side fail-fast — seccomp profile must exist before
# any docker create runs.  Profile is built by scripts/build_seccomp_profile.sh
# and lives in docker/seccomp-no-iptables.json.
seccomp_profile="${host_dir}/docker/seccomp-no-iptables.json"
if [[ ! -f "${seccomp_profile}" ]]; then
    echo "FATAL: seccomp profile not found: ${seccomp_profile}" >&2
    echo "  Run: bash scripts/build_seccomp_profile.sh" >&2
    exit 1
fi

total=$(( ${#MODEL_NAMES[@]} * ${#CASES[@]} ))
run_idx=0

# ===========================================================================
# Main loop (two-level structure: model -> case; task_type parsed from entry)
# ===========================================================================

for model_name in "${MODEL_NAMES[@]}"; do
    for case_entry in "${CASES[@]}"; do

        run_idx=$((run_idx + 1))

        # =====================================================================
        # Per-case subshell
        # =====================================================================
        (
            set -euo pipefail

            # ---------- (1) Parse case_entry ---------------------------------
            IFS='|' read -r design_type task_type case_name <<< "${case_entry}"

            # ---------- print banner ---------------------------------------
            echo ""
            echo "=========================================================="
            echo "  Run ${run_idx}/${total}: ${task_type} | ${model_name} | ${case_name} (${design_type})"
            echo "=========================================================="

            # validate design_type / task_type
            if [[ "${design_type}" != "cell" && "${design_type}" != "polygon" && "${design_type}" != "block" ]]; then
                echo "ERROR: Invalid design_type '${design_type}' for case '${case_name}'." >&2
                exit 1
            fi
            if [[ "${task_type}" != "detection" && "${task_type}" != "repair" ]]; then
                echo "ERROR: Invalid task_type '${task_type}' for case '${case_name}'." >&2
                exit 1
            fi

            # ---------- (2) testcase paths ---------------------------------
            case_testcase_dir="${testcase_base}/${design_type}"

            if [[ "${design_type}" == "cell" ]]; then
                design_rule="${testcase_base}/asap7_cell.lydrc"
            else
                design_rule="${testcase_base}/asap7.lydrc"
            fi

            # ---------- (3) effort / run_id (cursor has no effort) ---------
            effort=""
            run_id="${model_name}"

            # ---------- (4) container name --------------------------------
            container_name="drc-bench-${task_type}-${model_name}-${case_name}-$$"
            container_name=$(echo "${container_name}" | tr -c 'a-zA-Z0-9_.-' '-')

            # ---------- (5) input json path -------------------------------
            mkdir -p "${host_dir}/temp/info"
            input_json="${host_dir}/temp/info/${run_id}-${design_type}-${task_type}-${case_name}.json"

            # ---------- (6) staging path (multi-tenant suffix ${USER:-anon}.$$) -------
            runtime_root="${host_dir}/temp/runtime/${USER:-anon}/${run_id}/${design_type}/${task_type}/${case_name}.$$"
            staging_result="${runtime_root}/result"
            staging_score="${runtime_root}/score"
            staging_logs="${runtime_root}/logs"
            staging_temp="${runtime_root}/temp"
            staging_task="${runtime_root}/task"

            # ---------- (7) sealed_audit dir (host-only, never mounted) ----
            sealed_audit_dir="${host_dir}/.sealed_audit/${USER:-anon}/${run_id}/${design_type}/${task_type}/${case_name}.$$"

            # ---------- (8) score JSON / CSV path -------------------------
            score_json="${staging_score}/${run_id}/${design_type}/${task_type}/${case_name}_${task_type}_score.json"
            score_csv="${staging_score}/${run_id}/${design_type}/${task_type}/${task_type}_score.csv"

            # Prevent contamination from leftover staging
            rm -rf "${runtime_root}" "${sealed_audit_dir}"
            mkdir -p "${staging_result}" "${staging_score}" "${staging_logs}" \
                     "${staging_temp}" "${staging_task}" "${sealed_audit_dir}"

            # ---------- (9) Source of the original DRC report var ----------
            original_drc_report="${case_testcase_dir}/drc_report/${case_name}.drc.json"
            if [[ ! -f "${original_drc_report}" ]]; then
                original_drc_report="${case_testcase_dir}/drc_report/${case_name}.lyrpt"
            fi
            golden_report="${original_drc_report}"

            if [[ ! -f "${golden_report}" ]]; then
                echo "WARNING: Golden DRC report not found for ${case_name} at ${case_testcase_dir}/drc_report/" >&2
                golden_report=""
            fi

            # ---------- finalize_run trap ----------------------------------
            trap 'finalize_run $?' EXIT

            # =================================================================
            # Generate info.json on the host
            # =================================================================
            python3 "${host_dir}/src/build_case_info.py" \
                --model_name "${model_name}" \
                --case_name "${case_name}" \
                --design_type "${design_type}" \
                --task_type "${task_type}" \
                --output_path "placeholder" \
                --path_to_layout_script "${case_testcase_dir}/layout_script/${case_name}.py" \
                --path_to_layout_screenshot "${case_testcase_dir}/layout_screenshot/${case_name}/${case_name}.png" \
                --path_to_drc_report "${golden_report}" \
                --path_to_design_rule "${design_rule}" \
                --path_to_drm_jpg "${testcase_base}/drm_jpg" \
                --path_to_skill "${skill_file}" \
                --temp_dir "temp/${run_id}_${design_type}_${task_type}_${case_name}" \
                --json_output_path "${input_json}"

            echo "Generated info.json: ${input_json}"

            # =================================================================
            # Docker container setup
            # =================================================================
            # docker create flags include seccomp profile +
            # no-new-privileges + cap drop LINUX_IMMUTABLE.
            if [[ "${task_type}" == "detection" ]]; then
                IMAGE_TO_USE="${DETECTION_IMAGE}"
                EXTRA_DOCKER_FLAGS=(
                    "--cap-add=NET_ADMIN"
                    "--cap-drop=LINUX_IMMUTABLE"
                    "--security-opt" "seccomp=${seccomp_profile}"
                    "--security-opt" "no-new-privileges"
                )
            else
                IMAGE_TO_USE="${REPAIR_IMAGE}"
                EXTRA_DOCKER_FLAGS=(
                    "--cap-drop=LINUX_IMMUTABLE"
                    "--security-opt" "seccomp=${seccomp_profile}"
                    "--security-opt" "no-new-privileges"
                )
            fi

            echo "Creating container: ${container_name} (image=${IMAGE_TO_USE})"

            docker create \
                --name "${container_name}" \
                "${EXTRA_DOCKER_FLAGS[@]}" \
                -v "${HOME}/.config/cursor/auth.json:/root/.config/cursor/auth.json:ro" \
                -v "${host_dir}/agent:/workspace/agent:ro" \
                -v "${host_dir}/result:/workspace/result" \
                -v "${host_dir}/score:/workspace/score" \
                -v "${host_dir}/logs:/workspace/logs" \
                -v "${host_dir}/temp:/workspace/temp" \
                "${IMAGE_TO_USE}" \
                sleep infinity > /dev/null

            docker start "${container_name}" > /dev/null

            # -----------------------------------------------------------------
            # Copy info.json into container
            # -----------------------------------------------------------------
            docker cp "${input_json}" "${container_name}:/workspace/task/info.json"

            docker exec "${container_name}" mkdir -p /workspace/evaluator_helpers
            for helper in parse_info_json.py postprocess_info_json.py check_connectivity.py; do
                docker cp "${host_dir}/evaluator/${helper}" \
                    "${container_name}:/workspace/evaluator_helpers/${helper}"
            done

            # -----------------------------------------------------------------
            # Host-side stderr capture path
            # -----------------------------------------------------------------
            agent_stderr_log="${sealed_audit_dir}/agent_stderr.log"
            : > "${agent_stderr_log}"

            # =================================================================
            # Run pipeline (flow depends on task type)
            # =================================================================
            if [[ "${task_type}" == "repair" ]]; then
                # Repair: inject golden DRC report BEFORE agent (repair needs to see it).
                echo "Injecting golden DRC report into container..."
                if [[ -n "${golden_report}" && -f "${golden_report}" ]]; then
                    docker exec "${container_name}" mkdir -p "/workspace/testcase/asap7/${design_type}/drc_report"
                    docker cp "${golden_report}" \
                        "${container_name}:/workspace/testcase/asap7/${design_type}/drc_report/"
                fi

                echo "Running agent (repair, golden report visible)..."
                # PYTHONDONTWRITEBYTECODE=1.
                if docker exec \
                    -e "PYTHONDONTWRITEBYTECODE=1" \
                    "${container_name}" \
                    bash src/run_pipeline_cursor.sh --agent-only /workspace/task/info.json \
                    2>&1 | tee -a "${agent_stderr_log}"; then

                    # Disconnect first, then pause+kill via helper.
                    disconnect_container_network "${container_name}" \
                        || echo "WARNING: disconnect_container_network failed for ${case_name}. Continuing." >&2
                    kill_leftover_processes "${container_name}" \
                        || echo "WARNING: kill_leftover_processes failed for ${case_name}. Continuing." >&2

                    # Post-kill reinject.
                    reinject_critical_binaries "${container_name}" "${host_dir}" post-kill || \
                        echo "WARNING: critical binary re-inject failed; verify may use untrusted sha256sum" >&2

                    # Parse host-captured agent stderr.
                    eval "$(parse_agent_stderr "${agent_stderr_log}")" \
                        || echo "WARNING: parse_agent_stderr returned non-zero (using defaults)" >&2

                    # Aggregate per-call tokens; override tokens_json only when source==per_call_files. (cursor uses run_id="${model_name}"; see evaluate_cursor.sh:203.)
                    calls_dir_on_host="${host_dir}/score/${run_id}/${design_type}/${task_type}/calls"
                    _require_flag=""
                    if [[ "${agent_status:-fail}" == "success" ]]; then
                        _require_flag="--require-files"
                    fi
                    _agg_triple="$(aggregate_call_tokens_for_case \
                        "${calls_dir_on_host}" \
                        "${case_name}" \
                        "${sealed_audit_dir}/${case_name}_tokens_combined.json" \
                        "${tokens_json}" \
                        "${sealed_audit_dir}/${case_name}_aggregate_call_tokens.log" \
                        "${_require_flag}")" \
                        || _agg_triple="${tokens_json}|0|fallback_tokens"
                    _agg_tokens="$(printf '%s' "${_agg_triple}" | awk -F'|' '{print $1}')"
                    _agg_num="$(printf '%s'    "${_agg_triple}" | awk -F'|' '{print $2}')"
                    _agg_source="$(printf '%s' "${_agg_triple}" | awk -F'|' '{print $3}')"
                    if [[ "${_agg_source}" == "per_call_files" ]]; then
                        tokens_json="${_agg_tokens}"
                        num_calls="${_agg_num}"
                        # Per-call file is written only on agent-success branch
                        # in agent_backend/*.py (O_CREAT|O_EXCL). Its presence
                        # is independent proof the agent CLI completed. If the
                        # text-marker scrape said fail (e.g., host stderr log
                        # truncated by a concurrent docker-daemon race), promote
                        # status to success and rescue runtime from per-call.
                        if [[ "${agent_status:-fail}" != "success" ]]; then
                            echo "WARN: agent_status='${agent_status:-fail}' from stderr markers but per-call file present (n=${num_calls}); promoting to success." >&2
                            agent_status="success"
                            _pcf="$(find "${calls_dir_on_host}" -maxdepth 1 -type f -name "${case_name}_*.json" 2>/dev/null | sort | head -1)"
                            if [[ -n "${_pcf}" ]]; then
                                _rt="$(python3 -c '
import json, sys
from datetime import datetime
try:
    d = json.load(open(sys.argv[1]))
    s = d.get("started_at"); f = d.get("finished_at")
    if s and f:
        ts = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        tf = datetime.strptime(f, "%Y-%m-%dT%H:%M:%SZ")
        print((tf - ts).total_seconds())
    else:
        print(0)
except Exception:
    print(0)
' "${_pcf}" 2>/dev/null || echo 0)"
                                if [[ "${_rt}" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [[ "${_rt}" != "0" ]]; then
                                    agent_runtime_seconds="${_rt}"
                                fi
                            fi
                        fi
                    elif [[ "${_agg_source}" == "mandatory_calls_recording_missing" ]]; then
                        agent_status="fail"
                        num_calls=0
                    else
                        num_calls=0
                    fi
                    [[ "${num_calls}" =~ ^[0-9]+$ ]] || num_calls=0

                    # Seal per-call files for this case (filter by case_name prefix).
                    mkdir -p "${sealed_audit_dir}/${case_name}_call_tokens"
                    find "${calls_dir_on_host}" -maxdepth 1 -type f \
                         -name "${case_name}_*.json" -print0 2>/dev/null \
                        | xargs -0 -I{} cp -aP {} \
                          "${sealed_audit_dir}/${case_name}_call_tokens/" 2>/dev/null || true

                    agent_meta_trusted="${sealed_audit_dir}/${case_name}_agent_meta.json"
                    write_trusted_agent_meta "${agent_meta_trusted}" \
                        "${agent_status:-fail}" \
                        "${agent_runtime_seconds:-0}" \
                        "${tokens_json}" \
                        || echo "WARNING: write_trusted_agent_meta failed" >&2

                    # Seal agent output (repair output is _repaired.py).
                    container_output="/workspace/result/${run_id}/${design_type}/${task_type}/${case_name}/${case_name}_repaired.py"
                    sealed_output="${sealed_audit_dir}/${case_name}_repaired.py"
                    docker cp "${container_name}:${container_output}" "${sealed_output}" 2>/dev/null \
                        || echo "WARNING: agent output not produced; sealed_output empty" >&2

                    if [[ -f "${sealed_output}" ]]; then
                        sha256sum "${sealed_output}" | awk '{print $1}' > "${sealed_audit_dir}/${case_name}_repaired.sha256"
                    fi

                    docker exec "${container_name}" mkdir -p /workspace/evaluator 2>/dev/null || true
                    docker cp "${host_dir}/evaluator/." \
                        "${container_name}:/workspace/evaluator" \
                        || echo "WARNING: docker cp evaluator/. failed" >&2

                    # docker cp trusted agent_meta.json into container.
                    if [[ -f "${agent_meta_trusted}" ]]; then
                        docker exec "${container_name}" mkdir -p /workspace/temp/sealed 2>/dev/null || true
                        docker cp "${agent_meta_trusted}" \
                            "${container_name}:/workspace/temp/sealed/${case_name}_agent_meta.json" 2>/dev/null \
                            || echo "WARNING: failed to inject trusted agent_meta.json into container" >&2
                    fi

                    # (Golden DRC report already injected before agent; no
                    # second injection needed — repair flow exposes golden
                    # to the agent legitimately.)

                    echo "Running scoring phase..."
                    docker exec \
                        -e "HARDENED_EVALUATION=1" \
                        -e "EVALUATOR_DIR=/workspace/evaluator" \
                        -e "TRUSTED_PYTHON=/usr/local/bin/python3-trusted" \
                        -e "NUM_CALLS=${num_calls:-0}" \
                        "${container_name}" \
                        bash src/run_pipeline_cursor.sh --score-only /workspace/task/info.json \
                        2>&1 | tee -a "${agent_stderr_log}" \
                    || echo "WARNING: Scoring failed for ${case_name}. Continuing." >&2
                else
                    echo "WARNING: Agent failed for ${case_name}, skipping scoring. Continuing." >&2
                fi

            else
                echo "Running agent (detection, no golden report visible)..."
                # PYTHONDONTWRITEBYTECODE=1.
                if docker exec \
                    -e "PYTHONDONTWRITEBYTECODE=1" \
                    "${container_name}" \
                    bash src/run_pipeline_cursor.sh --agent-only /workspace/task/info.json \
                    2>&1 | tee -a "${agent_stderr_log}"; then

                    # Disconnect first, then pause+kill via helper.
                    disconnect_container_network "${container_name}" \
                        || echo "WARNING: disconnect_container_network failed for ${case_name}. Continuing." >&2
                    kill_leftover_processes "${container_name}" \
                        || echo "WARNING: kill_leftover_processes failed for ${case_name}. Continuing." >&2

                    # Post-kill reinject.
                    reinject_critical_binaries "${container_name}" "${host_dir}" post-kill || \
                        echo "WARNING: critical binary re-inject failed; verify may use untrusted sha256sum" >&2

                    # Parse host-captured agent stderr.
                    eval "$(parse_agent_stderr "${agent_stderr_log}")" \
                        || echo "WARNING: parse_agent_stderr returned non-zero (using defaults)" >&2

                    calls_dir_on_host="${host_dir}/score/${run_id}/${design_type}/${task_type}/calls"
                    _require_flag=""
                    if [[ "${agent_status:-fail}" == "success" ]]; then
                        _require_flag="--require-files"
                    fi
                    _agg_triple="$(aggregate_call_tokens_for_case \
                        "${calls_dir_on_host}" \
                        "${case_name}" \
                        "${sealed_audit_dir}/${case_name}_tokens_combined.json" \
                        "${tokens_json}" \
                        "${sealed_audit_dir}/${case_name}_aggregate_call_tokens.log" \
                        "${_require_flag}")" \
                        || _agg_triple="${tokens_json}|0|fallback_tokens"
                    _agg_tokens="$(printf '%s' "${_agg_triple}" | awk -F'|' '{print $1}')"
                    _agg_num="$(printf '%s'    "${_agg_triple}" | awk -F'|' '{print $2}')"
                    _agg_source="$(printf '%s' "${_agg_triple}" | awk -F'|' '{print $3}')"
                    if [[ "${_agg_source}" == "per_call_files" ]]; then
                        tokens_json="${_agg_tokens}"
                        num_calls="${_agg_num}"
                        # Per-call file is written only on agent-success branch
                        # in agent_backend/*.py (O_CREAT|O_EXCL). Its presence
                        # is independent proof the agent CLI completed. If the
                        # text-marker scrape said fail (e.g., host stderr log
                        # truncated by a concurrent docker-daemon race), promote
                        # status to success and rescue runtime from per-call.
                        if [[ "${agent_status:-fail}" != "success" ]]; then
                            echo "WARN: agent_status='${agent_status:-fail}' from stderr markers but per-call file present (n=${num_calls}); promoting to success." >&2
                            agent_status="success"
                            _pcf="$(find "${calls_dir_on_host}" -maxdepth 1 -type f -name "${case_name}_*.json" 2>/dev/null | sort | head -1)"
                            if [[ -n "${_pcf}" ]]; then
                                _rt="$(python3 -c '
import json, sys
from datetime import datetime
try:
    d = json.load(open(sys.argv[1]))
    s = d.get("started_at"); f = d.get("finished_at")
    if s and f:
        ts = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        tf = datetime.strptime(f, "%Y-%m-%dT%H:%M:%SZ")
        print((tf - ts).total_seconds())
    else:
        print(0)
except Exception:
    print(0)
' "${_pcf}" 2>/dev/null || echo 0)"
                                if [[ "${_rt}" =~ ^[0-9]+(\.[0-9]+)?$ ]] && [[ "${_rt}" != "0" ]]; then
                                    agent_runtime_seconds="${_rt}"
                                fi
                            fi
                        fi
                    elif [[ "${_agg_source}" == "mandatory_calls_recording_missing" ]]; then
                        agent_status="fail"
                        num_calls=0
                    else
                        num_calls=0
                    fi
                    [[ "${num_calls}" =~ ^[0-9]+$ ]] || num_calls=0

                    # Seal per-call files for this case (filter by case_name prefix).
                    mkdir -p "${sealed_audit_dir}/${case_name}_call_tokens"
                    find "${calls_dir_on_host}" -maxdepth 1 -type f \
                         -name "${case_name}_*.json" -print0 2>/dev/null \
                        | xargs -0 -I{} cp -aP {} \
                          "${sealed_audit_dir}/${case_name}_call_tokens/" 2>/dev/null || true

                    agent_meta_trusted="${sealed_audit_dir}/${case_name}_agent_meta.json"
                    write_trusted_agent_meta "${agent_meta_trusted}" \
                        "${agent_status:-fail}" \
                        "${agent_runtime_seconds:-0}" \
                        "${tokens_json}" \
                        || echo "WARNING: write_trusted_agent_meta failed" >&2

                    # Seal agent output (forensic; fail-soft).
                    container_output="/workspace/result/${run_id}/${design_type}/${task_type}/${case_name}/${case_name}_${task_type}.json"
                    sealed_output="${sealed_audit_dir}/${case_name}_${task_type}.json"
                    docker cp "${container_name}:${container_output}" "${sealed_output}" 2>/dev/null \
                        || echo "WARNING: agent output not produced; sealed_output empty" >&2

                    # Sealed hash (host trusted).
                    sealed_hash="${sealed_audit_dir}/${case_name}_${task_type}.sha256"
                    if [[ -f "${sealed_output}" ]]; then
                        sha256sum "${sealed_output}" | awk '{print $1}' > "${sealed_hash}"
                    fi

                    # Inject evaluator bundle into
                    # container.  Use trailing-dot `evaluator/.` so docker cp
                    # treats source as "directory contents" — destination
                    # /workspace/evaluator must exist as directory.  Without
                    # the trailing dot docker cp may treat source as file or
                    # nest evaluator/evaluator/ depending on dest existence.
                    docker exec "${container_name}" mkdir -p /workspace/evaluator 2>/dev/null || true
                    docker cp "${host_dir}/evaluator/." \
                        "${container_name}:/workspace/evaluator" \
                        || echo "WARNING: docker cp evaluator/. failed" >&2

                    # docker cp trusted agent_meta.json into container.
                    if [[ -f "${agent_meta_trusted}" ]]; then
                        docker exec "${container_name}" mkdir -p /workspace/temp/sealed 2>/dev/null || true
                        docker cp "${agent_meta_trusted}" \
                            "${container_name}:/workspace/temp/sealed/${case_name}_agent_meta.json" 2>/dev/null \
                            || echo "WARNING: failed to inject trusted agent_meta.json into container" >&2
                    fi

                    echo "Injecting golden DRC report into container for scoring..."
                    if [[ -n "${golden_report}" && -f "${golden_report}" ]]; then
                        docker exec "${container_name}" mkdir -p "/workspace/testcase/asap7/${design_type}/drc_report"
                        docker cp "${golden_report}" \
                            "${container_name}:/workspace/testcase/asap7/${design_type}/drc_report/"

                        # sha256 verify after golden inject
                        host_golden_hash=$(sha256sum "${golden_report}" | awk '{print $1}')
                        container_golden_path="/workspace/testcase/asap7/${design_type}/drc_report/$(basename "${golden_report}")"
                        if docker exec "${container_name}" test -x /usr/local/bin/sha256sum-trusted 2>/dev/null; then
                            container_golden_hash=$(docker exec "${container_name}" /usr/local/bin/sha256sum-trusted "${container_golden_path}" 2>/dev/null | awk '{print $1}')
                        else
                            container_golden_hash=$(docker exec "${container_name}" sha256sum "${container_golden_path}" 2>/dev/null | awk '{print $1}')
                        fi
                        if [[ -n "${container_golden_hash}" && "${host_golden_hash}" != "${container_golden_hash}" ]]; then
                            echo "ERROR: golden DRC hash mismatch (fail-closed) — host=${host_golden_hash:0:12}, container=${container_golden_hash:0:12}" >&2
                            # subshell exits non-zero; finalize_run trap will
                            # still run; the outer loop catches rc via
                            # `|| echo "case ... failed"`.
                            exit 1
                        fi
                    fi

                    echo "Running scoring phase..."
                    # Score phase: HARDENED_EVALUATION=1 + NUM_CALLS for runtime.csv.
                    docker exec \
                        -e "HARDENED_EVALUATION=1" \
                        -e "EVALUATOR_DIR=/workspace/evaluator" \
                        -e "TRUSTED_PYTHON=/usr/local/bin/python3-trusted" \
                        -e "NUM_CALLS=${num_calls:-0}" \
                        "${container_name}" \
                        bash src/run_pipeline_cursor.sh --score-only /workspace/task/info.json \
                        2>&1 | tee -a "${agent_stderr_log}" \
                    || echo "WARNING: Scoring failed for ${case_name}. Continuing." >&2
                else
                    echo "WARNING: Agent failed for ${case_name}, skipping scoring. Continuing." >&2
                fi
            fi

            echo "  Results : result/${run_id}/${design_type}/${task_type}/${case_name}/"
            echo "  Scores  : score/${run_id}/${design_type}/${task_type}/"

            # -----------------------------------------------------------------
            # Copy task directory (prompts, info.json) from container to host
            # -----------------------------------------------------------------
            mkdir -p "${host_dir}/task"
            docker cp "${container_name}:/workspace/task/" "${host_dir}/task/" 2>/dev/null || true

            # -----------------------------------------------------------------
            # Cleanup container for this iteration
            # -----------------------------------------------------------------
            echo "Cleaning up container: ${container_name}"
            docker stop "${container_name}" > /dev/null 2>&1 || true
            docker kill "${container_name}" > /dev/null 2>&1 || true
            docker rm "${container_name}" > /dev/null 2>&1 || true

        ) || echo "case ${case_entry} failed: rc=$?" >&2

    done
done

echo ""
echo "=========================================================="
echo "  All runs complete."
echo "=========================================================="
