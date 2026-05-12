# src/ — Pipeline orchestration scripts

In-container pipeline drivers and host-side paper experiment runners.

> **Modification policy:** **Do NOT modify** anything under `src/`. These scripts define the agent / score split-flow, the host-side trusted-meta injection, and the post-kill clean-up — patching them changes the trust model and invalidates results. Only `agent/` is user-modifiable — see [`../CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) for the contracts your custom agent must satisfy so these orchestration scripts still work.

## Quick reference

- `lib_helpers.sh` — shared bash helpers sourced by all `evaluate_*.sh` scripts (runtime staging, `finalize_run`, `disconnect_container_network`, `kill_leftover_processes`, `mark_invalid`, `generate_evaluator_manifest`, `reinject_critical_binaries`).
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

`info.json` schema lives in [`agent/README.md`](../agent/README.md) (Example info.json). `output_path` and `temp_dir` are overwritten by the pipeline with computed container paths.

## Pipeline steps

1. `evaluator/postprocess_info_json.py` — rewrite info.json paths to container view.
2. `agent/prompt_format.py` — render prompt from `agent/prompts/<task>.json` + info.json.
3. `agent/agent.py --backend {cursor,claude,codex}` — single LLM call; emits `STATUS=` / `TOKENS_JSON=` / `RUNTIME_SECONDS=` markers on stderr.
4. (repair only) KLayout batch render -> `evaluator/run_klayout_drc.py` -> `evaluator/process_klayout_reports.py` (`.lyrpt` -> `.drc.json`) -> `evaluator/sanity_check.py` -> `evaluator/check_connectivity.py` (cell / block).
5. `evaluator/score_repair.py` or `evaluator/score_detection.py` — reads `agent_status` / `runtime_seconds` / 4 token fields from a trusted `--agent-meta` JSON (round-10 / round-14 invariant), writes per-case score JSON.
6. (repair) `evaluator/merge_score_sanity.py` + `evaluator/merge_score_connectivity.py` — merge into score JSON.
7. `evaluator/write_score_csv.py` + `evaluator/log_runtime.py` — per-case CSV + append to `logs/runtime.csv`.

All console output is also captured to `logs/<run_id>_<design_type>_<task_type>_<case_name>.log`.

## Env vars

| Variable | Default | Description |
|---|---|---|
| `WORKSPACE` | `/workspace` | Workspace root (set by Docker image ENV). |
| `SKIP_DRC` | `0` | `1` skips KLayout DRC (repair only). |
| `CLAUDE_EFFORT` | unset | **Required** for `run_pipeline_claude.sh` (e.g. `medium`, `high`); forwarded as `--effort` and folded into `run_id`. |
| `CODEX_EFFORT` | unset | **Required** for `run_pipeline_codex.sh`; forwarded as `--effort` and folded into `run_id`. |

## See also

- [`../agent/README.md`](../agent/README.md) — agent dispatcher, backends, prompt schema, example info.json.
- [`../evaluator/README.md`](../evaluator/README.md) — trusted score bundle and helpers invoked from steps 4–7.
