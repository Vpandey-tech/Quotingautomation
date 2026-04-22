"""
Engineering Design Parameter Definitions
Each component type has its own parameter set with proper engineering requirements.
References: Engineers Edge, Shigley's, ISO/ASME standards.
"""

from typing import Dict, List, Optional, Any

# ── Material Property Database ────────────────────────────────────────────────
MATERIAL_DB: Dict[str, Dict[str, Any]] = {
    "steel_en8": {
        "name": "EN8 (080M40)", "grade": "Medium Carbon Steel",
        "yield_mpa": 465, "ultimate_mpa": 700, "shear_mpa": 280,
        "endurance_mpa": 280, "elastic_modulus_gpa": 200,
        "density_kg_m3": 7850, "hardness_bhn": 201,
    },
    "steel_1045": {
        "name": "AISI 1045", "grade": "Medium Carbon Steel",
        "yield_mpa": 310, "ultimate_mpa": 565, "shear_mpa": 200,
        "endurance_mpa": 225, "elastic_modulus_gpa": 205,
        "density_kg_m3": 7870, "hardness_bhn": 163,
    },
    "steel_4140": {
        "name": "AISI 4140", "grade": "Alloy Steel (Cr-Mo)",
        "yield_mpa": 655, "ultimate_mpa": 850, "shear_mpa": 425,
        "endurance_mpa": 340, "elastic_modulus_gpa": 210,
        "density_kg_m3": 7850, "hardness_bhn": 248,
    },
    "steel_4340": {
        "name": "AISI 4340", "grade": "Ni-Cr-Mo Alloy Steel",
        "yield_mpa": 470, "ultimate_mpa": 745, "shear_mpa": 305,
        "endurance_mpa": 298, "elastic_modulus_gpa": 205,
        "density_kg_m3": 7850, "hardness_bhn": 217,
    },
    "ss_304": {
        "name": "SS 304", "grade": "Austenitic Stainless Steel",
        "yield_mpa": 215, "ultimate_mpa": 505, "shear_mpa": 140,
        "endurance_mpa": 190, "elastic_modulus_gpa": 193,
        "density_kg_m3": 8000, "hardness_bhn": 123,
    },
    "ci_grade_25": {
        "name": "Cast Iron Grade 25", "grade": "Grey Cast Iron",
        "yield_mpa": 170, "ultimate_mpa": 250, "shear_mpa": 100,
        "endurance_mpa": 100, "elastic_modulus_gpa": 100,
        "density_kg_m3": 7200, "hardness_bhn": 195,
    },
}


def get_material(material_id: str) -> Dict[str, Any]:
    return MATERIAL_DB.get(material_id, MATERIAL_DB["steel_1045"])


# ── Parameter Definitions Per Component Type ──────────────────────────────────
# Each param: key, label, unit, type(number|select), options/range, required

SHAFT_PARAMS: List[Dict[str, Any]] = [
    {"key": "power_kw", "label": "Transmitted Power", "unit": "kW",
     "type": "number", "min": 0.1, "max": 5000, "required": True,
     "question": "What is the transmitted power in kW?"},
    {"key": "speed_rpm", "label": "Operating Speed", "unit": "RPM",
     "type": "number", "min": 1, "max": 100000, "required": True,
     "question": "What is the operating speed in RPM?"},
    {"key": "loading_type", "label": "Loading Type", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "pure_torsion", "label": "Pure Torsion"},
         {"value": "combined_bending_torsion", "label": "Combined Bending + Torsion"},
         {"value": "fluctuating", "label": "Fluctuating / Fatigue Loading"},
     ],
     "question": "What type of loading does the shaft experience?"},
    {"key": "bending_moment_nm", "label": "Bending Moment", "unit": "N·m",
     "type": "number", "min": 0, "max": 500000, "required": False,
     "question": "Enter bending moment in N·m (0 if pure torsion):",
     "condition": {"key": "loading_type", "not_equals": "pure_torsion"}},
    {"key": "material_id", "label": "Material Grade", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": k, "label": f"{v['name']} — σy={v['yield_mpa']} MPa"}
         for k, v in MATERIAL_DB.items()
     ],
     "question": "Select the shaft material grade:"},
    {"key": "shaft_type", "label": "Shaft Type", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "solid", "label": "Solid Shaft"},
         {"value": "hollow", "label": "Hollow Shaft"},
     ],
     "question": "Is this a solid or hollow shaft?"},
    {"key": "inner_diameter_ratio", "label": "Inner/Outer Diameter Ratio (K)",
     "unit": "", "type": "number", "min": 0.1, "max": 0.9, "required": False,
     "question": "Enter the inner-to-outer diameter ratio K (e.g. 0.5):",
     "condition": {"key": "shaft_type", "equals": "hollow"}},
    {"key": "keyway", "label": "Keyway Present", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "yes", "label": "Yes — Keyway (stress concentration Kt ≈ 1.6)"},
         {"value": "no", "label": "No Keyway"},
     ],
     "question": "Does the shaft have a keyway?"},
    {"key": "fos", "label": "Factor of Safety", "unit": "",
     "type": "number", "min": 1.5, "max": 10, "required": True,
     "question": "Enter the Factor of Safety (min 1.5):"},
]

