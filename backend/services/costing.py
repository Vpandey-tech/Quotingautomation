"""
Costing Engine — Phase 3 (v2)

Aligned with Gemini algorithm conversation flow:
  Stage 1: CAD Ingestion & Preparation     → handled by frontend OCCT loader
  Stage 2: Feature Recognition             → handled by CadQuery backend (/api/analyze)
  Stage 3: Process Selection               → user selects, algorithm validates
  Stage 4: Cost Calculation (this module)   → Material + Machining + Setup + Overhead + Profit
  Stage 5: Quotation Generation            → PDF output via pdf.py

Formula:
  C_total = C_material + C_machining + C_drilling + C_setup + C_overhead + C_profit

Material Cost:
  mass_kg = volume_cm3 × density_g_cm3 / 1000
  C_material = mass_kg × (1 + scrap_factor) × price_usd_kg

Machining Cost (CNC Subtractive):
  stock_removal = bbox_volume - part_volume  (Buy-to-Fly ratio)
  time_hr = stock_removal / (MRR × machinability)  +  finishing_time
  C_machining = time_hr × machine_rate × complexity × tolerance

Machining Cost (Additive / 3D Printing):
  FDM  target: ~$0.25/gram  →  fill_rate ≈ 58 cm³/hr at $18/hr
  SLA  target: ~$1.00/gram  →  fill_rate ≈ 25 cm³/hr at $28/hr

Reference machine rates (2026 industry average from Gemini conversation):
  CNC 3-Axis:  $40-$80/hr  (industry avg) → we use $75/hr
  CNC 5-Axis:  $100-$180/hr → we use $150/hr
  CNC Turning: $40-$70/hr   → we use $62/hr
  EDM Wire:    $70-$120/hr  → we use $90/hr
  FDM:         $18/hr
  SLA/Resin:   $28/hr
  Setup fees:  $50-$300 one-time per batch
"""

import math
try:
    from services.pricing import MATERIALS
except ImportError:
    from pricing import MATERIALS


