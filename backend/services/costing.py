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
PROCESS_RATES = {
    "cnc_turning": {
        "name":       "CNC Turning",
        "rate_hr":    62.0,
        "setup_usd":  100.0,
        "axes":       2,
    },
    "cnc_milling_2ax": {
        "name":       "CNC Milling (2-Axis)",
        "rate_hr":    62.0,       # Same rate as CNC Turning per senior's instruction
        "setup_usd":  100.0,
        "axes":       2,
    },
    "cnc_milling_3ax": {
        "name":       "CNC Milling (3-Axis)",
        "rate_hr":    75.0,
        "setup_usd":  150.0,
        "axes":       3,
    },
    "cnc_milling_5ax": {
        "name":       "CNC Milling (5-Axis)",
        "rate_hr":    150.0,
        "setup_usd":  300.0,
        "axes":       5,
    },
    "swiss_machining": {
        "name":       "Swiss Machining",
        "rate_hr":    110.0,
        "setup_usd":  250.0,
        "axes":       5,
    },
    "edm_wire": {
        "name":       "EDM Wire Cutting",
        "rate_hr":    90.0,
        "setup_usd":  180.0,
        "axes":       2,
    },
    "laser_cutting": {
        "name":       "Laser Cutting",
        "rate_hr":    85.0,
        "setup_usd":  80.0,
        "axes":       2,
    },
    "injection_molding": {
        "name":       "Injection Molding",
        "rate_hr":    45.0,
        "setup_usd":  5000.0,
        "axes":       0,
    },
    "fdm_3d_print": {
        "name":       "3D Printing (FDM)",
        "rate_hr":    18.0,
        "setup_usd":  25.0,
        "axes":       0,
    },
    "sla_3d_print": {
        "name":       "3D Printing (SLA/Resin)",
        "rate_hr":    28.0,
        "setup_usd":  45.0,
        "axes":       0,
    },
    "dmls_metal_print": {
        "name":       "Metal 3D Printing (DMLS)",
        "rate_hr":    120.0,
        "setup_usd":  200.0,
        "axes":       0,
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

# ── Business parameters (unchanged per senior) ───────────────────────────────
OVERHEAD_RATE = 0.18   # 18% overhead
PROFIT_MARGIN = 0.22   # 22% profit margin
GST_RATE      = 0.18   # 18% GST (9% SGST + 9% CGST)


def compute_quote(
    geometry:       dict,
    material_id:    str,
    process_ids:    list,
    tolerance_id:   str,
    quantity:        int,
    metal_price_inr: float,    # INR/kg — already converted via Section A
    exchange_rate:   float,    # USD → INR rate for machine rate conversion
    surface_treatment_ids: list = None,
    profit_margin_pct: float = 22.0, # e.g. 22.0 = 22%
    include_setup_cost: bool = True,  # Senior Req: toggle setup cost
    hole_count_override: int = -1,    # Senior Req: -1 = use detected, >=0 = override
    stock_type: str = "round_bar",    # Senior Req: stock type for material calc
) -> dict:
    """
    Full cost calculation in INR using envelope-based material costing.

    Machine rates are converted inside this function using Section B formula:
      INR/hr = (USD/hr ÷ 10) × exchange_rate × 1.5

    Senior's enhancements:
      - Envelope-based material weight from standard stock sizes
      - Setup cost include/exclude toggle
      - Hole count override for user accuracy
      - Material utilization percentage output
    """
    if not surface_treatment_ids:
        surface_treatment_ids = []

    mat  = MATERIALS[material_id]
    tol  = TOLERANCE_MULTIPLIERS[tolerance_id]

    volume_mm3  = safe_float(geometry.get("volume"), 0.0)
    surface_mm2 = safe_float(geometry.get("surfaceArea"), 0.0)
    complexity  = geometry.get("complexity", {})
    comp_tier   = complexity.get("tier", "Simple") if isinstance(complexity, dict) else "Simple"

    # ── Rule: if > 5 processes, force Very Complex ─────────────────────────────
    if len(process_ids) >= 5:
        comp_tier = "Very Complex"

    # ── Get bounding box dimensions ──────────────────────────────────────────
    bb = geometry.get("boundingBox", {})
    size_x = safe_float(bb.get("sizeX"), 1.0)
    size_y = safe_float(bb.get("sizeY"), 1.0)
    size_z = safe_float(bb.get("sizeZ"), 1.0)

    # ── ENVELOPE-BASED Material Calculation (Senior's Core Requirement) ──────
    # This replaces the old volume-based calculation.
    # Logic: Part Dimension + Machining Allowance → Standard Stock Size → Weight
    material_estimate = calculate_raw_material(
        size_x_mm=size_x,
        size_y_mm=size_y,
        size_z_mm=size_z,
        density_g_cm3=mat["density"],
        quantity=quantity,
        stock_type=stock_type,
        part_volume_mm3=volume_mm3,
    )

    # Use the envelope-based raw stock weight (NOT part weight)
    raw_stock_kg = material_estimate["raw_stock_kg"]
    mat_cost_unit = raw_stock_kg * metal_price_inr

    # Keep part mass for informational display
    volume_cm3 = max(volume_mm3 / 1000.0, 0.001)
    part_mass_kg = volume_cm3 * mat["density"] / 1000.0

    # ── Hole count handling (Senior Req: user override) ──────────────────────
    holes = geometry.get("holes", [])
    if hole_count_override >= 0:
        # User has overridden the hole count
        if hole_count_override == 0:
            effective_holes = []
        elif hole_count_override <= len(holes):
            effective_holes = holes[:hole_count_override]
        else:
            # User says more holes than detected — replicate average hole params
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
                # No holes detected but user says there are — use default 6mm through hole
                for _ in range(hole_count_override):
                    effective_holes.append({"diameter": 6.0, "depth": 10.0, "type": "through"})
    else:
        effective_holes = holes

    effective_hole_count = len(effective_holes)

    # ── Machining Time & Cost Estimation (Loop over processes) ────────────────
    total_machining_hr = 0.0
    total_mach_cost_unit = 0.0
    total_setup_inr = 0.0
    total_drill_cost = 0.0

    mfg_processes = []

    for process_id in process_ids:
        if process_id not in PROCESS_RATES:
            continue
        proc = PROCESS_RATES[process_id]
        mfg_processes.append(proc["name"])
        
        proc_rate_inr = convert_machine_rate(proc["rate_hr"], exchange_rate)
        total_setup_inr += convert_setup_fee(proc["setup_usd"], exchange_rate)

        if proc["axes"] == 0:
            # NON-SUBTRACTIVE
            if "fdm" in process_id:
                fill_rate_cm3_hr = 57.6
            elif "sla" in process_id:
                fill_rate_cm3_hr = 25.5
            elif "dmls" in process_id:
                fill_rate_cm3_hr = 8.0
            elif "injection" in process_id:
                fill_rate_cm3_hr = 120.0
            else:
                fill_rate_cm3_hr = 30.0
            machining_hr = volume_cm3 / fill_rate_cm3_hr
        else:
            # SUBTRACTIVE (CNC) — use envelope volume for stock removal calculation
            envelope_vol_cm3 = material_estimate.get("envelope_volume_cm3", volume_cm3 * 1.3)
            stock_removal_cm3 = max(envelope_vol_cm3 - volume_cm3, volume_cm3 * 0.15)

            eff_mrr = mat["mrr_cm3_hr"] * mat["machinability"]
            machining_hr = stock_removal_cm3 / max(eff_mrr, 1.0)
            
            # Distribute stock removal across CNC processes
            machining_hr = machining_hr / sum(1 for p in process_ids if PROCESS_RATES.get(p, {}).get("axes", 0) > 0)

            finish_hr = (surface_mm2 / 10000.0) * mat["finish_factor"] * 0.05
            machining_hr += finish_hr

        # ── Apply complexity & tolerance multipliers per process ───────────────
        comp_mult   = COMPLEXITY_MULTIPLIERS.get(comp_tier, 1.0)
        tol_mult    = tol["multiplier"]
        adj_mach_hr = machining_hr * comp_mult * tol_mult
        
        total_machining_hr += adj_mach_hr
        total_mach_cost_unit += adj_mach_hr * proc_rate_inr

        # ── Hole drilling surcharge (INR) ONLY IF first subtractive process ──
        if proc["axes"] > 0 and effective_holes and total_drill_cost == 0.0:
            for hole in effective_holes:
                d = safe_float(hole.get("diameter"), 1.0)
                depth = safe_float(hole.get("depth"), d)
                h_type = hole.get("type", "through")
                depth_factor = 1.5 if h_type == "blind" else 1.0
                total_drill_cost += 2.0 * depth_factor * (depth / max(d, 1)) * (proc_rate_inr / 60.0)

    # ── Setup cost (amortised over quantity, INR) — CONDITIONAL ──────────────
    if include_setup_cost:
        setup_per_unit = total_setup_inr / max(quantity, 1)
    else:
        setup_per_unit = 0.0

    # ── Subtotal per unit ─────────────────────────────────────────────────────
    subtotal_unit = mat_cost_unit + total_mach_cost_unit + total_drill_cost + setup_per_unit

    # ── Overhead + Profit ─────────────────────────────────────────────────────
    overhead_unit = subtotal_unit * OVERHEAD_RATE
    # Profit calculated dynamically based on user input
    profit_margin_val = max(15.0, min(30.0, profit_margin_pct)) / 100.0
    profit_unit   = (subtotal_unit + overhead_unit) * profit_margin_val
    total_unit    = subtotal_unit + overhead_unit + profit_unit

    # ── Quantity discount (unchanged) ─────────────────────────────────────────
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

    # ── GST Calculation ──────────────────────────────────────────────────────
    sgst = total_order * 0.09
    cgst = total_order * 0.09
    grand_total = total_order + sgst + cgst

    # ── Manufacturing processes description ──────────────────────────────────
    if effective_hole_count > 0 and "Drilling" not in mfg_processes:
        mfg_processes.append("Drilling")
        
    for st_id in surface_treatment_ids:
        mfg_processes.append(st_id.replace("_", " ").title())

    return {
        "material":     mat["name"],
        "process":      ", ".join(mfg_processes),
        "tolerance":    tol["label"],
        "complexity":   comp_tier,
        "quantity":     quantity,
        "metal_price_inr_kg": round(metal_price_inr, 2),
        "exchange_rate":      round(exchange_rate, 2),
        "machine_rate_inr_hr": round(proc_rate_inr, 2) if 'proc_rate_inr' in locals() else 0.0,

        # Per-unit breakdown (INR)
        "breakdown": {
            "material_cost":    round(mat_cost_unit,    2),
            "machining_cost":   round(total_mach_cost_unit,   2),
            "drilling_cost":    round(total_drill_cost,       2),
            "setup_cost":       round(setup_per_unit,   2),
            "overhead":         round(overhead_unit,    2),
            "profit_margin":    round(profit_unit,      2),
        },

        "unit_price":            round(total_unit,       2),
        "unit_price_discounted": round(total_unit_discounted, 2),
        "discount_pct":          round(discount_pct * 100, 1),
        "order_total":           round(total_order,      2),

        # GST (INR)
        "sgst_rate":   9.0,
        "cgst_rate":   9.0,
        "sgst":        round(sgst, 2),
        "cgst":        round(cgst, 2),
        "grand_total": round(grand_total, 2),

        # Derived — part info
        "mass_kg":              round(part_mass_kg,     4),
        "machining_hours":      round(total_machining_hr,      3),
        "holes_count":          effective_hole_count,
        "manufacturing_processes": mfg_processes,
        "currency":             "INR",

        # ── NEW: Senior's envelope-based material estimation outputs ─────────
        "include_setup_cost":   include_setup_cost,
        "stock_type":           material_estimate.get("stock_type", stock_type),
        "stock_type_name":      material_estimate.get("stock_type_name", "Round Bar"),
        "material_estimate": {
            "gross_weight_per_part_kg": material_estimate["gross_weight_per_part_kg"],
            "total_batch_weight_kg":    material_estimate["total_batch_weight_kg"],
            "material_utilization_pct": material_estimate["material_utilization_pct"],
            "envelope_volume_mm3":      material_estimate.get("envelope_volume_mm3", 0),
            "standard_stock_size":      _get_standard_size_label(material_estimate),
            "parts_per_bar":            material_estimate.get("parts_per_bar", 0),
            "bars_needed":              material_estimate.get("bars_needed", 0),
            "allowances":               material_estimate.get("allowances", {}),
        },
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
