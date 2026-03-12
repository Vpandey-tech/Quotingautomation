"""
PDF Engineering Drawing Analyzer — powered by Google Gemini

Accepts a PDF file containing engineering drawings (isometric views,
orthographic projections, dimensions, BOMs) and extracts structured
data that can be used to generate a manufacturing quotation.

Features:
  - Auto-retry on rate limit (429) errors
  - Fallback from gemini-2.0-flash → gemini-1.5-flash
  - Structured JSON output compatible with quote engine
"""

import os
import json
import time
import tempfile
from typing import Optional


def _configure_gemini():
    """Configure and return Gemini model. Returns None if no API key."""
    try:
        import google.generativeai as genai
    except ImportError:
        print("[PDF_ANALYZER] google-generativeai not installed. Run: pip install google-generativeai")
        return None, None

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("[PDF_ANALYZER] GEMINI_API_KEY not set in .env")
        return None, None

    genai.configure(api_key=api_key)
    return genai, True


EXTRACTION_PROMPT = """You are an expert manufacturing engineer analyzing an engineering drawing PDF.
Your job is to extract ALL manufacturing-relevant information for creating a quotation.

Extract the following information for EACH part visible in the drawing:

1. Part name/description
2. ALL dimensions (length, width, height, diameter, radius, depth) in mm
3. Material specified (if any)
4. Tolerances mentioned (e.g., ±0.1 mm, H7, etc.)
5. Surface finish requirements (Ra values, plating, coating)
6. ALL holes: type (through/blind/threaded), diameter, depth, count
7. Weight if mentioned (in kg)
8. Quantity if mentioned
9. Manufacturing processes suggested or visible
10. Special notes, chamfers, fillets, threads (M6, M8, etc.)
11. Estimate the volume in mm³ from dimensions
12. Estimate the surface area in mm² from dimensions
13. Bounding box: sizeX, sizeY, sizeZ in mm

Return as valid JSON (no markdown, no code fences):
{
    "parts": [
        {
            "name": "Part Name",
            "description": "Brief description",
            "dimensions": {
                "length": 0, "width": 0, "height": 0,
                "diameter": 0, "radius": 0
            },
            "bounding_box": {"sizeX": 0, "sizeY": 0, "sizeZ": 0},
            "material": "material name or null",
            "material_id": "best matching ID from: aluminum_6061, aluminum_7075, stainless_steel_304, stainless_steel_316l, mild_steel, titanium_ti6al4v, copper, brass_360, inconel_718, tool_steel_d2, pla_plastic, abs_plastic — or null",
            "tolerance": "tolerance description or null",
            "tolerance_id": "best matching from: rough, standard, precision, high, ultra — or standard",
            "surface_finish": "finish description or null",
            "holes": [
                {"type": "through", "diameter": 0, "depth": 0, "count": 1}
            ],
            "weight_kg": null,
            "quantity": 1,
            "manufacturing_processes": ["turning", "milling", "drilling"],
            "process_id": "best matching from: cnc_turning, cnc_milling_2ax, cnc_milling_3ax, cnc_milling_5ax, swiss_machining, edm_wire, laser_cutting, injection_molding, fdm_3d_print, sla_3d_print, dmls_metal_print",
            "notes": "chamfers, threads, special requirements",
            "estimated_volume_mm3": 0,
            "estimated_surface_area_mm2": 0
        }
    ],
    "assembly_name": "Assembly name if this is part of an assembly, else null",
    "general_notes": "Any general drawing notes, title block info",
    "client_info": {
        "client_name": "Person name found in the PDF (from 'Prepared for', 'Customer', 'Client', 'Attention', 'To', title block, or any recipient name) or null",
        "client_company": "Company/organization name found in the PDF (from header, title block, 'Prepared for', 'Customer', 'Client', company logo text, or any business name) or null",
        "client_contact": "Any phone, email, or address found for the client, or null"
    },
    "title_block": {
        "drawing_number": "",
        "revision": "",
        "scale": "",
        "drawn_by": ""
    }
}

CRITICAL RULES — DO NOT HALLUCINATE:
- ONLY extract values that are EXPLICITLY VISIBLE in the drawing. If a dimension, material, tolerance, or any value is NOT written or shown in the PDF, set it to null or 0. NEVER guess or invent values.
- If you are unsure about any value, set it to null. It is better to leave a field null than to provide a wrong number.
- Dimensions MUST be read directly from dimension lines, callouts, or text in the drawing. If a dimension is not labeled, set it to 0.
- Material MUST only be filled if it is explicitly written in the drawing (e.g., "EN-8", "SS 304", "Al 6061"). Do NOT assume material from part appearance.
- Tolerance MUST only be filled if tolerance values are explicitly shown (e.g., "±0.1", "H7", "IT6").
- Holes MUST only be listed if they are visible in the drawing with diameter callouts. Do NOT invent holes.
- For cylindrical parts, calculate volume as pi * r^2 * length (only using dimensions FROM the drawing)
- For prismatic parts, calculate volume as length * width * height (only using dimensions FROM the drawing)
- Map materials to the closest material_id from the list provided
- If EN-8 or similar is mentioned, map to mild_steel
- If material is not specified, set material_id to null
- ALWAYS look for client/customer/company names in the PDF — title blocks, headers, "Prepared for", "Attention:", letterhead, addresses, etc. Extract them into client_info
- Return ONLY the JSON, no other text"""


