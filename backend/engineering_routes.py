"""
Engineering Design API Routes — /api/design/*
Completely separate from the existing quoting engine endpoints.
Now with:
  - Editable parameters (edit after submission)
  - Knowledge Base stats & search
  - Gemini AI cross-validation agent
"""

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time, os, uuid, json

from services.engineering.params import (
    get_params_for_component, get_next_missing_param,
    validate_param, are_all_params_collected, COMPONENT_LABELS,
    COMPONENT_PARAMS, get_material,
)
from services.engineering.math_engine import run_calculation
from services.engineering.knowledge_lookup import (
    get_kb_stats, search_kb, build_ai_context,
    safe_eval_formula, validate_calculation, reload_kb,
)

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
        "result": None,
        "messages": [],
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
        "label": COMPONENT_LABELS.get(s["component_type"], ""),
        "status": s["status"],
        "params": s["params"],
        "created_at": s["created_at"],
        "updated_at": s["updated_at"],
        "has_result": s["result"] is not None,
    }

# ── Pydantic Models ───────────────────────────────────────────────────────────
class CreateSessionBody(BaseModel):
    component_type: str = Field(..., pattern="^(shaft|bearing|gearbox|cam|custom)$")
    custom_description: Optional[str] = None

class SubmitParamBody(BaseModel):
    key: str
    value: Any

class EditParamBody(BaseModel):
    key: str
    value: Any

class CustomChatBody(BaseModel):
    message: str

class KBSearchBody(BaseModel):
    domain: Optional[str] = None
    topic: Optional[str] = None
    entry_type: Optional[str] = None

class FormulaEvalBody(BaseModel):
    domain: str
    topic: str
    inputs: Dict[str, float]


# ── Knowledge Base Endpoints ─────────────────────────────────────────────────
@router.get("/knowledge-base/stats")
async def kb_stats():
    """Get knowledge base statistics — total entries, domains, type breakdown."""
    return get_kb_stats()


@router.post("/knowledge-base/search")
async def kb_search(body: KBSearchBody):
    """Search the knowledge base by domain, topic, or type."""
    results = search_kb(domain=body.domain, topic=body.topic, entry_type=body.entry_type)
    return {"count": len(results), "results": results}


@router.post("/knowledge-base/evaluate")
async def kb_evaluate(body: FormulaEvalBody):
    """Evaluate a specific formula from the knowledge base with given inputs."""
    result = validate_calculation(body.domain, body.topic, body.inputs)
    return result


@router.post("/knowledge-base/reload")
async def kb_reload():
    """Force-reload the knowledge base from disk."""
    kb = reload_kb()
    return {"reloaded": True, "total_entries": len(kb)}


# ── Stats ─────────────────────────────────────────────────────────────────────
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


@router.get("/components")
async def list_components():
    return {
        ct: {"label": COMPONENT_LABELS[ct], "params": params}
        for ct, params in COMPONENT_PARAMS.items()
    }


@router.get("/components/{component_type}/params")
async def get_component_params(component_type: str):
    params = get_params_for_component(component_type)
    if not params:
        raise HTTPException(404, f"Unknown component type: {component_type}")
    return {
        "component_type": component_type,
        "label": COMPONENT_LABELS.get(component_type, component_type),
        "params": params,
    }


@router.get("/sessions")
async def list_sessions():
    sessions = sorted(_sessions.values(), key=lambda s: s["created_at"], reverse=True)
    return [
        {
            "id": s["id"], "component_type": s["component_type"],
            "status": s["status"], "params": s["params"],
            "created_at": s["created_at"], "updated_at": s["updated_at"],
            "has_result": s["result"] is not None,
        }
        for s in sessions
    ]


