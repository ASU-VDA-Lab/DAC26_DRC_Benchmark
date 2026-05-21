# DAC 2026 DRC Benchmark

Benchmark for evaluating LLMs on ASAP7 KLayout DRC repair and detection inside a self-contained Docker container.

Two tasks are evaluated:

- **Detection** — the agent sees a layout (a KLayout Python script) **without** the golden DRC report, and must predict which design rules are violated and where (edge pairs for spacing rules, bounding boxes otherwise). Scored against the golden DRC report by Hopcroft–Karp maximum bipartite matching per rule (Precision / Recall / F1).
- **Repair** — the agent sees a layout **plus** the golden DRC report listing every violation, and must produce a modified layout script that resolves the violations. Scored by re-running KLayout DRC on the agent's output and comparing to the golden (`repair_rate`, `new_violation_rate`, `connectivity_preserved`).

## Modification policy

**Only `agent/` is user-modifiable.** Everything else (scoring code, orchestration, Docker hardening, test cases, helper scripts) is part of the frozen benchmark infrastructure; modifying it invalidates the result for cross-submission comparison.

| Directory | User may modify? | Purpose |
|---|---|---|
| `agent/` | ✅ **Yes** | Your contribution: dispatcher, backend adapters, prompt templates, `skill.md`. |
| `evaluator/` | ❌ No | Trusted scoring / render / DRC bundle. Hash-verified at score-phase entry. |
| `src/` | ❌ No | Pipeline orchestration (`run_pipeline_*.sh`, `evaluate_*.sh`, `lib_helpers.sh`). |
| `testcase/` | ❌ No | Frozen ASAP7 benchmark cases (594 total). |
| `docker/`, `Dockerfile.*`, `scripts/` | ❌ No | Container hardening + one-time setup. |
| `result/`, `score/`, `task/`, `temp/`, `logs/` | n/a | Runtime artifacts; auto-created and overwritten per run. |

**Building a custom agent?** See [`CUSTOM_AGENT.md`](./CUSTOM_AGENT.md) for the full contract: required filenames, CLI arguments your `agent.py` must accept, the stderr markers it must emit, the info.json fields available to your prompt template, and a minimum-viable skeleton.

## Quick reference

- [`Dockerfile.repair`](./Dockerfile.repair) — repair-task image (AlmaLinux 8.10 + KLayout 0.30.1 + Cursor / Claude Code / Codex CLIs).
- [`Dockerfile.detection`](./Dockerfile.detection) — detection-task image; ships without KLayout, with iptables blocklist on klayout / package-index domains so the agent cannot recover the golden DRC answer.
- [`docker/`](./docker) — entrypoint helpers (firewall + blocklist).
- [`src/`](./src) — pipeline orchestration scripts (`run_pipeline_*.sh`, `evaluate_*.sh`, `lib_helpers.sh`, `build_case_info.py`). See [`src/README.md`](./src/README.md).
- [`agent/`](./agent) — unified LLM agent layer (`agent.py` dispatcher, prompt JSON templates, `skill.md`, backends). See [`agent/README.md`](./agent/README.md).
- [`CUSTOM_AGENT.md`](./CUSTOM_AGENT.md) — contract guide for building a custom agentic flow (required filenames, CLI signature, stderr markers, info.json placeholders, minimum-viable skeleton).
- [`evaluator/`](./evaluator) — trusted score-phase bundle (DRC runner, scorers, sanity / connectivity, `compute_evaluator_hash.py`, `trusted_bin/`). See [`evaluator/README.md`](./evaluator/README.md). Token-recording backends live in `src/agent_backend/` (frozen, image-baked).
- [`testcase/`](./testcase) — ASAP7 PDK + 594 cases (`cell` 255 / `polygon` 332 / `block` 7). See [`testcase/README.md`](./testcase/README.md).
- [`CASE_STAT.md`](./CASE_STAT.md) — per-design-type and per-case statistics (violation counts, rule frequencies, die / core area).
- [`scripts/`](./scripts) — one-time setup (`build_trusted_bin.sh`, `build_seccomp_profile.sh`).
- [`example/`](./example) — pre-built `info.json` files used by the single-case Docker examples below (one per CLI / task). See [`example/README.md`](./example/README.md).
- [`result/`](./result), [`score/`](./score), [`task/`](./task), [`temp/`](./temp), [`logs/`](./logs) — runtime I/O (auto-created).

## Quick start

### Prerequisites

