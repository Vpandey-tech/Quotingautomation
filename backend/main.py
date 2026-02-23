"""
AccuDesign Quoting Agent — Phase 3 Backend
FastAPI + CadQuery geometry analysis + Live pricing + Quote engine

Endpoints:
  GET  /api/health              — Health check
  GET  /api/materials           — All supported materials
  GET  /api/processes           — All manufacturing processes
  GET  /api/tolerances          — All tolerance tiers
  GET  /api/prices              — Current metal prices (live or cached)
  POST /api/analyze             — Upload STEP → B-Rep geometry analysis
  POST /api/quote               — Full quote from geometry + selections
  POST /api/quote/pdf           — Full quote as downloadable PDF

Run:
  py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.background import BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
import tempfile, os
from dotenv import load_dotenv

load_dotenv()

from services.pricing import MATERIALS, get_live_prices
from services.costing import compute_quote, TOLERANCE_MULTIPLIERS, PROCESS_RATES
from services.pdf import generate_quote_pdf

app = FastAPI(
    title="AccuDesign Quoting API",
    description="Phase 3: Live metal pricing + MRR-based quote engine",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Open for local dev. Lock to domain on prod.
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────
class QuoteRequest(BaseModel):
    geometry:     dict  = Field(..., description="Result from /api/analyze or mesh fallback")
    material_id:  str   = Field(..., example="aluminum_6061")
    process_id:   str   = Field(..., example="cnc_milling_3ax")
    tolerance_id: str   = Field("standard", example="standard")
    quantity:     int   = Field(1, ge=1, le=10000)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "phase": 3,
        "version": "0.3.0",
        "materials": len(MATERIALS),
        "processes": len(PROCESS_RATES),
        "tolerances": len(TOLERANCE_MULTIPLIERS),
    }


# ── Materials & Processes catalogue ───────────────────────────────────────────
@app.get("/api/materials", tags=["Catalogue"])
def get_materials():
    """Return all supported materials with properties."""
    return {
        mid: {
            "name":          m["name"],
            "density":       m["density"],
            "price_usd_kg":  m["price_usd_kg"],
            "machinability": m["machinability"],
        }
        for mid, m in MATERIALS.items()
    }


@app.get("/api/processes", tags=["Catalogue"])
def get_processes():
    """Return all supported manufacturing processes."""
    return {
        pid: {
            "name":      p["name"],
            "rate_hr":   p["rate_hr"],
            "setup_usd": p["setup_usd"],
            "axes":      p["axes"],
        }
        for pid, p in PROCESS_RATES.items()
    }


@app.get("/api/tolerances", tags=["Catalogue"])
def get_tolerances():
    """Return all supported tolerance tiers."""
    return {
        tid: {
            "label":      t["label"],
            "multiplier": t["multiplier"],
        }
        for tid, t in TOLERANCE_MULTIPLIERS.items()
    }


# ── Live metal prices ─────────────────────────────────────────────────────────
@app.get("/api/prices", tags=["Pricing"])
async def get_prices():
    """
    Fetch current metal prices.
    Priority: metals.dev → World Bank → hardcoded fallback.
    Results are cached for 6 hours.
    """
    return await get_live_prices()


# ── STEP File Analysis ────────────────────────────────────────────────────────
@app.post("/api/analyze", tags=["Geometry"])
async def analyze_step(file: UploadFile = File(...)):
    """
    Upload a STEP file → returns full B-Rep geometric analysis via CadQuery.
    This result is then passed verbatim to /api/quote.
    Falls back gracefully — even if CadQuery fails, /api/quote still works
    with the mesh-derived geometry from the frontend.
    """
    fname = (file.filename or "").lower()
    if not (fname.endswith('.step') or fname.endswith('.stp')):
        raise HTTPException(400, "Only STEP/STP files are accepted.")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "Uploaded file is empty.")

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


# ── Quote endpoint ────────────────────────────────────────────────────────────
@app.post("/api/quote", tags=["Quoting"])
async def generate_quote(req: QuoteRequest):
    """
    Generate a full manufacturing quote.

    Steps:
    1. Validate material/process/tolerance IDs
    2. Fetch live metal price for selected material
    3. Run MRR-based machining time estimation
    4. Apply complexity, tolerance, overhead, profit multipliers
    5. Return itemised cost breakdown
    """
    if req.material_id not in MATERIALS:
        raise HTTPException(400, f"Unknown material: '{req.material_id}'. "
                                 f"Valid values: {list(MATERIALS.keys())}")
    if req.process_id not in PROCESS_RATES:
        raise HTTPException(400, f"Unknown process: '{req.process_id}'. "
                                 f"Valid values: {list(PROCESS_RATES.keys())}")
    if req.tolerance_id not in TOLERANCE_MULTIPLIERS:
        raise HTTPException(400, f"Unknown tolerance: '{req.tolerance_id}'. "
                                 f"Valid values: {list(TOLERANCE_MULTIPLIERS.keys())}")

    # Get live price for this material
    price_data = await get_live_prices()
    metal_price = price_data["prices"].get(
        req.material_id,
        MATERIALS[req.material_id]["price_usd_kg"]  # fallback
    )

    try:
        quote = compute_quote(
            geometry=req.geometry,
            material_id=req.material_id,
            process_id=req.process_id,
            tolerance_id=req.tolerance_id,
            quantity=req.quantity,
            metal_price=metal_price,
        )
        quote["price_source"] = price_data["source"]
        quote["price_note"]   = price_data.get("note", "")
        return JSONResponse(content=quote)
    except Exception as e:
        import traceback
        print(f"\n{'='*60}\n[QUOTE ERROR]\n{traceback.format_exc()}\n{'='*60}\n")
        raise HTTPException(500, f"Quote computation failed: {str(e)}")


# ── PDF quote endpoint ────────────────────────────────────────────────────────
@app.post("/api/quote/pdf", tags=["Quoting"])
async def generate_quote_pdf_endpoint(req: QuoteRequest, background_tasks: BackgroundTasks):
    """Generate a full manufacturing quote and return as downloadable PDF."""
    if req.material_id not in MATERIALS:
        raise HTTPException(400, f"Unknown material: '{req.material_id}'")
    if req.process_id not in PROCESS_RATES:
        raise HTTPException(400, f"Unknown process: '{req.process_id}'")
    if req.tolerance_id not in TOLERANCE_MULTIPLIERS:
        raise HTTPException(400, f"Unknown tolerance: '{req.tolerance_id}'")

    price_data = await get_live_prices()
    metal_price = price_data["prices"].get(
        req.material_id,
        MATERIALS[req.material_id]["price_usd_kg"]
    )

    try:
        quote = compute_quote(
            geometry=req.geometry,
            material_id=req.material_id,
            process_id=req.process_id,
            tolerance_id=req.tolerance_id,
            quantity=req.quantity,
            metal_price=metal_price,
        )
        quote["price_source"] = price_data["source"]
        pdf_path = generate_quote_pdf(quote)
        background_tasks.add_task(_safe_delete, pdf_path)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename="AccuDesign_Quote.pdf"
        )
    except Exception as e:
        import traceback
        print(f"\n{'='*60}\n[PDF ERROR]\n{traceback.format_exc()}\n{'='*60}\n")
        raise HTTPException(500, f"PDF generation failed: {str(e)}")


def _safe_delete(path: str):
    """Delete a file, ignoring errors (used as background task after FileResponse)."""
    try:
        os.unlink(path)
    except Exception:
        pass


# ── Private: CadQuery geometry analysis ───────────────────────────────────────
def _analyze_with_cadquery(path: str, original_name: str) -> dict:
    """
    Full B-Rep analysis using CadQuery.
    Extracts: bounding box, volume, surface area, holes, complexity score.

    CadQuery Solid API (cadquery 2.x):
      .BoundingBox() → bb.xmin/xmax/ymin/ymax/zmin/zmax
      .Volume()      → float, mm³
      .Area()        → float, mm²
      .Center()      → Vector with .x/.y/.z   ← NOT CenterOfMass()
      .Faces()       → list of Face objects
      .Edges()       → list of Edge objects
      .Vertices()    → list of Vertex objects
    """
    import traceback

    try:
        import cadquery as cq
    except Exception as e:
        raise RuntimeError(f"CadQuery import failed: {e}")

    # OCC imports for hole detection — handle both OCC.Core and OCP install paths
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
            pass  # Hole detection gracefully skipped

    try:
        shape = cq.importers.importStep(path)
    except Exception as e:
        raise RuntimeError(f"STEP file import failed: {e}")

    solid = shape.val()

    # ── Bounding box ──────────────────────────────────────────────────────────
    bb     = solid.BoundingBox()
    size_x = round(bb.xmax - bb.xmin, 4)
    size_y = round(bb.ymax - bb.ymin, 4)
    size_z = round(bb.zmax - bb.zmin, 4)

    # ── Volume & Surface ──────────────────────────────────────────────────────
    volume       = round(abs(solid.Volume()), 4)   # mm³
    surface_area = round(solid.Area(), 4)           # mm²

    # ── Center of mass — CadQuery uses .Center() NOT .CenterOfMass() ─────────
    try:
        centroid_vec = solid.Center()
        centroid = {"x": round(centroid_vec.x, 4),
                    "y": round(centroid_vec.y, 4),
                    "z": round(centroid_vec.z, 4)}
    except Exception:
        centroid = {"x": 0.0, "y": 0.0, "z": 0.0}

    # ── Topology ──────────────────────────────────────────────────────────────
    faces    = solid.Faces()
    edges    = solid.Edges()
    vertices = solid.Vertices()

    # ── Hole detection via OCC cylindrical face adaptor ───────────────────────
    holes = []
    if BRepAdaptor_Surface and GeomAbs_Cylinder:
        for face in faces:
            try:
                adaptor = BRepAdaptor_Surface(face.wrapped)
                if adaptor.GetType() != GeomAbs_Cylinder:
                    continue
                cylinder = adaptor.Cylinder()
                radius   = cylinder.Radius()
                if radius <= 0 or radius > 500:   # sanity filter (mm)
                    continue
                diameter = round(radius * 2, 4)
                # Bounding box of the face to estimate depth
                fbb   = face.BoundingBox()
                depth = round(max(
                    fbb.xmax - fbb.xmin,
                    fbb.ymax - fbb.ymin,
                    fbb.zmax - fbb.zmin,
                ), 4)
                hole_type = "through" if depth > diameter * 0.5 else "blind"
                holes.append({"diameter": diameter, "depth": depth, "type": hole_type})
            except Exception:
                continue  # Skip malformed faces gracefully

    # ── Complexity scoring ────────────────────────────────────────────────────
    n_faces = len(faces)
    n_edges = len(edges)
    n_holes = len(holes)
    score   = n_faces * 1 + n_edges * 0.5 + n_holes * 10
    tier    = ("Simple"       if score < 100  else
               "Moderate"     if score < 300  else
               "Complex"      if score < 800  else "Very Complex")

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
