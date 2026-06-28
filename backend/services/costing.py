"""
Costing Engine — Phase 5 (Envelope-Based Material + Senior Enhancements)

Formula:
  C_total = C_material + C_machining + C_drilling + C_setup + C_overhead + C_profit
  + GST (SGST 9% + CGST 9%)

All outputs are in INR (₹).
Machine rates and material prices are converted from USD using:
  Section A (materials): INR = (USD/kg × rate) + ₹150
  Section B (machines):  INR = (USD/hr ÷ 10) × rate × 1.5

Changes from Phase 4 (Senior's Requirements):
  - Envelope-based raw material weight (NOT part weight)
  - Standard stock size lookup (Machinery's Handbook)
  - 5% scrap factor for material handling
  - Setup cost include/exclude toggle
  - User-adjustable hole count override
  - Material utilization percentage in output
  - Gross weight per part and total batch weight in output
"""
import math
import re

def safe_float(val, default_val=0.0):
    """Safely convert any mixed string (e.g., '1/2\" BSP', '~10mm') to float by extracting the first numeric sequence."""
    try:
        if val is None:
            return float(default_val)
        return float(val)
    except (ValueError, TypeError):
        if isinstance(val, str):
            m = re.search(r"[-+]?\d*\.?\d+", val)
            if m:
                return float(m.group(0))
        return float(default_val)

try:
    from services.pricing import MATERIALS
    from services.currency import convert_material_price, convert_machine_rate, convert_setup_fee
    from services.material_calculator import calculate_raw_material
except ImportError:
    from pricing import MATERIALS
    from currency import convert_material_price, convert_machine_rate, convert_setup_fee
    from material_calculator import calculate_raw_material


# ── Machine rates (USD/hr) — source of truth in USD ──────────────────────────
# Values calibrated so that convert_machine_rate aligns with Indian job shop rates (₹/hr)
# Pune/Ahmedabad 2026 standards:
# CNC Milling 3ax: ~₹1000/hr, CNC Turning: ~₹850/hr, EDM: ~₹1500/hr, Injection Molding: ~₹2000/hr
PROCESS_RATES = {
    "cnc_turning": {
        "name":       "CNC Turning",
        "rate_hr":    66.0,       # ~₹850/hr
        "setup_usd":  100.0,
        "axes":       2,
        "category":   "subtractive"
    },
    "cnc_milling_2ax": {
        "name":       "CNC Milling (2-Axis)",
        "rate_hr":    62.0,       # ~₹800/hr
        "setup_usd":  100.0,
        "axes":       2,
        "category":   "subtractive"
    },
    "cnc_milling_3ax": {
        "name":       "CNC Milling (3-Axis)",
        "rate_hr":    78.0,       # ~₹1000/hr
        "setup_usd":  150.0,
        "axes":       3,
        "category":   "subtractive"
    },
    "cnc_milling_5ax": {
        "name":       "CNC Milling (5-Axis)",
        "rate_hr":    140.0,      # ~₹1800/hr
        "setup_usd":  300.0,
        "axes":       5,
        "category":   "subtractive"
    },
    "swiss_machining": {
        "name":       "Swiss Machining",
        "rate_hr":    117.0,      # ~₹1500/hr
        "setup_usd":  250.0,
        "axes":       5,
        "category":   "subtractive"
    },
    "edm_wire": {
        "name":       "EDM Wire Cutting",
        "rate_hr":    117.0,      # ~₹1500/hr
        "setup_usd":  150.0,
        "axes":       2,
        "category":   "subtractive"
    },
    "drilling_dro": {
        "name":       "Drilling/DRO",
        "rate_hr":    39.0,        # Exactly 50% of CNC Milling 3-Axis rate (78.0)
        "setup_usd":  75.0,        # Exactly 50% of CNC Milling 3-Axis setup (150.0)
        "axes":       2,
        "category":   "subtractive"
    },
    "laser_cutting": {
        "name":       "Laser Cutting",
        "rate_hr":    14.0,       # ~₹180/hr
        "setup_usd":  30.0,
        "axes":       2,
        "category":   "fabrication"
    },
    "waterjet_cutting": {
        "name":       "Waterjet Cutting",
        "rate_hr":    17.2,       # ~₹220/hr
        "setup_usd":  40.0,
        "axes":       2,
        "category":   "fabrication"
    },
    "sheet_metal_bending": {
        "name":       "Sheet Metal Bending",
        "rate_hr":    8.0,        # ~₹100/hr
        "setup_usd":  20.0,
        "axes":       0,
        "category":   "forming"
    },
    "injection_molding": {
        "name":       "Injection Molding",
        "rate_hr":    156.0,      # ~₹2000/hr
        "setup_usd":  1500.0,     # Amortized machine setup
        "axes":       0,
        "category":   "molding"
    },
    "fdm_3d_print": {
        "name":       "3D Printing (FDM)",
        "rate_hr":    19.5,       # ~₹250/hr
        "setup_usd":  10.0,
        "axes":       0,
        "category":   "additive"
    },
    "sla_3d_print": {
        "name":       "3D Printing (SLA/SLS)",
        "rate_hr":    27.3,       # ~₹350/hr
        "setup_usd":  15.0,
        "axes":       0,
        "category":   "additive"
    },
    "dmls_metal_print": {
        "name":       "Metal 3D Printing (DMLS)",
        "rate_hr":    120.0,      # ~₹1540/hr
        "setup_usd":  200.0,
        "axes":       0,
        "category":   "additive"
    },
    "surface_grinding": {
        "name":       "Surface Grinding",
        "rate_hr":    54.6,       # ~₹700/hr
        "setup_usd":  50.0,
        "axes":       2,
        "category":   "finishing"
    },
}

