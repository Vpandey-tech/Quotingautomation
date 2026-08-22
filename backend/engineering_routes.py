"""
Engineering Design API Routes — /api/design/*
Refactored architecture:
  - 1 Gemini Spec-Intake call per design (zero turn-by-turn LLM loops)
  - Deterministic parametric CAD builders (build123d / OpenCASCADE)
  - Hardened Code-Only Topological & DFM Validation Gate
  - Direct spec diffing for cheap incremental edits (0 LLM calls)
  - Byte-compatible quoting engine handoff with exact OpenCASCADE volume/surfaceArea
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time, os, uuid, json, logging, math, re

from services.engineering.params import (
    get_params_for_component, get_next_missing_param,
    validate_param, are_all_params_collected, COMPONENT_LABELS,
    COMPONENT_PARAMS, get_material, compute_smart_defaults,
    generate_clarification_questions, normalize_spec_keys,
    IntakeResult, ClarificationQuestion,
    DEFAULT_UNITS, DEFAULT_ORIGIN, DEFAULT_BASE_PLANE, DEFAULT_UP_AXIS
)
from services.engineering.math_engine import run_calculation
from services.engineering.knowledge_lookup import (
    get_kb_stats, search_kb, build_ai_context,
    safe_eval_formula, validate_calculation, reload_kb,
)
from services.engineering.report_generator import (
    build_report_markdown, generate_pdf_report,
)
from services.engineering.cad_engine import generate_cad as cad_generate, run_dfm_checks
from services.engineering.hardware import search_hardware_parts, get_hardware_step

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/design", tags=["Engineering Design"])

# ── In-Memory Session Store ───────────────────────────────────────────────────
_sessions: Dict[str, Dict[str, Any]] = {}

def _new_session(component_type: str) -> Dict[str, Any]:
    sid = str(uuid.uuid4())[:8]
    session = {
        "id": sid,
        "component_type": component_type,
        "status": "collecting_params",
        "params": {},
        "clarification_questions": [],
        "result": None,
        "cad_result": None,
        "messages": [],
        "token_usage": {
            "intake_calls": 0,
            "delta_parser_calls": 0,
            "failure_corrector_calls": 0,
            "total_tokens": 0
        },
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    _sessions[sid] = session
    return session

def _get_session(sid: str) -> Dict[str, Any]:
    s = _sessions.get(sid)
    if not s:
        raise HTTPException(404, "Session not found")
    return s

def _session_summary(s: Dict) -> Dict:
    return {
        "id": s["id"],
        "component_type": s["component_type"],
        "label": COMPONENT_LABELS.get(s["component_type"], s["component_type"].title()),
        "status": s["status"],
        "params": s["params"],
        "token_usage": s.get("token_usage", {}),
        "created_at": s["created_at"],
        "updated_at": s["updated_at"],
        "has_result": s["result"] is not None,
        "has_cad": s.get("cad_file_path") is not None,
    }

# ── Pydantic Request Models ───────────────────────────────────────────────────
class CreateSessionBody(BaseModel):
    component_type: str = Field(default="custom")
    custom_description: Optional[str] = None

class SpecIntakeBody(BaseModel):
    message: str

class BatchAnswersBody(BaseModel):
    answers: Dict[str, Any]

class PatchParamBody(BaseModel):
    params: Dict[str, Any]

class KBSearchBody(BaseModel):
    domain: Optional[str] = None
    topic: Optional[str] = None
    entry_type: Optional[str] = None

class FormulaEvalBody(BaseModel):
    domain: str
    topic: str
    inputs: Dict[str, float]


# ── Gemini Helpers with Exact Call Budget & Token Tracking ─────────────────────

async def call_gemini_spec_intake(user_prompt: str, session: Dict[str, Any]) -> IntakeResult:
    """
    Step 1: ONE Gemini Flash-tier call per design session.
    Extracts structured parameters and returns batched clarification questions.
    """
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash-001"
    ]

    prompt = f"""You are an expert Mechanical Design Engineering System.
Analyze the following user design request:
"{user_prompt}"