- **Docker** — for building and running the benchmark container.
- **Cursor CLI on the host** (for Cursor pipeline) — install and log in. The Cursor installer puts the binary on PATH as `agent` (not `cursor`):
  ```bash
  curl https://cursor.com/install -fsS | bash
  agent login
  ```
  The login credentials at `~/.config/cursor/auth.json` are bind-mounted (read-only) into the container at runtime.
- **Claude Code CLI on the host** (for Claude Code pipeline) — install and log in:
  ```bash
  curl -fsSL https://claude.ai/install.sh | bash
  claude login
  ```
  The login credentials at `~/.claude/.credentials.json` are bind-mounted (read-only) into the container at runtime.
- **Codex CLI on the host** (for Codex pipeline) — install and log in:
  ```bash
  npm install -g @openai/codex@0.124.0
  codex login
  ```
  The login credentials at `~/.codex/auth.json` are bind-mounted (read-only) into the container at runtime.
- **KLayout 0.30.1** — pre-installed in the Docker image (downloaded from klayout.org during build).
- **Python 3.6+** — pre-installed in the Docker image (standard library only; no extra pip packages required).

### 1. Build the Docker images

Two images are used:

- `drc-benchmark-repair` (full KLayout) — for repair tasks, which legitimately need to run DRC.
- `drc-benchmark-detection` (no KLayout, with iptables blocklist on klayout / package-index domains) — for detection tasks, to prevent the agent from leaking the golden DRC answer by invoking or installing KLayout.

```bash
cd DAC26_DRC_Benchmark/
docker build -f Dockerfile.repair    -t drc-benchmark-repair    .
docker build -f Dockerfile.detection -t drc-benchmark-detection .
```

Both images are AlmaLinux 8.10 with Cursor CLI + Claude Code CLI + Codex CLI pre-installed. The repair image additionally has KLayout 0.30.1, Ruby, and Qt5. The detection image has Python 3.6 and `iptables` only; download tools (`wget`, `curl`, `pip`, `yum`, `rpm`, `gcc`, `git`, `npm`, etc.) are stripped, and the entrypoint installs a runtime blocklist of klayout.org, pypi.org, github.com, etc.

### 2. Run a single test case

Run from `DAC26_DRC_Benchmark/`. Each case feeds one `info.json` (use one from [`example/`](./example) or build your own — see [`example/README.md`](./example/README.md)) through a two-phase Docker pipeline.

`run_pipeline_*.sh` accepts three modes:

| Flag | Runs | When to use |
|---|---|---|
| `--agent-only` | Prompt format → agent call → persist `.agent_meta.json` | **Phase 1** of every paper run. |
| `--score-only` | Render / DRC / sanity / connectivity (repair) or detection scorer → CSV + runtime log; score JSON embeds `evaluator_hash` | **Phase 2** of every paper run, after the host disconnect / kill / evaluator-inject handoff. |
| *(none)* | Both phases back-to-back inside one container invocation | Smoke testing only — bypasses the host-side trust-boundary handoff, so scores are **not** paper-comparable. |

Both repair and detection use the same `--agent-only` → handoff → `--score-only` split. The only difference: repair `docker cp`s the golden DRC report **before** the agent (legitimate input); detection does it **after** the kill / disconnect step (and `postprocess_info_json.py` rewrites `path_to_drc_report` to `""` for the agent).

**Canonical script** — Claude Code + repair (Cell1 cell, uses [`example/cell1_repair_claude_code.json`](./example/cell1_repair_claude_code.json)). For other CLI / task combos, only the knob block changes (Cursor + repair and Codex + detection knob blocks are listed below the main script):

| Knob | Cursor | Claude Code | Codex |
|---|---|---|---|
| `PIPELINE` | `run_pipeline_cursor.sh` | `run_pipeline_claude.sh` | `run_pipeline_codex.sh` |
| Host → container auth | `~/.config/cursor/auth.json` → `/root/.config/cursor/auth.json` | `~/.claude/.credentials.json` → `/root/.claude/.credentials.json` | `~/.codex/auth.json` → `/root/.codex/auth.json` |
| `EFFORT_ENV` (both phases) | `()` | `(-e CLAUDE_EFFORT=medium)` | `(-e CODEX_EFFORT=high)` |
| `AGENT_EXTRA_ENV` (agent only) | `()` | `(-e CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000)` | `()` |

`TASK=detection` additionally needs `--cap-add=NET_ADMIN` on `docker create` (the script below sets `NET_FLAG` from `$TASK` automatically). Run `scripts/build_seccomp_profile.sh` once on the host first to produce `docker/seccomp-no-iptables.json` — without it, the `HARDEN_FLAGS` block below errors out.