BEARING_PARAMS: List[Dict[str, Any]] = [
    {"key": "radial_load_n", "label": "Radial Load", "unit": "N",
     "type": "number", "min": 1, "max": 5000000, "required": True,
     "question": "What is the radial load on the bearing in N?"},
    {"key": "axial_load_n", "label": "Axial (Thrust) Load", "unit": "N",
     "type": "number", "min": 0, "max": 5000000, "required": True,
     "question": "What is the axial (thrust) load in N? (0 if none)"},
    {"key": "speed_rpm", "label": "Shaft Speed", "unit": "RPM",
     "type": "number", "min": 1, "max": 100000, "required": True,
     "question": "What is the shaft speed in RPM?"},
    {"key": "desired_life_hours", "label": "Desired Life (L10h)", "unit": "hours",
     "type": "number", "min": 500, "max": 200000, "required": True,
     "question": "Desired bearing life in hours? (e.g. 20000 for general machinery)"},
    {"key": "bearing_type", "label": "Bearing Type", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "deep_groove_ball", "label": "Deep Groove Ball Bearing (p=3)"},
         {"value": "cylindrical_roller", "label": "Cylindrical Roller Bearing (p=10/3)"},
         {"value": "taper_roller", "label": "Taper Roller Bearing (p=10/3)"},
         {"value": "angular_contact_ball", "label": "Angular Contact Ball (p=3)"},
     ],
     "question": "Select the bearing type:"},
    {"key": "reliability", "label": "Reliability Factor", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "90", "label": "90% (a1 = 1.00) — Standard"},
         {"value": "95", "label": "95% (a1 = 0.62)"},
         {"value": "99", "label": "99% (a1 = 0.21) — Critical"},
     ],
     "question": "Required reliability level?"},
    {"key": "fos", "label": "Static Safety Factor (S0)", "unit": "",
     "type": "number", "min": 1.0, "max": 10, "required": True,
     "question": "Static safety factor S0? (1.5 general, 3.0 shock loads)"},
]

GEARBOX_PARAMS: List[Dict[str, Any]] = [
    {"key": "power_kw", "label": "Transmitted Power", "unit": "kW",
     "type": "number", "min": 0.1, "max": 5000, "required": True,
     "question": "What is the transmitted power in kW?"},
    {"key": "input_speed_rpm", "label": "Input Shaft Speed", "unit": "RPM",
     "type": "number", "min": 1, "max": 100000, "required": True,
     "question": "What is the input (pinion) shaft speed in RPM?"},
    {"key": "gear_ratio", "label": "Gear Ratio (i)", "unit": "",
     "type": "number", "min": 1.0, "max": 50, "required": True,
     "question": "What is the desired gear ratio?"},
    {"key": "gear_type", "label": "Gear Type", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "spur", "label": "Spur Gear (straight teeth)"},
         {"value": "helical", "label": "Helical Gear (angled teeth)"},
     ],
     "question": "What type of gear?"},
    {"key": "pressure_angle", "label": "Pressure Angle", "unit": "°",
     "type": "select", "required": True,
     "options": [
         {"value": "20", "label": "20° (Standard — most common)"},
         {"value": "14.5", "label": "14.5° (Legacy systems)"},
         {"value": "25", "label": "25° (High load capacity)"},
     ],
     "question": "Select the pressure angle:"},
    {"key": "material_id", "label": "Gear Material", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": k, "label": f"{v['name']} — σy={v['yield_mpa']} MPa"}
         for k, v in MATERIAL_DB.items()
     ],
     "question": "Select the gear material:"},
    {"key": "quality_grade", "label": "AGMA Quality Grade", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "6", "label": "Grade 6 — Commercial"},
         {"value": "8", "label": "Grade 8 — Precision"},
         {"value": "10", "label": "Grade 10 — High Precision"},
     ],
     "question": "Select AGMA quality grade:"},
    {"key": "fos", "label": "Factor of Safety", "unit": "",
     "type": "number", "min": 1.5, "max": 10, "required": True,
     "question": "Enter the Factor of Safety (min 1.5):"},
]

