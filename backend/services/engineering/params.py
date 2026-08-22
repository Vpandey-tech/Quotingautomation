"""
Engineering Design Parameter Definitions & Canonical Structured Schemas
References: Engineers Edge, Shigley's, ISO/ASME standards, earthtojake text-to-cad conventions.

Conventions (Codified Defaults):
  - Units: mm
  - Origin: center-of-part-or-assembly unless mating interface specifies otherwise
  - Base Plane: XY
  - Up Axis: +Z
  - Output Format: AP242 / AP214 closed watertight manifold solids
"""

from typing import Dict, List, Optional, Any, Union
import re
from pydantic import BaseModel, Field

# ── STEP-First & CAD Canonical Defaults ───────────────────────────────────────
DEFAULT_UNITS: str = "mm"
DEFAULT_ORIGIN: str = "center"
DEFAULT_BASE_PLANE: str = "XY"
DEFAULT_UP_AXIS: str = "+Z"
DEFAULT_STEP_FORMAT: str = "AP242"

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
    "aluminum_6061": {
        "name": "Aluminum 6061-T6", "common_name": "6061-T6 Aluminum",
        "grade": "Structural Aluminum",
        "use_case": "Lightweight brackets, plates, structural frames",
        "yield_mpa": 276, "ultimate_mpa": 310, "shear_mpa": 207,
        "endurance_mpa": 96, "elastic_modulus_gpa": 68.9,
        "density_kg_m3": 2700, "hardness_bhn": 95,
    }
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


# ── Pydantic Canonical Spec Schemas for Deterministic CAD Builders ─────────────

class BaseSpec(BaseModel):
    material_id: Optional[str] = Field(default="steel_1045", description="Material grade identifier")
    quantity: Optional[int] = Field(default=1, ge=1, description="Production quantity")
    tolerance_class: Optional[str] = Field(default="ISO 2768-m", description="Dimensional tolerance class")
    fos: Optional[float] = Field(default=2.0, ge=1.0, le=10.0, description="Factor of Safety")


class ShaftSpec(BaseSpec):
    power_kw: Optional[float] = Field(default=None, description="Transmitted power in kW")
    speed_rpm: Optional[float] = Field(default=None, description="Operating speed in RPM")
    loading_type: Optional[str] = Field(default="pure_torsion", description="Loading type (pure_torsion, combined_bending_torsion, fluctuating)")
    shaft_type: Optional[str] = Field(default="solid", description="solid or hollow")
    inner_diameter_ratio: Optional[float] = Field(default=0.0, description="Inner/outer diameter ratio for hollow shaft")
    keyway: Optional[str] = Field(default="no", description="yes or no")
    num_keyways: Optional[int] = Field(default=0, description="Number of keyways (0-3)")
    length_mm: Optional[float] = Field(default=300.0, description="Total shaft length in mm")
    diameter_mm: Optional[float] = Field(default=None, description="Shaft diameter in mm (if pre-specified)")


class FlangeSpec(BaseSpec):
    outer_diameter_mm: Optional[float] = Field(default=None, description="Outer diameter in mm")
    inner_bore_diameter_mm: Optional[float] = Field(default=0.0, description="Center bore diameter in mm")
    thickness_mm: Optional[float] = Field(default=None, description="Flange thickness in mm")
    bolt_circle_diameter_mm: Optional[float] = Field(default=None, description="Bolt Circle Diameter (PCD) in mm")
    num_bolts: Optional[int] = Field(default=None, description="Number of bolt holes")
    bolt_size: Optional[str] = Field(default="M8", description="Bolt size e.g. M6, M8, M10, M12")
    face_type: Optional[str] = Field(default="flat_face", description="flat_face or raised_face")


class PlateHolePatternSpec(BaseSpec):
    length_mm: Optional[float] = Field(default=None, description="Plate length in mm")
    width_mm: Optional[float] = Field(default=None, description="Plate width in mm")
    thickness_mm: Optional[float] = Field(default=None, description="Plate thickness in mm")
    hole_layout: Optional[str] = Field(default="rectangular", description="rectangular or circular")
    hole_diameter_mm: Optional[float] = Field(default=None, description="Hole diameter in mm")
    hole_count: Optional[int] = Field(default=None, description="Total number of holes")


