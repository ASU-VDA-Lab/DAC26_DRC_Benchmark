# agent/ — Unified LLM agent layer

Agent dispatcher, prompt JSON templates, and `skill.md` — the agent-side of the trust boundary, fully decoupled from `evaluator/`.

> **Modification policy:** `agent/` is the **only** user-modifiable directory in this benchmark. You may freely add backends, edit prompts, tune the dispatcher, or extend `skill.md`. Every other directory (`evaluator/`, `src/`, `testcase/`, `docker/`, `scripts/`, `Dockerfile.*`) is frozen infrastructure and must not be patched — modifying it invalidates cross-submission comparisons.
>
> **Building your own agent?** Read [`../CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) for the complete contract: required filenames, the CLI signature your `agent.py` must accept, the stderr markers it must emit, the info.json fields available to your prompt template, and a minimum-viable skeleton.

## Quick reference

- `agent.py` — unified dispatcher. Single entry point for `run_pipeline_*.sh`; selects backend via `--backend {claude,codex,cursor}`.
- `prompt_format.py` — JSON-template -> plain-text prompt renderer (uses `string.Template` + `_SafeDict`).
- `skill.md` — ASAP7 DRC knowledge handed to the agent via `path_to_skill` (kept as Markdown, not JSON).
- Backend modules live in `src/agent_backend/` (frozen, image-baked). See `CUSTOM_AGENT.md` "Backend CLI invariants (frozen)".
- `prompts/{detection,repair_cell,repair_block,repair_polygon}.json` — prompt templates (one per task).
- `__init__.py` is an explicit empty package marker; do not switch to PEP 420 namespace packages — name collisions break the dispatcher.
- `AGENT_CALLS_DIR` (env var, exported by `run_pipeline_*.sh` during the agent phase, set to `${score_dir}/calls/`) — flat directory where each backend writes one per-call JSON named `${case_name}_${call_seq:04d}_<sha8>.json`. The host's post-kill aggregator (`evaluator/aggregate_call_tokens.py`) sums the four-key token totals and the `by_model` breakdown, and records `num_calls` in `runtime.csv`. Per-case score JSON carries an `evaluator_hash` field. Full contract: [`../CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) §"Per-call token recording".

## Trust boundary

- `/workspace/agent/` is mounted **read-only**; the agent cannot rewrite its own prompts or skill.
- `/workspace/evaluator/` is the canonical name of the trusted score bundle and is **invisible** during the agent phase — host-side `docker cp` injects it only after agent kill + network disconnect (see [`../evaluator/README.md`](../evaluator/README.md)).
- During the agent phase, the prompt may instruct the agent to run `python3 /workspace/evaluator_helpers/check_connectivity.py ...`; that path is the minimal helpers subset carved out of `evaluator/check_connectivity.py`. The agent cannot modify it; the source-of-truth is `evaluator/`.
- `/workspace/result/`, `/workspace/score/`, `/workspace/temp/`, `/workspace/logs/` are read-write for the agent. `/workspace/task/` is populated by the host via `docker cp` and rewritten in-container by `evaluator/postprocess_info_json.py`.

## See also

- [`../CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) — how to build a custom agent that satisfies the frozen pipeline's contracts (CLI args, stderr markers, output schema, info.json placeholders, sample skeleton).
- [`../evaluator/README.md`](../evaluator/README.md) — score-phase bundle, `HARDENED_EVALUATION` / `secured-exec.sh` / `evaluator_hash` contract.
- [`../src/README.md`](../src/README.md) — pipeline scripts that drive `agent.py`.
