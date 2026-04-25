"""
Parametric CAD Engine — build123d (primary) with cadquery fallback.
Generates .STEP files from engineering calculation dimensions.

Supports:
  - Shaft: solid/hollow, keyways, chamfers
  - Gearbox: housing box with input/output stubs
  - Bearing: ring cross-section
  - Cam: base profile disc
  - Custom: parametric box with hole deductions

Security: No user-controlled code execution. All geometry is constructed
from validated numeric dimensions only.
"""

import os
import math
from typing import Dict, Any, Optional


def _get_output_dir() -> str:
    """Get (and create) the CAD output directory."""
    out = os.path.join(os.path.dirname(__file__), "..", "..", "generated_cad")
    os.makedirs(out, exist_ok=True)
    return out


# ── Engine Detection ─────────────────────────────────────────────────────────

def _detect_engine() -> str:
    """Detect which CAD kernel is available."""
    try:
        import build123d  # noqa: F401
        return "build123d"
    except ImportError:
        pass
    try:
        import cadquery  # noqa: F401
        return "cadquery"
    except ImportError:
        pass
    return "none"


# ══════════════════════════════════════════════════════════════════════════════
#  BUILD123D IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _b3d_shaft(dims: Dict, params: Dict) -> str:
    """Generate shaft STEP using build123d."""
    from build123d import (
        Cylinder, Pos, Rot, Box, Location, export_step, Part, Align
    )

    d = float(dims.get("diameter_mm", 30))
    L = float(dims.get("length_mm", 300))
    d_inner = dims.get("inner_diameter_mm")
    r = d / 2

    # Base shaft — solid or hollow
    shaft = Cylinder(r, L, align=(Align.CENTER, Align.CENTER, Align.MIN))

    if d_inner and float(d_inner) > 0:
        r_inner = float(d_inner) / 2
        bore = Cylinder(r_inner, L + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        shaft = shaft - bore

    # Keyway cuts
    has_keyway = str(params.get("keyway", "no")) == "yes"
    if has_keyway:
        n_keys = int(float(params.get("num_keyways", 1)))
        kw_width = d * 0.25
        kw_depth = d * 0.12
        kw_length = L * 0.8

        for i in range(min(n_keys, 3)):
            angle = i * (360.0 / max(n_keys, 1))
            # Position keyway at the shaft surface
            slot = Box(
                kw_width, kw_depth, kw_length,
                align=(Align.CENTER, Align.MIN, Align.CENTER),
            )
            slot = slot.locate(
                Location(Pos(0, r - kw_depth * 0.3, L / 2)) *
                Location(Rot(0, 0, angle))
            )
            shaft = shaft - slot

    # Chamfer on ends (subtle 1mm x 45°)
    # build123d chamfer is complex on cylinders, skip for now

    out_path = os.path.join(_get_output_dir(), f"shaft_{int(d)}x{int(L)}.step")
    export_step(shaft, out_path)
    return out_path


def _b3d_gearbox(dims: Dict, params: Dict) -> str:
    """Generate gearbox housing STEP using build123d."""
    from build123d import Box, Cylinder, Pos, Location, export_step, Align

    d1 = float(dims.get("pinion_pitch_dia_mm", 50))
    d2 = float(dims.get("gear_pitch_dia_mm", 150))
    fw = float(dims.get("face_width_mm", 20))
    stages = int(params.get("num_stages", 1))

    box_l = d1 + d2 + 60
    box_w = fw * stages + 40
    box_h = max(d1, d2) + 60

    housing = Box(box_l, box_w, box_h)

    # Input shaft stub
    in_stub = Cylinder(d1 / 6, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
    in_stub = in_stub.locate(Location(Pos(-box_l / 4, 0, box_h / 2)))
    housing = housing + in_stub

    # Output shaft stub
    out_stub = Cylinder(d2 / 6, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
    out_stub = out_stub.locate(Location(Pos(box_l / 4, 0, box_h / 2)))
    housing = housing + out_stub

    out_path = os.path.join(_get_output_dir(), f"gearbox_{int(d1)}_{int(d2)}.step")
    export_step(housing, out_path)
    return out_path


def _b3d_bearing(dims: Dict, params: Dict) -> str:
    """Generate bearing ring STEP using build123d."""
    from build123d import Cylinder, export_step, Align

    bore = float(dims.get("bore_diameter_mm", 25))
    od = bore * 2.2
    w = bore * 0.5

    outer = Cylinder(od / 2, w, align=(Align.CENTER, Align.CENTER, Align.MIN))
    inner = Cylinder(bore / 2, w + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    ring = outer - inner

    out_path = os.path.join(_get_output_dir(), f"bearing_bore{int(bore)}.step")
    export_step(ring, out_path)
    return out_path


def _b3d_cam(dims: Dict, params: Dict) -> str:
    """Generate cam disc STEP using build123d."""
    from build123d import Cylinder, export_step, Align

    r_max = float(dims.get("max_radius_mm", 50))
    width = float(dims.get("cam_width_mm", 20))

    cam = Cylinder(r_max, width, align=(Align.CENTER, Align.CENTER, Align.MIN))

    # Bore hole (10mm default)
    bore = Cylinder(5, width + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    cam = cam - bore

    out_path = os.path.join(_get_output_dir(), f"cam_r{int(r_max)}.step")
    export_step(cam, out_path)
    return out_path


def _b3d_custom(dims: Dict, params: Dict) -> str:
    """Generate custom part STEP using build123d."""
    from build123d import Box, Cylinder, Pos, Location, export_step, Align
    import re

    Lp = float(dims.get("length_mm", 100))
    Wp = float(dims.get("width_mm", 50))
    Hp = float(dims.get("height_mm", 25))

    part = Box(Lp, Wp, Hp)

    # Hole deductions
    holes_desc = str(params.get("has_holes", "no"))
    if holes_desc.lower() not in ("no", "none", ""):
        nums = re.findall(r'(\d+\.?\d*)', holes_desc)
        if len(nums) >= 2:
            n_holes = int(float(nums[0]))
            d_hole = float(nums[1])
            depth = min(Hp, 25)
            spacing = Lp / (n_holes + 1)
            for i in range(n_holes):
                x_pos = -Lp / 2 + spacing * (i + 1)
                hole = Cylinder(d_hole / 2, depth + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
                hole = hole.locate(Location(Pos(x_pos, 0, -Hp / 2)))
                part = part - hole

    out_path = os.path.join(_get_output_dir(), f"custom_{int(Lp)}x{int(Wp)}x{int(Hp)}.step")
    export_step(part, out_path)
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
#  CADQUERY FALLBACK IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _cq_shaft(dims: Dict, params: Dict) -> str:
    import cadquery as cq
    d = float(dims.get("diameter_mm", 30))
    L = float(dims.get("length_mm", 300))
    d_inner = dims.get("inner_diameter_mm")

    if d_inner and float(d_inner) > 0:
        shape = cq.Workplane("XY").circle(d / 2).circle(float(d_inner) / 2).extrude(L)
    else:
        shape = cq.Workplane("XY").circle(d / 2).extrude(L)

    out_path = os.path.join(_get_output_dir(), f"shaft_{int(d)}x{int(L)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


def _cq_gearbox(dims: Dict, params: Dict) -> str:
    import cadquery as cq
    d1 = float(dims.get("pinion_pitch_dia_mm", 50))
    d2 = float(dims.get("gear_pitch_dia_mm", 150))
    fw = float(dims.get("face_width_mm", 20))
    stages = int(params.get("num_stages", 1))

    box_l = d1 + d2 + 50
    box_w = fw * stages + 50
    box_h = max(d1, d2) + 50
    shape = cq.Workplane("XY").box(box_l, box_w, box_h)

    out_path = os.path.join(_get_output_dir(), f"gearbox_{int(d1)}_{int(d2)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


def _cq_bearing(dims: Dict, params: Dict) -> str:
    import cadquery as cq
    bore = float(dims.get("bore_diameter_mm", 25))
    shape = cq.Workplane("XY").circle(bore * 1.1).circle(bore / 2).extrude(bore * 0.5)

    out_path = os.path.join(_get_output_dir(), f"bearing_bore{int(bore)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


def _cq_cam(dims: Dict, params: Dict) -> str:
    import cadquery as cq
    r_max = float(dims.get("max_radius_mm", 50))
    width = float(dims.get("cam_width_mm", 20))
    shape = cq.Workplane("XY").circle(r_max).extrude(width)

    out_path = os.path.join(_get_output_dir(), f"cam_r{int(r_max)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


def _cq_custom(dims: Dict, params: Dict) -> str:
    import cadquery as cq
    Lp = float(dims.get("length_mm", 100))
    Wp = float(dims.get("width_mm", 50))
    Hp = float(dims.get("height_mm", 25))
    shape = cq.Workplane("XY").box(Lp, Wp, Hp)

    out_path = os.path.join(_get_output_dir(), f"custom_{int(Lp)}x{int(Wp)}x{int(Hp)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

_B3D_DISPATCH = {
    "shaft": _b3d_shaft,
    "gearbox": _b3d_gearbox,
    "bearing": _b3d_bearing,
    "cam": _b3d_cam,
    "custom": _b3d_custom,
}

_CQ_DISPATCH = {
    "shaft": _cq_shaft,
    "gearbox": _cq_gearbox,
    "bearing": _cq_bearing,
    "cam": _cq_cam,
    "custom": _cq_custom,
}


def generate_cad(
    component_type: str,
    dims: Dict[str, Any],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate a parametric STEP file for the given component.
    Tries build123d first, falls back to cadquery, then returns dims-only.
    
    Returns:
        {
            "engine": "build123d" | "cadquery" | "none",
            "step_file": "/path/to/file.step" | None,
            "dimensions": {...},
            "note": "..." (if no CAD engine available)
        }
    """
    engine = _detect_engine()

    if engine == "build123d":
        dispatch = _B3D_DISPATCH
    elif engine == "cadquery":
        dispatch = _CQ_DISPATCH
    else:
        return {
            "engine": "none",
            "step_file": None,
            "dimensions": dims,
            "note": "No CAD engine installed. Install build123d or cadquery for STEP generation.",
        }

    builder = dispatch.get(component_type)
    if not builder:
        return {
            "engine": engine,
            "step_file": None,
            "dimensions": dims,
            "note": f"No CAD template for component type: {component_type}",
        }

    try:
        step_path = builder(dims, params)
        return {
            "engine": engine,
            "step_file": step_path,
            "dimensions": dims,
        }
    except Exception as e:
        return {
            "engine": engine,
            "step_file": None,
            "dimensions": dims,
            "note": f"CAD generation error: {str(e)}",
        }
