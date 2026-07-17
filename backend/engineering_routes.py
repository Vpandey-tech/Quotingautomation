"""
Engineering Design API Routes — /api/design/*
Completely separate from the existing quoting engine endpoints.
Now with:
  - Editable parameters (edit after submission)
  - Knowledge Base stats & search
  - Gemini AI cross-validation agent
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time, os, uuid, json

from services.engineering.params import (
    get_params_for_component, get_next_missing_param,
    validate_param, are_all_params_collected, COMPONENT_LABELS,
    COMPONENT_PARAMS, get_material, compute_smart_defaults
)
from services.engineering.math_engine import run_calculation
from services.engineering.knowledge_lookup import (
    get_kb_stats, search_kb, build_ai_context,
    safe_eval_formula, validate_calculation, reload_kb,
)
from services.engineering.report_generator import (
    build_report_markdown, generate_pdf_report,
)
from services.engineering.cad_engine import generate_cad as cad_generate

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
    assumptions = []
    if next_param is None:
        assumptions = compute_smart_defaults(session["component_type"], session["params"])

    return {
        **_session_summary(session),
        "messages": session["messages"],
        "next_param": next_param,
        "assumptions": assumptions,
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
        import re
        val_str = str(body.value).strip()
        match = re.search(r"[-+]?\d*\.?\d+", val_str)
        if match:
            session["params"][body.key] = float(match.group(0))
        else:
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
    {"key": "part_name", "q": "What is the name of the part you want to design?",
     "options": [
         {"value": "Shaft Adapter", "label": "Shaft Adapter"},
         {"value": "Mounting Bracket", "label": "Mounting Bracket"},
         {"value": "Coupling Flange", "label": "Coupling Flange"},
         {"value": "Spacer Ring", "label": "Spacer Ring"},
     ]},
    {"key": "part_purpose", "q": "What is its primary function/purpose?",
     "options": [
         {"value": "Mounting / support", "label": "Mounting / support"},
         {"value": "Power transmission", "label": "Power transmission"},
         {"value": "Alignment / spacing", "label": "Alignment / spacing"},
     ]},
    {"key": "overall_shape", "q": "Describe the overall shape (cylindrical, rectangular, L-bracket, disc, etc.):",
     "options": [
         {"value": "cylindrical", "label": "Cylindrical (rod/tube)"},
         {"value": "rectangular", "label": "Rectangular (plate/block)"},
         {"value": "L-bracket", "label": "L-Bracket"},
         {"value": "disc", "label": "Disc / Ring"},
     ]},
    {"key": "length_mm", "q": "What is the overall length/height in mm?", "type": "number",
     "options": [
         {"value": "50", "label": "50 mm"},
         {"value": "100", "label": "100 mm"},
         {"value": "200", "label": "200 mm"},
         {"value": "500", "label": "500 mm"},
     ]},
    {"key": "width_mm", "q": "What is the overall width in mm?", "type": "number",
     "options": [
         {"value": "30", "label": "30 mm"},
         {"value": "50", "label": "50 mm"},
         {"value": "80", "label": "80 mm"},
         {"value": "100", "label": "100 mm"},
     ]},
    {"key": "height_mm", "q": "What is the overall height/thickness in mm?", "type": "number",
     "options": [
         {"value": "10", "label": "10 mm"},
         {"value": "20", "label": "20 mm"},
         {"value": "30", "label": "30 mm"},
         {"value": "50", "label": "50 mm"},
     ]},
    {"key": "material_type", "q": "What material? (steel, aluminum, cast iron, stainless steel, brass, plastic):",
     "options": [
         {"value": "steel", "label": "Medium Carbon Steel"},
         {"value": "aluminum", "label": "Aluminum (6061-T6)"},
         {"value": "stainless steel", "label": "Stainless Steel (304/316)"},
         {"value": "brass", "label": "Brass"},
         {"value": "plastic", "label": "Delrin / Plastic"},
     ]},
    {"key": "has_holes", "q": "Does it have any holes? If yes, how many and what diameter (mm)?",
     "options": [
         {"value": "no", "label": "No holes"},
         {"value": "2 holes, 10mm diameter", "label": "2 holes (10mm)"},
         {"value": "4 holes, 12mm diameter", "label": "4 holes (12mm)"},
         {"value": "6 holes, 16mm diameter", "label": "6 holes (16mm)"},
     ]},
    {"key": "has_slots", "q": "Does it have any slots or grooves? Describe dimensions if yes:",
     "options": [
         {"value": "no", "label": "No slots"},
         {"value": "1 slot, 10mm wide", "label": "1 slot (10mm wide)"},
     ]},
    {"key": "has_chamfers", "q": "Does it need chamfers or fillets on edges? (yes/no, and radius in mm):",
     "options": [
         {"value": "no", "label": "No"},
         {"value": "1mm chamfer", "label": "1mm chamfer"},
         {"value": "2mm fillet", "label": "2mm fillet"},
     ]},
    {"key": "tolerance", "q": "What tolerance class? (general ±0.5mm, precision ±0.1mm, tight ±0.05mm):",
     "options": [
         {"value": "general \u00b10.5mm", "label": "General (\u00b10.5mm)"},
         {"value": "precision \u00b10.1mm", "label": "Precision (\u00b10.1mm)"},
         {"value": "tight \u00b10.05mm", "label": "Tight (\u00b10.05mm)"},
     ]},
    {"key": "surface_finish", "q": "Required surface finish? (as-machined, ground, polished):",
     "options": [
         {"value": "as-machined", "label": "As-Machined (standard)"},
         {"value": "ground", "label": "Ground finish"},
         {"value": "polished", "label": "Polished finish"},
     ]},
    {"key": "additional_features", "q": "Any additional features? (threads, counterbores, pockets, etc.) Describe or type 'none':",
     "options": [
         {"value": "none", "label": "None"},
         {"value": "M10 threads", "label": "M10 Threads"},
     ]},
    {"key": "load_conditions", "q": "What loads will this part experience? (static, dynamic, impact — describe forces if known):",
     "options": [
         {"value": "static", "label": "Static load only"},
         {"value": "dynamic", "label": "Dynamic / fluctuating load"},
         {"value": "impact", "label": "Impact / shock load"},
         {"value": "none", "label": "Negligible / None"},
     ]},
    {"key": "quantity", "q": "How many units do you need manufactured?", "type": "number",
     "options": [
         {"value": "1", "label": "1 pc (prototype)"},
         {"value": "10", "label": "10 pcs"},
         {"value": "50", "label": "50 pcs"},
         {"value": "100", "label": "100 pcs"},
     ]},
]


def _get_next_custom_question(session):
    """Find the next unanswered custom question."""
    params = session.get("params", {})
    shape = str(params.get("overall_shape", "")).lower()
    is_cylindrical = "cylind" in shape or "round" in shape or "disc" in shape or "ring" in shape or "flange" in shape
    if is_cylindrical and params.get("length_mm") is not None:
        params["width_mm"] = params["length_mm"]

    for q in CUSTOM_QUESTIONS:
        if q["key"] not in params or params[q["key"]] is None:
            if is_cylindrical and q["key"] == "width_mm":
                continue
            return q
    return None


async def extract_params_from_text(text: str, unanswered_qs: List[Dict[str, Any]]) -> Dict[str, Any]:
    import re
    extracted = {}
    text_lower = text.lower()

    # 1. Regex fallback parsing (very fast and robust)
    dim_matches = re.findall(r"(\d+(?:\.\d+)?)\s*(?:x|\*)\s*(\d+(?:\.\d+)?)\s*(?:x|\*)\s*(\d+(?:\.\d+)?)", text_lower)
    if dim_matches:
        extracted["length_mm"] = float(dim_matches[0][0])
        extracted["width_mm"] = float(dim_matches[0][1])
        extracted["height_mm"] = float(dim_matches[0][2])
    else:
        len_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:long|length)", text_lower)
        if len_match:
            extracted["length_mm"] = float(len_match.group(1))
        wid_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:wide|width)", text_lower)
        if wid_match:
            extracted["width_mm"] = float(wid_match.group(1))
        hei_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:thick|thickness|height)", text_lower)
        if hei_match:
            extracted["height_mm"] = float(hei_match.group(1))

    od_match = re.search(r"(?:outer diameter|od)\s*(\d+(?:\.\d+)?)", text_lower)
    id_match = re.search(r"(?:inner diameter|inner bore|id)\s*(\d+(?:\.\d+)?)", text_lower)
    thick_match = re.search(r"(?:thickness|height|thick)\s*(\d+(?:\.\d+)?)", text_lower)
    if od_match:
        extracted["length_mm"] = float(od_match.group(1))
        extracted["width_mm"] = float(od_match.group(1))
    if id_match:
        extracted["has_holes"] = f"Yes, inner bore {id_match.group(1)}mm"
    if thick_match:
        extracted["height_mm"] = float(thick_match.group(1))

    qty_match = re.search(r"(\d+)\s*(?:pcs|pcs\.|pieces|units|quantity|qty)", text_lower)
    if qty_match:
        extracted["quantity"] = float(qty_match.group(1))

    materials = ["steel", "aluminum", "cast iron", "stainless steel", "brass", "plastic"]
    for mat in materials:
        if mat in text_lower:
            extracted["material_type"] = mat
            break

    # 2. Try Gemini AI extraction if api key is configured
    api_key = os.getenv("GEMINI_API_KEY", "")
    if api_key:
        try:
            import google.generativeai as genai
            import json
            genai.configure(api_key=api_key)
            
            prompt = f"""Analyze this user message about a custom mechanical part: "{text}"
