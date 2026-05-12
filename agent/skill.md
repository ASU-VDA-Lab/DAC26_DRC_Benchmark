# ASAP7 DRC Rules and KLayout -- Agent Skill Guide

This document provides the knowledge an LLM agent needs to fix and predict DRC (Design Rule Check) violations in ASAP7 layouts checked with KLayout DRC.

---

## 1. ASAP7 PDK Overview

ASAP7 is a 7nm PDK.

### Database Unit (dbu)

- **dbu = 0.00025 um** (0.25 nm)
- To convert from micrometers to dbu: `dbu_value = int(round(um_value / 0.00025))`
- To convert from nanometers to dbu: `dbu_value = int(round(nm_value / 0.25))`
- Example: 18 nm = 72 dbu, 54 nm = 216 dbu, 108 nm = 432 dbu

### Layer Stack

The ASAP7 layer stack includes the following layers (bottom to top, grouped by function):

- WELL
- FIN
- GATE
- ACTIVE
- GCUT
- NSELECT
- PSELECT
- SLVT
- LVT
- SRAMVT
- SDT
- LIG
- LISD
- M0
- V0
- M1
- V1
- M2
- V2
- M3
- V3
- M4
- V4
- M5
- V5
- M6
- V6
- M7
- V7
- M8
- V8
- M9
- V9

---

## 2. Layer Number Mapping

Each layer in the GDS/OASIS file is identified by a layer number. The datatype is typically 0. The complete mapping is:

| Layer Number | Layer Name | Description |
|---|---|---|
| 0 | M0 | Metal 0 (cell designs only) |
| 1 | WELL | N-well |
| 2 | FIN | Fin |
| 7 | GATE | Gate polysilicon |
| 10 | GCUT | Gate cut |
| 11 | ACTIVE | Active / diffusion |
| 16 | LIG | Local interconnect gate |
| 17 | LISD | Local interconnect source/drain |
| 18 | V0 | Via 0 |
| 19 | M1 | Metal 1 |
| 20 | M2 | Metal 2 |
| 21 | V1 | Via 1 |
| 25 | V2 | Via 2 |
| 30 | M3 | Metal 3 |
| 35 | V3 | Via 3 |
| 40 | M4 | Metal 4 |
| 45 | V4 | Via 4 |
| 50 | M5 | Metal 5 |
| 55 | V5 | Via 5 |
| 60 | M6 | Metal 6 |
| 65 | V6 | Via 6 |
| 70 | M7 | Metal 7 |
| 75 | V7 | Via 7 |
| 80 | M8 | Metal 8 |
| 85 | V8 | Via 8 |
| 90 | M9 | Metal 9 |
| 95 | V9 | Via 9 |

When creating layers in KLayout scripts, use `layout.layer(pya.LayerInfo(layer_number, 0))`.

---

## 3. Common DRC Rule Categories

DRC rule names in ASAP7 follow the pattern `LAYER.CATEGORY.NUMBER` (e.g., `M1.W.1`, `V0.M1.EN.1`). Understanding the category codes is essential for interpreting and repairing violations.

### W -- Width Rules

Specify the minimum (or exact) width of shapes on a layer.

- **Meaning:** A shape is too narrow in some dimension.
- **Fix:** Expand the shape edge(s) outward until the width meets the minimum.
- **Example:** `M1.W.1` = minimum width of M1 shapes is 18 nm.

### S -- Spacing Rules

Specify the minimum spacing between shapes on the same layer or between different layers.

- **Meaning:** Two shapes are too close together.
- **Fix:** Move one or both shapes apart, or merge them if they are nearly touching and merging does not create other violations.
- **Example:** `M1.S.1` = minimum spacing for M1.

### EN -- Enclosure Rules

Specify the minimum enclosure (overlap margin) of one layer by another.

- **Meaning:** A via or inner shape is not sufficiently enclosed by its surrounding metal or other layer.
- **Fix:** Expand the enclosing layer so it extends past the enclosed shape by at least the required amount on all specified sides.
- **Example:** `V0.M1.EN.1` = M1 must enclose V0 by a minimum distance.

### EX -- Extension Rules

Specify the minimum extension of one layer past another layer's edge.

- **Meaning:** A layer does not extend far enough beyond a reference layer.
- **Fix:** Extend the violating shape past the reference edge by the required amount.
- **Example:** `GATE.ACTIVE.EX.1` = GATE must extend past ACTIVE by a minimum distance.

### A -- Area Rules

Specify the minimum area of shapes on a layer.

- **Meaning:** A shape is too small in total area.
- **Fix:** Enlarge the shape (increase width or length) until its area meets the minimum.
- **Example:** `M1.A.1` = minimum area for M1 shapes.

### AUX -- Auxiliary Rules

