"""
Engineering Design Parameter Definitions
Each component type has its own parameter set with proper engineering requirements.
References: Engineers Edge, Shigley's, ISO/ASME standards.

Now includes:
  - Assumptions system (smart defaults with user review/approve)
  - Shaft: keyway count, shock factors
  - Gearbox: motor specs, decimal ratio, multi-stage, size constraints
  - User-friendly material names
"""

from typing import Dict, List, Optional, Any
import re

# ── Material Property Database ────────────────────────────────────────────────
MATERIAL_DB: Dict[str, Dict[str, Any]] = {
    "steel_en8": {
        "name": "EN8 (080M40)", "common_name": "EN8 Medium Carbon Steel",
        "grade": "Medium Carbon Steel",
        "use_case": "General purpose shafts, gears, axles",
        "yield_mpa": 465, "ultimate_mpa": 700, "shear_mpa": 280,
        "endurance_mpa": 280, "elastic_modulus_gpa": 200,
        "density_kg_m3": 7850, "hardness_bhn": 201,
    },
    "steel_1045": {
        "name": "AISI 1045", "common_name": "Medium Carbon Steel (1045)",
        "grade": "Medium Carbon Steel",
        "use_case": "Shafts, gears, bolts — widely available",
        "yield_mpa": 310, "ultimate_mpa": 565, "shear_mpa": 200,
        "endurance_mpa": 225, "elastic_modulus_gpa": 205,
        "density_kg_m3": 7870, "hardness_bhn": 163,
    },
    "steel_4140": {
        "name": "AISI 4140", "common_name": "Chrome-Moly Alloy Steel (4140)",
        "grade": "Alloy Steel (Cr-Mo)",
        "use_case": "High-strength shafts, gears, spindles",
        "yield_mpa": 655, "ultimate_mpa": 850, "shear_mpa": 425,
        "endurance_mpa": 340, "elastic_modulus_gpa": 210,
        "density_kg_m3": 7850, "hardness_bhn": 248,
    },
    "steel_4340": {
        "name": "AISI 4340", "common_name": "Nickel-Chrome-Moly Steel (4340)",
        "grade": "Ni-Cr-Mo Alloy Steel",
        "use_case": "Heavy-duty gears, aircraft parts, high fatigue resistance",
        "yield_mpa": 470, "ultimate_mpa": 745, "shear_mpa": 305,
        "endurance_mpa": 298, "elastic_modulus_gpa": 205,
        "density_kg_m3": 7850, "hardness_bhn": 217,
    },
    "ss_304": {
        "name": "SS 304", "common_name": "Stainless Steel 304 (SS304)",
        "grade": "Austenitic Stainless Steel",
        "use_case": "Corrosion-resistant parts, food/pharma equipment",
        "yield_mpa": 215, "ultimate_mpa": 505, "shear_mpa": 140,
        "endurance_mpa": 190, "elastic_modulus_gpa": 193,
        "density_kg_m3": 8000, "hardness_bhn": 123,
    },
    "ci_grade_25": {
        "name": "Cast Iron Grade 25", "common_name": "Grey Cast Iron (Grade 25)",
        "grade": "Grey Cast Iron",
        "use_case": "Housings, casings, machine beds",
        "yield_mpa": 170, "ultimate_mpa": 250, "shear_mpa": 100,
        "endurance_mpa": 100, "elastic_modulus_gpa": 100,
        "density_kg_m3": 7200, "hardness_bhn": 195,
    },
}


def get_material(material_id: str) -> Dict[str, Any]:
    return MATERIAL_DB.get(material_id, MATERIAL_DB["steel_1045"])


def _material_options() -> List[Dict[str, str]]:
    """Build user-friendly material options with common names."""
    return [
        {
            "value": k,
            "label": f"{v['common_name']} — σy={v['yield_mpa']} MPa ({v['use_case']})",
        }
        for k, v in MATERIAL_DB.items()
    ]


# ── Gear Ratio Parser ─────────────────────────────────────────────────────────
def parse_gear_ratio(value: str) -> Optional[float]:
    """
    Parse gear ratio from various formats:
      '3' → 3.0
      '1.3' → 1.3
      '2.75' → 2.75
      '1:3' → 3.0
      '1:1.3' → 1.3
      '2:75' → 37.5
    Returns None if unparseable.
    """
    s = str(value).strip()
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2:
            try:
                a, b = float(parts[0]), float(parts[1])
                if a > 0:
                    return round(b / a, 4)
            except ValueError:
                return None
    try:
        return float(s)
    except ValueError:
        return None


