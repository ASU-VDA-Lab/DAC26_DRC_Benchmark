# Building a custom agentic flow

This guide tells you exactly what you can change, what you must not change, and what contracts your custom agent has to honor so the frozen benchmark pipeline (`run_pipeline_*.sh` and `evaluate_*.sh`) still works.

## TL;DR

1. **Only edit files inside `agent/`** — everything else is frozen benchmark infrastructure. The token-recording backends now live in `src/agent_backend/` (frozen, image-baked).
2. **Keep these filenames at these paths** (the frozen pipeline calls them by path): `agent/agent.py`, `agent/prompt_format.py`, `agent/skill.md`, `agent/prompts/{detection,repair_cell,repair_polygon,repair_block}.json`.
3. **`agent/agent.py` must emit `STATUS=...`, `TOKENS_JSON=...`, `RUNTIME_SECONDS=...` lines to stderr** so the host can parse them and write the trusted agent_meta JSON.

**Trust posture (three layers):**

- `agent/` — user-customizable per-run agent logic; bind-mounted **read-only** into the container.
- `src/agent_backend/` — frozen, image-baked token-recording backends. Image rebuild required for any change.
- `evaluator/` — trusted scoring bundle; hash-stamped per case via `evaluator_hash` embedded in every per-case score JSON.

---

## What you can freely change

Anything inside `agent/`:

```
agent/
├── agent.py              ← rewrite freely (must honor CLI + stderr contract)
├── prompt_format.py      ← rewrite freely
├── skill.md              ← any markdown content
├── prompts/
│   ├── detection.json    ← any template; uses ${field} placeholders
│   ├── repair_cell.json
│   ├── repair_polygon.json
│   └── repair_block.json
├── __init__.py
└── any_helper.py         ← add new modules freely
```

You can:

- Add multi-turn loops, tool use, RAG, self-critique, voting, anything else inside `agent.py`.
- Add or modify dispatch wiring in `agent/agent.py`. The three token-recording backends in `src/agent_backend/` (`claude.py`, `codex.py`, `cursor.py`) are frozen — image rebuild required to modify.
- Read additional environment variables, write to `temp_dir`, and use any libraries available in the container.
- Inject your own derived fields in `prompt_format.py` before substitution.
- Change `skill.md` to whatever knowledge you want to feed the model.
- Restructure the **contents** of `prompts/*.json` (keep the filenames).

---

## What you cannot change

| Directory / file | Why |
|---|---|
| `evaluator/` (entire) | Trusted scoring bundle; do not modify. Each per-case score JSON records `evaluator_hash`; tampering detectable post-hoc by re-hashing a clean checkout. |
| `src/agent_backend/` (entire) | Frozen image-baked token-recording backends; modification requires docker image rebuild. Customizable dispatch logic belongs in `agent/agent.py`. |
| `src/` (entire) | Pipeline orchestration: `run_pipeline_*.sh`, `evaluate_*.sh`, `lib_helpers.sh`. |
| `testcase/` (entire) | Frozen evaluation inputs (594 ASAP7 cases). |
| `docker/`, `Dockerfile.*`, `scripts/` | Container hardening and one-time setup. |
| `agent/agent.py` **filename** | Hard-coded as `AGENT_SCRIPT="${agent_dir}/agent.py"` in each `run_pipeline_*.sh` (grep `AGENT_SCRIPT=`). |
| `agent/prompt_format.py` **filename** | Hard-coded in each `run_pipeline_*.sh` (grep `prompt_format.py`). |
| `agent/skill.md` **filename** | Hard-coded in `evaluate_*.sh` and `run_pipeline_*.sh` (grep `skill_file=`). |
| `agent/prompts/<task>.json` **filenames** | Hard-coded prompt-template selection in each `run_pipeline_*.sh` (grep `prompts/repair_` / `prompts/${task_type}`). |

**File contents** are yours; **paths** are not. Renaming `agent/skill.md` to `agent/my_knowledge.md` breaks `evaluate_*.sh` at file-not-found before any case runs.

---