Additional geometric constraints that do not fit into the above categories.

- **Meaning:** Various constraints such as no-bend rules, jog requirements, or orientation restrictions.
- **Fix:** Depends on the specific rule; often requires reshaping geometry to remove bends, jogs, or non-orthogonal edges.
- **Example:** `M1.AUX.1` = M1 shapes must not have bends (must be rectangular).

### L -- Length Rules

Specify the minimum length of shapes or edges.

- **Meaning:** A shape or a particular edge of a shape is too short.
- **Fix:** Extend the shape along the short dimension.

### OV -- Overlap Rules

Specify minimum overlap between two layers.

- **Meaning:** Two layers that should overlap do not overlap sufficiently.
- **Fix:** Adjust shapes so the overlap area meets the minimum.

---

## 4. Key Design Rules Quick Reference

These are the most commonly encountered rules and frequent sources of violations. All dimensions are in nanometers.

### WELL Rules

| Rule | Description | Value |
|---|---|---|
| WELL.W.1 | Min horizontal width | 108 nm |
| WELL.W.2 | Min vertical width | 54 nm |

### FIN Rules

| Rule | Description | Value |
|---|---|---|
| FIN.W.1 | Exact vertical width | 7 nm |
| FIN.S.1 | Exact vertical pitch (center-to-center) | 27 nm |

FIN shapes have strict exact-width and exact-pitch requirements. Any deviation causes violations.

### GATE Rules

| Rule | Description | Value |
|---|---|---|
| GATE.W.1 | Exact horizontal width | 20 nm |
| GATE.S.1 | Exact horizontal pitch (center-to-center) | 54 nm |

GATE shapes also have exact width and pitch. They run perpendicular to FINs.

### M1 (Metal 1) Rules

| Rule | Description | Value |
|---|---|---|
| M1.W.1 | Min width | 18 nm |
| M1.S.1 | Min side-to-side spacing | varies by context |
| M1.S.2 | Min tip-to-tip spacing | varies by context |
| M1.S.3 | Min tip-to-side spacing | varies by context |
| M1.S.4 | Min spacing (wide metal) | varies by context |
| M1.S.5 | Min spacing (PRL-dependent) | varies by context |
| M1.S.6 | Min spacing (other context) | varies by context |

M1 spacing rules have multiple sub-categories depending on the geometric relationship between the two shapes (parallel run length, tip-to-tip, tip-to-side, etc.).

### Via Rules (V0 as example)

| Rule | Description | Value |
|---|---|---|
| V0.W.1 | Via width | exact or min, depending on context |
| V0.M1.EN.1 | V0 enclosure by M1 | min enclosure distance |

Via rules primarily involve width/size of the via shape and enclosure by the metals above and below.

### General Metal Rules (M2-M9)

Higher metals follow similar patterns to M1 but with different dimensions. Typical rules include:
- `MX.W.1` -- minimum width (increases for higher metals)
- `MX.S.1` through `MX.S.N` -- various spacing rules
- `VX.MX.EN.1` -- via enclosure by metal
- `MX.A.1` -- minimum area

---

## 5. DRC Repair Strategies

When repairing DRC violations in a layout, follow these principles and strategies.

### General Principles

1. **Never delete layers that carry net connectivity.** Removing a metal or via shape can break the electrical connection between components. Only reshape or move them.
2. **Maintain logical connectivity.** Vias must overlap the metal layers above and below them. If you move a via, ensure it still overlaps both metals. If you resize a metal, ensure all vias on it remain enclosed. For cell and block designs, a golden connectivity JSON file is provided that describes all electrical paths from each seed polygon. After repair, verify connectivity is preserved by running:
   `python3 /workspace/evaluator_helpers/check_connectivity.py <golden_json> <modified_script> <cell|block>`
3. **Preserve the top cell name and dbu.** The output GDS must have the same top cell name and dbu (0.00025 um) as the input.
4. **Repair violations without introducing new ones.** After repairing one violation, verify that the repair does not create new violations on the same or neighboring layers.
5. **Minimal changes are preferred.** Make the smallest possible modification that resolves the violation.

### Strategy by Violation Type

**Width violations (W):**
- Identify which dimension (horizontal or vertical) is too narrow.
- Expand the shape in that dimension to meet the minimum width.
- For exact-width rules (FIN, GATE), the shape must be exactly the specified width -- not more, not less.
- When expanding, expand in a direction that does not cause spacing violations with neighbors.

**Spacing violations (S):**
- Determine the type of spacing violation (side-to-side, tip-to-tip, tip-to-side).
- Option A: Move one shape away from the other until the spacing is met.
- Option B: If two shapes are very close and on the same net, merge them into one shape (if this does not violate width/area rules).
- When moving shapes, check that the new position does not violate spacing with other neighbors.

