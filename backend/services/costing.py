"""
Costing Engine — Phase 4 (INR Edition)

Formula:
  C_total = C_material + C_machining + C_drilling + C_setup + C_overhead + C_profit
  + GST (SGST 9% + CGST 9%)

All outputs are in INR (₹).
Machine rates and material prices are converted from USD using:
  Section A (materials): INR = (USD/kg × rate) + ₹150
  Section B (machines):  INR = (USD/hr ÷ 10) × rate × 1.5

Changes from Phase 3:
  - Added CNC Milling 2-Axis (same rate as CNC Turning)
  - All outputs in INR
  - GST calculation (SGST 9% + CGST 9%)
  - Surface Treatment, Logistics, Engineering Charges line items
"""

import math
try:
    from services.pricing import MATERIALS
    from services.currency import convert_material_price, convert_machine_rate, convert_setup_fee
except ImportError:
    from pricing import MATERIALS
    from currency import convert_material_price, convert_machine_rate, convert_setup_fee


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
SCRAP_RATE    = 0.12   # 12% material scrap
OVERHEAD_RATE = 0.18   # 18% overhead
PROFIT_MARGIN = 0.22   # 22% profit margin
GST_RATE      = 0.18   # 18% GST (9% SGST + 9% CGST)


def compute_quote(
    geometry:       dict,
    material_id:    str,
    process_id:     str,
    tolerance_id:   str,
    quantity:        int,
    metal_price_inr: float,    # INR/kg — already converted via Section A
    exchange_rate:   float,    # USD → INR rate for machine rate conversion
) -> dict:
    """
    Full cost calculation in INR.

    Machine rates are converted inside this function using Section B formula:
      INR/hr = (USD/hr ÷ 10) × exchange_rate × 1.5
    """
    mat  = MATERIALS[material_id]
    proc = PROCESS_RATES[process_id]
    tol  = TOLERANCE_MULTIPLIERS[tolerance_id]

    # Convert machine rate and setup fee to INR (Section B)
    proc_rate_inr = convert_machine_rate(proc["rate_hr"], exchange_rate)
    setup_inr     = convert_setup_fee(proc["setup_usd"], exchange_rate)

    volume_mm3  = float(geometry.get("volume", 0))
    surface_mm2 = float(geometry.get("surfaceArea", 0))
    complexity  = geometry.get("complexity", {})
    comp_tier   = complexity.get("tier", "Simple") if isinstance(complexity, dict) else "Simple"

    # ── Volume conversions ────────────────────────────────────────────────────
    volume_cm3 = max(volume_mm3 / 1000.0, 0.001)

    # ── Material Cost (INR) ──────────────────────────────────────────────────
    mass_kg       = volume_cm3 * mat["density"] / 1000.0
    raw_stock_kg  = mass_kg * (1 + SCRAP_RATE)
    mat_cost_unit = raw_stock_kg * metal_price_inr

    # ── Machining Time Estimation ─────────────────────────────────────────────
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
        # SUBTRACTIVE (CNC)
        bb = geometry.get("boundingBox", {})
        if bb and bb.get("sizeX") and bb.get("sizeY") and bb.get("sizeZ"):
            bbox_vol_cm3 = (
                float(bb["sizeX"]) * float(bb["sizeY"]) * float(bb["sizeZ"])
            ) / 1000.0
            stock_removal_cm3 = max(bbox_vol_cm3 - volume_cm3, volume_cm3 * 0.15)
        else:
            stock_removal_cm3 = volume_cm3 * 0.30

        eff_mrr = mat["mrr_cm3_hr"] * mat["machinability"]
        machining_hr = stock_removal_cm3 / max(eff_mrr, 1.0)

        finish_hr = (surface_mm2 / 10000.0) * mat["finish_factor"] * 0.05
        machining_hr += finish_hr

    # ── Apply complexity & tolerance multipliers ──────────────────────────────
    comp_mult   = COMPLEXITY_MULTIPLIERS.get(comp_tier, 1.0)
    tol_mult    = tol["multiplier"]
    adj_mach_hr = machining_hr * comp_mult * tol_mult

    # C_machining = Machining Time × Machine Rate (INR)
    mach_cost_unit = adj_mach_hr * proc_rate_inr

    # ── Hole drilling surcharge (INR) ─────────────────────────────────────────
    holes = geometry.get("holes", [])
    drill_cost = 0.0
    for hole in holes:
        d = float(hole.get("diameter", 1))
        depth = float(hole.get("depth", d))
        h_type = hole.get("type", "through")
        depth_factor = 1.5 if h_type == "blind" else 1.0
        drill_cost += 2.0 * depth_factor * (depth / max(d, 1)) * (proc_rate_inr / 60.0)

    # ── Setup cost (amortised over quantity, INR) ─────────────────────────────
    setup_per_unit = setup_inr / max(quantity, 1)

    # ── Subtotal per unit ─────────────────────────────────────────────────────
    subtotal_unit = mat_cost_unit + mach_cost_unit + drill_cost + setup_per_unit

    # ── Overhead + Profit ─────────────────────────────────────────────────────
    overhead_unit = subtotal_unit * OVERHEAD_RATE
    profit_unit   = (subtotal_unit + overhead_unit) * PROFIT_MARGIN
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
    mfg_processes = [proc["name"]]
    if len(holes) > 0:
        mfg_processes.append("Drilling")

    return {
        "material":     mat["name"],
        "process":      proc["name"],
        "tolerance":    tol["label"],
        "complexity":   comp_tier,
        "quantity":     quantity,
        "metal_price_inr_kg": round(metal_price_inr, 2),
        "exchange_rate":      round(exchange_rate, 2),
        "machine_rate_inr_hr": round(proc_rate_inr, 2),

        # Per-unit breakdown (INR)
        "breakdown": {
            "material_cost":    round(mat_cost_unit,    2),
            "machining_cost":   round(mach_cost_unit,   2),
            "drilling_cost":    round(drill_cost,       2),
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

        # Derived
        "mass_kg":              round(mass_kg,          4),
        "machining_hours":      round(adj_mach_hr,      3),
        "holes_count":          len(holes),
        "manufacturing_processes": mfg_processes,
        "currency":             "INR",
    }
