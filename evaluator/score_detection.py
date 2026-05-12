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
# score_detection.py - Scoring script for DRC detection evaluation.
#
# Compares an LLM's detected violations (JSON) against a golden DRC report.
# Matching is geometry-based and depends on whether the golden bbox has area:
#
#   - Golden polygon / non-zero bbox (w*h > 0): predicted and golden bboxes
#     must overlap AND the area ratio pred/golden must fall in
#     [MERCY_LOW, MERCY_HIGH] = [0.81, 1.21].  This is the linear 10%
#     tolerance on each side squared into an area tolerance: 0.9*0.9 = 0.81,
#     1.1*1.1 = 1.21.
#
#   - Golden edge / line (w*h = 0 and w+h > 0): the predicted bbox must
#     *encompass* both endpoints of the golden edge AND the predicted bbox's
#     longest side must not exceed `edge_length * 1.1`.  This replaces the
#     old area-ratio check which is mathematically undefined when
#     golden_area = 0.
#
#   - Golden dot (w = h = 0): cannot match (shouldn't occur after the
#     dot-to-polygon fix in process_klayout_reports.py).
#
# Scoring policy (geometry_required_edge_aware):
#   - TP only when both sides supply geometry AND the above rules pass.
#   - When geometry is absent on either side, TP=0 for that rule.
#
# Matching algorithm: Hopcroft-Karp maximum bipartite matching.
# Supports KLayout (.lyrpt XML) and processed JSON (.drc.json) formats.

import argparse
import json
import re
import sys
import xml.etree.ElementTree as et
from collections import deque


# --- Polygon (non-degenerate) area tolerance -------------------------------
# Linear 10% tolerance on each side -> 0.9*0.9 = 0.81, 1.1*1.1 = 1.21.
MERCY_LOW = 0.81
MERCY_HIGH = 1.21

# --- Edge encompass tolerance ---------------------------------------------
# For edge-type golden violations the predicted bbox's longest side must not
# exceed EDGE_SIDE_TOL * edge_length, and must contain both edge endpoints.
EDGE_SIDE_TOL = 1.1


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _bbox_of_edges(edges):
    # Compute bounding box from a list of edges [[x1,y1,x2,y2], ...].
    xs = [c for e in edges for c in (e[0], e[2])]
    ys = [c for e in edges for c in (e[1], e[3])]
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_of_vertices(verts):
    # Compute bounding box from polygon vertices [[x,y], ...].
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_area(bbox):
    # Area of bounding box (xmin, ymin, xmax, ymax).
    w = max(0, bbox[2] - bbox[0])
    h = max(0, bbox[3] - bbox[1])
    return w * h


def _bboxes_overlap(b1, b2):
    # Check if two bounding boxes have non-zero intersection.
    return (min(b1[2], b2[2]) > max(b1[0], b2[0]) and
            min(b1[3], b2[3]) > max(b1[1], b2[1]))


def _point_in_bbox(px, py, bb):
    # Inclusive: a point on the boundary counts as inside.
    return bb[0] <= px <= bb[2] and bb[1] <= py <= bb[3]


def _is_edge_bbox(bbox):
    # True iff the golden bbox describes an edge (line segment) rather than a
    # polygon or a dot.  w*h == 0 AND w+h > 0.
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    return (w * h == 0) and (w + h > 0)