# ── Tolerance multipliers ─────────────────────────────────────────────────────
TOLERANCE_MULTIPLIERS = {
    "rough":       {"label": "Rough (±1.0 mm)",            "multiplier": 0.85},
    "standard":    {"label": "Standard (±0.5 mm)",         "multiplier": 1.00},
    "precision":   {"label": "Precision (±0.1 mm)",        "multiplier": 1.35},
    "high":        {"label": "High Precision (±0.025 mm)", "multiplier": 1.90},
    "ultra":       {"label": "Ultra Precision (±0.01 mm)", "multiplier": 2.80},
}

# ── Complexity multipliers ────────────────────────────────────────────────────
COMPLEXITY_MULTIPLIERS = {
    "Simple":       1.00,
    "Moderate":     1.25,
    "Complex":      1.65,
    "Very Complex": 2.40,
}

# ── Business parameters ───────────────────────────────────────────────────────
OVERHEAD_RATE = 0.18   # 18% overhead
PROFIT_MARGIN = 0.22   # 22% profit margin
GST_RATE      = 0.18   # 18% GST (9% SGST + 9% CGST)

# ── Regional Cost Indices (Step 7.3) ──────────────────────────────────────────
REGIONAL_INDICES = {
    "pune":      {"labor": 1.00, "machine": 1.00, "material": 1.00},
    "ahmedabad": {"labor": 0.95, "machine": 0.95, "material": 0.98},
    "mumbai":    {"labor": 1.15, "machine": 1.10, "material": 1.05},
    "chennai":   {"labor": 1.05, "machine": 1.00, "material": 1.00},
    "bangalore": {"labor": 1.10, "machine": 1.05, "material": 1.02},
    "delhi":     {"labor": 1.05, "machine": 1.00, "material": 1.00},
}

# ── Surface Treatment Rates (INR/mm²) and Batch Minimum Charges ───────────────
SURFACE_TREATMENT_RATES = {
    "anodize_clear":      {"name": "Anodize (Clear)",       "rate_inr_mm2": 0.05, "min_charge_inr": 250.0},
    "anodize_black":      {"name": "Anodize (Black)",       "rate_inr_mm2": 0.06, "min_charge_inr": 250.0},
    "powder_coat":         {"name": "Powder Coating",        "rate_inr_mm2": 0.02, "min_charge_inr": 150.0},
    "bead_blast":          {"name": "Bead Blasting",         "rate_inr_mm2": 0.02, "min_charge_inr": 100.0},
    "passivation":         {"name": "Passivation",           "rate_inr_mm2": 0.015, "min_charge_inr": 150.0},
    "electroless_nickel": {"name": "Electroless Nickel",    "rate_inr_mm2": 0.08, "min_charge_inr": 300.0},
    "heat_treatment":      {"name": "Heat Treatment",        "rate_inr_kg": 60.0,  "min_charge_inr": 500.0}, # Weight-based
}