## Backend CLI invariants (frozen)

The three image-baked backends under `src/agent_backend/` invoke their respective CLIs with a fixed set of flags. **These are load-bearing for benchmark integrity** — changing them in your own fork of the image must be done with eyes open to the threat each prevents.

### `src/agent_backend/claude.py` — 5 invariants

| CLI flag / behavior | Threat if changed |
|---|---|
| `--output-format json` | Parser crash; downstream `usage` dict missing. |
| `--allowedTools Bash(*) Read Write Edit Glob Grep Agent NotebookEdit` | **Critical**: adding `WebFetch` enables exfiltration of golden DRC reports. |
| `-p` (print mode, non-interactive) | Stalled REPL waiting for stdin. |
| Stdin-for-long-prompts above `LONG_PROMPT_THRESHOLD` (100 000 chars) | Argv DOS / kernel ARG_MAX. |
| `subprocess.Popen` with no `shell=True` | Shell injection via prompt content. |

### `src/agent_backend/codex.py` — 8 invariants

| CLI flag / behavior | Threat if changed |
|---|---|
| `exec --json` | Per-event JSONL stream becomes unparseable. |
| `--ephemeral` | **Critical**: cross-case session state leaks. |
| `--skip-git-repo-check` | Codex refuses to run in non-repo directories. |
| `--sandbox <env CODEX_SANDBOX or "danger-full-access">` | Codex's workspace-write sandbox may require user namespaces disabled in containers. |
| `-c approval_policy="never"` | Interactive prompt stalls the run. |
| `-c web_search="disabled"` | **Critical**: Codex web-search would exfiltrate. |
| `-c sandbox_workspace_write.network_access=false` | **Critical**: defense-in-depth against network egress. |
| `--color never` | ANSI escapes corrupt JSONL parsing. |

### `src/agent_backend/cursor.py` — 4 invariants

| CLI flag / behavior | Threat if changed |
|---|---|
| `--output-format json` | Parser crash; downstream `usage` dict missing. |
| `--trust` | Cursor blocks with a workspace-trust prompt. |
| `-p` (print mode, non-interactive) | Stalled REPL. |
| `--workspace <dir>` | Cursor defaults to cwd which may leak host paths. |

All three backends write exactly one `${AGENT_CALLS_DIR}/<call_id>.json` per CLI invocation via the shared helper `src/agent_backend/per_call_writer_helpers.py`, with four-key totals + `by_model`. To add a fourth backend, do NOT add a file under `src/agent_backend/`; rewrite the dispatch path in `agent/agent.py` to handle the new backend name and perform the per-call write inline using the helper.

---

## The four contracts you must honor

### Contract 1 — `agent/agent.py` CLI arguments

Each `run_pipeline_*.sh` (grep `python3 "${AGENT_SCRIPT}"`) invokes the dispatcher like this:

```bash
python3 agent/agent.py \
    --backend <name> \
    <prompt.md> <output_path> \      # positional
    --model <model_name> \
    --task_type {repair|detection} \
    --workspace /workspace \
    --temp_dir <path> \
    [--fallback <orig_script>] \     # repair only
    [--raw-json-out <path.json>] \   # always passed today, but accept missing for forward-compat
    [--effort {high|medium|low}]
```

If your flow does not use some of these, still declare them in `argparse` and ignore the value internally — do **not** make them error.

Future pipeline revisions may add more flags. The reference `agent.py` uses `parser.parse_args()`, which **does** error on unknown flags; if you want to be forward-compatible, prefer `parser.parse_known_args()` so an unrecognized flag from a newer pipeline does not blow up your run.

### Contract 2 — `agent/agent.py` stderr markers

Before exit, `agent.py` **must** print these three lines on stderr in this exact format:

```
STATUS=success
TOKENS_JSON={"input_tokens": N, "output_tokens": N, "cache_read_tokens": N, "cache_write_tokens": N}
RUNTIME_SECONDS=12.345
```

