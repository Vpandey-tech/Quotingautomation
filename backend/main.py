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
from fastapi.responses import JSONResponse, FileResponse
from fastapi.background import BackgroundTasks
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
    process_id:     str  = Field(..., example="cnc_milling_3ax")
    tolerance_id:   str  = Field("standard", example="standard")
    quantity:       int  = Field(1, ge=1, le=10000)
    client_name:    str  = Field("", example="Vishal Jadhav")
    client_company: str  = Field("", example="Aerochamp Aviation (Intl.) Pvt. Ltd.")
    source_filename: str = Field("", example="shaft_drawing.pdf")
    screenshot:     Optional[str] = Field(None, description="Base64 isometric view screenshot")


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
        raise HTTPException(500, "PDF analysis failed. Check server logs.")

    return JSONResponse(content=result)


def _run_pdf_analysis(pdf_bytes: bytes, filename: str):
    """Synchronous wrapper for PDF analysis (runs in threadpool)."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(analyze_pdf_drawing(pdf_bytes, filename))
    finally:
        loop.close()


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
    if req.process_id not in PROCESS_RATES:
        raise HTTPException(400, f"Unknown process: '{req.process_id}'. "
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
            process_id=req.process_id,
            tolerance_id=req.tolerance_id,
            quantity=req.quantity,
            metal_price_inr=metal_price_inr,
            exchange_rate=rate,
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
    if req.process_id not in PROCESS_RATES:
        raise HTTPException(400, f"Unknown process: '{req.process_id}'")
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
            process_id=req.process_id,
            tolerance_id=req.tolerance_id,
            quantity=req.quantity,
            metal_price_inr=metal_price_inr,
            exchange_rate=rate,
        )
        quote["price_source"] = price_data["source"]
        quote["quote_number"] = quote_number

        pdf_path = generate_quote_pdf(
            quote_data=quote,
            quote_number=quote_number,
            client_name=req.client_name,
            client_company=req.client_company,
            source_filename=req.source_filename,
            screenshot_b64=req.screenshot,
        )
        background_tasks.add_task(_safe_delete, pdf_path)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"AccuDesign_Quote_{quote_number.replace('/', '_')}.pdf"
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
                diameter = round(radius * 2, 4)
                fbb   = face.BoundingBox()
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
