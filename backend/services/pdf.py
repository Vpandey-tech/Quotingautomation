"""
Authentic ACCU DESIGN Quotation Generator

Matches the exact layout from the provided Image 3 reference.
  - Symmetrical, proper positioning, no off-center boxes
  - Header with Logo top-right
  - Stacked Date/Quote No on the left
  - Table: Sr#, DESCRIPTION, DIMENSIONS, CATEGORY, PART NO, MATERIAL, QTY, Weight(kg), MANUFACTURING PROCESS, Cost
  - Totals: Appended cleanly to the bottom of the table
  - Grand total and Amount in Words highlighted in lime-green
  - Footer with double line separator
  - Full Unicode support for exact formatting (₹ symbol)
"""

import tempfile
import base64
import os
from fpdf import FPDF
from datetime import datetime

try:
    from services.quote_number import amount_in_words
except ImportError:
    from quote_number import amount_in_words

# ── Resolve paths ────────────────────────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BACKEND_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

# ── Windows font paths (for Unicode ₹ support) ──────────────────────────────
FONT_DIR = r"C:\Windows\Fonts"
ARIAL_REGULAR = os.path.join(FONT_DIR, "arial.ttf")
ARIAL_BOLD = os.path.join(FONT_DIR, "arialbd.ttf")
ARIAL_ITALIC = os.path.join(FONT_DIR, "ariali.ttf")
ARIAL_BOLD_ITALIC = os.path.join(FONT_DIR, "arialbi.ttf")

HAS_UNICODE = all(os.path.isfile(f) for f in [ARIAL_REGULAR, ARIAL_BOLD, ARIAL_ITALIC])
INR = "\u20B9" if HAS_UNICODE else "Rs."


def _fmt_inr(amount, decimals=0):
    if amount is None or amount == 0:
        return f"{INR}0"
    if decimals > 0:
        return f"{INR}{amount:,.{decimals}f}"
    return f"{INR}{amount:,.0f}"


class AccuDesignAuthenticPDF(FPDF):
    """Generates the EXACT layout shown in Image 3 for Accu Design."""

    def __init__(self):
        super().__init__()
        self._font_family = "Helvetica"
        
        # Load Arial Unicode to support Rupee symbol properly
        if HAS_UNICODE:
            try:
                self.add_font("ArialUni", "", ARIAL_REGULAR, uni=True)
                self.add_font("ArialUni", "B", ARIAL_BOLD, uni=True)
                self.add_font("ArialUni", "I", ARIAL_ITALIC, uni=True)
                self._font_family = "ArialUni"
            except Exception:
                pass

    def _set_font(self, style="", size=10):
        self.set_font(self._font_family, style, size)

    def header(self):
        # Top-left title "ACCU DESIGN"
        self._set_font("B", 18)
        self.set_y(15)
        self.set_x(10)
        self.cell(0, 7, "ACCU DESIGN", ln=True)
        
        # Tagline below it
        self._set_font("I", 9)
        self.set_x(10)
        self.set_text_color(50, 50, 50)
        self.cell(0, 5, "Accuracy is all that matters...", ln=True)
        self.set_text_color(0, 0, 0)

        # Place the LOGO on the top right
        if os.path.isfile(LOGO_PATH):
            try:
                # Based on Image 3, logo is perfectly positioned at top right
                # Page width is 210. Margin is 10.
                self.image(LOGO_PATH, x=155, y=5, w=38)
            except Exception:
                pass

        # Draw the double separator line (=============)
        self.ln(2)
        y = self.get_y()
        self.set_line_width(0.4)
        self.set_draw_color(0, 0, 0)
        self.line(10, y, 200, y)
        self.line(10, y + 1.2, 200, y + 1.2)
        
        self.set_y(y + 3)

    def footer(self):
        self.set_y(-30)
        # Double separator line
        y = self.get_y()
        self.set_line_width(0.3)
        self.line(10, y, 200, y)
        self.line(10, y + 1.0, 200, y + 1.0)
        
        self.set_y(y + 2)
        self._set_font("B", 7)
        self.cell(0, 4, "GSTIN: 27ADXPD2924L1Z3", ln=True)
        self._set_font("", 7)
        self.cell(0, 4, "Workshop Address: S.No. 30/15, Unity Industrial Estate, Saidham Road, Dhyari, Pune - 411041", ln=True)
        self.cell(0, 4, "Email ID: projects@accudesign.in", ln=True)


# ══════════════════════════════════════════════════════════════════════════════
# Authentic Generator Function
# ══════════════════════════════════════════════════════════════════════════════

