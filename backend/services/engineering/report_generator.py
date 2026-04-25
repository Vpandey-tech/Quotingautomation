"""
Engineering Report Generator — Professional Calculation Sheets
Uses handcalcs for transparent, Mathcad-style rendered formulas
and fpdf2 for PDF output.

Generates standards-compliant design validation reports with:
  - Full formula transparency (every step shown)
  - Unit tracking
  - Safety assessment summary
  - Standards references

Security: No user-controlled eval — all formulas are pre-verified from math_engine.
"""

import math
import os
import time
from typing import Dict, Any, Optional

# Try importing handcalcs — graceful fallback if not installed or outside Jupyter
try:
    import handcalcs.render as hc_render
    HANDCALCS_AVAILABLE = True
except (ImportError, AttributeError, Exception):
    # handcalcs requires IPython/Jupyter for magic registration
    HANDCALCS_AVAILABLE = False

# PDF generation
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


# ── Report Data Builder ──────────────────────────────────────────────────────

def _format_calc_step(calc: Dict) -> str:
    """Format a single calculation step as a readable string."""
    name = calc.get("name", "")
    formula = calc.get("formula", "")
    result = calc.get("result", 0)
    unit = calc.get("unit", "")
    desc = calc.get("description", "")
    
    line = f"{name}: {formula} = {result} {unit}"
    if desc:
        line += f"  ({desc})"
    return line


def build_report_markdown(
    component_type: str,
    params: Dict[str, Any],
    result: Dict[str, Any],
    session_id: str = "",
) -> str:
    """
    Build a complete engineering report in Markdown format.
    This is the primary output — can be rendered in browser or converted to PDF.
    """
    label_map = {
        "shaft": "Shaft Design Report",
        "bearing": "Bearing Selection Report",
        "gearbox": "Gearbox Design Report",
        "cam": "CAM Design Report",
        "custom": "Custom Part Design Report",
    }
    
    title = label_map.get(component_type, "Engineering Design Report")
    calcs = result.get("calculations", [])
    dims = result.get("dimensions", {})
    safety = result.get("safety", {})
    standards = result.get("standards", [])
    material = result.get("material", {})
    
    lines = []
    lines.append(f"# {title}")
    lines.append(f"**Report ID:** {session_id}  ")
    lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**Component:** {component_type.upper()}  ")
    lines.append("")
    
    # ── Input Parameters ──
    lines.append("## 1. Input Parameters")
    lines.append("")
    lines.append("| Parameter | Value |")
    lines.append("|-----------|-------|")
    for k, v in params.items():
        lines.append(f"| {k.replace('_', ' ').title()} | {v} |")
    lines.append("")
    
    # ── Material Properties ──
    if material:
        lines.append("## 2. Material Properties")
        lines.append("")
        lines.append("| Property | Value |")
        lines.append("|----------|-------|")
        mat_display = {
            "name": "Grade",
            "yield_mpa": "Yield Strength (σy)",
            "ultimate_mpa": "Ultimate Strength (σu)",
            "shear_mpa": "Shear Strength (τ)",
            "endurance_mpa": "Endurance Limit (σe)",
            "elastic_modulus_gpa": "Elastic Modulus (E)",
            "density_kg_m3": "Density (ρ)",
            "hardness_bhn": "Hardness (BHN)",
        }
        for key, label in mat_display.items():
            val = material.get(key)
            if val is not None:
                unit = ""
                if "mpa" in key:
                    unit = " MPa"
                elif "gpa" in key:
                    unit = " GPa"
                elif "density" in key:
                    unit = " kg/m³"
                lines.append(f"| {label} | {val}{unit} |")
        lines.append("")
    
    # ── Calculation Steps ──
    lines.append("## 3. Design Calculations")
    lines.append("")
    for i, calc in enumerate(calcs, 1):
        name = calc.get("name", "")
        formula = calc.get("formula", "")
        result_val = calc.get("result", 0)
        unit = calc.get("unit", "")
        desc = calc.get("description", "")
        
        lines.append(f"### 3.{i}. {name}")
        if formula:
            lines.append(f"**Formula:** `{formula}`  ")
        lines.append(f"**Result:** **{result_val} {unit}**  ")
        if desc:
            lines.append(f"*{desc}*  ")
        lines.append("")
    
    # ── Dimensions Summary ──
    lines.append("## 4. Final Dimensions")
    lines.append("")
    lines.append("| Dimension | Value |")
    lines.append("|-----------|-------|")
    for k, v in dims.items():
        if v is not None:
            unit = "mm" if "mm" in k else ("teeth" if "teeth" in k else "")
            lines.append(f"| {k.replace('_', ' ').title()} | {v} {unit} |")
    lines.append("")
    
    # ── Safety Assessment ──
    lines.append("## 5. Safety Assessment")
    lines.append("")
    fos_actual = safety.get("fos_actual")
    fos_req = safety.get("fos_required")
    is_safe = safety.get("is_safe", False)
    
    status_icon = "✅ PASS" if is_safe else "❌ FAIL"
    lines.append(f"**Overall Status:** {status_icon}  ")
    if fos_actual is not None:
        lines.append(f"**Actual FOS:** {fos_actual}  ")
    if fos_req is not None:
        lines.append(f"**Required FOS:** {fos_req}  ")
    lines.append("")
    
    warnings = safety.get("warnings", [])
    if warnings:
        lines.append("### ⚠️ Warnings")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")
    
    recommendations = safety.get("recommendations", [])
    if recommendations:
        lines.append("### 💡 Recommendations")
        for r in recommendations:
            lines.append(f"- {r}")
        lines.append("")
    
    # ── Standards References ──
    if standards:
        lines.append("## 6. Applicable Standards")
        lines.append("")
        for s in standards:
            lines.append(f"- {s}")
        lines.append("")
    
    # ── Footer ──
    lines.append("---")
    lines.append("*Generated by AccuDesign Engineering Engine — AI-Integrated Automation Engine (AIAE)*  ")
    lines.append("*All calculations are deterministic. AI is used for cross-validation only.*")
    
    return "\n".join(lines)


