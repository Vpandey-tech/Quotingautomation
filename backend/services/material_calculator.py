"""
Raw Material Calculator — Industry-Standard Envelope-Based Costing

Implements the senior's exact logic:
  1. Take finished part dimensions (X, Y, Z bounding box)
  2. Add machining allowances (surface, kerf, grip)
  3. Calculate Gross Envelope Volume
  4. Match to next standard stock size (Machinery's Handbook)
  5. Calculate weight using density
  6. Apply 5% scrap factor

Logic Flow:
  Input: Part Dimensions (X, Y, Z)
  → Part Dimension + Machining Allowance = Minimum Envelope
  → Lookup: Query "Standard Stock Table" → find Next Size Up
  → Result: Use THAT weight for cost, not the part weight

References:
  - Machinery's Handbook 32nd Edition (2024)
  - EngineersEdge.com material density standards
"""

import math

try:
    from services.stock_sizes import find_next_stock_size, STANDARD_BAR_LENGTH_MM
except ImportError:
    from stock_sizes import find_next_stock_size, STANDARD_BAR_LENGTH_MM


# ── Machining Allowance Constants (per senior's specification) ───────────────
SURFACE_ALLOWANCE_MM = 3.0      # 3mm added to diameter/thickness per side for cleanup
SAW_KERF_MM          = 4.0      # 4mm per cut for saw blade loss
END_GRIP_MM          = 50.0     # 50mm per 3-meter bar for machine chucking/remnant
# Note: End grip is applied per bar, not per part. If multiple parts are cut
# from one bar, the grip is amortized across all parts from that bar.

# ── Scrap Factor (per senior's specification) ────────────────────────────────
SCRAP_FACTOR = 0.05  # 5% for material handling losses


def calculate_raw_material(
    size_x_mm: float,
    size_y_mm: float,
    size_z_mm: float,
    density_g_cm3: float,
    quantity: int,
    stock_type: str = "round_bar",
    surface_allowance_mm: float = SURFACE_ALLOWANCE_MM,
    saw_kerf_mm: float = SAW_KERF_MM,
    end_grip_mm: float = END_GRIP_MM,
    scrap_factor: float = SCRAP_FACTOR,
    part_volume_mm3: float = 0.0,
) -> dict:
    """
    Calculate raw material weight and cost using industry-standard
    envelope-based methodology.

    Args:
        size_x_mm: Finished part length (X dimension) in mm
        size_y_mm: Finished part width (Y dimension) in mm
        size_z_mm: Finished part height/thickness (Z dimension) in mm
        density_g_cm3: Material density in g/cm³
        quantity: Number of parts in the batch
        stock_type: "round_bar", "plate", "hex_bar"
        surface_allowance_mm: Cleanup allowance per side (default 3mm)
        saw_kerf_mm: Material lost per saw cut (default 4mm)
        end_grip_mm: Chucking remnant per bar (default 50mm)
        scrap_factor: Material handling scrap (default 0.05 = 5%)
        part_volume_mm3: Exact part volume for utilization calc (0 = use envelope)

    Returns:
        dict with complete material estimation breakdown
    """
    # Ensure minimum dimensions (prevent division by zero)
    size_x = max(size_x_mm, 0.1)
    size_y = max(size_y_mm, 0.1)
    size_z = max(size_z_mm, 0.1)
    qty = max(quantity, 1)

    if stock_type == "round_bar":
        result = _calc_round_bar(
            size_x, size_y, size_z, density_g_cm3, qty,
            surface_allowance_mm, saw_kerf_mm, end_grip_mm, scrap_factor,
            part_volume_mm3,
        )
    elif stock_type == "hex_bar":
        result = _calc_hex_bar(
            size_x, size_y, size_z, density_g_cm3, qty,
            surface_allowance_mm, saw_kerf_mm, end_grip_mm, scrap_factor,
            part_volume_mm3,
        )
    elif stock_type == "plate":
        result = _calc_plate(
            size_x, size_y, size_z, density_g_cm3, qty,
            surface_allowance_mm, saw_kerf_mm, scrap_factor,
            part_volume_mm3,
        )
    else:
        # Default to round bar
        result = _calc_round_bar(
            size_x, size_y, size_z, density_g_cm3, qty,
            surface_allowance_mm, saw_kerf_mm, end_grip_mm, scrap_factor,
            part_volume_mm3,
        )

    return result


