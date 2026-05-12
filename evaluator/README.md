# evaluator/ — Trusted score-phase bundle

Source-of-truth for the score / render / DRC / sanity / connectivity logic. Invisible to the agent phase; injected only after agent kill and network disconnect.

> **Modification policy:** **Do NOT modify** anything under `evaluator/`. This bundle is hash-verified at score-phase entry (`evaluator.sha256`) and any local edit will either fail the manifest check or silently invalidate cross-submission comparisons. Only `agent/` is user-modifiable — see [`../CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) for what you can change and the contracts your custom agent must honor.

## Trust model

- The container's agent phase **never** sees `/workspace/evaluator/`. The agent only gets a minimal `evaluator_helpers/` subset (`parse_info_json.py`, `postprocess_info_json.py`, `check_connectivity.py`) for prompt parsing and self-checks.
- Score phase entry sequence (host-side, in `lib_helpers.sh`): `kill_leftover_processes` -> `disconnect_container_network` -> `docker cp evaluator/. <cid>:/workspace/evaluator/` -> overwrite `/usr/local/bin/{bash,python3,sha256sum}-trusted` from `evaluator/trusted_bin/`. `/workspace/evaluator_helpers/` is left in place from the agent phase but is no longer trusted by scoring: `run_pipeline_*.sh` overrides `helpers_dir` to `${evaluator_dir}` when `phase=score`, so every score-phase `parse_info_json.py` / `postprocess_info_json.py` / `check_connectivity.py` call reads from the manifest-verified `/workspace/evaluator/` copy.
- Every score-phase `docker exec` is wrapped by `secured-exec.sh` and runs with `HARDENED_EVALUATION=1` and `EVALUATOR_DIR=/workspace/evaluator`. The wrapper sanitizes `EVALUATOR_HELPERS_DIR` via its env allowlist (`: "${EVALUATOR_HELPERS_DIR:=}"`), forwarding only the empty default when the agent-phase env was not propagated.
- `verify_evaluator_bundle` is the first step of the score block; it reads `evaluator.sha256` and compares each file (fail-closed exit 1).

## Files

| File | Role |
|---|---|
| `parse_info_json.py` | info.json -> shell var assignments (also exposed in agent-phase `evaluator_helpers/`). |
| `postprocess_info_json.py` | Rewrite info.json paths to container view. |
| `check_connectivity.py` | Connectivity verifier (cell / block); also exposed in agent-phase helpers for the agent's own self-check. |
| `score_repair.py` | Repair scorer (`repair_rate`, `new_violation_rate`). |
| `score_detection.py` | Detection scorer (geometry-based matching, schema validate). |
| `run_klayout_drc.py` | KLayout DRC runner. |
| `process_klayout_reports.py` | `.lyrpt` -> `.drc.json` (`--fix-dots` substitutes containing polygon bbox). |
| `sanity_check.py` | GDS integrity validator; dynamic-loads sibling `check_connectivity.py` (must stay co-located). |
| `prepare_render_script.py` | Rewrite `layout.write()` path before render. |
| `merge_score_sanity.py` / `merge_score_connectivity.py` | Merge fields into score JSON. |
| `write_score_csv.py` | Score JSON -> CSV row (None -> "NULL"; fixed fieldnames). |
| `write_invalid_score.py` | Fail-closed invalid-score emitter. |
| `log_runtime.py` | Append per-run row to `runtime.csv`. |
| `evaluator.sha256` | Manifest verified at score-phase entry by `verify_evaluator_bundle.sh`. |
| `trusted_bin/{bash,python3,sha256sum}` | GNU coreutils binaries; copied to `/usr/local/bin/*-trusted` by `reinject_critical_binaries`. `.hash` covers all three. |

## Manifest and injection sequence

```bash
# host, just before the score phase
( cd evaluator && find . -type f \( -name '*.py' -o -name '*.sh' \) \
    -not -path './trusted_bin/*' \
    | sort | xargs sha256sum > evaluator.sha256 )
```

1. Agent phase exits and `docker exec` returns.
2. Host runs `kill_leftover_processes` (`docker top` + `kill -9`).
3. Host runs `docker network disconnect`.
4. Host `docker cp evaluator/. <cid>:/workspace/evaluator/` and overwrites `bash-trusted` / `python3-trusted` / `sha256sum-trusted` from `trusted_bin/`. `/workspace/evaluator_helpers/` is left intact from the agent phase; the score block reads its helpers from `/workspace/evaluator/` (manifest-verified) instead.
5. Score block starts with `verify_evaluator_bundle` (fail-closed).

## Manifest regeneration note

**Modifying any file under `evaluator/` requires regenerating `evaluator.sha256` on the host before the next run; otherwise `verify_evaluator_bundle` fails closed at score-phase entry.**

## Score-phase invariants

1. Score-phase helpers always use absolute `/workspace/evaluator/<file>.py`; no fallback to `/workspace/src/` or `/workspace/evaluator_helpers/`.
2. `docker exec` env must carry `EVALUATOR_DIR=/workspace/evaluator` and `HARDENED_EVALUATION=1`.
3. The score block reverse-checks that `EVALUATOR_HELPERS_DIR` is empty.
4. `verify_evaluator_bundle` runs first and is fail-closed.
5. `trusted_bin/{bash,python3,sha256sum}` must be GNU coreutils format; the smoke test verifies them against `.hash`.

## Score JSON schema

Common fields (both tasks): `agent_status`, `runtime_seconds`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`.

Repair adds: `sanity_passed`, `sanity_details`, `top_cell_exists`, `gds_not_empty`, `critical_layers_preserved`, `cell_structure_intact`, `outline_boundary_respected` (cell / block; failure adds `protruding_layers`), `instance_placements_unchanged` (cell / block; failure adds `missing_instances`, `extra_instances`), `polygon_shape_counts_ok` (polygon; failure adds `shape_count_mismatches`), `connectivity_preserved` (cell / block).

Detection adds: `matching_algorithm` (`"hopcroft_karp"`), `scoring_policy` (`"geometry_required_edge_aware"`), `mercy_low` / `mercy_high` (`0.81` / `1.21`), `edge_side_tolerance` (`1.1`), `geometry_unavailable_rules`.

## See also

- [`../agent/README.md`](../agent/README.md) — agent-side trust boundary; intentionally decoupled from `evaluator/`.
- [`../src/README.md`](../src/README.md) — pipeline scripts that drive both phases.
- [`../scripts/build_trusted_bin.sh`](../scripts/build_trusted_bin.sh) — extracts `bash` / `python3` / `sha256sum` from the hardened image into `evaluator/trusted_bin/`.