# ── Parameter Definitions Per Component Type ──────────────────────────────────

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
    {"key": "material_id", "label": "Material Grade", "unit": "",
     "type": "select", "required": True,
     "options": _material_options(),
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
     "options": [
         {"value": "0.3", "label": "0.3 (Thick-walled)"},
         {"value": "0.5", "label": "0.5 (Standard hollow)"},
         {"value": "0.7", "label": "0.7 (Thin-walled)"},
     ],
     "condition": {"key": "shaft_type", "equals": "hollow"}},
    {"key": "keyway", "label": "Keyway Present", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "yes", "label": "Yes — Keyway (stress concentration Kt ≈ 1.6)"},
         {"value": "no", "label": "No Keyway"},
     ],
     "question": "Does the shaft have a keyway?"},
    {"key": "num_keyways", "label": "Number of Keyways", "unit": "",
     "type": "number", "min": 1, "max": 3, "required": True,
     "question": "How many keyways throughout the shaft? (maximum 3)",
     "options": [
         {"value": "1", "label": "1 keyway"},
         {"value": "2", "label": "2 keyways (180°)"},
         {"value": "3", "label": "3 keyways (120°)"},
     ],
     "condition": {"key": "keyway", "equals": "yes"}},
    {"key": "fos", "label": "Factor of Safety", "unit": "",
     "type": "number", "min": 1.5, "max": 10, "required": True,
     "question": "Enter the Factor of Safety (min 1.5):",
     "options": [
         {"value": "1.5", "label": "1.5 (Steady Load)"},
         {"value": "2.0", "label": "2.0 (Moderate Shock)"},
         {"value": "2.5", "label": "2.5 (Heavy Shock)"},
         {"value": "3.0", "label": "3.0 (Extreme Load)"},
     ]},
]

GEARBOX_PARAMS: List[Dict[str, Any]] = [
    # Motor specifications
    {"key": "power_kw", "label": "Motor Power", "unit": "kW",
     "type": "number", "min": 0.1, "max": 5000, "required": True,
     "question": "What is the motor/input power in kW?"},
    {"key": "input_speed_rpm", "label": "Input/Motor Speed", "unit": "RPM",
     "type": "number", "min": 1, "max": 100000, "required": True,
     "question": "What is the input (motor) speed in RPM?"},
    {"key": "motor_phase", "label": "Motor Phase", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "single_phase", "label": "Single Phase"},
         {"value": "three_phase", "label": "3-Phase"},
     ],
     "question": "Is the motor single phase or 3-phase?"},
    {"key": "motor_poles", "label": "Number of Poles", "unit": "",
     "type": "select", "required": False,
     "options": [
         {"value": "2", "label": "2 Poles (~3000 RPM sync)"},
         {"value": "4", "label": "4 Poles (~1500 RPM sync)"},
         {"value": "6", "label": "6 Poles (~1000 RPM sync)"},
         {"value": "8", "label": "8 Poles (~750 RPM sync)"},
         {"value": "na", "label": "Not Applicable / Unknown"},
     ],
     "question": "How many poles does the motor have? (select N/A if unknown)"},
    {"key": "motor_config", "label": "Motor Configuration", "unit": "",
     "type": "select", "required": False,
     "options": [
         {"value": "star", "label": "Star (Y) Connection"},
         {"value": "delta", "label": "Delta (Δ) Connection"},
         {"value": "na", "label": "Not Applicable / Unknown"},
     ],
     "question": "What is the motor's electrical configuration?",
     "condition": {"key": "motor_phase", "equals": "three_phase"}},
    {"key": "output_speed_rpm", "label": "Desired Output Speed", "unit": "RPM",
     "type": "number", "min": 0.1, "max": 100000, "required": True,
     "question": "What output speed do you need in RPM?"},
    {"key": "gear_ratio", "label": "Gear Ratio", "unit": "",
     "type": "text", "required": True,
     "question": "Enter gear ratio (e.g. 3, 1.3, 1:3, 1:1.3, 2:75). Leave blank to auto-calculate from speeds.",
     "allow_empty": True},
    {"key": "multi_stage", "label": "Multi-Stage Gearbox", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "no", "label": "Single Stage Gearbox"},
         {"value": "yes", "label": "Multi-Stage Gearbox"},
     ],
     "question": "Do you need a single stage or multi-stage gearbox?"},
    {"key": "num_stages", "label": "Number of Stages", "unit": "",
     "type": "number", "min": 2, "max": 5, "required": True,
     "question": "How many stages? (2–5)",
     "condition": {"key": "multi_stage", "equals": "yes"}},
    {"key": "gear_type", "label": "Gear Type", "unit": "",
     "type": "select", "required": True,
     "options": [
         {"value": "spur", "label": "Spur Gear (straight teeth)"},
         {"value": "helical", "label": "Helical Gear (angled teeth, smoother)"},
     ],
     "question": "What type of gear?"},
    {"key": "material_id", "label": "Gear Material", "unit": "",
     "type": "select", "required": True,
     "options": _material_options(),
     "question": "Select the gear material:"},
    {"key": "size_max_width_mm", "label": "Max Gearbox Width", "unit": "mm",
     "type": "number", "min": 10, "max": 10000, "required": False,
     "question": "Any width constraint for the gearbox? (mm, or 0 for no constraint)",
     "allow_zero": True},
    {"key": "size_max_height_mm", "label": "Max Gearbox Height", "unit": "mm",
     "type": "number", "min": 10, "max": 10000, "required": False,
     "question": "Any height constraint for the gearbox? (mm, or 0 for no constraint)",
     "allow_zero": True},
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