```bash
# === knobs ===
INFO_JSON=example/cell1_repair_claude_code.json
CASE=Cell1                   # must match case_name inside $INFO_JSON
DESIGN=cell                  # must match design_type inside $INFO_JSON
TASK=repair                  # must match task_type inside $INFO_JSON
PIPELINE=run_pipeline_claude.sh
AUTH_HOST="$HOME/.claude/.credentials.json"
AUTH_CONT="/root/.claude/.credentials.json"
EFFORT_ENV=(-e CLAUDE_EFFORT=medium)              # used by BOTH agent and score phases
AGENT_EXTRA_ENV=(-e CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000)  # agent phase ONLY (Claude-specific)
IMAGE="drc-benchmark-${TASK}"           # repair -> -repair, detection -> -detection
NET_FLAG=(); [[ "$TASK" == "detection" ]] && NET_FLAG=(--cap-add=NET_ADMIN)
RUN_ID="claude-sonnet-4-6-medium"       # claude / codex: ${model_name}-${effort}; cursor: ${model_name}

# Paper-grade hardening flags (mirror the `harden_flags` block in src/evaluate_claude.sh).
# Run scripts/build_seccomp_profile.sh once on the host first; produces
# docker/seccomp-no-iptables.json. Skip these three lines for a quick smoke
# test; the scores will then NOT be paper-comparable.
SECCOMP="$(pwd)/docker/seccomp-no-iptables.json"
HARDEN_FLAGS=(--cap-drop=LINUX_IMMUTABLE
              --security-opt "seccomp=${SECCOMP}"
              --security-opt no-new-privileges)

CONTAINER="drc-bench-${CASE}-${TASK}"
HOST_DIR="$(pwd)"
SEALED_DIR="$HOST_DIR/.sealed_audit/$CASE"
AGENT_STDERR="$SEALED_DIR/agent_stderr.log"
mkdir -p "$SEALED_DIR"

# Trust-boundary helpers (disconnect_container_network, kill_leftover_processes,
# reinject_critical_binaries, parse_agent_stderr, write_trusted_agent_meta,
# Source from src/ — agent/ does not see this.
source src/lib_helpers.sh

# ----- Stage container (agent/ read-only; evaluator/ NOT mounted) -----
docker create --name "$CONTAINER" "${NET_FLAG[@]}" "${HARDEN_FLAGS[@]}" \
    -v "${AUTH_HOST}:${AUTH_CONT}:ro" \
    -v "$HOST_DIR/agent:/workspace/agent:ro" \
    -v "$HOST_DIR/result:/workspace/result" \
    -v "$HOST_DIR/score:/workspace/score" \
    -v "$HOST_DIR/logs:/workspace/logs" \
    -v "$HOST_DIR/temp:/workspace/temp" \
    "$IMAGE" \
    sleep infinity
docker start "$CONTAINER"

# Use the pre-built info.json from example/. Only model_name / case_name /
# design_type / task_type are read for shell dispatch; every path_to_* /
# output_path / temp_dir is overwritten in-container by
# evaluator/postprocess_info_json.py. The relative paths inside the JSON
# are kept human-readable so you can sanity-check the case exists on disk
# (e.g. testcase/asap7/cell/layout_script/Cell1.py).
docker cp "$INFO_JSON" "$CONTAINER:/workspace/task/info.json"

# Inject the minimal helper subset the agent phase needs (parse_info_json,
# postprocess_info_json, check_connectivity for the agent's self-check).
# The full evaluator/ bundle stays out of /workspace/ until after kill.
docker exec "$CONTAINER" mkdir -p /workspace/evaluator_helpers
for f in parse_info_json.py postprocess_info_json.py check_connectivity.py; do
    docker cp "evaluator/$f" "$CONTAINER:/workspace/evaluator_helpers/$f"
done

# Repair: inject golden DRC report BEFORE the agent (legitimate input).
if [[ "$TASK" == "repair" ]]; then
    docker exec "$CONTAINER" mkdir -p "/workspace/testcase/asap7/$DESIGN/drc_report"
    docker cp "testcase/asap7/$DESIGN/drc_report/$CASE.drc.json" \
        "$CONTAINER:/workspace/testcase/asap7/$DESIGN/drc_report/"
fi

# Pre-kill: stage *-trusted copies of bash / python3 / sha256sum /
# secured-exec.sh so the post-kill helpers can reach them.
reinject_critical_binaries "$CONTAINER" "$HOST_DIR" pre-kill

# ============= Phase 1: --agent-only =============
# PYTHONDONTWRITEBYTECODE=1 prevents .pyc writes into the :ro mounted
# /workspace/agent (the pipeline also re-exports it internally as
# belt-and-suspenders). AGENT_EXTRA_ENV is included here but NOT on the
# score-phase exec below.
docker exec "${EFFORT_ENV[@]}" "${AGENT_EXTRA_ENV[@]}" \
    -e PYTHONDONTWRITEBYTECODE=1 \
    "$CONTAINER" \
    bash "src/${PIPELINE}" --agent-only /workspace/task/info.json \
    2>&1 | tee "$AGENT_STDERR"

# ============= Host-side trust-boundary handoff =============
disconnect_container_network "$CONTAINER"
kill_leftover_processes     "$CONTAINER"
reinject_critical_binaries  "$CONTAINER" "$HOST_DIR" post-kill

eval "$(parse_agent_stderr "$AGENT_STDERR")"

# Aggregate per-call token JSONs (each backend writes one to ${score_dir}/calls/<ID>.json
# during agent phase). Mandatory: if STATUS=success but no per-call file is found,
# scoring fails-closed with invalid_reason=mandatory_calls_recording_missing.
CALLS_DIR="$HOST_DIR/score/$RUN_ID/$DESIGN/$TASK/calls"
REQ=""; [[ "$agent_status" == "success" ]] && REQ="--require-files"
_agg=$(aggregate_call_tokens_for_case "$CALLS_DIR" "$CASE" \
    "$SEALED_DIR/${CASE}_tokens_combined.json" "$tokens_json" \
    "$SEALED_DIR/${CASE}_aggregate.log" "$REQ")
_src=$(printf '%s' "$_agg" | awk -F'|' '{print $3}')
if [[ "$_src" == "per_call_files" ]]; then
    tokens_json=$(printf '%s' "$_agg" | awk -F'|' '{print $1}')
    num_calls=$(printf '%s' "$_agg" | awk -F'|' '{print $2}')
elif [[ "$_src" == "mandatory_calls_recording_missing" ]]; then
    agent_status="fail"
    num_calls=0
else
    num_calls=0
fi

write_trusted_agent_meta "$SEALED_DIR/${CASE}_agent_meta.json" \
    "$agent_status" "$agent_runtime_seconds" "$tokens_json"

docker exec "$CONTAINER" mkdir -p /workspace/evaluator /workspace/temp/sealed
docker cp evaluator/. "$CONTAINER:/workspace/evaluator/"
docker cp "$SEALED_DIR/${CASE}_agent_meta.json" \
    "$CONTAINER:/workspace/temp/sealed/${CASE}_agent_meta.json"

# Detection: inject golden DRC report ONLY NOW (after kill + disconnect).
if [[ "$TASK" == "detection" ]]; then
    docker exec "$CONTAINER" mkdir -p "/workspace/testcase/asap7/$DESIGN/drc_report"
    docker cp "testcase/asap7/$DESIGN/drc_report/$CASE.drc.json" \
        "$CONTAINER:/workspace/testcase/asap7/$DESIGN/drc_report/"
fi

# ============= Phase 2: --score-only (HARDENED_EVALUATION=1 + EVALUATOR_DIR
# + TRUSTED_PYTHON satisfy the score-phase invariants in run_pipeline_*.sh;
# NUM_CALLS is forwarded into the runtime.csv num_calls column). =============
docker exec "${EFFORT_ENV[@]}" \
    -e HARDENED_EVALUATION=1 \
    -e EVALUATOR_DIR=/workspace/evaluator \
    -e TRUSTED_PYTHON=/usr/local/bin/python3-trusted \
    -e "NUM_CALLS=${num_calls:-0}" \
    "$CONTAINER" \
    bash "src/${PIPELINE}" --score-only /workspace/task/info.json

docker rm -f "$CONTAINER"
```