def _violation_matches(pred_bbox, golden_bbox):
    # Check if a predicted violation matches a golden violation.
    #
    # Branches on the golden bbox's shape:
    #   - Non-degenerate polygon: overlap + area ratio in [0.81, 1.21].
    #   - Edge (line): both edge endpoints inside pred bbox, pred longest
    #     side <= edge_length * 1.1.
    #   - Dot: cannot match.
    golden_area = _bbox_area(golden_bbox)

    # -- Non-degenerate polygon ---------------------------------------------
    if golden_area > 0:
        if not _bboxes_overlap(pred_bbox, golden_bbox):
            return False
        pred_area = _bbox_area(pred_bbox)
        ratio = pred_area / golden_area
        return MERCY_LOW <= ratio <= MERCY_HIGH

    # -- Edge (line segment) ------------------------------------------------
    if _is_edge_bbox(golden_bbox):
        gw = golden_bbox[2] - golden_bbox[0]
        gh = golden_bbox[3] - golden_bbox[1]
        edge_length = max(gw, gh)

        pw = pred_bbox[2] - pred_bbox[0]
        ph = pred_bbox[3] - pred_bbox[1]
        pred_longest = max(pw, ph)
        if pred_longest > edge_length * EDGE_SIDE_TOL:
            return False

        # Both endpoints of the degenerate-bbox line must be inside pred bbox.
        if not _point_in_bbox(golden_bbox[0], golden_bbox[1], pred_bbox):
            return False
        if not _point_in_bbox(golden_bbox[2], golden_bbox[3], pred_bbox):
            return False
        return True

    # -- Dot: cannot match --------------------------------------------------
    return False


def _hopcroft_karp(adj, num_left, num_right):
    # Hopcroft-Karp maximum bipartite matching.
    #
    # Uses BFS to build a layered shortest-augmenting-path graph, then DFS to
    # find vertex-disjoint augmenting paths along that graph.  Runs in
    # O(E * sqrt(V)) time, which is optimal for bipartite matching.
    #
    # Args:
    #     adj      : dict mapping left-node index -> list of right-node indices
    #     num_left : number of left nodes  (predicted violations)
    #     num_right: number of right nodes (golden violations)
    #
    # Returns:
    #     dict mapping matched left-node index -> matched right-node index
    INF = float('inf')
    match_left = [None] * num_left
    match_right = [None] * num_right
    dist = [0] * num_left

    def bfs():
        queue = deque()
        for u in range(num_left):
            if match_left[u] is None:
                dist[u] = 0
                queue.append(u)
            else:
                dist[u] = INF
        found = False
        while queue:
            u = queue.popleft()
            for v in adj.get(u, []):
                w = match_right[v]
                if w is None:
                    found = True
                elif dist[w] == INF:
                    dist[w] = dist[u] + 1
                    queue.append(w)
        return found

    def dfs(u):
        for v in adj.get(u, []):
            w = match_right[v]
            if w is None or (dist[w] == dist[u] + 1 and dfs(w)):
                match_left[u] = v
                match_right[v] = u
                return True
        dist[u] = INF
        return False

    while bfs():
        for u in range(num_left):
            if match_left[u] is None:
                dfs(u)

    return {u: v for u, v in enumerate(match_left) if v is not None}


def _match_violations(predicted, golden):
    # Maximum bipartite matching of predicted to golden violations by geometry.
    #
    # Uses Hopcroft-Karp for optimal (order-independent) matching.  Each
    # violation dict must have a "bbox" key: (xmin, ymin, xmax, ymax).
    # Returns (tp, fp, fn).
    if not predicted or not golden:
        return 0, len(predicted), len(golden)

    # Build adjacency: O(P*G) calls to _violation_matches
    adj = {}
    for i, pv in enumerate(predicted):
        adj[i] = [j for j, gv in enumerate(golden)
                   if _violation_matches(pv["bbox"], gv["bbox"])]

    matching = _hopcroft_karp(adj, len(predicted), len(golden))
    tp = len(matching)
    fp = len(predicted) - tp
    fn = len(golden) - tp
    return tp, fp, fn


# ---------------------------------------------------------------------------
# Golden report parsers
# ---------------------------------------------------------------------------

def _parse_golden_report(report_path):
    # Parse golden DRC report.
    #
    # Returns (counts_dict, geometry_dict):
    #     counts_dict:   {rule_name: violation_count}
    #     geometry_dict: {rule_name: [{"bbox": (xmin, ymin, xmax, ymax)}, ...]}
    #
    # Supports .drc.json and .lyrpt formats.
    if report_path.endswith(".drc.json"):
        return _parse_drc_json_golden(report_path)
    else:
        # Default: KLayout XML (.lyrpt or unknown extension)
        return _parse_klayout_report_with_geometry(report_path)