We need to extract answers for these parameters:
{json.dumps(unanswered_qs, indent=2)}

CRITICAL RULE: Only extract parameters that are EXPLICITLY mentioned or clearly detailed in the user's message.
DO NOT assume, default, or guess values for parameters that are not mentioned. For example, if the user does not explicitly talk about holes, slots, chamfers, tolerances, quantities, or loads, DO NOT include those keys in the "extracted" dictionary at all (omit them entirely).

Return ONLY valid JSON in this exact format:
{{
  "extracted": {{
    "key1": "value",
    "key2": 123
  }}
}}
Do not include any markdown styling. Only output the raw JSON."""
            
            models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash-001",
            ]
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = await run_in_threadpool(
                        model.generate_content,
                        [prompt],
                        generation_config=genai.types.GenerationConfig(temperature=0.0)
                    )
                    resp_text = response.text.strip()
                    if "```json" in resp_text:
                        resp_text = resp_text.split("```json", 1)[1].split("```", 1)[0]
                    elif "```" in resp_text:
                        resp_text = resp_text.split("```", 1)[1].split("```", 1)[0]
                    resp_text = resp_text.strip()
                    start = resp_text.find("{")
                    end = resp_text.rfind("}")
                    if start != -1 and end != -1:
                        data = json.loads(resp_text[start:end+1])
                        ai_extracted = data.get("extracted", {})
                        for k, v in ai_extracted.items():
                            if v is not None and v != "":
                                q_def = next((q for q in unanswered_qs if q["key"] == k), None)
                                if q_def and q_def.get("type") == "number":
                                    try:
                                        import re
                                        nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(v))
                                        if nums:
                                            extracted[k] = float(nums[0])
                                    except ValueError:
                                        continue
                                else:
                                    extracted[k] = str(v)
                        break
                except Exception:
                    continue
        except Exception:
            pass
            
    return extracted


@router.post("/sessions/{session_id}/chat")
async def custom_chat(session_id: str, body: CustomChatBody):
    """Handle free-form chat for custom parts — iterative question intake."""
    session = _get_session(session_id)
    if session["component_type"] != "custom":
        raise HTTPException(400, "Chat endpoint is for custom parts only.")

    message_text = body.message.strip()
    
    # Initial start trigger message should not be stored as an answer
    if message_text.lower() == "start":
        next_q = _get_next_custom_question(session)
        return {
            "all_done": False,
            "answered": None,
            "next_question": next_q,
            "params_so_far": session["params"],
            "progress": f"{len(session['params'])}/{len(CUSTOM_QUESTIONS)}",
        }

    unanswered_qs = [q for q in CUSTOM_QUESTIONS if q["key"] not in session["params"] or session["params"][q["key"]] is None]
    current_q = _get_next_custom_question(session)

    extracted_dict = await extract_params_from_text(message_text, unanswered_qs)
    extracted_summary = []

    # 1. Apply any extracted parameters
    if extracted_dict:
        for k, v in extracted_dict.items():
            session["params"][k] = v
            extracted_summary.append(f"{k}: {v}")

    # 2. If the current question was not filled by extraction, fill it with the raw message text
    if current_q and (current_q["key"] not in session["params"] or session["params"][current_q["key"]] is None):
        val = message_text
        if current_q.get("type") == "number":
            try:
                import re
                nums = re.findall(r"[-+]?\d*\.?\d+", val)
                if nums:
                    val = float(nums[0])
                else:
                    val = float(val)
            except ValueError:
                return {
                    "error": f"Please enter a valid number for {current_q.get('label', current_q['key'])}.",
                    "current_question": current_q,
                }
        session["params"][current_q["key"]] = val
        extracted_summary.append(f"{current_q['key']}: {val}")

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
        "answered": current_q["key"] if current_q else "multiple",
        "extracted_val": ", ".join(extracted_summary) if extracted_summary else None,
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
        import re
        val_str = str(body.value).strip()
        match = re.search(r"[-+]?\d*\.?\d+", val_str)
        if match:
            session["params"][body.key] = float(match.group(0))
        else:
            session["params"][body.key] = float(body.value)
    else:
        session["params"][body.key] = str(body.value)
    session["updated_at"] = time.time()

    next_param = get_next_missing_param(session["component_type"], session["params"])
    assumptions = []
    if next_param is None:
        session["status"] = "params_complete"
        # Compute smart defaults to show to the user
        assumptions = compute_smart_defaults(session["component_type"], session["params"])

    return {
        "param_accepted": True, "key": body.key, "value": body.value,
        "next_param": next_param,
        "all_params_collected": next_param is None,
        "assumptions": assumptions,
        "params": session["params"], "status": session["status"],
    }


@router.post("/sessions/{session_id}/chat/multimodal")
async def custom_chat_multimodal(
    session_id: str, 
    file: UploadFile = File(...),
    message: str = Form("")
):
    """Handle free-form chat for custom parts with an uploaded file."""
    session = _get_session(session_id)
    if session["component_type"] != "custom":
        raise HTTPException(400, "Chat endpoint is for custom parts only.")

    current_q = _get_next_custom_question(session)
    val = message.strip()
    
    if file:
        import google.generativeai as genai
        import json
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
            contents = await file.read()
            fname = (file.filename or "").lower()
            mime_type = "application/pdf"
            if fname.endswith(('.png', '.jpg', '.jpeg')):
                mime_type = "image/jpeg" if fname.endswith(('jpg', 'jpeg')) else "image/png"
            elif fname.endswith(('.step', '.stp')):
                mime_type = "text/plain"
            unanswered_qs = [q for q in CUSTOM_QUESTIONS if q["key"] not in session["params"] or session["params"][q["key"]] is None]
            prompt = f"""The user uploaded '{fname}' and said: '{message}'.
