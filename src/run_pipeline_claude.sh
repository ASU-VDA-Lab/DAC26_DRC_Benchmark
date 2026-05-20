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
# Orchestrates the full evaluation pipeline using KLayout DRC for one model.
#
# Usage:
#   bash src/run_pipeline_claude.sh [--agent-only|--score-only] <info.json>
#
# Phase flags (apply to both detection and repair tasks):
#   --agent-only   Run only prompt formatting and agent call (no scoring)
#   --score-only   Run only scoring, CSV, and logging (agent must have run first)
#
# Each invocation runs exactly one model and stores results under
# result/<model_name>/<design_type>/<task_type>/<case_name>/ and
# score/<model_name>/<design_type>/<task_type>/.

set -euo pipefail

# Compute workspace + helper dir paths early (needed for helper scripts).
workspace="${WORKSPACE:-/workspace}"
agent_dir="/workspace/agent"
helpers_dir="${EVALUATOR_HELPERS_DIR:-/workspace/evaluator_helpers}"
evaluator_dir="${EVALUATOR_DIR:-/workspace/evaluator}"
backend="claude"

# ---------------------------------------------------------------------------
# 1. Parse arguments
# ---------------------------------------------------------------------------
phase="full"  # full | agent | score

# Check for phase flags
while [[ "${1:-}" == --* ]]; do
    case "$1" in
        --agent-only) phase="agent"; shift ;;
        --score-only) phase="score"; shift ;;
        *) echo "Error: unknown flag '$1'" >&2; exit 1 ;;
    esac
done

# In --score-only mode, read helper scripts (parse_info_json,
# postprocess_info_json, check_connectivity) from the trusted
# /workspace/evaluator/ bundle that the host injected after agent kill, not
# from /workspace/evaluator_helpers/ which the agent may have tampered.
if [[ "${phase}" == "score" && -d "${evaluator_dir}" ]]; then
    helpers_dir="${evaluator_dir}"
fi

if [[ "$#" -ne 1 ]]; then
    echo "Usage: bash src/run_pipeline_claude.sh [--agent-only|--score-only] <info.json>" >&2
    exit 1
fi

input_json="$1"
if [[ ! -f "${input_json}" ]]; then
    echo "Error: info.json not found: ${input_json}" >&2
    exit 1
fi
eval "$(python3 "${helpers_dir}/parse_info_json.py" "${input_json}")"

if [[ -z "${task_type}" || -z "${model_name}" || -z "${case_name}" || -z "${design_type}" ]]; then
    echo "Error: missing required fields (task_type, model_name, case_name, design_type)." >&2
    exit 1
fi

if [[ "${task_type}" != "repair" && "${task_type}" != "detection" ]]; then
    echo "Error: task_type must be 'repair' or 'detection', got '${task_type}'." >&2
    exit 1
fi

if [[ "${design_type}" != "cell" && "${design_type}" != "polygon" && "${design_type}" != "block" ]]; then
    echo "Error: design_type must be 'cell', 'polygon', or 'block', got '${design_type}'." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Score-phase invariant
# ---------------------------------------------------------------------------
# 1. Hardened mode (HARDENED_EVALUATION=1 or SEALED_OUTPUT_SHA256 supplied)
#    requires evaluator_dir == /workspace/evaluator AND that directory exists.
# 2. agent phase reverse check: /workspace/evaluator must NOT exist before
#    score phase (host-side bundle injection happens between phases).
if [[ -n "${SEALED_OUTPUT_SHA256:-}" || "${HARDENED_EVALUATION:-0}" == "1" ]]; then
    if [[ "${evaluator_dir}" != "/workspace/evaluator" ]]; then
        echo "ERROR: HARDENED mode but EVALUATOR_DIR != /workspace/evaluator" >&2
        exit 1
    fi
    if [[ ! -d "${evaluator_dir}" ]]; then
        echo "ERROR: HARDENED mode but evaluator_dir missing: ${evaluator_dir}" >&2
        exit 1
    fi
fi

# Agent phase reverse check (evaluator bundle must not be visible yet)
if [[ "${phase:-}" == "agent" && -d "/workspace/evaluator" ]]; then
    echo "ERROR: /workspace/evaluator must NOT exist during agent phase" >&2
    exit 1
