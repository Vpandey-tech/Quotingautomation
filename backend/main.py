"""
AccuDesign Quoting Agent — Phase 4 Backend (INR Edition)
FastAPI + CadQuery geometry analysis + Live pricing (INR) + Quote engine + PDF analysis

Endpoints:
  GET  /api/health              — Health check
  GET  /api/materials           — All supported materials
  GET  /api/processes           — All manufacturing processes
  GET  /api/tolerances          — All tolerance tiers
  GET  /api/prices              — Current metal prices (INR with exchange rate)
  GET  /api/exchange-rate       — Current USD → INR rate
  POST /api/analyze             — Upload STEP → B-Rep geometry analysis
  POST /api/analyze/pdf         — Upload PDF drawing → Gemini AI analysis
  POST /api/quote               — Full quote from geometry + selections (INR)
  POST /api/quote/pdf           — Full quote as downloadable PDF (ACCU DESIGN format)

Run:
  py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.background import BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Optional, List
import tempfile, os
import numpy as np
for alias, target in [
    ("bool8", "bool_"),
    ("bool0", "bool_"),
    ("object0", "object_"),
    ("int0", "intp"),
    ("uint0", "uintp"),
    ("void0", "void"),
    ("bytes0", "bytes_"),
    ("str0", "str_"),
    ("float0", "float64"),
    ("complex0", "complex128"),
]:
    if not hasattr(np, alias) and hasattr(np, target):
        setattr(np, alias, getattr(np, target))

from dotenv import load_dotenv

load_dotenv()

from services.pricing import MATERIALS, get_live_prices
from services.costing import compute_quote, TOLERANCE_MULTIPLIERS, PROCESS_RATES
from services.pdf import generate_quote_pdf
from services.currency import get_usd_to_inr, convert_material_price
from services.quote_number import generate_quote_number
from services.pdf_analyzer import analyze_pdf_drawing
from services.stock_sizes import get_stock_table, get_all_stock_types, find_next_stock_size
from services.material_calculator import calculate_raw_material
from services.gemini_validator import validate_with_gemini

# ── Engineering Design Module (AIAE) ─────────────────────────────────────────
from engineering_routes import router as design_router

app = FastAPI(
    title="AccuDesign Quoting API",
    description="Phase 4: INR pricing + ACCU DESIGN PDF + PDF drawing analysis",
    version="0.4.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Lock to domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the engineering design module routes
app.include_router(design_router)

# ── Schemas ───────────────────────────────────────────────────────────────────
class QuoteRequest(BaseModel):
    geometry:       dict = Field(..., description="Result from /api/analyze or mesh fallback")
    material_id:    str  = Field(..., example="aluminum_6061")
    process_ids:    list = Field(default=["cnc_milling_3ax"], description="List of selected manufacturing processes")
    tolerance_id:   str  = Field("standard", example="standard")
    quantity:       int  = Field(1, ge=1, le=10000)
    surface_treatment_ids: list = Field(default=[], description="List of selected surface treatments")
    profit_margin_pct: float = Field(22.0, ge=15.0, le=30.0, description="Profit margin between 15% and 30%")
    client_name:    str  = Field("", example="Vishal Jadhav")
    client_company: str  = Field("", example="Aerochamp Aviation (Intl.) Pvt. Ltd.")
    source_filename: str = Field("", example="shaft_drawing.pdf")
    screenshot:     Optional[str] = Field(None, description="Base64 isometric view screenshot")
    # Senior's Phase 5 additions:
    include_setup_cost: bool = Field(True, description="Include/exclude setup & amortization cost in quote")
    include_drilling_surcharge: bool = Field(True, description="Include/exclude drilling surcharge in quote")
    hole_count_override: int = Field(-1, ge=-1, description="Override hole count. -1 = use AI/B-Rep detected count")
    stock_type: str = Field("round_bar", description="Stock type: round_bar, plate, hex_bar")
    # Region and Bends additions:
    region: str = Field("pune", description="Region: pune, ahmedabad, mumbai, chennai, bangalore, delhi")
    bends_count: int = Field(0, ge=0, description="Number of bends for sheet metal")
    bend_length_mm: float = Field(0.0, ge=0.0, description="Total length of bends in mm")

class ChatRequest(BaseModel):
    message: str
    metrics: dict

class BomPdfRequest(BaseModel):
    parts:          list  = Field(..., description="List of part objects from the BOM quote")
    quote_number:   str   = Field("")
    client_name:    str   = Field("")
    client_company: str   = Field("")
    hsn_code:       str   = Field("84669310")
    source_filename: str  = Field("")
    profit_margin_pct: float = Field(22.0, ge=15.0, le=30.0)
    # Pre-computed combined totals from frontend — ensures PDF matches UI exactly
    combined_order_total: Optional[float] = Field(None, description="Pre-computed combined order total")
    combined_sgst: Optional[float] = Field(None, description="Pre-computed combined SGST")
    combined_cgst: Optional[float] = Field(None, description="Pre-computed combined CGST")
    combined_grand_total: Optional[float] = Field(None, description="Pre-computed combined grand total")

class MaterialEstimateRequest(BaseModel):
    size_x: float = Field(..., description="Part bounding box X dimension (mm)")
    size_y: float = Field(..., description="Part bounding box Y dimension (mm)")
    size_z: float = Field(..., description="Part bounding box Z dimension (mm)")
    material_id: str = Field("aluminum_6061", description="Material ID for density lookup")
    quantity: int = Field(1, ge=1, le=10000)
    stock_type: str = Field("round_bar", description="round_bar, plate, hex_bar")
    part_volume_mm3: float = Field(0.0, description="Exact part volume for utilization calc")
    region: str = Field("pune", description="pune, ahmedabad, mumbai, chennai, bangalore, delhi")

class AiValidationRequest(BaseModel):
    size_x: float = Field(...)
    size_y: float = Field(...)
    size_z: float = Field(...)
    material_id: str = Field("aluminum_6061")
    quantity: int = Field(1, ge=1)
    stock_type: str = Field("round_bar")
    part_volume_mm3: float = Field(0.0)
    region: str = Field("pune")

class UpdateMaterialPricesRequest(BaseModel):
    prices: dict = Field(..., description="Mapping of material_id -> base_inr_kg")



# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
async def health():
    fx = await get_usd_to_inr()
    return {
        "status": "ok",
        "phase": 4,
        "version": "0.4.0",
        "currency": "INR",
        "exchange_rate": fx["rate"],
        "exchange_source": fx["source"],
        "materials": len(MATERIALS),
        "processes": len(PROCESS_RATES),
        "tolerances": len(TOLERANCE_MULTIPLIERS),
    }


# ── Exchange Rate ─────────────────────────────────────────────────────────────
@app.get("/api/exchange-rate", tags=["Pricing"])
async def get_exchange_rate():
    """Get current USD → INR exchange rate."""
    return await get_usd_to_inr()


# ── Materials & Processes catalogue ───────────────────────────────────────────
@app.get("/api/materials", tags=["Catalogue"])
async def get_materials():
    """Return all supported materials with INR prices."""
    fx = await get_usd_to_inr()
    rate = fx["rate"]
    return {
        mid: {
            "name":          m["name"],
            "density":       m["density"],
            "price_usd_kg":  m["price_usd_kg"],
            "price_inr_kg":  convert_material_price(m["price_usd_kg"], rate, mid),
            "machinability": m["machinability"],
            "grade":         m.get("grade", "-"),
            "standard":      m.get("standard", "-"),
            "tensile_strength": m.get("tensile_strength", "-"),
            "yield_strength":   m.get("yield_strength", "-"),
            "notes":         m.get("notes", "-"),
        }
        for mid, m in MATERIALS.items()
    }


@app.post("/api/materials/update", tags=["Catalogue"])
async def update_material_prices(req: UpdateMaterialPricesRequest):
    """Update material base prices in INR/kg and persist to materials_db.json."""
    from services.pricing import MATERIALS, save_stored_prices
    updated_count = 0
    for mid, price in req.prices.items():
        if mid in MATERIALS:
            MATERIALS[mid]["base_inr_kg"] = float(price)
            updated_count += 1
    
    if updated_count > 0:
        save_stored_prices()
        return {"success": True, "updated_count": updated_count}
    raise HTTPException(400, "No valid materials found to update.")


@app.post("/api/materials/reset", tags=["Catalogue"])
async def reset_material_prices():
    """Reset material prices by deleting materials_db.json and reloading defaults."""
    from services.pricing import DB_FILE, load_stored_prices, MATERIALS
    import os
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
        except Exception as e:
            raise HTTPException(500, f"Failed to reset database: {e}")
            
    # Restore defaults
    DEFAULTS = {
        'mild_steel': 70.0,
        'low_carbon_steel': 75.0,
        'medium_carbon_steel': 80.0,
        'high_carbon_steel': 85.0,
        'free_machining_steel': 70.0,
        'alloy_steel': 115.0,
        'tool_steel_d2': 450.0,
        'stainless_steel_304': 275.0,
        'stainless_steel_304l': 295.0,
        'stainless_steel_316': 375.0,
        'stainless_steel_316l': 395.0,
        'stainless_steel_410': 225.0,
        'cast_iron_gray': 100.0,
        'cast_iron_ductile': 150.0,
        'aluminum_6061': 225.0,
        'aluminum_6063': 200.0,
        'aluminum_7075': 315.0,
        'copper': 750.0,
        'brass_60_40': 500.0,
        'brass_70_30': 550.0,
        'phosphor_bronze': 675.0,
        'titanium_grade_2': 2750.0,
        'titanium_grade_5': 3250.0,
        'magnesium_az91d': 350.0,
        'nickel_200': 1350.0,
        'monel_400': 1750.0,
        'inconel_625': 3000.0,
        'abs_plastic': 175.0,
        'abs_flame_retardant': 225.0,
        'polypropylene': 115.0,
        'polyethylene_hdpe': 105.0,
        'polycarbonate': 325.0,
        'nylon_pa6': 275.0,
        'nylon_pa66': 315.0,
        'acrylic_pmma': 225.0,
        'pom_delrin': 400.0,
        'pet_plastic': 150.0,
        'peek_plastic': 2250.0,
        'ptfe_teflon': 600.0,
        'pvc_plastic': 100.0,
        'epoxy_resin': 300.0,
        'phenolic': 200.0,
        'gfrp': 450.0,
        'cfrp': 1500.0,
        'kevlar_epoxy': 2000.0,
        'aluminum_sic': 1150.0,
        'alumina_al2o3': 650.0,
        'zirconia_zro2': 1250.0,
        'silicon_nitride': 2000.0,
        'silicon_carbide': 1500.0,
        'tungsten_carbide': 3000.0,
        'inconel_600': 2500.0,
        'inconel_718': 3000.0,
        'waspaloy': 3500.0,
        'hastelloy_x': 3500.0,
        'molybdenum': 4500.0,
        'tungsten': 6000.0,
        'tantalum': 7000.0,
    }
    for mid, default_price in DEFAULTS.items():
        if mid in MATERIALS:
            MATERIALS[mid]["base_inr_kg"] = default_price
            
    return {"success": True, "message": "Database reset to defaults."}


@app.post("/api/materials/upload-excel", tags=["Catalogue"])
async def upload_material_prices_excel(file: UploadFile = File(...)):
    """
    Upload an Excel (.xlsx) or CSV (.csv) file to update raw material base prices (INR/kg).
    Parses headers loosely to locate 'Material' and 'Price' columns.
    """
    import io
    import csv
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(500, "openpyxl is not installed in the backend environment. Run pip install openpyxl.")

    filename = (file.filename or "").lower()
    if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
        raise HTTPException(400, "Unsupported file format. Please upload an Excel (.xlsx) or CSV (.csv) file.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "File is empty.")

    from services.pricing import MATERIALS, save_stored_prices
    
    rows = []
    
    # Parse based on extension
    if filename.endswith('.csv'):
        try:
            decoded = contents.decode('utf-8-sig', errors='ignore')
            reader = csv.reader(io.StringIO(decoded))
            for row in reader:
                rows.append([cell.strip() for cell in row])
        except Exception as e:
            raise HTTPException(400, f"Error parsing CSV file: {str(e)}")
    else:
        # Excel .xlsx or .xls
        try:
            wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None for cell in row):
                    rows.append([str(cell).strip() if cell is not None else "" for cell in row])
        except Exception as e:
            raise HTTPException(400, f"Error parsing Excel file: {str(e)}. Ensure it is a valid .xlsx file.")

    if not rows:
        raise HTTPException(400, "No data rows found in the uploaded file.")

    # Locate headers in the first few rows (usually row 0 or 1)
    header_idx = 0
    mat_col_idx = -1
    price_col_idx = -1
    
    for idx, r in enumerate(rows[:5]):
        for col_idx, cell in enumerate(r):
            cell_lower = cell.lower()
            if any(k in cell_lower for k in ["material", "grade", "standard", "alias", "id", "name"]):
                if mat_col_idx == -1:
                    mat_col_idx = col_idx
                    header_idx = idx
            if any(k in cell_lower for k in ["price", "rate", "inr", "cost", "rs"]):
                if price_col_idx == -1:
                    price_col_idx = col_idx
                    header_idx = idx

    # Fallbacks if headers not detected: assume col 0 is material, col 1 is price
    if mat_col_idx == -1:
        mat_col_idx = 0
    if price_col_idx == -1:
        price_col_idx = 1 if len(rows[0]) > 1 else 0

    updated_materials = []
    unrecognized = []
    
    def find_matching_material_id(text: str) -> Optional[str]:
        if not text:
            return None
        text_clean = str(text).strip().lower().replace("-", "").replace("_", "").replace(" ", "")
        
        aliases = {
            "ss304": "stainless_steel_304",
            "ss304l": "stainless_steel_304",
            "304": "stainless_steel_304",
            "ss316": "stainless_steel_316l",
            "ss316l": "stainless_steel_316l",
            "316": "stainless_steel_316l",
            "ms": "mild_steel",
            "is2062": "mild_steel",
            "a36": "mild_steel",
            "en8": "mild_steel",
            "al6061": "aluminum_6061",
            "6061": "aluminum_6061",
            "al7075": "aluminum_7075",
            "7075": "aluminum_7075",
            "he30": "commercial_aluminium_he30",
            "brass": "brass_360",
            "copper": "copper",
            "titanium": "titanium_ti6al4v",
            "inconel": "inconel_718",
            "d2": "tool_steel_d2",
            "abs": "abs_plastic",
            "pla": "pla_plastic"
        }
        if text_clean in aliases:
            return aliases[text_clean]

        for mid, mat in MATERIALS.items():
            mid_clean = mid.replace("_", "")
            name_clean = mat["name"].lower().replace("-", "").replace("_", "").replace(" ", "")
            grade_clean = mat.get("grade", "").lower().replace("-", "").replace("_", "").replace(" ", "")
            std_clean = mat.get("standard", "").lower().replace("-", "").replace("_", "").replace(" ", "")
            
            if text_clean in [mid_clean, name_clean, grade_clean, std_clean]:
                return mid
            if text_clean in name_clean or name_clean in text_clean:
                return mid
        return None

    # Parse rows
    for r in rows[header_idx + 1:]:
        if len(r) <= max(mat_col_idx, price_col_idx):
            continue
        mat_text = r[mat_col_idx].strip()
        price_text = r[price_col_idx].strip()
        
        if not mat_text:
            continue
            
        mid = find_matching_material_id(mat_text)
        
        if mid:
            try:
                clean_price = price_text.replace("₹", "").replace("$", "").replace(",", "").strip()
                price_val = float(clean_price)
                if price_val > 0:
                    MATERIALS[mid]["base_inr_kg"] = price_val
                    updated_materials.append({
                        "id": mid,
                        "name": MATERIALS[mid]["name"],
                        "matched_from": mat_text,
                        "new_price": price_val
                    })
            except ValueError:
                continue
        else:
            unrecognized.append(mat_text)

    if len(updated_materials) > 0:
        save_stored_prices()
        return {
            "success": True,
            "updated_count": len(updated_materials),
            "updated_materials": updated_materials,
            "unrecognized": unrecognized
        }
    else:
        raise HTTPException(400, f"No matching materials found in the uploaded file. Columns assumed: Material Col={mat_col_idx}, Price Col={price_col_idx}.")


@app.get("/api/processes", tags=["Catalogue"])
async def get_processes():
    """Return all supported manufacturing processes with INR rates."""
    fx = await get_usd_to_inr()
    rate = fx["rate"]
    from services.currency import convert_machine_rate, convert_setup_fee
    return {
        pid: {
            "name":         p["name"],
            "rate_usd_hr":  p["rate_hr"],
            "rate_inr_hr":  convert_machine_rate(p["rate_hr"], rate),
            "setup_usd":    p["setup_usd"],
            "setup_inr":    convert_setup_fee(p["setup_usd"], rate),
            "axes":         p["axes"],
        }
        for pid, p in PROCESS_RATES.items()
    }


@app.get("/api/tolerances", tags=["Catalogue"])
def get_tolerances():
    """Return all supported tolerance tiers."""
    return {
        tid: {"label": t["label"], "multiplier": t["multiplier"]}
        for tid, t in TOLERANCE_MULTIPLIERS.items()
    }


# ── Standard Stock Sizes (Machinery's Handbook) ─────────────────────────────
@app.get("/api/stock-sizes", tags=["Catalogue"])
def get_stock_sizes(stock_type: str = "round_bar"):
    """Return standard stock sizes for a given stock type (Machinery's Handbook 32nd Ed)."""
    return {
        "stock_type": stock_type,
        "sizes": get_stock_table(stock_type),
        "all_types": get_all_stock_types(),
    }


# ── Material Estimate (pre-quote weight calculation) ────────────────────────
@app.post("/api/material-estimate", tags=["Quoting"])
async def material_estimate(req: MaterialEstimateRequest):
    """
    Pre-quote endpoint: Calculate raw material weight using envelope-based
    methodology BEFORE generating the full quote.
    Lets the user verify critical data points before triggering the quote.
    """
    if req.material_id not in MATERIALS:
        raise HTTPException(400, f"Unknown material: '{req.material_id}'")

    mat = MATERIALS[req.material_id]
    result = calculate_raw_material(
        size_x_mm=req.size_x,
        size_y_mm=req.size_y,
        size_z_mm=req.size_z,
        density_g_cm3=mat["density"],
        quantity=req.quantity,
        stock_type=req.stock_type,
        part_volume_mm3=req.part_volume_mm3,
    )

    # Add material info to response
    fx = await get_usd_to_inr()
    rate = fx["rate"]
    price_data = await get_live_prices()
    usd_price = price_data["prices"].get(req.material_id, mat["price_usd_kg"])
    metal_price_inr = convert_material_price(usd_price, rate, req.material_id)

    # Apply regional material index adjustment
    from services.costing import REGIONAL_INDICES
    reg_index = REGIONAL_INDICES.get(req.region.lower(), {"material": 1.0, "machine": 1.0, "labor": 1.0})
    metal_price_inr = metal_price_inr * reg_index["material"]

    result["material_name"] = mat["name"]
    result["density_g_cm3"] = mat["density"]
    result["metal_price_inr_kg"] = round(metal_price_inr, 2)
    result["estimated_material_cost_inr"] = round(result["raw_stock_kg"] * metal_price_inr, 2)

    return JSONResponse(content=result)


# ── AI Cross-Validation (Gemini — on-demand only) ──────────────────────────
@app.post("/api/validate-material", tags=["Quoting"])
async def validate_material_ai(req: AiValidationRequest):
    """
    Cross-validate deterministic material calculation with Gemini AI.
    ONLY called when user explicitly clicks 'Validate with AI'.
    Uses senior's exact prompt. Returns confidence score + discrepancy analysis.
    """
    if req.material_id not in MATERIALS:
        raise HTTPException(400, f"Unknown material: '{req.material_id}'")

    mat = MATERIALS[req.material_id]
    fx = await get_usd_to_inr()
    rate = fx["rate"]
    price_data = await get_live_prices()
    usd_price = price_data["prices"].get(req.material_id, mat["price_usd_kg"])
    metal_price_inr = convert_material_price(usd_price, rate, req.material_id)

    # Apply regional material index adjustment
    from services.costing import REGIONAL_INDICES
    reg_index = REGIONAL_INDICES.get(req.region.lower(), {"material": 1.0, "machine": 1.0, "labor": 1.0})
    metal_price_inr = metal_price_inr * reg_index["material"]

    # ── Calculate our values here in the backend — never trust frontend to pass them ──
    # This is the SAME calculation used in /api/material-estimate and compute_quote()
    # Doing it here guarantees our_gross_weight is never 0, fixing "Match: Unknown"
    our_calc = calculate_raw_material(
        size_x_mm=req.size_x,
        size_y_mm=req.size_y,
        size_z_mm=req.size_z,
        density_g_cm3=mat["density"],
        quantity=req.quantity,
        stock_type=req.stock_type,
        part_volume_mm3=req.part_volume_mm3,
    )
    from services.costing import _get_standard_size_label
    our_stock_size   = _get_standard_size_label(our_calc)
    our_gross_weight = our_calc["gross_weight_per_part_kg"]   # ← exact value used for pricing
    our_batch_weight = our_calc["total_batch_weight_kg"]
    our_utilization  = our_calc["material_utilization_pct"]
    our_material_cost = round(our_calc["raw_stock_kg"] * metal_price_inr, 2)

    result = await validate_with_gemini(
        # Raw inputs
        material_name=mat["name"],
        density=mat["density"],
        size_x=req.size_x,
        size_y=req.size_y,
        size_z=req.size_z,
        stock_type=req.stock_type,
        quantity=req.quantity,
        metal_price_inr_kg=metal_price_inr,
        # Our calculated values for comparison
        our_stock_size=our_stock_size,
        our_gross_weight=our_gross_weight,
        our_batch_weight=our_batch_weight,
        our_utilization=our_utilization,
        our_material_cost=our_material_cost,
    )

    # Also include our calculated values in the response for the UI side-by-side display
    result["our_calculation"] = {
        "stock_size":         our_stock_size,
        "gross_weight_kg":    our_gross_weight,
        "total_batch_weight_kg": our_batch_weight,
        "material_utilization_pct": our_utilization,
        "material_cost_inr":  our_material_cost,
        "parts_per_bar":      our_calc.get("parts_per_bar", 0),
        "envelope_volume_mm3": our_calc.get("envelope_volume_mm3", 0),
    }

    return JSONResponse(content=result)


# ── Live metal prices (INR) ──────────────────────────────────────────────────
@app.get("/api/prices", tags=["Pricing"])
async def get_prices():
    """
    Fetch current metal prices converted to INR.
    Section A formula: INR/kg = (USD/kg × exchange_rate) + ₹150
    """
    price_data = await get_live_prices()
    fx = await get_usd_to_inr()
    rate = fx["rate"]

    inr_prices = {}
    for mid, usd_price in price_data["prices"].items():
        inr_prices[mid] = convert_material_price(usd_price, rate, mid)

    return {
        "prices_usd": price_data["prices"],
        "prices_inr": inr_prices,
        "exchange_rate": rate,
        "exchange_source": fx["source"],
        "price_source": price_data["source"],
        "timestamp": price_data["timestamp"],
        "note": price_data.get("note", ""),
        "currency": "INR",
    }


# ── STEP File Analysis ────────────────────────────────────────────────────────
@app.post("/api/analyze", tags=["Geometry"])
async def analyze_step(file: UploadFile = File(...)):
    """Upload a STEP file → returns full B-Rep geometric analysis via CadQuery."""
    fname = (file.filename or "").lower()
    if not (fname.endswith('.step') or fname.endswith('.stp')):
        raise HTTPException(400, "Only STEP/STP files are accepted.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "Uploaded file is empty.")
    if len(contents) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(400, "File too large. Maximum 50MB.")

    with tempfile.NamedTemporaryFile(suffix='.step', delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = await run_in_threadpool(_analyze_with_cadquery, tmp_path, file.filename)
        return JSONResponse(content=result)
    except Exception as e:
        import traceback
        print(f"\n{'='*60}\n[ANALYZE ERROR] {file.filename}\n{traceback.format_exc()}\n{'='*60}\n")
        raise HTTPException(500, f"B-Rep analysis failed: {str(e)}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── PDF Drawing Analysis (Gemini) ─────────────────────────────────────────────
@app.post("/api/analyze/pdf", tags=["Geometry"])
async def analyze_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF engineering drawing → Gemini AI extracts dimensions,
    materials, holes, and manufacturing requirements.
    Returns structured part data compatible with the quote engine.
    """
    fname = (file.filename or "").lower()
    if not fname.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are accepted for drawing analysis.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "Uploaded file is empty.")
    if len(contents) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(400, "PDF too large. Maximum 20MB.")

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        raise HTTPException(503,
            "PDF analysis requires valid ACCU AI credentials in the workspace backend."
        )

    result = await run_in_threadpool(analyze_pdf_drawing, contents, file.filename)
    if result is None:
        raise HTTPException(429, "ACCU AI rate limit exceeded. Please try again shortly or configure a premium endpoint.")

    return JSONResponse(content=result)


# ── Chat Assistant (Gemini) ───────────────────────────────────────────────────
@app.post("/api/chat", tags=["AI"])
async def chat_adjust(req: ChatRequest):
    """
    Interpret user chat instructions to update the quote metrics object.
    It returns a conversational response + the newly modified JSON.
    """
    import google.generativeai as genai
    import json
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return JSONResponse(content={"response": "I am offline since ACCU AI credentials are not configured in backend/.env. Please configure them to enable chat.", "metrics": req.metrics})
        
    try:
        prompt = f"""You are ACCU AI Copilot, a helpful manufacturing quoting assistant. 
The user wants to adjust their quote parameters based on their message: "{req.message}"
Current configuration metrics state:
{json.dumps(req.metrics, indent=2)}

Please smartly interpret their request and update the configuration metrics variables accordingly.
For example, if they specify material: "Aluminium 6061", change the "materialId" to "aluminum_6061", and "material" to "Aluminum 6061".
Try to match their terms loosely. E.g if they say 'commercial aluminium' pick 'commercial_aluminium_he30'. If they say 'turning', set 'processId' to 'cnc_turning'.

CRITICAL INSTRUCTIONS FOR 'response':
1. It MUST be highly conversational, extremely brief, and punchy (1 to 3 sentences maximum).
2. NEVER output a giant wall of text, massive lists, or excessive markdown formatting. If the user asks what parameters or numbers were found, just give a quick one-sentence high-level summary. Focus on clarity, not overwhelming detail.
3. ALWAYS ensure numerical values are accurately preserved and stated if relevant.

Return ONLY valid JSON in this exact format, without code blocks or markdown, just the raw braces:
{{
  "response": "Brief professional conversational response acknowledging changes made.",
  "metrics": {{ ... complete updated metrics object ... }}
}}"""
        
        # Use raw Google Generative AI call
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        generation_config = genai.types.GenerationConfig(temperature=0.0)
        
        response = await run_in_threadpool(
            model.generate_content,
            prompt,
            generation_config=generation_config
        )
        text = response.text
        
        if not text:
            raise Exception("Empty response from AI")

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        data = json.loads(text.strip())
        return JSONResponse(content={
            "response": data.get("response", "Updated configuration."),
            "metrics": data.get("metrics", req.metrics)
        })
    except json.JSONDecodeError:
        return JSONResponse(content={"response": "I had trouble understanding that change. Could you please rephrase it or adjust manually?", "metrics": req.metrics})
    except Exception as e:
        print("Chat API Error:", e)
        return JSONResponse(content={"response": "I had an unexpected issue processing your request. Please adjust it manually.", "metrics": req.metrics})

# ── Quote endpoint (INR) ─────────────────────────────────────────────────────
@app.post("/api/quote", tags=["Quoting"])
async def gen_quote(req: QuoteRequest):
    """
    Generate a full manufacturing quote in INR.
    Uses Section A formula for material prices and Section B for machine rates.
    """
    if req.material_id not in MATERIALS:
        raise HTTPException(400, f"Unknown material: '{req.material_id}'. "
                                 f"Valid: {list(MATERIALS.keys())}")
    
    for pid in req.process_ids:
        if pid not in PROCESS_RATES:
            raise HTTPException(400, f"Unknown process: '{pid}'. "
                                     f"Valid: {list(PROCESS_RATES.keys())}")
    if req.tolerance_id not in TOLERANCE_MULTIPLIERS:
        raise HTTPException(400, f"Unknown tolerance: '{req.tolerance_id}'. "
                                 f"Valid: {list(TOLERANCE_MULTIPLIERS.keys())}")

    # Get live prices and exchange rate
    price_data = await get_live_prices()
    fx = await get_usd_to_inr()
    rate = fx["rate"]

    # Get material price in USD, then convert to INR (Section A)
    usd_price = price_data["prices"].get(
        req.material_id,
        MATERIALS[req.material_id]["price_usd_kg"]
    )
    metal_price_inr = convert_material_price(usd_price, rate, req.material_id)

    # Generate quotation number
    quote_number = generate_quote_number(req.client_company or req.client_name)

    try:
        quote = compute_quote(
            geometry=req.geometry,
            material_id=req.material_id,
            process_ids=req.process_ids,
            tolerance_id=req.tolerance_id,
            quantity=req.quantity,
            metal_price_inr=metal_price_inr,
            exchange_rate=rate,
            surface_treatment_ids=req.surface_treatment_ids,
            profit_margin_pct=req.profit_margin_pct,
            include_setup_cost=req.include_setup_cost,
            include_drilling_surcharge=req.include_drilling_surcharge,
            hole_count_override=req.hole_count_override,
            stock_type=req.stock_type,
            region=req.region,
            bends_count=req.bends_count,
            bend_length_mm=req.bend_length_mm,
        )
        quote["price_source"]    = price_data["source"]
        quote["price_note"]      = price_data.get("note", "")
        quote["exchange_rate"]   = rate
        quote["exchange_source"] = fx["source"]
        quote["quote_number"]    = quote_number
        quote["client_name"]     = req.client_name
        quote["client_company"]  = req.client_company
        return JSONResponse(content=quote)
    except Exception as e:
        import traceback
        print(f"\n{'='*60}\n[QUOTE ERROR]\n{traceback.format_exc()}\n{'='*60}\n")
        raise HTTPException(500, f"Quote computation failed: {str(e)}")


# ── PDF quote endpoint (ACCU DESIGN format) ──────────────────────────────────
@app.post("/api/quote/pdf", tags=["Quoting"])
async def gen_quote_pdf(req: QuoteRequest, background_tasks: BackgroundTasks):
    """Generate a quotation PDF in ACCU DESIGN format (INR)."""
    if req.material_id not in MATERIALS:
        raise HTTPException(400, f"Unknown material: '{req.material_id}'")
        
    for pid in req.process_ids:
        if pid not in PROCESS_RATES:
            raise HTTPException(400, f"Unknown process: '{pid}'")
    if req.tolerance_id not in TOLERANCE_MULTIPLIERS:
        raise HTTPException(400, f"Unknown tolerance: '{req.tolerance_id}'")

    price_data = await get_live_prices()
    fx = await get_usd_to_inr()
    rate = fx["rate"]

    usd_price = price_data["prices"].get(
        req.material_id,
        MATERIALS[req.material_id]["price_usd_kg"]
    )
    metal_price_inr = convert_material_price(usd_price, rate, req.material_id)
    quote_number = generate_quote_number(req.client_company or req.client_name)

    try:
        quote = compute_quote(
            geometry=req.geometry,
            material_id=req.material_id,
            process_ids=req.process_ids,
            tolerance_id=req.tolerance_id,
            quantity=req.quantity,
            metal_price_inr=metal_price_inr,
            exchange_rate=rate,
            surface_treatment_ids=req.surface_treatment_ids,
            profit_margin_pct=req.profit_margin_pct,
            include_setup_cost=req.include_setup_cost,
            include_drilling_surcharge=req.include_drilling_surcharge,
            hole_count_override=req.hole_count_override,
            stock_type=req.stock_type,
            region=req.region,
            bends_count=req.bends_count,
            bend_length_mm=req.bend_length_mm,
        )
        quote["price_source"] = price_data["source"]
        quote["quote_number"] = quote_number

        result = generate_quote_pdf(
            quote_data=quote,
            quote_number=quote_number,
            client_name=req.client_name,
            client_company=req.client_company,
            source_filename=req.source_filename,
            screenshot_b64=req.screenshot,
        )

        # Bulletproof unpack — works whether pdf.py returns 1 or 2 values
        if isinstance(result, tuple):
            pdf_path = result[0]
            safe_qnum = quote_number.replace("/", "_").strip()
            suggested_filename = result[1] if len(result) > 1 else f"ACCUDESIGN_QUOTE_{safe_qnum}.pdf"
        else:
            pdf_path = result
            safe_qnum = quote_number.replace("/", "_").strip()
            suggested_filename = f"ACCUDESIGN_QUOTE_{safe_qnum}.pdf"

        background_tasks.add_task(_safe_delete, pdf_path)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=suggested_filename,
        )
    except Exception as e:
        import traceback
        print(f"\n{'='*60}\n[PDF ERROR]\n{traceback.format_exc()}\n{'='*60}\n")
        raise HTTPException(500, f"PDF generation failed: {str(e)}")


def _safe_delete(path: str):
    try:
        os.unlink(path)
    except Exception:
        pass


# ── BOM Assembly PDF endpoint ───────────────────────────────────────────────
@app.post("/api/quote/bom-pdf", tags=["Quoting"])
async def gen_bom_quote_pdf(req: BomPdfRequest, background_tasks: BackgroundTasks):
    """
    Generate BOM PDF using costs already computed by the frontend.
    Frontend calls /api/quote per part and stores order_total, sgst, cgst,
    grand_total in each part object. We use those directly — no recomputation.
    """
    try:
        from services.pdf import generate_bom_quote_pdf

        enriched_parts = []
        for p in req.parts:
            part = dict(p)

            # Detect buyout
            is_buyout = (
                bool(part.get("isBuyout"))
                or str(part.get("part_category", "")).lower() == "buyout item"
            )
            part["isBuyout"] = is_buyout

            if is_buyout:
                part["order_total"] = 0.0
                part["sgst"]        = 0.0
                part["cgst"]        = 0.0
                part["grand_total"] = 0.0
                enriched_parts.append(part)
                continue

            # ── Use pre-computed costs from the frontend ──────────────────────
            # Frontend sends: order_total, sgst, cgst, grand_total, unit_price
            # These come straight from /api/quote responses — they are correct.
            qty = int(part.get("qty") or part.get("quantity") or 1)
            part["quantity"] = qty

            # order_total = unit_price_discounted × qty  (pre-tax)
            order_total = float(part.get("order_total") or 0)
            if order_total == 0:
                # fallback: unit_price × qty
                order_total = round(float(part.get("unit_price") or 0) * qty, 2)
            part["order_total"] = order_total

            # sgst / cgst — use pre-computed or derive from order_total
            part["sgst"]        = float(part.get("sgst") or round(order_total * 0.09, 2))
            part["cgst"]        = float(part.get("cgst") or round(order_total * 0.09, 2))
            part["grand_total"] = float(part.get("grand_total") or
                                        round(order_total + part["sgst"] + part["cgst"], 2))

            enriched_parts.append(part)

        # ── Generate PDF ──────────────────────────────────────────────────────
        result = generate_bom_quote_pdf(
            parts=enriched_parts,
            quote_number=req.quote_number,
            client_name=req.client_name,
            client_company=req.client_company,
            hsn_code=req.hsn_code,
            source_filename=req.source_filename,
            profit_margin_pct=req.profit_margin_pct,
            # Pre-computed combined totals — ensures PDF matches UI exactly
            combined_order_total=req.combined_order_total,
            combined_sgst=req.combined_sgst,
            combined_cgst=req.combined_cgst,
            combined_grand_total=req.combined_grand_total,
        )

        # Bulletproof unpack — works with old pdf.py (1 val) or new (2 vals)
        if isinstance(result, tuple):
            pdf_path  = result[0]
            suggested = result[1] if len(result) > 1 else None
        else:
            pdf_path  = result
            suggested = None

        safe_qnum = req.quote_number.replace("/", "_").strip()
        filename  = suggested or f"ACCUDESIGN_BOM_QUOTE_{safe_qnum}.pdf"

        background_tasks.add_task(_safe_delete, pdf_path)
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)

    except Exception as e:
        import traceback
        print(f"\n{'='*60}\n[BOM PDF ERROR]\n{traceback.format_exc()}\n{'='*60}\n")
        raise HTTPException(500, f"BOM PDF generation failed: {str(e)}")


# ── CadQuery / build123d geometry analysis ────────────────────────────────────
def _analyze_with_cadquery(path: str, original_name: str) -> dict:
    """Full B-Rep geometry analysis using build123d / OpenCASCADE with CadQuery fallback."""
    try:
        from build123d import import_step
        shape = import_step(path)

        bbox = shape.bounding_box()
        size_x = round(float(bbox.size.X), 4)
        size_y = round(float(bbox.size.Y), 4)
        size_z = round(float(bbox.size.Z), 4)
        thickness = round(min(size_x, size_y, size_z), 4)

        volume = round(abs(float(shape.volume)), 4)
        faces = shape.faces()
        edges = shape.edges()
        vertices = shape.vertices()

        surface_area = round(float(sum(f.area for f in faces)), 4)

        try:
            ctr = shape.center()
            centroid = {"x": round(float(ctr.X), 4), "y": round(float(ctr.Y), 4), "z": round(float(ctr.Z), 4)}
        except Exception:
            centroid = {"x": 0.0, "y": 0.0, "z": 0.0}

        total_edge_length = 0.0
        for edge in edges:
            try:
                total_edge_length += float(edge.length)
            except Exception:
                pass
        if total_edge_length <= 0.0:
            total_edge_length = 2 * (size_x + size_y)

        # Detect cylindrical holes via OpenCASCADE Surface Adaptor
        holes = []
        seen_centers = []
        try:
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            from OCP.GeomAbs import GeomAbs_SurfaceType
            for face in faces:
                try:
                    adaptor = BRepAdaptor_Surface(face.wrapped)
                    if adaptor.GetType() != GeomAbs_SurfaceType.GeomAbs_Cylinder:
                        continue
                    cylinder = adaptor.Cylinder()
                    radius = float(cylinder.Radius())
                    if radius <= 0 or radius > 500:
                        continue

                    fbb = face.bounding_box()
                    cx = (fbb.max.X + fbb.min.X) / 2.0
                    cy = (fbb.max.Y + fbb.min.Y) / 2.0
                    cz = (fbb.max.Z + fbb.min.Z) / 2.0

                    is_dup = False
                    for (sx, sy, sz) in seen_centers:
                        if abs(cx - sx) < 0.5 and abs(cy - sy) < 0.5 and abs(cz - sz) < 0.5:
                            is_dup = True
                            break
                    if is_dup:
                        continue
                    seen_centers.append((cx, cy, cz))

                    diameter = round(radius * 2, 4)
                    depth = round(max(fbb.size.X, fbb.size.Y, fbb.size.Z), 4)
                    hole_type = "through" if depth > diameter * 0.5 else "blind"
                    holes.append({"diameter": diameter, "depth": depth, "type": hole_type})
                except Exception:
                    continue
        except Exception:
            pass

        n_faces = len(faces)
        n_edges = len(edges)
        n_holes = len(holes)
        score = n_faces * 1 + n_edges * 0.5 + n_holes * 10
        tier = ("Simple" if score < 100 else "Moderate" if score < 300 else
                "Complex" if score < 800 else "Very Complex")

        return {
            "fileName":    original_name,
            "unit":        "Millimeter",
            "boundingBox": {"sizeX": size_x, "sizeY": size_y, "sizeZ": size_z},
            "volume":      volume,
            "surfaceArea": surface_area,
            "centroid":    centroid,
            "perimeter":   round(total_edge_length, 4),
            "thickness":   thickness,
            "topology":    {"faces": n_faces, "edges": n_edges, "vertices": len(vertices)},
            "holes":       holes,
            "complexity":  {"score": round(score, 1), "tier": tier,
                            "faces": n_faces, "edges": n_edges, "holes": n_holes},
        }

    except Exception as b3d_err:
        logger.warning(f"build123d analysis fallback, trying cadquery: {b3d_err}")
        try:
            import cadquery as cq
            shape = cq.importers.importStep(path)
            solid = shape.val()
            bb = solid.BoundingBox()
            size_x = round(bb.xmax - bb.xmin, 4)
            size_y = round(bb.ymax - bb.ymin, 4)
            size_z = round(bb.zmax - bb.zmin, 4)
            return {
                "fileName": original_name, "unit": "Millimeter",
                "boundingBox": {"sizeX": size_x, "sizeY": size_y, "sizeZ": size_z},
                "volume": round(abs(solid.Volume()), 4),
                "surfaceArea": round(solid.Area(), 4),
                "centroid": {"x": 0.0, "y": 0.0, "z": 0.0},
                "perimeter": round(2 * (size_x + size_y), 4),
                "thickness": min(size_x, size_y, size_z),
                "topology": {"faces": len(solid.Faces()), "edges": len(solid.Edges()), "vertices": len(solid.Vertices())},
                "holes": [],
                "complexity": {"score": 50, "tier": "Simple", "faces": len(solid.Faces()), "edges": len(solid.Edges()), "holes": 0},
            }
        except Exception as cq_err:
            raise RuntimeError(f"B-Rep analysis failed: {b3d_err} | {cq_err}")

# ── STATIC ASSETS (For Production/Render) ────────────────────────────────────
# We serve the compiled React SPA from the "dist" folder.
import posixpath

dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")

if os.path.isdir(dist_path):
    # Serve assets like JS/CSS (only if the assets subfolder exists)
    assets_path = os.path.join(dist_path, "assets")
    if os.path.isdir(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    # Serve files at root like vite.svg or favicon.ico if they exist
    for root_file in os.listdir(dist_path):
        fpath = os.path.join(dist_path, root_file)
        if os.path.isfile(fpath) and root_file != "index.html":
            # Quick static route for root-level files
            pass # (Skipping manual root file mapping for brevity, Vite usually puts everything cleanly in /assets)

    # Catch-all Route: serve index.html for all non-API paths so React Router works natively
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # Don't intercept API calls
        if full_path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found")
        
        # If looking for a static root file that might exist
        potential_file = os.path.join(dist_path, full_path)
        if os.path.isfile(potential_file):
            return FileResponse(potential_file)

        # Fallback to index.html for React SPA
        return FileResponse(os.path.join(dist_path, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)