The block above is **Claude Code + repair** (Cell1 on the cell design). For other CLI / task combinations, the rest of the script is unchanged — just swap the knobs at the top.

**Cursor + repair** (uses [`example/cell1_repair_cursor.json`](./example/cell1_repair_cursor.json)):

```bash
# === knobs (Cursor repair) ===
INFO_JSON=example/cell1_repair_cursor.json
CASE=Cell1
DESIGN=cell                  # cell | polygon | block
TASK=repair                  # repair | detection
PIPELINE=run_pipeline_cursor.sh
AUTH_HOST="$HOME/.config/cursor/auth.json"
AUTH_CONT="/root/.config/cursor/auth.json"
EFFORT_ENV=()                            # Cursor CLI has no --effort
AGENT_EXTRA_ENV=()                       # no Cursor-specific agent extras
IMAGE="drc-benchmark-${TASK}"           # resolves to drc-benchmark-repair
NET_FLAG=(); [[ "$TASK" == "detection" ]] && NET_FLAG=(--cap-add=NET_ADMIN)
RUN_ID="gpt-5.4-high"                    # cursor: run_id == model_name verbatim
```

**Codex + detection** (uses [`example/cell1_detection_codex.json`](./example/cell1_detection_codex.json)):

```bash
# === knobs (Codex detection) ===
INFO_JSON=example/cell1_detection_codex.json
CASE=Cell1
DESIGN=cell                  # cell | polygon | block
TASK=detection               # repair | detection
PIPELINE=run_pipeline_codex.sh
AUTH_HOST="$HOME/.codex/auth.json"
AUTH_CONT="/root/.codex/auth.json"
EFFORT_ENV=(-e CODEX_EFFORT=high)        # used by BOTH agent and score phases
AGENT_EXTRA_ENV=()                       # no Codex-specific agent extras
IMAGE="drc-benchmark-${TASK}"           # resolves to drc-benchmark-detection
NET_FLAG=(); [[ "$TASK" == "detection" ]] && NET_FLAG=(--cap-add=NET_ADMIN)
RUN_ID="gpt-5.4-high"                    # codex: ${model_name}-${codex_effort}
```