def _calc_round_bar(
    x, y, z, density, qty,
    surface_allow, kerf, grip, scrap,
    part_vol,
):
    """
    Round bar stock calculation.
    
    The cross-section (diameter) is determined by the larger of Y and Z
    plus surface allowance on both sides.
    The length is determined by X plus kerf.
    End grip is amortized based on how many parts can be cut from one bar.
    """
    # ── Step 1: Required cross-section diameter ──────────────────────────────
    max_cross_section = max(y, z)
    required_diameter = max_cross_section + (2 * surface_allow)  # Both sides

    # ── Step 2: Match to next standard stock size ────────────────────────────
    standard_diameter = find_next_stock_size(required_diameter, "round_bar")

    # ── Step 3: Required length per part (including kerf) ────────────────────
    part_cut_length = x + (2 * surface_allow) + kerf

    # ── Step 4: Calculate parts per bar and grip amortization ────────────────
    usable_bar_length = STANDARD_BAR_LENGTH_MM - grip
    parts_per_bar = max(1, math.floor(usable_bar_length / part_cut_length))
    bars_needed = math.ceil(qty / parts_per_bar)

    # Effective length per part including amortized grip
    grip_per_part = grip / parts_per_bar
    effective_length_per_part = part_cut_length + grip_per_part

    # ── Step 5: Gross Envelope Volume per part ───────────────────────────────
    radius_mm = standard_diameter / 2.0
    envelope_volume_mm3 = math.pi * (radius_mm ** 2) * effective_length_per_part

    # ── Step 6: Weight calculation ───────────────────────────────────────────
    envelope_volume_cm3 = envelope_volume_mm3 / 1000.0
    gross_weight_per_part_kg = (envelope_volume_cm3 * density / 1000.0) * (1 + scrap)
    total_batch_weight_kg = gross_weight_per_part_kg * qty

    # ── Step 7: Material utilization percentage ──────────────────────────────
    if part_vol > 0:
        finished_volume_mm3 = part_vol
    else:
        # Estimate: assume part fills ~60% of bounding box for rough estimate
        finished_volume_mm3 = x * y * z * 0.6
    
    material_utilization_pct = (finished_volume_mm3 / envelope_volume_mm3) * 100 if envelope_volume_mm3 > 0 else 0

    return {
        "stock_type": "round_bar",
        "stock_type_name": "Round Bar",

        # Input dimensions
        "finished_dimensions": {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)},

        # Machining allowances applied
        "allowances": {
            "surface_allowance_mm": surface_allow,
            "saw_kerf_mm": kerf,
            "end_grip_mm": grip,
            "scrap_factor_pct": round(scrap * 100, 1),
        },

        # Envelope calculation
        "required_diameter_mm": round(required_diameter, 2),
        "standard_diameter_mm": round(standard_diameter, 2),
        "required_length_mm": round(part_cut_length, 2),
        "effective_length_mm": round(effective_length_per_part, 2),
        "envelope_volume_mm3": round(envelope_volume_mm3, 2),
        "envelope_volume_cm3": round(envelope_volume_cm3, 4),

        # Bar usage
        "bar_length_mm": STANDARD_BAR_LENGTH_MM,
        "parts_per_bar": parts_per_bar,
        "bars_needed": bars_needed,

        # Weight output (per senior's requirement)
        "gross_weight_per_part_kg": round(gross_weight_per_part_kg, 4),
        "total_batch_weight_kg": round(total_batch_weight_kg, 4),
        "material_utilization_pct": round(material_utilization_pct, 1),

        # For cost calculation
        "raw_stock_kg": round(gross_weight_per_part_kg, 4),
    }