def _parse_drc_json_golden(report_path):
    # Parse a processed .drc.json golden report.
    #
    # Returns (counts_dict, geometry_dict):
    #     counts_dict:   {rule_name: violation_count}
    #     geometry_dict: {rule_name: [{"bbox": (xmin, ymin, xmax, ymax)}, ...]}
    with open(report_path) as f:
        data = json.load(f)
    counts = {}
    geometry = {}
    for rule, info in data.get("rules", {}).items():
        counts[rule] = info["violation_count"]
        viols = []
        for v in info.get("violations", []):
            bbox = v.get("bbox")
            if bbox:
                viols.append({"bbox": tuple(bbox)})
        if viols:
            geometry[rule] = viols
    return counts, geometry


def _parse_klayout_report_with_geometry(report_path):
    # Parse a KLayout DRC report (.lyrpt XML) returning both counts and geometry.
    #
    # Each <item> element holds a <category> (rule name) and a <values> block
    # with zero or more <value> children.  Each <value> text describes one
    # violation in one of two formats (coordinates converted to dbu):
    #
    #   edge:      "edge: (x1,y1;x2,y2)"
    #   edge-pair: "edge-pair: (x1,y1;x2,y2)/(x3,y3;x4,y4)"
    #
    # Returns (counts_dict, geometry_dict):
    #     counts_dict:   {rule_name: violation_count}
    #     geometry_dict: {rule_name: [{"bbox": (xmin, ymin, xmax, ymax)}, ...]}
    # Patterns for the two value formats
    _edge_pat = re.compile(
        r'edge:\s*\(\s*([^;]+);([^)]+)\)'
    )
    _edge_pair_pat = re.compile(
        r'edge-pair:\s*\(\s*([^;]+);([^)]+)\)\s*/\s*\(\s*([^;]+);([^)]+)\)'
    )

    def _parse_point(s):
        # Parse 'x,y' string (in microns from KLayout) into (int, int) in dbu.
        x_str, y_str = s.strip().split(",")
        return int(round(float(x_str) / 0.00025)), int(round(float(y_str) / 0.00025))

    def _value_to_bbox(text):
        # Convert a <value> text to a (xmin, ymin, xmax, ymax) bbox, or None.
        m = _edge_pair_pat.search(text)
        if m:
            x1, y1 = _parse_point(m.group(1))
            x2, y2 = _parse_point(m.group(2))
            x3, y3 = _parse_point(m.group(3))
            x4, y4 = _parse_point(m.group(4))
            xs = (x1, x2, x3, x4)
            ys = (y1, y2, y3, y4)
            return (min(xs), min(ys), max(xs), max(ys))

        m = _edge_pat.search(text)
        if m:
            x1, y1 = _parse_point(m.group(1))
            x2, y2 = _parse_point(m.group(2))
            xs = (x1, x2)
            ys = (y1, y2)
            return (min(xs), min(ys), max(xs), max(ys))

        return None

    tree = et.parse(report_path)
    root = tree.getroot()
    counts = {}
    geometry = {}

    items = root.find("items")
    if items is None:
        return counts, geometry

    for item in items.findall("item"):
        cat = item.find("category")
        if cat is None or cat.text is None:
            continue
        rule = cat.text.strip().strip("'")

        vals_el = item.find("values")
        if vals_el is None:
            continue

        value_els = vals_el.findall("value")
        counts[rule] = counts.get(rule, 0) + len(value_els)

        for val_el in value_els:
            text = val_el.text or ""
            bbox = _value_to_bbox(text)
            if bbox is not None:
                geometry.setdefault(rule, []).append({"bbox": bbox})

    return counts, geometry


# ---------------------------------------------------------------------------
# Prediction parser
# ---------------------------------------------------------------------------

