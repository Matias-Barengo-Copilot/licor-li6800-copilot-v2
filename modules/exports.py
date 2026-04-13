"""
Export functionality: PDF report generation.
"""
import io
from datetime import datetime

import pandas as pd
import plotly.io as pio

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


class ProgramReport(FPDF if FPDF_AVAILABLE else object):
    def header(self):
        self.set_fill_color(255, 107, 53)   # Urban orange
        self.rect(0, 0, 210, 12, "F")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 12, "  Program IQ  —  Urban Arts Intelligence Dashboard", ln=True)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generated {datetime.now().strftime('%B %d, %Y')}  |  Page {self.page_no()}", align="C")


def generate_pdf(
    metrics: dict,
    df_perf: pd.DataFrame,
    df_teams: pd.DataFrame,
    insights: list[str],
    session_fig=None,
) -> bytes:
    """
    Generate a PDF program report.
    Returns raw bytes of the PDF.
    """
    if not FPDF_AVAILABLE:
        return b""

    pdf = ProgramReport(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Title block ────────────────────────────────────────────────────────
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(255, 107, 53)
    pdf.cell(0, 10, "Program Performance Report", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"School Year 2025/26  ·  3D Game Design  ·  Urban Arts", ln=True)
    pdf.ln(4)

    # ── Key Metrics ────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Key Metrics", ln=True)
    pdf.set_draw_color(255, 107, 53)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    rows_data = [
        ("Total Students", str(metrics.get("total_students", "—"))),
        ("Average Attendance", f"{metrics.get('avg_attendance', 0):.1f}%"),
        ("Sessions Recorded", str(metrics.get("sessions", "—"))),
        ("High Performers (≥90%)", str(metrics.get("high_performers", "—"))),
        ("Students At Risk (<70%)", str(metrics.get("low_performers", "—"))),
        ("Critical (<50%)", str(metrics.get("critical_students", "—"))),
    ]
    for label, value in rows_data:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(80, 6, label, border="B")
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(40, 6, value, border="B", ln=True)
    pdf.ln(6)

    # ── Attendance chart ───────────────────────────────────────────────────
    if session_fig is not None:
        try:
            img_bytes = pio.to_image(session_fig, format="png", width=900, height=350, scale=2)
            img_io = io.BytesIO(img_bytes)
            pdf.image(img_io, x=10, w=190)
            pdf.ln(4)
        except Exception:
            pass

    # ── Team Summary ───────────────────────────────────────────────────────
    if not df_teams.empty:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 8, "Team Performance Summary", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        headers = ["Team", "Students", "Avg Attendance", "Avg Work Quality", "Absences"]
        widths = [55, 25, 35, 40, 30]

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(240, 240, 240)
        for h, w in zip(headers, widths):
            pdf.cell(w, 7, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        for _, row in df_teams.iterrows():
            vals = [
                str(row.get("Project Team Name", "")),
                str(row.get("Students", "")),
                f"{row.get('Avg_Attendance', 0):.1f}%",
                f"{row.get('Avg_Good', 0):.1f}%",
                str(int(row.get("Total_Absences", 0))),
            ]
            for v, w in zip(vals, widths):
                pdf.cell(w, 6, v, border=1)
            pdf.ln()
        pdf.ln(6)

    # ── AI Insights ────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 8, "AI-Generated Insights", ln=True)
    pdf.set_draw_color(124, 58, 237)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    for insight in insights:
        pdf.set_x(12)
        pdf.cell(4, 6, "\u2022")
        pdf.set_x(16)
        pdf.multi_cell(0, 6, insight)
        pdf.ln(2)

    # ── At-Risk Students ───────────────────────────────────────────────────
    at_risk_df = df_perf[df_perf["At Risk"]] if "At Risk" in df_perf.columns else pd.DataFrame()
    if not at_risk_df.empty:
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(239, 68, 68)
        pdf.cell(0, 8, "Students Requiring Attention", ln=True)
        pdf.set_draw_color(239, 68, 68)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(3)

        headers = ["Name", "Attendance", "Absences", "Missing Work", "Priority"]
        widths = [55, 30, 25, 35, 25]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(255, 220, 220)
        for h, w in zip(headers, widths):
            pdf.cell(w, 7, h, border=1, fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        for _, row in at_risk_df.iterrows():
            name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
            att = f"{row.get('Attendance %', 0):.1f}%"
            absent = str(int(row.get("Absent", 0)))
            missing = f"{row.get('% missing_num', 0) or 0:.0f}%"
            priority = str(row.get("Priority", ""))
            for v, w in zip([name, att, absent, missing, priority], widths):
                pdf.cell(w, 6, v, border=1)
            pdf.ln()

    out = pdf.output(dest="S")
    if isinstance(out, str):
        return out.encode("latin-1")
    return bytes(out)
