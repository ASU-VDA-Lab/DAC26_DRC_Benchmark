#BSD 3-Clause License
#
#Copyright (c) 2026, ASU-VDA-Lab
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#
#1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#3. Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#################################################################################
# process_klayout_reports.py — Convert KLayout DRC .lyrpt XML reports to structured .drc.json files.
#
# Usage:
#     # Single-file mode:
#     python3 evaluator/process_klayout_reports.py \
#         --lyrpt testcase/asap7/cell/drc_report/Cell1.lyrpt \
#         --output testcase/asap7/cell/drc_report/Cell1.drc.json \
#         --case_name Cell1 --design_type cell
#
#     # Batch mode (scan all known testcase directories):
#     python3 evaluator/process_klayout_reports.py [--workspace /path/to/workspace]
#
# The .lyrpt format is produced by KLayout DRC and is an XML report-database.
# This script parses:
#   - <categories>: maps rule names to human-readable descriptions.
#   - <items>:       one <item> per violation, containing geometry in <values>/<value>.
#
# Geometry value formats handled:
#   edge: (x1,y1;x2,y2)
#   edge-pair: (x1,y1;x2,y2)/(x3,y3;x4,y4)
#   polygon: (x1,y1;x2,y2;...;xn,yn)

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ASAP7 layer name -> layer number (from agent/skill.md).
# Used by the optional --layout-script post-processing to look up polygons by layer.
_LAYER_NAME_TO_NUM = {
    "M0": 0, "WELL": 1, "FIN": 2, "GATE": 7, "GCUT": 10, "ACTIVE": 11,
    "LIG": 16, "LISD": 17, "V0": 18, "M1": 19, "M2": 20, "V1": 21,
    "V2": 25, "M3": 30, "V3": 35, "M4": 40, "V4": 45, "M5": 50,
    "V5": 55, "M6": 60, "V6": 65, "M7": 70, "V7": 75, "M8": 80,
    "V8": 85, "M9": 90, "V9": 95,
}

_DBU_PER_UM = 1.0 / 0.00025  # 4000 dbu per um


# ---------------------------------------------------------------------------
# Coordinate / geometry parsing helpers
# ---------------------------------------------------------------------------

def _um_to_dbu(val: float) -> int:
    # Convert a micron value to dbu (1 dbu = 0.00025 um).
    return int(round(val * _DBU_PER_UM))


def _parse_point(token: str) -> List[int]:
    # Parse a 'x,y' token (in microns from KLayout) into [x, y] as dbu integers.
    parts = token.strip().split(",")
    if len(parts) != 2:
        raise ValueError(f"Expected 'x,y', got: {token!r}")
    return [_um_to_dbu(float(parts[0])), _um_to_dbu(float(parts[1]))]


def _parse_edge_string(edge_str: str) -> List[int]:
    # Parse a parenthesised edge string '(x1,y1;x2,y2)' into
    # [x1, y1, x2, y2] in dbu.
    edge_str = edge_str.strip().lstrip("(").rstrip(")")
    halves = edge_str.split(";")
    if len(halves) != 2:
        raise ValueError(f"Expected two points in edge, got: {edge_str!r}")
    p1 = _parse_point(halves[0])
    p2 = _parse_point(halves[1])
    return [p1[0], p1[1], p2[0], p2[1]]


def _bbox_from_coords(coords: List[int]) -> List[int]:
    # Compute axis-aligned bounding box [min_x, min_y, max_x, max_y]
    # from a flat list of alternating x, y values (in dbu).
    xs = coords[0::2]
    ys = coords[1::2]
    return [min(xs), min(ys), max(xs), max(ys)]


