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
- [`evaluator/`](./evaluator) — trusted score-phase bundle (DRC runner, scorers, sanity / connectivity, manifest, `trusted_bin/`). See [`evaluator/README.md`](./evaluator/README.md).
- [`testcase/`](./testcase) — ASAP7 PDK + 594 cases (`cell` 255 / `polygon` 332 / `block` 7). See [`testcase/README.md`](./testcase/README.md).
- [`CASE_STAT.md`](./CASE_STAT.md) — per-design-type and per-case statistics (violation counts, rule frequencies, die / core area).
- [`scripts/`](./scripts) — one-time setup (`build_trusted_bin.sh`, `build_seccomp_profile.sh`).
- [`result/`](./result), [`score/`](./score), [`task/`](./task), [`temp/`](./temp), [`logs/`](./logs) — runtime I/O (auto-created).

## Quick start

### Prerequisites

- **Docker** — for building and running the benchmark container.
- **Cursor CLI on the host** (for Cursor pipeline) — install and log in:
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

All commands must be run from the `DAC26_DRC_Benchmark/` directory. To run a single case, prepare an `info.json` (see [`agent/README.md`](./agent/README.md) for the required keys) and call the pipeline script inside the Docker container. `output_path` and `temp_dir` are automatically overwritten by the pipeline with computed container paths — you can leave them empty or set them to any placeholder value.

Use `drc-benchmark-repair` for repair tasks and `drc-benchmark-detection` for detection tasks. Detection additionally requires `--cap-add=NET_ADMIN` so the container entrypoint can program its iptables blocklist. For Codex, `CODEX_EFFORT` is required (e.g. `high` / `medium` / `low`) and is passed via `docker exec -e CODEX_EFFORT=...`.

**Cursor Agent CLI (repair example):**

```bash
CASE=Cell1
DESIGN=cell
CONTAINER=drc-bench-$CASE

# agent/ and evaluator/ are NOT baked into the image; bind-mount agent/ and
# docker cp evaluator/ in at the right times (mirrors evaluate_cursor.sh).
docker create --name "$CONTAINER" \
    -v "$HOME/.config/cursor/auth.json:/root/.config/cursor/auth.json:ro" \
    -v "$(pwd)/agent:/workspace/agent:ro" \
    -v "$(pwd)/result:/workspace/result" \
    -v "$(pwd)/score:/workspace/score" \
    -v "$(pwd)/logs:/workspace/logs" \
    -v "$(pwd)/temp:/workspace/temp" \
    drc-benchmark-repair \
    sleep infinity
docker start "$CONTAINER"

docker cp info.json "$CONTAINER:/workspace/task/info.json"

# Inject helper-script subset that the pipeline needs in the agent phase
# (parse_info_json, postprocess_info_json, check_connectivity for self-check).
docker exec "$CONTAINER" mkdir -p /workspace/evaluator_helpers
for f in parse_info_json.py postprocess_info_json.py check_connectivity.py; do
    docker cp "evaluator/$f" "$CONTAINER:/workspace/evaluator_helpers/$f"
done

# Inject the full trusted evaluator/ bundle so the score phase can run.
docker exec "$CONTAINER" mkdir -p /workspace/evaluator
docker cp evaluator/. "$CONTAINER:/workspace/evaluator/"

# Repair sees the golden DRC report (legitimate input).
docker exec "$CONTAINER" mkdir -p "/workspace/testcase/asap7/$DESIGN/drc_report"
docker cp "testcase/asap7/$DESIGN/drc_report/$CASE.drc.json" \
    "$CONTAINER:/workspace/testcase/asap7/$DESIGN/drc_report/"

docker exec "$CONTAINER" bash src/run_pipeline_cursor.sh /workspace/task/info.json

docker rm -f "$CONTAINER"
```

**Claude Code CLI (detection example):**

Detection runs `--agent-only` first (no golden report visible), then `docker cp` injects the golden report, then `--score-only`. Detection additionally requires `--cap-add=NET_ADMIN` so the entrypoint can program its iptables blocklist.