@router.post("/sessions")
async def create_session(body: CreateSessionBody):
    session = _new_session(body.component_type)
    if body.custom_description:
        session["custom_description"] = body.custom_description
        session["custom_chat"] = [
            {"role": "system", "text": f"User wants to design: {body.custom_description}"},
        ]
    next_param = get_next_missing_param(session["component_type"], session["params"])
    return {**_session_summary(session), "next_param": next_param}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = _get_session(session_id)
    next_param = get_next_missing_param(session["component_type"], session["params"])
    return {
        **_session_summary(session),
        "messages": session["messages"],
        "next_param": next_param,
        "all_params_collected": are_all_params_collected(session["component_type"], session["params"]),
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in _sessions:
        del _sessions[session_id]
    return {"deleted": True}


# ── Edit Parameter (AFTER submission) ────────────────────────────────────────
@router.put("/sessions/{session_id}/params")
async def edit_param(session_id: str, body: EditParamBody):
    """
    Edit an already-submitted parameter value.
    Resets status back to params_complete so report can be re-generated.
    """
    session = _get_session(session_id)

    if session["component_type"] == "custom":
        # For custom parts, just update the param directly
        session["params"][body.key] = body.value
        session["updated_at"] = time.time()
        # If report was already generated, invalidate it
        if session["status"] in ("report_ready", "report_approved", "cad_ready"):
            session["status"] = "params_complete"
            session["result"] = None
        return {
            "param_updated": True, "key": body.key, "value": body.value,
            "params": session["params"], "status": session["status"],
        }

    # Standard components — validate the edit
    all_params = get_params_for_component(session["component_type"])
    param_def = next((p for p in all_params if p["key"] == body.key), None)
    if not param_def:
        raise HTTPException(400, f"Unknown parameter key: {body.key}")

    err = validate_param(param_def, body.value)
    if err:
        raise HTTPException(422, err)

    if param_def["type"] == "number":
        session["params"][body.key] = float(body.value)
    else:
        session["params"][body.key] = str(body.value)

    session["updated_at"] = time.time()

    # Invalidate the report if it was already generated
    if session["status"] in ("report_ready", "report_approved", "cad_ready"):
        session["status"] = "params_complete"
        session["result"] = None

    next_param = get_next_missing_param(session["component_type"], session["params"])
    return {
        "param_updated": True, "key": body.key, "value": body.value,
        "next_param": next_param,
        "all_params_collected": next_param is None,
        "params": session["params"], "status": session["status"],
    }


# ── Custom Part Free-Form Chat ────────────────────────────────────────────────
# Iterative question loop for custom/unknown parts
CUSTOM_QUESTIONS = [
    {"key": "part_name", "q": "What is the name of the part you want to design?"},
    {"key": "part_purpose", "q": "What is its primary function/purpose?"},
    {"key": "overall_shape", "q": "Describe the overall shape (cylindrical, rectangular, L-bracket, disc, etc.):"},
    {"key": "length_mm", "q": "What is the overall length/height in mm?", "type": "number"},
    {"key": "width_mm", "q": "What is the overall width in mm?", "type": "number"},
    {"key": "height_mm", "q": "What is the overall height/thickness in mm?", "type": "number"},
    {"key": "material_type", "q": "What material? (steel, aluminum, cast iron, stainless steel, brass, plastic):"},
    {"key": "has_holes", "q": "Does it have any holes? If yes, how many and what diameter (mm)?"},
    {"key": "has_slots", "q": "Does it have any slots or grooves? Describe dimensions if yes:"},
    {"key": "has_chamfers", "q": "Does it need chamfers or fillets on edges? (yes/no, and radius in mm):"},
    {"key": "tolerance", "q": "What tolerance class? (general ±0.5mm, precision ±0.1mm, tight ±0.05mm):"},
    {"key": "surface_finish", "q": "Required surface finish? (as-machined, ground, polished):"},
    {"key": "additional_features", "q": "Any additional features? (threads, counterbores, pockets, etc.) Describe or type 'none':"},
    {"key": "load_conditions", "q": "What loads will this part experience? (static, dynamic, impact — describe forces if known):"},
    {"key": "quantity", "q": "How many units do you need manufactured?", "type": "number"},
]


def _get_next_custom_question(session):
    """Find the next unanswered custom question."""
    params = session.get("params", {})
    for q in CUSTOM_QUESTIONS:
        if q["key"] not in params or params[q["key"]] is None:
            return q
    return None


@router.post("/sessions/{session_id}/chat")
async def custom_chat(session_id: str, body: CustomChatBody):
    """Handle free-form chat for custom parts — iterative question intake."""
    session = _get_session(session_id)
    if session["component_type"] != "custom":
        raise HTTPException(400, "Chat endpoint is for custom parts only.")

    # Find current question and store the answer
    current_q = _get_next_custom_question(session)
    if current_q:
        val = body.message.strip()
        if current_q.get("type") == "number":
            try:
                val = float(val)
            except ValueError:
                return {
                    "error": f"Please enter a valid number for {current_q['key']}.",
                    "current_question": current_q,
                }
        session["params"][current_q["key"]] = val
        session["updated_at"] = time.time()

    # Get next question
    next_q = _get_next_custom_question(session)
    if next_q is None:
        session["status"] = "params_complete"
        return {
            "all_done": True,
            "status": "params_complete",
            "params": session["params"],
            "message": "All information collected! Ready to generate your design report.",
        }

    return {
        "all_done": False,
        "answered": current_q["key"] if current_q else None,
        "next_question": next_q,
        "params_so_far": session["params"],
        "progress": f"{len(session['params'])}/{len(CUSTOM_QUESTIONS)}",
    }


@router.post("/sessions/{session_id}/params")
async def submit_param(session_id: str, body: SubmitParamBody):
    session = _get_session(session_id)
    if session["status"] != "collecting_params":
        raise HTTPException(400, "Parameters already collected.")

    all_params = get_params_for_component(session["component_type"])
    param_def = next((p for p in all_params if p["key"] == body.key), None)
    if not param_def:
        raise HTTPException(400, f"Unknown parameter key: {body.key}")

    err = validate_param(param_def, body.value)
    if err:
        raise HTTPException(422, err)

    if param_def["type"] == "number":
        session["params"][body.key] = float(body.value)
    else:
        session["params"][body.key] = str(body.value)
    session["updated_at"] = time.time()

    next_param = get_next_missing_param(session["component_type"], session["params"])
    if next_param is None:
        session["status"] = "params_complete"

    return {
        "param_accepted": True, "key": body.key, "value": body.value,
        "next_param": next_param,
        "all_params_collected": next_param is None,
        "params": session["params"], "status": session["status"],
    }


@router.post("/sessions/{session_id}/generate-report")
async def generate_report(session_id: str):
    session = _get_session(session_id)
    if session["status"] == "collecting_params":
        raise HTTPException(400, "Complete parameter intake first.")
    try:
        result = run_calculation(session["component_type"], session["params"])
    except Exception as e:
        raise HTTPException(500, f"Calculation error: {str(e)}")

    session["result"] = result
    session["status"] = "report_ready"
    session["updated_at"] = time.time()
    return {"session_id": session_id, "status": "report_ready", "result": result}


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


# ── AI Cross-Validation Agent ────────────────────────────────────────────────
@router.post("/sessions/{session_id}/validate")
async def ai_validate_report(session_id: str):
    """
    Use Gemini to cross-validate the engineering calculations.
    """
    session = _get_session(session_id)
    if not session["result"]:
        raise HTTPException(400, "Generate a report first before validating.")

    # Load .env explicitly
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(503, "GEMINI_API_KEY not configured.")

    # Build context from the knowledge base
    kb_context = build_ai_context(session["component_type"], session["params"])

    # Safely serialize result fields
    calcs = session["result"].get("calculations", [])
    safety = session["result"].get("safety", {})

    prompt = f"""You are an expert Mechanical Design Verification Agent for the AIAE system.
Your role is to CROSS-VALIDATE engineering calculations. Be extremely rigorous.

## Component Type: {session["component_type"].upper()}
## Input Parameters:
{json.dumps(session["params"], indent=2)}

## Calculation Results to Validate:
{json.dumps(calcs, indent=2, default=str)}

## Safety Assessment:
{json.dumps(safety, indent=2, default=str)}

## Relevant Engineering Knowledge Base (Source of Truth):
{kb_context}

## YOUR TASK:
1. Check each calculation - verify the formulas and numeric results are correct
2. Check units - ensure dimensional consistency throughout
3. Check safety - verify FOS is adequate for the application
4. Identify errors - flag any miscalculations, wrong formulas, or unsafe designs
5. Provide recommendations - suggest improvements if any

Return ONLY valid JSON (no markdown, no code blocks) in this exact format:
{{
  "validation_status": "PASS",
  "confidence_score": 0.85,
  "checks": [
    {{
      "item": "Name of calculation checked",
      "status": "OK",
      "expected": "expected value or range",
      "actual": "actual computed value",
      "note": "explanation"
    }}
  ],
  "overall_assessment": "1-2 sentence summary",
  "recommendations": ["suggestion1", "suggestion2"]
}}"""

    import google.generativeai as genai
    import logging
    logger = logging.getLogger(__name__)
    
    genai.configure(api_key=api_key)
    
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash-001",
    ]

    validation = None
    last_error = None

    for model_name in models_to_try:
        model_succeeded = False
        
        for attempt in range(3):
            try:
                model = genai.GenerativeModel(model_name)
                
                # run_in_threadpool because we are in an async route
                response = await run_in_threadpool(
                    model.generate_content, 
                    prompt,
                    generation_config=genai.types.GenerationConfig(temperature=0.0)
                )

                # Safely extract text — response.text can throw on blocked responses
                text = ""
                try:
                    text = response.text or ""
                except Exception:
                    # Try to get from candidates
                    if response.candidates:
                        for part in response.candidates[0].content.parts:
                            text += part.text
                    if not text:
                        raise ValueError("AI response was blocked or empty.")

                # Parse JSON from response
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]

                validation = json.loads(text.strip())
                model_succeeded = True
                logger.info(f"✓ {model_name} succeeded (attempt {attempt + 1})")
                break  # Break retry loop on success

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"{model_name} malformed JSON (attempt {attempt + 1}): {e}")
                continue

            except Exception as e:
                import asyncio
                last_error = e
                error_str = str(e)
                if (
                    "429" in error_str
                    or "ResourceExhausted" in error_str
                    or "quota" in error_str.lower()
                ):
                    wait_time = min(10 * (attempt + 1), 35)
                    logger.warning(
                        f"Rate limited on {model_name}, "
                        f"waiting {wait_time}s... (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Non-retryable error on {model_name}: {e}")
                    break
                
        if model_succeeded:
            break  # Break model fallback loop on success

    if not validation:
        # Graceful fallback if all models/retries fail
        logger.error(f"All validation models failed. Last error: {str(last_error)}")
        validation = {
            "validation_status": "WARN",
            "confidence_score": 0.0,
            "checks": [],
            "overall_assessment": f"Validation service error or quota exceeded. Manual review required. Details: {str(last_error)}",
            "recommendations": ["Review calculations manually against Shigley's reference tables."],
        }

    return {
        "session_id": session_id,
        "validation": validation,
        "kb_domains_checked": kb_context[:200] + "...",
    }