class BracketSpec(BaseSpec):
    bracket_type: Optional[str] = Field(default="l_shape", description="l_shape, flat_plate, or u_shape")
    wall_thickness_mm: Optional[float] = Field(default=None, description="Wall thickness in mm")
    length_mm: Optional[float] = Field(default=100.0, description="Base length in mm")
    width_mm: Optional[float] = Field(default=50.0, description="Width in mm")
    height_mm: Optional[float] = Field(default=60.0, description="Height/leg length in mm")
    hole_count: Optional[int] = Field(default=2, description="Mounting hole count")
    hole_diameter_mm: Optional[float] = Field(default=6.5, description="Mounting hole diameter in mm")
    gusset_needed: Optional[str] = Field(default="no", description="yes or no for reinforcement rib")


class SpacerSpec(BaseSpec):
    outer_diameter_mm: Optional[float] = Field(default=None, description="Outer diameter in mm")
    inner_bore_diameter_mm: Optional[float] = Field(default=None, description="Inner bore diameter in mm")
    length_mm: Optional[float] = Field(default=None, description="Length/height in mm")


class LeverSpec(BaseSpec):
    length_mm: Optional[float] = Field(default=None, description="Lever arm length in mm")
    thickness_mm: Optional[float] = Field(default=None, description="Lever thickness in mm")
    width_mm: Optional[float] = Field(default=None, description="Lever section width in mm")
    pivot_bore_diameter_mm: Optional[float] = Field(default=None, description="Pivot bore diameter in mm")
    load_end_bore_diameter_mm: Optional[float] = Field(default=None, description="End connection bore diameter in mm")


class EnclosureSpec(BaseSpec):
    outer_length_mm: Optional[float] = Field(default=None, description="Outer length in mm")
    outer_width_mm: Optional[float] = Field(default=None, description="Outer width in mm")
    outer_height_mm: Optional[float] = Field(default=None, description="Outer height in mm")
    wall_thickness_mm: Optional[float] = Field(default=None, description="Wall thickness in mm")
    is_hollow: Optional[str] = Field(default="yes", description="yes or no")


class BearingSpec(BaseSpec):
    radial_load_n: Optional[float] = Field(default=None, description="Radial load in N")
    axial_load_n: Optional[float] = Field(default=0.0, description="Axial/thrust load in N")
    speed_rpm: Optional[float] = Field(default=None, description="Shaft speed in RPM")
    desired_life_hours: Optional[float] = Field(default=20000.0, description="L10 life in hours")
    bearing_type: Optional[str] = Field(default="deep_groove_ball", description="Bearing type")
    reliability: Optional[str] = Field(default="90", description="90, 95, or 99")


class GearboxSpec(BaseSpec):
    power_kw: Optional[float] = Field(default=None, description="Motor power in kW")
    input_speed_rpm: Optional[float] = Field(default=None, description="Input speed in RPM")
    output_speed_rpm: Optional[float] = Field(default=None, description="Desired output speed in RPM")
    gear_ratio: Optional[str] = Field(default="auto", description="Gear ratio e.g. 3, 1:3, 2.5")
    multi_stage: Optional[str] = Field(default="no", description="yes or no")
    gear_type: Optional[str] = Field(default="spur", description="spur or helical")


class CustomSpec(BaseSpec):
    length_mm: Optional[float] = Field(default=100.0, description="Envelope length in mm")
    width_mm: Optional[float] = Field(default=50.0, description="Envelope width in mm")
    height_mm: Optional[float] = Field(default=25.0, description="Envelope height/thickness in mm")
    overall_shape: Optional[str] = Field(default="rectangular", description="cylindrical, rectangular, L-bracket, or other")
    has_holes: Optional[str] = Field(default="no", description="yes or no")
    has_slots: Optional[str] = Field(default="no", description="yes or no")
    has_chamfers: Optional[str] = Field(default="no", description="yes or no")


# ── Structured Clarification Question Model ───────────────────────────────────

class ClarificationQuestion(BaseModel):
    field: str = Field(description="Spec parameter key name")
    label: str = Field(description="Human readable label")
    question: str = Field(description="Natural language question for user")
    type: str = Field(default="number", description="number, select, or text")
    unit: Optional[str] = Field(default="", description="Unit of measurement (mm, kW, RPM, etc.)")
    options: Optional[List[Dict[str, str]]] = Field(default=None, description="Selectable option chips if applicable")
    default_value: Optional[Any] = Field(default=None, description="Recommended default value")


class IntakeResult(BaseModel):
    component_family: str = Field(
        description="One of: shaft, flange, plate_hole_pattern, bracket, spacer, lever, housing, bearing, gearbox, cam, custom"
    )
    extracted_spec: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value pairs of all extracted numeric and categorical design parameters"
    )
    clarification_questions: List[ClarificationQuestion] = Field(
        default_factory=list,
        description="Batched list of missing required parameters"
    )
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in parsing")


# ── Parameter Definitions Per Component Type (Existing Standard Forms) ────────

