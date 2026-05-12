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
# sanity_check.py - Validates that an LLM-modified GDS file is still structurally valid.
#
# Uses KLayout's Python API (pya) to inspect both the original and modified GDS files
# and verifies that the modified file has not been corrupted or gamed.
#
# Optional 5th check (connectivity_preserved) is run when layout scripts and design_type
# are provided. It imports check_connectivity.py from the same directory.

import importlib.util
import json
import os
import sys
from typing import Optional

try:
    import pya
except ImportError as exc:
    raise ImportError(
        "KLayout's Python module 'pya' is not available. "
        "Please run this script inside the KLayout Python environment or install "
        "klayout via 'pip install klayout' and ensure the module is on your PYTHONPATH."
    ) from exc

# ASAP7 critical layers: {layer_number: description}
CRITICAL_LAYERS = {
    1: "nwell",
    2: "fin",
    7: "gate",
    11: "active",
    18: "v0",
    19: "m1",
}

# Subcells whose name starts with this prefix are considered VIA cells and are
# exempt from the locked-layer exact-match check and the non-VIA instance check
# (repair is allowed to move / alter via placements).
VIA_CELL_PREFIX = "VIA_"

# Layers (layer, datatype) on which shapes must remain bit-exact vs the
# original. For cell: only M0. For block: the structural + non-vertical-metal
# stack (m0 is absent in block testcases).
CELL_LOCKED_LAYERS = {(0, 0)}

BLOCK_LOCKED_LAYERS = {
    (1, 0),   # nwell
    (2, 0),   # fin
    (7, 0),   # gate
    (8, 0),   # dummy
    (10, 0),  # gcut
    (11, 0),  # active
    (12, 0),  # nselect
    (13, 0),  # pselect
    (16, 0),  # lig
    (17, 0),  # lisd
    (18, 0),  # v0
    (19, 0),  # m1
    (88, 0),  # sdt
    (97, 0),  # slvt
    (98, 0),  # lvt
    (99, 0),  # sramdrc
    (110, 0), # sramvt
}


def _load_layout(gds_path: str) -> pya.Layout:
    # Load a GDS file into a KLayout Layout object.
    layout = pya.Layout()
    layout.read(gds_path)
    return layout


def _get_top_cell_name(layout: pya.Layout) -> Optional[str]:
    # Return the name of the top cell, or None if the layout has no cells.
    top_cells = layout.top_cells()
    if not top_cells:
        return None
    return top_cells[0].name


def _get_all_cell_names(layout: pya.Layout) -> set:
    # Return the set of all cell names in the layout.
    return {layout.cell(i).name for i in range(layout.cells())}


def _get_layers_with_shapes(layout: pya.Layout) -> set:
    # Return the set of layer numbers that have at least one shape anywhere in
    # the layout (across all cells).
    layers_with_shapes = set()
    layer_infos = layout.layer_infos()

    for layer_info in layer_infos:
        layer_index = layout.find_layer(layer_info)
        if layer_index is None:
            continue
        layer_num = layer_info.layer
        for cell_index in range(layout.cells()):
            cell = layout.cell(cell_index)
            if not cell.shapes(layer_index).is_empty():
                layers_with_shapes.add(layer_num)
                break  # no need to check further cells for this layer

    return layers_with_shapes


def _layout_has_shapes(layout: pya.Layout) -> bool:
    # Return True if any cell in the layout contains at least one shape.
    for layer_info in layout.layer_infos():
        layer_index = layout.find_layer(layer_info)
        if layer_index is None:
            continue
        for cell_index in range(layout.cells()):
            cell = layout.cell(cell_index)
            if not cell.shapes(layer_index).is_empty():
                return True
    return False


def _get_shape_counts_per_layer(layout: pya.Layout) -> dict:
    # Return {layer_number: shape_count} counting all shapes across all cells.
    counts = {}
    for layer_info in layout.layer_infos():
        layer_index = layout.find_layer(layer_info)
        if layer_index is None:
            continue
        layer_num = layer_info.layer
        total = 0
        for cell_index in range(layout.cells()):
            cell = layout.cell(cell_index)
            total += cell.shapes(layer_index).size()
        if total > 0:
            counts[layer_num] = total
    return counts


OUTLINE_LAYER = 235
OUTLINE_DATATYPE = 0