def _parse_detection(detection_path):
    # Parse LLM detection JSON.
    #
    # Returns {rule_name: {"count": N, "violations": [{"bbox": ...}]}}.
    # The "violations" list may be empty if geometry was not provided.
    with open(detection_path, encoding="utf-8") as f:
        data = json.load(f)

    result = {}
    for entry in data:
        rule = entry["rule_name"]
        count = int(entry["violation_count"])

        violations = []
        for v in entry.get("violations", []):
            vtype = v.get("type", "")
            if vtype == "edge_pair":
                e1 = v["edge1"]
                e2 = v["edge2"]
                bbox = _bbox_of_edges([e1, e2])
                violations.append({"bbox": bbox})
            elif vtype == "bbox":
                b = v["bbox"]
                violations.append({"bbox": tuple(b)})

        if rule in result:
            result[rule]["count"] += count
            result[rule]["violations"].extend(violations)
        else:
            result[rule] = {"count": count, "violations": violations}

    return result


# ---------------------------------------------------------------------------
# Main scoring
# ---------------------------------------------------------------------------

def score_detection(detection_path, golden_report_path):
    # Score DRC violation detections against a golden DRC report.
    #
    # Scoring policy ("geometry_required"):
    #   - TP is awarded only when both sides supply per-violation geometry AND
    #     bounding boxes pass the overlap + mercy-area-ratio test.
    #   - Rules where geometry is unavailable on either side receive
    #     tp=0, fp=pred_count, fn=golden_count.  Those rules are collected in
    #     the returned "geometry_unavailable_rules" list.
    #
    # Matching algorithm: Hopcroft-Karp maximum bipartite matching, which
    # guarantees an optimal (maximum-cardinality) assignment regardless of
    # iteration order.
    #
    # Args:
    #     detection_path:    Path to LLM detection JSON.
    #     golden_report_path: Path to golden DRC report (.drc.json or .lyrpt).
    predicted = _parse_detection(detection_path)
    golden_counts, golden_geo = _parse_golden_report(golden_report_path)

    all_rules = set(predicted.keys()) | set(golden_counts.keys())

    sum_tp = sum_fp = sum_fn = 0
    geo_matched_rules = 0
    # Rules where geometry was absent on at least one side; TP is forced to 0.
    geometry_unavailable_rules = []

    for rule in all_rules:
        pred_data = predicted.get(rule, {"count": 0, "violations": []})
        golden_count = golden_counts.get(rule, 0)
        pred_viols = pred_data.get("violations", [])
        golden_viols = golden_geo.get(rule, [])

        # --- Geometry-based matching (requires both sides to have regions) ---
        if pred_viols and golden_viols:
            tp, fp, fn = _match_violations(pred_viols, golden_viols)
            geo_matched_rules += 1

        else:
            # Geometry unavailable on at least one side: no TP credit can be
            # granted because we cannot verify spatial overlap.  Every
            # predicted violation is a FP and every golden violation is a FN.
            pred_count = pred_data["count"]
            tp = 0
            fp = pred_count
            fn = golden_count
            geometry_unavailable_rules.append(rule)

        sum_tp += tp
        sum_fp += fp
        sum_fn += fn

    # Aggregate metrics
    sum_precision = sum_tp / (sum_tp + sum_fp) if (sum_tp + sum_fp) > 0 else 0.0
    sum_recall = sum_tp / (sum_tp + sum_fn) if (sum_tp + sum_fn) > 0 else 0.0
    sum_f1 = (2 * sum_precision * sum_recall / (sum_precision + sum_recall)
              if sum_precision + sum_recall > 0 else 0.0)

    total_pred = sum(d["count"] for d in predicted.values())
    total_golden = sum(golden_counts.values())

    return {
        # --- Core metrics (backward-compatible keys) ---
        "sum_precision": sum_precision,
        "sum_recall": sum_recall,
        "sum_f1": sum_f1,
        "total_predicted_violations": total_pred,
        "total_golden_violations": total_golden,
        "total_rules_predicted": len(predicted),
        "total_rules_golden": len(golden_counts),
        "total_rules_union": len(all_rules),
        "sum_tp": sum_tp,
        "sum_fp": sum_fp,
        "sum_fn": sum_fn,
        "geo_matched_rules": geo_matched_rules,
        # count_matched_rules retained for backward compatibility; always 0
        # under geometry_required (no count-based fallback TP).
        "count_matched_rules": 0,
        "mercy_low": MERCY_LOW,
        "mercy_high": MERCY_HIGH,
        "edge_side_tolerance": EDGE_SIDE_TOL,
        "geometry_unavailable_rules": sorted(geometry_unavailable_rules),
        "geometry_unavailable_count": len(geometry_unavailable_rules),
        "scoring_policy": "geometry_required_edge_aware",
        "matching_algorithm": "hopcroft_karp",
    }