SHAFT_PARAMS: List[Dict[str, Any]] = [
    {"key": "power_kw", "label": "Transmitted Power", "unit": "kW", "type": "number", "min": 0.1, "max": 5000, "required": True, "question": "What is the transmitted power in kW?"},
    {"key": "speed_rpm", "label": "Operating Speed", "unit": "RPM", "type": "number", "min": 1, "max": 100000, "required": True, "question": "What is the operating speed in RPM?"},
    {"key": "loading_type", "label": "Loading Type", "unit": "", "type": "select", "required": True, "options": [{"value": "pure_torsion", "label": "Pure Torsion"}, {"value": "combined_bending_torsion", "label": "Combined Bending + Torsion"}, {"value": "fluctuating", "label": "Fluctuating / Fatigue Loading"}], "question": "What type of loading does the shaft experience?"},
    {"key": "material_id", "label": "Material Grade", "unit": "", "type": "select", "required": True, "options": _material_options(), "question": "Select the shaft material grade:"},
    {"key": "shaft_type", "label": "Shaft Type", "unit": "", "type": "select", "required": True, "options": [{"value": "solid", "label": "Solid Shaft"}, {"value": "hollow", "label": "Hollow Shaft"}], "question": "Is this a solid or hollow shaft?"},
    {"key": "inner_diameter_ratio", "label": "Inner/Outer Ratio (K)", "unit": "", "type": "number", "min": 0.1, "max": 0.9, "required": False, "question": "Enter inner-to-outer ratio K (e.g. 0.5):", "options": [{"value": "0.3", "label": "0.3 (Thick-walled)"}, {"value": "0.5", "label": "0.5 (Standard hollow)"}, {"value": "0.7", "label": "0.7 (Thin-walled)"}], "condition": {"key": "shaft_type", "equals": "hollow"}},
    {"key": "keyway", "label": "Keyway Present", "unit": "", "type": "select", "required": True, "options": [{"value": "yes", "label": "Yes — Keyway"}, {"value": "no", "label": "No Keyway"}], "question": "Does the shaft have a keyway?"},
    {"key": "num_keyways", "label": "Number of Keyways", "unit": "", "type": "number", "min": 1, "max": 3, "required": True, "question": "How many keyways? (1-3)", "options": [{"value": "1", "label": "1 keyway"}, {"value": "2", "label": "2 keyways (180°)"}, {"value": "3", "label": "3 keyways (120°)"}], "condition": {"key": "keyway", "equals": "yes"}},
    {"key": "fos", "label": "Factor of Safety", "unit": "", "type": "number", "min": 1.5, "max": 10, "required": True, "question": "Enter Factor of Safety (min 1.5):", "options": [{"value": "1.5", "label": "1.5 (Steady)"}, {"value": "2.0", "label": "2.0 (Moderate Shock)"}, {"value": "2.5", "label": "2.5 (Heavy Shock)"}]},
]

GEARBOX_PARAMS: List[Dict[str, Any]] = [
    {"key": "power_kw", "label": "Motor Power", "unit": "kW", "type": "number", "min": 0.1, "max": 5000, "required": True, "question": "What is the motor/input power in kW?"},
    {"key": "input_speed_rpm", "label": "Input Speed", "unit": "RPM", "type": "number", "min": 1, "max": 100000, "required": True, "question": "What is the input (motor) speed in RPM?"},
    {"key": "motor_phase", "label": "Motor Phase", "unit": "", "type": "select", "required": True, "options": [{"value": "single_phase", "label": "Single Phase"}, {"value": "three_phase", "label": "3-Phase"}], "question": "Is the motor single phase or 3-phase?"},
    {"key": "output_speed_rpm", "label": "Desired Output Speed", "unit": "RPM", "type": "number", "min": 0.1, "max": 100000, "required": True, "question": "What output speed do you need in RPM?"},
    {"key": "gear_ratio", "label": "Gear Ratio", "unit": "", "type": "text", "required": True, "question": "Enter gear ratio (e.g. 3, 1:3). Leave blank to auto-calc.", "allow_empty": True},
    {"key": "multi_stage", "label": "Multi-Stage Gearbox", "unit": "", "type": "select", "required": True, "options": [{"value": "no", "label": "Single Stage"}, {"value": "yes", "label": "Multi-Stage"}], "question": "Single stage or multi-stage?"},
    {"key": "gear_type", "label": "Gear Type", "unit": "", "type": "select", "required": True, "options": [{"value": "spur", "label": "Spur Gear"}, {"value": "helical", "label": "Helical Gear"}], "question": "Spur or Helical gear?"},
    {"key": "material_id", "label": "Gear Material", "unit": "", "type": "select", "required": True, "options": _material_options(), "question": "Select gear material:"},
    {"key": "fos", "label": "Factor of Safety", "unit": "", "type": "number", "min": 1.5, "max": 10, "required": True, "question": "Factor of Safety (min 1.5):"},
]