def parse_geometry(value_text: str) -> dict:
    # Parse a single <value> text from a KLayout lyrpt report and return
    # a violation dict with keys 'type', geometry fields, and 'bbox'.
    #
    # Supported formats
    # -----------------
    # edge:      edge: (x1,y1;x2,y2)
    # edge-pair: edge-pair: (x1,y1;x2,y2)/(x3,y3;x4,y4)
    # polygon:   polygon: (x1,y1;x2,y2;...;xn,yn)
    value_text = value_text.strip()

    if value_text.startswith("edge-pair:"):
        body = value_text[len("edge-pair:"):].strip()
        # Split on '/' or '|' that separates the two parenthesised edges.
        # Each part is of the form (x1,y1;x2,y2).
        edge_parts = re.split(r"[/|](?=\()", body)
        if len(edge_parts) != 2:
            raise ValueError(f"Cannot split edge-pair into two edges: {body!r}")
        edge1 = _parse_edge_string(edge_parts[0])
        edge2 = _parse_edge_string(edge_parts[1])
        all_coords = edge1 + edge2
        return {
            "type": "edge_pair",
            "edges": [edge1, edge2],
            "bbox": _bbox_from_coords(all_coords),
        }

    if value_text.startswith("edge:"):
        body = value_text[len("edge:"):].strip()
        edge = _parse_edge_string(body)
        return {
            "type": "edge",
            "edges": [edge],
            "bbox": _bbox_from_coords(edge),
        }

    if value_text.startswith("polygon:"):
        body = value_text[len("polygon:"):].strip().lstrip("(").rstrip(")")
        # A polygon-with-hole uses '/' to separate the outer ring from hole ring(s)
        # within the same parenthesis group, e.g.:
        #   -0.001,-0.001;-0.001,0.051;0.051,0.051;0.051,-0.001/0.001,0.001;...
        # Split on '/' first to get individual rings; collect all vertices.
        rings_raw = body.split("/")
        all_vertices = []
        all_coords = []  # type: List[float]
        for ring_raw in rings_raw:
            point_tokens = ring_raw.split(";")
            for t in point_tokens:
                t = t.strip()
                if t:
                    pt = _parse_point(t)
                    all_vertices.append(pt)
                    all_coords.extend(pt)
        return {
            "type": "polygon",
            "vertices": all_vertices,
            "bbox": _bbox_from_coords(all_coords),
        }

    raise ValueError(f"Unrecognised geometry value format: {value_text!r}")


# ---------------------------------------------------------------------------
# .lyrpt XML parsing
# ---------------------------------------------------------------------------

def parse_lyrpt(lyrpt_path: str) -> dict:
    # Parse a KLayout .lyrpt XML report and return a raw data dict:
    #
    #     {
    #         "top_cell": str,
    #         "description_map": {rule_name: description_text, ...},
    #         "violations_by_rule": {rule_name: [violation_dict, ...], ...},
    #     }
    tree = ET.parse(lyrpt_path)
    root = tree.getroot()

    # ------------------------------------------------------------------
    # 1. Top-cell name
    # ------------------------------------------------------------------
    top_cell_el = root.find("top-cell")
    top_cell = top_cell_el.text.strip() if top_cell_el is not None and top_cell_el.text else ""

    # ------------------------------------------------------------------
    # 2. Build description map from <categories> section
    # ------------------------------------------------------------------
    description_map = {}  # type: Dict[str, str]
    categories_el = root.find("categories")
    if categories_el is not None:
        for cat in categories_el.findall("category"):
            name_el = cat.find("name")
            desc_el = cat.find("description")
            if name_el is not None and name_el.text:
                rule_name = name_el.text.strip()
                description = desc_el.text.strip() if (desc_el is not None and desc_el.text) else ""
                description_map[rule_name] = description

    # ------------------------------------------------------------------
    # 3. Parse <items> section
    # ------------------------------------------------------------------
    violations_by_rule = {}  # type: Dict[str, List[dict]]

    items_el = root.find("items")
    if items_el is not None:
        for item in items_el.findall("item"):
            # Extract rule name, stripping surrounding single-quotes if present.
            category_el = item.find("category")
            if category_el is None or not category_el.text:
                continue
            raw_category = category_el.text.strip()
            rule_name = raw_category.strip("'")

            # Parse all <value> children within <values>.
            values_el = item.find("values")
            if values_el is None:
                continue
            for value_el in values_el.findall("value"):
                if value_el.text is None:
                    continue
                try:
                    violation = parse_geometry(value_el.text)
                except ValueError as exc:
                    print(
                        f"WARNING: Could not parse geometry in {lyrpt_path!r} "
                        f"for rule {rule_name!r}: {exc}",
                        file=sys.stderr,
                    )
                    continue
                violations_by_rule.setdefault(rule_name, []).append(violation)

    return {
        "top_cell": top_cell,
        "description_map": description_map,
        "violations_by_rule": violations_by_rule,
    }