TASK:
1. Classify the part into one of the canonical builder component families:
   - "shaft": Cylindrical drive shafts, axles, spindles (power, speed, torque, keyways)
   - "flange": Circular or ring-shaped flanges with bolt circle patterns (PCD, outer dia, bore, thickness)
   - "plate_hole_pattern": Flat plates or baseplates with linear/circular mounting holes
   - "bracket": L-brackets, U-brackets, or mounting plates with wall thickness and holes
   - "spacer": Bushings, standoffs, or collars with inner bore and outer diameter
   - "lever": Pivot lever arms, linkages, rocker arms with pivot bore and load bore
   - "housing": Protective casings, enclosures, covers, or gearbox shells
   - "bearing": Ball or roller bearings (loads, speed, life)
   - "gearbox": Gear transmission systems (power, ratio, stages)
   - "cam": Cam disc motion profiles (rise, dwell, lift)
   - "custom": Any other mechanical part

2. Extract all explicitly mentioned or strongly implied numeric dimensions (mm), materials, loads, and features into "extracted_spec".

3. If required dimensions are missing for that component family, formulate them as clear clarification questions.

Return ONLY a valid JSON object matching this schema:
{{
  "component_family": "flange",
  "extracted_spec": {{
    "outer_diameter_mm": 150.0,
    "thickness_mm": 20.0,
    "material_id": "steel_1045"
  }},
  "clarification_questions": [
    {{
      "field": "bolt_circle_diameter_mm",
      "label": "Bolt Circle Diameter (PCD)",
      "question": "What is the Bolt Circle Diameter (PCD) in mm?",
      "type": "number",
      "unit": "mm",
      "default_value": 110.0
    }}
  ],
  "confidence_score": 0.95
}}"""

    import google.generativeai as genai
    for key_idx in [1, 2]:
        api_key = os.getenv("GEMINI_API_KEY_2" if key_idx == 2 else "GEMINI_API_KEY", "")
        if not api_key:
            continue
        genai.configure(api_key=api_key)
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = await run_in_threadpool(
                    model.generate_content,
                    [prompt],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0,
                        response_mime_type="application/json"
                    )
                )
                text = response.text.strip()
                data = json.loads(text)
                
                # Track token usage
                session["token_usage"]["intake_calls"] += 1
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    session["token_usage"]["total_tokens"] += getattr(response.usage_metadata, "total_token_count", 0)
                    
                logger.info(f"✓ Gemini Spec-Intake succeeded on {model_name} (Call count: {session['token_usage']['intake_calls']})")
                
                comp_family = data.get("component_family", "custom").lower()
                extracted_spec = normalize_spec_keys(data.get("extracted_spec", {}))
                
                # Generate programmatically synchronized questions from params.py
                programmatic_qs = generate_clarification_questions(comp_family, extracted_spec)
                
                return IntakeResult(
                    component_family=comp_family,
                    extracted_spec=extracted_spec,
                    clarification_questions=programmatic_qs,
                    confidence_score=float(data.get("confidence_score", 0.9))
                )
            except Exception as e:
                logger.warning(f"Spec intake failed on {model_name}: {e}")
                continue

    # Fallback if Gemini is unreachable (Heuristic parsing, 0 API calls)
    return _heuristic_spec_intake(user_prompt)


def _heuristic_spec_intake(text: str) -> IntakeResult:
    import re
    t = text.lower()
    comp_family = "custom"
    if "flange" in t:
        comp_family = "flange"
    elif "shaft" in t or "axle" in t or "spindle" in t:
        comp_family = "shaft"
    elif "bracket" in t or "angle" in t:
        comp_family = "bracket"
    elif "plate" in t:
        comp_family = "plate_hole_pattern"
    elif "spacer" in t or "bushing" in t or "collar" in t:
        comp_family = "spacer"
    elif "lever" in t:
        comp_family = "lever"
    elif "housing" in t or "enclosure" in t or "casing" in t:
        comp_family = "housing"

    spec = {}
    # Extract numbers with units
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*(?:mm|dia|diameter|thk|thick|length)", t)
    if nums:
        if comp_family == "shaft":
            spec["diameter_mm"] = float(nums[0])
            if len(nums) > 1:
                spec["length_mm"] = float(nums[1])
        elif comp_family == "flange":
            spec["outer_diameter_mm"] = float(nums[0])
            if len(nums) > 1:
                spec["thickness_mm"] = float(nums[1])

    qs = generate_clarification_questions(comp_family, spec)
    return IntakeResult(
        component_family=comp_family,
        extracted_spec=spec,
        clarification_questions=qs,
        confidence_score=0.7
    )


async def call_gemini_delta_parser(free_text: str, session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 4: Delta Param Parser — called ONLY when follow-up answers are unstructured paragraphs.
    """
    missing_qs = session.get("clarification_questions", [])
    prompt = f"""Extract parameter answers from this user message: "{free_text}"
Component Family: {session['component_type']}
Target Parameters:
{json.dumps([q if isinstance(q, dict) else q.dict() for q in missing_qs], indent=2)}

Return ONLY a valid JSON object mapping parameter keys to their parsed values."""

    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = await run_in_threadpool(
                model.generate_content,
                [prompt],
                generation_config=genai.types.GenerationConfig(temperature=0.0, response_mime_type="application/json")
            )
            session["token_usage"]["delta_parser_calls"] += 1
            return json.loads(response.text.strip())
        except Exception as e:
            logger.warning(f"Delta parser failed: {e}")

    return {}


