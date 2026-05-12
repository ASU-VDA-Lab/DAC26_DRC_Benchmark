# Building a custom agentic flow

This guide tells you exactly what you can change, what you must not change, and what contracts your custom agent has to honor so the frozen benchmark pipeline (`run_pipeline_*.sh` and `evaluate_*.sh`) still works.

## TL;DR

1. **Only edit files inside `agent/`** — everything else is frozen benchmark infrastructure.
2. **Keep these filenames at these paths** (the frozen pipeline calls them by path): `agent/agent.py`, `agent/prompt_format.py`, `agent/skill.md`, `agent/prompts/{detection,repair_cell,repair_polygon,repair_block}.json`.
3. **`agent/agent.py` must emit `STATUS=...`, `TOKENS_JSON=...`, `RUNTIME_SECONDS=...` lines to stderr** so the host can parse them and write the trusted agent_meta JSON.

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
├── backends/             ← add/remove/rename freely
│   ├── __init__.py
│   ├── claude.py
│   ├── codex.py
│   ├── cursor.py
│   └── your_backend.py   ← add your own
├── __init__.py
└── any_helper.py         ← add new modules freely
```

You can:

- Add multi-turn loops, tool use, RAG, self-critique, voting, anything else inside `agent.py`.
- Add new backends under `agent/backends/<name>.py` and teach `agent.py` to dispatch via `--backend <name>`.
- Read additional environment variables, write to `temp_dir`, and use any libraries available in the container.
- Inject your own derived fields in `prompt_format.py` before substitution.
- Change `skill.md` to whatever knowledge you want to feed the model.
- Restructure the **contents** of `prompts/*.json` (keep the filenames).

---

## What you cannot change

| Directory / file | Why |
|---|---|
| `evaluator/` (entire) | Trusted scoring bundle; hash-verified at score-phase entry via `evaluator.sha256`. |
| `src/` (entire) | Pipeline orchestration: `run_pipeline_*.sh`, `evaluate_*.sh`, `lib_helpers.sh`. |
| `testcase/` (entire) | Frozen evaluation inputs (594 ASAP7 cases). |
| `docker/`, `Dockerfile.*`, `scripts/` | Container hardening and one-time setup. |
| `agent/agent.py` **filename** | Hard-coded as `AGENT_SCRIPT="${agent_dir}/agent.py"` in `run_pipeline_*.sh:191`. |
| `agent/prompt_format.py` **filename** | Hard-coded in `run_pipeline_*.sh:256`. |
| `agent/skill.md` **filename** | Hard-coded in `evaluate_*.sh` and `run_pipeline_*.sh`. |
| `agent/prompts/<task>.json` **filenames** | Hard-coded glob in `run_pipeline_*.sh:168-174`. |

**File contents** are yours; **paths** are not. Renaming `agent/skill.md` to `agent/my_knowledge.md` breaks `evaluate_*.sh` at file-not-found before any case runs.

---

## The four contracts you must honor

### Contract 1 — `agent/agent.py` CLI arguments

`run_pipeline_*.sh:286,495` invokes the dispatcher like this:

```bash
python3 agent/agent.py \
    --backend <name> \
    <prompt.md> <output_path> \      # positional
    --model <model_name> \
    --task_type {repair|detection} \
    --workspace /workspace \
    --temp_dir <path> \
    [--fallback <orig_script>] \     # repair only
    --raw-json-out <path.json> \
    [--effort {high|medium|low}]
```

If your flow does not use some of these, still declare them in `argparse` and ignore the value internally — do **not** make them error. Unknown flags also must not error (since future pipeline revisions may add more).

### Contract 2 — `agent/agent.py` stderr markers

Before exit, `agent.py` **must** print these three lines on stderr in this exact format:

```
STATUS=success
TOKENS_JSON={"input_tokens": N, "output_tokens": N, "cache_read_tokens": N, "cache_write_tokens": N}
RUNTIME_SECONDS=12.345
```

- `STATUS` must be `success` or `fail`; anything else is coerced to `fail` by the host parser (`lib_helpers.sh:314-318`).
- `TOKENS_JSON` keys must be exactly those four names; extra keys are stripped.
- `RUNTIME_SECONDS` must match `^[0-9]+(\.[0-9]+)?$`.

If your agent has no real token counts (e.g. a non-API backend), emit zeros — but **emit all three marker lines**, otherwise the host treats the run as `agent_status=fail` and writes a null score.

### Contract 3 — `agent/prompt_format.py` CLI

`run_pipeline_*.sh:256` invokes the renderer like this:

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
parser.add_argument("--raw-json-out", dest="raw_json_out", required=True)
parser.add_argument("--effort", default=None)
args = parser.parse_args()

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

# Write raw JSON (your own format)
with open(args.raw_json_out, "w") as f:
    json.dump({"tokens": tokens, "status": status}, f)

sys.exit(0)
```

```python
# agent/prompt_format.py
import json, sys, string

class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"

info = json.load(open(sys.argv[1]))
template = json.load(open(sys.argv[2]))
rendered = string.Template(template["user"]).safe_substitute(_SafeDict(info))
print(rendered)
```

```markdown
<!-- agent/skill.md -->
(Domain knowledge you want to surface to the model.)
```

```json
// agent/prompts/detection.json
{ "user": "Find DRC violations in:\n${path_to_layout_script}\n\nRules: ${path_to_design_rule}" }
```

(Provide similar templates for `repair_cell.json`, `repair_polygon.json`, `repair_block.json`.)

After dropping these in, **rebuild the docker images** (`src/` and `agent/` are baked in):

```bash
docker build -f Dockerfile.repair    -t drc-benchmark-repair    .
docker build -f Dockerfile.detection -t drc-benchmark-detection .
```

Then run `bash src/evaluate_claude.sh` (or whichever runner matches your backend).

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

1. **Repurpose an existing backend slot.** Use `--backend cursor` (or `claude` / `codex`) and put your real implementation in `agent/backends/cursor.py`. The runner only dispatches; the actual call lives in your backend module.
2. **Bypass `evaluate_*.sh`.** Invoke `run_pipeline_<x>.sh` directly per case from your own driver script. That is exactly what the runners do internally — iterate the CASES matrix and call the pipeline.

---

## Why these constraints exist (trust model recap)

The benchmark uses an **agent-score isolation** invariant: during the agent phase, the container has only `agent/` (read-only) and a minimal `evaluator_helpers/` subset (three files: `parse_info_json.py`, `postprocess_info_json.py`, `check_connectivity.py`). The full `evaluator/` bundle — containing the scorer, render script, DRC runner, and manifest — is injected by the host **only after the agent is killed and the network is disconnected**.

If you could modify `evaluator/`, you would see the scoring formula and could optimize for the metric rather than for genuine DRC correctness. If you could modify `src/` or `docker/`, you could weaken the kill + isolation step. Keeping all of those frozen is what makes benchmark scores comparable across submissions.

For details on this trust model see [`evaluator/README.md`](./evaluator/README.md) and the host wiring in [`src/lib_helpers.sh`](./src/lib_helpers.sh) (`reinject_critical_binaries`, `generate_evaluator_manifest`, `write_trusted_agent_meta`).

---

## Pre-submission sanity checklist

- [ ] `bash src/evaluate_claude.sh` (or your runner) completes at least one case end to end.
- [ ] `.sealed_audit/.../*_agent_meta.json` shows your actual token counts, not zeros.
- [ ] `score/.../*_score.json` is produced with `agent_status: "success"`.
- [ ] `git status` shows only `agent/` files modified (plus optionally rebuilt docker images and runtime artifacts).
- [ ] `git diff` against `src/`, `evaluator/`, `testcase/`, `docker/`, `Dockerfile.*`, `scripts/` is empty.

If any item fails, you have either broken a contract or modified frozen code — that submission will not be comparable to others.