**Output locations:** `score/<run_id>/<design>/<task>/<case>_score.json` (each carries an `evaluator_hash` field), trusted `.sealed_audit/<case>/agent_meta.json`, and a per-run row appended to `logs/runtime.csv`. For prompt iteration where paper-comparable scores don't matter, pre-inject the full `evaluator/` bundle and run `bash src/${PIPELINE} /workspace/task/info.json` (no flag) — Full mode bypasses the trust-boundary handoff.

### 3. Reproduce paper experiments

`evaluate_cursor.sh` (Cursor), `evaluate_claude.sh` (Claude Code), and `evaluate_codex.sh` (Codex) reproduce the experiments in the paper. They automate `info.json` generation, Docker container lifecycle, and golden DRC report injection across all task / model / case combinations. Edit the `CASES` array in the script to control which cases are swept.

```bash
bash src/evaluate_cursor.sh          # Cursor Agent CLI
bash src/evaluate_claude.sh          # Claude Code CLI
bash src/evaluate_codex.sh           # Codex CLI
```

## Pipeline architecture

```
host (evaluate_*.sh)
  -> docker create + cp info.json
  -> agent phase   : run_pipeline_*.sh -> agent/agent.py --backend <b>
                     (evaluator/ NOT mounted; iptables blocklist active for detection)
  -> kill leftover, network disconnect, docker cp evaluator/. + trusted_bin
  -> score phase   : embed evaluator_hash into score JSON
                     -> render (repair) -> KLayout DRC -> sanity / connectivity
                     -> score_repair.py | score_detection.py -> CSV + runtime.csv
```

**Per-call token recording (mandatory):** every agent backend writes one `${AGENT_CALLS_DIR}/<ID>.json` per LLM call, where `<ID>=${case_name}_${call_seq:04d}_<sha8>` (flat directory shared across cases). Each per-call JSON carries the four-key totals plus a `by_model` breakdown — Claude Code's haiku subagent tokens are recorded under their own model key. After the agent is killed, `evaluator/aggregate_call_tokens.py` (called by the host via `aggregate_call_tokens_for_case` in `src/lib_helpers.sh`) sums totals and forwards `n_call_ids_valid` to the `num_calls` column of `logs/runtime.csv`. Fail-closed: if `STATUS=success` but zero per-call files exist for the case, `write_invalid_score.py` emits a null score with `invalid_reason=mandatory_calls_recording_missing`. Central writer: `src/agent_backend/per_call_writer_helpers.py`. Full contract: [`CUSTOM_AGENT.md`](./CUSTOM_AGENT.md) §"Per-call token recording".

Step-level details live in [`src/README.md`](./src/README.md); trusted-bundle internals in [`evaluator/README.md`](./evaluator/README.md).

## Trust boundary index

- Agent phase and score phase are strictly separated; the agent never sees `/workspace/evaluator/`.
- For detection cases, `evaluator/postprocess_info_json.py` rewrites `path_to_drc_report` to the empty string in the agent-visible info.json — the gate that keeps the detection agent from reading the golden DRC report.
- `Dockerfile.detection` ships without KLayout / wget / curl / pip / yum / git; entrypoint installs an iptables OUTPUT REJECT list on klayout.org / pypi.org / github.com / etc., then drops `NET_ADMIN` from the bounding set.
- All score-phase `docker exec` calls go through `secured-exec.sh` with `HARDENED_EVALUATION=1` and `EVALUATOR_DIR=/workspace/evaluator`.
- Each per-case score JSON carries an additive `evaluator_hash` field (multi-line sha256sum-style) recording which evaluator bundle produced that score. Pipeline does not verify at runtime; cross-host reproducibility check is reader-side.
- `evaluator/trusted_bin/{bash,python3,sha256sum}` are re-injected over `*-trusted` paths after agent kill, so a tampered `/bin/bash` cannot subvert score-phase execution.