- `STATUS` must be `success` or `fail`; anything else is coerced to `fail` by the host parser in `lib_helpers.sh` (grep `===== STATUS =====`).
- `TOKENS_JSON` keys must be exactly those four names; extra keys are stripped.
- `RUNTIME_SECONDS` must match `^[0-9]+(\.[0-9]+)?$`.

If your agent has no real token counts (e.g. a non-API backend), emit zeros — but **emit all three marker lines**, otherwise the host treats the run as `agent_status=fail` and writes a null score.

### Contract 3 — `agent/prompt_format.py` CLI

Each `run_pipeline_*.sh` (grep `prompt_format.py`) invokes the renderer like this:

```bash
python3 agent/prompt_format.py <case_info_json> <prompt_template_json> > <formatted_prompt.md>
```

Read the info.json (positional 1), read the JSON template (positional 2), print the formatted prompt to stdout. The rest of the implementation is yours.

### Contract 4 — file output

After `agent.py` returns:

- **Repair:** `<output_path>` must exist and be a Python layout script. The renderer will feed it to KLayout for DRC.
- **Detection:** `<output_path>` must exist and be a JSON file matching the detection schema (validated by `score_detection.py`).

If your agent fails to produce output, the `--fallback` is used for repair only — but detection has no fallback; you must produce a parseable JSON or the score phase fails closed.

---

## Per-call token recording (mandatory)

During the agent phase, every backend MUST write one `${AGENT_CALLS_DIR}/<ID>.json` per successful CLI call, where `<ID>=${case_name}_${call_seq:04d}_<sha8>` (the eight-hex-char prefix of a per-call session id). The aggregator fails closed at score time when STATUS=success but zero per-call files were found, emitting an invalid score with `invalid_reason=mandatory_calls_recording_missing`.

**Env vars.** During the agent phase the pipeline exports:

- `AGENT_CALLS_DIR=${score_dir}/calls` — flat directory shared across cases under the same `${score_dir}`.
- `AGENT_CASE_NAME=${case_name}` — used as the filename prefix.

Stale files for the current case are removed with `rm -f ${AGENT_CALLS_DIR}/${case_name}_*.json` before each agent run (scope-clean; other cases under the same `calls/` are untouched).

**Per-call JSON schema.** Required keys:

```json
{
  "call_id": "<case_name>_NNNN_<sha8>",
  "case_name": "<case_name>",
  "model": "<primary-model-name>",
  "schema_version": "1",
  "input_tokens": 100, "output_tokens": 50,
  "cache_read_tokens": 0, "cache_write_tokens": 0,
  "by_model": {
    "<model-name-1>": {
      "input_tokens": 100, "output_tokens": 50,
      "cache_read_tokens": 0, "cache_write_tokens": 0
    }
  }
}
```

Optional forensic fields (`session_id`, `runtime_seconds`, `started_at`, `finished_at`) are allowed but ignored by the aggregator.

**Fail-closed.** When `STATUS=success` and zero `${case_name}_*.json` files exist, the aggregator exits 4 and the host writes a fail-closed null score JSON via `write_invalid_score.py --invalid-reason=mandatory_calls_recording_missing --null-tokens`. The score JSON's `valid_repair` / `valid_detection` field is `false` and `invalid_reason` is `mandatory_calls_recording_missing`.

When `STATUS=fail`, the `--require-files` flag is not set; the aggregator's marker fallback path is preserved verbatim.

**Concurrency.** Concurrent runs of the same `(run_id, model_name, design_type, task_type, case_name)` tuple on the same host are caller responsibility — bump `model_name` or effort so the derived `run_id` differs, otherwise the second invocation's `rm -f` may clear the first's per-call files. The host no longer holds a `flock` for this; same-case parallelism on one host requires distinct `run_id` values.

---

## Minimum viable custom agent — skeleton

The smallest tree that satisfies all four contracts:

```python
# agent/agent.py
import argparse, json, sys, time
parser = argparse.ArgumentParser()
parser.add_argument("--backend", required=True)
parser.add_argument("prompt_path")
parser.add_argument("output_path")
parser.add_argument("--model", required=True)
parser.add_argument("--task_type", required=True)
parser.add_argument("--workspace", required=True)
parser.add_argument("--temp_dir", required=True)
parser.add_argument("--fallback", default=None)
parser.add_argument("--raw-json-out", dest="raw_json_out", default=None)
parser.add_argument("--effort", default=None)
# parse_known_args() so a future pipeline flag does not abort the run.
args, _unknown = parser.parse_known_args()

start = time.time()
try:
    with open(args.prompt_path) as f:
        prompt = f.read()

    # === your agentic flow goes here ===
    result_text, token_usage = call_my_llm(prompt, args.model)
    with open(args.output_path, "w") as f:
        f.write(result_text)
    # ===

    status = "success"
    tokens = token_usage  # dict with the 4 required keys
except Exception as e:
    print(f"agent error: {e}", file=sys.stderr)
    status = "fail"
    tokens = {"input_tokens": 0, "output_tokens": 0,
              "cache_read_tokens": 0, "cache_write_tokens": 0}
    if args.task_type == "repair" and args.fallback:
        import shutil; shutil.copy(args.fallback, args.output_path)

# Emit markers (REQUIRED)
print(f"STATUS={status}", file=sys.stderr)
print(f"TOKENS_JSON={json.dumps(tokens)}", file=sys.stderr)
print(f"RUNTIME_SECONDS={time.time()-start:.3f}", file=sys.stderr)

# Write raw JSON (your own format) when the pipeline asks for it
if args.raw_json_out:
    with open(args.raw_json_out, "w") as f:
        json.dump({"tokens": tokens, "status": status}, f)

sys.exit(0)
```

```python
# agent/prompt_format.py
# Must read the same 6-key schema that the shipped prompts/*.json files use:
#   task, schema_version, system, user_template, variables, output_format
# `user_template` (not `user`) is the placeholder body; every ${var} placeholder
# in it must be declared in the `variables` list, or you will get a ValueError.
import json, string, sys

class _SafeDict(dict):
    def __missing__(self, key):
        return "${" + key + "}"

info = json.load(open(sys.argv[1]))
template = json.load(open(sys.argv[2]))

system = template.get("system", "")
user = string.Template(template["user_template"]).safe_substitute(_SafeDict(info))
sys.stdout.write(f"{system}\n\n{user}\n" if system else user + "\n")
```

```markdown
<!-- agent/skill.md -->
(Domain knowledge you want to surface to the model.)
```

```json
// agent/prompts/detection.json -- must keep the 6-key schema
{
  "task": "detection",
  "schema_version": "1.0",
  "system": "You are an EDA engineer who performs static DRC detection.",
  "user_template": "Find DRC violations in:\n${path_to_layout_script}\n\nRules: ${path_to_design_rule}\nWrite the JSON result to ${output_path}.",
  "variables": ["path_to_layout_script", "path_to_design_rule", "output_path"],
  "output_format": { "kind": "json", "description": "Array of violation objects." }
}
```

(Provide similar templates for `repair_cell.json`, `repair_polygon.json`, `repair_block.json`.)

If you rewrite `prompt_format.py` with a different template schema, you must rewrite **all four** `prompts/*.json` files in lockstep — the shipped `prompt_format.py` and the shipped prompt JSONs are coupled, and mixing the two will fail validation.

Then run `bash src/evaluate_claude.sh` (or whichever runner matches your backend).

**No image rebuild is needed** when you only change `agent/`. `evaluate_*.sh` bind-mounts `agent/` into the container read-only (`-v ${host_dir}/agent:/workspace/agent:ro`), so your edits are picked up on the next run.

Rebuilds are still required when `src/agent_backend/` changes — same rule as `src/`, `evaluator/`, `testcase/`, `docker/`, `Dockerfile.*`. But per the modification policy, you should not be editing those:

```bash
docker build -f Dockerfile.repair    -t drc-benchmark-repair    .
docker build -f Dockerfile.detection -t drc-benchmark-detection .
```

---

## info.json fields available to your prompt template