def _calc_hex_bar(
    x, y, z, density, qty,
    surface_allow, kerf, grip, scrap,
    part_vol,
):
    """
    Hex bar stock calculation.
    
    Hex bar is specified by "across flats" (AF) dimension.
    The circumscribed circle diameter is AF × 2/√3.
    We need the AF to encompass the max cross-section + allowance.
    """
    max_cross_section = max(y, z)
    required_af = max_cross_section + (2 * surface_allow)
    standard_af = find_next_stock_size(required_af, "hex_bar")

    part_cut_length = x + (2 * surface_allow) + kerf

    usable_bar_length = STANDARD_BAR_LENGTH_MM - grip
    parts_per_bar = max(1, math.floor(usable_bar_length / part_cut_length))
    bars_needed = math.ceil(qty / parts_per_bar)
    grip_per_part = grip / parts_per_bar
    effective_length_per_part = part_cut_length + grip_per_part

    # Hex cross-section area = (3√3 / 2) × (AF/2)² = (3√3 / 8) × AF²
    hex_area_mm2 = (3 * math.sqrt(3) / 8.0) * (standard_af ** 2)
    envelope_volume_mm3 = hex_area_mm2 * effective_length_per_part
    envelope_volume_cm3 = envelope_volume_mm3 / 1000.0

    gross_weight_per_part_kg = (envelope_volume_cm3 * density / 1000.0) * (1 + scrap)
    total_batch_weight_kg = gross_weight_per_part_kg * qty

    if part_vol > 0:
        finished_volume_mm3 = part_vol
    else:
        finished_volume_mm3 = x * y * z * 0.6

    material_utilization_pct = (finished_volume_mm3 / envelope_volume_mm3) * 100 if envelope_volume_mm3 > 0 else 0

    return {
        "stock_type": "hex_bar",
        "stock_type_name": "Hex Bar",
        "finished_dimensions": {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)},
        "allowances": {
            "surface_allowance_mm": surface_allow,
            "saw_kerf_mm": kerf,
            "end_grip_mm": grip,
            "scrap_factor_pct": round(scrap * 100, 1),
        },
        "required_af_mm": round(required_af, 2),
        "standard_af_mm": round(standard_af, 2),
        "required_length_mm": round(part_cut_length, 2),
        "effective_length_mm": round(effective_length_per_part, 2),
        "envelope_volume_mm3": round(envelope_volume_mm3, 2),
        "envelope_volume_cm3": round(envelope_volume_cm3, 4),
        "bar_length_mm": STANDARD_BAR_LENGTH_MM,
        "parts_per_bar": parts_per_bar,
        "bars_needed": bars_needed,
        "gross_weight_per_part_kg": round(gross_weight_per_part_kg, 4),
        "total_batch_weight_kg": round(total_batch_weight_kg, 4),
        "material_utilization_pct": round(material_utilization_pct, 1),
        "raw_stock_kg": round(gross_weight_per_part_kg, 4),
    }


def _calc_plate(
    x, y, z, density, qty,
    surface_allow, kerf, scrap,
    part_vol,
):
    """
    Plate / Flat bar stock calculation.
    
    For plates, the thickness is the critical dimension that must match
    a standard stock size. Width and length are cut to size.
    No end grip for plates (they are cut from sheet/plate).
    """
    # Thickness = smallest of Y or Z (the narrow dimension)
    # Width = the other dimension
    # Length = X
    thickness = min(y, z)
    width = max(y, z)

    required_thickness = thickness + (2 * surface_allow)
    required_width = width + (2 * surface_allow)
    required_length = x + (2 * surface_allow) + kerf

    standard_thickness = find_next_stock_size(required_thickness, "plate")
    standard_width = find_next_stock_size(required_width, "flat_width")

    envelope_volume_mm3 = required_length * standard_width * standard_thickness
    envelope_volume_cm3 = envelope_volume_mm3 / 1000.0

    gross_weight_per_part_kg = (envelope_volume_cm3 * density / 1000.0) * (1 + scrap)
    total_batch_weight_kg = gross_weight_per_part_kg * qty

    if part_vol > 0:
        finished_volume_mm3 = part_vol
    else:
        finished_volume_mm3 = x * y * z * 0.6

    material_utilization_pct = (finished_volume_mm3 / envelope_volume_mm3) * 100 if envelope_volume_mm3 > 0 else 0

    return {
        "stock_type": "plate",
        "stock_type_name": "Plate / Flat Bar",
        "finished_dimensions": {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)},
        "allowances": {
            "surface_allowance_mm": surface_allow,
            "saw_kerf_mm": kerf,
            "end_grip_mm": 0,
            "scrap_factor_pct": round(scrap * 100, 1),
        },
        "required_thickness_mm": round(required_thickness, 2),
        "standard_thickness_mm": round(standard_thickness, 2),
        "required_width_mm": round(required_width, 2),
        "standard_width_mm": round(standard_width, 2),
        "required_length_mm": round(required_length, 2),
        "envelope_volume_mm3": round(envelope_volume_mm3, 2),
        "envelope_volume_cm3": round(envelope_volume_cm3, 4),
        "bar_length_mm": 0,
        "parts_per_bar": 0,
        "bars_needed": 0,
        "gross_weight_per_part_kg": round(gross_weight_per_part_kg, 4),
        "total_batch_weight_kg": round(total_batch_weight_kg, 4),
        "material_utilization_pct": round(material_utilization_pct, 1),
        "raw_stock_kg": round(gross_weight_per_part_kg, 4),
    }