BEARING_PARAMS: List[Dict[str, Any]] = [
    {"key": "radial_load_n", "label": "Radial Load", "unit": "N", "type": "number", "min": 1, "max": 5000000, "required": True, "question": "Radial load on bearing in N?"},
    {"key": "axial_load_n", "label": "Axial Load", "unit": "N", "type": "number", "min": 0, "max": 5000000, "required": True, "question": "Axial (thrust) load in N? (0 if none)"},
    {"key": "speed_rpm", "label": "Shaft Speed", "unit": "RPM", "type": "number", "min": 1, "max": 100000, "required": True, "question": "Shaft speed in RPM?"},
    {"key": "desired_life_hours", "label": "Desired Life (L10h)", "unit": "hours", "type": "number", "min": 500, "max": 200000, "required": True, "question": "Desired bearing life in hours? (e.g. 20000)"},
    {"key": "bearing_type", "label": "Bearing Type", "unit": "", "type": "select", "required": True, "options": [{"value": "deep_groove_ball", "label": "Deep Groove Ball Bearing (p=3)"}, {"value": "cylindrical_roller", "label": "Cylindrical Roller Bearing (p=10/3)"}, {"value": "taper_roller", "label": "Taper Roller Bearing (p=10/3)"}], "question": "Select bearing type:"},
    {"key": "reliability", "label": "Reliability Factor", "unit": "", "type": "select", "required": True, "options": [{"value": "90", "label": "90% (a1 = 1.00)"}, {"value": "95", "label": "95% (a1 = 0.62)"}, {"value": "99", "label": "99% (a1 = 0.21)"}], "question": "Reliability level?"},
    {"key": "fos", "label": "Static Safety Factor (S0)", "unit": "", "type": "number", "min": 1.0, "max": 10, "required": True, "question": "Static safety factor S0?"},
]

CAM_PARAMS: List[Dict[str, Any]] = [
    {"key": "cam_speed_rpm", "label": "Cam Speed", "unit": "RPM", "type": "number", "min": 1, "max": 10000, "required": True, "question": "Cam rotational speed in RPM?"},
    {"key": "follower_lift_mm", "label": "Max Follower Lift", "unit": "mm", "type": "number", "min": 1, "max": 500, "required": True, "question": "Max follower lift (stroke) in mm?"},
    {"key": "profile_type", "label": "Cam Profile Motion", "unit": "", "type": "select", "required": True, "options": [{"value": "shm", "label": "Simple Harmonic Motion (SHM)"}, {"value": "cycloidal", "label": "Cycloidal"}, {"value": "parabolic", "label": "Parabolic"}], "question": "Select cam profile:"},
    {"key": "follower_type", "label": "Follower Type", "unit": "", "type": "select", "required": True, "options": [{"value": "flat_face", "label": "Flat-Face"}, {"value": "roller", "label": "Roller"}, {"value": "knife_edge", "label": "Knife-Edge"}], "question": "Select follower type:"},
    {"key": "base_circle_radius_mm", "label": "Base Circle Radius", "unit": "mm", "type": "number", "min": 10, "max": 500, "required": True, "question": "Base circle radius in mm:"},
    {"key": "rise_angle_deg", "label": "Rise Angle", "unit": "°", "type": "number", "min": 30, "max": 180, "required": True, "question": "Rise angle in degrees? (e.g. 120°)"},
    {"key": "dwell_angle_deg", "label": "Dwell Angle", "unit": "°", "type": "number", "min": 0, "max": 180, "required": True, "question": "Dwell angle at top in degrees? (e.g. 60°)"},
    {"key": "fos", "label": "Factor of Safety", "unit": "", "type": "number", "min": 1.5, "max": 10, "required": True, "question": "Enter Factor of Safety (min 1.5):"},
]

# Assumptions per component
SHAFT_ASSUMPTIONS: List[Dict[str, Any]] = [
    {"key": "bending_moment_nm", "label": "Bending Moment", "unit": "N·m", "default_value": 0, "explanation": "Default is 0 N·m for pure torsion.", "type": "number", "min": 0, "max": 500000},
    {"key": "kb_shock", "label": "Bending Shock Factor (Kb)", "unit": "", "default_value": 0, "explanation": "0 = auto based on load type (1.0 steady, 1.5 moderate, 2.0 heavy).", "type": "number", "min": 0, "max": 3.0},
    {"key": "kt_shock", "label": "Torsion Shock Factor (Kt)", "unit": "", "default_value": 0, "explanation": "0 = auto based on load type (1.0 steady, 1.0 moderate, 1.5 heavy).", "type": "number", "min": 0, "max": 3.0},
]