fi

# Belt-and-suspenders — even if docker exec did not
# pass -e PYTHONDONTWRITEBYTECODE=1, exporting it here keeps Python from
# writing .pyc into :ro mounted /workspace/agent.
export PYTHONDONTWRITEBYTECODE=1

# ---------------------------------------------------------------------------
# 2. Paths setup
# ---------------------------------------------------------------------------
testcase_base="${workspace}/testcase/asap7"
case_testcase_dir="${testcase_base}/${design_type}"

# ---------------------------------------------------------------------------
# Effort + run identifier (run_id = "${model_name}-${claude_effort}" so
# different effort tiers produce distinct output folders / files).
# ---------------------------------------------------------------------------
claude_effort="${CLAUDE_EFFORT:-}"
if [[ -z "${claude_effort}" ]]; then
    echo "Error: CLAUDE_EFFORT env var is required (e.g. 'medium', 'high')." >&2
    exit 1
fi
run_id="${model_name}-${claude_effort}"

# ---------------------------------------------------------------------------
# Log all stdout+stderr to a file while still printing to the terminal
# ---------------------------------------------------------------------------
log_dir="${workspace}/logs"
mkdir -p "${log_dir}"
log_file="${log_dir}/${run_id}_${design_type}_${task_type}_${case_name}.log"
exec > >(tee "${log_file}") 2>&1

# Golden DRC report: check drc_report/ (may be injected via docker cp)
golden_json="${case_testcase_dir}/drc_report/${case_name}.drc.json"
golden_lyrpt="${case_testcase_dir}/drc_report/${case_name}.lyrpt"
if [[ -f "${golden_json}" ]]; then
    golden_report="${golden_json}"
elif [[ -f "${golden_lyrpt}" ]]; then
    golden_report="${golden_lyrpt}"
else
    golden_report=""
fi

# For repair, golden report must be present before agent runs
if [[ "${task_type}" == "repair" && -z "${golden_report}" ]]; then
    echo "WARNING: Golden DRC report not found for ${case_name}. Scoring may fail." >&2
fi

# Prompt template selection: design-type-specific for repair, generic for detection.
# Fail-fast when neither design-specific nor generic
# template exists, instead of silently passing a nonexistent path to
# prompt_format.py (which would raise a traceback under set -euo).
if [[ "${task_type}" == "repair" && -f "${agent_dir}/prompts/repair_${design_type}.json" ]]; then
    prompt_template="${agent_dir}/prompts/repair_${design_type}.json"
elif [[ -f "${agent_dir}/prompts/${task_type}.json" ]]; then
    prompt_template="${agent_dir}/prompts/${task_type}.json"
else
    echo "ERROR: prompt template missing for task_type=${task_type} design_type=${design_type}" >&2
    echo "       Looked for: ${agent_dir}/prompts/repair_${design_type}.json (repair) and ${agent_dir}/prompts/${task_type}.json" >&2
    exit 1
fi

# Skill file for KLayout DRC
skill_file="${agent_dir}/skill.md"

# DRC rule file (.lydrc for KLayout)
if [[ "${design_type}" == "cell" ]]; then
    design_rule="${testcase_base}/asap7_cell.lydrc"
else
    design_rule="${testcase_base}/asap7.lydrc"
fi

# ---------------------------------------------------------------------------
# 3. Agent dispatcher (unified)
# ---------------------------------------------------------------------------
AGENT_SCRIPT="${agent_dir}/agent.py"

echo "============================================="
echo "  DRC Benchmark Pipeline (KLayout)"
echo "============================================="
echo "  task_type   : ${task_type}"
echo "  model_name  : ${model_name}"
echo "  case_name   : ${case_name}"
echo "  design_type : ${design_type}"
echo "  phase       : ${phase}"
echo "  workspace   : ${workspace}"
echo "  effort      : ${claude_effort}"
echo ""

# ---------------------------------------------------------------------------
# Helper: write score dict from JSON to CSV
# ---------------------------------------------------------------------------
write_score_csv() {
    local score_json="$1"
    local score_csv="$2"
    local case="$3"

    "${PY:-python3}" "${evaluator_dir}/write_score_csv.py" "${score_json}" "${score_csv}" "${case}"
}

