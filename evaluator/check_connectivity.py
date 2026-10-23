#!/usr/bin/env python3
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
#check_connectivity.py — Validate that electrical connectivity is preserved
#after LLM DRC repair by comparing the golden connectivity JSON against the
#modified script's traced connectivity.
#
#Cell comparison rules (golden "paths"):
#  Step 1 — Seed validation: locate each golden seed polygon (M0) in the
#           modified script by canonical points. Missing seed → fail.
#  Step 2 — Endpoint validation per seed:
#           - M0 endpoints: canonical points must match exactly as a multiset.
#           - Other endpoints: count per layer must match.
#
#Block comparison rules (golden "terminals" + "pairs"):
#  Starts : standard-cell M1 polygons, plus the VDD/VSS M1 rails (top-cell M1
#           rectangles of rail height spanning at least half the outline).
#  Trace  : polygon-level BFS over metal (same-layer touch/overlap) and via
#           (positive-area overlap) adjacency. The BFS records and stops at
#           (a) any other standard-cell M1 polygon, and (b) any metal polygon
#           carrying (layer, 251) pin shapes (all its pins are recorded).
#           A start that reaches nothing is recorded as (start, null).
#  Compare: the multiset of (start, end) pairs, keyed by canonical points,
#           must match the golden exactly. Missing / extra start → fail.

import json
import re
import sys
import os
from collections import defaultdict, deque, Counter
from pathlib import Path

from shapely.geometry import Polygon as ShapelyPolygon
from shapely.ops import unary_union


# ===================================================================
# Constants
# ===================================================================

# --- Cell ---
CELL_STACK = [
    (0, 18, 19),    # M0 - V0 - M1
    (19, 21, 20),   # M1 - V1 - M2
]

CELL_METAL_LAYERS = set()
CELL_VIA_LAYERS = set()
for _b, _v, _a in CELL_STACK:
    CELL_METAL_LAYERS.add(_b)
    CELL_METAL_LAYERS.add(_a)
    CELL_VIA_LAYERS.add(_v)
CELL_ALL_LAYERS = CELL_METAL_LAYERS | CELL_VIA_LAYERS
CELL_SEED_LAYER = 0
CELL_VIA_TO_BELOW_ABOVE = {v: (b, a) for b, v, a in CELL_STACK}

# --- Block ---
BLOCK_STACK = [
    (19, 21, 20),   (20, 25, 30),   (30, 35, 40),
    (40, 45, 50),   (50, 55, 60),   (60, 65, 70),
    (70, 75, 80),   (80, 85, 90),   (90, 95, 96),
]

BLOCK_METAL_LAYERS = set()
BLOCK_VIA_LAYERS = set()
for _b, _v, _a in BLOCK_STACK:
    BLOCK_METAL_LAYERS.add(_b)
    BLOCK_METAL_LAYERS.add(_a)
    BLOCK_VIA_LAYERS.add(_v)
BLOCK_ALL_LAYERS = BLOCK_METAL_LAYERS | BLOCK_VIA_LAYERS
BLOCK_SEED_LAYER = 19
BLOCK_VIA_TO_BELOW_ABOVE = {v: (b, a) for b, v, a in BLOCK_STACK}

BLOCK_PIN_DATATYPE = 251
BLOCK_OUTLINE_LAYER = 235
BLOCK_RAIL_HEIGHT = 72          # VDD/VSS M1 rail height (18 nm)
BLOCK_GRID_BUCKET = 2048        # spatial-index bucket size (dbu)

# Metal above-via lookup (for directional rule)
CELL_METAL_ABOVE_VIA = {b: v for b, v, a in CELL_STACK}


# ===================================================================
# Regex patterns
# ===================================================================

# Cell
RE_CELL_TOP = re.compile(
    r'^top_cell\s*=\s*layout\.create_cell\("([^"]+)"\)')
RE_CELL_POLY_START = re.compile(
    r'^(\w+)\s*=\s*pya\.Polygon\(\[')
RE_CELL_POINT = re.compile(
    r'pya\.Point\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)')
RE_CELL_INSERT = re.compile(
    r'^top_cell\.shapes\(layout\.layer\(pya\.LayerInfo\('
    r'\s*(\d+)\s*,\s*(\d+)\s*\)\)\)\.insert\((\w+)\)')

# Block
RE_BLK_CREATE_CELL = re.compile(
    r'^(\w+)\s*=\s*layout\.create_cell\("([^"]+)"\)')
RE_BLK_POLY_DEF = re.compile(
    r'^(\w+)\s*=\s*pya\.Polygon\((.+)\)')
RE_BLK_POINT = re.compile(
    r'pya\.Point\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)')
RE_BLK_SHAPE_INSERT = re.compile(
    r'^(\w+)\.shapes\(layout\.layer\(pya\.LayerInfo\((\d+),\s*(\d+)\)\)\)'
    r'\.insert\((\w+)\)')
RE_BLK_CELL_INST = re.compile(
    r'^(\w+)\.insert\(pya\.CellInstArray\((\w+)\.cell_index\(\)\s*,\s*'
    r'pya\.Trans\(\s*(\d+)\s*,\s*(True|False)\s*,\s*'
    r'pya\.Vector\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*\)\s*\)\s*\)')