CAM_PARAMS: List[Dict[str, Any]] = [
    {"key": "cam_speed_rpm", "label": "Cam Speed", "unit": "RPM",
     "type": "number", "min": 1, "max": 10000, "required": True,
     "question": "What is the cam rotational speed in RPM?"},
    {"key": "follower_lift_mm", "label": "Maximum Follower Lift", "unit": "mm",
     "type": "number", "min": 1, "max": 500, "required": True,
     "question": "What is the maximum follower lift (stroke) in mm?"},
    {"key": "profile_type", "label": "Cam Profile Motion", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "shm", "label": "Simple Harmonic Motion (SHM)"},
         {"value": "cycloidal", "label": "Cycloidal (smooth — no jerk at endpoints)"},
         {"value": "parabolic", "label": "Parabolic (constant acceleration)"},
     ],
     "question": "Select the cam motion profile:"},
    {"key": "follower_type", "label": "Follower Type", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "flat_face", "label": "Flat-Face Follower"},
         {"value": "roller", "label": "Roller Follower"},
         {"value": "knife_edge", "label": "Knife-Edge Follower"},
     ],
     "question": "Select the follower type:"},
    {"key": "base_circle_radius_mm", "label": "Base Circle Radius", "unit": "mm",
     "type": "number", "min": 10, "max": 500, "required": True,
     "question": "Enter the base circle radius in mm:"},
    {"key": "rise_angle_deg", "label": "Rise Angle", "unit": "°",
     "type": "number", "min": 30, "max": 180, "required": True,
     "question": "Rise angle in degrees? (e.g. 120°)"},
    {"key": "dwell_angle_deg", "label": "Dwell Angle (at top)", "unit": "°",
     "type": "number", "min": 0, "max": 180, "required": True,
     "question": "Dwell angle at top in degrees? (e.g. 60°)"},
    {"key": "fos", "label": "Factor of Safety", "unit": "",
     "type": "number", "min": 1.5, "max": 10, "required": True,
     "question": "Enter the Factor of Safety (min 1.5):"},
]


# ── Registry ──────────────────────────────────────────────────────────────────
COMPONENT_PARAMS: Dict[str, List[Dict[str, Any]]] = {
    "shaft": SHAFT_PARAMS,
    "bearing": BEARING_PARAMS,
    "gearbox": GEARBOX_PARAMS,
    "cam": CAM_PARAMS,
    "custom": [],  # Custom parts use free-form iterative intake
}

COMPONENT_LABELS: Dict[str, str] = {
    "shaft": "Shaft Design",
    "bearing": "Bearing Selection",
    "gearbox": "Gearbox Design",
    "cam": "CAM Design",
    "custom": "Custom Part Design",
}


def get_params_for_component(component_type: str) -> List[Dict[str, Any]]:
    """Get the full parameter definition list for a component type."""
    return COMPONENT_PARAMS.get(component_type, [])


def get_required_params(component_type: str) -> List[str]:
    """Get list of required parameter keys for a component type."""
    params = get_params_for_component(component_type)
    return [p["key"] for p in params if p.get("required", False)]


def get_next_missing_param(component_type: str, collected: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Given collected values, find the next param to ask for."""
    params = get_params_for_component(component_type)
    for p in params:
        key = p["key"]
        # Skip if already collected
        if key in collected and collected[key] is not None:
            continue
        # Check conditional visibility
        cond = p.get("condition")
        if cond:
            dep_key = cond["key"]
            dep_val = collected.get(dep_key)
            if "equals" in cond and dep_val != cond["equals"]:
                continue
            if "not_equals" in cond and dep_val == cond["not_equals"]:
                continue
        if p.get("required", False):
            return p
    return None


def validate_param(param_def: Dict[str, Any], value: Any) -> Optional[str]:
    """Validate a single parameter value. Returns error message or None."""
    if param_def["type"] == "number":
        try:
            v = float(value)
        except (ValueError, TypeError):
            return f"{param_def['label']} must be a number."
        if "min" in param_def and v < param_def["min"]:
            return f"{param_def['label']} must be ≥ {param_def['min']}."
        if "max" in param_def and v > param_def["max"]:
            return f"{param_def['label']} must be ≤ {param_def['max']}."
    elif param_def["type"] == "select":
        valid_values = [o["value"] for o in param_def.get("options", [])]
        if str(value) not in valid_values:
            return f"Invalid selection for {param_def['label']}."
    return None


def are_all_params_collected(component_type: str, collected: Dict[str, Any]) -> bool:
    """Check if all required parameters are collected."""
    return get_next_missing_param(component_type, collected) is None
