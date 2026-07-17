"""
Engineering Math Engine — Deterministic Calculations
Each component type uses proper engineering formulas per:
  - Shigley's Mechanical Engineering Design
  - Engineers Edge reference tables
  - ISO 281 (bearings), AGMA 2001 (gears), ASME B106.1M (shafts)

Cross-validation: Results are verified against knowledge_base.json
where matching formulas exist. No LLM arithmetic — Python handles all numbers.
"""

import math
from typing import Dict, Any, List, Optional
from .params import get_material, MATERIAL_DB, parse_gear_ratio
from .knowledge_lookup import validate_calculation as kb_validate, search_kb


# ── Result Structures ─────────────────────────────────────────────────────────
def _calc(name: str, formula: str, result: float, unit: str, desc: str) -> Dict:
    return {
        "name": name, "formula": formula,
        "result": round(result, 4), "unit": unit, "description": desc,
    }


def _kb_cross_check(domain: str, topic: str, inputs: Dict[str, float],
                    our_result: float, tolerance: float = 0.01) -> Optional[Dict]:
    """
    Cross-check our hardcoded result against the KB formula.
    Returns a verification dict or None if no matching KB entry.
    """
    try:
        kb_result = kb_validate(domain, topic, inputs)
        if kb_result.get("valid"):
            kb_val = kb_result["result"]
            diff = abs(kb_val - our_result) / max(abs(our_result), 1e-9)
            return {
                "kb_verified": diff <= tolerance,
                "kb_value": kb_val,
                "our_value": round(our_result, 6),
                "deviation_pct": round(diff * 100, 4),
                "source": f"{domain}/{topic}",
            }
    except Exception:
        pass
    return None

def _run_kb_checks(P, N, T, omega, sigma_b, tau_actual, sigma_vm) -> List[Dict]:
    """
    Run KB cross-validation checks for shaft calculations.
    Compares our hardcoded results against knowledge_base.json formulas.
    """
    checks = []

    # Torque: T = 9550 * P / N
    v = _kb_cross_check("Mechanics", "Torque", {"P": P, "N": N}, T)
    if v:
        checks.append({"formula": "Torque (T = 9550*P/N)", **v})

    # Angular velocity: omega = 2*pi*N / 60
    v = _kb_cross_check("Mechanics", "Angular Velocity", {"N": N}, omega)
    if v:
        checks.append({"formula": "Angular Velocity (omega = 2piN/60)", **v})

    # Von Mises: sigma_vm = sqrt(sigma_b^2 + 3*tau^2)
    v = _kb_cross_check("Mechanics", "Von Mises",
                         {"sigma_b": sigma_b, "tau": tau_actual}, sigma_vm)
    if v:
        checks.append({"formula": "Von Mises Stress", **v})

    return checks