def _get_outline_region(layout: pya.Layout) -> Optional[pya.Region]:
    # Extract the outline polygon(s) from layer (235, 0) of the top cell.
    # Returns a pya.Region, or None if the layer is empty / missing.
    top_cell = layout.top_cell()
    if top_cell is None:
        return None
    li = layout.find_layer(OUTLINE_LAYER, OUTLINE_DATATYPE)
    if li is None:
        return None
    shapes = top_cell.shapes(li)
    if shapes.is_empty():
        return None
    return pya.Region(shapes)


def _check_outline_boundary(
    original_layout: pya.Layout,
    modified_layout: pya.Layout,
) -> dict:
    # Check that all top-cell direct shapes in the modified layout fall within
    # the outline region (layer 235, 0) from the original layout.
    #
    # Returns {"passed": bool, "details": str, "protruding_layers": list}
    outline = _get_outline_region(original_layout)
    if outline is None:
        return {
            "passed": True,
            "details": "Outline layer (235,0) not found in original; check skipped.",
            "protruding_layers": [],
        }

    mod_top = modified_layout.top_cell()
    if mod_top is None:
        return {
            "passed": False,
            "details": "Modified layout has no top cell.",
            "protruding_layers": [],
        }

    protruding = []

    for layer_info in modified_layout.layer_infos():
        # Skip the outline layer itself
        if (layer_info.layer == OUTLINE_LAYER
                and layer_info.datatype == OUTLINE_DATATYPE):
            continue

        li = modified_layout.find_layer(layer_info)
        if li is None:
            continue

        shapes = mod_top.shapes(li)
        if shapes.is_empty():
            continue

        layer_region = pya.Region(shapes)
        outside = layer_region - outline
        if not outside.is_empty():
            outside_box = outside.bbox()
            protruding.append({
                "layer": layer_info.layer,
                "datatype": layer_info.datatype,
                "outside_bbox": [
                    outside_box.left, outside_box.bottom,
                    outside_box.right, outside_box.top,
                ],
            })

    if protruding:
        layer_strs = [
            "layer {}/{} (outside bbox: [{},{},{},{}])".format(
                p["layer"], p["datatype"],
                p["outside_bbox"][0], p["outside_bbox"][1],
                p["outside_bbox"][2], p["outside_bbox"][3],
            )
            for p in protruding
        ]
        return {
            "passed": False,
            "details": "Shapes outside outline on: " + "; ".join(layer_strs),
            "protruding_layers": protruding,
        }

    return {"passed": True, "details": "", "protruding_layers": []}


def _is_via_cell(cell_name: str) -> bool:
    # True iff cell_name designates a VIA subcell (exempt from locked-layer /
    # non-VIA instance checks).
    return cell_name.startswith(VIA_CELL_PREFIX)


