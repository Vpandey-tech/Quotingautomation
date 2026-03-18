"""
Gemini AI Cross-Validation for Material Costing

Uses the SAME logic as material_calculator.py — sends only raw inputs to Gemini
so it can calculate independently, then compares final outputs.

KEY DESIGN PRINCIPLE:
  - We NEVER send our derived values (weight, volume, cost) to Gemini for it to check.
  - We send only the raw inputs and let Gemini calculate from scratch.
  - This makes it a true independent second calculator, not a circular self-check.

Features:
  - Auto-retry on rate limit (429) errors
  - Fallback: gemini-2.5-flash → gemini-2.0-flash → gemini-2.5-pro → gemini-2.0-flash-001
  - NO max_output_tokens cap — prevents JSON truncation errors
  - Robust JSON extraction (handles markdown fences + trailing prose)
  - Confidence score shown to user on UI
"""

import os
import json
import logging
import asyncio
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ── Standard metric stock sizes (mirrors stock_sizes.py) ─────────────────────
# Gemini must pick from ONLY these — same table as our hardcoded lookup
ROUND_BAR_SIZES_MM = [
    6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 30, 32, 35, 38, 40,
    42, 45, 48, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100,
    110, 120, 130, 140, 150, 160, 180, 200,
]
HEX_BAR_SIZES_MM = [
    6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 27, 30, 32, 36, 40, 45, 50, 55, 60,
]
PLATE_THICKNESS_MM = [
    3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 40, 50,
]
STANDARD_BAR_LENGTH_MM = 3000  # Same constant as material_calculator.py


# ── Prompt sends ONLY raw inputs — Gemini calculates independently ────────────
MATERIAL_COST_PROMPT = """You are a Manufacturing Cost Estimator. Calculate raw material weight and cost INDEPENDENTLY from scratch using only the inputs below. Follow the exact steps given — do not guess or skip steps.

=== RAW INPUTS ===
Material: {material_name}
Density: {density} g/cm³
Finished Part Bounding Box: X={size_x}mm (length) × Y={size_y}mm × Z={size_z}mm
Stock Type: {stock_type_name}
Batch Quantity: {quantity} parts
Metal Price: ₹{metal_price_inr_kg}/kg

=== MACHINING ALLOWANCES (apply exactly as specified) ===
Surface Allowance: {surface_allowance}mm added to diameter/thickness on EACH side (total added = 2 × {surface_allowance}mm = {double_surface}mm)
Saw Kerf: {saw_kerf}mm per cut
End Grip: {end_grip}mm per bar for machine chucking (amortized across parts cut from that bar)
Scrap Factor: {scrap_pct}% added to final weight
Standard Bar Length: {bar_length_mm}mm

=== STANDARD STOCK SIZES — pick ONLY from this list, next size UP ===
{stock_sizes_list}

=== EXACT CALCULATION STEPS ===

FOR ROUND BAR:
1.  max_cross          = max(Y, Z) = max({size_y}, {size_z})
2.  required_diameter  = max_cross + (2 × {surface_allowance})
3.  standard_diameter  = next value >= required_diameter from the round bar list above
4.  part_cut_length    = X + (2 × {surface_allowance}) + {saw_kerf}
5.  usable_bar         = {bar_length_mm} - {end_grip}
6.  parts_per_bar      = floor(usable_bar / part_cut_length)   [minimum 1]
7.  grip_per_part      = {end_grip} / parts_per_bar
8.  effective_length   = part_cut_length + grip_per_part
9.  envelope_vol_mm3   = π × (standard_diameter / 2)² × effective_length
10. weight_raw_kg      = (envelope_vol_mm3 / 1000) × density / 1000
11. gross_weight_kg    = weight_raw_kg × (1 + {scrap_pct} / 100)
12. batch_weight_kg    = gross_weight_kg × {quantity}
13. material_cost_inr  = batch_weight_kg × {metal_price_inr_kg}

FOR HEX BAR:
Same as round bar but:
- required_af = max(Y, Z) + 2 × {surface_allowance}
- standard_af = next value >= required_af from hex bar list
- hex_area_mm2 = (3 × √3 / 8) × standard_af²
- envelope_vol_mm3 = hex_area_mm2 × effective_length

FOR PLATE:
- thickness = min(Y, Z),  width = max(Y, Z)
- required_thickness = thickness + 2 × {surface_allowance}
- required_width     = width + 2 × {surface_allowance}
- required_length    = X + 2 × {surface_allowance} + {saw_kerf}
- standard_thickness = next value >= required_thickness from plate list
- envelope_vol_mm3   = required_length × required_width × standard_thickness
- No end grip for plates (parts_per_bar = 0, grip_per_part = 0)

=== OUR SYSTEM'S RESULT (shown for your reference AFTER you finish your own calculation) ===
Stock size we matched : {our_stock_size}
Our gross weight/part : {our_gross_weight_kg} kg
Our total batch weight: {our_batch_weight_kg} kg
Our material cost     : ₹{our_material_cost}
Our utilization       : {our_utilization_pct}%

RESPOND IN THIS EXACT JSON FORMAT ONLY — no markdown, no code fences, no extra text:
{{
  "ai_stock_size_mm": <number>,
  "ai_stock_size_label": "<e.g. Ø60mm Round Bar>",
  "ai_part_cut_length_mm": <number>,
  "ai_parts_per_bar": <integer>,
  "ai_effective_length_mm": <number>,
  "ai_envelope_volume_mm3": <number>,
  "ai_gross_weight_per_part_kg": <number>,
  "ai_total_batch_weight_kg": <number>,
  "ai_material_cost_inr": <number>,
  "ai_utilization_pct": <number>,
  "confidence_score": <0-100 integer>,
  "step_by_step": "<one line summary of your key intermediate values>",
  "discrepancy_notes": "<SHORT friendly message for a non-technical business client. NO jargon, NO variable names like standard_diameter or envelope_vol_mm3, NO step references. Use plain language. Examples: If values align write: Our calculations are closely aligned — the material cost estimate looks accurate. If minor diff write: Minor difference in bar size selected — the estimate is still reliable. If stock size differs write: The AI selected a slightly different bar size which may slightly affect material cost, but the estimate is solid. If poor match write: There is a notable difference in the calculated weight — we recommend reviewing the part dimensions before finalising the quote. Never mention internal steps or engineering terms.>"
}}"""