We need to collect the following missing information for their custom part:
{json.dumps(unanswered_qs, indent=2)}

CRITICAL RULE: Only extract parameters that are EXPLICITLY mentioned or clearly detailed in the user's message or file content.
DO NOT assume, default, or guess values for parameters that are not mentioned. For example, if the user does not explicitly talk about holes, slots, chamfers, tolerances, quantities, or loads, DO NOT include those keys in the "extracted" dictionary at all (omit them entirely).

Return ONLY valid JSON in this exact format, with no markdown, just the raw braces:
{{
  "extracted": {{
    "key1": "value",
    "key2": 123
  }}
}}
If you cannot find the answer to a specific question, omit its key from the 'extracted' object."""
            
            parts = [prompt]
            if mime_type == "text/plain":
                parts.append(contents.decode('utf-8', errors='ignore')[:50000])
            else:
                parts.append({"mime_type": mime_type, "data": contents})
                
            models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash-001",
            ]
            
            val = None
            extracted_dict = {}
            last_err = None
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = await run_in_threadpool(
                        model.generate_content,
                        parts,
                        generation_config=genai.types.GenerationConfig(temperature=0.0)
                    )
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json", 1)[1]
                        text = text.split("```", 1)[0]
                    elif "```" in text:
                        text = text.split("```", 1)[1]
                        text = text.split("```", 1)[0]
                    text = text.strip()
                    start = text.find("{")
                    end = text.rfind("}")
                    if start != -1 and end != -1 and end >= start:
                        text = text[start: end + 1]
                    data = json.loads(text)
                    extracted_dict = data.get("extracted", {})
                    break
                except Exception as e:
                    last_err = e
                    continue
            
            if not extracted_dict and last_err:
                return {"error": f"Failed to extract information: {str(last_err)}", "current_question": current_q}
            
            # Apply extracted answers
            extracted_summary = []
            for q in unanswered_qs:
                if q["key"] in extracted_dict:
                    v = extracted_dict[q["key"]]
                    if q.get("type") == "number":
                        try:
                            import re
                            nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(v))
                            if nums:
                                v = float(nums[0])
                            else:
                                v = float(v)
                        except ValueError:
                            continue # skip invalid numbers
                    session["params"][q["key"]] = v
                    extracted_summary.append(f"{q['key']}: {v}")
            
            val = ", ".join(extracted_summary) if extracted_summary else None
            session["updated_at"] = time.time()
            
    elif current_q and val:
        if current_q.get("type") == "number":
            try:
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", val)
                if nums:
                    val = float(nums[0])
                else:
                    val = float(val)
            except ValueError:
                return {
                    "error": f"Please enter a valid number for {current_q['key']}.",
                    "current_question": current_q,
                }
        session["params"][current_q["key"]] = val
        session["updated_at"] = time.time()

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
        "extracted_val": val if current_q and val else None,
        "next_question": next_q,
        "params_so_far": session["params"],
        "progress": f"{len(session['params'])}/{len(CUSTOM_QUESTIONS)}",
    }


@router.post("/sessions/{session_id}/params/multimodal")
async def submit_param_multimodal(
    session_id: str,
    key: str = Form(...),
    file: UploadFile = File(...)
):
    session = _get_session(session_id)
    if session["status"] != "collecting_params":
        raise HTTPException(400, "Parameters already collected.")

    all_params = get_params_for_component(session["component_type"])
    param_def = next((p for p in all_params if p["key"] == key), None)
    if not param_def:
        raise HTTPException(400, f"Unknown parameter key: {key}")

    val = "Uploaded file"
    if file:
        import google.generativeai as genai
        import json
        api_key = os.getenv("GEMINI_API_KEY", "")
        if api_key:
            genai.configure(api_key=api_key)
            contents = await file.read()
            fname = (file.filename or "").lower()
            mime_type = "application/pdf"
            if fname.endswith(('.png', '.jpg', '.jpeg')):
                mime_type = "image/jpeg" if fname.endswith(('jpg', 'jpeg')) else "image/png"
            elif fname.endswith(('.step', '.stp')):
                mime_type = "text/plain"
            
            prompt = f"The user uploaded '{fname}'. Extract the answer for the parameter '{param_def['label']}' (unit: {param_def.get('unit', '')}). Return JUST the answer value directly, no markdown."
            
            parts = [prompt]
            if mime_type == "text/plain":
                parts.append(contents.decode('utf-8', errors='ignore')[:50000])
            else:
                parts.append({"mime_type": mime_type, "data": contents})
                
            models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-2.5-pro",
                "gemini-2.0-flash-001",
            ]
            
            val = None
            last_err = None
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = await run_in_threadpool(
                        model.generate_content,
                        parts,
                        generation_config=genai.types.GenerationConfig(temperature=0.0)
                    )
                    text = response.text.strip()
                    import re
                    if param_def.get("type") == "number":
                        nums = re.findall(r"[-+]?\d*\.\d+|\d+", text)
                        if nums:
                            val = str(nums[0])
                        else:
                            raise ValueError("No numeric value detected")
                    else:
                        val = text
                    break
                except Exception as e:
                    last_err = e
                    continue
            
            if not val:
                raise HTTPException(422, f"Could not extract '{param_def['label']}' from {fname}. Please enter it manually.")

    err = validate_param(param_def, val)
    if err:
        raise HTTPException(422, f"Invalid value extracted from file: {err}. Please enter manually.")

    if param_def["type"] == "number":
        session["params"][key] = float(val)
    else:
        session["params"][key] = str(val)
    session["updated_at"] = time.time()

    next_param = get_next_missing_param(session["component_type"], session["params"])
    assumptions = []
    if next_param is None:
        session["status"] = "params_complete"
        # Compute smart defaults to show to the user
        assumptions = compute_smart_defaults(session["component_type"], session["params"])

    return {
        "param_accepted": True, "key": key, "value": val,
        "next_param": next_param,
        "all_params_collected": next_param is None,
        "assumptions": assumptions,
        "params": session["params"], "status": session["status"],
    }

async def call_groq_api(prompt: str, response_json: bool = True) -> Optional[str]:
    import httpx, os, logging
    logger = logging.getLogger("uvicorn.error")
    
    groq_api_key = os.getenv("GROQ_API_KEY", "")
    if not groq_api_key:
        return None
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
    }
    if response_json:
        payload["response_format"] = {"type": "json_object"}
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=15.0)
            if response.status_code == 200:
                res_data = response.json()
                return res_data["choices"][0]["message"]["content"].strip()
            else:
                logger.warning(f"Groq API returned status code {response.status_code}: {response.text}")
    except Exception as e:
        logger.warning(f"Groq API call failed: {e}")
        
    return None

async def generate_custom_operations(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Use Groq or Gemini to synthesize a list of build123d advanced operations (JSON)
    based on the user's free-form chat descriptions.
    """
    import os, json

    prompt = f"""We are building a 3D CAD model using a list of parametric operations.
Here is the description of the custom part:
- Name: {params.get("part_name")}
- Purpose: {params.get("part_purpose")}
- Overall Shape: {params.get("overall_shape")}
- Length/Outer Diameter: {params.get("length_mm")} mm
- Width: {params.get("width_mm")} mm
- Height/Thickness: {params.get("height_mm")} mm
- Material: {params.get("material_type")}
- Holes/Bores: {params.get("has_holes")}
- Slots/Grooves: {params.get("has_slots")}
- Chamfers/Fillets: {params.get("has_chamfers")}
- Special Requirements: {params.get("additional_features")}

Your task is to generate a list of advanced CAD operations to build this part.
Supported operations:
1. {{"type": "box", "action": "add"|"cut", "l": float, "w": float, "h": float, "x": float, "y": float, "z": float, "rx": float, "ry": float, "rz": float}}
2. {{"type": "cylinder", "action": "add"|"cut", "r": float, "h": float, "x": float, "y": float, "z": float, "rx": float, "ry": float, "rz": float}}
3. {{"type": "sphere", "action": "add"|"cut", "r": float, "x": float, "y": float, "z": float}}
4. {{"type": "hole_pattern", "action": "cut", "pattern": "linear"|"circular", "count": int, "diameter": float, "depth": float}}
   - If pattern is "linear": needs "spacing": float, "direction": [x,y,z], "start": [x,y,z]
   - If pattern is "circular": needs "pcd_radius": float, "center": [x,y,z], "start_angle": float
5. {{"type": "fillet"|"chamfer", "target": "top"|"bottom"|"all", "radius"|"length": float}}

STRICT MAPPING RULES:
1. CYLINDRICAL/ROUND PARTS (e.g. flange, disc, ring, cylinder, tube):
   - The first operation MUST be a "cylinder" with action="add".
   - Use the outer diameter as the cylinder diameter (radius r = Length/Outer Diameter / 2).
   - Use the height/thickness as the cylinder height (h = Height/Thickness).
   - Centered at x=0, y=0, z=0.
   - Do NOT use a "box" operation anywhere for a cylindrical part.

2. INNER BORE / CONCENTRIC HOLES:
   - If the part is a ring or flange with a central inner bore or hole, add a "cylinder" operation with action="cut".
   - Set r = inner_bore_diameter / 2.
   - Set h = Height/Thickness + 10 (to ensure a clean through-cut).
   - Centered at x=0, y=0, z=0.

3. circular BOLT HOLE PATTERNS:
   - If there are multiple bolt holes arranged on a circle (e.g. "6 bolt holes on a 104mm PCD" or "symmetrical pattern"), use a circular "hole_pattern" with action="cut".
   - Set pattern = "circular".
   - Set count = number of bolt holes (e.g. 6).
   - Set diameter = bolt hole diameter (e.g. 12).
   - Set depth = Height/Thickness + 10 (for through-cut).
   - Set pcd_radius = PCD / 2 (e.g. 104 / 2 = 52).
   - Set center = [0, 0, 0] and start_angle = 0.

4. CHAMFERS / FILLETS:
   - If chamfers or fillets on edges are requested, add a "chamfer" or "fillet" operation.
   - Set target = "all" or "top" or "bottom".
   - Set length/radius to the requested value (e.g. 2.0).

Return ONLY valid JSON containing a list of operations. E.g.:
[
  {{"type": "cylinder", "action": "add", "r": 60, "h": 30, "x": 0, "y": 0, "z": 0}},
  ...
]
Do not include any markdown formatting. Only output the raw JSON list."""

    # 1. Try Groq first (extremely fast and separate quota limits)
    import logging
    logger = logging.getLogger("uvicorn.error")
    
    try:
        groq_res = await call_groq_api(prompt, response_json=True)
        if groq_res:
            ops = json.loads(groq_res)
            # Support both root list and wrapper dict formats
            if isinstance(ops, dict) and "operations" in ops:
                ops = ops["operations"]
            if isinstance(ops, list) and len(ops) > 0:
                logger.info("✓ Successfully generated custom operations using Groq (Llama-3.3-70B)")
                return ops
    except Exception as e:
        logger.warning(f"Groq custom operations extraction failed: {e}. Falling back to Gemini.")

    # 2. Fallback to Gemini Key 1 then Key 2
    import google.generativeai as genai
    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash-001",
    ]

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
                    generation_config=genai.types.GenerationConfig(temperature=0.0)
                )
                text = response.text.strip()
                if "```json" in text:
                    text = text.split("```json", 1)[1].split("```", 1)[0]
                elif "```" in text:
                    text = text.split("```", 1)[1].split("```", 1)[0]
                text = text.strip()
                ops = json.loads(text)
                if isinstance(ops, list) and len(ops) > 0:
                    logger.info(f"✓ Successfully generated custom operations using Gemini Key {key_idx}")
                    return ops
            except Exception as e:
                err_msg = str(e).lower()
                if "429" in err_msg or "quota" in err_msg or "resource" in err_msg:
                    logger.warning(f"Gemini API key {key_idx} is rate-limited or out of quota (429). Skipping other models for this key.")
                    break
                continue

    # Heuristic Programmatic Fallback if Gemini quota is exceeded (429)
    shape = str(params.get("overall_shape", "")).lower()
    is_cylindrical = "cylind" in shape or "round" in shape or "disc" in shape or "ring" in shape or "flange" in shape
    
    L = float(params.get("length_mm", 100))
    W = float(params.get("width_mm", 50))
    H = float(params.get("height_mm", 25))
    
    fallback_ops = []
    import re
    if is_cylindrical:
        r_outer = L / 2
        fallback_ops.append({"type": "cylinder", "action": "add", "r": r_outer, "h": H, "x": 0.0, "y": 0.0, "z": 0.0})
        
        holes_desc = str(params.get("has_holes", "")).lower()
        # Match "80mm inner bore" (number first)
        bore_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:inner bore|bore|inner diameter|id|inner dia)", holes_desc)
        if not bore_match:
            # Match "inner bore 80mm" (words first)
            bore_match = re.search(r"(?:inner bore|bore|inner diameter|id|inner dia)\s*(?:of|is|:)?\s*(\d+(?:\.\d+)?)", holes_desc)
            
        r_inner = 0.0
        if bore_match:
            r_inner = float(bore_match.group(1)) / 2
            fallback_ops.append({"type": "cylinder", "action": "cut", "r": r_inner, "h": H + 10, "x": 0.0, "y": 0.0, "z": 0.0})
            
        qty_match = re.search(r"(\d+)\s*(?:bolt)?\s*holes", holes_desc)
        dia_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:diameter|dia|size)", holes_desc)
        pcd_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:bolt circle|pcd|circle|diameter circle)", holes_desc)
        
        if qty_match and dia_match:
            count = int(qty_match.group(1))
            dia = float(dia_match.group(1))
            pcd_r = float(pcd_match.group(1)) / 2 if pcd_match else (r_outer + r_inner) / 2
            
            fallback_ops.append({
                "type": "hole_pattern",
                "action": "cut",
                "pattern": "circular",
                "count": count,
                "diameter": dia,
                "depth": H + 10,
                "pcd_radius": pcd_r,
                "center": [0.0, 0.0, 0.0],
                "start_angle": 0.0
            })
            
        chamfers_desc = str(params.get("has_chamfers", "")).lower()
        if "chamfer" in chamfers_desc and "no" not in chamfers_desc:
            ch_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*chamfer", chamfers_desc)
            ch_len = float(ch_match.group(1)) if ch_match else 1.0
            fallback_ops.append({"type": "chamfer", "target": "all", "length": ch_len})
        elif "fillet" in chamfers_desc and "no" not in chamfers_desc:
            fi_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*fillet", chamfers_desc)
            fi_rad = float(fi_match.group(1)) if fi_match else 1.0
            fallback_ops.append({"type": "fillet", "target": "all", "radius": fi_rad})
    else:
        fallback_ops.append({"type": "box", "action": "add", "l": L, "w": W, "h": H, "x": 0.0, "y": 0.0, "z": 0.0})
        
        holes_desc = str(params.get("has_holes", "")).lower()
        qty_match = re.search(r"(\d+)\s*holes", holes_desc)
        dia_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm)?\s*(?:diameter|dia)", holes_desc)
        if qty_match and dia_match:
            count = int(qty_match.group(1))
            dia = float(dia_match.group(1))
            spacing = L / (count + 1)
            fallback_ops.append({
                "type": "hole_pattern",
                "action": "cut",
                "pattern": "linear",
                "count": count,
                "diameter": dia,
                "depth": H + 10,
                "spacing": spacing,
                "direction": [1.0, 0.0, 0.0],
                "start": [-L/2 + spacing, 0.0, 0.0]
            })

    return fallback_ops