async def analyze_pdf_drawing(pdf_bytes: bytes, filename: str) -> Optional[dict]:
    """
    Analyze a PDF engineering drawing using Google Gemini.

    Returns structured data with extracted parts, dimensions, materials,
    tolerances, holes, and manufacturing requirements.
    """
    genai, configured = _configure_gemini()
    if not configured:
        return None

    # Save PDF temporarily for Gemini upload
    tmp_path = None
    uploaded_file = None
    text = ""

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # Upload to Gemini
        uploaded_file = genai.upload_file(tmp_path, mime_type="application/pdf")

        # Try models in order of preference with retry
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-001"
        ]
        last_error = None

        for model_name in models_to_try:
            for attempt in range(3):  # Up to 3 retries per model
                try:
                    print(f"[PDF_ANALYZER] Trying {model_name} (attempt {attempt + 1})")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content([EXTRACTION_PROMPT, uploaded_file])
                    text = response.text.strip()
                    last_error = None
                    break  # Success — exit retry loop
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    if "429" in error_str or "ResourceExhausted" in error_str or "quota" in error_str.lower():
                        wait_time = min(10 * (attempt + 1), 35)
                        print(f"[PDF_ANALYZER] Rate limited on {model_name}, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"[PDF_ANALYZER] Error with {model_name}: {e}")
                        break  # Non-retryable error, try next model

            if last_error is None and text:
                break  # Got a successful response, stop trying models

        if last_error and not text:
            print(f"[PDF_ANALYZER] All models failed. Last error: {last_error}")
            return None

        # Parse response
        # Extract JSON from potential markdown code fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text.strip())

        # Build geometry-like objects for each part (compatible with our quote engine)
        for part in result.get("parts", []):
            bb = part.get("bounding_box", {})
            part["geometry"] = {
                "volume": part.get("estimated_volume_mm3", 0),
                "surfaceArea": part.get("estimated_surface_area_mm2", 0),
                "boundingBox": {
                    "sizeX": bb.get("sizeX", 0),
                    "sizeY": bb.get("sizeY", 0),
                    "sizeZ": bb.get("sizeZ", 0),
                },
                "complexity": {
                    "tier": "Moderate",
                    "score": 150,
                    "faces": 0,
                    "edges": 0,
                    "holes": sum(h.get("count", 1) for h in part.get("holes", [])),
                },
                "holes": [
                    {
                        "diameter": h.get("diameter", 5),
                        "depth": h.get("depth", h.get("diameter", 5)),
                        "type": h.get("type", "through"),
                    }
                    for h in part.get("holes", [])
                    for _ in range(h.get("count", 1))
                ],
            }

        return result

    except json.JSONDecodeError as e:
        print(f"[PDF_ANALYZER] JSON parse error: {e}")
        print(f"[PDF_ANALYZER] Raw response: {text[:500]}")
        return None
    except Exception as e:
        print(f"[PDF_ANALYZER] Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Cleanup temp file
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        # Cleanup uploaded file from Gemini
        if uploaded_file:
            try:
                genai.delete_file(uploaded_file.name)
            except Exception:
                pass
