# example/ — Pre-built `info.json` files for the single-case examples

The single-case Docker examples in the root [`README.md`](../README.md) (Section: "Run a single test case") `docker cp` one of these JSON files into `/workspace/task/info.json` inside the container. Use them so the example is self-contained and you do not need to run `src/build_case_info.py` by hand.

Each file mirrors what `build_case_info.py` would produce for that case, but with **relative** paths (so the file is portable across machines).

## Files

| File | Pipeline | Model (via that CLI) | Task | Case | Design | DRC rule |
|---|---|---|---|---|---|---|
| [`cell1_repair_claude_code.json`](./cell1_repair_claude_code.json) | `run_pipeline_claude.sh` | `claude-sonnet-4-6` | repair | `Cell1` | `cell` | `asap7_cell.lydrc` |
| [`cell1_repair_cursor.json`](./cell1_repair_cursor.json) | `run_pipeline_cursor.sh` | `gpt-5.4-high` | repair | `Cell1` | `cell` | `asap7_cell.lydrc` |
| [`cell1_detection_codex.json`](./cell1_detection_codex.json) | `run_pipeline_codex.sh` | `gpt-5.4` | detection | `Cell1` | `cell` | `asap7_cell.lydrc` |

Note that `cell1_repair_cursor.json` runs **GPT-5.4 through the Cursor Agent CLI** — Cursor is a multi-model CLI, so the same pipeline (`run_pipeline_cursor.sh`) can dispatch to any of `claude-4.6-opus-high`, `claude-4.6-sonnet-medium`, `gpt-5.4-high`, `gemini-3.1-pro`, `grok-4-20`, `kimi-k2.5` (see `MODEL_NAMES` in `src/evaluate_cursor.sh`). To run a different Cursor-supported model, just change the `model_name` field.

## Required fields

The pipeline (`evaluator/parse_info_json.py`) reads only **four** keys for shell dispatch:

| Key | Allowed values |
|---|---|
| `model_name` | Any string the chosen CLI accepts (`claude-sonnet-4-6`, `gpt-5.4-high`, `gpt-5.4`, ...) |
| `case_name` | One of the names under `testcase/asap7/<design>/layout_script/` (e.g. `Cell1`, `Polygon69`, `Block1`) |
| `design_type` | `cell` \| `polygon` \| `block` |
| `task_type` | `repair` \| `detection` |

## Overwritten fields (any value works — pipeline rewrites them)

Every `path_to_*`, `output_path`, and `temp_dir` value below is overwritten in-container by `evaluator/postprocess_info_json.py` with paths computed from the four required fields and from `run_pipeline_*.sh`'s CLI arguments. The shipped JSON values are kept human-readable (e.g. `agent/skill.md` instead of `""`) so you can sanity-check that the case actually exists on disk — but the pipeline never reads them.

| Field | Rewritten in-container to |
|---|---|
| `path_to_skill` | `/workspace/agent/skill.md` |
| `path_to_layout_script` | `/workspace/testcase/asap7/<design>/layout_script/<case>.py` |
| `path_to_layout_screenshot` | `/workspace/testcase/asap7/<design>/layout_screenshot/<case>/<case>.png` |
| `path_to_drc_report` | golden `.drc.json` path (repair) or `""` (detection — gate that keeps the agent from seeing the golden answer) |
| `path_to_design_rule` | `/workspace/testcase/asap7/asap7_cell.lydrc` (cell) or `/workspace/testcase/asap7/asap7.lydrc` (polygon / block) |
| `path_to_drm_jpg` | `/workspace/testcase/asap7/drm_jpg` |
| `path_to_connectivity_file` | `/workspace/testcase/asap7/<design>/connectivity/<case>.json` — **conditional**: only rewritten if the key is already present in the JSON. Include it for cell / block, omit it for polygon. |
| `output_path` | `/workspace/result/<run_id>/<design>/<task>/<case>/<case>_<suffix>` — `_repaired.py` for repair, `_detection.json` for detection |
| `temp_dir` | `/workspace/temp/<run_id>_<design>_<task>_<case>_$$` |

Note the **conditional** on `path_to_connectivity_file`: its **presence** in the JSON is the gate that triggers the connectivity check downstream (run for cell / block; skipped for polygon). The string value is overwritten regardless.

## Customising the case

To run a different case, copy one of these files and edit the four required keys. Update `path_to_*` to match for clarity (they are still overwritten, but readers expect them to line up with `case_name` / `design_type`):

```bash
cp example/cell1_repair_claude_code.json my_info.json
# edit my_info.json -> { "case_name": "Polygon69", "design_type": "polygon",
#                       "path_to_design_rule": "testcase/asap7/asap7.lydrc",
#                       "path_to_layout_script": ".../polygon/layout_script/Polygon69.py",
#                       ... and DELETE path_to_connectivity_file (polygon has no connectivity) }
```

Then `docker cp my_info.json "$CONTAINER:/workspace/task/info.json"` in place of the example's `docker cp example/...`.

## Mapping to the actual `evaluate_*.sh` flow

For each CLI, the in-container `docker exec` env vars during the agent phase differ slightly:

| CLI | Agent-phase env | Score-phase env |
|---|---|---|
| Claude Code | `CLAUDE_EFFORT`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000`, `PYTHONDONTWRITEBYTECODE=1` | `CLAUDE_EFFORT`, `HARDENED_EVALUATION=1`, `EVALUATOR_DIR=/workspace/evaluator`, `TRUSTED_PYTHON=/usr/local/bin/python3-trusted` |
| Cursor | `PYTHONDONTWRITEBYTECODE=1` (no effort env — Cursor's CLI has no `--effort` flag) | `HARDENED_EVALUATION=1`, `EVALUATOR_DIR=/workspace/evaluator`, `TRUSTED_PYTHON=/usr/local/bin/python3-trusted` |
| Codex | `CODEX_EFFORT`, `PYTHONDONTWRITEBYTECODE=1` | `CODEX_EFFORT`, `HARDENED_EVALUATION=1`, `EVALUATOR_DIR=/workspace/evaluator`, `TRUSTED_PYTHON=/usr/local/bin/python3-trusted` |

The single-case example in the root README handles this via the `EFFORT_ENV=(...)` array per CLI — an empty array for Cursor expands to nothing, so the same `docker exec "${EFFORT_ENV[@]}" -e PYTHONDONTWRITEBYTECODE=1 ...` line works for all three.

## See also

- [`../README.md`](../README.md) — "Run a single test case" section uses these files.
- [`../src/build_case_info.py`](../src/build_case_info.py) — what `evaluate_*.sh` calls to produce a richer info.json for paper runs (with absolute paths and the same key set).
- [`../CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) — "info.json fields available to your prompt template" section, with the full placeholder list a custom prompt can reference.