# ---------------------------------------------------------------------------
# Dot-to-polygon lookup (optional post-processing)
#
# A "dot" violation has a zero-area bbox (width=0 AND height=0), produced by
# KLayout grid-alignment rules such as M4.AUX.1.  We locate the polygon on the
# relevant layer that has this dot as a vertex, then replace the violation's
# bbox with that polygon's bbox so downstream geometry-based scorers can match
# predictions against it.
# ---------------------------------------------------------------------------

def _parse_layout_polygons(script_path: str) -> Dict[int, List[List[Tuple[int, int]]]]:
    # Parse a KLayout Python layout script and flatten all shapes to
    # top-cell dbu coordinates.  Returns {layer_num: [[(x,y), ...], ...]}.
    #
    # Handles cell hierarchy: sub-cells are instantiated with pya.Trans
    # transforms; we compose transforms recursively.
    with open(script_path) as f:
        src = f.read()

    poly_def = re.compile(
        r'^\s*(\w+)\s*=\s*pya\.Polygon\(\s*\[(.*?)\]\s*\)\s*$', re.MULTILINE)
    box_def = re.compile(
        r'^\s*(\w+)\s*=\s*pya\.Box\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*$',
        re.MULTILINE)
    point_re = re.compile(r'pya\.Point\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)')
    insert_layerinfo = re.compile(
        r'(\w+)\.shapes\(\s*layout\.layer\(\s*pya\.LayerInfo\(\s*(\d+)\s*,\s*\d+\s*\)\s*\)\s*\)\.insert\(\s*(\w+)\s*\)')
    insert_num = re.compile(
        r'(\w+)\.shapes\(\s*layout\.layer\(\s*(\d+)\s*,\s*\d+\s*\)\s*\)\.insert\(\s*(\w+)\s*\)')
    insert_var = re.compile(
        r'(\w+)\.shapes\(\s*(\w+)\s*\)\.insert\(\s*(\w+)\s*\)')
    # Inline insertion: cell.shapes(...).insert(pya.Polygon([...]))  or pya.Box(...)
    inline_poly_layerinfo = re.compile(
        r'(\w+)\.shapes\(\s*layout\.layer\(\s*pya\.LayerInfo\(\s*(\d+)\s*,\s*\d+\s*\)\s*\)\s*\)'
        r'\.insert\(\s*pya\.Polygon\(\s*\[(.*?)\]\s*\)\s*\)',
        re.DOTALL)
    inline_poly_num = re.compile(
        r'(\w+)\.shapes\(\s*layout\.layer\(\s*(\d+)\s*,\s*\d+\s*\)\s*\)'
        r'\.insert\(\s*pya\.Polygon\(\s*\[(.*?)\]\s*\)\s*\)',
        re.DOTALL)
    inline_poly_var = re.compile(
        r'(\w+)\.shapes\(\s*(\w+)\s*\)'
        r'\.insert\(\s*pya\.Polygon\(\s*\[(.*?)\]\s*\)\s*\)',
        re.DOTALL)
    inline_box_layerinfo = re.compile(
        r'(\w+)\.shapes\(\s*layout\.layer\(\s*pya\.LayerInfo\(\s*(\d+)\s*,\s*\d+\s*\)\s*\)\s*\)'
        r'\.insert\(\s*pya\.Box\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*\)')
    inline_box_num = re.compile(
        r'(\w+)\.shapes\(\s*layout\.layer\(\s*(\d+)\s*,\s*\d+\s*\)\s*\)'
        r'\.insert\(\s*pya\.Box\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*\)')
    inline_box_var = re.compile(
        r'(\w+)\.shapes\(\s*(\w+)\s*\)'
        r'\.insert\(\s*pya\.Box\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*\)')
    layer_var = re.compile(
        r'^\s*(\w+)\s*=\s*layout\.layer\(\s*(?:pya\.LayerInfo\(\s*)?(\d+)\s*,\s*\d+\s*\)?\s*\)\s*$',
        re.MULTILINE)
    cell_alias_re = re.compile(
        r'^\s*(top_cell|cell_\w+)\s*=\s*layout\.create_cell\(\s*[\'"]([^\'"]+)[\'"]\s*\)\s*$',
        re.MULTILINE)
    instance_re = re.compile(
        r'(\w+)\.insert\(\s*pya\.CellInstArray\(\s*(\w+)\.cell_index\(\)\s*,\s*'
        r'pya\.Trans\(\s*(\d+|pya\.Trans\.R\d+)\s*(?:,\s*(True|False))?\s*,\s*'
        r'pya\.(?:Vector|Point)\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*\)\s*\)\s*\)')

    polys: Dict[str, List[Tuple[int, int]]] = {}
    for m in poly_def.finditer(src):
        polys[m.group(1)] = [(int(px), int(py))
                              for px, py in point_re.findall(m.group(2))]
    for m in box_def.finditer(src):
        name, x1, y1, x2, y2 = m.groups()
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        polys[name] = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]

    layer_vars: Dict[str, int] = {}
    for m in layer_var.finditer(src):
        layer_vars[m.group(1)] = int(m.group(2))

    cell_aliases = [m.group(1) for m in cell_alias_re.finditer(src)]
    if "top_cell" in cell_aliases:
        top_alias = "top_cell"
    else:
        top_alias = cell_aliases[-1] if cell_aliases else None

    cell_shapes: Dict[str, Dict[int, List[str]]] = {}
    for m in insert_layerinfo.finditer(src):
        c, ln, p = m.group(1), int(m.group(2)), m.group(3)
        cell_shapes.setdefault(c, {}).setdefault(ln, []).append(p)
    for m in insert_num.finditer(src):
        c, ln, p = m.group(1), int(m.group(2)), m.group(3)
        cell_shapes.setdefault(c, {}).setdefault(ln, []).append(p)
    for m in insert_var.finditer(src):
        c, var, p = m.group(1), m.group(2), m.group(3)
        if var in layer_vars:
            ln = layer_vars[var]
            existing = cell_shapes.get(c, {}).get(ln, [])
            if p not in existing:
                cell_shapes.setdefault(c, {}).setdefault(ln, []).append(p)

    # Inline shape insertions (polygon/box defined inside .insert(...)).
    # Synthesise a name so they flow through the same flattening pipeline.
    inline_idx = [0]

    def _add_inline_poly(cell_alias, layer_num, vertices):
        name = f"__inline_{inline_idx[0]}"
        inline_idx[0] += 1
        polys[name] = vertices
        cell_shapes.setdefault(cell_alias, {}).setdefault(layer_num, []).append(name)

    for m in inline_poly_layerinfo.finditer(src):
        c, ln = m.group(1), int(m.group(2))
        pts = [(int(px), int(py)) for px, py in point_re.findall(m.group(3))]
        if pts:
            _add_inline_poly(c, ln, pts)
    for m in inline_poly_num.finditer(src):
        c, ln = m.group(1), int(m.group(2))
        pts = [(int(px), int(py)) for px, py in point_re.findall(m.group(3))]
        if pts:
            _add_inline_poly(c, ln, pts)
    for m in inline_poly_var.finditer(src):
        c, var = m.group(1), m.group(2)
        if var not in layer_vars:
            continue
        ln = layer_vars[var]
        pts = [(int(px), int(py)) for px, py in point_re.findall(m.group(3))]
        if pts:
            _add_inline_poly(c, ln, pts)
    for m in inline_box_layerinfo.finditer(src):
        c, ln = m.group(1), int(m.group(2))
        x1, y1, x2, y2 = (int(m.group(i)) for i in (3, 4, 5, 6))
        _add_inline_poly(c, ln, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
    for m in inline_box_num.finditer(src):
        c, ln = m.group(1), int(m.group(2))
        x1, y1, x2, y2 = (int(m.group(i)) for i in (3, 4, 5, 6))
        _add_inline_poly(c, ln, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
    for m in inline_box_var.finditer(src):
        c, var = m.group(1), m.group(2)
        if var not in layer_vars:
            continue
        ln = layer_vars[var]
        x1, y1, x2, y2 = (int(m.group(i)) for i in (3, 4, 5, 6))
        _add_inline_poly(c, ln, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)])

    cell_instances: Dict[str, List[Tuple[str, int, bool, int, int]]] = {}
    for m in instance_re.finditer(src):
        parent, child = m.group(1), m.group(2)
        rot_str = m.group(3)
        if rot_str.startswith("pya.Trans.R"):
            rot = int(rot_str[len("pya.Trans.R"):]) // 90
        else:
            rot = int(rot_str)
        mirror = (m.group(4) == "True") if m.group(4) else False
        tx, ty = int(m.group(5)), int(m.group(6))
        cell_instances.setdefault(parent, []).append((child, rot, mirror, tx, ty))

    def apply_trans(pt, rot, mirror, tx, ty):
        x, y = pt
        if mirror:
            y = -y
        for _ in range(rot % 4):
            x, y = -y, x
        return (x + tx, y + ty)

    result: Dict[int, List[List[Tuple[int, int]]]] = {}

    def flatten(cell_alias, rot, mirror, tx, ty):
        for layer_num, poly_names in cell_shapes.get(cell_alias, {}).items():
            for pname in poly_names:
                if pname not in polys:
                    continue
                transformed = [apply_trans(pt, rot, mirror, tx, ty)
                               for pt in polys[pname]]
                result.setdefault(layer_num, []).append(transformed)
        for (child, crot, cmirror, ctx, cty) in cell_instances.get(cell_alias, []):
            new_tx, new_ty = apply_trans((ctx, cty), rot, mirror, tx, ty)
            new_rot = (rot + crot) % 4
            new_mirror = mirror ^ cmirror
            flatten(child, new_rot, new_mirror, new_tx, new_ty)

    if top_alias:
        flatten(top_alias, 0, False, 0, 0)
    return result