```bash
CASE=Cell1
DESIGN=cell
CONTAINER=drc-bench-$CASE

# agent/ and evaluator/ are NOT baked into the image; bind-mount agent/ now
# and docker cp the full evaluator/ bundle only after the agent phase ends
# (so it stays invisible during agent execution).
docker create --name "$CONTAINER" --cap-add=NET_ADMIN \
    -v "$HOME/.claude/.credentials.json:/root/.claude/.credentials.json:ro" \
    -v "$(pwd)/agent:/workspace/agent:ro" \
    -v "$(pwd)/result:/workspace/result" \
    -v "$(pwd)/score:/workspace/score" \
    -v "$(pwd)/logs:/workspace/logs" \
    -v "$(pwd)/temp:/workspace/temp" \
    drc-benchmark-detection \
    sleep infinity
docker start "$CONTAINER"

docker cp info.json "$CONTAINER:/workspace/task/info.json"

# Inject only the helper subset for the agent phase; the full evaluator
# bundle stays out of /workspace/ until after the agent finishes.
docker exec "$CONTAINER" mkdir -p /workspace/evaluator_helpers
for f in parse_info_json.py postprocess_info_json.py check_connectivity.py; do
    docker cp "evaluator/$f" "$CONTAINER:/workspace/evaluator_helpers/$f"
done

# Phase 1: agent-only (golden report NOT yet in container; evaluator/ NOT
# yet in container). CLAUDE_EFFORT is required by run_pipeline_claude.sh
# (see src/README.md).
docker exec -e CLAUDE_EFFORT=high "$CONTAINER" \
    bash src/run_pipeline_claude.sh --agent-only /workspace/task/info.json

# Phase 2: inject golden report + full evaluator bundle, then score.
docker exec "$CONTAINER" mkdir -p "/workspace/testcase/asap7/$DESIGN/drc_report"
docker cp "testcase/asap7/$DESIGN/drc_report/$CASE.drc.json" \
    "$CONTAINER:/workspace/testcase/asap7/$DESIGN/drc_report/"
docker exec "$CONTAINER" mkdir -p /workspace/evaluator
docker cp evaluator/. "$CONTAINER:/workspace/evaluator/"

docker exec -e CLAUDE_EFFORT=high "$CONTAINER" \
    bash src/run_pipeline_claude.sh --score-only /workspace/task/info.json

docker rm -f "$CONTAINER"
```

**Codex CLI (repair example):**

`CODEX_EFFORT` is required; it selects the Codex reasoning effort level and also becomes part of the `run_id` (`<model_name>-<effort>`) used for `result/`, `score/`, and log paths.

```bash
CASE=Cell1
DESIGN=cell
CONTAINER=drc-bench-$CASE

# agent/ and evaluator/ are NOT baked into the image; bind-mount agent/ and
# docker cp evaluator/ in at the right times (mirrors evaluate_codex.sh).
docker create --name "$CONTAINER" \
    -v "$HOME/.codex/auth.json:/root/.codex/auth.json:ro" \
    -v "$(pwd)/agent:/workspace/agent:ro" \
    -v "$(pwd)/result:/workspace/result" \
    -v "$(pwd)/score:/workspace/score" \
    -v "$(pwd)/logs:/workspace/logs" \
    -v "$(pwd)/temp:/workspace/temp" \
    drc-benchmark-repair \
    sleep infinity
docker start "$CONTAINER"

docker cp info.json "$CONTAINER:/workspace/task/info.json"

# Inject helper-script subset + full evaluator bundle (repair runs as a
# single --full phase here, so both are needed before bash src/run_pipeline_*).
docker exec "$CONTAINER" mkdir -p /workspace/evaluator_helpers /workspace/evaluator
for f in parse_info_json.py postprocess_info_json.py check_connectivity.py; do
    docker cp "evaluator/$f" "$CONTAINER:/workspace/evaluator_helpers/$f"
done
docker cp evaluator/. "$CONTAINER:/workspace/evaluator/"

# Repair sees the golden DRC report (legitimate input).
docker exec "$CONTAINER" mkdir -p "/workspace/testcase/asap7/$DESIGN/drc_report"
docker cp "testcase/asap7/$DESIGN/drc_report/$CASE.drc.json" \
    "$CONTAINER:/workspace/testcase/asap7/$DESIGN/drc_report/"

docker exec -e CODEX_EFFORT=high "$CONTAINER" \
    bash src/run_pipeline_codex.sh /workspace/task/info.json

docker rm -f "$CONTAINER"
```

For Codex detection runs, use `drc-benchmark-detection` with `--cap-add=NET_ADMIN` and the same `--agent-only` / `--score-only` two-phase flow shown above for Claude.

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
  -> score phase   : verify_evaluator_bundle (sha256 manifest)
                     -> render (repair) -> KLayout DRC -> sanity / connectivity
                     -> score_repair.py | score_detection.py -> CSV + runtime.csv
```

Step-level details live in [`src/README.md`](./src/README.md); trusted-bundle internals in [`evaluator/README.md`](./evaluator/README.md).

## Trust boundary index

- Agent phase and score phase are strictly separated; the agent never sees `/workspace/evaluator/`.
- For detection cases, `evaluator/postprocess_info_json.py` rewrites `path_to_drc_report` to the empty string in the agent-visible info.json — the gate that keeps the detection agent from reading the golden DRC report.
- `Dockerfile.detection` ships without KLayout / wget / curl / pip / yum / git; entrypoint installs an iptables OUTPUT REJECT list on klayout.org / pypi.org / github.com / etc., then drops `NET_ADMIN` from the bounding set.
- All score-phase `docker exec` calls go through `secured-exec.sh` with `HARDENED_EVALUATION=1` and `EVALUATOR_DIR=/workspace/evaluator`.
- `evaluator.sha256` manifest is verified by `verify_evaluator_bundle` as the first step of the score phase (fail-closed).
- `evaluator/trusted_bin/{bash,python3,sha256sum}` are re-injected over `*-trusted` paths after agent kill, so a tampered `/bin/bash` cannot subvert manifest verification.

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
- [`evaluator/README.md`](./evaluator/README.md) — trusted score-phase bundle, manifest, score JSON schema, full hardening invariants.
- [`testcase/README.md`](./testcase/README.md) — ASAP7 PDK and benchmark cases.
