"""
Knowledge Base Lookup Service — RAG-ready retrieval for the AIAE system.
Loads knowledge_base.json and provides deterministic formula retrieval
and AI-powered cross-validation using Gemini.

Security: Uses safe_eval with restricted builtins — never raw eval().
"""

import json
import math
import os
from typing import Dict, Any, List, Optional


_KB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.json")
_KB_CACHE: Optional[List[Dict]] = None


def _load_kb() -> List[Dict]:
    """Load and cache the knowledge base."""
    global _KB_CACHE
    if _KB_CACHE is None:
        with open(_KB_PATH, "r", encoding="utf-8") as f:
            _KB_CACHE = json.load(f)
    return _KB_CACHE


def reload_kb():
    """Force reload (call after edits to the JSON)."""
    global _KB_CACHE
    _KB_CACHE = None
    return _load_kb()


def get_kb_stats() -> Dict[str, Any]:
    """Return summary statistics about the knowledge base."""
    kb = _load_kb()
    domains = {}
    types = {"formula": 0, "rule": 0, "table": 0}
    for entry in kb:
        d = entry.get("domain", "Unknown")
        domains[d] = domains.get(d, 0) + 1
        t = entry.get("type", "unknown")
        if t in types:
            types[t] += 1
    return {
        "total_entries": len(kb),
        "domains": domains,
        "domain_count": len(domains),
        "type_breakdown": types,
    }


def search_kb(domain: str = None, topic: str = None, entry_type: str = None) -> List[Dict]:
    """Search the knowledge base by domain, topic substring, or type."""
    kb = _load_kb()
    results = []
    for entry in kb:
        if domain and domain.lower() not in entry.get("domain", "").lower():
            continue
        if topic and topic.lower() not in entry.get("topic", "").lower():
            continue
        if entry_type and entry.get("type") != entry_type:
            continue
        results.append(entry)
    return results


def get_formulas_for_domain(domain: str) -> List[Dict]:
    """Get all formulas (evaluable) for a specific domain."""
    return search_kb(domain=domain, entry_type="formula")


def get_rules_for_domain(domain: str) -> List[Dict]:
    """Get all rule-based logic for a domain."""
    return search_kb(domain=domain, entry_type="rule")


def get_tables_for_domain(domain: str) -> List[Dict]:
    """Get all lookup tables for a domain."""
    return search_kb(domain=domain, entry_type="table")


# ── Safe Evaluation Engine ────────────────────────────────────────────────────
# Restricted builtins — NO access to __import__, open, exec, etc.
_SAFE_BUILTINS = {
    "abs": abs, "round": round, "min": min, "max": max,
    "int": int, "float": float,
}

_SAFE_MATH = {
    "pi": math.pi, "e": math.e,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "atan2": math.atan2, "sqrt": math.sqrt, "log": math.log,
    "log10": math.log10, "exp": math.exp, "ceil": math.ceil,
    "floor": math.floor, "radians": math.radians, "degrees": math.degrees,
}


def safe_eval_formula(formula_string: str, variables: Dict[str, float]) -> float:
    """
    Safely evaluate a formula string with given variable bindings.
    Uses restricted namespace — no access to dangerous builtins.
    
    Example:
        safe_eval_formula("k_a = a * S_ut**b", {"a": 2.7, "S_ut": 80, "b": -0.265})
    """
    # Strip the assignment part (e.g., "k_a = a * S_ut**b" → "a * S_ut**b")
    expr = formula_string
    if "=" in expr:
        parts = expr.split("=", 1)
        if len(parts) == 2 and parts[0].strip().replace("_", "").isalnum():
            expr = parts[1].strip()

    namespace = {}
    namespace.update(_SAFE_MATH)
    namespace.update(_SAFE_BUILTINS)
    namespace.update(variables)
    namespace["__builtins__"] = {}  # Block all dangerous builtins

    try:
        result = eval(expr, namespace)
        return float(result)
    except Exception as e:
        raise ValueError(f"Formula evaluation failed: '{expr}' — {str(e)}")


def validate_calculation(domain: str, topic: str, inputs: Dict[str, float]) -> Dict[str, Any]:
    """
    Validate a calculation by finding the matching formula in the KB
    and executing it with the given inputs.
    Returns the computed result and comparison data.
    """
    entries = search_kb(domain=domain, topic=topic, entry_type="formula")
    if not entries:
        return {"error": f"No formula found for domain='{domain}', topic='{topic}'"}

    entry = entries[0]
    formula = entry.get("formula_string")
    if not formula:
        return {"error": "Entry has no evaluable formula_string"}

    # Check all required inputs are provided
    required = [inp["symbol"] for inp in entry.get("inputs", [])]
    missing = [s for s in required if s not in inputs]
    if missing:
        return {
            "error": f"Missing input variables: {missing}",
            "required": required,
            "provided": list(inputs.keys()),
        }

    try:
        result = safe_eval_formula(formula, inputs)
        output_info = entry.get("output", {})
        return {
            "valid": True,
            "formula": formula,
            "result": round(result, 6),
            "output_symbol": output_info.get("symbol", "result"),
            "output_unit": output_info.get("unit", ""),
            "output_description": output_info.get("description", ""),
            "domain": domain,
            "topic": topic,
        }
    except ValueError as e:
        return {"error": str(e), "formula": formula}


def build_ai_context(component_type: str, params: Dict[str, Any]) -> str:
    """
    Build a rich context string from the knowledge base for Gemini
    to use when cross-validating engineering calculations.
    Maps component types to relevant KB domains.
    """
    domain_map = {
        "shaft": ["Shaft Design for Stress", "Fatigue Failure and Endurance Limit", "Mechanics"],
        "gearbox": ["Spur and Helical Gears (AGMA Standards)", "Gear Kinematics and Spur Gear Geometry", "Mechanics"],
        "bearing": ["Lubrication and Hydrodynamic Journal Bearings", "Rolling-Contact Bearings"],
        "cam": ["Mechanics", "Geometry"],
        "custom": ["Press Fits and Contact Stresses", "Screws, Fasteners, and Bolted Joints", "Geometry", "Mathematics"],
    }

    domains = domain_map.get(component_type, [])
    context_parts = []

    for domain in domains:
        entries = search_kb(domain=domain)
        if entries:
            context_parts.append(f"\n## {domain}")
            for entry in entries:
                if entry["type"] == "formula":
                    context_parts.append(
                        f"- **{entry['topic']}**: `{entry['formula_string']}`"
                    )
                elif entry["type"] == "rule":
                    context_parts.append(
                        f"- **{entry['topic']}** (Rule): {entry.get('rule_logic', 'N/A')}"
                    )
                elif entry["type"] == "table":
                    context_parts.append(
                        f"- **{entry['topic']}** (Table): {json.dumps(entry.get('table_data', {}), indent=None)}"
                    )

    return "\n".join(context_parts) if context_parts else "No specific KB entries found for this component type."