def _rule_to_layer_nums(rule_name: str) -> List[int]:
    # Extract layer number(s) referenced in a rule name (e.g. 'M4.AUX.1' -> [40]).
    nums = []
    for part in rule_name.split("."):
        if part in _LAYER_NAME_TO_NUM:
            nums.append(_LAYER_NAME_TO_NUM[part])
    return nums


def _find_polygon_with_vertex(
    layers: Dict[int, List[List[Tuple[int, int]]]],
    layer_nums: List[int],
    target_dbu: Tuple[int, int],
) -> Optional[Tuple[int, int, int, int]]:
    # Find the smallest polygon on any of the given layers that has target_dbu
    # as one of its vertices.  Returns the polygon's bbox in dbu, or None.
    matches = []
    for ln in layer_nums:
        for poly in layers.get(ln, []):
            if target_dbu in poly:
                xs = [v[0] for v in poly]
                ys = [v[1] for v in poly]
                matches.append((min(xs), min(ys), max(xs), max(ys)))
    if not matches:
        return None
    return min(matches, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))


def _canonical_edge(e):
    # Return an edge [x1,y1,x2,y2] with endpoints in canonical (sorted) order
    # so that (A->B) and (B->A) compare equal.
    p1 = (e[0], e[1])
    p2 = (e[2], e[3])
    if p1 <= p2:
        return [e[0], e[1], e[2], e[3]]
    return [e[2], e[3], e[0], e[1]]