# ── Assumptions (Smart Defaults) Per Component ────────────────────────────────
# These are shown AFTER required params are collected.
# User can edit or approve each one with a tick mark.

SHAFT_ASSUMPTIONS: List[Dict[str, Any]] = [
    {
        "key": "bending_moment_nm",
        "label": "Bending Moment",
        "unit": "N·m",
        "default_value": 0,
        "explanation": "Industry standard default is 0 N·m for pure torsion. Set a value if combined bending loads are present.",
        "type": "number", "min": 0, "max": 500000,
    },
    {
        "key": "kb_shock",
        "label": "Bending Shock Factor (Kb)",
        "unit": "",
        "default_value": 0,
        "explanation": "ASME B106.1M factor. 0 = no shock (system auto-selects based on loading type: 1.0 steady, 1.5 moderate, 2.0 heavy).",
        "type": "number", "min": 0, "max": 3.0,
    },
    {
        "key": "kt_shock",
        "label": "Torsion Shock Factor (Kt)",
        "unit": "",
        "default_value": 0,
        "explanation": "ASME B106.1M factor. 0 = no shock (system auto-selects based on loading type: 1.0 steady, 1.0 moderate, 1.5 heavy).",
        "type": "number", "min": 0, "max": 3.0,
    },
]

GEARBOX_ASSUMPTIONS: List[Dict[str, Any]] = [
    {
        "key": "pressure_angle",
        "label": "Pressure Angle",
        "unit": "°",
        "default_value": 20,
        "explanation": "20° is the most common industry standard. 14.5° for legacy, 25° for high load.",
        "type": "select",
        "options": [
            {"value": "20", "label": "20° (Standard — most common)"},
            {"value": "14.5", "label": "14.5° (Legacy systems)"},
            {"value": "25", "label": "25° (High load capacity)"},
        ],
    },
    {
        "key": "quality_grade",
        "label": "AGMA Quality Grade",
        "unit": "",
        "default_value": "8",
        "explanation": "Grade 8 (Precision) is standard for industrial gearboxes. Grade 6 for commercial, Grade 10 for high precision.",
        "type": "select",
        "options": [
            {"value": "6", "label": "Grade 6 — Commercial"},
            {"value": "8", "label": "Grade 8 — Precision (recommended)"},
            {"value": "10", "label": "Grade 10 — High Precision"},
        ],
    },
    {
        "key": "efficiency_per_stage",
        "label": "Efficiency per Stage",
        "unit": "%",
        "default_value": 97,
        "explanation": "97% is standard for well-lubricated spur/helical gear stages. Lower for worm gears.",
        "type": "number", "min": 80, "max": 99.9,
    },
    {
        "key": "face_width_ratio",
        "label": "Face Width / Module Ratio",
        "unit": "",
        "default_value": 10,
        "explanation": "Face width = ratio × module. 8–12 is standard range. Higher for heavy loads.",
        "type": "number", "min": 6, "max": 20,
    },
]

BEARING_ASSUMPTIONS: List[Dict[str, Any]] = []
CAM_ASSUMPTIONS: List[Dict[str, Any]] = []