def compute_quote(
    geometry:       dict,
    material_id:    str,
    process_ids:    list,
    tolerance_id:   str,
    quantity:        int,
    metal_price_inr: float,    # INR/kg
    exchange_rate:   float,    # USD → INR rate
    surface_treatment_ids: list = None,
    profit_margin_pct: float = 22.0,
    include_setup_cost: bool = True,
    include_drilling_surcharge: bool = True,
    hole_count_override: int = -1,
    stock_type: str = "round_bar",
    region: str = "pune",
    bends_count: int = 0,
    bend_length_mm: float = 0.0,
) -> dict:
    """
    Full cost calculation in INR incorporating process-specific cost drivers,
    regional indices, and design constraints.
    """
    if not surface_treatment_ids:
        surface_treatment_ids = []

    mat  = MATERIALS[material_id]
    tol  = TOLERANCE_MULTIPLIERS[tolerance_id]

    volume_mm3  = safe_float(geometry.get("volume"), 0.0)
    surface_mm2 = safe_float(geometry.get("surfaceArea"), 0.0)
    complexity  = geometry.get("complexity", {})
    comp_tier   = complexity.get("tier", "Simple") if isinstance(complexity, dict) else "Simple"

    # Fetch regional index multipliers
    reg_index = REGIONAL_INDICES.get(region.lower(), {"labor": 1.0, "machine": 1.0, "material": 1.0})

    # Rule: if > 5 processes, force Very Complex
    if len(process_ids) >= 5:
        comp_tier = "Very Complex"

    bb = geometry.get("boundingBox", {})
    size_x = safe_float(bb.get("sizeX"), 1.0)
    size_y = safe_float(bb.get("sizeY"), 1.0)
    size_z = safe_float(bb.get("sizeZ"), 1.0)
    thickness = safe_float(geometry.get("thickness", min(size_x, size_y, size_z)), 1.0)
    perimeter = safe_float(geometry.get("perimeter", 2 * (size_x + size_y)), 1.0)

    # ── RAW MATERIAL CALCULATION ───────────────────────────────────────────────
    # Molding/Additive processes bypass stock size envelopes and utilize part volume directly
    is_additive_or_molding = any(pid in ["injection_molding", "fdm_3d_print", "sla_3d_print", "dmls_metal_print"] for pid in process_ids)

    if is_additive_or_molding:
        waste_factor = 0.05 if "injection_molding" in process_ids else 0.15
        net_weight_kg = (volume_mm3 / 1000.0) * mat["density"] / 1000.0
        gross_weight_kg = net_weight_kg * (1 + waste_factor)
        total_batch_weight_kg = gross_weight_kg * quantity
        mat_cost_unit = gross_weight_kg * metal_price_inr * reg_index["material"]
        part_mass_kg = net_weight_kg

        material_estimate = {
            "stock_type": "part_volume",
            "stock_type_name": "Liquid/Filament (Part Volume)",
            "finished_dimensions": {"x": round(size_x, 2), "y": round(size_y, 2), "z": round(size_z, 2)},
            "allowances": {
                "surface_allowance_mm": 0,
                "saw_kerf_mm": 0,
                "end_grip_mm": 0,
                "scrap_factor_pct": round(waste_factor * 100, 1),
            },
            "envelope_volume_mm3": round(volume_mm3, 2),
            "envelope_volume_cm3": round(volume_mm3 / 1000.0, 4),
            "gross_weight_per_part_kg": round(gross_weight_kg, 4),
            "total_batch_weight_kg": round(total_batch_weight_kg, 4),
            "material_utilization_pct": round((1 / (1 + waste_factor)) * 100, 1),
            "raw_stock_kg": round(gross_weight_kg, 4),
            "standard_stock_size": "Direct Volume Fill"
        }
    else:
        # standard envelope-based calculation
        material_estimate = calculate_raw_material(
            size_x_mm=size_x,
            size_y_mm=size_y,
            size_z_mm=size_z,
            density_g_cm3=mat["density"],
            quantity=quantity,
            stock_type=stock_type,
            part_volume_mm3=volume_mm3,
        )
        raw_stock_kg = material_estimate["raw_stock_kg"]
        mat_cost_unit = raw_stock_kg * metal_price_inr * reg_index["material"]
        volume_cm3 = max(volume_mm3 / 1000.0, 0.001)
        part_mass_kg = volume_cm3 * mat["density"] / 1000.0

    # ── Hole count handling (user override) ──────────────────────
    holes = geometry.get("holes", [])
    if hole_count_override >= 0:
        effective_hole_count = hole_count_override
        if hole_count_override == 0:
            effective_holes = []
        elif hole_count_override <= len(holes):
            effective_holes = holes[:hole_count_override]
        else:
            effective_holes = list(holes)
            if holes:
                avg_hole = {
                    "diameter": sum(safe_float(h.get("diameter", 5), 5) for h in holes) / len(holes),
                    "depth": sum(safe_float(h.get("depth", 5), 5) for h in holes) / len(holes),
                    "type": "through",
                }
                for _ in range(hole_count_override - len(holes)):
                    effective_holes.append(avg_hole)
            else:
                for _ in range(hole_count_override):
                    effective_holes.append({"diameter": 6.0, "depth": 10.0, "type": "through"})
    else:
        effective_holes = holes
        effective_hole_count = len(effective_holes)

    # ── Process specific costing ───────────────────────────────────────────────
    total_machining_hr = 0.0
    total_mach_cost_unit = 0.0
    total_setup_inr = 0.0
    total_drill_cost = 0.0

    mfg_processes = []
    comp_mult = COMPLEXITY_MULTIPLIERS.get(comp_tier, 1.0)
    tol_mult = tol["multiplier"]

    for process_id in process_ids:
        if process_id not in PROCESS_RATES:
            continue
        proc = PROCESS_RATES[process_id]
        mfg_processes.append(proc["name"])

        # Convert machine rate and setup rate incorporating regional index
        proc_rate_inr = convert_machine_rate(proc["rate_hr"], exchange_rate) * reg_index["machine"]
        total_setup_inr += convert_setup_fee(proc["setup_usd"], exchange_rate) * reg_index["labor"]

        machining_hr = 0.0
        volume_cm3 = volume_mm3 / 1000.0

        category = proc.get("category", "subtractive")

        if category == "additive":
            # 3D Printing time depends on volumes and layer speeds
            if "fdm" in process_id:
                fill_rate_cm3_hr = 57.6
            elif "sla" in process_id:
                fill_rate_cm3_hr = 25.5
            elif "dmls" in process_id:
                fill_rate_cm3_hr = 8.0
            else:
                fill_rate_cm3_hr = 30.0
            machining_hr = volume_cm3 / fill_rate_cm3_hr
        
        elif category == "molding":
            # Injection molding cycle time (in seconds)
            cycle_time = 25.0
            if comp_tier == "Moderate":
                cycle_time = 45.0
            elif comp_tier == "Complex":
                cycle_time = 75.0
            elif comp_tier == "Very Complex":
                cycle_time = 120.0
            # Amortized cycle hours per part
            machining_hr = cycle_time / 3600.0

        elif category == "fabrication":
            # Laser & Waterjet sheet cutting speed (mm/min)
            if process_id == "laser_cutting":
                # Real-world Indian laser cutting rate:
                # E.g. ~₹15-30/meter for thin sheets, up to ₹100-200/meter for thick plates.
                # If proc_rate_inr is ~₹180/hr, setting machining_hr = (perimeter * thickness * 0.0001)
                # results in a very accurate, market-aligned price:
                # For 2mm sheet, 1000mm perimeter: 0.2 hrs * 180 = ₹36
                # For 10mm plate, 1000mm perimeter: 1.0 hr * 180 = ₹180
                machining_hr = perimeter * max(thickness, 1.0) * 0.0001
                # Laser pierce surcharge: ₹5 per hole
                total_drill_cost += effective_hole_count * 5.0
            elif process_id == "waterjet_cutting":
                # Waterjet is slower and includes abrasive costs (~₹150/hr).
                # Setting machining_hr = (perimeter * thickness * 0.0003) results in:
                # For 10mm plate, 1000mm perimeter: 3.0 hrs * 220 = ₹660
                machining_hr = perimeter * max(thickness, 1.0) * 0.0003
                # Abrasive cost: ₹150 per hour
                total_drill_cost += machining_hr * 150.0

        elif process_id == "edm_wire":
            # Wire EDM Area cut rate (150 mm²/min)
            cut_area_mm2 = perimeter * thickness
            machining_hr = (cut_area_mm2 / 150.0) / 60.0

        elif process_id == "sheet_metal_bending":
            # Bending is costed per bend (₹80-120 per bend) rather than per hour.
            # With proc_rate_inr ~₹100/hr, we set 1.0 hour per bend to achieve a baseline of ~₹100/bend.
            # We also add a factor for bend length: 0.001 hour (₹0.10) per mm of bend length.
            machining_hr = (bends_count * 1.0) + (bend_length_mm * 0.001)

        elif process_id == "surface_grinding":
            # Grinding area speed (500,000 mm²/hr)
            machining_hr = surface_mm2 / 500000.0

        else:
            # Subtractive CNC Machining (Milling/Turning)
            envelope_vol_cm3 = material_estimate.get("envelope_volume_cm3", volume_cm3 * 1.3)
            stock_removal_cm3 = max(envelope_vol_cm3 - volume_cm3, volume_cm3 * 0.15)
            eff_mrr = mat["mrr_cm3_hr"] * mat["machinability"]
            machining_hr = stock_removal_cm3 / max(eff_mrr, 1.0)

            # Distribute machining time across multiple subtractive processes
            subtractive_count = sum(1 for p in process_ids if PROCESS_RATES.get(p, {}).get("category") == "subtractive")
            if subtractive_count > 0:
                machining_hr = machining_hr / subtractive_count

            finish_hr = (surface_mm2 / 10000.0) * mat["finish_factor"] * 0.05
            machining_hr += finish_hr

        # Adjust machining hour for complexity and tolerances
        adj_mach_hr = machining_hr * comp_mult * tol_mult
        total_machining_hr += adj_mach_hr
        total_mach_cost_unit += adj_mach_hr * proc_rate_inr

        # Setup cost per unit amortization
        if include_setup_cost:
            if category == "molding":
                # Mold tooling cost amortization
                mold_cost = 100000.0
                if comp_tier == "Moderate":
                    mold_cost = 250000.0
                elif comp_tier == "Complex":
                    mold_cost = 500000.0
                elif comp_tier == "Very Complex":
                    mold_cost = 800000.0
                # Add tooling amortization directly to setup
                total_setup_inr += mold_cost * reg_index["labor"]
            
            setup_per_part = total_setup_inr / max(quantity, 1)
        else:
            setup_per_part = 0.0

        # Subtractive drilling surcharge
        if include_drilling_surcharge and category == "subtractive" and effective_holes and total_drill_cost == 0.0:
            for hole in effective_holes:
                d = safe_float(hole.get("diameter"), 1.0)
                depth = safe_float(hole.get("depth"), d)
                h_type = hole.get("type", "through")
                depth_factor = 1.5 if h_type == "blind" else 1.0
                total_drill_cost += 2.0 * depth_factor * (depth / max(d, 1)) * (proc_rate_inr / 60.0)

    # ── Post-processing surface treatments costing ──────────────────────────────
    total_surface_treatment_cost_unit = 0.0
    for st_id in surface_treatment_ids:
        if st_id not in SURFACE_TREATMENT_RATES:
            continue
        st = SURFACE_TREATMENT_RATES[st_id]
        if st_id == "heat_treatment":
            cost = part_mass_kg * st["rate_inr_kg"]
        else:
            cost = (surface_mm2 * st["rate_inr_mm2"])
        
        # Batch minimum charge amortization
        unit_cost = max(cost * quantity, st["min_charge_inr"]) / quantity
        total_surface_treatment_cost_unit += unit_cost
        mfg_processes.append(st["name"])

    # ── Subtotal unit cost ─────────────────────────────────────────────────────
    subtotal_unit = mat_cost_unit + total_mach_cost_unit + total_drill_cost + setup_per_part + total_surface_treatment_cost_unit

    # ── Overhead + Profit ─────────────────────────────────────────────────────
    overhead_unit = subtotal_unit * OVERHEAD_RATE
    profit_margin_val = max(15.0, min(30.0, profit_margin_pct)) / 100.0
    profit_unit   = (subtotal_unit + overhead_unit) * profit_margin_val
    total_unit    = subtotal_unit + overhead_unit + profit_unit

    # Quantity discount logic
    if quantity >= 100:
        discount_pct = 0.15
    elif quantity >= 25:
        discount_pct = 0.08
    elif quantity >= 5:
        discount_pct = 0.03
    else:
        discount_pct = 0.0

    total_unit_discounted = total_unit * (1 - discount_pct)
    total_order = total_unit_discounted * quantity

    sgst = total_order * 0.09
    cgst = total_order * 0.09
    grand_total = total_order + sgst + cgst

    # ── DESIGN FOR MANUFACTURING (DFM) ENGINE ─────────────────────────────────
    dfm_warnings = []
    dfm_recommendations = []

    # 1. Wall thickness check
    min_dim = min(size_x, size_y, size_z)
    if "pla_plastic" in material_id or "abs_plastic" in material_id or "nylon_plastic" in material_id or "polycarbonate" in material_id:
        if min_dim < 1.0:
            dfm_warnings.append(f"Extremely thin wall thickness detected ({min_dim:.1f}mm). Recommend wall thickness above 1.0mm for plastics.")
    else:
        if min_dim < 1.5:
            dfm_warnings.append(f"Very thin sheet/wall thickness ({min_dim:.1f}mm) for machining. May cause warping or severe vibration.")

    # 2. Hole depth ratio check
    for h in effective_holes:
        hd = safe_float(h.get("diameter"), 1.0)
        hdepth = safe_float(h.get("depth"), 0.0)
        if hd > 0 and hdepth / hd > 10.0:
            dfm_warnings.append(f"Deep hole detected (Ø{hd:.1f} × {hdepth:.1f} depth). Ratio {hdepth/hd:.1f}x exceeds 10x. Requires slow feed or EDM.")
            break

    # 3. Fillet radii check (CNC pocket corners)
    subtractive_milling = any("milling" in pid for pid in process_ids)
    if subtractive_milling and surface_mm2 > 5000.0:
        dfm_recommendations.append("Ensure internal corners have fillet radii (min 1-2mm) to avoid requiring expensive Wire EDM or relief milling.")

    # 4. Tolerance check for additive/molded components
    if tolerance_id in ["high", "ultra"] and any(pid in ["fdm_3d_print", "sla_3d_print", "injection_molding"] for pid in process_ids):
        dfm_warnings.append("High/Ultra precision tolerances requested on 3D printed or molded parts. Secondary grinding or machining is recommended to achieve this accuracy.")

    # 5. Draft angle for injection molding
    if "injection_molding" in process_ids:
        dfm_recommendations.append("Apply a draft angle of 1.5° - 2.0° on all vertical walls for clean part ejection from the mold cavity.")

    # 6. Sheet metal bending thickness check
    if "sheet_metal_bending" in process_ids and thickness > 6.0:
        dfm_warnings.append(f"Sheet thickness of {thickness:.1f}mm is too high for standard bending operations. Max recommended thickness is 6.0mm.")

    return {
        "material":     mat["name"],
        "process":      ", ".join(mfg_processes),
        "tolerance":    tol["label"],
        "complexity":   comp_tier,
        "quantity":     quantity,
        "metal_price_inr_kg":  round(metal_price_inr, 2),
        "exchange_rate":       round(exchange_rate, 2),
        "machine_rate_inr_hr": round(proc_rate_inr, 2) if 'proc_rate_inr' in locals() else 0.0,

        "breakdown": {
            "material_cost":  round(mat_cost_unit,        2),
            "machining_cost": round(total_mach_cost_unit + total_surface_treatment_cost_unit, 2), # Combine machining + finishing
            "drilling_cost":  round(total_drill_cost,     2),
            "setup_cost":     round(setup_per_part,       2),
            "overhead":       round(overhead_unit,        2),
            "profit_margin":  round(profit_unit,          2),
        },

        "unit_price":            round(total_unit,            2),
        "unit_price_discounted": round(total_unit_discounted, 2),
        "discount_pct":          round(discount_pct * 100,    1),
        "order_total":           round(total_order,           2),
        "sgst_rate":   9.0,
        "cgst_rate":   9.0,
        "sgst":        round(sgst,        2),
        "cgst":        round(cgst,        2),
        "grand_total": round(grand_total, 2),

        "mass_kg":                 round(part_mass_kg,       4),
        "scrap_weight_kg":         max(0.0, round(material_estimate["gross_weight_per_part_kg"] - part_mass_kg, 4)),
        "machining_hours":         round(total_machining_hr, 3),
        "holes_count":             effective_hole_count,
        "manufacturing_processes": mfg_processes,
        "currency":                "INR",

        "include_setup_cost": include_setup_cost,
        "stock_type":         material_estimate.get("stock_type",      stock_type),
        "stock_type_name":    material_estimate.get("stock_type_name", "Round Bar"),
        "material_estimate":  material_estimate,
        "dfm_feedback":       {"warnings": dfm_warnings, "recommendations": dfm_recommendations},
        "region":             region,
        "bends_count":        bends_count,
        "bend_length_mm":     bend_length_mm,
    }



def _get_standard_size_label(estimate: dict) -> str:
    """Build a human-readable label for the matched standard stock size."""
    st = estimate.get("stock_type", "round_bar")
    if st == "round_bar":
        return f"Ø{estimate.get('standard_diameter_mm', 0)} mm Round Bar"
    elif st == "hex_bar":
        return f"{estimate.get('standard_af_mm', 0)} mm AF Hex Bar"
    elif st == "plate":
        return f"{estimate.get('standard_thickness_mm', 0)} × {estimate.get('standard_width_mm', 0)} mm Plate"
    return "N/A"