def _violation_dedupe_key(v: dict) -> str:
    # Canonical key for a violation, used for dedup.
    #
    # For edge / edge_pair violations, KLayout emits edges with arbitrary
    # endpoint direction AND (for edge_pair) arbitrary edge ordering.
    # We canonicalise both so that A<->B and A'<->B' collapse correctly.
    # For other types we compare the dict verbatim (with sorted keys).
    vcopy = dict(v)
    edges = vcopy.get("edges")
    if isinstance(edges, list):
        edges = [_canonical_edge(e) for e in edges]
        if vcopy.get("type") == "edge_pair":
            edges.sort()
        vcopy["edges"] = edges
    return json.dumps(vcopy, sort_keys=True)


def dedupe_violations(data: dict) -> int:
    # Remove duplicate violations within each rule.  Two violations are
    # considered duplicates when their canonical key matches (see
    # _violation_dedupe_key).  Updates violation_count per rule and
    # total_violations on the data dict.  Returns the number of duplicates
    # removed.
    #
    # Why this matters:
    #   1. After the dot-to-polygon lookup KLayout's per-vertex dot reports
    #      collapse to the same polygon bbox.
    #   2. KLayout emits the two edges of an edge_pair in arbitrary order, so
    #      A->B and B->A show up as separate violations of the same spacing.
    removed = 0
    for rule, info in data.get("rules", {}).items():
        seen = set()
        deduped = []
        for v in info.get("violations", []):
            key = _violation_dedupe_key(v)
            if key in seen:
                removed += 1
                continue
            seen.add(key)
            deduped.append(v)
        info["violations"] = deduped
        info["violation_count"] = len(deduped)
    data["total_violations"] = sum(
        info.get("violation_count", 0) for info in data.get("rules", {}).values()
    )
    return removed


