"""
Standard Stock Size Lookup — Reference: Machinery's Handbook 32nd Ed. (2024)

Provides standard metric stock sizes for:
  - Round Bars (EN 10060 / ISO 1035-1)
  - Flat Bars / Plates (EN 10058 / ISO 1035-4)
  - Hex Bars (EN 10061)

Functions:
  find_next_stock_size(required_dim_mm, stock_type) → standard size in mm
  get_stock_table(stock_type) → list of standard sizes
"""

# ── Standard Metric Round Bar Diameters (mm) ─────────────────────────────────
# Sources: EN 10060, ISO 1035-1, Machinery's Handbook Table 4-1
# Covers cold-drawn bright bar and hot-rolled bar stock commonly used in CNC
ROUND_BAR_DIAMETERS = [
    3, 4, 5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
    21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
    32, 34, 35, 36, 38, 40,
    42, 45, 48, 50,
    52, 55, 56, 58, 60,
    63, 65, 68, 70,
    72, 75, 78, 80,
    82, 85, 88, 90,
    92, 95, 98, 100,
    105, 110, 115, 120,
    125, 130, 135, 140,
    145, 150, 155, 160,
    165, 170, 175, 180,
    185, 190, 195, 200,
    210, 220, 230, 240, 250,
    260, 270, 280, 290, 300,
    310, 320, 330, 340, 350,
    360, 370, 380, 390, 400,
    410, 420, 430, 440, 450,
    460, 470, 480, 490, 500,
]

# ── Standard Metric Flat Bar / Plate Thicknesses (mm) ────────────────────────
# Sources: EN 10058, EN 10029 (plates), Machinery's Handbook Table 4-3
# Standard plate thicknesses used in CNC milling / waterjet / laser
PLATE_THICKNESSES = [
    1.0, 1.2, 1.5, 1.6, 2.0, 2.5, 3.0,
    3.5, 4.0, 4.5, 5.0, 5.5, 6.0,
    7.0, 8.0, 9.0, 10.0,
    11.0, 12.0, 13.0, 14.0, 15.0,
    16.0, 18.0, 20.0,
    22.0, 25.0, 28.0, 30.0,
    32.0, 35.0, 38.0, 40.0,
    42.0, 45.0, 48.0, 50.0,
    55.0, 60.0, 65.0, 70.0,
    75.0, 80.0, 85.0, 90.0,
    95.0, 100.0,
    110.0, 120.0, 130.0, 140.0, 150.0,
    160.0, 170.0, 180.0, 190.0, 200.0,
]

# ── Standard Metric Flat Bar Widths (mm) ─────────────────────────────────────
# Sources: EN 10058, Machinery's Handbook Table 4-3
FLAT_BAR_WIDTHS = [
    10, 12, 15, 16, 18, 20,
    22, 25, 28, 30,
    32, 35, 38, 40,
    42, 45, 48, 50,
    55, 60, 65, 70, 75, 80,
    85, 90, 95, 100,
    110, 120, 125, 130, 140, 150,
    160, 170, 180, 190, 200,
    220, 250, 280, 300,
    320, 350, 380, 400,
    450, 500,
]

# ── Standard Metric Hex Bar Sizes (Across Flats, mm) ────────────────────────
# Sources: EN 10061, Machinery's Handbook Table 4-6
HEX_BAR_AF = [
    5, 6, 7, 8, 9, 10,
    11, 12, 13, 14, 15, 16, 17,
    18, 19, 20, 21, 22, 23, 24, 25,
    26, 27, 28, 29, 30,
    32, 34, 35, 36, 38, 40,
    41, 42, 45, 46, 48, 50,
    52, 55, 56, 58, 60,
    63, 65, 68, 70,
    72, 75, 78, 80,
    82, 85, 90, 95, 100,
]

# ── Standard Bar Lengths (mm) ───────────────────────────────────────────────
# Standard purchased bar stock comes in 3-meter (3000mm) or 6-meter lengths
STANDARD_BAR_LENGTH_MM = 3000.0
LONG_BAR_LENGTH_MM = 6000.0


def find_next_stock_size(required_dim_mm: float, stock_type: str = "round_bar") -> float:
    """
    Given a required minimum dimension (in mm), find the next available
    standard stock size >= required_dim_mm.

    Args:
        required_dim_mm: Minimum required dimension after adding machining allowances
        stock_type: One of "round_bar", "plate", "flat_width", "hex_bar"

    Returns:
        The next standard size in mm that is >= required_dim_mm.
        If required_dim_mm exceeds all standard sizes, returns required_dim_mm
        rounded up to the nearest 10mm (custom order territory).
    """
    table_map = {
        "round_bar":  ROUND_BAR_DIAMETERS,
        "plate":      PLATE_THICKNESSES,
        "flat_width": FLAT_BAR_WIDTHS,
        "hex_bar":    HEX_BAR_AF,
    }

    table = table_map.get(stock_type, ROUND_BAR_DIAMETERS)

    for size in table:
        if size >= required_dim_mm:
            return float(size)

    # Beyond standard range — round up to nearest 10mm (custom forging/casting)
    import math
    return float(math.ceil(required_dim_mm / 10.0) * 10.0)


def get_stock_table(stock_type: str = "round_bar") -> list:
    """Return the full list of standard sizes for the given stock type."""
    table_map = {
        "round_bar":  ROUND_BAR_DIAMETERS,
        "plate":      PLATE_THICKNESSES,
        "flat_width": FLAT_BAR_WIDTHS,
        "hex_bar":    HEX_BAR_AF,
    }
    return [float(s) for s in table_map.get(stock_type, ROUND_BAR_DIAMETERS)]


def get_all_stock_types() -> list:
    """Return metadata for all stock types."""
    return [
        {"id": "round_bar",  "name": "Round Bar",   "unit": "Diameter (mm)"},
        {"id": "plate",      "name": "Plate / Flat", "unit": "Thickness (mm)"},
        {"id": "flat_width", "name": "Flat Bar Width", "unit": "Width (mm)"},
        {"id": "hex_bar",    "name": "Hex Bar",      "unit": "Across Flats (mm)"},
    ]
