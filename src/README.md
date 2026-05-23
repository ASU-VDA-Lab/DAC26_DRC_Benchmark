# src/ — Pipeline orchestration scripts

In-container pipeline drivers and host-side paper experiment runners.

> **Modification policy:** **Do NOT modify** anything under `src/`. These scripts define the agent / score split-flow, the host-side trusted-meta injection, and the post-kill clean-up — patching them changes the trust model and invalidates results. Only `agent/` is user-modifiable — see [`../CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) for the contracts your custom agent must satisfy so these orchestration scripts still work.

## Quick reference

- `lib_helpers.sh` — shared bash helpers sourced by all `evaluate_*.sh` scripts (runtime staging, `finalize_run`, `disconnect_container_network`, `kill_leftover_processes`, `aggregate_call_tokens_for_case`, `promote_status_from_per_call`, `reinject_critical_binaries`).
- `agent_backend/` — frozen backend modules for the three supported CLIs (`claude` / `codex` / `cursor`) plus the shared `per_call_writer_helpers.py`. See `CUSTOM_AGENT.md` "Backend CLI invariants (frozen)". Edits require a docker rebuild. Constraint: do not add Python modules with stdlib-shadowing names (`json.py`, `os.py`, etc.) at the `src/` top level — `agent.py`'s `sys.path` prepend of `/workspace/src` would pick them up.
- `run_pipeline_cursor.sh` — in-container orchestrator (Cursor Agent CLI).
- `run_pipeline_claude.sh` — same, invokes `agent/agent.py --backend claude`.
- `run_pipeline_codex.sh` — same, invokes `--backend codex`. **Requires `CODEX_EFFORT`**; the `run_id` is `<model_name>-<effort>`.
- `evaluate_cursor.sh` — host-side paper runner (Cursor): iterates task_type x model_name x case, generates `info.json`, manages container lifecycle, injects golden DRC reports.
- `evaluate_claude.sh` — same for Claude Code; `MODEL_NAMES` entries are `"<model> <effort>"` pairs.
- `evaluate_codex.sh` — same for Codex; bind-mounts `~/.codex/auth.json`; same `"<model> <effort>"` format.
- `build_case_info.py` — emits per-case `info.json` (paths + prompt config + `path_to_connectivity_file` for cell / block).

## Workflow

In-container (single case):

```bash
bash src/run_pipeline_cursor.sh                /workspace/task/info.json
bash src/run_pipeline_claude.sh [--agent-only|--score-only] /workspace/task/info.json
CODEX_EFFORT=high bash src/run_pipeline_codex.sh           /workspace/task/info.json
```

Host-side (paper experiments):

```bash
bash src/evaluate_cursor.sh
bash src/evaluate_claude.sh
bash src/evaluate_codex.sh
```

`info.json` field list lives in [`CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) under "info.json fields available to your prompt template". `output_path` and `temp_dir` are overwritten by the pipeline with computed container paths.

## Pipeline steps

1. `evaluator/postprocess_info_json.py` — rewrite info.json paths to container view.
2. `agent/prompt_format.py` — render prompt from `agent/prompts/<task>.json` + info.json.
3. `agent/agent.py --backend {cursor,claude,codex}` — single LLM call; emits `STATUS=` and `RUNTIME_SECONDS=` markers on stderr (always), plus `TOKENS_JSON=` when `RECORD_TOKENS=1`.
4. (repair only) KLayout batch render -> `evaluator/run_klayout_drc.py` -> `evaluator/process_klayout_reports.py` (`.lyrpt` -> `.drc.json`) -> `evaluator/sanity_check.py` -> `evaluator/check_connectivity.py` (cell / block).
5. `evaluator/score_repair.py` or `evaluator/score_detection.py` — reads `agent_status` / `runtime_seconds` / 4 token fields from a trusted `--agent-meta` JSON (canonical agent-meta channel), writes per-case score JSON.
6. (repair) `evaluator/merge_score_sanity.py` + `evaluator/merge_score_connectivity.py` — merge into score JSON.
7. The four token fields plus `num_calls` are written directly into `score.json` by `score_repair.py` / `score_detection.py` when `RECORD_TOKENS=1`. With `RECORD_TOKENS=0` (default) those five fields are omitted entirely. There are no CSV outputs. The `NUM_CALLS` env var is computed by the `aggregate_call_tokens_for_case` helper in `lib_helpers.sh` (which wraps `evaluator/aggregate_call_tokens.py` and reads its `--output` JSON file — never `eval`s stdout) and is forwarded into the scorer via `--num-calls`.

All console output is also captured to `logs/<run_id>_<design_type>_<task_type>_<case_name>.log`. Each per-case score JSON additionally carries an `evaluator_hash` field embedded by `evaluator/score_repair.py` / `score_detection.py` / `write_invalid_score.py` (audit-only; pipeline does not verify at runtime).

## Env vars

| Variable | Default | Description |
|---|---|---|
| `WORKSPACE` | `/workspace` | Workspace root (set by Docker image ENV). |
| `SKIP_DRC` | `0` | `1` skips KLayout DRC (repair only). |
| `CLAUDE_EFFORT` | unset | **Required** for `run_pipeline_claude.sh` (e.g. `medium`, `high`); forwarded as `--effort` and folded into `run_id`. |
| `CODEX_EFFORT` | unset | **Required** for `run_pipeline_codex.sh`; forwarded as `--effort` and folded into `run_id`. |
| `RECORD_TOKENS` | `0` | Toggle per-call token recording. `1` enables backend per-call writes, the host aggregator, and emission of the 4 token fields + `num_calls` in `score.json`. `0` (default) skips the entire recording pipeline; those five fields are omitted from `score.json`. |
| `AGENT_CALLS_DIR` | `${score_dir}/calls` (set by `run_pipeline_*.sh` on non-score phase **only when `RECORD_TOKENS=1`**) | Flat directory (shared across cases) where backends write one `${case_name}_${call_seq:04d}_<sha8>.json` per LLM call via the shared helper `src/agent_backend/per_call_writer_helpers.py`. Best-effort: STATUS=success + zero per-call files for the case -> the scorer emits a string sentinel for the four token fields and `num_calls`. |
| `AGENT_CASE_NAME` | `${case_name}` (set by `run_pipeline_*.sh` on non-score phase only when `RECORD_TOKENS=1`) | Case name used as filename prefix by the per-call writer helper. |
| `NUM_CALLS` | `0` | Set by `evaluate_*.sh` on the score-phase `docker exec`; forwarded from the aggregator's `n_call_ids_valid` into the scorer's `--num-calls` flag (only consumed when `RECORD_TOKENS=1`). |

## See also

- [`../agent/README.md`](../agent/README.md) — agent dispatcher, backends, prompt schema.
- [`../CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) — info.json field list and the agent CLI / stderr contracts.
- [`../evaluator/README.md`](../evaluator/README.md) — trusted score bundle and helpers invoked from steps 4–7.