def apply_dot_to_polygon_lookup(data: dict, layout_script_path: str) -> int:
    # Replace dot violations (bbox with w=0 AND h=0) with the bbox of the polygon
    # they are a vertex of.  Modifies `data` in place.  Returns the number of
    # violations fixed.  Dots that cannot be matched are left unchanged.
    if not os.path.isfile(layout_script_path):
        print(
            f"WARNING: layout script not found ({layout_script_path}); "
            f"skipping dot-to-polygon lookup",
            file=sys.stderr,
        )
        return 0

    layers = None  # lazy-parse
    fixed = 0

    for rule_name, info in data.get("rules", {}).items():
        for v in info.get("violations", []):
            bb = v.get("bbox")
            if not bb:
                continue
            if (bb[2] - bb[0]) != 0 or (bb[3] - bb[1]) != 0:
                continue  # not a dot

            # bbox is already in dbu (integer) after parsing
            target_dbu = (bb[0], bb[1])

            layer_nums = _rule_to_layer_nums(rule_name)
            if not layer_nums:
                continue

            if layers is None:
                layers = _parse_layout_polygons(layout_script_path)

            poly_bbox = _find_polygon_with_vertex(layers, layer_nums, target_dbu)
            if poly_bbox is None:
                continue

            xmin, ymin, xmax, ymax = poly_bbox
            v["type"] = "polygon"
            v["bbox"] = [xmin, ymin, xmax, ymax]
            v["vertices"] = [
                [xmin, ymin], [xmin, ymax], [xmax, ymax], [xmax, ymin],
            ]
            v.pop("edges", None)
            fixed += 1

    return fixed


# ---------------------------------------------------------------------------
# Output JSON construction
# ---------------------------------------------------------------------------

def build_drc_json(
    parsed: dict,
    case_name: str,
    design_type: str,
) -> dict:
    # Build the output .drc.json dict from parsed lyrpt data.
    violations_by_rule = parsed["violations_by_rule"]
    description_map = parsed["description_map"]

    rules_dict = {}  # type: Dict[str, dict]
    total_violations = 0

    for rule_name, violations in violations_by_rule.items():
        count = len(violations)
        total_violations += count
        rules_dict[rule_name] = {
            "violation_count": count,
            "description": description_map.get(rule_name, ""),
            "violations": violations,
        }

    return {
        "case_name": case_name,
        "design_type": design_type,
        "total_violations": total_violations,
        "total_rules_violated": len(rules_dict),
        "rules": rules_dict,
    }


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def process_single_file(
    lyrpt_path: str,
    output_path: str,
    case_name: str,
    design_type: str,
    layout_script_path: Optional[str] = None,
) -> None:
    # Parse one .lyrpt file and write the corresponding .drc.json.
    # If layout_script_path is provided, apply the dot-to-polygon lookup so
    # zero-area grid-alignment violations are replaced with their containing
    # polygon's bbox.
    parsed = parse_lyrpt(lyrpt_path)
    output = build_drc_json(parsed, case_name, design_type)

    fixed_dots = 0
    if layout_script_path:
        fixed_dots = apply_dot_to_polygon_lookup(output, layout_script_path)

    # Always dedupe: KLayout may emit multiple violations with identical
    # geometry (especially after dot-to-polygon lookup collapses vertex-level
    # reports into polygon-level bboxes).
    removed_dups = dedupe_violations(output)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)

    notes = []
    if fixed_dots:
        notes.append(f"fixed {fixed_dots} dot(s)")
    if removed_dups:
        notes.append(f"dedup {removed_dups}")
    note = f"  [{', '.join(notes)}]" if notes else ""
    print(
        f"  Wrote {output['total_violations']} violation(s) across "
        f"{output['total_rules_violated']} rule(s) → {output_path}{note}"
    )