@router.post("/sessions/{session_id}/generate-report")
async def generate_report(session_id: str):
    session = _get_session(session_id)
    if session["status"] == "collecting_params":
        raise HTTPException(400, "Complete parameter intake first.")
        
    # Generate custom CAD operations before calculations
    if session["component_type"] == "custom" and not session["params"].get("operations"):
        try:
            ops = await generate_custom_operations(session["params"])
            if ops:
                session["params"]["operations"] = ops
        except Exception as oe:
            import logging
            logger = logging.getLogger("uvicorn.error")
            logger.error(f"Failed to generate custom operations: {oe}")

    # Auto-fill missing assumptions with their defaults before calculating
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

    # Generate Markdown report
    try:
        md_report = build_report_markdown(
            session["component_type"], session["params"], result, session_id
        )
        session["report_markdown"] = md_report
    except Exception:
        session["report_markdown"] = None

    # Generate PDF report
    try:
        pdf_path = generate_pdf_report(
            session["component_type"], session["params"], result, session_id
        )
        session["report_pdf_path"] = pdf_path
    except Exception:
        session["report_pdf_path"] = None

    return {
        "session_id": session_id, "status": "report_ready", "result": result,
        "has_pdf": session.get("report_pdf_path") is not None,
        "has_markdown": session.get("report_markdown") is not None,
    }


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
    logger = logging.getLogger("uvicorn.error")

    validation = None
    last_error = None

    # 1. Try Groq first for calculation validation
    try:
        groq_res = await call_groq_api(prompt, response_json=True)
        if groq_res:
            validation = json.loads(groq_res)
            logger.info("✓ Successfully validated report calculations using Groq (Llama-3.3-70B)")
    except Exception as e:
        logger.warning(f"Groq report validation failed: {e}. Falling back to Gemini.")

    # 2. Fallback to Gemini Key 1 and Key 2
    if not validation:
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-001",
        ]

        # Rotate through Key 1 and Key 2 to bypass 429 errors
        for key_idx in [1, 2]:
            current_api_key = os.getenv("GEMINI_API_KEY_2" if key_idx == 2 else "GEMINI_API_KEY", "")
            if not current_api_key:
                continue
            
            genai.configure(api_key=current_api_key)
            key_failed = False
            
            for model_name in models_to_try:
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
                    logger.info(f"✓ {model_name} succeeded with Gemini Key {key_idx}")
                    break  # Break models loop on success

                except json.JSONDecodeError as e:
                    last_error = e
                    logger.warning(f"{model_name} malformed JSON with Key {key_idx}: {e}")
                    continue

                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    if (
                        "429" in error_str
                        or "ResourceExhausted" in error_str
                        or "quota" in error_str.lower()
                    ):
                        logger.warning(f"Gemini Key {key_idx} is rate-limited or out of quota (429) on {model_name}. Skipping this key.")
                        key_failed = True
                        break  # Break models loop immediately to rotate key
                    else:
                        logger.warning(f"Error on {model_name} with Key {key_idx}: {e}")
                        continue
                        
            if validation:
                break  # Break keys loop on success

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
async def generate_cad_endpoint(session_id: str):
    session = _get_session(session_id)
    if session["status"] != "report_approved":
        raise HTTPException(400, "Approve the report before generating CAD.")

    dims = session["result"].get("dimensions", {})
    ctype = session["component_type"]

    try:
        cad_result = cad_generate(ctype, dims, session["params"])
        step_path = cad_result.get("step_file")

        if not step_path:
            raise HTTPException(500, f"CAD generation failed verification check: {cad_result.get('note', 'Unknown error')}")

        session["cad_file_path"] = step_path
        session["status"] = "cad_ready"
        session["updated_at"] = time.time()

        return {
            "status": "cad_ready",
            "session_id": session_id,
            "engine": cad_result.get("engine", "none"),
            "step_file": step_path,
            "download_url": f"/api/design/sessions/{session_id}/download-cad",
            "dimensions": dims,
            "note": cad_result.get("note"),
        }
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


@router.get("/sessions/{session_id}/download-pdf")
async def download_pdf(session_id: str):
    """Download the generated PDF engineering report."""
    from fastapi.responses import FileResponse
    session = _get_session(session_id)
    fpath = session.get("report_pdf_path")
    if not fpath or not os.path.isfile(fpath):
        raise HTTPException(404, "No PDF report generated yet.")
    return FileResponse(fpath, media_type="application/pdf",
                        filename=f"AccuDesign_Report_{session['component_type']}_{session_id}.pdf")


@router.get("/sessions/{session_id}/report-markdown")
async def get_report_markdown(session_id: str):
    """Get the Markdown-formatted engineering report."""
    session = _get_session(session_id)
    md = session.get("report_markdown")
    if not md:
        raise HTTPException(404, "No Markdown report generated yet.")
    return {"session_id": session_id, "markdown": md}


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
