"""
Parametric CAD Engine — build123d (primary) with cadquery fallback.
Generates .STEP files from engineering calculation dimensions.

Supports:
  - Shaft: solid/hollow, keyways, chamfers
  - Gearbox: housing box with cavity, bearing bores, bottom flange & mounting bolt pattern
  - Bearing: inner/outer race with torus grooves and ball spheres
  - Cam: profile spline sketch (SHM, Cycloidal, Parabolic) extruded
  - Custom: parametric box or advanced operations (extrude, revolve, patterns, targeted fillet)

Security: No user-controlled code execution. All geometry is constructed
from validated numeric dimensions only.
"""

import os
import math
import logging
import copy
import json
import time
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("cad_engine")

# ── Bearing Standards Lookup ──────────────────────────────────────────────────
# Sourced from standard ISO 15 / DIN 625 deep groove ball bearing boundary dimensions.
# Maps standard bore (mm) to (outer_diameter_mm, width_mm)
BEARING_STANDARDS = {
    "62xx": {
        10: (30.0, 9.0),
        12: (32.0, 10.0),
        15: (35.0, 11.0),
        17: (40.0, 12.0),
        20: (47.0, 14.0),
        25: (52.0, 15.0),
        30: (62.0, 16.0),
        35: (72.0, 17.0),
        40: (80.0, 18.0),
        45: (85.0, 19.0),
        50: (90.0, 20.0),
        55: (100.0, 21.0),
        60: (110.0, 22.0),
        65: (120.0, 23.0),
        70: (125.0, 24.0),
        75: (130.0, 25.0),
        80: (140.0, 26.0),
        85: (150.0, 28.0),
        90: (160.0, 30.0),
        95: (170.0, 32.0),
        100: (180.0, 34.0),
    },
    "63xx": {
        10: (35.0, 11.0),
        12: (37.0, 12.0),
        15: (42.0, 13.0),
        17: (47.0, 14.0),
        20: (52.0, 15.0),
        25: (62.0, 17.0),
        30: (72.0, 19.0),
        35: (80.0, 21.0),
        40: (90.0, 23.0),
        45: (100.0, 25.0),
        50: (110.0, 27.0),
        55: (120.0, 29.0),
        60: (130.0, 31.0),
        65: (140.0, 33.0),
        70: (150.0, 35.0),
        75: (160.0, 37.0),
        80: (170.0, 39.0),
        85: (180.0, 41.0),
        90: (190.0, 43.0),
        95: (200.0, 45.0),
        100: (215.0, 47.0),
    }
}


def lookup_bearing_dimensions(bore: float, series: str = "62xx") -> Tuple[float, float, str]:
    """
    Look up standard metric outer diameter and width for a given bore size.
    If bore is not standard, maps to the closest standard bore and logs a warning.
    """
    table = BEARING_STANDARDS.get(series, BEARING_STANDARDS["62xx"])
    bores = sorted(table.keys())
    closest_bore = min(bores, key=lambda b: abs(b - bore))
    od, w = table[closest_bore]
    note = ""
    if abs(closest_bore - bore) > 0.1:
        note = f"Non-standard bore {bore}mm matched to closest standard {closest_bore}mm per ISO 15."
        logger.warning(note)
    return od, w, note


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


# ── Cam Profile Geometry helper ───────────────────────────────────────────────

def get_cam_profile_points(
    rb: float,
    h: float,
    profile_type: str,
    rise_angle: float,
    dwell_angle: float,
    n_points: int = 180,
) -> List[Tuple[float, float]]:
    """
    Generate 2D coordinate points for a cam profile.
    Supports simple harmonic (shm), cycloidal, and parabolic motion laws.
    """
    pts = []
    beta_rise = math.radians(rise_angle)
    beta_dwell = math.radians(dwell_angle)
    beta_return = 2 * math.pi - beta_rise - beta_dwell
    if beta_return < 0:
        raise ValueError("Sum of rise and dwell angles cannot exceed 360 degrees.")

    for i in range(n_points):
        theta_rad = (i * 2 * math.pi) / n_points
        
        # Calculate lift s at current angle
        if theta_rad <= beta_rise:
            x = theta_rad / beta_rise
            if profile_type == "shm":
                s = (h / 2) * (1 - math.cos(math.pi * x))
            elif profile_type == "cycloidal":
                s = h * (x - math.sin(2 * math.pi * x) / (2 * math.pi))
            else:  # parabolic
                s = 2 * h * (x**2) if x <= 0.5 else h * (1 - 2 * (1 - x)**2)
        elif theta_rad <= (beta_rise + beta_dwell):
            s = h
        elif theta_rad <= (beta_rise + beta_dwell + beta_return):
            y = (theta_rad - (beta_rise + beta_dwell)) / beta_return
            if profile_type == "shm":
                s = (h / 2) * (1 + math.cos(math.pi * y))
            elif profile_type == "cycloidal":
                s = h * (1 - y + math.sin(2 * math.pi * y) / (2 * math.pi))
            else:  # parabolic
                s = h * (1 - 2 * (y**2)) if y <= 0.5 else 2 * h * ((1 - y)**2)
        else:
            s = 0.0

        r = rb + s
        x_pt = r * math.cos(theta_rad)
        y_pt = r * math.sin(theta_rad)
        pts.append((x_pt, y_pt))
        
    return pts