# ===================================================================
# Shared utilities
# ===================================================================

def canonicalize_points(points):
    n = len(points)
    if n < 3:
        return [[int(x), int(y)] for x, y in points]
    min_idx = min(range(n), key=lambda i: points[i])
    rotated = list(points[min_idx:]) + list(points[:min_idx])
    area = 0
    for i in range(n):
        x1, y1 = rotated[i]
        x2, y2 = rotated[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    if area < 0:
        rotated = [rotated[0]] + list(reversed(rotated[1:]))
    return [[int(x), int(y)] for x, y in rotated]


def points_key(points):
    return tuple(tuple(p) for p in points)


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1


def compute_bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


def bboxes_touch_or_overlap(a, b):
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def bboxes_strict_overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def safe_polygon(points):
    try:
        p = ShapelyPolygon(points)
        if not p.is_valid:
            p = p.buffer(0)
            if p.is_empty:
                return None
        return p
    except Exception:
        return None


# ===================================================================
# Cell parser
# ===================================================================

def parse_cell_script(script_path):
    top_cell_name = None
    var_to_points = {}
    var_to_layer = {}
    current_var = None
    collecting_points = False
    current_points = []

    with Path(script_path).open("r") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if top_cell_name is None:
                m = RE_CELL_TOP.match(line)
                if m:
                    top_cell_name = m.group(1)
                    continue
            if not collecting_points:
                m = RE_CELL_POLY_START.match(line)
                if m:
                    current_var = m.group(1)
                    collecting_points = True
                    current_points = []
            if collecting_points:
                for pt in RE_CELL_POINT.finditer(line):
                    current_points.append(
                        (int(pt.group(1)), int(pt.group(2))))
                if "])" in line:
                    if current_var and current_points:
                        var_to_points[current_var] = current_points
                    collecting_points = False
                    current_var = None
                    current_points = []
                continue
            m = RE_CELL_INSERT.match(line)
            if m:
                layer = int(m.group(1))
                datatype = int(m.group(2))
                var_name = m.group(3)
                if datatype == 0 and layer in CELL_ALL_LAYERS:
                    var_to_layer[var_name] = layer

    polygons_by_layer = defaultdict(list)
    for var_name, layer in var_to_layer.items():
        if var_name in var_to_points:
            polygons_by_layer[layer].append({
                "points": var_to_points[var_name],
                "source_cell": top_cell_name or "unknown",
            })
    return top_cell_name, dict(polygons_by_layer)


# ===================================================================
# Block parser (with transforms and source-cell tracking)
# ===================================================================

def apply_trans(rot, mirror, dx, dy, px, py):
    stored_rot = (rot | 4) if mirror else (rot & 3)
    if stored_rot == 0:   rx, ry = px, py
    elif stored_rot == 1: rx, ry = -py, px
    elif stored_rot == 2: rx, ry = -px, -py
    elif stored_rot == 3: rx, ry = py, -px
    elif stored_rot == 4: rx, ry = px, -py
    elif stored_rot == 5: rx, ry = py, px
    elif stored_rot == 6: rx, ry = -px, py
    else:                 rx, ry = -py, -px
    return rx + dx, ry + dy


def transform_points(rot, mirror, dx, dy, points):
    return [apply_trans(rot, mirror, dx, dy, x, y) for x, y in points]


def compose_trans(p_rot, p_mirror, p_dx, p_dy, c_rot, c_mirror, c_dx, c_dy):
    def apply_both(px, py):
        ix, iy = apply_trans(c_rot, c_mirror, c_dx, c_dy, px, py)
        return apply_trans(p_rot, p_mirror, p_dx, p_dy, ix, iy)
    ox, oy = apply_both(0, 0)
    ex, ey = apply_both(1, 0)
    col_x = (ex - ox, ey - oy)
    fx, fy = apply_both(0, 1)
    det = (ex - ox) * (fy - oy) - (fx - ox) * (ey - oy)
    is_mirror = (det < 0)
    if col_x == (1, 0):   n_rot = 0
    elif col_x == (0, 1): n_rot = 1
    elif col_x == (-1, 0): n_rot = 2
    else:                   n_rot = 3
    return n_rot, is_mirror, ox, oy


def parse_block_script(script_path):
    with Path(script_path).open("r") as fh:
        lines = fh.readlines()

    var_to_cell_name = {}
    cell_shapes = defaultdict(lambda: defaultdict(list))
    cell_children = defaultdict(list)
    poly_points = {}

    for line in lines:
        line = line.rstrip()
        m = RE_BLK_CREATE_CELL.match(line)
        if m:
            var_to_cell_name[m.group(1)] = m.group(2)

    for line in lines:
        line = line.rstrip()
        m = RE_BLK_POLY_DEF.match(line)
        if m:
            pts = [(int(p[0]), int(p[1]))
                   for p in RE_BLK_POINT.findall(m.group(2))]
            if pts:
                poly_points[m.group(1)] = pts

    for line in lines:
        line = line.rstrip()
        m = RE_BLK_SHAPE_INSERT.match(line)
        if m:
            cell_var, layer_s, dtype_s, shape_var = (
                m.group(1), m.group(2), m.group(3), m.group(4))
            layer_num = int(layer_s)
            if int(dtype_s) != 0 or layer_num not in BLOCK_ALL_LAYERS:
                continue
            if shape_var in poly_points and cell_var in var_to_cell_name:
                cell_shapes[cell_var][layer_num].append(
                    (poly_points[shape_var], var_to_cell_name[cell_var]))

    for line in lines:
        line = line.rstrip()
        m = RE_BLK_CELL_INST.match(line)
        if m:
            pv, cv = m.group(1), m.group(2)
            rot, mirror = int(m.group(3)), (m.group(4) == "True")
            dx, dy = int(m.group(5)), int(m.group(6))
            if pv in var_to_cell_name and cv in var_to_cell_name:
                cell_children[pv].append((cv, rot, mirror, dx, dy))

    top_var = None
    for line in lines:
        m = RE_BLK_CREATE_CELL.match(line.rstrip())
        if m:
            top_var = m.group(1)
    if top_var is None:
        return {}

    flat_shapes = defaultdict(list)

    def flatten(cell_var, rot, mirror, dx, dy, depth=0):
        if depth > 20:
            return
        for layer_num, shapes in cell_shapes[cell_var].items():
            for shape_pts, source_cell in shapes:
                flat_shapes[layer_num].append({
                    "points": transform_points(rot, mirror, dx, dy,
                                               shape_pts),
                    "source_cell": source_cell,
                })
        for cv, cr, cm, cd, cdy in cell_children[cell_var]:
            nr, nm, nd, ndy = compose_trans(rot, mirror, dx, dy,
                                            cr, cm, cd, cdy)
            flatten(cv, nr, nm, nd, ndy, depth + 1)

    flatten(top_var, 0, False, 0, 0)
    return dict(flat_shapes)


# ===================================================================
# Shared: merge, graph, prune, DFS, expand
# ===================================================================

def merge_same_layer_metals(polygons_by_layer, metal_layers):
    result = {}
    for layer in sorted(metal_layers):
        polys = polygons_by_layer.get(layer, [])
        n = len(polys)
        if n == 0:
            result[layer] = []
            continue
        shapely_polys = [safe_polygon(p["points"]) for p in polys]
        bboxes = [compute_bbox(p["points"]) for p in polys]
        uf = UnionFind(n)
        for i in range(n):
            if shapely_polys[i] is None:
                continue
            for j in range(i + 1, n):
                if shapely_polys[j] is None:
                    continue
                if not bboxes_touch_or_overlap(bboxes[i], bboxes[j]):
                    continue
                try:
                    inter = shapely_polys[i].intersection(shapely_polys[j])
                    if inter.is_empty:
                        continue
                    if inter.area > 0 or inter.length > 0:
                        uf.union(i, j)
                except Exception:
                    pass
        groups = defaultdict(list)
        for i in range(n):
            if shapely_polys[i] is not None:
                groups[uf.find(i)].append(i)
        entries = []
        for root, members in groups.items():
            ms = sorted(members)
            try:
                merged_shape = unary_union([shapely_polys[i] for i in ms])
            except Exception:
                merged_shape = shapely_polys[ms[0]]
            bounds = merged_shape.bounds
            mb = (int(round(bounds[0])), int(round(bounds[1])),
                  int(round(bounds[2])), int(round(bounds[3])))
            entries.append((mb, merged_shape, [polys[i] for i in ms]))
        entries.sort(key=lambda e: e[0])
        result[layer] = [
            {"super_id": idx, "merged_shape": s, "merged_bounds": b,
             "originals": o}
            for idx, (b, s, o) in enumerate(entries)
        ]
    return result


def build_graph(merged_metals, polygons_by_layer, via_layers,
                via_to_below_above):
    adj_set = defaultdict(set)
    vias = []
    for via_layer in sorted(via_layers):
        bl, al = via_to_below_above[via_layer]
        for vp in polygons_by_layer.get(via_layer, []):
            vs = safe_polygon(vp["points"])
            if vs is None:
                continue
            vb = compute_bbox(vp["points"])
            all_metals = set()
            for ml in (bl, al):
                for sp in merged_metals.get(ml, []):
                    if not bboxes_strict_overlap(vb, sp["merged_bounds"]):
                        continue
                    try:
                        if vs.intersection(sp["merged_shape"]).area > 0:
                            all_metals.add((ml, sp["super_id"]))
                    except Exception:
                        continue
            vi = len(vias)
            vias.append({"idx": vi, "layer": via_layer,
                         "points": vp["points"],
                         "source_cell": vp.get("source_cell", ""),
                         "all_metals": sorted(all_metals)})
            for k in all_metals:
                adj_set[k].add(vi)
    return {k: sorted(v) for k, v in adj_set.items()}, vias


def prune_redundant_vias(adjacent_vias, vias, via_layers,
                         via_to_below_above):
    kept = set()
    for via_layer in sorted(via_layers):
        bl, al = via_to_below_above[via_layer]
        layer_vias = [v for v in vias if v["layer"] == via_layer]
        groups = defaultdict(list)
        for v in layer_vias:
            bm = frozenset(m for m in v["all_metals"] if m[0] == bl)
            am = frozenset(m for m in v["all_metals"] if m[0] == al)
            if not bm or not am:
                kept.add(v["idx"])
                continue
            groups[(bm, am)].append(v)
        for grp in groups.values():
            grp.sort(key=lambda v: (
                (lambda b: ((b[2]-b[0])*(b[3]-b[1]), b))(
                    compute_bbox(v["points"]))))
            kept.add(grp[0]["idx"])
    new_adj = defaultdict(list)
    for v in vias:
        if v["idx"] in kept:
            for mk in v["all_metals"]:
                new_adj[mk].append(v["idx"])
    return {k: sorted(v) for k, v in new_adj.items()}, kept


def get_upper_vias_for(metal_key, adjacent_vias, vias, metal_above_via):
    ml = metal_key[0]
    av = metal_above_via.get(ml)
    if av is None:
        return []
    return [vi for vi in adjacent_vias.get(metal_key, [])
            if vias[vi]["layer"] == av]


def enumerate_paths(seed_key, adjacent_vias, vias, via_to_below_above,
                    metal_above_via):
    path_records = set()
    visited_vias = set()
    root_vl = adjacent_vias.get(seed_key, [])
    if not root_vl:
        path_records.add((seed_key, ('metal', seed_key)))
        return path_records
    stack = [[seed_key, root_vl, 0, None, None, 0, False]]
    while stack:
        fr = stack[-1]
        mk, vl = fr[0], fr[1]
        if fr[3] is None:
            picked = False
            while fr[2] < len(vl):
                vi = vl[fr[2]]
                fr[2] += 1
                if vi in visited_vias:
                    continue
                visited_vias.add(vi)
                via = vias[vi]
                cl = mk[0]
                om = [m for m in via["all_metals"] if m[0] != cl]
                if not om:
                    path_records.add((seed_key, ('dead_via', vi)))
                    visited_vias.discard(vi)
                    fr[6] = True
                    continue
                fr[3] = vi
                fr[4] = om
                fr[5] = 0
                fr[6] = True
                picked = True
                break
            if not picked:
                if not fr[6]:
                    path_records.add((seed_key, ('metal', mk)))
                stack.pop()
                continue
        if fr[5] < len(fr[4]):
            nm = fr[4][fr[5]]
            fr[5] += 1
            via_obj = vias[fr[3]]
            vbl, val = via_to_below_above[via_obj["layer"]]
            arrived_from_below = (nm[0] == val)
            child_all = adjacent_vias.get(nm, [])
            if not child_all:
                path_records.add((seed_key, ('metal', nm)))
                continue
            if arrived_from_below:
                upper = get_upper_vias_for(nm, adjacent_vias, vias,
                                           metal_above_via)
                if upper:
                    child_vl = upper
                else:
                    child_vl = child_all
            else:
                child_vl = child_all
            stack.append([nm, child_vl, 0, None, None, 0, False])
        else:
            visited_vias.discard(fr[3])
            fr[3] = None
            fr[4] = None
            fr[5] = 0
    return path_records


def expand_cell_path(seed_key, endpoint, merged_metals, vias):
    sl, ss = seed_key
    seed_origs = merged_metals[sl][ss]["originals"]
    if endpoint[0] == 'metal':
        el, es = endpoint[1]
        end_origs = merged_metals[el][es]["originals"]
    elif endpoint[0] == 'dead_via':
        via = vias[endpoint[1]]
        el = via["layer"]
        end_origs = [{"points": via["points"],
                      "source_cell": via["source_cell"]}]
    else:
        return
    for so in seed_origs:
        sp = canonicalize_points(so["points"])
        sc = so["source_cell"]
        for eo in end_origs:
            ep = canonicalize_points(eo["points"])
            ec = eo["source_cell"]
            yield {"start": {"layer": sl, "points": sp, "source_cell": sc},
                   "end": {"layer": el, "points": ep, "source_cell": ec}}


# ===================================================================
# Trace modified script
# ===================================================================

def trace_modified_cell(modified_script_path):
    _, polys = parse_cell_script(modified_script_path)
    merged = merge_same_layer_metals(polys, CELL_METAL_LAYERS)
    adj, vias = build_graph(merged, polys, CELL_VIA_LAYERS,
                            CELL_VIA_TO_BELOW_ABOVE)
    adj, _ = prune_redundant_vias(adj, vias, CELL_VIA_LAYERS,
                                  CELL_VIA_TO_BELOW_ABOVE)
    seeds = merged.get(CELL_SEED_LAYER, [])
    records = set()
    for sp in seeds:
        sk = (CELL_SEED_LAYER, sp["super_id"])
        records.update(enumerate_paths(
            sk, adj, vias, CELL_VIA_TO_BELOW_ABOVE,
            CELL_METAL_ABOVE_VIA))
    paths = []
    for sk, ep in sorted(records, key=lambda r: (r[0], str(r[1]))):
        for row in expand_cell_path(sk, ep, merged, vias):
            paths.append(row)

    # Tag cell endpoints: M0 -> pin=True, others -> pin=False
    for path in paths:
        path["end"]["pin"] = (path["end"]["layer"] == CELL_SEED_LAYER)

    return paths


# ===================================================================
# Block: polygon-level BFS producing (start, end) pairs
# ===================================================================

BLOCK_KIND_ORDER = {"pdn_rail": 0, "std_m1": 1, "pin": 2}


def parse_block_top_items(script_path):
    """Return (top_name, outline_bbox, pins) from a block layout script.

    pins: list of (layer, points) for (layer, 251) shapes on block metal
    layers inserted directly into the top cell. outline_bbox is the bbox of
    the top-cell (235, 0) shapes, or None when absent.
    """
    with Path(script_path).open("r") as fh:
        lines = [line.rstrip() for line in fh]

    var_to_cell_name = {}
    poly_points = {}
    top_var = None
    for line in lines:
        m = RE_BLK_CREATE_CELL.match(line)
        if m:
            var_to_cell_name[m.group(1)] = m.group(2)
            top_var = m.group(1)
            continue
        m = RE_BLK_POLY_DEF.match(line)
        if m:
            pts = [(int(p[0]), int(p[1]))
                   for p in RE_BLK_POINT.findall(m.group(2))]
            if pts:
                poly_points[m.group(1)] = pts

    pins = []
    outline_pts = []
    for line in lines:
        m = RE_BLK_SHAPE_INSERT.match(line)
        if not m or m.group(1) != top_var or m.group(4) not in poly_points:
            continue
        layer_num, datatype = int(m.group(2)), int(m.group(3))
        pts = poly_points[m.group(4)]
        if datatype == BLOCK_PIN_DATATYPE and layer_num in BLOCK_METAL_LAYERS:
            pins.append((layer_num, pts))
        elif layer_num == BLOCK_OUTLINE_LAYER and datatype == 0:
            outline_pts.extend(pts)

    outline = compute_bbox(outline_pts) if outline_pts else None
    return var_to_cell_name.get(top_var), outline, pins


def _rect_of(points):
    """Return (x0, y0, x1, y1) if points form an axis-aligned rectangle."""
    if len(points) != 4:
        return None
    for i in range(4):
        (ax, ay), (bx, by) = points[i], points[(i + 1) % 4]
        if ax != bx and ay != by:
            return None
    xs = sorted(set(p[0] for p in points))
    ys = sorted(set(p[1] for p in points))
    if len(xs) != 2 or len(ys) != 2:
        return None
    return (xs[0], ys[0], xs[1], ys[1])


class _BlockShape(object):
    __slots__ = ("layer", "points", "source_cell", "bbox", "rect", "_geom")

    def __init__(self, layer, points, source_cell):
        self.layer = layer
        self.points = points
        self.source_cell = source_cell
        self.bbox = compute_bbox(points)
        self.rect = _rect_of(points)
        self._geom = None

    def geom(self):
        if self._geom is None:
            self._geom = safe_polygon(self.points)
        return self._geom


def _shapes_connect(a, b, need_area):
    """Electrical contact test between two shapes.

    need_area=False (same-layer metal): overlap, or a shared edge segment of
    positive length. need_area=True (via-metal, pin-metal): positive-area
    overlap. Corner-only contact never connects.
    """
    ix = min(a.bbox[2], b.bbox[2]) - max(a.bbox[0], b.bbox[0])
    iy = min(a.bbox[3], b.bbox[3]) - max(a.bbox[1], b.bbox[1])
    if ix < 0 or iy < 0 or (ix == 0 and iy == 0):
        return False
    if need_area and (ix == 0 or iy == 0):
        return False
    if a.rect is not None and b.rect is not None:
        return True
    ga, gb = a.geom(), b.geom()
    if ga is None or gb is None:
        return False
    try:
        inter = ga.intersection(gb)
    except Exception:
        return False
    if inter.is_empty:
        return False
    return inter.area > 0 or (not need_area and inter.length > 0)


class _GridIndex(object):
    """Uniform-grid bbox index (shapely-version independent)."""

    def __init__(self, items, bucket=BLOCK_GRID_BUCKET):
        self.bucket = bucket
        self.cells = defaultdict(list)
        for idx, bb in items:
            for key in self._keys(bb):
                self.cells[key].append(idx)

    def _keys(self, bb):
        q = self.bucket
        for gx in range(bb[0] // q, bb[2] // q + 1):
            for gy in range(bb[1] // q, bb[3] // q + 1):
                yield (gx, gy)

    def query(self, bb):
        seen = set()
        for key in self._keys(bb):
            for idx in self.cells.get(key, ()):
                if idx not in seen:
                    seen.add(idx)
        return seen


class BlockGraph(object):
    """Flattened block shapes with metal/via adjacency and pin attachment."""

    def __init__(self, script_path):
        self.top_name, self.outline, pin_list = parse_block_top_items(
            script_path)
        flat = parse_block_script(script_path)
        self.shapes = []
        for layer in sorted(flat):
            for s in flat[layer]:
                self.shapes.append(
                    _BlockShape(layer, s["points"], s["source_cell"]))
        self.pins = [_BlockShape(layer, pts, self.top_name)
                     for layer, pts in pin_list]

        by_layer = defaultdict(list)
        for i, s in enumerate(self.shapes):
            by_layer[s.layer].append(i)
        index = {layer: _GridIndex([(i, self.shapes[i].bbox) for i in ids])
                 for layer, ids in by_layer.items()}

        self.adj = [set() for _ in self.shapes]
        for layer in sorted(BLOCK_METAL_LAYERS):
            for i in by_layer.get(layer, []):
                for j in index[layer].query(self.shapes[i].bbox):
                    if j > i and _shapes_connect(self.shapes[i],
                                                 self.shapes[j], False):
                        self.adj[i].add(j)
                        self.adj[j].add(i)
        for via_layer in sorted(BLOCK_VIA_LAYERS):
            for v in by_layer.get(via_layer, []):
                for ml in BLOCK_VIA_TO_BELOW_ABOVE[via_layer]:
                    if ml not in index:
                        continue
                    for m in index[ml].query(self.shapes[v].bbox):
                        if _shapes_connect(self.shapes[v], self.shapes[m],
                                           True):
                            self.adj[v].add(m)
                            self.adj[m].add(v)

        self.pins_on = defaultdict(list)
        for p, pin in enumerate(self.pins):
            if pin.layer not in index:
                continue
            for m in index[pin.layer].query(pin.bbox):
                if _shapes_connect(pin, self.shapes[m], True):
                    self.pins_on[m].append(p)

        if self.outline is not None:
            width = self.outline[2] - self.outline[0]
        elif self.shapes:
            width = (max(s.bbox[2] for s in self.shapes)
                     - min(s.bbox[0] for s in self.shapes))
        else:
            width = 0
        self.kind = [self._classify(s, width) for s in self.shapes]

    def _classify(self, s, outline_width):
        """Start kind of a shape: "std_m1", "pdn_rail" or None."""
        if s.layer != BLOCK_SEED_LAYER:
            return None
        if s.source_cell == self.top_name:
            r = s.rect
            if (r is not None and r[3] - r[1] == BLOCK_RAIL_HEIGHT
                    and 2 * (r[2] - r[0]) >= outline_width):
                return "pdn_rail"
            return None
        if s.source_cell.startswith("VIA_"):
            return None
        return "std_m1"

    def starts(self):
        return [i for i, k in enumerate(self.kind) if k is not None]

    def shape_key(self, i):
        s = self.shapes[i]
        return (self.kind[i], s.layer,
                points_key(canonicalize_points(s.points)))

    def pin_key(self, p):
        pin = self.pins[p]
        return ("pin", pin.layer,
                points_key(canonicalize_points(pin.points)))

    def endpoints(self, seed):
        """BFS from seed; stop at other std-cell M1 and at pin-carrying metal.

        Returns a list of end keys (one per distinct end shape / pin).
        """
        seen = {seed}
        queue = deque([seed])
        ends = []
        while queue:
            u = queue.popleft()
            if u != seed:
                if self.kind[u] == "std_m1":
                    ends.append(self.shape_key(u))
                    continue
                if self.pins_on.get(u):
                    ends.extend(self.pin_key(p) for p in self.pins_on[u])
                    continue
            elif self.pins_on.get(u):
                ends.extend(self.pin_key(p) for p in self.pins_on[u])
            for w in self.adj[u]:
                if w not in seen:
                    seen.add(w)
                    queue.append(w)
        return ends


def trace_block_pairs(script_path):
    """Trace a block script into a list of (start_key, end_key|None) pairs.

    Keys are (kind, layer, canonical points) with kind "pdn_rail", "std_m1"
    or "pin". Returns (graph, pairs).
    """
    g = BlockGraph(script_path)
    pairs = []
    for s in g.starts():
        sk = g.shape_key(s)
        ends = g.endpoints(s)
        if not ends:
            pairs.append((sk, None))
        for ek in sorted(ends):
            pairs.append((sk, ek))
    return g, pairs


def _terminal_sort_key(key):
    return (BLOCK_KIND_ORDER[key[0]], key[1], key[2])


def encode_block_pairs(case_name, pairs, extra=None):
    """Build the golden block JSON object (terminals + id pairs).

    extra: optional {terminal_key: {field: value}} merged into terminals
    (e.g. source_cell, net); comparison ignores these fields.
    """
    extra = extra or {}
    keys = set(s for s, _ in pairs) | set(e for _, e in pairs if e is not None)
    keys = sorted(keys, key=_terminal_sort_key)
    ids = {k: i for i, k in enumerate(keys)}
    terminals = []
    for k in keys:
        t = {"id": ids[k], "kind": k[0], "layer": k[1],
             "points": [list(p) for p in k[2]]}
        t.update(extra.get(k, {}))
        terminals.append(t)
    rows = sorted([ids[s], -1 if e is None else ids[e]] for s, e in pairs)
    return {
        "case": case_name,
        "design_type": "block",
        "num_terminals": len(terminals),
        "num_pairs": len(rows),
        "terminals": terminals,
        "pairs": [[s, None if e < 0 else e] for s, e in rows],
    }


def decode_block_pairs(data):
    keys = {}
    for t in data["terminals"]:
        pts = [tuple(p) for p in t["points"]]
        keys[t["id"]] = (t["kind"], t["layer"],
                         points_key(canonicalize_points(pts)))
    return [(keys[s], None if e is None else keys[e])
            for s, e in data["pairs"]]


def _key_to_json(key):
    return {"kind": key[0], "layer": key[1],
            "points": [list(p) for p in key[2]]}


def compare_block_pairs(golden_pairs, modified_pairs):
    gc = Counter(golden_pairs)
    mc = Counter(modified_pairs)
    missing = gc - mc
    extra = mc - gc

    g_seeds = set(s for s, _ in golden_pairs)
    m_seeds = set(s for s, _ in modified_pairs)
    missing_seeds = sorted(g_seeds - m_seeds, key=_terminal_sort_key)
    extra_seeds = sorted(m_seeds - g_seeds, key=_terminal_sort_key)
    skip = set(missing_seeds) | set(extra_seeds)

    # Per-seed endpoint differences, split into 251-pin vs std-cell M1 ends
    # (a lost or gained "no endpoint" record counts as an M1 difference).
    pin_diff = defaultdict(lambda: {"missing": [], "extra": []})
    m1_diff = defaultdict(lambda: {"missing": [], "extra": []})
    for side, counter in (("missing", missing), ("extra", extra)):
        for (s, e), n in counter.items():
            if s in skip:
                continue
            bucket = pin_diff if (e is not None and e[0] == "pin") else m1_diff
            bucket[s][side].extend([e] * n)

    def detail(diff):
        rows = []
        for s in sorted(diff, key=_terminal_sort_key)[:10]:
            d = diff[s]
            rows.append({
                "seed": _key_to_json(s),
                "missing_endpoints": [None if e is None else _key_to_json(e)
                                      for e in d["missing"][:5]],
                "extra_endpoints": [None if e is None else _key_to_json(e)
                                    for e in d["extra"][:5]],
                "missing_count": len(d["missing"]),
                "extra_count": len(d["extra"]),
            })
        return rows

    passed = not missing and not extra
    n_missing_pairs = sum(missing.values())
    n_extra_pairs = sum(extra.values())
    if passed:
        details = ("All {} seeds verified; {} start-end pairs match exactly. "
                   "Connectivity preserved.".format(len(g_seeds),
                                                    len(golden_pairs)))
    else:
        parts = []
        if missing_seeds:
            parts.append("{} seed(s) missing".format(len(missing_seeds)))
        if extra_seeds:
            parts.append("{} extra seed(s)".format(len(extra_seeds)))
        if pin_diff:
            parts.append("{} seed(s) with 251-pin endpoint mismatch".format(
                len(pin_diff)))
        if m1_diff:
            parts.append("{} seed(s) with std-cell M1 endpoint mismatch".format(
                len(m1_diff)))
        details = "FAILED: {} ({} missing / {} extra pairs). {} seeds checked.".format(
            "; ".join(parts), n_missing_pairs, n_extra_pairs, len(g_seeds))

    return {
        "connectivity_preserved": passed,
        "passed": passed,
        "seeds_checked": len(g_seeds),
        "seeds_missing": len(missing_seeds),
        "extra_seeds": len(extra_seeds),
        "pin_endpoint_mismatches": len(pin_diff),
        "layer_count_mismatches": len(m1_diff),
        "missing_pairs": n_missing_pairs,
        "extra_pairs": n_extra_pairs,
        "details": details,
        "missing_seeds": [_key_to_json(s) for s in missing_seeds[:10]],
        "extra_seeds_detail": [_key_to_json(s) for s in extra_seeds[:10]],
        "pin_mismatches_detail": detail(pin_diff),
        "layer_mismatches_detail": detail(m1_diff),
    }


def check_block_connectivity(golden_json_path, modified_script_path):
    with open(str(golden_json_path)) as f:
        data = json.load(f)
    if "terminals" not in data or "pairs" not in data:
        return {"connectivity_preserved": False, "passed": False,
                "details": "Block golden JSON must contain 'terminals' and "
                           "'pairs': {}".format(golden_json_path)}
    golden_pairs = decode_block_pairs(data)
    _, modified_pairs = trace_block_pairs(str(modified_script_path))
    result = compare_block_pairs(golden_pairs, modified_pairs)
    result["golden_json"] = str(golden_json_path)
    result["modified_script"] = str(modified_script_path)
    result["original_script"] = str(derive_original_script(golden_json_path))
    result["golden_pairs_count"] = len(golden_pairs)
    result["modified_pairs_count"] = len(modified_pairs)
    return result


# ===================================================================
# Golden JSON + path derivation
# ===================================================================

def load_golden_json(json_path):
    with open(json_path) as f:
        data = json.load(f)
    return data["case"], data["design_type"], data["paths"]


def derive_original_script(golden_json_path):
    p = Path(golden_json_path)
    return p.parent.parent / "layout_script" / (p.stem + ".py")


# ===================================================================
# Comparison
# ===================================================================

def compare_connectivity(golden_paths, modified_paths, design_type):
    def group_by_seed(paths):
        groups = defaultdict(list)
        for p in paths:
            sk = (p["start"]["layer"], points_key(p["start"]["points"]))
            groups[sk].append(p)
        return groups

    gg = group_by_seed(golden_paths)
    mg = group_by_seed(modified_paths)

    checked = missing = 0
    layer_mm = []
    pin_mm = []
    missing_seeds = []

    for sk in sorted(gg.keys()):
        checked += 1
        if sk not in mg:
            missing += 1
            missing_seeds.append(
                {"layer": sk[0], "points": [list(p) for p in sk[1]]})
            continue

        # Group golden endpoints by layer, preserving pin flag
        def by_layer_golden(paths):
            bl = defaultdict(list)
            for p in paths:
                pin = p["end"].get("pin", False)
                bl[p["end"]["layer"]].append(
                    (points_key(canonicalize_points(p["end"]["points"])), pin))
            return bl

        # Group modified endpoints by layer, preserving pin flag
        def by_layer_modified(paths):
            bl = defaultdict(list)
            for p in paths:
                pin = p["end"].get("pin", False)
                bl[p["end"]["layer"]].append(
                    (points_key(canonicalize_points(p["end"]["points"])), pin))
            return bl

        gbl = by_layer_golden(gg[sk])
        mbl = by_layer_modified(mg[sk])

        for lyr in sorted(set(list(gbl.keys()) + list(mbl.keys()))):
            g_entries = gbl.get(lyr, [])
            m_entries = mbl.get(lyr, [])

            # Split into pin and non-pin
            g_pin = sorted([e[0] for e in g_entries if e[1]])
            g_non_pin = [e[0] for e in g_entries if not e[1]]
            m_pin = sorted([e[0] for e in m_entries if e[1]])
            m_non_pin = [e[0] for e in m_entries if not e[1]]

            # Pin endpoints: exact multiset match
            if g_pin != m_pin:
                pin_mm.append({
                    "seed_layer": sk[0],
                    "seed_points": [list(p) for p in sk[1]],
                    "endpoint_layer": lyr,
                    "golden_pin_count": len(g_pin),
                    "modified_pin_count": len(m_pin),
                })

            # Non-pin endpoints: count match
            if len(g_non_pin) != len(m_non_pin):
                layer_mm.append({
                    "seed_layer": sk[0],
                    "seed_points": [list(p) for p in sk[1]],
                    "endpoint_layer": lyr,
                    "golden_count": len(g_non_pin),
                    "modified_count": len(m_non_pin),
                })

    passed = (missing == 0 and not layer_mm and not pin_mm)
    if passed:
        details = "All {} seeds verified. Connectivity preserved.".format(
            checked)
    else:
        parts = []
        if missing:
            parts.append("{} seed(s) missing".format(missing))
        if pin_mm:
            parts.append("{} pin endpoint mismatch(es)".format(len(pin_mm)))
        if layer_mm:
            parts.append("{} layer count mismatch(es)".format(len(layer_mm)))
        details = "FAILED: {}. {} seeds checked.".format(
            "; ".join(parts), checked)

    return {
        "connectivity_preserved": passed,
        "passed": passed,
        "seeds_checked": checked,
        "seeds_missing": missing,
        "pin_endpoint_mismatches": len(pin_mm),
        "layer_count_mismatches": len(layer_mm),
        "details": details,
        "missing_seeds": missing_seeds[:10],
        "pin_mismatches_detail": pin_mm[:10],
        "layer_mismatches_detail": layer_mm[:10],
    }


# ===================================================================
# Main entry point
# ===================================================================

def check_connectivity(golden_json_path, modified_script_path, design_type):
    gp = Path(golden_json_path)
    mp = Path(modified_script_path)
    if not gp.exists():
        return {"connectivity_preserved": False, "passed": False,
                "details": "Golden JSON not found: {}".format(gp)}
    if not mp.exists():
        return {"connectivity_preserved": False, "passed": False,
                "details": "Modified script not found: {}".format(mp)}

    if design_type == "block":
        return check_block_connectivity(gp, mp)

    case_name, _, golden_paths = load_golden_json(gp)
    if not golden_paths:
        return {"connectivity_preserved": True, "passed": True,
                "details": "Golden JSON has 0 paths.", "seeds_checked": 0}

    if design_type == "cell":
        modified_paths = trace_modified_cell(str(mp))
    else:
        return {"connectivity_preserved": False, "passed": False,
                "details": "Unknown design_type: {}".format(design_type)}

    result = compare_connectivity(golden_paths, modified_paths, design_type)
    result["golden_json"] = str(gp)
    result["modified_script"] = str(mp)
    result["original_script"] = str(derive_original_script(golden_json_path))
    result["golden_paths_count"] = len(golden_paths)
    result["modified_paths_count"] = len(modified_paths)
    return result


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 check_connectivity.py "
              "<golden_json> <modified_script> <cell|block>",
              file=sys.stderr)
        sys.exit(1)
    gj, ms, dt = sys.argv[1], sys.argv[2], sys.argv[3]
    if dt not in ("cell", "block"):
        print("Error: design_type must be 'cell' or 'block'",
              file=sys.stderr)
        sys.exit(1)
    result = check_connectivity(gj, ms, dt)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)