def generate_quote_pdf(
    quote_data: dict,
    quote_number: str = "",
    client_name: str = "",
    client_company: str = "",
    source_filename: str = "",
    parts: list = None,
    screenshot_b64: str = None,
) -> str:
    pdf = AccuDesignAuthenticPDF()
    pdf.set_auto_page_break(auto=True, margin=35)
    pdf.add_page()
    now = datetime.now()

    # ── "Quotation" title center ─────────────────────────────────────────────
    pdf._set_font("B", 11)
    pdf.cell(0, 8, "Quotation", align="C", ln=True)
    pdf.ln(2)

    # ── Date and Quotation Number (Stacked Left) ────────────────────────────
    pdf._set_font("", 9)
    pdf.cell(0, 5, f"Date: {now.strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 5, f"Quotation No: {quote_number}", ln=True)
    pdf.ln(4)

    # ── Client Address Block ─────────────────────────────────────────────────
    pdf._set_font("B", 9)
    pdf.cell(0, 5, "To,", ln=True)
    if client_company:
        pdf.cell(0, 5, client_company, ln=True)
    
    # Optional Source File info
    if source_filename:
        pdf._set_font("I", 8)
        pdf.cell(0, 5, f"Subject: {source_filename}", ln=True)

    pdf.ln(2)
    pdf._set_font("B", 9)
    name_display = f"Mr. {client_name}" if client_name else "Purchasing Manager"
    pdf.cell(0, 5, f"Kindly Attention: {name_display}", ln=True)
    pdf.ln(3)

    # ── Subject Line ─────────────────────────────────────────────────────────
    pdf._set_font("", 9)
    part_name_subject = source_filename.replace('.pdf','').replace('.step','') if source_filename else "parts"
    subj_text = f"We are hereby pleased to share with you the best Techno - commercial offer for the\n{part_name_subject} for your perusal."
    pdf.multi_cell(0, 5, subj_text)
    pdf.ln(6)

    # ── PARTS TABLE ──────────────────────────────────────────────────────────
    # Exact replica of Image 3 columns:
    # Sr# | DESCRIPTION | DIMENSIONS | CATEGORY | PART NO. | MATERIAL | QTY. | Weight(kg) | MANUFACTURING PROCESS | Cost
    col_w = [8, 30, 20, 15, 14, 16, 8, 14, 47, 18]
    total_w = sum(col_w) # 190

    headers = ["Sr#", "DESCRIPTION", "DIMENSIONS", "CATEGORY", "PART NO.", "MATERIAL", "QTY.", "Weight\n(kg)", "MFG. PROCESS", "Cost"]

    pdf._set_font("B", 6.5)
    pdf.set_fill_color(240, 240, 240)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.2)

    # Calculate max height for headers
    header_h = 8
    start_x = pdf.get_x()
    start_y = pdf.get_y()
    
    # Draw header cells
    for i, h in enumerate(headers):
        pdf.set_xy(start_x + sum(col_w[:i]), start_y)
        # To handle newlines in headers cleanly, we draw a multi_cell box
        pdf.multi_cell(col_w[i], header_h/2 if '\n' in h else header_h, h, border=1, align="C", fill=True)
        # reset x/y happens automatically but we override
    
    pdf.set_y(start_y + header_h)

    total_a = 0.0
    items_count = 0

    pdf._set_font("", 6.5)
    pdf.set_fill_color(255, 255, 255) # White for body

    def draw_row(idx_str, desc, dims, cat, part_no, mat, qty, wt, proc, cost_val):
        h = 6
        x = pdf.get_x()
        y = pdf.get_y()
        
        # Check page break
        if y + h > 260:
            pdf.add_page()
            y = pdf.get_y()

        row_data = [
            str(idx_str),
            str(desc)[:25],
            str(dims)[:20],
            str(cat)[:10],
            str(part_no),
            str(mat)[:12],
            str(qty),
            str(wt),
            str(proc)[:40],
            cost_val
        ]
        
        for i, val in enumerate(row_data):
            pdf.set_xy(x + sum(col_w[:i]), y)
            align = "C" if i in [0, 3, 4, 5, 6, 7, 9] else "L"
            
            # Draw cell
            pdf.cell(col_w[i], h, val, border=1, align=align)
        
        pdf.set_y(y + h)

    if parts and len(parts) > 0:
        for idx, part in enumerate(parts, 1):
            rcost = part.get("cost_inr", 0)
            total_a += rcost
            draw_row(
                idx_str=idx,
                desc=part.get("name", "Part"),
                dims=part.get("dimensions_str", "-"),
                cat="Part",
                part_no=f"{idx:02d}",
                mat=part.get("material_short", "-"),
                qty=part.get("quantity", 1),
                wt=f"{part.get('weight_kg', 0):.3f}",
                proc=part.get("manufacturing_processes_str", "-"),
                cost_val=_fmt_inr(rcost)
            )
            items_count = idx
    else:
        rcost = quote_data.get("order_total", 0)
        total_a = rcost
        bb = quote_data.get("bounding_box", {})
        d_str = f"{bb.get('sizeX', 0):.0f}x{bb.get('sizeY', 0):.0f}x{bb.get('sizeZ', 0):.0f}" if bb else "CAD Data"
        draw_row(
            "1",
            source_filename.replace('.pdf','').replace('.step','')[:25] if source_filename else "CNC Part",
            d_str,
            "Part",
            "01",
            quote_data.get("material", "-")[:12],
            quote_data.get("quantity", 1),
            f"{quote_data.get('mass_kg', 0):.3f}",
            quote_data.get("process", "CNC Machining"),
            _fmt_inr(rcost)
        )
        items_count = 1

    # ── TOTALS APPENDED ROWS ─────────────────────────────────────────────────
    # In Image 3, the totals are perfectly aligned below the table,
    # where the Sr# column increments, the middle columns merge into a label, and Cost is filled.
    label_w = sum(col_w[1:-1]) # Everything between Sr# and Cost
    cost_w = col_w[-1]

    def draw_appended_row(desc_label, cost_val, color=None, is_words=False):
        nonlocal items_count
        items_count += 1
        
        h = 6
        x = pdf.get_x()
        y = pdf.get_y()

        fill = False
        if color:
            pdf.set_fill_color(*color)
            fill = True

        # Sr# Col
        pdf.set_xy(x, y)
        pdf.cell(col_w[0], h, str(items_count), border=1, align="C", fill=fill)
        
        # Label & Cost
        if is_words:
            # Spans label_w AND cost_w
            pdf.set_xy(x + col_w[0], y)
            pdf._set_font("B", 7)
            pdf.cell(label_w + cost_w, h, desc_label, border=1, align="L", fill=fill)
        else:
            pdf.set_xy(x + col_w[0], y)
            pdf.cell(label_w, h, desc_label, border=1, align="C", fill=fill)
            pdf.set_xy(x + col_w[0] + label_w, y)
            pdf._set_font("B" if "TOTAL" in desc_label else "", 7)
            pdf.cell(cost_w, h, cost_val, border=1, align="C", fill=fill)

        pdf._set_font("", 6.5) # reset
        pdf.set_y(y + h)

    # 1. Total A
    draw_appended_row("TOTAL A", _fmt_inr(total_a))
    
    # 2. Additions (Image 3 shows these even if 0, but as blanks or values)
    draw_appended_row("SURFACE TREATMENT/COATING", _fmt_inr(0))
    draw_appended_row("Internal Logistics, Manufacturing Ops, Rework", _fmt_inr(0))
    draw_appended_row("Engineering Charges", _fmt_inr(0))

    # 3. Total B
    draw_appended_row("TOTAL B", _fmt_inr(total_a))

    # 4. Taxation rows (We do SGST then CGST cleanly)
    sgst = quote_data.get("sgst", total_a * 0.09)
    cgst = quote_data.get("cgst", total_a * 0.09)
    
    # SGST
    draw_appended_row("Taxation C - SGST @ 9%", _fmt_inr(sgst))
    # CGST
    draw_appended_row("Taxation C - CGST @ 9%", _fmt_inr(cgst))

    # 5. Grand Total (Green Highlight)
    grand_total = quote_data.get("grand_total", total_a + sgst + cgst)
    lgreen = (210, 245, 210) # Light lime-green from Image 3
    draw_appended_row("GRAND TOTAL = (A+B+C)", _fmt_inr(grand_total), color=lgreen)

    # 6. Amount in Words (Green Highlight)
    words = amount_in_words(grand_total)
    draw_appended_row(f" Amount in Words: {words}", "", color=lgreen, is_words=True)

    pdf.ln(15)

    # ── TERMS & CONDITIONS ───────────────────────────────────────────────────
    pdf._set_font("B", 8)
    pdf.cell(0, 5, "Terms & Conditions:", ln=True)
    pdf._set_font("", 8)

    terms = [
        "GST @18% against supply order.",
        "Delivery Time within 3 weeks, Inclusive of Transportation.",
        "70% Advance and remaining payment successful quality acceptance by client.",
        "Validity of the above quotation for 15 days.",
        "All disputes are subject to Pune jurisdiction only."
    ]
    for i, t in enumerate(terms, 1):
        pdf.cell(0, 4.5, f"{i}. {t}", ln=True)

    pdf.ln(8)

    # ── SIGNATURE ────────────────────────────────────────────────────────────
    pdf._set_font("", 9)
    pdf.cell(0, 5, "Yours Faithfully,", ln=True)
    pdf.ln(8)
    pdf._set_font("B", 9)
    pdf.cell(0, 5, "For ACCU DESIGN", ln=True)
    pdf.ln(8)
    # Stamp / Signature placeholder space
    pdf._set_font("", 8)
    pdf.cell(0, 5, "Proprietor", ln=True)

    # Optional Isometric Screenshot at top right below header
    if screenshot_b64:
        # Save it and place it dynamically near the To address
        pass # Based on Image 3, we don't pollute the pure table format with a screenshot unless required. Let's omit it for 100% authenticity to Image 3, as Image 3 has no screenshot.

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name
