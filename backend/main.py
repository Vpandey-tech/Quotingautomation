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

class AiValidationRequest(BaseModel):
    # Raw inputs only — the endpoint calculates our_ values itself
    # so "Match: Unknown" (caused by frontend passing our_gross_weight=0) is impossible
    size_x: float = Field(...)
    size_y: float = Field(...)
    size_z: float = Field(...)
    material_id: str = Field("aluminum_6061")
    quantity: int = Field(1, ge=1)
    stock_type: str = Field("round_bar")
    part_volume_mm3: float = Field(0.0)


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
            "price_inr_kg":  convert_material_price(m["price_usd_kg"], rate),
            "machinability": m["machinability"],
        }
        for mid, m in MATERIALS.items()
    }


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
    metal_price_inr = convert_material_price(usd_price, rate)

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
    metal_price_inr = convert_material_price(usd_price, rate)

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
        inr_prices[mid] = convert_material_price(usd_price, rate)

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
            "PDF analysis requires a valid GEMINI_API_KEY. "
            "Get one free at https://aistudio.google.com/app/apikey "
            "and set it in backend/.env"
        )

    result = await run_in_threadpool(_run_pdf_analysis, contents, file.filename)
    if result is None:
        raise HTTPException(429, "Google Gemini API Limit Exceeded. Your free tier quota has run out. Please wait for the daily reset.")

    return JSONResponse(content=result)


def _run_pdf_analysis(pdf_bytes: bytes, filename: str):
    """Synchronous wrapper for PDF analysis (runs in threadpool)."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(analyze_pdf_drawing(pdf_bytes, filename))
    finally:
        loop.close()


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
        return JSONResponse(content={"response": "I'm offline since GEMINI_API_KEY is not set. Please manually configure.", "metrics": req.metrics})
        
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
    metal_price_inr = convert_material_price(usd_price, rate)

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
    metal_price_inr = convert_material_price(usd_price, rate)
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


# ── CadQuery geometry analysis ────────────────────────────────────────────────
def _analyze_with_cadquery(path: str, original_name: str) -> dict:
    """Full B-Rep analysis using CadQuery."""
    try:
        import cadquery as cq
    except Exception as e:
        raise RuntimeError(f"CadQuery import failed: {e}")

    BRepAdaptor_Surface = None
    GeomAbs_Cylinder = None
    try:
        from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
        from OCC.Core.GeomAbs import GeomAbs_Cylinder
    except ImportError:
        try:
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            from OCP.GeomAbs import GeomAbs_Cylinder
        except ImportError:
            pass

    try:
        shape = cq.importers.importStep(path)
    except Exception as e:
        raise RuntimeError(f"STEP file import failed: {e}")

    solid = shape.val()

    bb     = solid.BoundingBox()
    size_x = round(bb.xmax - bb.xmin, 4)
    size_y = round(bb.ymax - bb.ymin, 4)
    size_z = round(bb.zmax - bb.zmin, 4)

    volume       = round(abs(solid.Volume()), 4)
    surface_area = round(solid.Area(), 4)

    try:
        centroid_vec = solid.Center()
        centroid = {"x": round(centroid_vec.x, 4), "y": round(centroid_vec.y, 4), "z": round(centroid_vec.z, 4)}
    except Exception:
        centroid = {"x": 0.0, "y": 0.0, "z": 0.0}

    faces    = solid.Faces()
    edges    = solid.Edges()
    vertices = solid.Vertices()

    holes = []
    seen_centers = []
    if BRepAdaptor_Surface and GeomAbs_Cylinder:
        for face in faces:
            try:
                adaptor = BRepAdaptor_Surface(face.wrapped)
                if adaptor.GetType() != GeomAbs_Cylinder:
                    continue
                cylinder = adaptor.Cylinder()
                radius   = cylinder.Radius()
                if radius <= 0 or radius > 500:
                    continue
                    
                fbb   = face.BoundingBox()
                cx = (fbb.xmax + fbb.xmin) / 2.0
                cy = (fbb.ymax + fbb.ymin) / 2.0
                cz = (fbb.zmax + fbb.zmin) / 2.0
                
                # Check for duplicates to prevent overcounting split cylinder faces
                is_dup = False
                for (sx, sy, sz) in seen_centers:
                    if abs(cx-sx) < 0.5 and abs(cy-sy) < 0.5 and abs(cz-sz) < 0.5:
                        is_dup = True
                        break
                if is_dup:
                    continue
                seen_centers.append((cx, cy, cz))
                
                diameter = round(radius * 2, 4)
                depth = round(max(fbb.xmax - fbb.xmin, fbb.ymax - fbb.ymin, fbb.zmax - fbb.zmin), 4)
                hole_type = "through" if depth > diameter * 0.5 else "blind"
                holes.append({"diameter": diameter, "depth": depth, "type": hole_type})
            except Exception:
                continue

    n_faces = len(faces)
    n_edges = len(edges)
    n_holes = len(holes)
    score   = n_faces * 1 + n_edges * 0.5 + n_holes * 10
    tier    = ("Simple" if score < 100 else "Moderate" if score < 300 else
               "Complex" if score < 800 else "Very Complex")

    return {
        "fileName":    original_name,
        "unit":        "Millimeter",
        "boundingBox": {"sizeX": size_x, "sizeY": size_y, "sizeZ": size_z},
        "volume":      volume,
        "surfaceArea": surface_area,
        "centroid":    centroid,
        "topology":    {"faces": n_faces, "edges": n_edges, "vertices": len(vertices)},
        "holes":       holes,
        "complexity":  {"score": round(score, 1), "tier": tier,
                        "faces": n_faces, "edges": n_edges, "holes": n_holes},
    }

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