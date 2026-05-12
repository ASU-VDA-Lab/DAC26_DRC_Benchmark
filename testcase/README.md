# testcase/ — ASAP7 PDK and benchmark cases

ASAP7 KLayout technology files and 594 DRC benchmark cases.

> **Modification policy:** **Do NOT modify** anything under `testcase/`. These are the frozen evaluation inputs; any edit (including tweaking a `.lydrc` rule, swapping a `.gds`, or regenerating a `drc_report`) changes what the benchmark measures and invalidates cross-submission comparisons. Only `agent/` is user-modifiable — see [`../CUSTOM_AGENT.md`](../CUSTOM_AGENT.md) for what to put there.

## Files

- `asap7/asap7.lydrc` — KLayout DRC rule file (~375 rules) for polygon and block designs.
- `asap7/asap7_cell.lydrc` — cell-specific variant; adds `m0 = input(0, 0)` layer.
- `asap7/asap7.lyt` — KLayout technology file; layer stack; `dbu = 0.00025` um.
- `asap7/asap7.lyp` — layer properties (display colors / fill).
- `asap7/drm_jpg/` — design rule manual images (referenced by `path_to_drm_jpg`).
- `asap7/cell/` — 255 standard-cell cases. Subdirs: `gds/` `layout_script/` `layout_screenshot/<case>/` `drc_report/` `connectivity/`.
- `asap7/polygon/` — 332 isolated-polygon cases. Subdirs: `gds/` `layout_script/` `layout_screenshot/` `drc_report/`.
- `asap7/block/` — 7 block-level cases. Subdirs: `gds/` `layout_script/` `layout_screenshot/` `drc_report/` `connectivity/`.

## Design types

| Type | Cases | DRC rule file | Notes |
|---|---:|---|---|
| `cell` | 255 | `asap7_cell.lydrc` | Standard-cell layouts (10–50 polygons, 5–15 violations). |
| `polygon` | 332 | `asap7.lydrc` | Isolated polygon constructs; repair restricted to resize / move (no add / delete). |
| `block` | 7 | `asap7.lydrc` | Block-level layouts with multi-cell routing and vias (100+ polygons). |

## File naming

All files for a single case share the base `<case_name>`:

| Directory | Pattern | Example |
|---|---|---|
| `gds/` | `<case_name>.gds` | `Cell1.gds` |
| `layout_script/` | `<case_name>.py` | `Cell1.py` |
| `layout_screenshot/` | `<case_name>/<case_name>.png` | `Cell1/Cell1.png` |
| `drc_report/` | `<case_name>.drc.json` | `Cell1.drc.json` |
| `connectivity/` | `<case_name>.json` | `Cell1.json` (cell / block only) |

Golden DRC reports are **not** baked into the Docker image; the host injects them via `docker cp` at the appropriate point in the trust-boundary timeline (after the agent finishes for detection; before the agent runs for repair).

## DRC report formats

`.lyrpt` — KLayout's native XML report; produced when KLayout DRC re-runs on a repaired GDS. The pipeline converts it to `.drc.json` via `evaluator/process_klayout_reports.py`.

`.drc.json` — primary structured format consumed by both the agent prompt and the scorer. Per-rule violation counts, descriptions, and per-violation geometry in dbu (integer; 1 dbu = 0.00025 um):

```json
{
  "case_name": "Cell1",
  "design_type": "cell",
  "total_violations": 3,
  "total_rules_violated": 1,
  "rules": {
    "M1.S.4": {
      "violation_count": 3,
      "description": "Minimum spacing of M1 on same track.",
      "violations": [
        {"type": "edge_pair", "edges": [[1768, 832, 1840, 832], [1768, 944, 1840, 944]], "bbox": [1768, 832, 1840, 944]}
      ]
    }
  }
}
```

## Rule naming convention

`[LAYER].TYPE.NUMBER[SUFFIX]`. Examples: `M1.S.4` (min M1 spacing on same track), `WELL.W.1` (min WELL width 108 nm).

| Component | Examples |
|---|---|
| `LAYER` | `WELL`, `FIN`, `GATE`, `ACTIVE`, `M0`–`M9`, `V0`–`V9` |
| `TYPE` | `W` width, `S` spacing, `EN` enclosure, `EX` extension, `A` area |
| `NUMBER[SUFFIX]` | `1`, `4`, `1A`, ... |

For detection output: rules with `.S.` -> agent emits **edge pairs**; all others -> **bounding boxes**.

## See also

- [`../README.md`](../README.md) — root quick-start showing how to inject golden reports into a single case.
- [`../evaluator/README.md`](../evaluator/README.md) — `process_klayout_reports.py` (`.lyrpt` -> `.drc.json`) and the scorers consuming `.drc.json`.