**Enclosure violations (EN):**
- Identify which side(s) of the enclosed shape (usually a via) lack sufficient enclosure.
- Expand the enclosing metal on the deficient side(s).
- Ensure the expansion does not create spacing violations with neighboring shapes on the same metal layer.

**Pitch violations (exact pitch for FIN, GATE):**
- Compute the correct positions based on the required pitch.
- Adjust the shape center-to-center distance to match exactly.
- FIN pitch = 27 nm, GATE pitch = 54 nm.

**Area violations (A):**
- Enlarge the shape (increase width or length) to meet the minimum area.
- Prefer expanding in the direction that causes the fewest conflicts.

**Auxiliary violations (AUX):**
- Read the specific rule description. Common cases:
  - No-bend rule: Replace an L-shaped or bent polygon with one or more rectangles.
  - Orientation rule: Rotate or redraw the shape in the correct orientation.

### Fixing Workflow

1. Parse the DRC report to identify all violations, their rule names, and locations.
2. Group violations by type and proximity (nearby violations may be related).
3. Fix violations in order of severity or dependency (e.g., fix width before spacing, as widening a shape changes spacing).
4. After all fixes, regenerate the layout and re-run DRC to verify no new violations were introduced.

---

## 6. DRC Detection Strategies

When detecting whether a layout will have DRC violations (and how many), use these strategies.

### Systematic Checking Approach

1. **Layer by layer:** For each layer present in the layout, check its shapes against the relevant width, spacing, area, and auxiliary rules.
2. **Layer-pair checks:** For each via layer, check enclosure by the metals above and below. For overlapping layers (GATE over ACTIVE, etc.), check extension and overlap rules.
3. **Count each violation marker separately.** A single shape can cause multiple violations if it fails multiple rules or if the same rule is violated at multiple locations.

### Common Violation Patterns

- **Tip-to-tip vs. side-to-side spacing:** These often have different minimum values. Two shapes that pass side-to-side spacing may fail tip-to-tip spacing (or vice versa). Always check which geometric relationship applies.
- **Via enclosure violations:** These are among the most common violations. Check all four sides of every via against the enclosure requirement of the metal above and below.
- **Non-orthogonal geometry:** Any non-Manhattan (non-90-degree) edges are likely to cause violations in ASAP7, which expects orthogonal (rectilinear) geometry.
- **Exact-width/pitch layers:** FIN and GATE require exact dimensions. Any deviation, even by 1 dbu, causes a violation.
- **Wide-metal spacing:** Some spacing rules increase when one or both shapes exceed a width threshold. A shape that passes normal spacing may fail wide-metal spacing.
- **Minimum area:** Small shapes (e.g., short metal stubs) may fail area rules even if their width and spacing are correct.

### Counting Violations

- Each distinct violation location counts as one violation for its rule.
- If a shape violates the same rule on two different edges, that is two violations.
- The DRC summary reports total count per rule. Sum all rule counts for the total violation count.

---

## 7. DRC Report Format (`.drc.json`)

DRC reports are structured JSON files stored in `drc_report/`. This is the format the agent reads.

```json
{
  "case_name": "Cell100",
  "design_type": "cell",
  "total_violations": 20,
  "total_rules_violated": 2,
  "rules": {
    "M1.S.4": {
      "violation_count": 1,
      "description": "Minimum spacing of M1 on same track is 18 nm.",
      "violations": [
        {
          "type": "edge_pair",
          "edges": [[1768, 832, 1840, 832], [1768, 944, 1840, 944]],
          "bbox": [1768, 832, 1840, 944]
        }
      ]
    }
  }
}
```

- `rules`: object keyed by rule name; each entry has `violation_count` and a `violations` array.
- `violations`: each entry has a `type` (`"edge_pair"` for spacing rules, `"bbox"` for others), geometry coordinates in dbu (integer database units; 1 dbu = 0.00025 um), and a `bbox` field.
- To get the total violation count for a rule, read `rules[rule_name]["violation_count"]`.
- Rules not present in `rules` (or with `violation_count == 0`) passed with no violations.

---

## 8. Layout Script Patterns (pya API)

The benchmark test cases use KLayout Python scripts (`pya` API) to generate GDS layouts.
All coordinates are integers in **dbu** (database units; 1 dbu = 0.00025 um = 0.25 nm).

### Polygon-Level Scripts

Polygon test cases are simple: one top cell, one or two layers, a few shapes.

```python
import pya

layout = pya.Layout()
layout.dbu = 0.00025

top_cell = layout.create_cell("M1.S.4")

m1_layer = layout.layer(19, 0)

m1_1 = pya.Polygon([pya.Point(0, 0), pya.Point(80, 0), pya.Point(80, 200), pya.Point(0, 200)])
top_cell.shapes(m1_layer).insert(m1_1)

m1_2 = pya.Polygon([pya.Point(0, 312), pya.Point(80, 312), pya.Point(80, 512), pya.Point(0, 512)])
top_cell.shapes(m1_layer).insert(m1_2)

layout.write("M1.S.4.gds")
```