def _canonicalize_polygon_points(polygon) -> tuple:
    # Canonicalize a pya.Polygon into a rotation/orientation-stable tuple of
    # integer (x, y) point tuples. Rotate so the lexicographically-smallest
    # point is first, then flip direction if signed area is negative (force
    # CCW). Mirrors check_connectivity.canonicalize_points, but takes a
    # pya.Polygon instead of a list.
    pts = [(int(p.x), int(p.y)) for p in polygon.each_point_hull()]
    n = len(pts)
    if n < 3:
        return tuple(pts)
    min_idx = min(range(n), key=lambda i: pts[i])
    rotated = list(pts[min_idx:]) + list(pts[:min_idx])
    area = 0
    for i in range(n):
        x1, y1 = rotated[i]
        x2, y2 = rotated[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    if area < 0:
        rotated = [rotated[0]] + list(reversed(rotated[1:]))
    return tuple(rotated)


def _shape_to_polygon(shape):
    # Convert a pya.Shape (polygon/box/path) into a pya.Polygon, or None if
    # the shape type isn't supported.
    try:
        if shape.is_polygon():
            return shape.polygon
        if shape.is_box():
            return pya.Polygon(shape.box)
        if shape.is_path():
            return shape.path.polygon()
    except Exception:
        return None
    return None


def _collect_shapes_per_cell(
    layout: pya.Layout,
    locked_layers: set,
    exclude_via: bool,
) -> set:
    # Collect shapes on the given locked layers from every cell in the layout
    # in its OWN local coordinate system (no flattening). Each record is a
    # (cell_name, layer, datatype, canonical_points_tuple) tuple.  When
    # exclude_via is True, cells whose name starts with VIA_CELL_PREFIX are
    # skipped entirely — their contents are exempt from exact-match.
    result = set()
    for cell_index in range(layout.cells()):
        cell = layout.cell(cell_index)
        name = cell.name
        if exclude_via and _is_via_cell(name):
            continue
        for layer_info in layout.layer_infos():
            key = (layer_info.layer, layer_info.datatype)
            if key not in locked_layers:
                continue
            li = layout.find_layer(layer_info)
            if li is None:
                continue
            for shape in cell.shapes(li).each():
                poly = _shape_to_polygon(shape)
                if poly is None:
                    continue
                pts = _canonicalize_polygon_points(poly)
                if not pts:
                    continue
                result.add((name, key[0], key[1], pts))
    return result


def _check_locked_layers_exact_match(
    original_layout: pya.Layout,
    modified_layout: pya.Layout,
    locked_layers: set,
    exclude_via: bool,
) -> tuple:
    # Compare locked-layer shapes (per-cell, local coords, canonicalized) as
    # multisets. Returns (passed, shape_count_mismatches) where
    # shape_count_mismatches maps layer_num -> {"original": K, "modified": L}.
    # K = shapes in original that have no exact match in modified.
    # L = shapes in modified that have no exact match in original.
    # This detects both count mismatches AND same-count-different-coords cases.
    orig_set = _collect_shapes_per_cell(original_layout, locked_layers, exclude_via)
    mod_set = _collect_shapes_per_cell(modified_layout, locked_layers, exclude_via)

    missing = orig_set - mod_set
    extra = mod_set - orig_set

    shape_count_mismatches = {}
    for (_cell, layer, _dt, _pts) in missing:
        shape_count_mismatches.setdefault(
            layer, {"original": 0, "modified": 0})["original"] += 1
    for (_cell, layer, _dt, _pts) in extra:
        shape_count_mismatches.setdefault(
            layer, {"original": 0, "modified": 0})["modified"] += 1

    passed = not shape_count_mismatches
    return passed, shape_count_mismatches


def _collect_instance_set(layout: pya.Layout, exclude_via: bool = False) -> set:
    # Collect all CellInstArray placements from the top cell as a set of
    # (cell_name, rot, disp_x, disp_y) tuples. Order-independent.
    # rot is 0-7 (pya.Trans encodes mirror in rot 4-7), so no separate mirror
    # field is needed.  When exclude_via is True, instances referencing cells
    # with the VIA_ prefix are skipped (they are allowed to move).
    top_cell = layout.top_cell()
    if top_cell is None:
        return set()

    instances = set()
    for inst in top_cell.each_inst():
        cell_name = layout.cell(inst.cell_index).name
        if exclude_via and _is_via_cell(cell_name):
            continue
        trans = inst.trans
        instances.add((cell_name, trans.rot, trans.disp.x, trans.disp.y))

    return instances


def _check_instance_placements(
    original_layout: pya.Layout,
    modified_layout: pya.Layout,
    exclude_via: bool = False,
) -> dict:
    # Check that all subcell instance placements in the modified layout match
    # the original exactly (order-independent). No instance may be moved,
    # deleted, or added.
    #
    # Returns {"passed": bool, "details": str,
    #          "missing_instances": list, "extra_instances": list}
    orig_set = _collect_instance_set(original_layout, exclude_via)
    mod_set = _collect_instance_set(modified_layout, exclude_via)

    missing = orig_set - mod_set
    extra = mod_set - orig_set

    missing_list = [
        {"cell_name": m[0], "rot": m[1], "disp_x": m[2], "disp_y": m[3]}
        for m in sorted(missing)
    ]
    extra_list = [
        {"cell_name": e[0], "rot": e[1], "disp_x": e[2], "disp_y": e[3]}
        for e in sorted(extra)
    ]

    if missing or extra:
        parts = []
        if missing:
            parts.append("{} instance(s) missing/moved".format(len(missing)))
        if extra:
            parts.append("{} unexpected instance(s) added".format(len(extra)))
        return {
            "passed": False,
            "details": "Instance placements changed: " + ", ".join(parts) + ".",
            "missing_instances": missing_list,
            "extra_instances": extra_list,
        }

    return {
        "passed": True,
        "details": "",
        "missing_instances": [],
        "extra_instances": [],
    }


def _load_check_connectivity_module():
    # Dynamically load check_connectivity.py from the same directory as this script.
    # Returns the module, or None if loading fails.
    this_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(this_dir, "check_connectivity.py")
    if not os.path.isfile(module_path):
        return None
    spec = importlib.util.spec_from_file_location("check_connectivity", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sanity_check(
    original_gds_path: str,
    modified_gds_path: str,
    original_script_path: Optional[str] = None,
    modified_script_path: Optional[str] = None,
    design_type: Optional[str] = None,
) -> dict:
    # Validate that a modified GDS file is structurally consistent with the original.
    #
    # Checks performed:
    #     top_cell_exists           - Modified GDS has a top cell matching the original
    #     gds_not_empty             - Modified GDS contains at least one shape
    #     critical_layers_preserved - All critical ASAP7 layers present in original
    #                                 are still present in modified
    #     cell_structure_intact     - Exact same set of cell names in both files
    #     polygon_shape_counts_ok   - (polygon only) Shape count per layer in modified
    #                                 matches original exactly; prevents adding or
    #                                 deleting polygons
    #     connectivity_preserved    - (optional) All original connections exist in
    #                                 modified layout; only run when
    #                                 original_script_path, modified_script_path,
    #                                 and design_type ("cell" or "block") are provided.
    #
    # Returns a dict with individual check results, an overall 'passed' flag, and
    # a human-readable 'details' string describing any failures.
    failures = []

    original_layout = _load_layout(original_gds_path)
    modified_layout = _load_layout(modified_gds_path)

    # --- Check 1: top_cell_exists ---
    original_top = _get_top_cell_name(original_layout)
    modified_top = _get_top_cell_name(modified_layout)

    if modified_top is None:
        top_cell_exists = False
        failures.append("Modified GDS has no top cell.")
    elif original_top is not None and modified_top != original_top:
        top_cell_exists = False
        failures.append(
            f"Top cell mismatch: original='{original_top}', modified='{modified_top}'."
        )
    else:
        top_cell_exists = True

    # --- Check 2: gds_not_empty ---
    gds_not_empty = _layout_has_shapes(modified_layout)
    if not gds_not_empty:
        failures.append("Modified GDS contains no shapes in any cell.")

    # --- Check 3: critical_layers_preserved ---
    original_layers = _get_layers_with_shapes(original_layout)
    modified_layers = _get_layers_with_shapes(modified_layout)

    missing_critical = []
    for layer_num, layer_name in CRITICAL_LAYERS.items():
        if layer_num in original_layers and layer_num not in modified_layers:
            missing_critical.append(f"layer {layer_num} ({layer_name})")

    critical_layers_preserved = len(missing_critical) == 0
    if not critical_layers_preserved:
        failures.append(
            "Critical layers missing from modified GDS: "
            + ", ".join(missing_critical)
            + "."
        )

    # --- Check 4: cell_structure_intact ---
    original_cells = _get_all_cell_names(original_layout)
    modified_cells = _get_all_cell_names(modified_layout)

    deleted_cells = original_cells - modified_cells
    cell_structure_intact = len(deleted_cells) == 0
    if not cell_structure_intact:
        failures.append(
            "Cells deleted from modified GDS: "
            + ", ".join(sorted(deleted_cells))
            + "."
        )

    # --- Check 5: outline_boundary_respected (cell/block only) ---
    outline_boundary_respected = True
    outline_result = None
    if design_type in ("cell", "block"):
        outline_result = _check_outline_boundary(original_layout, modified_layout)
        outline_boundary_respected = outline_result["passed"]
        if not outline_boundary_respected:
            failures.append(outline_result["details"])

    # --- Check 6: instance_placements_unchanged (cell/block only) ---
    # For block, exclude VIA_ subcells (they are allowed to move during repair).
    instance_placements_unchanged = True
    instance_result = None
    if design_type in ("cell", "block"):
        instance_result = _check_instance_placements(
            original_layout, modified_layout,
            exclude_via=(design_type == "block"),
        )
        instance_placements_unchanged = instance_result["passed"]
        if not instance_placements_unchanged:
            failures.append(instance_result["details"])

    # --- Check 7: shape-level structural check ---
    # polygon  -> per-layer shape count must match (existing behavior)
    # cell     -> M0 shapes must exactly match (per-cell, local coords)
    # block    -> 17 locked layers must exactly match in all non-VIA cells
    polygon_shape_counts_ok = True
    shape_count_mismatches = {}
    if design_type == "polygon":
        original_counts = _get_shape_counts_per_layer(original_layout)
        modified_counts = _get_shape_counts_per_layer(modified_layout)
        all_layers = set(original_counts.keys()) | set(modified_counts.keys())
        for layer_num in sorted(all_layers):
            orig = original_counts.get(layer_num, 0)
            mod = modified_counts.get(layer_num, 0)
            if orig != mod:
                polygon_shape_counts_ok = False
                shape_count_mismatches[layer_num] = {
                    "original": orig, "modified": mod
                }
        if not polygon_shape_counts_ok:
            mismatch_details = ", ".join(
                "layer {} (original={}, modified={})".format(
                    ln, info["original"], info["modified"])
                for ln, info in sorted(shape_count_mismatches.items())
            )
            failures.append(
                "Polygon shape count mismatch: " + mismatch_details + "."
            )
    elif design_type == "cell":
        polygon_shape_counts_ok, shape_count_mismatches = (
            _check_locked_layers_exact_match(
                original_layout, modified_layout,
                CELL_LOCKED_LAYERS, exclude_via=False,
            )
        )
        if not polygon_shape_counts_ok:
            mismatch_details = ", ".join(
                "layer {} (unmatched original={}, unmatched modified={})".format(
                    ln, info["original"], info["modified"])
                for ln, info in sorted(shape_count_mismatches.items())
            )
            failures.append(
                "M0 locked-layer shape mismatch (cell): "
                + mismatch_details + "."
            )
    elif design_type == "block":
        polygon_shape_counts_ok, shape_count_mismatches = (
            _check_locked_layers_exact_match(
                original_layout, modified_layout,
                BLOCK_LOCKED_LAYERS, exclude_via=True,
            )
        )
        if not polygon_shape_counts_ok:
            mismatch_details = ", ".join(
                "layer {} (unmatched original={}, unmatched modified={})".format(
                    ln, info["original"], info["modified"])
                for ln, info in sorted(shape_count_mismatches.items())
            )
            failures.append(
                "Locked-layer shape mismatch (block, non-VIA cells): "
                + mismatch_details + "."
            )

    # --- Check 8: connectivity_preserved (optional) ---
    connectivity_result = None
    run_connectivity_check = (
        original_script_path is not None
        and modified_script_path is not None
        and design_type in ("cell", "block")
    )

    if run_connectivity_check:
        check_conn_module = _load_check_connectivity_module()
        if check_conn_module is not None:
            golden_json = original_script_path.replace("/layout_script/", "/connectivity/").replace(".py", ".json")
            connectivity_result = check_conn_module.check_connectivity(
                golden_json,
                modified_script_path,
                design_type,
            )
            if not connectivity_result["passed"]:
                failures.append(
                    "Connectivity check failed: " + connectivity_result["details"]
                )
        else:
            failures.append(
                "Connectivity check skipped: check_connectivity.py not found."
            )

    # Build overall passed flag
    struct_passed = (
        top_cell_exists
        and gds_not_empty
        and critical_layers_preserved
        and cell_structure_intact
        and outline_boundary_respected
        and instance_placements_unchanged
        and polygon_shape_counts_ok
    )

    if run_connectivity_check and connectivity_result is not None:
        passed = struct_passed and connectivity_result["passed"]
    else:
        passed = struct_passed

    if passed:
        details = "All sanity checks passed."
    else:
        details = " ".join(failures)

    result = {
        "top_cell_exists": top_cell_exists,
        "gds_not_empty": gds_not_empty,
        "critical_layers_preserved": critical_layers_preserved,
        "cell_structure_intact": cell_structure_intact,
        "outline_boundary_respected": outline_boundary_respected,
        "instance_placements_unchanged": instance_placements_unchanged,
        "polygon_shape_counts_ok": polygon_shape_counts_ok,
        "passed": passed,
        "details": details,
    }

    if outline_result is not None and outline_result.get("protruding_layers"):
        result["protruding_layers"] = outline_result["protruding_layers"]

    if instance_result is not None:
        if instance_result.get("missing_instances"):
            result["missing_instances"] = instance_result["missing_instances"]
        if instance_result.get("extra_instances"):
            result["extra_instances"] = instance_result["extra_instances"]

    if shape_count_mismatches:
        result["shape_count_mismatches"] = shape_count_mismatches

    if connectivity_result is not None:
        # Schema produced by check_connectivity.compare_connectivity().
        # (Keys starting with 'seeds_' / 'pin_' / 'layer_' replace the older
        # '*_connections' / 'preservation_rate' terminology.)
        result["connectivity_preserved"]   = connectivity_result.get("connectivity_preserved")
        result["seeds_checked"]            = connectivity_result.get("seeds_checked")
        result["seeds_missing"]            = connectivity_result.get("seeds_missing")
        result["pin_endpoint_mismatches"]  = connectivity_result.get("pin_endpoint_mismatches")
        result["layer_count_mismatches"]   = connectivity_result.get("layer_count_mismatches")
        result["connectivity_details"]     = connectivity_result.get("details")
        if connectivity_result.get("missing_seeds"):
            result["missing_seeds"]        = connectivity_result["missing_seeds"]
        if connectivity_result.get("pin_mismatches_detail"):
            result["pin_mismatches_detail"] = connectivity_result["pin_mismatches_detail"]
        if connectivity_result.get("layer_mismatches_detail"):
            result["layer_mismatches_detail"] = connectivity_result["layer_mismatches_detail"]

    return result


def _parse_inputs():
    # Parse arguments from standard CLI or KLayout `-rd` defines.
    if len(sys.argv) in (3, 4, 6, 7):
        original_gds_path = sys.argv[1]
        modified_gds_path = sys.argv[2]

        if len(sys.argv) in (6, 7):
            original_script_path = sys.argv[3]
            modified_script_path = sys.argv[4]
            design_type = sys.argv[5]
        else:
            original_script_path = None
            modified_script_path = None
            design_type = None

        if len(sys.argv) == 4:
            sanity_json_out = sys.argv[3]
        elif len(sys.argv) == 7:
            sanity_json_out = sys.argv[6]
        else:
            sanity_json_out = None

        return (
            original_gds_path,
            modified_gds_path,
            original_script_path,
            modified_script_path,
            design_type,
            sanity_json_out,
        )

    original_gds_path = globals().get("original_gds_path")
    modified_gds_path = globals().get("modified_gds_path")
    original_script_path = globals().get("original_script_path")
    modified_script_path = globals().get("modified_script_path")
    design_type = globals().get("design_type")
    sanity_json_out = globals().get("sanity_json_out")

    if original_gds_path and modified_gds_path:
        if any(
            value is not None
            for value in (original_script_path, modified_script_path, design_type)
        ) and not all(
            value is not None
            for value in (original_script_path, modified_script_path, design_type)
        ):
            print(
                "When using KLayout -rd inputs, provide either only "
                "original_gds_path/modified_gds_path, or all of "
                "original_script_path/modified_script_path/design_type as well.",
                file=sys.stderr,
            )
            sys.exit(1)

        return (
            original_gds_path,
            modified_gds_path,
            original_script_path,
            modified_script_path,
            design_type,
            sanity_json_out,
        )

    print(
        "Usage: python sanity_check.py <original.gds> <modified.gds> "
        "[<original_script.py> <modified_script.py> <cell|block>] "
        "[<sanity_json_out>]\n"
        "   or: klayout -b -r sanity_check.py "
        "-rd original_gds_path=<original.gds> "
        "-rd modified_gds_path=<modified.gds> "
        "[-rd original_script_path=<original_script.py> "
        "-rd modified_script_path=<modified_script.py> "
        "-rd design_type=<cell|block>] "
        "[-rd sanity_json_out=<sanity.json>]",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    (
        original_gds_path,
        modified_gds_path,
        original_script_path,
        modified_script_path,
        design_type,
        sanity_json_out,
    ) = _parse_inputs()

    result = sanity_check(
        original_gds_path,
        modified_gds_path,
        original_script_path,
        modified_script_path,
        design_type,
    )
    result_json = json.dumps(result, indent=2)
    print(result_json)

    if sanity_json_out:
        try:
            with open(sanity_json_out, "w") as f:
                f.write(result_json)
        except OSError as exc:
            print(
                f"WARNING: could not write sanity JSON to {sanity_json_out}: {exc}",
                file=sys.stderr,
            )

    sys.exit(0 if result["passed"] else 1)
