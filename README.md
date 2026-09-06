# DAC 2026 DRC Benchmark

Benchmark for evaluating LLMs on ASAP7 KLayout DRC repair and detection inside a self-contained Docker container.

## Release

[![GitHub tag](https://img.shields.io/github/v/tag/ASU-VDA-Lab/DAC26_DRC_Benchmark)](https://github.com/ASU-VDA-Lab/DAC26_DRC_Benchmark/tree/v1)

[![GitHub tag](https://img.shields.io/github/v/tag/bingyuew/DAC26_DRC_Benchmark)](https://github.com/bingyuew/DAC26_DRC_Benchmark/tree/v2) Fix OpenROAD pdngen issue causing ASAP7 PDN via structure DRC violations. Refer to [change log](./change_log_v2.md) for details.

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
| `--score-only` | Render / DRC / sanity / connectivity (repair) or detection scorer; score JSON embeds `evaluator_hash`. When `RECORD_TOKENS=1`, the 4 token fields and `num_calls` are also embedded in `score.json`. | **Phase 2** of every paper run, after the host disconnect / kill / evaluator-inject handoff. |
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
RECORD_TOKENS=1                          # 1: record per-call tokens; 0 (default): skip them

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
    -e "RECORD_TOKENS=${RECORD_TOKENS}" \
    "$CONTAINER" \
    bash "src/${PIPELINE}" --agent-only /workspace/task/info.json \
    2>&1 | tee "$AGENT_STDERR"

# ============= Host-side trust-boundary handoff =============
disconnect_container_network "$CONTAINER"
kill_leftover_processes     "$CONTAINER"
reinject_critical_binaries  "$CONTAINER" "$HOST_DIR" post-kill

eval "$(parse_agent_stderr "$AGENT_STDERR")"

# Aggregate per-call token JSONs (each backend writes one to ${score_dir}/calls/<ID>.json
# during agent phase). Opt-in: skipped entirely when RECORD_TOKENS != 1.
num_calls=0
if [[ "${RECORD_TOKENS:-0}" == "1" ]]; then
    CALLS_DIR="$HOST_DIR/score/$RUN_ID/$DESIGN/$TASK/calls"
    _agg=$(aggregate_call_tokens_for_case "$CALLS_DIR" "$CASE" \
        "$SEALED_DIR/${CASE}_tokens_combined.json" "$tokens_json" \
        "$SEALED_DIR/${CASE}_aggregate.log")
    _src=$(printf '%s' "$_agg" | awk -F'|' '{print $3}')
    if [[ "$_src" == "per_call_files" ]]; then
        tokens_json=$(printf '%s' "$_agg" | awk -F'|' '{print $1}')
        num_calls=$(printf '%s' "$_agg" | awk -F'|' '{print $2}')
    fi
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
# RECORD_TOKENS toggles emission of the 4 token fields + num_calls in
# score.json; NUM_CALLS is forwarded into the scorer's --num-calls flag). =============
docker exec "${EFFORT_ENV[@]}" \
    -e HARDENED_EVALUATION=1 \
    -e EVALUATOR_DIR=/workspace/evaluator \
    -e TRUSTED_PYTHON=/usr/local/bin/python3-trusted \
    -e "RECORD_TOKENS=${RECORD_TOKENS}" \
    -e "NUM_CALLS=${num_calls:-0}" \
    "$CONTAINER" \
    bash "src/${PIPELINE}" --score-only /workspace/task/info.json

docker rm -f "$CONTAINER"
```

The block above is **Claude Code + repair** (Cell1 on the cell design). For other CLI / task combinations, the rest of the script is unchanged — just swap the knobs at the top.

**Token recording is opt-in.** Set `RECORD_TOKENS=0` (the default) on the host to skip the per-call backend writes, the aggregator helper, and the 4 token fields + `num_calls` in `score.json`. With `RECORD_TOKENS=0` the same canonical script runs unchanged — the `-e "RECORD_TOKENS=${RECORD_TOKENS}"` env propagation in both `docker exec` blocks short-circuits the recording pipeline inside the container. See §"Pipeline architecture" below for the full ON/OFF behaviour matrix.

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

**Output locations:** `score/<run_id>/<design>/<task>/<case>_score.json` (each carries an `evaluator_hash` field) and trusted `.sealed_audit/<case>/agent_meta.json`. No CSV outputs are produced. For prompt iteration where paper-comparable scores don't matter, pre-inject the full `evaluator/` bundle and run `bash src/${PIPELINE} /workspace/task/info.json` (no flag) — Full mode bypasses the trust-boundary handoff.

### 3. Reproduce paper experiments

`evaluate_cursor.sh` (Cursor), `evaluate_claude.sh` (Claude Code), and `evaluate_codex.sh` (Codex) reproduce the experiments in the paper. They automate `info.json` generation, Docker container lifecycle, and golden DRC report injection across all task / model / case combinations. Edit the `CASES` array in the script to control which cases are swept.

**To match the paper's score JSON (with token counts and per-call breakdown), set `RECORD_TOKENS=1`** — token recording is opt-in (default off):

```bash
RECORD_TOKENS=1 bash src/evaluate_cursor.sh   # Cursor Agent CLI
RECORD_TOKENS=1 bash src/evaluate_claude.sh   # Claude Code CLI
RECORD_TOKENS=1 bash src/evaluate_codex.sh    # Codex CLI
```

Without `RECORD_TOKENS=1`, the runs still produce a valid `*_score.json` per case (with `agent_status`, `valid_*`, metrics, and `evaluator_hash`) — only the four token fields, `num_calls`, and the per-call `calls/` subdirectory are skipped.

## Pipeline architecture

```
host (evaluate_*.sh)
  -> docker create + cp info.json
  -> agent phase   : run_pipeline_*.sh -> agent/agent.py --backend <b>
                     (evaluator/ NOT mounted; iptables blocklist active for detection)
  -> kill leftover, network disconnect, docker cp evaluator/. + trusted_bin
  -> score phase   : embed evaluator_hash into score JSON
                     -> render (repair) -> KLayout DRC -> sanity / connectivity
                     -> score_repair.py | score_detection.py -> score.json
```

**Per-call token recording (opt-in):** set `RECORD_TOKENS=1` to record one `${AGENT_CALLS_DIR}/<ID>.json` per LLM call, where `<ID>=${case_name}_${call_seq:04d}_<sha8>` (flat directory shared across cases). Each per-call JSON carries the four-key totals plus a `by_model` breakdown. After the agent is killed, `evaluator/aggregate_call_tokens.py` (called by the host via `aggregate_call_tokens_for_case` in `src/lib_helpers.sh`) sums totals and the scorer emits the 4 token fields plus `num_calls` directly into `score.json`. Best-effort: if `RECORD_TOKENS=1` but zero per-call files were recorded, the 4 token fields and `num_calls` become the string sentinel `"WARN: no per-call files recorded"`. With `RECORD_TOKENS=0` (default) the entire recording stack is skipped and the 4 token fields + `num_calls` are omitted from `score.json`. Central writer: `src/agent_backend/per_call_writer_helpers.py`. Full contract: [`CUSTOM_AGENT.md`](./CUSTOM_AGENT.md) §"Per-call token recording".

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