Key patterns:
- Layers created with `layout.layer(layer_number, datatype)` (shorthand) or `layout.layer(pya.LayerInfo(layer_number, datatype))`
- All shapes are `pya.Polygon` with `pya.Point` vertices (no `pya.Box` usage)
- Variable names like `m1_1`, `m1_2` or `active`, `nselect`

### Cell-Level Scripts

Cell test cases have a single top cell with shapes on multiple layers (M0, M1, V0).
Variable names follow the pattern `polygon_<net>_<index>`.

```python
import pya

layout = pya.Layout()
layout.dbu = 0.00025

top_cell = layout.create_cell("Cell1")

polygon_N1_0 = pya.Polygon([ pya.Point(520, 716), pya.Point(696, 716), pya.Point(696, 788), pya.Point(520, 788), ])
top_cell.shapes(layout.layer(pya.LayerInfo(0, 0))).insert(polygon_N1_0)   # M0

polygon_N1_28 = pya.Polygon([ pya.Point(616, 656), pya.Point(688, 656), pya.Point(688, 1264), pya.Point(616, 1264), ])
top_cell.shapes(layout.layer(pya.LayerInfo(19, 0))).insert(polygon_N1_28)  # M1

polygon_N1_44 = pya.Polygon([ pya.Point(616, 1148), pya.Point(688, 1148), pya.Point(688, 1220), pya.Point(616, 1220), ])
top_cell.shapes(layout.layer(pya.LayerInfo(18, 0))).insert(polygon_N1_44)  # V0

layout.write("Cell1.gds")
```

Key patterns:
- Layer specified inline: `layout.layer(pya.LayerInfo(layer_number, 0))`
- Layers used: M0 (0), M1 (19), V0 (18)
- All shapes are 4-point rectangles expressed as `pya.Polygon`

### Block-Level Scripts

Block test cases have multiple cells (standard cells, via cells) with a top cell
that instantiates them. Much larger — hundreds of shapes across many layers.

```python
import pya

layout = pya.Layout()
layout.dbu = 0.00025

# Create sub-cells
cell_VIA_VIA12 = layout.create_cell("VIA_VIA12")
cell_BUFx2_ASAP7_75t_R = layout.create_cell("BUFx2_ASAP7_75t_R")
cell_vedic2x2 = layout.create_cell("vedic2x2")

# Shapes in sub-cells
p0 = pya.Polygon([pya.Point(-56, -36), pya.Point(-56, 36), pya.Point(56, 36), pya.Point(56, -36)])
cell_VIA_VIA12.shapes(layout.layer(pya.LayerInfo(20, 0))).insert(p0)  # M2

# Cell instances in the top cell
cell_vedic2x2.insert(pya.CellInstArray(cell_BUFx2_ASAP7_75t_R.cell_index(),
    pya.Trans(pya.Point(x, y))))

layout.write("vedic2x2.gds")
```

Key patterns:
- Multiple cells created with `layout.create_cell()`
- Variable names: `p0`, `p1`, ... for shapes; `cell_<name>` for cells
- Uses `pya.CellInstArray` and `pya.Trans` for cell placement
- Layers span the full stack: M0-M5, V0-V4, WELL, FIN, GATE, ACTIVE, GCUT, LIG, LISD, SDT, etc.

### Common Rules for All Scripts

- `layout.dbu` is always `0.00025` (0.25 nm per dbu)
- All coordinates are integers in dbu
- All shapes are `pya.Polygon` with `pya.Point` vertices
- The script ends with `layout.write("<filename>.gds")`
- The top cell name matches the test case name

---

## Quick Reference: Layer Number to Name

```
 0 -> M0       1 -> WELL     2 -> FIN      7 -> GATE
10 -> GCUT    11 -> ACTIVE  16 -> LIG     17 -> LISD
18 -> V0      19 -> M1      20 -> M2      21 -> V1
25 -> V2      30 -> M3      35 -> V3      40 -> M4
45 -> V4      50 -> M5      55 -> V5      60 -> M6
65 -> V6      70 -> M7      75 -> V7      80 -> M8
85 -> V8      90 -> M9      95 -> V9
```

## Quick Reference: Common dbu Values

| Nanometers | dbu |
|---|---|
| 7 nm | 28 |
| 14 nm | 56 |
| 18 nm | 72 |
| 20 nm | 80 |
| 27 nm | 108 |
| 36 nm | 144 |
| 54 nm | 216 |
| 108 nm | 432 |