@router.post("/sessions/{session_id}/approve-report")
async def approve_report(session_id: str):
    session = _get_session(session_id)
    if session["status"] not in ("report_ready", "report_approved"):
        raise HTTPException(400, "No report to approve.")
    session["status"] = "report_approved"
    session["updated_at"] = time.time()
    return {"status": "report_approved", "session_id": session_id}


@router.post("/sessions/{session_id}/generate-cad")
async def generate_cad(session_id: str):
    session = _get_session(session_id)
    if session["status"] != "report_approved":
        raise HTTPException(400, "Approve the report before generating CAD.")

    dims = session["result"].get("dimensions", {})
    ctype = session["component_type"]

    try:
        import cadquery as cq
        if ctype == "shaft":
            d = dims.get("diameter_mm", 30)
            L = dims.get("length_mm", 300)
            d_inner = dims.get("inner_diameter_mm")
            if d_inner and d_inner > 0:
                shape = cq.Workplane("XY").circle(d/2).circle(d_inner/2).extrude(L)
            else:
                shape = cq.Workplane("XY").circle(d/2).extrude(L)
        elif ctype == "gearbox":
            d1 = dims.get("pinion_pitch_dia_mm", 50)
            fw = dims.get("face_width_mm", 20)
            shape = cq.Workplane("XY").circle(d1/2).extrude(fw)
        elif ctype == "bearing":
            bore = dims.get("bore_diameter_mm", 25)
            shape = cq.Workplane("XY").circle(bore*1.1).circle(bore/2).extrude(bore*0.5)
        elif ctype == "cam":
            Rmax = dims.get("max_radius_mm", 50)
            width = dims.get("cam_width_mm", 20)
            shape = cq.Workplane("XY").circle(Rmax).extrude(width)
        elif ctype == "custom":
            L = dims.get("length_mm", 100)
            W = dims.get("width_mm", 50)
            H = dims.get("height_mm", 25)
            shape = cq.Workplane("XY").box(L, W, H)

        out_dir = os.path.join(os.path.dirname(__file__), "generated_cad")
        os.makedirs(out_dir, exist_ok=True)
        step_path = os.path.join(out_dir, f"design_{session_id}.step")
        cq.exporters.export(shape, step_path)
        session["cad_file_path"] = step_path
        session["status"] = "cad_ready"
        session["updated_at"] = time.time()
        return {"status": "cad_ready", "session_id": session_id,
                "download_url": f"/api/design/sessions/{session_id}/download-cad"}
    except ImportError:
        session["status"] = "cad_ready"
        session["updated_at"] = time.time()
        return {"status": "cad_ready", "session_id": session_id,
                "note": "CadQuery not available — dimensions only.", "dimensions": dims}
    except Exception as e:
        raise HTTPException(500, f"CAD error: {str(e)}")