def run_batch(workspace: str, apply_dot_fix: bool = False) -> None:
    # Scan testcase/asap7/{cell,polygon,block}/drc_report/ for *.lyrpt files
    # and process each one, writing results to
    # testcase/asap7/{type}/drc_report/{case_name}.drc.json.
    # If apply_dot_fix is True, look up layout scripts at
    # testcase/asap7/{type}/layout_script/{case_name}.py and replace zero-area
    # dot violations with their containing polygon's bbox.
    design_types = ["cell", "polygon", "block"]
    base = os.path.join(workspace, "testcase", "asap7")
    total_processed = 0

    for design_type in design_types:
        drc_report_dir = os.path.join(base, design_type, "drc_report")
        script_dir = os.path.join(base, design_type, "layout_script")
        if not os.path.isdir(drc_report_dir):
            print(f"Skipping {drc_report_dir} (not found)")
            continue

        lyrpt_files = sorted(Path(drc_report_dir).glob("*.lyrpt"))
        if not lyrpt_files:
            print(f"No .lyrpt files found in {drc_report_dir}")
            continue

        print(f"\nProcessing {len(lyrpt_files)} file(s) in {drc_report_dir} ...")
        out_dir = os.path.join(base, design_type, "drc_report")

        for lyrpt_path in lyrpt_files:
            case_name = lyrpt_path.stem
            output_path = os.path.join(out_dir, f"{case_name}.drc.json")
            script_path = None
            if apply_dot_fix:
                script_path = os.path.join(script_dir, f"{case_name}.py")
            try:
                process_single_file(
                    str(lyrpt_path), output_path, case_name, design_type,
                    layout_script_path=script_path,
                )
                total_processed += 1
            except Exception as exc:
                print(
                    f"ERROR processing {lyrpt_path}: {exc}",
                    file=sys.stderr,
                )

    print(f"\nBatch complete. Processed {total_processed} file(s).")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert KLayout .lyrpt DRC reports to .drc.json files."
    )
    parser.add_argument(
        "--lyrpt",
        metavar="FILE",
        help="Path to the input .lyrpt file (single-file mode).",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Path to the output .drc.json file (single-file mode).",
    )
    parser.add_argument(
        "--case_name",
        metavar="NAME",
        help="Case name to embed in the JSON output (single-file mode).",
    )
    parser.add_argument(
        "--design_type",
        metavar="TYPE",
        help='Design type, e.g. "cell", "polygon", or "block" (single-file mode).',
    )
    parser.add_argument(
        "--workspace",
        metavar="DIR",
        default=None,
        help=(
            "Root workspace directory for batch mode "
            "(default: directory containing this script's parent)."
        ),
    )
    parser.add_argument(
        "--layout-script",
        metavar="FILE",
        default=None,
        help=(
            "Path to the layout script (.py) for single-file mode.  When "
            "provided, zero-area dot violations are replaced with the bbox "
            "of the polygon they are a vertex of."
        ),
    )
    parser.add_argument(
        "--fix-dots",
        action="store_true",
        help=(
            "In batch mode, look up layout_script/<case>.py for each case and "
            "apply dot-to-polygon lookup."
        ),
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Single-file mode: all four flags must be provided together.
    # ------------------------------------------------------------------
    single_mode_flags = [args.lyrpt, args.output, args.case_name, args.design_type]
    if any(single_mode_flags):
        missing = []
        if not args.lyrpt:
            missing.append("--lyrpt")
        if not args.output:
            missing.append("--output")
        if not args.case_name:
            missing.append("--case_name")
        if not args.design_type:
            missing.append("--design_type")
        if missing:
            parser.error(
                f"Single-file mode requires all of: --lyrpt, --output, "
                f"--case_name, --design_type. Missing: {', '.join(missing)}"
            )
        process_single_file(
            args.lyrpt, args.output, args.case_name, args.design_type,
            layout_script_path=args.layout_script,
        )
        return

    # ------------------------------------------------------------------
    # Batch mode
    # ------------------------------------------------------------------
    if args.workspace:
        workspace = args.workspace
    else:
        # Default: two levels up from this script (evaluator/ → repo root)
        workspace = str(Path(__file__).resolve().parent.parent)

    print(f"Batch mode. Workspace: {workspace}")
    run_batch(workspace, apply_dot_fix=args.fix_dots)


if __name__ == "__main__":
    main()