# ── Registry ──────────────────────────────────────────────────────────────────
COMPONENT_PARAMS: Dict[str, List[Dict[str, Any]]] = {
    "shaft": SHAFT_PARAMS,
    "bearing": BEARING_PARAMS,
    "gearbox": GEARBOX_PARAMS,
    "cam": CAM_PARAMS,
    "custom": [],
}

COMPONENT_ASSUMPTIONS: Dict[str, List[Dict[str, Any]]] = {
    "shaft": SHAFT_ASSUMPTIONS,
    "bearing": BEARING_ASSUMPTIONS,
    "gearbox": GEARBOX_ASSUMPTIONS,
    "cam": CAM_ASSUMPTIONS,
    "custom": [],
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


def get_assumptions_for_component(component_type: str) -> List[Dict[str, Any]]:
    """Get assumptions with smart defaults for a component type."""
    return COMPONENT_ASSUMPTIONS.get(component_type, [])


def compute_smart_defaults(component_type: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compute context-aware default values for assumptions based on
    the user's already-collected parameters. Returns assumptions
    with populated default_value fields.
    """
    assumptions = get_assumptions_for_component(component_type)
    if not assumptions:
        return []

    result = []
    for a in assumptions:
        entry = dict(a)  # copy

        if component_type == "shaft":
            loading = params.get("loading_type", "pure_torsion")
            if a["key"] == "bending_moment_nm":
                if loading == "pure_torsion":
                    entry["default_value"] = 0
                    entry["explanation"] = "Pure torsion selected — bending moment is 0 by default."
                else:
                    entry["default_value"] = 0
                    entry["explanation"] = (
                        "Combined loading selected — bending moment defaults to 0. "
                        "Enter the actual bending moment if known for accurate design."
                    )
            elif a["key"] == "kb_shock":
                shock_map = {"pure_torsion": 0, "combined_bending_torsion": 0, "fluctuating": 0}
                entry["default_value"] = shock_map.get(loading, 0)
                entry["explanation"] = (
                    f"Default: 0 (auto). System will use ASME values based on '{loading}' loading. "
                    "Override: 1.0=steady, 1.5=light shock, 2.0=heavy shock."
                )
            elif a["key"] == "kt_shock":
                shock_map = {"pure_torsion": 0, "combined_bending_torsion": 0, "fluctuating": 0}
                entry["default_value"] = shock_map.get(loading, 0)
                entry["explanation"] = (
                    f"Default: 0 (auto). System will use ASME values based on '{loading}' loading. "
                    "Override: 1.0=steady, 1.0=moderate, 1.5=heavy shock."
                )

        elif component_type == "gearbox":
            # Defaults are already set in GEARBOX_ASSUMPTIONS
            pass

        result.append(entry)

    return result


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
        # Skip optional params that allow empty
        if p.get("allow_empty") and not p.get("required"):
            continue
        if p.get("required", False):
            return p
    return None


def validate_param(param_def: Dict[str, Any], value: Any) -> Optional[str]:
    """Validate a single parameter value. Returns error message or None."""
    if param_def["type"] == "number":
        cleaned_val = value
        if isinstance(value, str):
            match = re.search(r"[-+]?\d*\.?\d+", value)
            if match:
                cleaned_val = match.group(0)
        try:
            v = float(cleaned_val)
        except (ValueError, TypeError):
            return f"{param_def['label']} must be a number."
        if "min" in param_def and v < param_def["min"]:
            if not (param_def.get("allow_zero") and v == 0):
                return f"{param_def['label']} must be ≥ {param_def['min']}."
        if "max" in param_def and v > param_def["max"]:
            return f"{param_def['label']} must be ≤ {param_def['max']}."
    elif param_def["type"] == "select":
        valid_values = [o["value"] for o in param_def.get("options", [])]
        if str(value) not in valid_values:
            return f"Invalid selection for {param_def['label']}."
    elif param_def["type"] == "text":
        # Text fields — custom validation per key
        if param_def["key"] == "gear_ratio":
            s = str(value).strip()
            if s and s != "auto":
                parsed = parse_gear_ratio(s)
                if parsed is None:
                    return "Invalid gear ratio format. Use: 3, 1.3, 1:3, 1:1.3, or 2:75"
                if parsed < 0.1 or parsed > 200:
                    return "Gear ratio must be between 0.1 and 200."
    return None


def are_all_params_collected(component_type: str, collected: Dict[str, Any]) -> bool:
    """Check if all required parameters are collected."""
    return get_next_missing_param(component_type, collected) is None