# ══════════════════════════════════════════════════════════════════════════════
#  SHAFT DESIGN — per ASME B106.1M, Shigley's Ch. 7
# ══════════════════════════════════════════════════════════════════════════════
def calculate_shaft(params: Dict[str, Any]) -> Dict[str, Any]:
    P = float(params["power_kw"])
    N = float(params["speed_rpm"])
    loading = params["loading_type"]
    mat_id = params.get("material_id", "steel_1045")
    shaft_type = params.get("shaft_type", "solid")
    K = float(params.get("inner_diameter_ratio", 0)) if shaft_type == "hollow" else 0.0
    has_keyway = params.get("keyway", "no") == "yes"
    num_keyways = float(params.get("num_keyways", 1)) if has_keyway else 0
    fos = float(params["fos"])
    M_b = float(params.get("bending_moment_nm", 0))

    mat = get_material(mat_id)
    sigma_y = mat["yield_mpa"]
    sigma_u = mat["ultimate_mpa"]
    E = mat["elastic_modulus_gpa"] * 1000  # GPa -> MPa

    calcs = []
    warnings = []
    recommendations = []

    # 1. Torque — standard formula T = 9550·P/N (N·m)
    T = (9550 * P) / N if N > 0 else 0
    calcs.append(_calc("Transmitted Torque", "T = 9550 × P / N",
                        T, "N·m", f"P={P} kW, N={N} RPM"))

    # 2. Angular velocity
    omega = (2 * math.pi * N) / 60
    calcs.append(_calc("Angular Velocity", "ω = 2π·N / 60", omega, "rad/s", ""))

    # 3. Allowable shear stress — Max Shear Stress Theory
    #    τ_allow = σy / (2 × FOS) per Tresca criterion
    Kt_key = 1.0
    if has_keyway:
        Kt_key = 1.6 + 0.1 * (num_keyways - 1)  # empirical addition for multiple keyways
    tau_allow = sigma_y / (2 * fos * Kt_key)
    calcs.append(_calc("Allowable Shear Stress",
                        f"τ_allow = σy / (2·FOS·Kt) = {sigma_y}/(2×{fos}×{Kt_key})",
                        tau_allow, "MPa",
                        f"Max Shear Stress Theory (Tresca). Kt={Kt_key}"))

    # 4. Equivalent moment with shock factors
    if loading == "pure_torsion":
        # Pure torsion: d³ = 16T / (π·τ_allow)
        T_mm = T * 1000  # N·m -> N·mm
        if shaft_type == "solid":
            d_cubed = (16 * T_mm) / (math.pi * tau_allow)
        else:
            d_cubed = (16 * T_mm) / (math.pi * tau_allow * (1 - K**4))
        d_mm = d_cubed ** (1/3) if d_cubed > 0 else 10
        calcs.append(_calc("Required Diameter (Torsion)",
                            "d = ∛(16T / (π·τ_allow·(1−K⁴)))",
                            d_mm, "mm", "Pure torsion design"))
    else:
        # Combined bending + torsion with ASME shock factors
        Kb = float(params.get("kb_shock", 0))
        Kt_shock = float(params.get("kt_shock", 0))
        
        if Kb == 0 or Kt_shock == 0:
            if loading == "fluctuating":
                Kb, Kt_shock = 2.0, 1.5  # heavy shock
            else:
                Kb, Kt_shock = 1.5, 1.0  # moderate
                
        calcs.append(_calc("Shock Factors", f"Kb={Kb}, Kt={Kt_shock}",
                            0, "—", "ASME B106.1M shock load factors"))

        # Me = √((Kb·M)² + (Kt·T)²)
        Me = math.sqrt((Kb * M_b)**2 + (Kt_shock * T)**2)
        Me_mm = Me * 1000  # N·mm
        calcs.append(_calc("Equivalent Moment (ASME)",
                            "Me = √((Kb·M)² + (Kt·T)²)",
                            Me, "N·m", "Combined loading with shock factors"))

        # d = ∛(16·Me / (π·τ_allow))
        if shaft_type == "solid":
            d_cubed = (16 * Me_mm) / (math.pi * tau_allow)
        else:
            d_cubed = (16 * Me_mm) / (math.pi * tau_allow * (1 - K**4))
        d_mm = d_cubed ** (1/3) if d_cubed > 0 else 10
        calcs.append(_calc("Required Diameter (Combined)",
                            "d = ∛(16·Me / (π·τ_allow·(1−K⁴)))",
                            d_mm, "mm", "ASME B106.1M"))

    # 5. Standardize to nearest 5mm
    d_std = max(math.ceil(d_mm / 5) * 5, 10)
    calcs.append(_calc("Standard Diameter", "Round up to nearest 5mm",
                        d_std, "mm", "Per ISO preferred sizes"))

    # 6. Verification — actual shear stress
    if shaft_type == "solid":
        J = (math.pi * (d_std ** 4)) / 32
        I = (math.pi * (d_std ** 4)) / 64
    else:
        d_inner = d_std * K
        J = (math.pi * (d_std**4 - d_inner**4)) / 32
        I = (math.pi * (d_std**4 - d_inner**4)) / 64

    tau_actual = (T * 1000 * (d_std / 2)) / J
    calcs.append(_calc("Actual Shear Stress", "τ = T·r / J",
                        tau_actual, "MPa", "Torsional shear verification"))

    # 7. Bending stress (if applicable)
    if M_b > 0:
        sigma_b = (M_b * 1000 * (d_std / 2)) / I
        calcs.append(_calc("Bending Stress", "σb = M·y / I",
                            sigma_b, "MPa", "Bending stress at outer fiber"))
    else:
        sigma_b = 0

    # 8. Von Mises combined stress
    sigma_vm = math.sqrt(sigma_b**2 + 3 * tau_actual**2)
    calcs.append(_calc("Von Mises Stress", "σv = √(σb² + 3τ²)",
                        sigma_vm, "MPa", "Combined stress criterion"))

    fos_actual = sigma_y / sigma_vm if sigma_vm > 0 else 99
    calcs.append(_calc("Actual Factor of Safety", "FOS = σy / σv",
                        fos_actual, "—", "Must be ≥ required FOS"))

    # 9. Deflection estimate (simply supported, central load)
    L_mm = d_std * 10  # typical L/D=10
    # δ = F·L³ / (48·E·I) — approximate with F from torque
    F_approx = (2 * T * 1000) / L_mm if L_mm > 0 else 0
    delta = (F_approx * L_mm**3) / (48 * E * I) if (E * I) > 0 else 0
    calcs.append(_calc("Est. Deflection (midspan)", "δ = F·L³/(48·E·I)",
                        delta, "mm", f"L={L_mm}mm, E={E/1000:.0f} GPa"))

    delta_limit = L_mm / 3000  # typical limit
    if delta > delta_limit:
        warnings.append(f"Deflection {delta:.4f}mm exceeds limit {delta_limit:.4f}mm (L/3000)")

    calcs.append(_calc("Recommended Length", "L ≈ 10 × d",
                        L_mm, "mm", "Typical L/D ratio for bearing support"))

    # Safety warnings
    if fos_actual < fos:
        warnings.append(f"CRITICAL: Actual FOS ({fos_actual:.2f}) below required ({fos})")
    if N > 3600:
        recommendations.append("High-speed shaft: perform critical speed analysis")
    if has_keyway:
        recommendations.append("Keyway present: use fillet radius ≥ 0.5mm per ASME B17.1")
    recommendations.append(f"Verify with fatigue analysis for σe = {mat.get('endurance_mpa', 'N/A')} MPa")

    return {
        "calculations": calcs,
        "dimensions": {
            "diameter_mm": d_std,
            "inner_diameter_mm": round(d_std * K, 1) if K > 0 else None,
            "length_mm": L_mm,
        },
        "safety": {
            "fos_actual": round(fos_actual, 2),
            "fos_required": fos,
            "is_safe": fos_actual >= fos,
            "warnings": warnings,
            "recommendations": recommendations,
        },
        "kb_verifications": _run_kb_checks(P, N, T, omega, sigma_b, tau_actual, sigma_vm),
        "standards": [
            "ASME B106.1M — Shaft Design",
            "ASME B17.1 — Keys and Keyseats",
            "ISO 286-1 — Limits and Fits",
            "Max Shear Stress Theory (Tresca)",
        ],
        "material": mat,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  BEARING SELECTION — per ISO 281, SKF methodology
# ══════════════════════════════════════════════════════════════════════════════
def calculate_bearing(params: Dict[str, Any]) -> Dict[str, Any]:
    Fr = float(params["radial_load_n"])
    Fa = float(params["axial_load_n"])
    N = float(params["speed_rpm"])
    Lh = float(params["desired_life_hours"])
    b_type = params["bearing_type"]
    reliability = params.get("reliability", "90")
    fos = float(params["fos"])

    calcs = []
    warnings = []
    recommendations = []

    # Life exponent
    p = 3.0 if b_type in ("deep_groove_ball", "angular_contact_ball") else 10/3

    # Reliability factor a1
    a1_map = {"90": 1.0, "95": 0.62, "99": 0.21}
    a1 = a1_map.get(reliability, 1.0)

    # Equivalent dynamic load P = X·Fr + Y·Fa
    # Simplified: for Fa/Fr < e, X=1, Y=0
    ratio = Fa / Fr if Fr > 0 else 0
    if b_type == "deep_groove_ball":
        if ratio <= 0.55:
            X, Y = 1.0, 0.0
        else:
            X, Y = 0.56, 1.6
    elif b_type == "angular_contact_ball":
        X, Y = 0.5, 0.87
    else:  # roller types
        if ratio <= 0.4:
            X, Y = 1.0, 0.0
        else:
            X, Y = 0.4, 1.5

    P_eq = X * Fr + Y * Fa
    calcs.append(_calc("Equivalent Dynamic Load",
                        f"P = X·Fr + Y·Fa = {X}×{Fr} + {Y}×{Fa}",
                        P_eq, "N", f"Load factors: X={X}, Y={Y}"))

    # Required life in millions of revolutions
    L10_rev = (60 * N * Lh) / 1e6
    calcs.append(_calc("Required Life (L10)",
                        "L10 = 60·N·Lh / 10⁶", L10_rev, "×10⁶ rev",
                        f"For {Lh} hours at {N} RPM"))

    # Adjusted life with reliability
    L10a = L10_rev / a1 if a1 > 0 else L10_rev
    calcs.append(_calc("Adjusted Life (reliability)",
                        f"L10a = L10 / a1 = {L10_rev:.2f}/{a1}",
                        L10a, "×10⁶ rev",
                        f"Reliability factor a1={a1} ({reliability}%)"))

    # Required dynamic load rating C
    C_req = P_eq * (L10a ** (1/p))
    calcs.append(_calc("Required Dynamic Load Rating (C)",
                        f"C = P × L10a^(1/p) = {P_eq:.0f} × {L10a:.2f}^(1/{p:.2f})",
                        C_req, "N",
                        "Minimum catalogue C rating to select bearing"))

    # Estimated bore diameter (empirical: d ≈ 10 × ∛(Fr/500))
    bore = max(10 * (Fr / 500) ** (1/3), 10)
    bore_std = math.ceil(bore / 5) * 5  # standard bore sizes in 5mm steps
    calcs.append(_calc("Estimated Bore Diameter",
                        "d ≈ 10 × ∛(Fr/500), rounded to std",
                        bore_std, "mm",
                        "Approximate — verify with bearing catalogue"))

    # Static safety check
    C0_req = fos * P_eq  # static load rating
    calcs.append(_calc("Required Static Load Rating (C0)",
                        f"C0 = S0 × P = {fos} × {P_eq:.0f}",
                        C0_req, "N",
                        f"Static safety factor S0={fos}"))

    # Expected life with selected C
    if P_eq > 0:
        L_expected_hrs = (a1 * (C_req / P_eq) ** p * 1e6) / (60 * N) if N > 0 else 0
    else:
        L_expected_hrs = 0
    calcs.append(_calc("Expected Bearing Life",
                        "Lh = a1 × (C/P)^p × 10⁶ / (60·N)",
                        L_expected_hrs, "hours",
                        "Calculated life with required C"))

    if N > 3000 and fos < 2.0:
        warnings.append("High-speed bearing: recommend S0 ≥ 2.0")
    if ratio > 0.8:
        recommendations.append("High axial/radial ratio: consider angular contact or taper roller")

    return {
        "calculations": calcs,
        "dimensions": {
            "bore_diameter_mm": bore_std,
            "C_required_n": round(C_req, 0),
            "C0_required_n": round(C0_req, 0),
        },
        "safety": {
            "fos_actual": fos,
            "fos_required": fos,
            "is_safe": True,
            "warnings": warnings,
            "recommendations": recommendations + [
                "Verify with bearing manufacturer catalogue (SKF, FAG, NSK)",
                f"Look for bearing with C ≥ {C_req:.0f} N, C0 ≥ {C0_req:.0f} N",
            ],
        },
        "standards": [
            "ISO 281 — Rolling Bearings — Dynamic Load Ratings",
            "ISO 76 — Static Load Ratings",
            "ISO 15 — Radial Bearings — Boundary Dimensions",
        ],
        "material": None,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  GEARBOX DESIGN — per AGMA 2001, ISO 6336
# ══════════════════════════════════════════════════════════════════════════════
def calculate_gearbox(params: Dict[str, Any]) -> Dict[str, Any]:
    P = float(params["power_kw"])
    N1 = float(params["input_speed_rpm"])
    N2_desired = float(params["output_speed_rpm"])
    
    raw_ratio = str(params.get("gear_ratio", "")).strip()
    if not raw_ratio or raw_ratio == "auto":
        i = N1 / N2_desired if N2_desired > 0 else 1.0
    else:
        parsed = parse_gear_ratio(raw_ratio)
        i = parsed if parsed is not None else (N1 / N2_desired if N2_desired > 0 else 1.0)
    
    multi_stage = params.get("multi_stage", "no") == "yes"
    num_stages = int(params.get("num_stages", 2)) if multi_stage else 1
    
    gear_type = params["gear_type"]
    phi = float(params.get("pressure_angle", 20))
    mat_id = params.get("material_id", "steel_1045")
    fos = float(params["fos"])

    mat = get_material(mat_id)
    sigma_y = mat["yield_mpa"]

    calcs = []
    warnings = []
    recommendations = []
    
    motor_phase = params.get("motor_phase", "")
    motor_poles = params.get("motor_poles", "")
    if motor_poles != "na" and motor_poles != "":
        calcs.append(_calc("Motor Specs", f"{motor_phase}, {motor_poles} poles", 0, "—", ""))

    # 1. Torque on pinion
    omega1 = (2 * math.pi * N1) / 60
    T1 = (P * 1000) / omega1 if omega1 > 0 else 0
    calcs.append(_calc("Pinion Torque", "T1 = P×1000 / ω1",
                        T1, "N·m", "Input torque on pinion"))

    # 2. Output speed & torque
    i_stage = i ** (1/num_stages) if num_stages > 0 else i
    calcs.append(_calc("Stage Ratio", "i_stage = ⁿ√i", i_stage, "—", f"Overall ratio = {i:.2f}, {num_stages} stages"))

    N2 = N1 / i
    eff_per_stage = float(params.get("efficiency_per_stage", 97)) / 100.0
    eff_total = eff_per_stage ** num_stages
    T2 = T1 * i * eff_total
    calcs.append(_calc("Output Speed", "N2 = N1 / i",
                        N2, "RPM", f"Target was {N2_desired} RPM"))
    calcs.append(_calc("Output Torque", "T2 = T1 × i × η_total",
                        T2, "N·m", f"With {eff_total*100:.1f}% total mech efficiency"))

    # 3. Minimum pinion teeth (to avoid undercutting)
    phi_rad = math.radians(phi)
    z_min = max(int(math.ceil(2 / (math.sin(phi_rad) ** 2))), 14)
    z1 = max(z_min, 18)  # practical minimum
    z2 = int(round(z1 * i_stage))
    calcs.append(_calc("Pinion Teeth (z1)", f"z_min = 2/sin²(φ) ≥ {z_min}",
                        z1, "teeth", f"Pressure angle = {phi}°"))
    calcs.append(_calc("Gear Teeth (z2 per stage)", "z2 = z1 × i_stage",
                        z2, "teeth", "Wheel teeth count for one stage"))

    # 4. Module from Lewis beam strength
    sigma_b = sigma_y / fos
    # Lewis form factor Y ≈ 0.32 for z=18..20 at 20°
    Y = 0.308 + 0.0012 * z1 if z1 <= 30 else 0.36
    # b = 10·m (face width), Ft = 2T/d = 2T/(m·z)
    # σ = Ft / (b·m·Y) => m³ = 2·T / (z1·10·Y·σ_b)
    m_cubed = (2 * T1 * 1000) / (z1 * 10 * Y * sigma_b)
    m_calc = m_cubed ** (1/3)

    # Standard modules (IS / DIN): 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10
    std_modules = [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
    m_std = min((m for m in std_modules if m >= m_calc), default=10)
    calcs.append(_calc("Calculated Module", "m = ∛(2T / (z·10·Y·σ_b))",
                        m_calc, "mm", f"Lewis form factor Y={Y:.3f}"))
    calcs.append(_calc("Standard Module", "Nearest standard module",
                        m_std, "mm", "Per IS 2535 / DIN 780"))

    # 5. Pitch diameters
    d1 = m_std * z1
    d2 = m_std * z2
    calcs.append(_calc("Pinion Pitch Diameter", "d1 = m × z1",
                        d1, "mm", ""))
    calcs.append(_calc("Gear Pitch Diameter", "d2 = m × z2",
                        d2, "mm", ""))

    # 6. Face width
    face_ratio = float(params.get("face_width_ratio", 10))
    b = face_ratio * m_std
    calcs.append(_calc("Face Width", f"b = {face_ratio} × m",
                        b, "mm", "From face width ratio assumption"))

    # 7. Tangential force & stress verification
    Ft = (2 * T1 * 1000) / d1 if d1 > 0 else 0
    sigma_actual = Ft / (b * m_std * Y) if (b * m_std * Y) > 0 else 0
    calcs.append(_calc("Tangential Force", "Ft = 2T1 / d1",
                        Ft, "N", "Force at pitch circle"))
    calcs.append(_calc("Actual Bending Stress", "σ = Ft / (b·m·Y)",
                        sigma_actual, "MPa", "Must be < allowable"))

    fos_actual = sigma_y / sigma_actual if sigma_actual > 0 else 99
    calcs.append(_calc("Actual FOS (Bending)", "FOS = σ_y / σ_actual",
                        fos_actual, "—", ""))

    if gear_type == "helical":
        recommendations.append("Helical: apply helix angle correction (β=15-25°)")
    if fos_actual < fos:
        warnings.append(f"Bending FOS ({fos_actual:.2f}) is below required ({fos})")

    size_w = float(params.get("size_max_width_mm", 0))
    size_h = float(params.get("size_max_height_mm", 0))
    # rough size estimate for gearbox:
    est_width = b * num_stages * 1.5
    est_height = (d1 + d2) * 1.2
    calcs.append(_calc("Estimated GB Width", "b × stages × casing factor", est_width, "mm", ""))
    calcs.append(_calc("Estimated GB Height", "(d1+d2) × casing factor", est_height, "mm", ""))

    if size_w > 0 and est_width > size_w:
        warnings.append(f"Estimated width ({est_width:.1f}mm) exceeds max constraint ({size_w}mm)")
    if size_h > 0 and est_height > size_h:
        warnings.append(f"Estimated height ({est_height:.1f}mm) exceeds max constraint ({size_h}mm)")

    return {
        "calculations": calcs,
        "dimensions": {
            "module_mm": m_std,
            "pinion_teeth": z1,
            "gear_teeth": z2,
            "pinion_pitch_dia_mm": d1,
            "gear_pitch_dia_mm": d2,
            "face_width_mm": b,
        },
        "safety": {
            "fos_actual": round(fos_actual, 2),
            "fos_required": fos,
            "is_safe": fos_actual >= fos,
            "warnings": warnings,
            "recommendations": recommendations + [
                "Perform AGMA 2001 surface durability check",
                "Verify center distance: a = (d1+d2)/2",
            ],
        },
        "standards": [
            "AGMA 2001-D04 — Spur & Helical Gear Rating",
            "ISO 6336-1 — Gear Load Capacity",
            "IS 2535 — Standard Gear Module Series",
        ],
        "material": mat,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CAM DESIGN — per Shigley's Ch. 3, Norton's Machine Design
# ══════════════════════════════════════════════════════════════════════════════
def calculate_cam(params: Dict[str, Any]) -> Dict[str, Any]:
    N = float(params["cam_speed_rpm"])
    h = float(params["follower_lift_mm"])
    profile = params["profile_type"]
    follower = params["follower_type"]
    Rb = float(params["base_circle_radius_mm"])
    beta_rise = float(params["rise_angle_deg"])
    beta_dwell = float(params.get("dwell_angle_deg", 60))
    fos = float(params["fos"])

    calcs = []
    warnings = []
    recommendations = []

    omega = (2 * math.pi * N) / 60
    beta_rise_rad = math.radians(beta_rise)

    calcs.append(_calc("Angular Velocity", "ω = 2π·N / 60",
                        omega, "rad/s", ""))

    # Max velocity and acceleration per profile
    if profile == "shm":
        v_max = (math.pi * h * omega) / (2 * beta_rise_rad)
        a_max = (math.pi**2 * h * omega**2) / (2 * beta_rise_rad**2)
        profile_name = "Simple Harmonic Motion"
    elif profile == "cycloidal":
        v_max = (2 * h * omega) / beta_rise_rad
        a_max = (2 * math.pi * h * omega**2) / (beta_rise_rad**2)
        profile_name = "Cycloidal"
    else:  # parabolic
        v_max = (2 * h * omega) / beta_rise_rad
        a_max = (4 * h * omega**2) / (beta_rise_rad**2)
        profile_name = "Parabolic (Constant Acceleration)"

    calcs.append(_calc("Max Follower Velocity",
                        f"{profile_name} formula", v_max, "mm/s", ""))
    calcs.append(_calc("Max Follower Acceleration",
                        f"{profile_name} formula", a_max, "mm/s²", ""))

    # Pressure angle check
    # tan(α_max) ≈ h / (π × Rb) for SHM (simplified)
    alpha_max_rad = math.atan2(h, math.pi * Rb) if Rb > 0 else 0
    alpha_max_deg = math.degrees(alpha_max_rad)
    calcs.append(_calc("Max Pressure Angle",
                        "α_max = atan(h / (π·Rb))",
                        alpha_max_deg, "°",
                        "Must be ≤ 30° for roller, ≤ 45° for flat-face"))

    limit = 45 if follower == "flat_face" else 30
    if alpha_max_deg > limit:
        warnings.append(f"Pressure angle {alpha_max_deg:.1f}° exceeds limit ({limit}°) — increase base circle radius")

    # Minimum radius of curvature (avoid undercutting)
    rho_min = Rb + h - (h * math.pi**2 / (4 * beta_rise_rad**2)) if profile == "shm" else Rb
    calcs.append(_calc("Min Radius of Curvature",
                        "ρ_min (profile-dependent)", max(rho_min, 0), "mm",
                        "Must be > 0 to avoid undercutting"))

    if rho_min < 0:
        warnings.append("CRITICAL: Negative radius of curvature — cam profile will undercut. Increase Rb.")

    # Cam max radius
    R_max = Rb + h
    calcs.append(_calc("Max Cam Radius", "R_max = Rb + h",
                        R_max, "mm", "Cam outer radius at full lift"))

    # Cam face width (empirical)
    cam_width = max(h * 1.5, 15)
    calcs.append(_calc("Recommended Cam Width",
                        "b ≈ 1.5 × h (min 15mm)", cam_width, "mm", ""))

    # Contact stress (Hertz) if roller follower
    if follower == "roller":
        roller_r = max(h * 0.4, 5)
        E_star = 200e3 / 2  # both steel, E*=E/2
        F_contact = a_max * 0.5  # simplified — mass × accel
        p_hertz = math.sqrt((F_contact * E_star) / (math.pi * cam_width * roller_r)) if cam_width * roller_r > 0 else 0
        calcs.append(_calc("Hertzian Contact Pressure",
                            "p_H = √(F·E* / (π·b·R))",
                            p_hertz, "MPa", f"Roller radius = {roller_r:.1f} mm"))

    beta_return = 360 - beta_rise - beta_dwell
    calcs.append(_calc("Return Angle", "360° - rise - dwell",
                        beta_return, "°", ""))

    if N > 1000:
        recommendations.append("High-speed cam: perform dynamic/vibration analysis")
    recommendations.append(f"Surface hardness: HRC 58-62 recommended for wear resistance")

    return {
        "calculations": calcs,
        "dimensions": {
            "base_circle_radius_mm": Rb,
            "max_radius_mm": R_max,
            "cam_width_mm": round(cam_width, 1),
            "lift_mm": h,
        },
        "safety": {
            "fos_actual": fos,
            "fos_required": fos,
            "is_safe": alpha_max_deg <= limit and rho_min >= 0,
            "warnings": warnings,
            "recommendations": recommendations,
        },
        "standards": [
            "ISO 6336 — Contact Stress Calculation",
            "ANSI/ASME B18.3 — Mechanical Components",
            "DIN 740 — Cam Mechanisms",
        ],
        "material": None,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM PART — Dimensional design from free-form user input
# ══════════════════════════════════════════════════════════════════════════════
def calculate_custom(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a design report for a custom part based on collected dimensions."""
    calcs = []
    warnings = []
    recommendations = []

    L = float(params.get("length_mm", 100))
    W = float(params.get("width_mm", 50))
    H = float(params.get("height_mm", 25))
    mat_type = str(params.get("material_type", "steel")).lower()

    # Material density lookup
    density_map = {
        "steel": 7850, "aluminum": 2700, "cast iron": 7200,
        "stainless steel": 8000, "brass": 8500, "plastic": 1200,
    }
    density = density_map.get(mat_type, 7850)

    # Bounding volume and Net volume
    from .cad_engine import compute_expected_properties
    expected = compute_expected_properties("custom", {"length_mm": L, "width_mm": W, "height_mm": H}, params)
    
    if expected and expected.get("volume", 0) > 0:
        net_vol = expected["volume"]
        vol_mm3 = L * W * H
        vol_m3 = vol_mm3 * 1e-9
        mass_kg = vol_m3 * density
        calcs.append(_calc("Bounding Volume", "V = L × W × H",
                            vol_mm3, "mm³", f"{L}×{W}×{H}"))
        calcs.append(_calc("Estimated Mass", "m = V × ρ",
                            mass_kg, "kg", f"Density = {density} kg/m³ ({mat_type})"))
        
        net_mass = net_vol * 1e-9 * density
        calcs.append(_calc("Net Volume (Custom Operations)", "V_net = V_cad",
                            net_vol, "mm³", "Volume calculated from CAD operations"))
        calcs.append(_calc("Net Mass", "m_net = V_net × ρ",
                            net_mass, "kg", "Final estimated mass"))
    else:
        # Basic volume
        vol_mm3 = L * W * H
        vol_m3 = vol_mm3 * 1e-9
        mass_kg = vol_m3 * density
        calcs.append(_calc("Bounding Volume", "V = L × W × H",
                            vol_mm3, "mm³", f"{L}×{W}×{H}"))
        calcs.append(_calc("Estimated Mass", "m = V × ρ",
                            mass_kg, "kg", f"Density = {density} kg/m³ ({mat_type})"))

        # Hole deductions
        holes_desc = str(params.get("has_holes", "no"))
        hole_vol = 0
        if holes_desc.lower() not in ("no", "none", ""):
            # Try to parse "3 holes, 10mm diameter" or similar
            import re
            nums = re.findall(r'(\d+\.?\d*)', holes_desc)
            if len(nums) >= 2:
                n_holes = int(float(nums[0]))
                d_hole = float(nums[1])
                hole_depth = min(H, 25)  # assume through-hole up to thickness
                single_hole = math.pi * (d_hole/2)**2 * hole_depth
                hole_vol = single_hole * n_holes
                calcs.append(_calc("Hole Volume Deduction",
                                    f"{n_holes} holes × π(d/2)²×h",
                                    hole_vol, "mm³",
                                    f"d={d_hole}mm, depth={hole_depth}mm"))

        net_vol = vol_mm3 - hole_vol
        net_mass = net_vol * 1e-9 * density
        calcs.append(_calc("Net Volume", "V_net = V_bound - V_holes",
                            net_vol, "mm³", "After subtracting holes"))
        calcs.append(_calc("Net Mass", "m_net = V_net × ρ",
                            net_mass, "kg", "Final estimated mass"))

    # Tolerance info
    tol = str(params.get("tolerance", "general"))
    if "tight" in tol.lower() or "0.05" in tol:
        recommendations.append("Tight tolerance (±0.05mm): CNC machining required, grinding recommended")
    elif "precision" in tol.lower() or "0.1" in tol:
        recommendations.append("Precision tolerance (±0.1mm): CNC machining recommended")

    # Surface finish
    finish = str(params.get("surface_finish", "as-machined"))
    if "polished" in finish.lower():
        recommendations.append("Polished finish: additional polishing operation needed, increases cost")
    elif "ground" in finish.lower():
        recommendations.append("Ground finish: surface grinding operation required")

    # Load condition notes
    load = str(params.get("load_conditions", "static"))
    if "dynamic" in load.lower() or "impact" in load.lower():
        warnings.append("Dynamic/impact loading: consider fatigue analysis and stress concentration factors")
        recommendations.append("Add generous fillets (R≥2mm) at all sharp corners to reduce stress concentration")

    qty = int(float(params.get("quantity", 1)))
    if qty > 100:
        recommendations.append(f"Batch of {qty}: consider casting or stamping for cost optimization")

    return {
        "calculations": calcs,
        "dimensions": {
            "length_mm": L, "width_mm": W, "height_mm": H,
            "net_volume_mm3": round(net_vol, 1),
            "net_mass_kg": round(net_mass, 4),
        },
        "safety": {
            "fos_actual": None,
            "fos_required": None,
            "is_safe": len(warnings) == 0,
            "warnings": warnings,
            "recommendations": recommendations,
        },
        "standards": [
            "ISO 2768 — General Tolerances",
            "ISO 1302 — Surface Texture",
            "ISO 286-1 — Limits and Fits",
        ],
        "material": {"name": mat_type.title(), "density_kg_m3": density},
        "custom_params": params,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════
ENGINES = {
    "shaft": calculate_shaft,
    "bearing": calculate_bearing,
    "gearbox": calculate_gearbox,
    "cam": calculate_cam,
    "custom": calculate_custom,
}


def run_calculation(component_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run the math engine for a given component type and parameters."""
    engine = ENGINES.get(component_type)
    if not engine:
        raise ValueError(f"Unknown component type: {component_type}")
    return engine(params)