# ---------------------------------------------------------------------------
# 4. Set up result/score directories (needed before prompt formatting)
# ---------------------------------------------------------------------------
result_dir="${workspace}/result/${run_id}/${design_type}/${task_type}/${case_name}"
score_dir="${workspace}/score/${run_id}/${design_type}/${task_type}"
temp_dir="${workspace}/temp/${run_id}_${design_type}_${task_type}_${case_name}_$$"
mkdir -p "${result_dir}" "${score_dir}" "${temp_dir}"

# Per-case AGENT_CALLS_DIR; gated on phase != score.
# Shared flat dir across cases; scope-clean stale files for THIS
# case only (do not rm -rf the shared calls/ tree). Parallel same-case
# runs (same run_id/model_name/design_type/task_type/case_name tuple) on
# the same host are caller responsibility; bump --run_id to isolate.
if [[ "${phase}" != "score" ]]; then
    export AGENT_CALLS_DIR="${score_dir}/calls"
    export AGENT_CASE_NAME="${case_name}"
    mkdir -p "${AGENT_CALLS_DIR}"
    rm -f "${AGENT_CALLS_DIR}/${case_name}_"*.json 2>/dev/null || true
fi

if [[ "${task_type}" == "repair" ]]; then
    agent_output="${result_dir}/${case_name}_repaired.py"
else
    agent_output="${result_dir}/${case_name}_detection.json"
fi

# ---------------------------------------------------------------------------
# 5. Format prompt (build processed info.json with container paths)
# ---------------------------------------------------------------------------
echo "[Step 1] Formatting prompt..."

task_dir="${workspace}/task/${run_id}/${design_type}/${task_type}"
mkdir -p "${task_dir}"

case_info_json="${task_dir}/${case_name}_info.json"

# Post-process the input JSON with container paths
python3 "${helpers_dir}/postprocess_info_json.py" \
    --input "${input_json}" \
    --output "${case_info_json}" \
    --skill_file "${skill_file}" \
    --testcase_dir "${case_testcase_dir}" \
    --case_name "${case_name}" \
    --golden_report "${golden_report}" \
    --design_rule "${design_rule}" \
    --drm_jpg "${testcase_base}/drm_jpg" \
    --output_path "${agent_output}" \
    --temp_dir "${temp_dir}" \
    --task_type "${task_type}"

formatted_prompt_path="${task_dir}/${case_name}_${task_type}_prompt.md"

python3 "${agent_dir}/prompt_format.py" \
    "${case_info_json}" \
    "${prompt_template}" \
    > "${formatted_prompt_path}"

echo "  Formatted prompt: ${formatted_prompt_path}"
echo ""

# ---------------------------------------------------------------------------
# 6. Run agent and downstream processing
# ---------------------------------------------------------------------------
original_script="${case_testcase_dir}/layout_script/${case_name}.py"

# Default values for agent meta (overwritten after agent call)
agent_status="fail"
agent_runtime_seconds="0"
tokens_json='{"input_tokens":0,"output_tokens":0,"cache_read_tokens":0,"cache_write_tokens":0}'