def _sanitize_for_pdf(text: str) -> str:
    """Replace Unicode engineering symbols with ASCII for PDF compatibility."""
    replacements = {
        "ω": "w", "π": "pi", "τ": "tau", "σ": "sigma", "δ": "delta",
        "ρ": "rho", "μ": "mu", "α": "alpha", "β": "beta", "θ": "theta",
        "φ": "phi", "ε": "epsilon", "Ω": "Omega", "Δ": "Delta",
        "√": "sqrt", "∛": "cbrt", "≥": ">=", "≤": "<=", "≈": "~=",
        "·": "*", "×": "x", "²": "^2", "³": "^3", "⁴": "^4",
        "°": "deg", "—": "-", "–": "-", "\u200b": "", "→": "->",
        "σy": "Sy", "σu": "Su", "σe": "Se", "σv": "Sv",
        "σb": "Sb", "τ_allow": "tau_allow",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Strip any remaining non-latin-1 chars
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf_report(
    component_type: str,
    params: Dict[str, Any],
    result: Dict[str, Any],
    session_id: str = "",
    output_dir: str = None,
) -> Optional[str]:
    """
    Generate a professional PDF engineering report.
    Returns the file path to the generated PDF, or None if fpdf2 is not available.
    """
    if not FPDF_AVAILABLE:
        return None
    
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "generated_reports")
    os.makedirs(output_dir, exist_ok=True)
    
    label_map = {
        "shaft": "Shaft Design Report",
        "bearing": "Bearing Selection Report",
        "gearbox": "Gearbox Design Report",
        "cam": "CAM Design Report",
        "custom": "Custom Part Design Report",
    }
    title = label_map.get(component_type, "Engineering Design Report")
    
    calcs = result.get("calculations", [])
    dims = result.get("dimensions", {})
    safety = result.get("safety", {})
    standards = result.get("standards", [])
    material = result.get("material", {})
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Helper — all text through sanitizer
    _cell = pdf.cell
    def safe_cell(*args, **kwargs):
        # Sanitize the text argument (3rd positional arg or 'text'/'txt')
        args = list(args)
        if len(args) >= 3 and isinstance(args[2], str):
            args[2] = _sanitize_for_pdf(args[2])
        if "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = _sanitize_for_pdf(kwargs["text"])
        if "txt" in kwargs and isinstance(kwargs["txt"], str):
            kwargs["txt"] = _sanitize_for_pdf(kwargs["txt"])
        return _cell(*args, **kwargs)
    pdf.cell = safe_cell
    
    # ── Header ──
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Report ID: {session_id}  |  Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}", 
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    # ── Input Parameters ──
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. Input Parameters", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for k, v in params.items():
        label = k.replace("_", " ").title()
        pdf.cell(80, 5, f"  {label}:", new_x="RIGHT")
        pdf.cell(0, 5, str(v), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # ── Material ──
    if material and material.get("name"):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "2. Material Properties", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        mat_fields = [
            ("name", "Grade", ""),
            ("yield_mpa", "Yield Strength", " MPa"),
            ("ultimate_mpa", "Ultimate Strength", " MPa"),
            ("elastic_modulus_gpa", "Elastic Modulus", " GPa"),
        ]
        for key, label, unit in mat_fields:
            val = material.get(key)
            if val is not None:
                pdf.cell(80, 5, f"  {label}:", new_x="RIGHT")
                pdf.cell(0, 5, f"{val}{unit}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
    
    # ── Calculations ──
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "3. Design Calculations", new_x="LMARGIN", new_y="NEXT")
    
    for i, calc in enumerate(calcs, 1):
        name = calc.get("name", "")
        formula = calc.get("formula", "")
        result_val = calc.get("result", 0)
        unit = calc.get("unit", "")
        desc = calc.get("description", "")
        
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, f"  3.{i}. {name}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        if formula:
            pdf.cell(0, 5, f"    Formula: {formula}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, f"    Result: {result_val} {unit}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 8)
        if desc:
            pdf.cell(0, 4, f"    {desc}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    
    # ── Dimensions ──
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "4. Final Dimensions", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for k, v in dims.items():
        if v is not None:
            label = k.replace("_", " ").title()
            pdf.cell(80, 5, f"  {label}:", new_x="RIGHT")
            pdf.cell(0, 5, str(v), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # ── Safety ──
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "5. Safety Assessment", new_x="LMARGIN", new_y="NEXT")
    is_safe = safety.get("is_safe", False)
    pdf.set_font("Helvetica", "B", 10)
    status = "PASS" if is_safe else "FAIL"
    pdf.cell(0, 6, f"  Status: {status}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    if safety.get("fos_actual") is not None:
        pdf.cell(0, 5, f"  Actual FOS: {safety['fos_actual']}  |  Required: {safety.get('fos_required', 'N/A')}", 
                 new_x="LMARGIN", new_y="NEXT")
    
    for w in safety.get("warnings", []):
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, f"  WARNING: {w}", new_x="LMARGIN", new_y="NEXT")
    for r in safety.get("recommendations", []):
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 4, f"  - {r}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # ── Standards ──
    if standards:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "6. Applicable Standards", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for s in standards:
            pdf.cell(0, 5, f"  - {s}", new_x="LMARGIN", new_y="NEXT")
    
    # ── Footer ──
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 4, "Generated by AccuDesign Engineering Engine (AIAE) — All calculations are deterministic.", 
             new_x="LMARGIN", new_y="NEXT", align="C")
    
    # Save
    filename = f"report_{component_type}_{session_id}.pdf"
    filepath = os.path.join(output_dir, filename)
    pdf.output(filepath)
    
    return filepath