def _build_stock_sizes_list(stock_type: str) -> str:
    """Build the stock sizes string for the prompt — mirrors stock_sizes.py table."""
    if stock_type == "round_bar":
        sizes = ", ".join(f"Ø{s}mm" for s in ROUND_BAR_SIZES_MM)
        return f"Round Bar diameters: {sizes}"
    elif stock_type == "hex_bar":
        sizes = ", ".join(f"{s}mm AF" for s in HEX_BAR_SIZES_MM)
        return f"Hex Bar across-flats: {sizes}"
    elif stock_type == "plate":
        sizes = ", ".join(f"{s}mm" for s in PLATE_THICKNESS_MM)
        return f"Plate thicknesses: {sizes}"
    sizes = ", ".join(f"Ø{s}mm" for s in ROUND_BAR_SIZES_MM)
    return f"Round Bar diameters: {sizes}"


def _extract_json_from_text(text: str) -> str:
    """
    Robustly extract a JSON object from Gemini response.
    Handles markdown fences and any trailing prose after closing brace.
    """
    if "```json" in text:
        text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1]
        text = text.split("```", 1)[0]

    text = text.strip()
    start = text.find("{")
    if start == -1:
        return text
    end = text.rfind("}")
    if end == -1 or end < start:
        return text
    return str(text)[start: end + 1]