if [[ "${task_type}" == "repair" ]]; then

    # ===================================================================
    # REPAIR: split agent / score / full flow (mirrors detection)
    # ===================================================================
    meta_file="${result_dir}/.agent_meta.json"

    if [[ "${phase}" != "score" ]]; then
        # ----- Agent phase -----
        echo "[Step 2] Calling LLM agent (single call, no timeout)..."

        agent_stderr_tmp="$(mktemp)"
        python3 "${AGENT_SCRIPT}" \
            --backend "${backend}" \
            "${formatted_prompt_path}" \
            "${agent_output}" \
            --model "${model_name}" \
            --task_type "repair" \
            --workspace "${workspace}" \
            --temp_dir "${temp_dir}" \
            --fallback "${original_script}" \
            --raw-json-out "${score_dir}/${case_name}_agent_raw.json" \
            ${claude_effort:+--effort "${claude_effort}"} \
            2>"${agent_stderr_tmp}" || true
        cat "${agent_stderr_tmp}" >&2

        # The host wrapper (evaluate_claude.sh) uses parse_agent_stderr +
        # write_trusted_agent_meta after disconnect+kill to write sanitized
        # trusted JSON into sealed_audit_dir, then docker cp into
        # /workspace/temp/sealed/. The container side prefers the trusted
        # meta; if missing, falls back to the original grep for
        # standalone-debug compatibility.
        agent_meta_path="/workspace/temp/sealed/${case_name}_agent_meta.json"
        if [[ -f "${agent_meta_path}" ]]; then
            agent_status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("agent_status","fail"))' "${agent_meta_path}" 2>/dev/null || echo fail)"
            agent_runtime_seconds="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("agent_runtime_seconds",0))' "${agent_meta_path}" 2>/dev/null || echo 0)"
            tokens_json="$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])).get("tokens",{})))' "${agent_meta_path}" 2>/dev/null || echo '{"input_tokens":0,"output_tokens":0,"cache_read_tokens":0,"cache_write_tokens":0}')"
        else
            agent_status="$(grep -oP 'STATUS=\K(success|fail)' "${agent_stderr_tmp}" | tail -1 || echo fail)"
            tokens_json="$(grep -oP 'TOKENS_JSON=\K.*' "${agent_stderr_tmp}" | tail -1 || echo '{"input_tokens":0,"output_tokens":0,"cache_read_tokens":0,"cache_write_tokens":0}')"
            agent_runtime_seconds="$(grep -oP 'RUNTIME_SECONDS=\K[0-9.]+' "${agent_stderr_tmp}" | tail -1 || echo 0)"
        fi
        rm -f "${agent_stderr_tmp}"

        echo "  Agent output  : ${agent_output}"
        echo "  Agent status  : ${agent_status}"
        echo "  Agent runtime : ${agent_runtime_seconds}s"
        echo ""

        # Persist agent meta for --score-only phase
        python3 -c 'import json,sys; d={"agent_status":sys.argv[1],"agent_runtime_seconds":float(sys.argv[2]),"tokens":json.loads(sys.argv[3])}; print(json.dumps(d))' \
            "${agent_status}" "${agent_runtime_seconds}" "${tokens_json}" > "${meta_file}"
    fi

    if [[ "${phase}" == "agent" ]]; then
        echo "  Agent-only phase complete."
        [[ -d "${temp_dir}" ]] && rm -rf "${temp_dir}"
        exit 0
    fi

    # ----- Score phase -----
    # Score phase entry: switch to TRUSTED_PYTHON if injected.
    PY="${TRUSTED_PYTHON:-python3}"
    agent_meta_path="/workspace/temp/sealed/${case_name}_agent_meta.json"

    # Recover meta for score-only mode
    if [[ -f "${meta_file}" ]]; then
        agent_status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["agent_status"])' "${meta_file}")"
        agent_runtime_seconds="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["agent_runtime_seconds"])' "${meta_file}")"
        tokens_json="$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["tokens"]))' "${meta_file}")"
    fi

    # Re-locate golden report (may have been injected after agent phase)
    if [[ -z "${golden_report}" || ! -f "${golden_report}" ]]; then
        golden_json="${case_testcase_dir}/drc_report/${case_name}.drc.json"
        golden_lyrpt="${case_testcase_dir}/drc_report/${case_name}.lyrpt"
        if [[ -f "${golden_json}" ]]; then
            golden_report="${golden_json}"
        elif [[ -f "${golden_lyrpt}" ]]; then
            golden_report="${golden_lyrpt}"
        fi
    fi

    # --- Render GDS ---
    echo "[Step 3] Rendering GDS..."
    render_script="${temp_dir}/${case_name}_render.py"
    gds_path="${temp_dir}/${case_name}.gds"
    lyrpt_path="${temp_dir}/${case_name}.lyrpt"
    drc_json_path="${temp_dir}/${case_name}.drc.json"

    "${PY}" "${evaluator_dir}/prepare_render_script.py" \
        "${agent_output}" "${render_script}" "${gds_path}"
    klayout -b -r "${render_script}" || echo "WARNING: KLayout render failed."

    # --- KLayout DRC ---
    if [[ "${SKIP_DRC:-0}" != "1" ]]; then
        echo "[Step 4] Running KLayout DRC..."
        "${PY}" "${evaluator_dir}/run_klayout_drc.py" "${gds_path}" "${design_rule}" "${lyrpt_path}" || true
        if [[ -f "${lyrpt_path}" ]]; then
            "${PY}" "${evaluator_dir}/process_klayout_reports.py" \
                --lyrpt "${lyrpt_path}" \
                --output "${drc_json_path}" \
                --case_name "${case_name}" \
                --design_type "${design_type}" \
                --layout-script "${agent_output}" || true
        fi
    fi

    # --- Sanity + Connectivity checks ---
    sanity_json_path="${temp_dir}/${case_name}_sanity.json"
    connectivity_json=""
    if [[ -f "${evaluator_dir}/sanity_check.py" ]]; then
        echo "[Step 5] Running sanity check..."
        klayout -b -r "${evaluator_dir}/sanity_check.py" \
            -rd "original_gds_path=${case_testcase_dir}/gds/${case_name}.gds" \
            -rd "modified_gds_path=${gds_path}" \
            -rd "original_script_path=${original_script}" \
            -rd "modified_script_path=${agent_output}" \
            -rd "design_type=${design_type}" \
            -rd "sanity_json_out=${sanity_json_path}" \
            || echo "WARNING: Sanity check failed."
    fi

    if [[ "${design_type}" == "cell" || "${design_type}" == "block" ]]; then
        echo "[Step 5] Checking connectivity (cell/block only)..."
        golden_conn_json="${original_script/\/layout_script\//\/connectivity\/}"
        golden_conn_json="${golden_conn_json%.py}.json"
        connectivity_json="${temp_dir}/${case_name}_connectivity.json"
        "${PY}" "${helpers_dir}/check_connectivity.py" \
            "${golden_conn_json}" "${agent_output}" "${design_type}" \
            > "${connectivity_json}" || true
    fi

    # --- Score ---
    echo "[Step 6] Scoring..."
    score_json="${score_dir}/${case_name}_score.json"
    if [[ -f "${drc_json_path}" ]]; then
        repaired_arg="${drc_json_path}"
    elif [[ -f "${lyrpt_path}" ]]; then
        repaired_arg="${lyrpt_path}"
    else
        repaired_arg=""
    fi

    # agent_meta fail-closed guard (symmetric with the
    # detection-side guard above). score_repair.py requires --agent-meta
    # and unconditionally opens it; if the trusted meta failed to inject
    # or agent_status is not success, write a null score JSON + CSV and
    # skip the scorer rather than crashing the whole pipeline.
    if [[ ! -f "${agent_meta_path}" ]]; then
        echo "agent_meta missing at ${agent_meta_path}; emitting fail-closed null repair score." >&2
        score_csv="${score_dir}/${case_name}_score.csv"
        "${PY}" "${evaluator_dir}/write_invalid_score.py" \
            --output "${score_json}" \
            --task "${task_type}" \
            --invalid-reason "agent_meta_missing" \
            --null-metrics --null-tokens || true
        "${PY}" "${evaluator_dir}/write_score_csv.py" \
            "${score_json}" "${score_csv}" "${case_name}" || true
        exit 0
    fi
    _agent_status_from_meta="$("${PY}" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("agent_status","fail"))' "${agent_meta_path}" 2>/dev/null || echo fail)"
    if [[ "${_agent_status_from_meta}" != "success" ]]; then
        echo "agent_status=${_agent_status_from_meta}; emitting fail-closed null repair score." >&2
        score_csv="${score_dir}/${case_name}_score.csv"
        "${PY}" "${evaluator_dir}/write_invalid_score.py" \
            --output "${score_json}" \
            --task "${task_type}" \
            --invalid-reason "agent_failed" \
            --null-metrics --null-tokens \
            --agent-meta "${agent_meta_path}" || true
        "${PY}" "${evaluator_dir}/write_score_csv.py" \
            "${score_json}" "${score_csv}" "${case_name}" || true
        exit 0
    fi

    "${PY}" "${evaluator_dir}/score_repair.py" \
        --original-drc "${golden_report}" \
        --new-drc "${repaired_arg}" \
        --output "${score_json}" \
        --agent-meta "${agent_meta_path}"

    # --- Merge check results into score ---
    if [[ -f "${sanity_json_path}" ]]; then
        echo "[Step 6.5] Merging sanity check into score..."
        "${PY}" "${evaluator_dir}/merge_score_sanity.py" \
            "${score_json}" "${sanity_json_path}" || true
    fi
    if [[ -n "${connectivity_json}" && -f "${connectivity_json}" ]]; then
        echo "[Step 6.5] Merging connectivity into score..."
        "${PY}" "${evaluator_dir}/merge_score_connectivity.py" \
            "${score_json}" "${connectivity_json}" || true
    fi

    # --- Write CSV ---
    score_csv="${score_dir}/${case_name}_score.csv"
    write_score_csv "${score_json}" "${score_csv}" "${case_name}"