GEARBOX_ASSUMPTIONS: List[Dict[str, Any]] = [
    {"key": "pressure_angle", "label": "Pressure Angle", "unit": "°", "default_value": 20, "explanation": "20° is standard.", "type": "select", "options": [{"value": "20", "label": "20°"}, {"value": "14.5", "label": "14.5°"}, {"value": "25", "label": "25°"}]},
    {"key": "quality_grade", "label": "AGMA Quality Grade", "unit": "", "default_value": "8", "explanation": "Grade 8 is precision standard.", "type": "select", "options": [{"value": "6", "label": "Grade 6"}, {"value": "8", "label": "Grade 8"}, {"value": "10", "label": "Grade 10"}]},
    {"key": "efficiency_per_stage", "label": "Efficiency per Stage", "unit": "%", "default_value": 97, "explanation": "97% standard.", "type": "number", "min": 80, "max": 99.9},
    {"key": "face_width_ratio", "label": "Face Width / Module Ratio", "unit": "", "default_value": 10, "explanation": "8-12 standard range.", "type": "number", "min": 6, "max": 20},
]

BEARING_ASSUMPTIONS: List[Dict[str, Any]] = []
CAM_ASSUMPTIONS: List[Dict[str, Any]] = []

BASE_CUSTOM_PARAMS: List[Dict[str, Any]] = [
    {"key": "part_name", "label": "Part Name", "type": "text", "required": True, "question": "What is the name of the part?"},
    {"key": "part_purpose", "label": "Primary Purpose", "type": "text", "required": True, "question": "What is its primary function/purpose?"},
    {"key": "overall_shape", "label": "Overall Shape", "type": "select", "required": True, "options": [{"value": "cylindrical", "label": "Cylindrical (disc, ring, flange, rod)"}, {"value": "rectangular", "label": "Rectangular (plate, block)"}, {"value": "L-bracket", "label": "L-Bracket / Angle bracket"}, {"value": "other", "label": "Other / Complex Shape"}], "question": "Describe the overall shape:"},
]

PARAM_KEY_ALIASES: Dict[str, str] = {
    # Flange aliases
    "pitch_circle_diameter_mm": "bolt_circle_diameter_mm",
    "pitch_circle_diameter": "bolt_circle_diameter_mm",
    "pcd_mm": "bolt_circle_diameter_mm",
    "pcd": "bolt_circle_diameter_mm",
    "bolt_pcd_mm": "bolt_circle_diameter_mm",
    "central_bore_diameter_mm": "inner_bore_diameter_mm",
    "center_bore_diameter_mm": "inner_bore_diameter_mm",
    "center_bore_mm": "inner_bore_diameter_mm",
    "bore_diameter_mm": "inner_bore_diameter_mm",
    "bore_mm": "inner_bore_diameter_mm",
    "inner_diameter_mm": "inner_bore_diameter_mm",
    "flange_outer_diameter_mm": "outer_diameter_mm",
    "od_mm": "outer_diameter_mm",
    "flange_thickness_mm": "thickness_mm",
    "thk_mm": "thickness_mm",
    "bolt_count": "num_bolts",
    "number_of_bolts": "num_bolts",
    "holes_count": "num_bolts",
    "hole_count": "num_bolts",
    # Shaft / General aliases
    "rotational_speed_rpm": "speed_rpm",
    "rpm": "speed_rpm",
    "power": "power_kw",
    "transmitted_power_kw": "power_kw",
    "minimum_factor_of_safety": "fos_target",
    "factor_of_safety": "fos_target",
    "safety_factor": "fos_target",
    "fos": "fos_target",
    "order_quantity": "quantity",
    "qty": "quantity",
    "part_quantity": "quantity",
}