Full definitions and injection sequence: [`evaluator/README.md`](./evaluator/README.md). Agent-side contract: [`agent/README.md`](./agent/README.md).

## Scoring

Repair metrics (golden `.drc.json` vs repaired `.drc.json` from re-running KLayout):

| Metric | Formula |
|---|---|
| `repair_rate` | `removed_violations / original_violations` |
| `new_violation_rate` | `new_violations / original_violations` |
| `connectivity_preserved` | shape-aware DFS on golden connectivity JSON (cell / block) |

Detection metrics (predicted DRV regions vs golden, geometry-based, Hopcroft-Karp maximum bipartite matching per rule):

| Metric | Formula |
|---|---|
| `Precision` | `sum(TP) / (sum(TP) + sum(FP))` |
| `Recall` | `sum(TP) / (sum(TP) + sum(FN))` |
| `F1` | harmonic mean |

Match: polygon golden bbox needs overlap and area ratio in `[0.81, 1.21]`; edge golden bbox needs both endpoints inside the predicted bbox and predicted longest side `<= edge_length * 1.1`. Score JSON schema (per-key descriptions) lives in [`evaluator/README.md`](./evaluator/README.md).

## Results

| Task | Metric | (Claude Code) Claude 4.6 Opus - High Effort | | | | | | (Claude Code) Claude 4.6 Sonnet - Medium Effort | | | | | | (Cursor) Claude 4.6 Opus - High Effort | | | | | | (Cursor) Claude 4.6 Sonnet - Medium Effort | | | | | | (Codex) GPT 5.4 - High Effort | | | | | | (Cursor) GPT 5.4 - High Effort | | | | | | (Cursor) Gemini 3.1 Pro | | | | | | (Cursor) Grok 4-20 | | | | | | (Cursor) Kimi K2.5 | | | | | |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | B7 | B5 | C228 | C1 | P263 | P69 | B7 | B5 | C228 | C1 | P263 | P69 | B7 | B5 | C228 | C1 | P263 | P69 | B7 | B5 | C228 | C1 | P263 | P69 | B7 | B5 | C228 | C1 | P263 | P69 | B7 | B5 | C228 | C1 | P263 | P69 | B7 | B5 | C228 | C1 | P263 | P69 | B7 | B5 | C228 | C1 | P263 | P69 | B7 | B5 | C228 | C1 | P263 | P69 |
| Detect | Precision | 0.12 | 0.01 | 0.00 | 0.25 | 1.00 | 1.00 | 0.03 | 1.00 | 1.00 | 0.30 | 1.00 | 1.00 | 0.07 | 0.00 | 0.39 | 0.87 | 1.00 | 1.00 | 0.00 | 0.95 | 1.00 | 1.00 | 1.00 | 0.00 | 0.56 | 0.70 | 1.00 | 1.00 | 1.00 | 1.00 | 0.78 | 0.95 | 1.00 | 0.26 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.78 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.83 | 0.18 | 0.50 | 0.00 |
| | Recall | 0.10 | 0.03 | 0.00 | 0.15 | 1.00 | 1.00 | 0.04 | 0.01 | 0.95 | 1.00 | 1.00 | 1.00 | 0.01 | 0.00 | 0.95 | 1.00 | 1.00 | 1.00 | 0.00 | 0.52 | 0.95 | 0.15 | 1.00 | 0.00 | 0.58 | 0.65 | 0.84 | 0.85 | 1.00 | 1.00 | 0.68 | 0.59 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.52 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.53 | 0.85 | 0.50 | 0.00 |
| | F1 | 0.11 | 0.02 | 0.00 | 0.19 | 1.00 | 1.00 | 0.04 | 0.03 | 0.97 | 0.46 | 1.00 | 1.00 | 0.03 | 0.00 | 0.55 | 0.93 | 1.00 | 1.00 | 0.00 | 0.67 | 0.97 | 0.27 | 1.00 | 0.00 | 0.57 | 0.67 | 0.91 | 0.92 | 1.00 | 1.00 | 0.73 | 0.73 | 1.00 | 0.41 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.62 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.65 | 0.30 | 0.50 | 0.00 |
| | Runtime (s) | 3,023 | 1,246 | 3,915 | 3,102 | 217 | 908 | 1,065 | 703 | 557 | 733 | 140 | 430 | 4,618 | 1,614 | 845 | 1,015 | 153 | 460 | 5,841 | 626 | 641 | 504 | 140 | 311 | 821 | 683 | 372 | 385 | 146 | 279 | 2,347 | 1,084 | 248 | 582 | 117 | 202 | 228 | 51 | 22 | 450 | 49 | 127 | 32 | 78 | 32 | 96 | 37 | 38 | 216 | 203 | 177 | 133 | 35 | 115 |
| | Input Token | 169(79) | 321K(318K) | 166K(164K) | 2.8K(18) | 2.8K(14) | 2.8K(14) | 73(73) | 42(42) | 33(33) | 7.6K(7.6K) | 19(19) | 15K(15K) | 222 | 106 | 31 | 30 | 19 | 19 | 82 | 17 | 27 | 31 | 22 | 19 | 3.5M | 4.3M | 1.3M | 1.2M | 682K | 854K | 214K | 145K | 90K | 85K | 98K | 75K | 123K | 51K | 34K | 238K | 48K | 109K | 112K | 74K | 77K | 85K | 139K | 126K | 0 | 0 | 0 | 0 | 0 | 0 |
| | Cache Read | 7.4M(5.5M) | 6.2M(6.2M) | 810K(810K) | 1.3M(1.3M) | 400K(400K) | 1.1M(1.1M) | 6.2M(6.2M) | 2.1M(2.1M) | 2.1M(2.1M) | 2.2M(2.2M) | 382K(382K) | 698K(698K) | 19M | 8.7M | 2.8M | 2.8M | 1.2M | 1.1M | 5.8M | 1.2M | 2.2M | 2.5M | 1.3M | 1.0M | 3.2M | 4.1M | 1.1M | 1.0M | 555K | 753K | 4.6M | 1.3M | 974K | 521K | 513K | 488K | 0 | 0 | 0 | 0 | 0 | 0 | 1.2M | 2.7M | 837K | 2.4M | 1.2M | 1.0M | 1.4M | 2.9M | 1.6M | 797K | 328K | 755K |
| | Cache Write | 627K(436K) | 397K(397K) | 140K(140K) | 140K(140K) | 38K(38K) | 120K(120K) | 395K(395K) | 386K(386K) | 131K(131K) | 135K(135K) | 40K(40K) | 80K(80K) | 740K | 386K | 124K | 132K | 79K | 172K | 624K | 220K | 127K | 123K | 67K | 94K | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | 514K | 1.1M | 862K | 582K | 124K | 477K |
| | Output Token | 152K(129K) | 65K(65K) | 232K(232K) | 129K(129K) | 12K(12K) | 54K(54K) | 85K(85K) | 54K(54K) | 48K(48K) | 58K(58K) | 8K(8K) | 28K(28K) | 177K | 66K | 52K | 60K | 6K | 23K | 57K | 4K | 57K | 42K | 9K | 20K | 37K | 28K | 16K | 19K | 6.4K | 13K | 35K | 18K | 11K | 28K | 5.6K | 10K | 503 | 301 | 271 | 4.5K | 814 | 482 | 938 | 6.9K | 1.1K | 9.0K | 1.2K | 2.3K | 17K | 21K | 25K | 22K | 4.1K | 14K |
| Repair | Repair Rate | 0.30 | -- | 1.00 | 1.00 | 1.00 | 1.00 | 0.63 | 0.46 | 0.26 | 1.00 | 1.00 | 1.00 | -- | 0.44 | 1.00 | 1.00 | 1.00 | 1.00 | 0.31 | -- | 1.00 | 1.00 | 1.00 | 1.00 | 0.32 | 0.26 | 0.05 | 1.00 | 1.00 | 1.00 | 0.20 | 0.35 | 1.00 | 1.00 | 1.00 | 1.00 | -- | -- | 0.16 | 1.00 | 1.00 | 1.00 | -- | -- | 0.16 | 0.15 | 0.50 | 0.00 | -- | -- | 0.05 | 0.92 | 1.00 | 0.00 |
| | New Violation Rate | 0.36 | -- | 0.00 | 0.00 | 0.00 | 0.00 | 0.14 | 2.12 | 0.00 | 0.00 | 0.00 | 0.00 | -- | 0.43 | 0.00 | 0.00 | 0.00 | 0.00 | 9.34 | -- | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.07 | 0.00 | 0.00 | 0.00 | 0.00 | 0.11 | 0.24 | 0.00 | 0.00 | 0.00 | 0.00 | -- | -- | 0.05 | 0.00 | 0.00 | 3.00 | -- | -- | 0.42 | 1.62 | 0.00 | 1.00 | -- | -- | 0.00 | 4.23 | 0.50 | 1.00 |
| | Runtime (s) | 5,281 | 7,879 | 1,684 | 1,055 | 225 | 1,146 | 1,740 | 1,493 | 3,852 | 3,121 | 182 | 1,003 | 7,211 | 2,496 | 995 | 983 | 167 | 572 | 1,840 | 4,303 | 1,025 | 794 | 128 | 301 | 2,039 | 1,517 | 965 | 688 | 174 | 648 | 2,342 | 820 | 438 | 428 | 192 | 385 | 658 | 3,931 | 161 | 540 | 86 | 125 | 99 | 76 | 101 | 86 | 39 | 46 | 2,532 | 3,170 | 76 | 264 | 39 | 28 |
| | Input Token | 2.4K(2K) | 8.2K(8.2K) | 16(16) | 6.8K(6.8K) | 13(13) | 9(9) | 167K(167K) | 109K(109K) | 294K(294K) | 18(18) | 14(14) | 10(10) | 250 | 101 | 44 | 47 | 17 | 26 | 19 | 130 | 36 | 36 | 17 | 18 | 12.1M | 12.9M | 3.1M | 2.4M | 903K | 4.8M | 167K | 279K | 145K | 134K | 57K | 82K | 191K | 21K | 125K | 143K | 70K | 65K | 229K | 142K | 132K | 119K | 55K | 83K | 0 | 0 | 0 | 0 | 0 | 0 |
| | Cache Read | 9.3M(7M) | 11.5M(11.5M) | 1.5M(1.5M) | 1.1M(1.1M) | 251K(251K) | 382K(382K) | 1.1M(1.1M) | 1.5M(289K) | 1.5M(1.5M) | 940K(940K) | 336K(336K) | 520K(520K) | 19M | 9.4M | 5.4M | 5.3M | 474K | 1.2M | 515K | 10.6M | 3.7M | 4.3M | 932K | 1.1M | 11.6M | 12.5M | 2.9M | 2.2M | 744K | 4.6M | 5.6M | 4.6M | 1.2M | 1.4M | 472K | 410K | 0 | 0 | 0 | 0 | 0 | 0 | 1.4M | 882K | 781K | 1.3M | 1.1M | 506K | 6.3M | 2.8M | 1.1M | 1.1M | 398K | 209K |
| | Cache Write | 1M(724K) | 1.5M(1.5M) | 152K(152K) | 127K(127K) | 32K(32K) | 87K(87K) | 169K(169K) | 151K(82K) | 208K(208K) | 134K(134K) | 29K(29K) | 88K(88K) | 1.7M | 619K | 174K | 289K | 25K | 68K | 50K | 217K | 293K | 235K | 67K | 93K | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | 1.8M | 1.1M | 679K | 561K | 192K | 119K |
| | Output Token | 311K(261K) | 464K(464K) | 100K(100K) | 66K(66K) | 11K(11K) | 58K(58K) | 108K(108K) | 111K(104K) | 244K(244K) | 210K(210K) | 14K(14K) | 64K(64K) | 290K | 110K | 49K | 48K | 7K | 27K | 4K | 122K | 81K | 60K | 8K | 20K | 68K | 59K | 47K | 28K | 6.6K | 21K | 46K | 42K | 26K | 27K | 9.3K | 12K | 1.9K | 197 | 9.9K | 9.5K | 2K | 2.4K | 13K | 10K | 15K | 11K | 2.0K | 4.1K | 28K | 109K | 13K | 49K | 5.5K | 2.6K |

**Notes:** Cases: B = Block, C = Cell, P = Polygon. **--**: Failed to produce a valid GDSII or preserve connectivity. Claude Code hardcodes the subagent to Claude 4.5 Haiku; in each token-count entry, the first number is the total and the number in parentheses is the Opus/Sonnet count. Cache write tokens are not available for Gemini, Grok, and GPT models (Cursor and Codex).

## See also

- [`src/README.md`](./src/README.md) — pipeline orchestration scripts.
- [`agent/README.md`](./agent/README.md) — agent dispatcher, prompts, trust-boundary contract.
- [`evaluator/README.md`](./evaluator/README.md) — trusted score-phase bundle, score JSON schema with `evaluator_hash`, full hardening invariants.
- [`testcase/README.md`](./testcase/README.md) — ASAP7 PDK and benchmark cases.