else

    # ===================================================================
    # DETECTION: agent-only / score-only two-phase flow
    # ===================================================================
    meta_file="${result_dir}/.agent_meta.json"

    if [[ "${phase}" != "score" ]]; then
        # ----- Agent phase -----
        echo "[Step 2] Calling LLM agent (detection, single call, no timeout)..."

        agent_stderr_tmp="$(mktemp)"
        python3 "${AGENT_SCRIPT}" \
            --backend "${backend}" \
            "${formatted_prompt_path}" \
            "${agent_output}" \
            --model "${model_name}" \
            --task_type "detection" \
            --workspace "${workspace}" \
            --temp_dir "${temp_dir}" \
            --raw-json-out "${score_dir}/${case_name}_agent_raw.json" \
            ${claude_effort:+--effort "${claude_effort}"} \
            2>"${agent_stderr_tmp}" || true
        cat "${agent_stderr_tmp}" >&2

        # Replaces in-container stderr grep. The host wrapper
        # has already docker cp'd a trusted JSON into
        # /workspace/temp/sealed/${case_name}_agent_meta.json after
        # disconnect+kill; the container side prefers the trusted meta and
        # falls back to the original grep for standalone-debug compatibility.
        agent_meta_path="/workspace/temp/sealed/${case_name}_agent_meta.json"
        if [[ -f "${agent_meta_path}" ]]; then
            agent_status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("agent_status","fail"))' "${agent_meta_path}" 2>/dev/null || echo fail)"
            agent_runtime_seconds="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("agent_runtime_seconds",0))' "${agent_meta_path}" 2>/dev/null || echo 0)"
            tokens_json="$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])).get("tokens",{})))' "${agent_meta_path}" 2>/dev/null || echo '{"input_tokens":0,"output_tokens":0,"cache_read_tokens":0,"cache_write_tokens":0}')"
        else
            agent_status="$(grep -oP 'STATUS=\K(success|fail)' "${agent_stderr_tmp}" | tail -1 || echo fail)"
            tokens_json="$(grep -oP 'TOKENS_JSON=\K.*' "${agent_stderr_tmp}" | tail -1 || echo '{"input_tokens":0,"output_tokens":0,"cache_read_tokens":0,"cache_write_tokens":0}')"
            agent_runtime_seconds="$(grep -oP 'RUNTIME_SECONDS=\K[0-9.]+' "${agent_stderr_tmp}" | tail -1 || echo 0)"
        fi
        rm -f "${agent_stderr_tmp}"

        echo "  Agent output  : ${agent_output}"
        echo "  Agent status  : ${agent_status}"
        echo "  Agent runtime : ${agent_runtime_seconds}s"
        echo ""

        # Persist agent meta for --score-only phase
        python3 -c 'import json,sys; d={"agent_status":sys.argv[1],"agent_runtime_seconds":float(sys.argv[2]),"tokens":json.loads(sys.argv[3])}; print(json.dumps(d))' \
            "${agent_status}" "${agent_runtime_seconds}" "${tokens_json}" > "${meta_file}"
    fi

    if [[ "${phase}" == "agent" ]]; then
        echo "  Agent-only phase complete."
        [[ -d "${temp_dir}" ]] && rm -rf "${temp_dir}"
        exit 0
    fi

    # ----- Score phase -----
    # Score phase entry: switch to TRUSTED_PYTHON if injected.
    PY="${TRUSTED_PYTHON:-python3}"

    # When agent fails, fail-closed by writing null
    # metrics + null tokens score JSON / CSV, to prevent downstream
    # score_detection.py from trying to parse an empty file. trusted meta is
    # docker cp'd in by the host wrapper; missing file or agent_status !=
    # success is treated as agent_failed.
    agent_meta_path="/workspace/temp/sealed/${case_name}_agent_meta.json"
    if [[ -f "${agent_meta_path}" ]]; then
        _agent_status_from_meta="$("${PY}" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("agent_status","fail"))' "${agent_meta_path}" 2>/dev/null || echo fail)"
        if [[ "${_agent_status_from_meta}" != "success" ]]; then
            echo "agent_status=${_agent_status_from_meta}; emitting fail-closed null score." >&2
            mkdir -p "${score_dir}"
            score_json="${score_dir}/${case_name}_score.json"
            score_csv="${score_dir}/${case_name}_score.csv"
            "${PY}" "${evaluator_dir}/write_invalid_score.py" \
                --output "${score_json}" \
                --task "${task_type}" \
                --invalid-reason "agent_failed" \
                --null-metrics --null-tokens \
                --agent-meta "${agent_meta_path}" || true
            "${PY}" "${evaluator_dir}/write_score_csv.py" \
                "${score_json}" "${score_csv}" "${case_name}" || true
            exit 0
        fi
    fi

    # Re-locate golden report (may have been injected after agent phase)
    if [[ -z "${golden_report}" || ! -f "${golden_report}" ]]; then
        golden_json="${case_testcase_dir}/drc_report/${case_name}.drc.json"
        golden_lyrpt="${case_testcase_dir}/drc_report/${case_name}.lyrpt"
        if [[ -f "${golden_json}" ]]; then
            golden_report="${golden_json}"
        elif [[ -f "${golden_lyrpt}" ]]; then
            golden_report="${golden_lyrpt}"
        fi
    fi

    if [[ -z "${golden_report}" || ! -f "${golden_report}" ]]; then
        echo "ERROR: Golden DRC report not found for ${case_name}. Cannot score." >&2
        exit 1
    fi

    # Recover meta for score-only mode
    if [[ -f "${meta_file}" ]]; then
        agent_status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["agent_status"])' "${meta_file}")"
        agent_runtime_seconds="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["agent_runtime_seconds"])' "${meta_file}")"
        tokens_json="$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["tokens"]))' "${meta_file}")"
    fi

    echo "[Step 3] Scoring detection results..."
    score_json="${score_dir}/${case_name}_score.json"

    "${PY}" "${evaluator_dir}/score_detection.py" \
        --predicted "${agent_output}" \
        --golden "${golden_report}" \
        --output "${score_json}" \
        --agent-meta "${agent_meta_path}"

    score_csv="${score_dir}/${case_name}_score.csv"
    write_score_csv "${score_json}" "${score_csv}" "${case_name}"