def validate_detection_schema(predicted):
    """Check whether the detection JSON schema is valid.

    Returns (is_valid: bool, reason: str); when invalid, reason is
    human-readable.
    invariant: any schema gap forces the entire detection score to 0.
    """
    if not isinstance(predicted, list):
        return False, "top_level_not_list"
    for entry in predicted:
        if not isinstance(entry, dict):
            return False, "entry_not_dict"
        if "rule_name" not in entry or not isinstance(entry["rule_name"], str):
            return False, "missing_rule_name"
        if "violation_count" not in entry or not isinstance(entry["violation_count"], int):
            return False, "violation_count_not_int"
        if entry["violation_count"] < 0:
            return False, "violation_count_negative"
        if "violations" not in entry or not isinstance(entry["violations"], list):
            return False, "violations_not_list"
        if entry["violation_count"] != len(entry["violations"]):
            return False, "violation_count_mismatch"
        rule = entry["rule_name"]
        for v in entry["violations"]:
            if not isinstance(v, dict) or "type" not in v:
                return False, "violation_missing_type"
            if ".S." in rule:
                if v["type"] != "edge_pair":
                    return False, "S_rule_not_edge_pair"
            else:
                if v["type"] != "bbox":
                    return False, "non_S_rule_not_bbox"
    return True, ""


def main():
    # align the CLI with the caller.
    # token / runtime / status are always read from the trusted agent_meta
    # JSON, no longer via CLI flags; schema validate is the first step
    # of the main flow.
    parser = argparse.ArgumentParser(description="Score DRC detection")
    parser.add_argument("--predicted",  required=True,
                        help="agent detection output JSON path")
    parser.add_argument("--golden",     required=True,
                        help="trusted golden DRC report path")
    parser.add_argument("--output",     required=True,
                        help="score JSON output path")
    parser.add_argument("--agent-meta", required=True,
                        help="trusted agent_meta JSON path")
    args = parser.parse_args()

    # ----- Schema validate first (main flow's first step) -----
    with open(args.predicted) as f:
        predicted = json.load(f)
    is_valid, reason = validate_detection_schema(predicted)
    if not is_valid:
        # Invariant: use write_invalid_score.py to keep the
        # schema unified; do not emit invalid JSON from score_detection.py.
        # Exit code 2 signals to the caller to use write_invalid_score.py.
        sys.stderr.write(f"ERROR: detection schema invalid: {reason}\n")
        sys.exit(2)

    # ----- token / runtime / status always read from trusted meta -----
    with open(args.agent_meta) as f:
        meta = json.load(f)
    agent_status        = meta.get("agent_status", "fail")
    agent_runtime_secs  = float(meta.get("agent_runtime_seconds") or 0.0)
    tokens              = meta.get("tokens") or {}

    # ----- main scoring logic -----
    result = score_detection(args.predicted, args.golden)

    # ----- Attach shared fields (shared score schema) -----
    # schema validation has passed, so mark
    # valid_detection=True for write_score_csv._pick_fields to detect the
    # DETECTION_FIELDS schema.
    result["valid_detection"]       = True
    result["agent_status"]          = agent_status
    result["runtime_seconds"]       = agent_runtime_secs
    result["input_tokens"]          = int(tokens.get("input_tokens", 0))
    result["output_tokens"]         = int(tokens.get("output_tokens", 0))
    result["cache_read_tokens"]     = int(tokens.get("cache_read_tokens", 0))
    result["cache_write_tokens"]    = int(tokens.get("cache_write_tokens", 0))

    # ----- write output file (no longer prints to stdout) -----
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