async def call_gemini_error_corrector(error_details: Dict[str, Any], session: Dict[str, Any]) -> str:
    """
    Step 4: Fallback Error-Corrector — called ONLY when CAD validation / DFM fails.
    Uses reasoning model to explain the geometric conflict.
    """
    prompt = f"""You are a senior mechanical engineering auditor.
A CAD model generation failed validation checks with the following diagnostic error:
Component: {session['component_type']}
Spec: {json.dumps(session['params'], indent=2)}
Error: {json.dumps(error_details, indent=2)}

Explain clearly and concisely in 2-3 sentences what went wrong geometrically, why it violates manufacturing/CAD standards, and what parameter values the user should change to fix it."""

    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-pro")
            response = await run_in_threadpool(model.generate_content, [prompt])
            session["token_usage"]["failure_corrector_calls"] += 1
            return response.text.strip()
        except Exception:
            pass

    return f"Geometric validation failed: {error_details.get('message', 'Parameter conflict detected.')}"


@router.get("/sessions")
async def list_sessions():
    """List all design sessions sorted by creation time descending."""
    sessions = sorted(_sessions.values(), key=lambda s: s["created_at"], reverse=True)
    return [_session_summary(s) for s in sessions]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session from in-memory store."""
    if session_id in _sessions:
        del _sessions[session_id]
        return {"deleted": True, "session_id": session_id}
    raise HTTPException(404, "Session not found")


@router.get("/components")
async def list_components():
    """List all supported component families and their parameter definitions."""
    return {
        ct: {"label": COMPONENT_LABELS.get(ct, ct.title()), "params": params}
        for ct, params in COMPONENT_PARAMS.items()
    }


@router.get("/components/{component_type}/params")
async def get_component_params(component_type: str):
    """Get parameter definitions for a specific component type."""
    params = get_params_for_component(component_type)
    if not params:
        raise HTTPException(404, f"Unknown component type: {component_type}")
    return {
        "component_type": component_type,
        "label": COMPONENT_LABELS.get(component_type, component_type.title()),
        "params": params,
    }


@router.post("/sessions")
async def create_session(body: CreateSessionBody):
    session = _new_session(body.component_type)
    if body.custom_description:
        session["custom_description"] = body.custom_description
        # Execute single spec intake call
        intake_res = await call_gemini_spec_intake(body.custom_description, session)
        session["component_type"] = intake_res.component_family
        session["params"].update(intake_res.extracted_spec)
        session["clarification_questions"] = [q.dict() for q in intake_res.clarification_questions]
        if len(intake_res.clarification_questions) == 0:
            session["status"] = "params_complete"

    return {
        **_session_summary(session),
        "clarification_questions": session.get("clarification_questions", []),
        "all_params_collected": len(session.get("clarification_questions", [])) == 0,
        "custom_description": session.get("custom_description"),
        "cad_result": session.get("cad_result"),
    }



@router.post("/sessions/{session_id}/spec-intake")
async def single_spec_intake(session_id: str, body: SpecIntakeBody):
    """
    One-pass Spec Gathering Endpoint (1 Gemini Call).
    Extracts structured spec and returns batched questions.
    """
    session = _get_session(session_id)
    intake_res = await call_gemini_spec_intake(body.message, session)

    session["component_type"] = intake_res.component_family
    session["params"].update(intake_res.extracted_spec)
    session["clarification_questions"] = [q.dict() for q in intake_res.clarification_questions]

    if "custom_description" not in session or not session["custom_description"]:
        session["custom_description"] = body.message

    if len(intake_res.clarification_questions) == 0:
        session["status"] = "params_complete"

    session["updated_at"] = time.time()

    return {
        **_session_summary(session),
        "component_family": intake_res.component_family,
        "extracted_spec": session["params"],
        "clarification_questions": session["clarification_questions"],
        "all_params_collected": len(session["clarification_questions"]) == 0,
        "custom_description": session.get("custom_description"),
        "cad_result": session.get("cad_result"),
        "token_usage": session["token_usage"],
    }


@router.post("/sessions/{session_id}/params/batch")
async def submit_batch_params(session_id: str, body: BatchAnswersBody):
    """
    Deterministic Batch Answer Submission (0 LLM Calls).
    Merges user answers into spec in-memory and re-evaluates completeness.
    """
    session = _get_session(session_id)
    for k, v in body.answers.items():
        if v is not None and str(v).strip() != "":
            try:
                # Type cast numbers
                if isinstance(v, str) and re.match(r"^[-+]?\d*\.?\d+$", v.strip()):
                    session["params"][k] = float(v.strip())
                else:
                    session["params"][k] = v
            except Exception:
                session["params"][k] = v

    # Re-evaluate missing questions
    remaining_qs = generate_clarification_questions(session["component_type"], session["params"])
    session["clarification_questions"] = [q.dict() for q in remaining_qs]

    if len(remaining_qs) == 0:
        session["status"] = "params_complete"

    session["updated_at"] = time.time()

    return {
        "session_id": session_id,
        "status": session["status"],
        "params": session["params"],
        "clarification_questions": session["clarification_questions"],
        "all_params_collected": len(remaining_qs) == 0,
        "custom_description": session.get("custom_description"),
        "cad_result": session.get("cad_result"),
        "token_usage": session["token_usage"],
    }


@router.patch("/sessions/{session_id}/params")
async def patch_params_fast(session_id: str, body: PatchParamBody):
    """
    Lightweight Spec Patch & Re-Solve Endpoint (< 200ms, 0 LLM Calls).
    Updates delta parameters and re-runs deterministic builders instantly.
    """
    session = _get_session(session_id)
    session["params"].update(body.params)
    session["updated_at"] = time.time()

    # Re-run calculations deterministically
    try:
        calc_result = run_calculation(session["component_type"], session["params"])
        session["result"] = calc_result
    except Exception as ce:
        logger.warning(f"Recalculation note: {ce}")

    # Re-run CAD generation if previously ready
    cad_info = None
    if session["status"] in ("report_approved", "cad_ready"):
        dims = session.get("result", {}).get("dimensions", session["params"])
        cad_res = cad_generate(session["component_type"], dims, session["params"])
        session["cad_result"] = cad_res
        if cad_res.get("validation_status") == "PASS":
            session["cad_file_path"] = cad_res.get("step_file")
            session["status"] = "cad_ready"
            cad_info = cad_res

    return {
        "session_id": session_id,
        "status": session["status"],
        "params": session["params"],
        "cad_info": cad_info,
        "cad_result": session.get("cad_result"),
        "custom_description": session.get("custom_description"),
        "token_usage": session["token_usage"],
    }


# ── Report & CAD Generation Endpoints ──────────────────────────────────────────

@router.post("/sessions/{session_id}/generate-report")
async def generate_report(session_id: str):
    session = _get_session(session_id)
    # Allow report generation if status is params_complete, or if there are params and
    # no blocking required questions remain (handles stale clarification_questions)
    remaining = generate_clarification_questions(session["component_type"], session["params"])
    if remaining and session["status"] == "collecting_params":
        raise HTTPException(400, "Please complete all required specifications before generating a report.")
    # Mark complete if it wasn't already
    if not remaining and session["status"] == "collecting_params":
        session["status"] = "params_complete"
        session["clarification_questions"] = []


    assumptions = compute_smart_defaults(session["component_type"], session["params"])
    for a in assumptions:
        if a["key"] not in session["params"] or session["params"][a["key"]] is None:
            session["params"][a["key"]] = a["default_value"]

    try:
        result = run_calculation(session["component_type"], session["params"])
    except Exception as e:
        raise HTTPException(500, f"Calculation error: {str(e)}")

    session["result"] = result
    session["status"] = "report_ready"
    session["updated_at"] = time.time()

    try:
        session["report_markdown"] = build_report_markdown(
            session["component_type"], session["params"], result, session_id
        )
    except Exception:
        session["report_markdown"] = None

    try:
        session["report_pdf_path"] = generate_pdf_report(
            session["component_type"], session["params"], result, session_id
        )
    except Exception:
        session["report_pdf_path"] = None

    return {
        "session_id": session_id,
        "status": "report_ready",
        "result": result,
        "has_pdf": session.get("report_pdf_path") is not None,
        "has_markdown": session.get("report_markdown") is not None,
    }


@router.post("/sessions/{session_id}/approve-report")
async def approve_report(session_id: str):
    session = _get_session(session_id)
    session["status"] = "report_approved"
    session["updated_at"] = time.time()
    return {"status": "report_approved", "session_id": session_id}


@router.post("/sessions/{session_id}/generate-cad")
async def generate_cad_endpoint(session_id: str):
    """
    Deterministic CAD generation + Hardened OpenCASCADE Validation Gate.
    0 LLM calls in happy path; 1 call only on validation failure to explain error.
    """
    session = _get_session(session_id)
    if session["status"] not in ("report_approved", "report_ready", "params_complete"):
        raise HTTPException(400, "Approve the report or complete parameters before generating CAD.")

    dims = session.get("result", {}).get("dimensions", session["params"])
    ctype = session["component_type"]

    cad_result = cad_generate(ctype, dims, session["params"])
    session["cad_result"] = cad_result

    # If CAD validation failed, invoke fallback reasoner (1 call)
    if cad_result.get("validation_status") != "PASS":
        failure_explanation = await call_gemini_error_corrector(cad_result.get("error", {}), session)
        return JSONResponse(
            status_code=422,
            content={
                "status": "cad_failed",
                "session_id": session_id,
                "error": cad_result.get("error"),
                "explanation": failure_explanation,
                "token_usage": session["token_usage"]
            }
        )

    step_path = cad_result.get("step_file")
    session["cad_file_path"] = step_path
    session["status"] = "cad_ready"
    session["updated_at"] = time.time()

    return {
        "status": "cad_ready",
        "session_id": session_id,
        "engine": cad_result.get("engine", "build123d"),
        "step_file": step_path,
        "download_url": f"/api/design/sessions/{session_id}/download-cad",
        "dimensions": dims,
        "volume": cad_result.get("volume"),
        "surface_area": cad_result.get("surface_area"),
        "token_usage": session["token_usage"],
    }


# ── Auto-Transfer to Quoting Engine (Byte-For-Byte Compatible Contract) ────────

@router.post("/sessions/{session_id}/send-to-quoting")
async def send_to_quoting(session_id: str):
    """
    Transfer design data to the quoting engine.
    Contract payload schema is 100% byte-compatible with the quoting module,
    with metrics.volume and metrics.surfaceArea derived from exact OpenCASCADE measurements.
    """
    session = _get_session(session_id)
    if session["status"] not in ("cad_ready", "report_approved"):
        raise HTTPException(400, "Generate CAD or approve report first.")

    result = session.get("result", {})
    dims = result.get("dimensions", session["params"])
    params = session.get("params", {})
    ctype = session["component_type"]
    cad_res = session.get("cad_result", {})

    # Use exact OpenCASCADE measured values when available
    volume = cad_res.get("volume")
    surface_area = cad_res.get("surface_area")

    size_x = float(dims.get("length_mm", dims.get("outer_diameter_mm", 100.0)))
    size_y = float(dims.get("width_mm", dims.get("outer_diameter_mm", 50.0)))
    size_z = float(dims.get("height_mm", dims.get("thickness_mm", 25.0)))

    # Fallback analytical calculation if CAD not yet measured
    if not volume or volume <= 0:
        if ctype == "shaft":
            d = float(dims.get("diameter_mm", 30))
            L = float(dims.get("length_mm", 300))
            volume = math.pi * ((d/2)**2) * L
            surface_area = 2 * math.pi * (d/2) * (d/2 + L)
            size_x, size_y, size_z = L, d, d
        elif ctype == "flange":
            od = float(dims.get("outer_diameter_mm", 150))
            th = float(dims.get("thickness_mm", 20))
            volume = math.pi * ((od/2)**2) * th
            surface_area = 2 * math.pi * (od/2) * (od/2 + th)
            size_x, size_y, size_z = od, od, th
        else:
            volume = size_x * size_y * size_z
            surface_area = 2 * (size_x*size_y + size_y*size_z + size_z*size_x)

    mat = params.get("material_id", "steel_1045")
    mat_obj = get_material(mat)
    detected_material = mat_obj.get("name", "Steel")

    has_cad_file = bool(session.get("cad_file_path") and os.path.isfile(session.get("cad_file_path", "")))

    return {
        "session_id": session_id,
        "transferred": True,
        "component_type": ctype,
        "has_cad_file": has_cad_file,
        "download_url": f"/api/design/sessions/{session_id}/download-cad" if has_cad_file else None,
        "metrics": {
            "volume": round(float(volume), 2),
            "surfaceArea": round(float(surface_area), 2),
            "sizeX": round(size_x, 2),
            "sizeY": round(size_y, 2),
            "sizeZ": round(size_z, 2),
            "material": detected_material,
            "quantity": int(params.get("quantity", 1)),
        },
        "engineering_data": {
            "params": params,
            "calculations": result.get("calculations", []),
            "safety": result.get("safety", {}),
            "dimensions": dims,
            "standards": result.get("standards", []),
        },
    }


# ── File Downloads & Utilities ────────────────────────────────────────────────

@router.get("/sessions/{session_id}/download-cad")
async def download_cad(session_id: str):
    session = _get_session(session_id)
    fpath = session.get("cad_file_path")
    if not fpath or not os.path.isfile(fpath):
        raise HTTPException(404, "No CAD file generated yet.")
    return FileResponse(fpath, media_type="application/octet-stream",
                        filename=f"AccuDesign_{session['component_type']}_{session_id}.step")

@router.get("/sessions/{session_id}/download-pdf")
async def download_pdf(session_id: str):
    session = _get_session(session_id)
    fpath = session.get("report_pdf_path")
    if not fpath or not os.path.isfile(fpath):
        raise HTTPException(404, "No PDF report generated yet.")
    return FileResponse(fpath, media_type="application/pdf",
                        filename=f"AccuDesign_Report_{session['component_type']}_{session_id}.pdf")

@router.get("/sessions/{session_id}/report")
async def get_report(session_id: str):
    session = _get_session(session_id)
    if not session["result"]:
        raise HTTPException(404, "No report generated yet.")
    return {
        "session_id": session_id,
        "component_type": session["component_type"],
        "label": COMPONENT_LABELS.get(session["component_type"], ""),
        "params": session["params"],
        "result": session["result"],
        "status": session["status"],
    }

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = _get_session(session_id)
    assumptions = compute_smart_defaults(session["component_type"], session["params"])
    return {
        **_session_summary(session),
        "messages": session.get("messages", []),
        "clarification_questions": session.get("clarification_questions", []),
        "assumptions": assumptions,
        "all_params_collected": len(session.get("clarification_questions", [])) == 0,
        "custom_description": session.get("custom_description"),
        "cad_result": session.get("cad_result"),
        "cad_file_path": session.get("cad_file_path"),
        "result": session.get("result"),
    }

@router.get("/hardware/search")
async def search_hardware(q: str):
    """Off-the-shelf standard hardware lookup (step.parts)."""
    return await search_hardware_parts(q)

@router.get("/stats")
async def design_stats():
    sessions = list(_sessions.values())
    kb = get_kb_stats()
    return {
        "totalSessions": len(sessions),
        "approvedReports": sum(1 for s in sessions if s["status"] == "report_approved"),
        "completedDesigns": sum(1 for s in sessions if s["status"] in ("cad_ready",)),
        "byComponentType": {
            ct: sum(1 for s in sessions if s["component_type"] == ct)
            for ct in COMPONENT_LABELS
        },
        "knowledgeBase": kb,
    }