fi

# ---------------------------------------------------------------------------
# 7. Append to logs/runtime.csv
# ---------------------------------------------------------------------------
log_dir="${workspace}/logs"
mkdir -p "${log_dir}"
runtime_csv="${log_dir}/runtime.csv"
timestamp_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# NUM_CALLS: optional; defaults to 0 for legacy single-call agents.
"${PY:-python3}" "${evaluator_dir}/log_runtime.py" \
    "${runtime_csv}" \
    "${model_name}" "${claude_effort}" "${task_type}" "${design_type}" "${case_name}" \
    "${agent_status}" \
    "${agent_runtime_seconds}" \
    "${tokens_json}" \
    "${timestamp_now}" \
    --num-calls "${NUM_CALLS:-0}"

echo "  Score: ${score_json}"
echo ""

# ---------------------------------------------------------------------------
# 8. Clean up temp directory
# ---------------------------------------------------------------------------
if [[ -d "${temp_dir}" ]]; then
    rm -rf "${temp_dir}"
    echo "  Temp directory cleaned: ${temp_dir}"
fi

echo "============================================="
echo "  Pipeline complete"
echo "  Model  : ${model_name}"
echo "  Case   : ${case_name}"
echo "  Results: ${result_dir}/"
echo "  Scores : ${workspace}/score/${run_id}/${design_type}/${task_type}/"
echo "============================================="