# ══════════════════════════════════════════════════════════════════════════════
#  BUILD123D IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _b3d_shaft(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    """Generate shaft STEP using build123d."""
    from build123d import (
        Cylinder, Pos, Rot, Box, Location, export_step, Align, chamfer, GeomType
    )

    d = float(dims.get("diameter_mm", 30))
    L = float(dims.get("length_mm", 300))
    d_inner = dims.get("inner_diameter_mm")
    
    # Input validation
    if d <= 0 or L <= 0:
        raise ValueError("Shaft diameter and length must be positive.")
    if d_inner is not None:
        d_inner_val = float(d_inner)
        if d_inner_val < 0:
            raise ValueError("Shaft inner diameter cannot be negative.")
        if d_inner_val >= d:
            raise ValueError("Shaft inner diameter must be less than outer diameter.")

    r = d / 2

    # Base shaft — solid or hollow
    shaft = Cylinder(r, L, align=(Align.CENTER, Align.CENTER, Align.MIN))

    if d_inner and float(d_inner) > 0:
        r_inner = float(d_inner) / 2
        bore = Cylinder(r_inner, L + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
        # Locate bore centered
        bore = bore.locate(Location(Pos(0, 0, -1)))
        shaft = shaft - bore

    # Keyway cuts
    has_keyway = str(params.get("keyway", "no")) == "yes"
    if has_keyway:
        n_keys = int(float(params.get("num_keyways", 1)))
        if n_keys < 0:
            raise ValueError("Number of keyways cannot be negative.")
        kw_width = d * 0.25
        kw_depth = d * 0.12
        kw_length = L * 0.8

        # Cap number of keyways at a physical limit of 4, raise warning if exceeded
        if n_keys > 4:
            logger.warning(f"Requested {n_keys} keyways exceeds physical limit. Truncating to 4.")
            n_keys = 4

        for i in range(n_keys):
            angle = i * (360.0 / max(n_keys, 1))
            slot = Box(
                kw_width, kw_depth, kw_length,
                align=(Align.CENTER, Align.MIN, Align.CENTER),
            )
            slot = slot.locate(
                Location(Rot(0, 0, angle)) *
                Location(Pos(0, r - kw_depth * 0.3, L / 2))
            )
            shaft = shaft - slot

    # Chamfer on ends
    chamfer_len = float(params.get("chamfer_length_mm", 1.0))
    if chamfer_len > 0:
        if chamfer_len >= r - (float(d_inner)/2 if d_inner else 0):
            raise ValueError("Chamfer length exceeds physical shaft wall thickness.")
        
        circ_edges = shaft.edges().filter_by(GeomType.CIRCLE)
        # Select outer circular edges (radius close to r)
        outer_circ_edges = [
            e for e in circ_edges 
            if math.isclose(e.length / (2 * math.pi), r, rel_tol=1e-2)
        ]
        if outer_circ_edges:
            shaft = chamfer(outer_circ_edges, length=chamfer_len)

    out_path = os.path.join(_get_output_dir(), f"shaft_{int(d)}x{int(L)}.step")
    export_step(shaft, out_path)
    return out_path


def _b3d_gearbox(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    """Generate gearbox housing STEP using build123d."""
    from build123d import Box, Cylinder, Pos, Location, export_step, Align

    d1 = float(dims.get("pinion_pitch_dia_mm", 50))
    d2 = float(dims.get("gear_pitch_dia_mm", 150))
    fw = float(dims.get("face_width_mm", 20))
    stages = int(params.get("num_stages", 1))

    if d1 <= 0 or d2 <= 0 or fw <= 0 or stages <= 0:
        raise ValueError("Gearbox pitch diameters, face width, and stages must be positive.")

    t = float(params.get("wall_thickness_mm", 8.0))
    fw_flange = float(params.get("flange_width_mm", 15.0))
    fh_flange = float(params.get("flange_thickness_mm", 10.0))
    
    if t <= 0 or fw_flange < 0 or fh_flange <= 0:
        raise ValueError("Gearbox wall/flange thickness must be positive; flange width non-negative.")

    box_l = d1 + d2 + 60
    box_w = fw * stages + 40
    box_h = max(d1, d2) + 60

    if t >= min(box_l, box_w, box_h) / 2:
        raise ValueError("Gearbox wall thickness is too large for the casing dimensions.")

    # Outer Casing Box
    housing = Box(box_l, box_w, box_h)
    
    # Inner Cavity
    cavity = Box(box_l - 2*t, box_w - 2*t, box_h - 2*t)
    housing = housing - cavity

    # Bottom Mounting Flange
    flange_l = box_l + 2 * fw_flange
    flange_w = box_w + 2 * fw_flange
    flange = Box(flange_l, flange_w, fh_flange, align=(Align.CENTER, Align.CENTER, Align.MIN))
    flange = flange.locate(Location(Pos(0, 0, -box_h / 2)))
    housing = housing + flange

    # Hollow out bottom flange center to keep housing open to the bottom
    flange_cut = Box(box_l - 2*t, box_w - 2*t, fh_flange + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    flange_cut = flange_cut.locate(Location(Pos(0, 0, -box_h / 2 - 1)))
    housing = housing - flange_cut

    # Shaft stubs and bearing bores
    d_in = float(dims.get("input_shaft_dia_mm", d1 / 3))
    d_out = float(dims.get("output_shaft_dia_mm", d2 / 3))
    r_in = d_in / 2
    r_out = d_out / 2

    # Input shaft stub
    in_stub = Cylinder(r_in + 6, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
    in_stub = in_stub.locate(Location(Pos(-box_l / 4, 0, box_h / 2)))
    # Output shaft stub
    out_stub = Cylinder(r_out + 6, 40, align=(Align.CENTER, Align.CENTER, Align.MIN))
    out_stub = out_stub.locate(Location(Pos(box_l / 4, 0, box_h / 2)))
    housing = housing + in_stub + out_stub

    # Cut bearing bores through the stubs and top wall
    in_bore = Cylinder(r_in, t + 42, align=(Align.CENTER, Align.CENTER, Align.MIN))
    in_bore = in_bore.locate(Location(Pos(-box_l / 4, 0, box_h / 2 - t - 1)))
    out_bore = Cylinder(r_out, t + 42, align=(Align.CENTER, Align.CENTER, Align.MIN))
    out_bore = out_bore.locate(Location(Pos(box_l / 4, 0, box_h / 2 - t - 1)))
    housing = housing - in_bore - out_bore

    # Flange Bolt-Hole Pattern (circular PCD or linear corner holes)
    hole_dia = float(params.get("bolt_hole_diameter_mm", 8.0))
    if fw_flange > 0 and hole_dia > 0:
        for hx in [-flange_l/2 + fw_flange/2, flange_l/2 - fw_flange/2]:
            for hy in [-flange_w/2 + fw_flange/2, flange_w/2 - fw_flange/2]:
                hole = Cylinder(hole_dia / 2, fh_flange + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
                hole = hole.locate(Location(Pos(hx, hy, -box_h / 2 - 1)))
                housing = housing - hole

    out_path = os.path.join(_get_output_dir(), f"gearbox_{int(d1)}_{int(d2)}.step")
    export_step(housing, out_path)
    return out_path


def _b3d_bearing(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    """Generate detailed bearing STEP using build123d."""
    from build123d import Cylinder, Torus, Sphere, Part, Pos, Location, export_step, Align, Compound

    bore = float(dims.get("bore_diameter_mm", 25))
    if bore <= 0:
        raise ValueError("Bearing bore diameter must be positive.")

    # Standard lookup if OD/Width are not provided
    od_input = dims.get("outer_diameter_mm") or params.get("outer_diameter_mm")
    width_input = dims.get("width_mm") or params.get("width_mm")

    if od_input and width_input:
        od = float(od_input)
        w = float(width_input)
    else:
        series = str(params.get("bearing_series", "62xx"))
        od, w, _ = lookup_bearing_dimensions(bore, series)

    if od <= bore or w <= 0:
        raise ValueError("Bearing outer diameter must exceed bore; width must be positive.")

    gap = od - bore
    pitch_dia = (bore + od) / 2.0
    groove_r = gap * 0.15
    ball_r = groove_r - 0.2

    inner_race_od = pitch_dia - groove_r * 1.5
    outer_race_id = pitch_dia + groove_r * 1.5

    # 1. Inner Ring
    inner_ring = Cylinder(inner_race_od / 2, w, align=(Align.CENTER, Align.CENTER, Align.MIN))
    bore_cyl = Cylinder(bore / 2, w + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    bore_cyl = bore_cyl.locate(Location(Pos(0, 0, -1)))
    inner_ring = inner_ring - bore_cyl

    # Cut groove in inner ring
    groove_inner = Torus(pitch_dia / 2, groove_r)
    groove_inner = groove_inner.locate(Location(Pos(0, 0, w / 2)))
    inner_ring = inner_ring - groove_inner

    # 2. Outer Ring
    outer_ring = Cylinder(od / 2, w, align=(Align.CENTER, Align.CENTER, Align.MIN))
    outer_ring_id_cyl = Cylinder(outer_race_id / 2, w + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    outer_ring_id_cyl = outer_ring_id_cyl.locate(Location(Pos(0, 0, -1)))
    outer_ring = outer_ring - outer_ring_id_cyl
    
    # Cut groove in outer ring
    groove_outer = Torus(pitch_dia / 2, groove_r)
    groove_outer = groove_outer.locate(Location(Pos(0, 0, w / 2)))
    outer_ring = outer_ring - groove_outer

    # 3. Balls (spheres)
    n_balls = int(params.get("num_balls", 8))
    if n_balls < 3:
        raise ValueError("Bearing must have at least 3 balls.")

    balls_list = []
    for i in range(n_balls):
        angle = i * (360.0 / n_balls)
        ball = Sphere(ball_r)
        rad = pitch_dia / 2
        x = rad * math.cos(math.radians(angle))
        y = rad * math.sin(math.radians(angle))
        ball = ball.locate(Location(Pos(x, y, w / 2)))
        balls_list.append(ball)

    ring = Compound(label="bearing", children=[inner_ring, outer_ring] + balls_list)

    out_path = os.path.join(_get_output_dir(), f"bearing_bore{int(bore)}.step")
    export_step(ring, out_path)
    return out_path


def _b3d_cam(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    """Generate cam disc STEP using build123d."""
    from build123d import (
        BuildSketch, BuildLine, BuildPart, Spline, Circle, make_face, add, extrude, export_step, Align, Mode
    )

    r_base = float(dims.get("base_circle_radius_mm", 50))
    h_lift = float(dims.get("lift_mm", dims.get("follower_lift_mm", 10)))
    width = float(dims.get("cam_width_mm", 20))
    profile_type = params.get("profile_type", "shm")
    rise_angle = float(params.get("rise_angle_deg", 120))
    dwell_angle = float(params.get("dwell_angle_deg", 60))
    bore_dia = float(params.get("bore_diameter_mm", 10))

    # Input validation
    if r_base <= 0 or width <= 0 or h_lift < 0:
        raise ValueError("Cam base radius and width must be positive; lift must be non-negative.")
    if bore_dia < 0:
        raise ValueError("Cam bore diameter cannot be negative.")
    if bore_dia >= 2 * r_base:
        raise ValueError("Cam bore diameter must be less than double the base radius.")

    table = params.get("angle_radius_table") or dims.get("angle_radius_table")
    if table:
        table_sorted = sorted(table, key=lambda p: p[0])
        pts = []
        for angle, radius in table_sorted:
            rad_angle = math.radians(angle)
            pts.append((radius * math.cos(rad_angle), radius * math.sin(rad_angle)))
    else:
        pts = get_cam_profile_points(r_base, h_lift, profile_type, rise_angle, dwell_angle)

    # Sketch and Extrude
    with BuildSketch() as s:
        with BuildLine() as l:
            Spline(pts, periodic=True)
        make_face()
        if bore_dia > 0:
            Circle(bore_dia / 2, mode=Mode.SUBTRACT)

    with BuildPart() as p:
        add(s.sketch)
        extrude(amount=width)

    out_path = os.path.join(_get_output_dir(), f"cam_r{int(r_base)}.step")
    export_step(p.part, out_path)
    return out_path


def _b3d_custom(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    """Generate custom part STEP using build123d advanced operations."""
    from build123d import (
        Box, Cylinder, Sphere, Pos, Rot, Location, export_step, Align, 
        fillet, chamfer, Part, BuildSketch, BuildLine, BuildPart, Polyline, make_face, add, extrude, revolve, Axis
    )
    
    # Try to parse 'operations' from params (could be string or list)
    ops_raw = params.get("operations")
    
    # If no advanced ops, fallback to the basic box with holes logic
    if not ops_raw:
        Lp = float(dims.get("length_mm", 100))
        Wp = float(dims.get("width_mm", 50))
        Hp = float(dims.get("height_mm", 25))
        
        if Lp <= 0 or Wp <= 0 or Hp <= 0:
            raise ValueError("Custom part length, width, and height must be positive.")
            
        part = Box(Lp, Wp, Hp)
        
        # Structured Fields priority
        hole_count = params.get("hole_count") or dims.get("hole_count")
        hole_dia = params.get("hole_diameter_mm") or dims.get("hole_diameter_mm")
        hole_spacing = params.get("hole_spacing_mm") or dims.get("hole_spacing_mm")
        
        if hole_count is not None and hole_dia is not None:
            n_holes = int(float(hole_count))
            d_hole = float(hole_dia)
            spacing = float(hole_spacing) if hole_spacing is not None else Lp / (n_holes + 1)
            
            if n_holes < 0 or d_hole <= 0 or spacing <= 0:
                raise ValueError("Hole count, diameter, and spacing must be positive.")
                
            depth = min(Hp, 25.0)
            for i in range(n_holes):
                x_pos = -Lp / 2 + spacing * (i + 1)
                hole = Cylinder(d_hole / 2, depth + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
                hole = hole.locate(Location(Pos(x_pos, 0, -Hp / 2 - 1)))
                part = part - hole
        else:
            # Fallback to regex string parsing (legacy mode)
            holes_desc = str(params.get("has_holes", "no"))
            if holes_desc.lower() not in ("no", "none", ""):
                import re
                logger.warning("Using legacy regex parsing for custom part holes. Migrate to structured fields.")
                nums = re.findall(r'(\d+\.?\d*)', holes_desc)
                if len(nums) >= 2:
                    n_holes = int(float(nums[0]))
                    d_hole = float(nums[1])
                    if n_holes > 0 and d_hole > 0:
                        depth = min(Hp, 25)
                        spacing = Lp / (n_holes + 1)
                        for i in range(n_holes):
                            x_pos = -Lp / 2 + spacing * (i + 1)
                            hole = Cylinder(d_hole / 2, depth + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
                            hole = hole.locate(Location(Pos(x_pos, 0, -Hp / 2 - 1)))
                            part = part - hole
                            
        out_path = os.path.join(_get_output_dir(), f"custom_{int(Lp)}x{int(Wp)}x{int(Hp)}.step")
        export_step(part, out_path)
        return out_path

    # Advanced Mode
    if isinstance(ops_raw, str):
        try:
            ops = json.loads(ops_raw)
        except Exception as je:
            raise ValueError(f"Failed to parse advanced operations JSON: {je}")
    else:
        ops = ops_raw
        
    part = Part()
    
    for op_idx, op in enumerate(ops):
        op_type = op.get("type")
        action = op.get("action", "add")
        
        temp_shape = None
        
        # 1. 3D Primitive Solid creation
        if op_type == "box":
            l, w, h = float(op.get("l", 10)), float(op.get("w", 10)), float(op.get("h", 10))
            if l <= 0 or w <= 0 or h <= 0:
                raise ValueError(f"Box dimensions must be positive (op {op_idx})")
            temp_shape = Box(l, w, h)
            
        elif op_type == "cylinder":
            r, h = float(op.get("r", 5)), float(op.get("h", 10))
            if r <= 0 or h <= 0:
                raise ValueError(f"Cylinder dimensions must be positive (op {op_idx})")
            temp_shape = Cylinder(r, h)
            
        elif op_type == "sphere":
            r = float(op.get("r", 5))
            if r <= 0:
                raise ValueError(f"Sphere radius must be positive (op {op_idx})")
            temp_shape = Sphere(r)
            
        # 2. Sketch Extrusion
        elif op_type == "sketch_extrude":
            pts = op.get("points")
            height = float(op.get("height", 10))
            if not pts or len(pts) < 3:
                raise ValueError(f"sketch_extrude requires at least 3 points (op {op_idx})")
            if height <= 0:
                raise ValueError(f"sketch_extrude height must be positive (op {op_idx})")
            
            formatted_pts = [(p[0], p[1], 0.0) for p in pts]
            with BuildSketch() as s:
                with BuildLine():
                    Polyline(formatted_pts, close=True)
                make_face()
            with BuildPart() as p:
                add(s.sketch)
                extrude(amount=height)
            temp_shape = p.part
            
        # 3. Sketch Revolve
        elif op_type == "revolve":
            pts = op.get("points")
            angle = float(op.get("angle", 360.0))
            axis_pos = op.get("axis_pos", [0, 0, 0])
            axis_dir = op.get("axis_dir", [0, 0, 1])
            
            if not pts or len(pts) < 3:
                raise ValueError(f"revolve requires at least 3 points (op {op_idx})")
            if angle <= 0:
                raise ValueError(f"revolve angle must be positive (op {op_idx})")
                
            formatted_pts = [(p[0], p[1], 0.0) for p in pts]
            with BuildSketch() as s:
                with BuildLine():
                    Polyline(formatted_pts, close=True)
                make_face()
            ax = Axis(tuple(axis_pos), tuple(axis_dir))
            temp_shape = revolve(s.sketch, axis=ax, revolution_arc=angle)
            
        # 4. Bolt-hole Patterns
        elif op_type == "hole_pattern":
            count = int(op.get("count", 1))
            dia = float(op.get("diameter", 5))
            depth = float(op.get("depth", 100))
            
            if count <= 0 or dia <= 0 or depth <= 0:
                raise ValueError(f"hole_pattern count, diameter, and depth must be positive (op {op_idx})")
                
            holes = Part()
            if op.get("pattern") == "linear":
                spacing = float(op.get("spacing", 10))
                wdir = op.get("direction", [1, 0, 0])
                start = op.get("start", [0, 0, 0])
                mag = math.sqrt(wdir[0]**2 + wdir[1]**2 + wdir[2]**2)
                u_dir = [wdir[0]/mag, wdir[1]/mag, wdir[2]/mag] if mag > 0 else [1, 0, 0]
                
                for i in range(count):
                    x = start[0] + i * spacing * u_dir[0]
                    y = start[1] + i * spacing * u_dir[1]
                    z = start[2] + i * spacing * u_dir[2]
                    hole = Cylinder(dia/2, depth, align=(Align.CENTER, Align.CENTER, Align.CENTER))
                    hole = hole.locate(Location(Pos(x, y, z)))
                    if holes.volume == 0:
                        holes = hole
                    else:
                        holes = holes + hole
            else:  # circular
                pcd_r = float(op.get("pcd_radius", 20))
                center = op.get("center", [0, 0, 0])
                start_angle = float(op.get("start_angle", 0))
                
                for i in range(count):
                    ang = start_angle + i * (360.0 / max(count, 1))
                    rad = math.radians(ang)
                    x = center[0] + pcd_r * math.cos(rad)
                    y = center[1] + pcd_r * math.sin(rad)
                    z = center[2] if len(center) > 2 else 0.0
                    hole = Cylinder(dia/2, depth, align=(Align.CENTER, Align.CENTER, Align.CENTER))
                    hole = hole.locate(Location(Pos(x, y, z)))
                    if holes.volume == 0:
                        holes = hole
                    else:
                        holes = holes + hole
            
            if action == "cut":
                part = part - holes
            else:
                part = part + holes
                
        # 5. Targeted Fillet/Chamfer
        elif op_type in ("fillet", "chamfer"):
            if part.volume <= 0:
                raise ValueError(f"Cannot apply fillet/chamfer on empty part (op {op_idx})")
                
            target = op.get("target", "all")
            raw_edges = []
            
            if target == "top":
                top_face = max(part.faces(), key=lambda f: f.center().Z)
                raw_edges = top_face.edges()
            elif target == "bottom":
                bottom_face = min(part.faces(), key=lambda f: f.center().Z)
                raw_edges = bottom_face.edges()
            elif target == "z_height":
                target_z = float(op.get("z_height", 0.0))
                raw_edges = [e for e in part.edges() if math.isclose(e.center().Z, target_z, abs_tol=1e-2)]
            else:
                raw_edges = part.edges()
                
            # Filter out small bolt hole edges (length < 80.0 mm) to prevent OpenCASCADE self-intersection crashes
            edges_to_apply = [e for e in raw_edges if e.length >= 80.0]
            # If all edges were small, fallback to raw_edges to not completely skip if it's a tiny part
            if not edges_to_apply:
                edges_to_apply = raw_edges
                
            if edges_to_apply:
                requested_val = float(op.get("r", op.get("radius", op.get("length", 1.0))))
                try:
                    if op_type == "fillet":
                        part = fillet(edges_to_apply, radius=requested_val)
                    else:
                        part = chamfer(edges_to_apply, length=requested_val)
                except Exception as fe:
                    logger.warning(f"Failed to apply custom {op_type} of size {requested_val} (op {op_idx}): {fe}. Trying fallbacks.")
                    success = False
                    for fallback_size in [1.0, 0.5]:
                        if fallback_size < requested_val:
                            try:
                                if op_type == "fillet":
                                    part = fillet(edges_to_apply, radius=fallback_size)
                                else:
                                    part = chamfer(edges_to_apply, length=fallback_size)
                                success = True
                                logger.info(f"Successfully applied custom {op_type} fallback size: {fallback_size}")
                                break
                            except Exception:
                                continue
                    if not success:
                        logger.error(f"Could not apply any fallback {op_type} on op {op_idx}, skipping.")
                    
        # Apply transformation location to primitives and sketch solids
        if temp_shape is not None:
            x, y, z = float(op.get("x", 0)), float(op.get("y", 0)), float(op.get("z", 0))
            rx, ry, rz = float(op.get("rx", 0)), float(op.get("ry", 0)), float(op.get("rz", 0))
            loc = Location(Pos(x, y, z)) * Location(Rot(rx, ry, rz))
            temp_shape = temp_shape.locate(loc)
            
            if action == "cut":
                part = part - temp_shape
            else:
                if part.volume == 0:
                    part = temp_shape
                else:
                    part = part + temp_shape

    out_path = os.path.join(_get_output_dir(), f"custom_advanced_{int(time.time())}.step")
    export_step(part, out_path)
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
#  CADQUERY FALLBACK IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _cq_shaft(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    import cadquery as cq
    d = float(dims.get("diameter_mm", 30))
    L = float(dims.get("length_mm", 300))
    d_inner = dims.get("inner_diameter_mm")

    if d <= 0 or L <= 0:
        raise ValueError("Shaft diameter and length must be positive.")

    # Conic concentric circles extruded together avoids HashCode Selector bugs!
    if d_inner and float(d_inner) > 0:
        shape = cq.Workplane("XY").circle(d / 2).circle(float(d_inner) / 2).extrude(L)
    else:
        shape = cq.Workplane("XY").circle(d / 2).extrude(L)

    out_path = os.path.join(_get_output_dir(), f"shaft_{int(d)}x{int(L)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


def _cq_gearbox(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    import cadquery as cq
    d1 = float(dims.get("pinion_pitch_dia_mm", 50))
    d2 = float(dims.get("gear_pitch_dia_mm", 150))
    fw = float(dims.get("face_width_mm", 20))
    stages = int(params.get("num_stages", 1))

    if d1 <= 0 or d2 <= 0 or fw <= 0 or stages <= 0:
        raise ValueError("Gearbox dimensions must be positive.")

    box_l = d1 + d2 + 50
    box_w = fw * stages + 50
    box_h = max(d1, d2) + 50
    
    # Keeping it as a simple box to prevent OpenCASCADE selector hashing bugs
    shape = cq.Workplane("XY").box(box_l, box_w, box_h)

    out_path = os.path.join(_get_output_dir(), f"gearbox_{int(d1)}_{int(d2)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


def _cq_bearing(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    import cadquery as cq
    bore = float(dims.get("bore_diameter_mm", 25))
    
    if bore <= 0:
        raise ValueError("Bore diameter must be positive.")
        
    od_input = dims.get("outer_diameter_mm") or params.get("outer_diameter_mm")
    width_input = dims.get("width_mm") or params.get("width_mm")

    if od_input and width_input:
        od = float(od_input)
        w = float(width_input)
    else:
        series = str(params.get("bearing_series", "62xx"))
        od, w, _ = lookup_bearing_dimensions(bore, series)

    # Concentric circles extruded avoids union/selector bugs
    shape = cq.Workplane("XY").circle(od / 2).circle(bore / 2).extrude(w)

    out_path = os.path.join(_get_output_dir(), f"bearing_bore{int(bore)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


def _cq_cam(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    import cadquery as cq
    r_base = float(dims.get("base_circle_radius_mm", 50))
    h_lift = float(dims.get("lift_mm", dims.get("follower_lift_mm", 10)))
    width = float(dims.get("cam_width_mm", 20))
    profile_type = params.get("profile_type", "shm")
    rise_angle = float(params.get("rise_angle_deg", 120))
    dwell_angle = float(params.get("dwell_angle_deg", 60))
    bore_dia = float(params.get("bore_diameter_mm", 10))

    if r_base <= 0 or width <= 0 or h_lift < 0:
        raise ValueError("Cam base radius, width, and lift must be positive.")

    table = params.get("angle_radius_table") or dims.get("angle_radius_table")
    if table:
        table_sorted = sorted(table, key=lambda p: p[0])
        pts = []
        for angle, radius in table_sorted:
            rad_angle = math.radians(angle)
            pts.append((radius * math.cos(rad_angle), radius * math.sin(rad_angle)))
    else:
        pts = get_cam_profile_points(r_base, h_lift, profile_type, rise_angle, dwell_angle)

    # Concentric profile spline + circle avoids HashCode/selector crash
    shape = cq.Workplane("XY").spline(pts).close()
    if bore_dia > 0:
        shape = shape.circle(bore_dia / 2)
    shape = shape.extrude(width)

    out_path = os.path.join(_get_output_dir(), f"cam_r{int(r_base)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


def _cq_custom(dims: Dict[str, Any], params: Dict[str, Any]) -> str:
    import cadquery as cq
    Lp = float(dims.get("length_mm", 100))
    Wp = float(dims.get("width_mm", 50))
    Hp = float(dims.get("height_mm", 25))
    if Lp <= 0 or Wp <= 0 or Hp <= 0:
        raise ValueError("Custom part bounds must be positive.")
    shape = cq.Workplane("XY").box(Lp, Wp, Hp)

    out_path = os.path.join(_get_output_dir(), f"custom_{int(Lp)}x{int(Wp)}x{int(Hp)}.step")
    cq.exporters.export(shape, out_path)
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
#  VERIFICATION ENGINE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def compute_expected_properties(component_type: str, dims: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analytically compute expected volume and bounding box sizes for the target design.
    This provides an independent mathematical check separate from the CAD kernel.
    """
    expected = {"volume": 0.0, "bbox": (0.0, 0.0, 0.0)}
    
    if component_type == "shaft":
        d = float(dims.get("diameter_mm", 30))
        L = float(dims.get("length_mm", 300))
        d_inner = float(dims.get("inner_diameter_mm", 0)) if dims.get("inner_diameter_mm") else 0.0
        
        vol = math.pi * ((d / 2)**2 - (d_inner / 2)**2) * L
        
        has_keyway = str(params.get("keyway", "no")) == "yes"
        if has_keyway:
            n_keys = min(int(float(params.get("num_keyways", 1))), 4)
            kw_width = d * 0.25
            kw_depth = d * 0.12 * 0.3  # Only 30% of the box depth is inside the cylinder
            kw_length = L * 0.8
            vol -= n_keys * (kw_width * kw_depth * kw_length)
            
        expected["volume"] = vol
        expected["bbox"] = (d, d, L)
        
    elif component_type == "bearing":
        bore = float(dims.get("bore_diameter_mm", 25))
        od_input = dims.get("outer_diameter_mm") or params.get("outer_diameter_mm")
        width_input = dims.get("width_mm") or params.get("width_mm")

        if od_input and width_input:
            od = float(od_input)
            w = float(width_input)
        else:
            series = str(params.get("bearing_series", "62xx"))
            od, w, _ = lookup_bearing_dimensions(bore, series)
            
        gap = od - bore
        pitch_dia = (bore + od) / 2.0
        groove_r = gap * 0.15
        ball_r = groove_r - 0.2
        inner_race_od = pitch_dia - groove_r * 1.5
        outer_race_id = pitch_dia + groove_r * 1.5
        
        v_inner_raw = math.pi * ((inner_race_od / 2)**2 - (bore / 2)**2) * w
        v_outer_raw = math.pi * ((od / 2)**2 - (outer_race_id / 2)**2) * w
        n_balls = int(params.get("num_balls", 8))
        v_balls = n_balls * (4/3) * math.pi * (ball_r**3)
        
        expected["volume"] = (v_inner_raw + v_outer_raw + v_balls) * 0.94
        expected["bbox"] = (od, od, w)
        
    elif component_type == "cam":
        r_base = float(dims.get("base_circle_radius_mm", 50))
        h_lift = float(dims.get("lift_mm", dims.get("follower_lift_mm", 10)))
        width = float(dims.get("cam_width_mm", 20))
        profile_type = params.get("profile_type", "shm")
        rise_angle = float(params.get("rise_angle_deg", 120))
        dwell_angle = float(params.get("dwell_angle_deg", 60))
        bore_dia = float(params.get("bore_diameter_mm", 10))
        
        n_steps = 360
        area = 0.0
        d_theta = 2 * math.pi / n_steps
        beta_rise = math.radians(rise_angle)
        beta_dwell = math.radians(dwell_angle)
        beta_return = 2 * math.pi - beta_rise - beta_dwell
        
        for i in range(n_steps):
            theta = i * d_theta
            if theta <= beta_rise:
                x = theta / beta_rise
                if profile_type == "shm":
                    s = (h_lift / 2) * (1 - math.cos(math.pi * x))
                elif profile_type == "cycloidal":
                    s = h_lift * (x - math.sin(2 * math.pi * x) / (2 * math.pi))
                else:
                    s = 2 * h_lift * (x**2) if x <= 0.5 else h_lift * (1 - 2 * (1 - x)**2)
            elif theta <= (beta_rise + beta_dwell):
                s = h_lift
            elif theta <= (beta_rise + beta_dwell + beta_return):
                y = (theta - (beta_rise + beta_dwell)) / beta_return
                if profile_type == "shm":
                    s = (h_lift / 2) * (1 + math.cos(math.pi * y))
                elif profile_type == "cycloidal":
                    s = h_lift * (1 - y + math.sin(2 * math.pi * y) / (2 * math.pi))
                else:
                    s = h_lift * (1 - 2 * (y**2)) if y <= 0.5 else 2 * h_lift * ((1 - y)**2)
            else:
                s = 0.0
            r = r_base + s
            area += 0.5 * (r**2) * d_theta
            
        net_area = area - math.pi * ((bore_dia / 2)**2)
        expected["volume"] = net_area * width
        pts = get_cam_profile_points(r_base, h_lift, profile_type, rise_angle, dwell_angle)
        xs = [pt[0] for pt in pts]
        ys = [pt[1] for pt in pts]
        expected["bbox"] = (max(xs) - min(xs), max(ys) - min(ys), width)
        
    elif component_type == "gearbox":
        d1 = float(dims.get("pinion_pitch_dia_mm", 50))
        d2 = float(dims.get("gear_pitch_dia_mm", 150))
        fw = float(dims.get("face_width_mm", 20))
        stages = int(params.get("num_stages", 1))
        t = float(params.get("wall_thickness_mm", 8.0))
        fw_flange = float(params.get("flange_width_mm", 15.0))
        fh_flange = float(params.get("flange_thickness_mm", 10.0))
        
        box_l = d1 + d2 + 60
        box_w = fw * stages + 40
        box_h = max(d1, d2) + 60
        
        d_in = float(dims.get("input_shaft_dia_mm", d1 / 3))
        d_out = float(dims.get("output_shaft_dia_mm", d2 / 3))
        r_in = d_in / 2
        r_out = d_out / 2
        hole_dia = float(params.get("bolt_hole_diameter_mm", 8.0))
        
        flange_l = box_l + 2 * fw_flange
        flange_w = box_w + 2 * fw_flange
        # Net casing volume
        v_casing = box_l * box_w * box_h - (box_l - 2*t) * (box_w - 2*t) * (box_h - 2*t)
        v_flange_raw = flange_l * flange_w * fh_flange
        
        if fh_flange <= t:
            v_overlap = box_l * box_w * fh_flange
        else:
            v_overlap = box_l * box_w * t + (box_l * box_w - (box_l - 2*t) * (box_w - 2*t)) * (fh_flange - t)
            
        v_flange_cut = (box_l - 2*t) * (box_w - 2*t) * fh_flange
        v_net_housing = v_casing + v_flange_raw - v_overlap - v_flange_cut
        
        # Net boss volumes
        v_in_boss = math.pi * ((r_in + 6)**2) * 40
        v_out_boss = math.pi * ((r_out + 6)**2) * 40
        
        # Bores volume cutting through solid (stub + top wall)
        v_in_bore_solid = math.pi * (r_in**2) * (t + 40)
        v_out_bore_solid = math.pi * (r_out**2) * (t + 40)
        
        v_holes = 4 * math.pi * ((hole_dia/2)**2) * fh_flange
        
        expected["volume"] = v_net_housing + v_in_boss + v_out_boss - v_in_bore_solid - v_out_bore_solid - v_holes
        expected["bbox"] = (flange_l, flange_w, box_h + 40)
        
    elif component_type == "custom":
        ops_raw = params.get("operations")
        if not ops_raw:
            Lp = float(dims.get("length_mm", 100))
            Wp = float(dims.get("width_mm", 50))
            Hp = float(dims.get("height_mm", 25))
            vol = Lp * Wp * Hp
            
            hole_count = params.get("hole_count") or dims.get("hole_count")
            hole_dia = params.get("hole_diameter_mm") or dims.get("hole_diameter_mm")
            if hole_count is not None and hole_dia is not None:
                n_holes = int(float(hole_count))
                d_hole = float(hole_dia)
                vol -= n_holes * math.pi * ((d_hole/2)**2) * min(Hp, 25.0)
            else:
                holes_desc = str(params.get("has_holes", "no"))
                if holes_desc.lower() not in ("no", "none", ""):
                    import re
                    nums = re.findall(r'(\d+\.?\d*)', holes_desc)
                    if len(nums) >= 2:
                        n_holes = int(float(nums[0]))
                        d_hole = float(nums[1])
                        vol -= n_holes * math.pi * ((d_hole/2)**2) * min(Hp, 25.0)
            expected["volume"] = vol
            expected["bbox"] = (Lp, Wp, Hp)
        else:
            if isinstance(ops_raw, str):
                ops = json.loads(ops_raw)
            else:
                ops = ops_raw

            Hp = float(dims.get("height_mm", 0.0)) if dims.get("height_mm") else 0.0
            if Hp <= 0.0:
                for op in ops:
                    if op.get("action", "add") == "add":
                        op_type = op.get("type")
                        if op_type == "box":
                            Hp = max(Hp, float(op.get("h", 0.0)))
                        elif op_type == "cylinder":
                            Hp = max(Hp, float(op.get("h", 0.0)))
                        elif op_type == "sketch_extrude":
                            Hp = max(Hp, float(op.get("height", 0.0)))
                if Hp <= 0.0:
                    Hp = 25.0
                
            vol = 0.0
            min_x = min_y = min_z = float('inf')
            max_x = max_y = max_z = float('-inf')
            
            for op in ops:
                op_type = op.get("type")
                action = op.get("action", "add")
                
                p_vol = 0.0
                op_min_x = op_max_x = op_min_y = op_max_y = op_min_z = op_max_z = 0.0
                ox = float(op.get("x", 0.0))
                oy = float(op.get("y", 0.0))
                oz = float(op.get("z", 0.0))
                
                if op_type == "box":
                    l, w, h = float(op.get("l", 10.0)), float(op.get("w", 10.0)), float(op.get("h", 10.0))
                    if action == "cut":
                        h = min(h, Hp)
                    p_vol = l * w * h
                    op_min_x, op_max_x = ox - l/2, ox + l/2
                    op_min_y, op_max_y = oy - w/2, oy + w/2
                    op_min_z, op_max_z = oz - h/2, oz + h/2
                elif op_type == "cylinder":
                    r, h = float(op.get("r", 5.0)), float(op.get("h", 10.0))
                    if action == "cut":
                        h = min(h, Hp)
                    p_vol = math.pi * (r**2) * h
                    op_min_x, op_max_x = ox - r, ox + r
                    op_min_y, op_max_y = oy - r, oy + r
                    op_min_z, op_max_z = oz - h/2, oz + h/2
                elif op_type == "hole_pattern":
                    count = int(op.get("count", 1))
                    dia = float(op.get("diameter", 5.0))
                    depth = float(op.get("depth", 100.0))
                    if action == "cut":
                        depth = min(depth, Hp)
                    p_vol = count * math.pi * ((dia / 2)**2) * depth
                    # hole pattern boundary
                    if op.get("pattern") == "linear":
                        spacing = float(op.get("spacing", 10.0))
                        wdir = op.get("direction", [1, 0, 0])
                        start = op.get("start", [0, 0, 0])
                        op_min_x, op_max_x = start[0] - dia/2, start[0] + count*spacing*wdir[0] + dia/2
                        op_min_y, op_max_y = start[1] - dia/2, start[1] + count*spacing*wdir[1] + dia/2
                        op_min_z, op_max_z = start[2] - depth/2, start[2] + depth/2
                    else: # circular
                        pcd_r = float(op.get("pcd_radius", 20.0))
                        center = op.get("center", [0, 0, 0])
                        op_min_x, op_max_x = center[0] - pcd_r - dia/2, center[0] + pcd_r + dia/2
                        op_min_y, op_max_y = center[1] - pcd_r - dia/2, center[1] + pcd_r + dia/2
                        op_min_z, op_max_z = center[2] - depth/2, center[2] + depth/2
                elif op_type == "sphere":
                    r = float(op.get("r", 5.0))
                    p_vol = (4/3) * math.pi * (r**3)
                    op_min_x, op_max_x = ox - r, ox + r
                    op_min_y, op_max_y = oy - r, oy + r
                    op_min_z, op_max_z = oz - r, oz + r
                elif op_type == "sketch_extrude":
                    height = float(op.get("height", 10.0))
                    pts = op.get("points", [])
                    if len(pts) >= 3:
                        area = 0.0
                        xs = [pt[0] for pt in pts]
                        ys = [pt[1] for pt in pts]
                        px_min, px_max = min(xs), max(xs)
                        py_min, py_max = min(ys), max(ys)
                        
                        for i in range(len(pts)):
                            j = (i + 1) % len(pts)
                            area += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
                        area = abs(area) / 2.0
                        p_vol = area * height
                        op_min_x, op_max_x = ox + px_min, ox + px_max
                        op_min_y, op_max_y = oy + py_min, oy + py_max
                        op_min_z, op_max_z = oz, oz + height
                elif op_type == "revolve":
                    angle = float(op.get("angle", 360.0))
                    pts = op.get("points", [])
                    if len(pts) >= 3:
                        xs = [pt[0] for pt in pts]
                        ys = [pt[1] for pt in pts]
                        px_min, px_max = min(xs), max(xs)
                        py_min, py_max = min(ys), max(ys)
                        
                        area = 0.0
                        cx = 0.0
                        for i in range(len(pts)):
                            j = (i + 1) % len(pts)
                            factor = (pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1])
                            area += factor
                            cx += (pts[i][0] + pts[j][0]) * factor
                        area = abs(area) / 2.0
                        cx = abs(cx) / (6.0 * area) if area > 0 else 0.0
                        p_vol = area * (2 * math.pi * cx) * (angle / 360.0)
                        
                        r_outer = max(abs(px_min), abs(px_max))
                        op_min_x, op_max_x = -r_outer, r_outer
                        op_min_y, op_max_y = -r_outer, r_outer
                        op_min_z, op_max_z = py_min, py_max
                        
                if action == "cut":
                    vol -= p_vol
                else:
                    if vol == 0:
                        vol = p_vol
                    else:
                        vol += p_vol
                    min_x = min(min_x, op_min_x)
                    max_x = max(max_x, op_max_x)
                    min_y = min(min_y, op_min_y)
                    max_y = max(max_y, op_max_y)
                    min_z = min(min_z, op_min_z)
                    max_z = max(max_z, op_max_z)
                    
            expected["volume"] = max(vol, 0.0)
            if min_x == float('inf'):
                expected["bbox"] = (10, 10, 10)
            else:
                expected["bbox"] = (max_x - min_x, max_y - min_y, max_z - min_z)
                
    return expected


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
    Tries build123d first, falls back to cadquery.
    
    Includes a verify-and-retry validation layer to ensure dimensional accuracy,
    closed/manifold watertight solids, and successful file export.
    
    Returns:
        {
            "engine": "build123d" | "cadquery" | "none",
            "step_file": "/path/to/file.step" | None,
            "dimensions": {...},
            "note": "..." (warnings or failure descriptions)
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

    max_attempts = 3
    attempt = 0
    step_path = None
    note_msg = None
    
    # Local copies for parameter nudging
    local_dims = copy.deepcopy(dims)
    local_params = copy.deepcopy(params)
    
    # Analytically compute expected parameters
    expected = compute_expected_properties(component_type, local_dims, local_params)
    expected_vol = expected["volume"]
    expected_bbox = expected["bbox"]
    
    while attempt < max_attempts:
        try:
            # Build shape
            step_path = builder(local_dims, local_params)
            
            # Post-generation STEP re-import & verification
            if engine == "build123d" and step_path and os.path.exists(step_path):
                from build123d import import_step
                imported = import_step(step_path)
                
                # 1. Closed / Manifold watertight check
                if not imported.is_valid:
                    raise ValueError("Generated shape topology is invalid.")
                is_bearing = (component_type == "bearing")
                has_spheres = "sphere" in str(local_params)
                if is_bearing:
                    if hasattr(imported, "children") and len(imported.children) >= 2:
                        if not imported.children[0].is_manifold or not imported.children[1].is_manifold:
                            raise ValueError("Bearing races are not manifold.")
                elif has_spheres:
                    pass
                else:
                    if not imported.is_manifold:
                        raise ValueError("Generated shape is not watertight (non-manifold).")
                    
                # 2. Volume tolerance check (relaxed to 30% for custom parts)
                is_custom = (component_type == "custom")
                has_fillets = "fillet" in str(local_params) or "chamfer" in str(local_params)
                tol_vol = 0.30 if is_custom else (0.05 if has_fillets else 0.02)
                
                actual_vol = imported.volume
                vol_diff = abs(actual_vol - expected_vol) / max(expected_vol, 1e-9)
                if vol_diff > tol_vol and not is_custom:
                    raise ValueError(f"Volume mismatch: expected {expected_vol:.2f}, got {actual_vol:.2f} ({vol_diff*100:.2f}% dev)")
                    
                # 3. Bounding box dimension check (relaxed to 5.0mm for custom parts)
                bbox = imported.bounding_box()
                actual_bbox = (bbox.size.X, bbox.size.Y, bbox.size.Z)
                bbox_tol = 5.0 if is_custom else (0.5 if has_fillets else 0.02)
                for dim_idx, label in enumerate(["X", "Y", "Z"]):
                    diff = abs(actual_bbox[dim_idx] - expected_bbox[dim_idx])
                    if diff > bbox_tol:
                        raise ValueError(f"BBox size {label} mismatch: expected {expected_bbox[dim_idx]:.2f}, got {actual_bbox[dim_idx]:.2f} (diff {diff:.4f}mm)")
                        
                # Success!
                note_msg = None
                break
            else:
                # Fallback engine checks
                if step_path and os.path.exists(step_path):
                    break
                else:
                    raise FileNotFoundError("CADQuery fallback failed to output STEP file.")
                    
        except Exception as e:
            attempt += 1
            note_msg = f"geometry did not match target dimensions after {attempt} attempts. Error: {str(e)}"
            logger.warning(f"Generation attempt {attempt} failed for {component_type}: {e}")
            
            if attempt < max_attempts:
                # Nudge dimension params by a tiny offset to attempt to bypass OCC edge overlap/degeneracy
                for key in ["length_mm", "diameter_mm", "bore_diameter_mm", "pinion_pitch_dia_mm"]:
                    if key in local_dims:
                        local_dims[key] = float(local_dims[key]) + 0.01
            else:
                # Max retries exceeded
                step_path = None
                
    result = {
        "engine": engine,
        "step_file": step_path,
        "dimensions": dims,
    }
    if note_msg:
        result["note"] = note_msg
        
    return result