def normalize_spec_keys(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Map extracted synonym keys to canonical parameter keys."""
    normalized = {}
    for k, v in spec.items():
        canonical_key = PARAM_KEY_ALIASES.get(k.lower().strip(), k)
        normalized[canonical_key] = v
    return normalized

CUSTOM_ARCHETYPE_PARAMS: Dict[str, List[Dict[str, Any]]] = {
    "flange": [
        {"key": "outer_diameter_mm", "label": "Outer Diameter", "unit": "mm", "type": "number", "min": 10.0, "max": 2000.0, "required": True, "default_value": 150.0, "question": "Enter outer diameter in mm:"},
        {"key": "inner_bore_diameter_mm", "label": "Inner Bore Diameter", "unit": "mm", "type": "number", "min": 0.0, "max": 1800.0, "required": True, "default_value": 30.0, "question": "Enter inner bore diameter in mm (0 if none):"},
        {"key": "thickness_mm", "label": "Thickness", "unit": "mm", "type": "number", "min": 1.0, "max": 500.0, "required": True, "default_value": 15.0, "question": "Enter thickness in mm:"},
        {"key": "bolt_circle_diameter_mm", "label": "Bolt Circle PCD", "unit": "mm", "type": "number", "min": 5.0, "max": 1900.0, "required": True, "default_value": 110.0, "question": "Enter Bolt Circle Diameter (PCD) in mm:"},
        {"key": "num_bolts", "label": "Number of Bolts", "unit": "", "type": "number", "min": 0.0, "max": 64.0, "required": True, "default_value": 4, "question": "Enter number of bolts/holes:"},
        {"key": "bolt_size", "label": "Bolt Size", "unit": "", "type": "select", "required": True, "default_value": "M8", "options": [{"value": "M4", "label": "M4"}, {"value": "M5", "label": "M5"}, {"value": "M6", "label": "M6"}, {"value": "M8", "label": "M8"}, {"value": "M10", "label": "M10"}, {"value": "M12", "label": "M12"}, {"value": "M16", "label": "M16"}], "question": "Select bolt size:"},
        {"key": "material_id", "label": "Material Grade", "unit": "", "type": "select", "required": True, "default_value": "steel_1045", "options": _material_options(), "question": "Select material grade:"},
    ],
    "plate_hole_pattern": [
        {"key": "length_mm", "label": "Plate Length", "unit": "mm", "type": "number", "min": 10.0, "max": 3000.0, "required": True, "default_value": 150.0, "question": "Enter plate length in mm:"},
        {"key": "width_mm", "label": "Plate Width", "unit": "mm", "type": "number", "min": 10.0, "max": 3000.0, "required": True, "default_value": 100.0, "question": "Enter plate width in mm:"},
        {"key": "thickness_mm", "label": "Plate Thickness", "unit": "mm", "type": "number", "min": 1.0, "max": 200.0, "required": True, "default_value": 10.0, "question": "Enter plate thickness in mm:"},
        {"key": "hole_layout", "label": "Hole Layout", "unit": "", "type": "select", "required": True, "default_value": "rectangular", "options": [{"value": "rectangular", "label": "Rectangular Grid"}, {"value": "circular", "label": "Circular Pattern"}], "question": "Select hole layout pattern:"},
        {"key": "hole_diameter_mm", "label": "Hole Diameter", "unit": "mm", "type": "number", "min": 1.0, "max": 100.0, "required": True, "default_value": 8.0, "question": "Enter hole diameter in mm:"},
        {"key": "hole_count", "label": "Hole Count", "unit": "", "type": "number", "min": 1.0, "max": 100.0, "required": True, "default_value": 4, "question": "Enter total hole count:"},
        {"key": "material_id", "label": "Material Grade", "unit": "", "type": "select", "required": True, "default_value": "steel_1045", "options": _material_options(), "question": "Select material grade:"},
    ],
    "bracket": [
        {"key": "bracket_type", "label": "Bracket Type", "unit": "", "type": "select", "required": True, "default_value": "l_shape", "options": [{"value": "l_shape", "label": "L-Shape Bracket"}, {"value": "flat_plate", "label": "Flat Plate Bracket"}, {"value": "u_shape", "label": "U-Shape Bracket"}], "question": "Select bracket type:"},
        {"key": "wall_thickness_mm", "label": "Wall Thickness", "unit": "mm", "type": "number", "min": 1.0, "max": 100.0, "required": True, "default_value": 4.0, "question": "Enter bracket wall thickness in mm:"},
        {"key": "length_mm", "label": "Base Length", "unit": "mm", "type": "number", "min": 10.0, "max": 1000.0, "required": True, "default_value": 100.0, "question": "Enter base length in mm:"},
        {"key": "width_mm", "label": "Width", "unit": "mm", "type": "number", "min": 10.0, "max": 1000.0, "required": True, "default_value": 50.0, "question": "Enter bracket width in mm:"},
        {"key": "height_mm", "label": "Height", "unit": "mm", "type": "number", "min": 10.0, "max": 1000.0, "required": True, "default_value": 60.0, "question": "Enter bracket height in mm:"},
        {"key": "hole_count", "label": "Mounting Hole Count", "unit": "", "type": "number", "min": 0.0, "max": 20.0, "required": True, "default_value": 2, "question": "Enter mounting hole count (0 if none):"},
        {"key": "gusset_needed", "label": "Gusset/Rib", "unit": "", "type": "select", "required": True, "default_value": "no", "options": [{"value": "yes", "label": "Yes — reinforce"}, {"value": "no", "label": "No"}], "question": "Reinforcement rib needed?"},
        {"key": "material_id", "label": "Material Grade", "unit": "", "type": "select", "required": True, "default_value": "aluminum_6061", "options": _material_options(), "question": "Select material grade:"},
    ],
    "spacer": [
        {"key": "outer_diameter_mm", "label": "Outer Diameter", "unit": "mm", "type": "number", "min": 2.0, "max": 500.0, "required": True, "default_value": 30.0, "question": "Enter spacer outer diameter in mm:"},
        {"key": "inner_bore_diameter_mm", "label": "Inner Bore Diameter", "unit": "mm", "type": "number", "min": 1.0, "max": 480.0, "required": True, "default_value": 12.0, "question": "Enter inner bore diameter in mm:"},
        {"key": "length_mm", "label": "Length/Height", "unit": "mm", "type": "number", "min": 1.0, "max": 1000.0, "required": True, "default_value": 25.0, "question": "Enter spacer length in mm:"},
        {"key": "material_id", "label": "Material Grade", "unit": "", "type": "select", "required": True, "default_value": "steel_1045", "options": _material_options(), "question": "Select material grade:"},
    ],
    "lever": [
        {"key": "length_mm", "label": "Lever Length", "unit": "mm", "type": "number", "min": 10.0, "max": 2000.0, "required": True, "default_value": 150.0, "question": "Enter lever length in mm:"},
        {"key": "thickness_mm", "label": "Lever Thickness", "unit": "mm", "type": "number", "min": 2.0, "max": 100.0, "required": True, "default_value": 10.0, "question": "Enter lever thickness in mm:"},
        {"key": "width_mm", "label": "Lever Width", "unit": "mm", "type": "number", "min": 5.0, "max": 500.0, "required": True, "default_value": 25.0, "question": "Enter lever width in mm:"},
        {"key": "pivot_bore_diameter_mm", "label": "Pivot Bore Diameter", "unit": "mm", "type": "number", "min": 2.0, "max": 200.0, "required": True, "default_value": 12.0, "question": "Enter pivot bore diameter in mm:"},
        {"key": "material_id", "label": "Material Grade", "unit": "", "type": "select", "required": True, "default_value": "aluminum_6061", "options": _material_options(), "question": "Select material grade:"},
    ],
    "housing": [
        {"key": "outer_length_mm", "label": "Outer Length", "unit": "mm", "type": "number", "min": 10.0, "max": 2000.0, "required": True, "default_value": 120.0, "question": "Enter housing outer length in mm:"},
        {"key": "outer_width_mm", "label": "Outer Width", "unit": "mm", "type": "number", "min": 10.0, "max": 2000.0, "required": True, "default_value": 80.0, "question": "Enter housing outer width in mm:"},
        {"key": "outer_height_mm", "label": "Outer Height", "unit": "mm", "type": "number", "min": 5.0, "max": 1000.0, "required": True, "default_value": 50.0, "question": "Enter housing outer height in mm:"},
        {"key": "wall_thickness_mm", "label": "Wall Thickness", "unit": "mm", "type": "number", "min": 1.0, "max": 50.0, "required": True, "default_value": 4.0, "question": "Enter wall thickness in mm:"},
        {"key": "is_hollow", "label": "Is Hollow", "unit": "", "type": "select", "required": True, "default_value": "yes", "options": [{"value": "yes", "label": "Yes — hollow"}, {"value": "no", "label": "No — solid block"}], "question": "Is this a hollow housing?"},
        {"key": "material_id", "label": "Material Grade", "unit": "", "type": "select", "required": True, "default_value": "aluminum_6061", "options": _material_options(), "question": "Select material grade:"},
    ],
    "generic": [
        {"key": "length_mm", "label": "Length", "unit": "mm", "type": "number", "min": 1.0, "max": 5000.0, "required": True, "default_value": 100.0, "question": "Enter length in mm:"},
        {"key": "width_mm", "label": "Width", "unit": "mm", "type": "number", "min": 1.0, "max": 5000.0, "required": True, "default_value": 50.0, "question": "Enter width in mm:"},
        {"key": "height_mm", "label": "Height/Thickness", "unit": "mm", "type": "number", "min": 1.0, "max": 5000.0, "required": True, "default_value": 25.0, "question": "Enter height in mm:"},
        {"key": "material_id", "label": "Material Grade", "unit": "", "type": "select", "required": True, "default_value": "steel_1045", "options": _material_options(), "question": "Select material grade:"},
    ]
}

COMPONENT_PARAMS: Dict[str, List[Dict[str, Any]]] = {
    "shaft": SHAFT_PARAMS,
    "bearing": BEARING_PARAMS,
    "gearbox": GEARBOX_PARAMS,
    "cam": CAM_PARAMS,
    "custom": [],
}

COMPONENT_LABELS: Dict[str, str] = {
    "shaft": "Shaft Design",
    "bearing": "Bearing Selection",
    "gearbox": "Gearbox Design",
    "cam": "CAM Design",
    "flange": "Flange Design",
    "plate_hole_pattern": "Plate with Hole Pattern",
    "bracket": "Bracket Design",
    "spacer": "Spacer / Bushing",
    "lever": "Lever Arm",
    "housing": "Enclosure / Housing",
    "custom": "Custom Part Design",
}


def get_params_for_component(component_type: str, archetype: Optional[str] = None) -> List[Dict[str, Any]]:
    if component_type == "custom":
        if archetype and archetype in CUSTOM_ARCHETYPE_PARAMS:
            return BASE_CUSTOM_PARAMS + CUSTOM_ARCHETYPE_PARAMS[archetype]
        return BASE_CUSTOM_PARAMS
    if component_type in CUSTOM_ARCHETYPE_PARAMS:
        return CUSTOM_ARCHETYPE_PARAMS[component_type]
    return COMPONENT_PARAMS.get(component_type, [])


def get_assumptions_for_component(component_type: str, archetype: Optional[str] = None) -> List[Dict[str, Any]]:
    if component_type == "shaft":
        return SHAFT_ASSUMPTIONS
    elif component_type == "gearbox":
        return GEARBOX_ASSUMPTIONS
    return []


def compute_smart_defaults(component_type: str, params: Dict[str, Any], archetype: Optional[str] = None) -> List[Dict[str, Any]]:
    assumptions = get_assumptions_for_component(component_type, archetype)
    result = []
    for a in assumptions:
        entry = dict(a)
        if component_type == "shaft":
            loading = params.get("loading_type", "pure_torsion")
            if a["key"] == "bending_moment_nm":
                entry["default_value"] = 0
                entry["explanation"] = f"Default 0 N·m for {loading}."
        result.append(entry)
    return result


def get_next_missing_param(component_type: str, collected: Dict[str, Any], archetype: Optional[str] = None) -> Optional[Dict[str, Any]]:
    params = get_params_for_component(component_type, archetype)
    for p in params:
        key = p["key"]
        if key in collected and collected[key] is not None:
            continue
        cond = p.get("condition")
        if cond:
            dep_key = cond["key"]
            dep_val = collected.get(dep_key)
            if "equals" in cond and dep_val != cond["equals"]:
                continue
            if "not_equals" in cond and dep_val == cond["not_equals"]:
                continue
        if p.get("allow_empty") and not p.get("required"):
            continue
        if p.get("required", False):
            return p
    return None


def are_all_params_collected(component_type: str, collected: Dict[str, Any], archetype: Optional[str] = None) -> bool:
    return get_next_missing_param(component_type, collected, archetype) is None


def validate_param(param_def: Dict[str, Any], value: Any) -> Optional[str]:
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
    return None


def generate_clarification_questions(
    component_family: str,
    collected_spec: Dict[str, Any]
) -> List[ClarificationQuestion]:
    """
    Generate batched clarification questions for all missing required parameters.
    """
    all_params = get_params_for_component(component_family)
    questions = []
    
    for p in all_params:
        key = p["key"]
        if key in collected_spec and collected_spec[key] is not None and str(collected_spec[key]).strip() != "":
            continue
            
        # Check condition visibility
        cond = p.get("condition")
        if cond:
            dep_key = cond["key"]
            dep_val = collected_spec.get(dep_key)
            if "equals" in cond and dep_val != cond["equals"]:
                continue
            if "not_equals" in cond and dep_val == cond["not_equals"]:
                continue
                
        if p.get("required", False):
            questions.append(ClarificationQuestion(
                field=key,
                label=p.get("label", key),
                question=p.get("question", f"Enter {p.get('label', key)}:"),
                type=p.get("type", "number"),
                unit=p.get("unit", ""),
                options=p.get("options"),
                default_value=p.get("default_value")
            ))
            
    return questions