`prompt_format.py` receives a fully-resolved info.json. These fields are available as `${field}` placeholders (pulled from `evaluator/postprocess_info_json.py`):

| Field | Set by | Notes |
|---|---|---|
| `model_name` | Host info.json builder | The model identifier passed via `--model`. |
| `case_name`, `design_type`, `task_type` | Host info.json builder | Test case identifiers. |
| `path_to_skill` | Postprocess | Container path to `agent/skill.md`. |
| `path_to_layout_script` | Postprocess | The case's Python layout source. |
| `path_to_layout_screenshot` | Postprocess | Per-case PNG render. |
| `path_to_drc_report` | Postprocess | **Repair only**; empty string for detection (this is the gate that keeps the detection agent from seeing the golden answer). |
| `path_to_design_rule` | Postprocess | Path to `.lydrc`. |
| `path_to_drm_jpg` | Postprocess | DRM image directory (optional). |
| `path_to_connectivity_file` | Postprocess | Cell / block designs only. |
| `output_path` | Postprocess | Where your agent must write the result. |
| `temp_dir` | Postprocess | Per-run scratch directory. |

Cherry-pick whatever you need; unused fields stay in the JSON but never reach the LLM. If you need an additional field, derive it inside `prompt_format.py` (read the JSON, add your field, then substitute) — do **not** modify `evaluator/postprocess_info_json.py`.

---

## Should I add a new `evaluate_<my_backend>.sh`?

No. `evaluate_*.sh` lives in frozen `src/`. The existing three runners (`claude`, `codex`, `cursor`) cover the three currently supported CLI families. If your agent runs through one of those CLIs (e.g., a different prompting strategy on Claude), just use the existing runner.

If your agent does not fit any of the three (for example, a custom REST client to your own model), pick one of:

1. **Override dispatch in `agent/agent.py`.** Add a branch in the importlib dispatch path for your new backend name. The frozen `src/agent_backend/` modules must not be edited; perform your per-call write inline in `agent/agent.py` using the shared helper `from per_call_writer_helpers import ...` (the sys.path bootstrap in `agent/agent.py` already adds `/workspace/src`).
2. **Bypass `evaluate_*.sh`.** Invoke `run_pipeline_<x>.sh` directly per case from your own driver script. That is exactly what the runners do internally — iterate the CASES matrix and call the pipeline.

---

## Why these constraints exist (trust model recap)

The benchmark uses an **agent-score isolation** invariant: during the agent phase, the container has only `agent/` (read-only) and a minimal `evaluator_helpers/` subset (three files: `parse_info_json.py`, `postprocess_info_json.py`, `check_connectivity.py`). The full `evaluator/` bundle — containing the scorer, render script, and DRC runner — is injected by the host **only after the agent is killed and the network is disconnected**.

If you could modify `evaluator/`, you would see the scoring formula and could optimize for the metric rather than for genuine DRC correctness. If you could modify `src/` or `docker/`, you could weaken the kill + isolation step. Keeping all of those frozen is what makes benchmark scores comparable across submissions. The frozen `src/agent_backend/` further keeps the token-recording surface beyond agent reach.

For details on this trust model see [`evaluator/README.md`](./evaluator/README.md) and the host wiring in [`src/lib_helpers.sh`](./src/lib_helpers.sh) (`reinject_critical_binaries`, `write_trusted_agent_meta`).

---

## Pre-submission sanity checklist

- [ ] `bash src/evaluate_claude.sh` (or your runner) completes at least one case end to end.
- [ ] `.sealed_audit/.../*_agent_meta.json` shows your actual token counts, not zeros.
- [ ] `score/.../*_score.json` is produced with `agent_status: "success"` and a non-empty `evaluator_hash` field.
- [ ] `git status` shows only `agent/` files modified (plus optionally rebuilt docker images and runtime artifacts).
- [ ] `git diff` against `src/`, `evaluator/`, `testcase/`, `docker/`, `Dockerfile.*`, `scripts/` is empty.

If any item fails, you have either broken a contract or modified frozen code — that submission will not be comparable to others.