# ── Machine rates (USD/hr) — aligned with 2026 industry averages ──────────────
PROCESS_RATES = {
    "cnc_turning": {
        "name":       "CNC Turning",
        "rate_hr":    62.0,
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
        "setup_usd":  5000.0,        # Tooling cost amortised
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
    "high":        {"label": "High Precision (±0.025 mm)",  "multiplier": 1.90},
    "ultra":       {"label": "Ultra Precision (±0.01 mm)",  "multiplier": 2.80},
}

# ── Complexity multipliers (fed by Phase 2 CadQuery analysis) ─────────────────
# Gemini ref: "Complexity Factor (k) that multiplies the base machine rate"
COMPLEXITY_MULTIPLIERS = {
    "Simple":       1.00,
    "Moderate":     1.25,
    "Complex":      1.65,
    "Very Complex": 2.40,
}

SCRAP_RATE    = 0.12   # 12% material scrap / bar stock wastage
OVERHEAD_RATE = 0.18   # 18% overhead (facility, utilities, QA)
PROFIT_MARGIN = 0.22   # 22% profit margin (15-30% range from Gemini)


def compute_quote(
    geometry:      dict,
    material_id:   str,
    process_id:    str,
    tolerance_id:  str,
    quantity:      int,
    metal_price:   float,        # USD/kg — from pricing service
) -> dict:
    """
    Stage 4: Full cost calculation following the Gemini algorithm flow.

    C_CNC = (Setup Time × R_labor) + (Machining Time × R_machine) + C_material
    C_total = C_CNC + C_drilling + C_overhead + C_profit
    """
    mat  = MATERIALS[material_id]
    proc = PROCESS_RATES[process_id]
    tol  = TOLERANCE_MULTIPLIERS[tolerance_id]

    volume_mm3  = float(geometry.get("volume", 0))
    surface_mm2 = float(geometry.get("surfaceArea", 0))
    complexity  = geometry.get("complexity", {})
    comp_tier   = complexity.get("tier", "Simple") if isinstance(complexity, dict) else "Simple"

    # ── Volume conversions ────────────────────────────────────────────────────
    volume_cm3  = max(volume_mm3 / 1000.0, 0.001)   # mm³ → cm³, guard against 0

    # ── Stage 2 → Material Cost ───────────────────────────────────────────────
    # mass_kg = Volume (cm³) × Density (g/cm³) / 1000
    mass_kg         = volume_cm3 * mat["density"] / 1000.0
    raw_stock_kg    = mass_kg * (1 + SCRAP_RATE)    # Add 12% scrap (bar/billet stock wastage)
    mat_cost_unit   = raw_stock_kg * metal_price

    # ── Stage 4 → Machining Time Estimation ───────────────────────────────────
    if proc["axes"] == 0:
        # ── NON-SUBTRACTIVE (Additive / Injection Molding) ────────────────────
        if "fdm" in process_id:
            # FDM: target $0.25/gram → fill_rate ≈ 57.6 cm³/hr at $18/hr
            fill_rate_cm3_hr = 57.6
        elif "sla" in process_id:
            # SLA: target $1.00/gram → fill_rate ≈ 25.5 cm³/hr at $28/hr
            fill_rate_cm3_hr = 25.5
        elif "dmls" in process_id:
            # DMLS Metal: very slow, $15-$50/gram → fill_rate ≈ 8 cm³/hr at $120/hr
            fill_rate_cm3_hr = 8.0
        elif "injection" in process_id:
            # Injection Molding: very fast cycle time once tooled
            # Cycle time ~ 30s for small parts → 120 cm³/hr effective
            fill_rate_cm3_hr = 120.0
        else:
            fill_rate_cm3_hr = 30.0  # Generic fallback
        machining_hr = volume_cm3 / fill_rate_cm3_hr
    else:
        # ── SUBTRACTIVE MANUFACTURING (CNC) ───────────────────────────────────
        # Buy-to-Fly ratio: stock_removal = bounding_box_vol - part_vol
        bb = geometry.get("boundingBox", {})
        if bb and bb.get("sizeX") and bb.get("sizeY") and bb.get("sizeZ"):
            bbox_vol_cm3 = (
                float(bb["sizeX"]) * float(bb["sizeY"]) * float(bb["sizeZ"])
            ) / 1000.0  # mm³ → cm³
            stock_removal_cm3 = max(bbox_vol_cm3 - volume_cm3, volume_cm3 * 0.15)
        else:
            # Fallback: assume 30% of part volume is removed
            stock_removal_cm3 = volume_cm3 * 0.30

        # Effective MRR adjusted by machinability
        # Gemini ref: SS304 takes 2.5× longer than Al 6061
        eff_mrr = mat["mrr_cm3_hr"] * mat["machinability"]
        machining_hr = stock_removal_cm3 / max(eff_mrr, 1.0)

        # Surface finishing pass (scales with surface area)
        finish_hr = (surface_mm2 / 10000.0) * mat["finish_factor"] * 0.05
        machining_hr += finish_hr

    # ── Apply complexity factor (k) and tolerance multiplier ──────────────────
    comp_mult   = COMPLEXITY_MULTIPLIERS.get(comp_tier, 1.0)
    tol_mult    = tol["multiplier"]
    adj_mach_hr = machining_hr * comp_mult * tol_mult

    # C_machining = Machining Time × Machine Rate
    mach_cost_unit = adj_mach_hr * proc["rate_hr"]

    # ── Hole drilling surcharge ───────────────────────────────────────────────
    holes = geometry.get("holes", [])
    drill_cost = 0.0
    for hole in holes:
        d = float(hole.get("diameter", 1))
        depth = float(hole.get("depth", d))
        h_type = hole.get("type", "through")
        # Deep blind holes cost more (retracting, chip clearing)
        depth_factor = 1.5 if h_type == "blind" else 1.0
        # Cost per hole ∝ depth/diameter ratio × machine rate per minute
        drill_cost += 2.0 * depth_factor * (depth / max(d, 1)) * (proc["rate_hr"] / 60.0)

    # ── Setup cost (amortised over quantity) ──────────────────────────────────
    # Gemini ref: Setup Fee $50-$300 one-time per batch
    setup_per_unit = proc["setup_usd"] / max(quantity, 1)

    # ── Subtotal per unit ─────────────────────────────────────────────────────
    subtotal_unit = mat_cost_unit + mach_cost_unit + drill_cost + setup_per_unit

    # ── Overhead + profit (Gemini ref: profit 15-30%, we use 22%) ─────────────
    overhead_unit = subtotal_unit * OVERHEAD_RATE
    profit_unit   = (subtotal_unit + overhead_unit) * PROFIT_MARGIN
    total_unit    = subtotal_unit + overhead_unit + profit_unit

    # ── Quantity discount ─────────────────────────────────────────────────────
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

    return {
        "material":     mat["name"],
        "process":      proc["name"],
        "tolerance":    tol["label"],
        "complexity":   comp_tier,
        "quantity":     quantity,
        "metal_price_usd_kg": round(metal_price, 4),

        # Per-unit breakdown
        "breakdown": {
            "material_cost":    round(mat_cost_unit,    2),
            "machining_cost":   round(mach_cost_unit,   2),
            "drilling_cost":    round(drill_cost,       2),
            "setup_cost":       round(setup_per_unit,   2),
            "overhead":         round(overhead_unit,    2),
            "profit_margin":    round(profit_unit,      2),
        },
        "unit_price":           round(total_unit,       2),
        "unit_price_discounted": round(total_unit_discounted, 2),
        "discount_pct":         round(discount_pct * 100, 1),
        "order_total":          round(total_order,      2),

        # Derived
        "mass_kg":              round(mass_kg,          4),
        "machining_hours":      round(adj_mach_hr,      3),
        "holes_count":          len(holes),
        "currency":             "USD",
    }