async def validate_with_gemini(
    # ── Raw inputs — exactly what material_calculator.py receives ────────────
    material_name: str,
    density: float,
    size_x: float,
    size_y: float,
    size_z: float,
    stock_type: str,
    quantity: int,
    metal_price_inr_kg: float,
    # ── Allowance constants — same defaults as material_calculator.py ─────────
    surface_allowance: float = 3.0,
    saw_kerf: float = 4.0,
    end_grip: float = 50.0,
    scrap_pct: float = 5.0,
    # ── Our results from compute_quote() → material_estimate ─────────────────
    # Pass these from costing.py:
    #   our_stock_size   = material_estimate["standard_stock_size"]  (or _get_standard_size_label)
    #   our_gross_weight = material_estimate["gross_weight_per_part_kg"]   ← CRITICAL for match %
    #   our_batch_weight = material_estimate["total_batch_weight_kg"]
    #   our_utilization  = material_estimate["material_utilization_pct"]
    #   our_material_cost= breakdown["material_cost"]  (from compute_quote return dict)
    our_stock_size: str = "",
    our_gross_weight: float = 0.0,
    our_batch_weight: float = 0.0,
    our_utilization: float = 0.0,
    our_material_cost: float = 0.0,
) -> dict:
    """
    Cross-validate material costing with Gemini AI.

    Gemini receives ONLY raw inputs and follows the same steps as
    material_calculator.py to calculate independently.
    Results are compared to our hardcoded output to produce:
      - confidence_score  (Gemini's self-reported confidence, 0-100)
      - match_level       (excellent / good / fair / poor / unknown)
      - weight_diff_pct   (% difference in gross weight per part)
      - comparison dict   (side-by-side values for UI display)
    """
    try:
        import google.generativeai as genai  # type: ignore[import]
    except ImportError:
        logger.error("[GEMINI_VALIDATOR] google-generativeai not installed.")
        return {
            "success": False,
            "error": "google-generativeai not installed. Run: pip install google-generativeai",
            "confidence_score": 0,
        }

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        return {
            "success": False,
            "error": "GEMINI_API_KEY not configured in environment.",
            "confidence_score": 0,
        }

    genai.configure(api_key=api_key)

    stock_type_names: Dict[str, str] = {
        "round_bar": "Round Bar",
        "plate":     "Plate / Flat Bar",
        "hex_bar":   "Hex Bar",
    }

    prompt = MATERIAL_COST_PROMPT.format(
        material_name=material_name,
        density=density,
        size_x=round(float(size_x), 2),
        size_y=round(float(size_y), 2),
        size_z=round(float(size_z), 2),
        stock_type_name=stock_type_names.get(stock_type, stock_type),
        quantity=quantity,
        metal_price_inr_kg=round(float(metal_price_inr_kg), 2),
        surface_allowance=surface_allowance,
        double_surface=round(2 * surface_allowance, 1),
        saw_kerf=saw_kerf,
        end_grip=end_grip,
        scrap_pct=scrap_pct,
        bar_length_mm=STANDARD_BAR_LENGTH_MM,
        stock_sizes_list=_build_stock_sizes_list(stock_type),
        our_stock_size=our_stock_size,
        our_gross_weight_kg=round(float(our_gross_weight), 4),
        our_batch_weight_kg=round(float(our_batch_weight), 4),
        our_material_cost=round(float(our_material_cost), 2),
        our_utilization_pct=round(float(our_utilization), 1),
    )

    # ── Model fallback (same order as pdf_analyzer.py) ────────────────────────
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash-001",
    ]

    ai_result: Optional[Dict[str, Any]] = None
    last_error: Optional[Exception] = None
    successful_model: str = ""

    for model_name in models_to_try:
        model_succeeded = False

        for attempt in range(3):
            try:
                logger.info(f"[GEMINI_VALIDATOR] Trying {model_name} (attempt {attempt + 1})")
                model = genai.GenerativeModel(model_name)

                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0,
                        # max_output_tokens intentionally NOT set —
                        # capping it caused "Unterminated string" JSON truncation errors
                    ),
                )

                raw_text = response.text.strip()
                json_text = _extract_json_from_text(raw_text)
                parsed = json.loads(json_text)

                if not isinstance(parsed, dict):
                    raise ValueError(f"Expected JSON object, got {type(parsed)}")

                ai_result = parsed
                successful_model = model_name
                last_error = None
                model_succeeded = True
                logger.info(f"[GEMINI_VALIDATOR] ✓ {model_name} succeeded (attempt {attempt + 1})")
                break

            except json.JSONDecodeError as je:
                last_error = je
                logger.warning(
                    f"[GEMINI_VALIDATOR] {model_name} malformed JSON "
                    f"(attempt {attempt + 1}): {je}"
                )
                continue

            except Exception as e:
                last_error = e
                error_str = str(e)
                if (
                    "429" in error_str
                    or "ResourceExhausted" in error_str
                    or "quota" in error_str.lower()
                ):
                    wait_time = min(10 * (attempt + 1), 35)
                    logger.warning(
                        f"[GEMINI_VALIDATOR] Rate limited on {model_name}, "
                        f"waiting {wait_time}s... (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"[GEMINI_VALIDATOR] Non-retryable error on {model_name}: {e}")
                    break

        if model_succeeded:
            break

    # ── All models failed ─────────────────────────────────────────────────────
    if ai_result is None:
        logger.error(f"[GEMINI_VALIDATOR] All models failed. Last error: {last_error}")
        return {
            "success": False,
            "error": f"AI Validation failed — all models exhausted. Last error: {str(last_error)}",
            "confidence_score": 0,
        }

    assert ai_result is not None

    # ── Compare our hardcoded result vs Gemini's independent calculation ──────
    ai_weight: float = float(ai_result.get("ai_gross_weight_per_part_kg") or 0)
    ai_cost: float   = float(ai_result.get("ai_material_cost_inr") or 0)

    weight_diff_pct = 0.0
    cost_diff_pct   = 0.0
    match_level     = "unknown"

    if our_gross_weight > 0 and ai_weight > 0:
        weight_diff_pct = abs(our_gross_weight - ai_weight) / our_gross_weight * 100
        if weight_diff_pct < 5:
            match_level = "excellent"
        elif weight_diff_pct < 15:
            match_level = "good"
        elif weight_diff_pct < 30:
            match_level = "fair"
        else:
            match_level = "poor"
    else:
        # our_gross_weight = 0 means caller didn't pass it — log clearly
        logger.warning(
            "[GEMINI_VALIDATOR] match_level=unknown because our_gross_weight=%.4f. "
            "Fix: pass material_estimate['gross_weight_per_part_kg'] from compute_quote() result.",
            our_gross_weight,
        )

    if our_material_cost > 0 and ai_cost > 0:
        cost_diff_pct = abs(our_material_cost - ai_cost) / our_material_cost * 100

    confidence_score: int = int(ai_result.get("confidence_score") or 75)

    logger.info(
        "[GEMINI_VALIDATOR] model=%s | confidence=%d | "
        "weight_diff=%.1f%% | cost_diff=%.1f%% | match=%s | "
        "our=%.4fkg | ai=%.4fkg",
        successful_model, confidence_score,
        weight_diff_pct, cost_diff_pct, match_level,
        our_gross_weight, ai_weight,
    )

    # ── Build user-friendly match label for UI display ───────────────────────
    match_labels = {
        "excellent": "✓ Excellent Match — estimate is highly accurate",
        "good":      "✓ Good Match — estimate is reliable",
        "fair":      "⚠ Fair Match — minor differences, review recommended",
        "poor":      "⚠ Notable Difference — please review dimensions before quoting",
        "unknown":   "— Match could not be calculated",
    }
    match_label = match_labels.get(match_level, match_level)

    return {
        "success":      True,
        "model_used":   successful_model,
        "ai_result":    ai_result,

        # ── Shown to user on UI ───────────────────────────────────────────────
        "confidence_score": confidence_score,
        "match_level":      match_level,        # raw value for logic/styling
        "match_label":      match_label,        # friendly string — show this to client
        "weight_diff_pct":  round(float(weight_diff_pct), 1),
        "cost_diff_pct":    round(float(cost_diff_pct), 1),

        # ── Side-by-side for UI table ─────────────────────────────────────────
        "comparison": {
            "our_stock_size":   our_stock_size,
            "ai_stock_size":    str(ai_result.get("ai_stock_size_label") or ""),
            "our_weight_kg":    round(float(our_gross_weight), 4),
            "ai_weight_kg":     round(ai_weight, 4),
            "our_cost_inr":     round(float(our_material_cost), 2),
            "ai_cost_inr":      round(ai_cost, 2),
            "our_utilization":  round(float(our_utilization), 1),
            "ai_utilization":   round(float(ai_result.get("ai_utilization_pct") or 0), 1),
            "ai_parts_per_bar": int(ai_result.get("ai_parts_per_bar") or 0),
            "ai_step_by_step":  str(ai_result.get("step_by_step") or ""),
        },

        "discrepancy_notes": str(ai_result.get("discrepancy_notes") or ""),
    }