"""
PDF Quote Generator
"""

import tempfile
from fpdf import FPDF
from datetime import datetime

class QuotePDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 15)
        self.cell(0, 10, "AccuDesign Manufacturing Quote", border=False, align="C")
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

def generate_quote_pdf(quote_data: dict, filename_prefix: str = "quote") -> str:
    """
    Generate a PDF quote and return the path to the temporary PDF file.
    """
    pdf = QuotePDF()
    pdf.add_page()
    
    # Title & Date
    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(0, 10, f"Quote Ref: AD-{datetime.now().strftime('%Y%m%d%H%M%S')}", ln=True)
    pdf.ln(10)
    
    # Part Summary
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Configuration Summary", ln=True)
    pdf.set_font("helvetica", size=11)
    
    summary_items = [
        ("Material", quote_data.get("material", "N/A")),
        ("Process", quote_data.get("process", "N/A")),
        ("Tolerance", quote_data.get("tolerance", "N/A")),
        ("Complexity", quote_data.get("complexity", "N/A")),
        ("Quantity", str(quote_data.get("quantity", 1))),
    ]
    
    for label, val in summary_items:
        pdf.cell(60, 8, label, border=1)
        pdf.cell(100, 8, val, border=1, ln=True)
        
    pdf.ln(10)
    
    # Cost Breakdown
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Per-Unit Cost Breakdown", ln=True)
    pdf.set_font("helvetica", size=11)
    
    bd = quote_data.get("breakdown", {})
    breakdown_items = [
        ("Material Cost", f"${bd.get('material_cost', 0.0):.2f}"),
        ("Machining Cost", f"${bd.get('machining_cost', 0.0):.2f}"),
        ("Drilling Surcharge", f"${bd.get('drilling_cost', 0.0):.2f}"),
        ("Setup (amortised)", f"${bd.get('setup_cost', 0.0):.2f}"),
        ("Overhead", f"${bd.get('overhead', 0.0):.2f}"),
        ("Profit Margin", f"${bd.get('profit_margin', 0.0):.2f}"),
    ]
    
    for label, val in breakdown_items:
        pdf.cell(60, 8, label, border=1)
        pdf.cell(100, 8, val, border=1, ln=True)

    pdf.ln(10)
    
    # Totals
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "Totals", ln=True)
    pdf.set_font("helvetica", size=11)
    
    totals_items = [
        ("Unit Price", f"${quote_data.get('unit_price', 0.0):.2f}"),
        (f"Discount ({quote_data.get('discount_pct', 0.0)}%)", f"${quote_data.get('unit_price', 0.0) - quote_data.get('unit_price_discounted', 0.0):.2f}"),
        ("Unit Price (Discounted)", f"${quote_data.get('unit_price_discounted', 0.0):.2f}"),
        (f"Order Total (x{quote_data.get('quantity', 1)})", f"${quote_data.get('order_total', 0.0):.2f}"),
    ]
    
    for label, val in totals_items:
        pdf.set_font("helvetica", "B" if "Total" in label else "", size=11)
        pdf.cell(80, 8, label, border=1)
        pdf.cell(80, 8, val, border=1, ln=True)
        
    pdf.ln(10)
    
    # Notes
    pdf.set_font("helvetica", "I", 10)
    pdf.multi_cell(0, 8, f"Note: Pricing is based on live market analysis. Metal source: {quote_data.get('price_source', 'N/A')}. Valid for 30 days.")
    
    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        return tmp.name