@router.get("/sessions/{session_id}/download-cad")
async def download_cad(session_id: str):
    from fastapi.responses import FileResponse
    session = _get_session(session_id)
    fpath = session.get("cad_file_path")
    if not fpath or not os.path.isfile(fpath):
        raise HTTPException(404, "No CAD file generated yet.")
    return FileResponse(fpath, media_type="application/octet-stream",
                        filename=f"AccuDesign_{session['component_type']}_{session_id}.step")


# ── Auto-Transfer to Quoting Engine ─────────────────────────────────────────
@router.post("/sessions/{session_id}/send-to-quoting")
async def send_to_quoting(session_id: str):
    """
    Automatically transfer the generated CAD/design data to the quoting engine.
    Returns all the data needed for the quoting page to pre-populate — 
    geometry, dimensions, material, and engineering parameters.
    No manual upload needed.
    """
    session = _get_session(session_id)
    if session["status"] not in ("cad_ready", "report_approved"):
        raise HTTPException(400, "Generate CAD or approve report first.")

    result = session.get("result", {})
    dims = result.get("dimensions", {})
    params = session.get("params", {})
    ctype = session["component_type"]

    # Build geometry/metrics from the engineering calculations
    # This mirrors what /api/analyze returns so the quoting page can use it directly
    volume = 0
    surface_area = 0
    size_x = dims.get("length_mm", dims.get("width_mm", 100))
    size_y = dims.get("width_mm", dims.get("diameter_mm", 50))
    size_z = dims.get("height_mm", dims.get("diameter_mm", 50))

    import math
    if ctype == "shaft":
        d = dims.get("diameter_mm", 30)
        L = dims.get("length_mm", 300)
        r = d / 2
        d_inner = dims.get("inner_diameter_mm", 0)
        if d_inner and d_inner > 0:
            r_inner = d_inner / 2
            volume = math.pi * (r**2 - r_inner**2) * L
            surface_area = 2 * math.pi * (r**2 - r_inner**2) + 2 * math.pi * (r + r_inner) * L
        else:
            volume = math.pi * r**2 * L
            surface_area = 2 * math.pi * r * (r + L)
        size_x = L
        size_y = d
        size_z = d
    elif ctype == "gearbox":
        d1 = dims.get("pinion_pitch_dia_mm", 50)
        fw = dims.get("face_width_mm", 20)
        volume = math.pi * (d1/2)**2 * fw
        surface_area = 2 * math.pi * (d1/2) * (d1/2 + fw)
        size_x = d1
        size_y = d1
        size_z = fw
    elif ctype == "bearing":
        bore = dims.get("bore_diameter_mm", 25)
        od = bore * 2.2
        w = bore * 0.5
        volume = math.pi * ((od/2)**2 - (bore/2)**2) * w
        surface_area = 2 * math.pi * ((od/2)**2 - (bore/2)**2) + 2 * math.pi * (od/2 + bore/2) * w
        size_x = od
        size_y = od
        size_z = w
    elif ctype == "cam":
        Rmax = dims.get("max_radius_mm", 50)
        cw = dims.get("cam_width_mm", 20)
        volume = math.pi * Rmax**2 * cw
        surface_area = 2 * math.pi * Rmax * (Rmax + cw)
        size_x = 2 * Rmax
        size_y = 2 * Rmax
        size_z = cw
    elif ctype == "custom":
        L = dims.get("length_mm", float(params.get("length_mm", 100)))
        W = dims.get("width_mm", float(params.get("width_mm", 50)))
        H = dims.get("height_mm", float(params.get("height_mm", 25)))
        volume = L * W * H
        surface_area = 2 * (L*W + W*H + H*L)
        size_x = L
        size_y = W
        size_z = H

    # Material mapping
    mat = params.get("material_id", params.get("material_type", "steel"))
    material_map = {
        "steel_en8": "Steel", "steel_1045": "Steel", "steel_4140": "Alloy Steel",
        "steel_4340": "Alloy Steel", "ss_304": "Stainless Steel",
        "ci_grade_25": "Cast Iron", "steel": "Steel", "aluminum": "Aluminum",
        "stainless steel": "Stainless Steel", "cast iron": "Cast Iron",
        "brass": "Brass", "plastic": "Plastic",
    }
    detected_material = material_map.get(mat, "Steel")

    # Check if CAD file exists
    has_cad_file = bool(session.get("cad_file_path") and os.path.isfile(session.get("cad_file_path", "")))

    return {
        "session_id": session_id,
        "transferred": True,
        "component_type": ctype,
        "has_cad_file": has_cad_file,
        "download_url": f"/api/design/sessions/{session_id}/download-cad" if has_cad_file else None,
        "metrics": {
            "volume": round(volume, 2),
            "surfaceArea": round(surface_area, 2),
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
