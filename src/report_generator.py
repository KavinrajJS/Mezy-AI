"""
src/report_generator.py
-----------------------
Generates executive intelligence reports in PDF (ReportLab) and Word (.docx).
Supports English and Tamil languages with strict accuracy rules:
  • All metrics calculated directly via Python and Pandas.
  • Zero AI arithmetic hallucination.
  • Original customer review quotes remain verbatim in their uploaded language.
  • Tamil Unicode font detection and graceful degradation for PDF.
  • Formats: PDF and Word (.docx).
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from config.settings import BASE_DIR, DB_PATH
from src.database import get_all_actions

from PIL import Image as PILImage, ImageDraw as PILImageDraw, ImageFont as PILImageFont

# ── ReportLab imports ──────────────────────────────────────────────────────
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        HRFlowable,
        Image as RLImage,
        KeepTogether,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ── python-docx imports ───────────────────────────────────────────────────
try:
    import docx
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement, parse_xml
    from docx.oxml.ns import nsdecls, qn
    from docx.shared import Inches, Pt, RGBColor
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


# ── Tamil Font Discovery & Registration for ReportLab ───────────────────────
_TAMIL_FONT_REGISTERED = False
_TAMIL_FONT_NAME: Optional[str] = None


def discover_and_register_tamil_font() -> Optional[str]:
    """Search system font directories and register a Tamil-capable TTF/TTC font for ReportLab.

    Returns the registered font family name, or None if no Tamil font is available.
    """
    global _TAMIL_FONT_REGISTERED, _TAMIL_FONT_NAME

    if not REPORTLAB_AVAILABLE:
        return None

    if _TAMIL_FONT_REGISTERED and _TAMIL_FONT_NAME:
        return _TAMIL_FONT_NAME

    font_search_paths = [
        Path(r"C:\Windows\Fonts"),
        Path(os.path.expanduser("~/.fonts")),
        Path("/usr/share/fonts/truetype"),
        Path("/usr/local/share/fonts"),
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
        BASE_DIR / "assets" / "fonts",
    ]

    # Candidate fonts in order of preference
    candidates = [
        ("Nirmala", "Nirmala.ttc", 0, 1),      # Windows Nirmala UI (subfont 0=reg, 1=bold)
        ("NirmalaUI", "Nirmala.ttf", None, None),
        ("Latha", "latha.ttf", None, None),
        ("Vijaya", "vijaya.ttf", None, None),
        ("MuktiNarrow", "MuktiNarrow.ttf", None, None),
    ]

    for search_dir in font_search_paths:
        if not search_dir.exists():
            continue

        for font_name, filename, reg_idx, bold_idx in candidates:
            target_file = search_dir / filename
            if not target_file.exists():
                # Case-insensitive check on Windows/Linux
                matches = list(search_dir.glob(filename))
                if matches:
                    target_file = matches[0]

            if target_file.exists():
                try:
                    if reg_idx is not None:
                        # TTC Collection
                        pdfmetrics.registerFont(
                            TTFont(font_name, str(target_file), subfontIndex=reg_idx)
                        )
                        bold_name = f"{font_name}-Bold"
                        if bold_idx is not None:
                            try:
                                pdfmetrics.registerFont(
                                    TTFont(bold_name, str(target_file), subfontIndex=bold_idx)
                                )
                                registerFontFamily(
                                    font_name,
                                    normal=font_name,
                                    bold=bold_name,
                                    italic=font_name,
                                    boldItalic=bold_name,
                                )
                            except Exception:
                                registerFontFamily(font_name, normal=font_name, bold=font_name)
                        else:
                            registerFontFamily(font_name, normal=font_name, bold=font_name)
                    else:
                        pdfmetrics.registerFont(TTFont(font_name, str(target_file)))
                        registerFontFamily(font_name, normal=font_name, bold=font_name)

                    _TAMIL_FONT_NAME = font_name
                    _TAMIL_FONT_REGISTERED = True
                    return _TAMIL_FONT_NAME
                except Exception:
                    continue

    return None


# ── Grounded Data Builder ──────────────────────────────────────────────────
def build_report_data(
    reviews_df: Optional[pd.DataFrame] = None,
    analysis_results: Optional[Dict[str, Any]] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    language: str = "English",
) -> Dict[str, Any]:
    """Extract and calculate grounded report data.

    All numerical results are computed strictly with Python and Pandas.
    Customer review quotes remain verbatim in their original uploaded text.
    """
    lang = "Tamil" if str(language).strip().capitalize() == "Tamil" else "English"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 1. Basic counts & summary
    total_reviews = 0
    avg_rating: Optional[float] = None
    has_ratings = False
    ratings_count = 0
    date_coverage = "Not provided"

    if reviews_df is not None and not reviews_df.empty:
        total_reviews = len(reviews_df)

        if "rating" in reviews_df.columns:
            valid_ratings = pd.to_numeric(reviews_df["rating"], errors="coerce").dropna()
            ratings_count = len(valid_ratings)
            if ratings_count > 0:
                has_ratings = True
                avg_rating = round(float(valid_ratings.mean()), 1)

        # Date coverage
        for d_col in ["review_date", "date", "created_at", "timestamp"]:
            if d_col in reviews_df.columns:
                parsed_dates = pd.to_datetime(reviews_df[d_col], errors="coerce").dropna()
                if not parsed_dates.empty:
                    d_min = parsed_dates.min().strftime("%d-%m-%Y")
                    d_max = parsed_dates.max().strftime("%d-%m-%Y")
                    date_coverage = f"{d_min} to {d_max}"
                    break
    elif analysis_results and "summary" in analysis_results:
        total_reviews = int(analysis_results["summary"].get("total_reviews", 0))

    # 2. Sentiment calculation
    sentiment_breakdown: List[Dict[str, Any]] = []
    supported_labels = ["Positive", "Negative", "Neutral", "Mixed"]

    if reviews_df is not None and not reviews_df.empty and "sentiment" in reviews_df.columns:
        s_counts = reviews_df["sentiment"].astype(str).str.strip().str.capitalize().value_counts()
        for s_label in supported_labels:
            cnt = int(s_counts.get(s_label, 0))
            pct = round((cnt / total_reviews * 100.0), 1) if total_reviews > 0 else 0.0
            sentiment_breakdown.append({
                "sentiment": s_label,
                "count": cnt,
                "percentage": pct,
            })
        if "Uncertain" in s_counts and s_counts["Uncertain"] > 0:
            u_cnt = int(s_counts["Uncertain"])
            u_pct = round((u_cnt / total_reviews * 100.0), 1) if total_reviews > 0 else 0.0
            sentiment_breakdown.append({
                "sentiment": "Uncertain",
                "count": u_cnt,
                "percentage": u_pct,
            })
    elif analysis_results and "per_review_breakdown" in analysis_results and analysis_results["per_review_breakdown"]:
        breakdown = analysis_results["per_review_breakdown"]
        sent_series = pd.Series([
            str(item.get("sentiment", "Neutral")).strip().capitalize()
            for item in breakdown if isinstance(item, dict)
        ])
        s_counts = sent_series.value_counts()
        for s_label in supported_labels:
            cnt = int(s_counts.get(s_label, 0))
            pct = round((cnt / total_reviews * 100.0), 1) if total_reviews > 0 else 0.0
            sentiment_breakdown.append({
                "sentiment": s_label,
                "count": cnt,
                "percentage": pct,
            })
        if "Uncertain" in s_counts and s_counts["Uncertain"] > 0:
            u_cnt = int(s_counts["Uncertain"])
            u_pct = round((u_cnt / total_reviews * 100.0), 1) if total_reviews > 0 else 0.0
            sentiment_breakdown.append({
                "sentiment": "Uncertain",
                "count": u_cnt,
                "percentage": u_pct,
            })
    elif analysis_results and "sentiment_stats" in analysis_results:
        stats = analysis_results["sentiment_stats"]
        for s_label in supported_labels:
            key = s_label.lower()
            cnt = int(stats.get(key, 0))
            pct_val = stats.get(f"{key}_pct")
            if cnt == 0 and pct_val is not None and float(pct_val) > 0 and total_reviews > 0:
                cnt = int(round(float(pct_val) * total_reviews / 100.0))
            if pct_val is not None:
                pct = float(pct_val)
            else:
                pct = round((cnt / total_reviews * 100.0), 1) if total_reviews > 0 else 0.0
            sentiment_breakdown.append({
                "sentiment": s_label,
                "count": cnt,
                "percentage": pct,
            })
        if int(stats.get("uncertain", 0)) > 0 or float(stats.get("uncertain_pct", 0.0)) > 0:
            u_cnt = int(stats.get("uncertain", 0))
            u_pct = float(stats.get("uncertain_pct", round((u_cnt / total_reviews * 100.0), 1) if total_reviews > 0 else 0.0))
            sentiment_breakdown.append({
                "sentiment": "Uncertain",
                "count": u_cnt,
                "percentage": u_pct,
            })

    # 3. Narrative highlights & feedback themes
    executive_summary = ""
    customer_likes: List[Dict[str, str]] = []
    common_complaints: List[Dict[str, str]] = []
    topics_needing_improvement: List[Dict[str, str]] = []

    if analysis_results and isinstance(analysis_results, dict):
        executive_summary = (
            analysis_results.get("summary", {}).get("executive_summary")
            or analysis_results.get("executive_summary", "")
        )

        # Likes
        for item in analysis_results.get("customer_likes", []):
            if isinstance(item, dict):
                customer_likes.append({
                    "topic": str(item.get("topic", "General Praise")),
                    "summary": str(item.get("summary", "")),
                    "evidence_quote": str(item.get("evidence_quote", "")),
                })

        # Complaints
        for item in analysis_results.get("common_complaints", []):
            if isinstance(item, dict):
                common_complaints.append({
                    "topic": str(item.get("topic", "Operational Friction")),
                    "summary": str(item.get("summary", "")),
                    "evidence_quote": str(item.get("evidence_quote", "")),
                })

        # Topics needing improvement
        recs = analysis_results.get("actionable_recommendations", [])
        for rec in recs:
            if isinstance(rec, dict):
                topics_needing_improvement.append({
                    "area": str(rec.get("area", "Service / Operations")),
                    "priority": str(rec.get("priority", "Medium")),
                    "recommendation": str(rec.get("recommendation", "")),
                    "reasoning": str(rec.get("reasoning", "")),
                    "evidence": str(rec.get("supporting_evidence", "")),
                })

    # 4. Saved Actions from SQLite
    saved_actions = actions if actions is not None else get_all_actions()

    # 5. Data quality limitations
    limitations: List[str] = []
    if total_reviews == 0:
        limitations.append("Insufficient review data provided to compute statistical patterns.")
    elif total_reviews < 10:
        limitations.append(f"Small sample size ({total_reviews} reviews); patterns should be treated as preliminary.")

    if not has_ratings:
        limitations.append("Star ratings were absent or invalid in the uploaded dataset.")
    elif ratings_count < total_reviews:
        limitations.append(f"Ratings were only provided on {ratings_count} of {total_reviews} reviews.")

    if date_coverage == "Not provided":
        limitations.append("Date information was not present in the dataset; temporal trends cannot be established.")

    return {
        "language": lang,
        "generation_date": now_str,
        "total_reviews": total_reviews,
        "has_ratings": has_ratings,
        "avg_rating": avg_rating,
        "date_coverage": date_coverage,
        "executive_summary": executive_summary,
        "sentiment_breakdown": sentiment_breakdown,
        "customer_likes": customer_likes,
        "common_complaints": common_complaints,
        "topics_needing_improvement": topics_needing_improvement,
        "saved_actions": saved_actions,
        "limitations": limitations,
    }


def generate_sentiment_pie_chart_png(
    sentiment_breakdown: List[Dict[str, Any]],
    language: str = "English",
) -> Optional[bytes]:
    """Generate a clean, high-DPI PNG pie chart showing sentiment category distribution.

    Uses Pillow with the exact Mezy palette and renders slice angles directly
    from verified review calculation percentages.
    """
    if not sentiment_breakdown:
        return None

    color_map = {
        "Positive":  "#22c55e",  # Green
        "Negative":  "#ef4444",  # Red
        "Neutral":   "#64748b",  # Cement grey
        "Mixed":     "#2563eb",  # Contrasting blue
        "Uncertain": "#94a3b8",
    }

    slices_to_draw = [
        s for s in sentiment_breakdown
        if (s.get("count", 0) > 0 or s.get("percentage", 0) > 0)
    ]
    if not slices_to_draw:
        return None

    try:
        # Clean canvas for sharp rendering
        img = PILImage.new("RGBA", (620, 260), (255, 255, 255, 0))
        draw = PILImageDraw.Draw(img)

        # Resolve typography
        font = None
        if language == "Tamil":
            for font_cand in ["Nirmala.ttc", "latha.ttf", "vijaya.ttf", "segoeui.ttf", "arial.ttf"]:
                try:
                    font = PILImageFont.truetype(font_cand, 13)
                    break
                except Exception:
                    continue
        else:
            for font_cand in ["segoeui.ttf", "arial.ttf", "calibri.ttf"]:
                try:
                    font = PILImageFont.truetype(font_cand, 13)
                    break
                except Exception:
                    continue

        if font is None:
            font = PILImageFont.load_default()

        cx, cy, r = 130, 130, 95
        bbox = (cx - r, cy - r, cx + r, cy + r)

        total_counts = sum(s.get("count", 0) for s in slices_to_draw)
        start_angle = -90.0
        for i, s in enumerate(slices_to_draw):
            s_name = s.get("sentiment", "Neutral")
            cnt = s.get("count", 0)
            pct = float(s.get("percentage", 0))
            c_hex = color_map.get(s_name, "#64748b")

            if i == len(slices_to_draw) - 1:
                end_angle = 270.0
            else:
                if total_counts > 0:
                    extent = (cnt / total_counts) * 360.0
                else:
                    total_pct = sum(item.get("percentage", 0.0) for item in slices_to_draw)
                    extent = (pct / total_pct) * 360.0 if total_pct > 0 else 0.0
                end_angle = start_angle + extent

            draw.pieslice(bbox, start=start_angle, end=end_angle, fill=c_hex, outline="white", width=2)
            start_angle = end_angle

        # Legend on the right - show complete category distribution
        legend_items = [
            s for s in sentiment_breakdown
            if s.get("sentiment") in ["Positive", "Negative", "Neutral", "Mixed"]
            or s.get("count", 0) > 0 or s.get("percentage", 0) > 0
        ]
        if not legend_items:
            legend_items = slices_to_draw

        lx = 275
        total_items = len(legend_items)
        item_height = 34
        ly = max(20, int(130 - (total_items * item_height) / 2))

        for s in legend_items:
            s_name = s.get("sentiment", "Neutral")
            cnt = s.get("count", 0)
            pct = s.get("percentage", 0)
            c_hex = color_map.get(s_name, "#64748b")

            # Crisp marker with outline for distinct contrast against white report background
            draw.rounded_rectangle((lx, ly + 2, lx + 18, ly + 20), radius=4, fill=c_hex, outline="#334155" if s_name == "Neutral" else "#cbd5e1", width=1)

            display_name = s_name
            if language == "Tamil":
                display_name = SENTIMENT_MAP_TAMIL.get(s_name, s_name)

            label_text = f"{display_name}: {pct}% ({cnt})"
            draw.text((lx + 28, ly + 3), label_text, fill="#0f172a", font=font)
            ly += item_height

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return None


# ── Multi-language UI string definitions for reports ───────────────────────
REPORT_LABELS = {
    "English": {
        "title": "Mezy Customer Review Intelligence Report",
        "subtitle": "Synthesized executive findings grounded in verified customer feedback",
        "gen_date": "Generated Date",
        "exec_summary_heading": "Executive Summary",
        "sentiment_heading": "Review Volume & Sentiment Distribution",
        "total_reviews": "Total Reviews Analysed",
        "avg_rating": "Average Customer Rating",
        "sentiment_col": "Sentiment",
        "count_col": "Count",
        "pct_col": "Percentage",
        "strengths_heading": "Main Positive Feedback",
        "complaints_heading": "Common Customer Complaints & Friction Points",
        "improvements_heading": "Key Areas & Topics Needing Improvement",
        "actions_heading": "Saved Improvement Actions & Priorities",
        "limitations_heading": "Data Quality & Limitations",
        "no_summary": "No executive summary available for this dataset.",
        "no_likes": "No dominant praise patterns detected.",
        "no_complaints": "No recurring complaint patterns detected.",
        "no_improvements": "No specific improvement topics registered.",
        "no_actions": "No improvement actions have been saved yet in the Action Tracker.",
        "no_limitations": "No data-quality limitations identified.",
        "evidence_quote": "Customer Evidence Quote:",
        "action_title": "Issue Title",
        "action_plan": "Suggested Action",
        "priority": "Priority",
        "status": "Status",
        "notes": "Notes",
        "footer_text": "Mezy AI • Confidential Customer Review Intelligence Report",
        "page": "Page",
        "of": "of",
    },
    "Tamil": {
        "title": "Mezy வாடிக்கையாளர் விமர்சன நுண்ணறிவு அறிக்கை",
        "subtitle": "வாடிக்கையாளர் கருத்துகளின் அடிப்படையில் உருவாக்கப்பட்ட நிர்வாக அறிக்கை",
        "gen_date": "உருவாக்கப்பட்ட தேதி",
        "exec_summary_heading": "நிர்வாக சுருக்கம்",
        "sentiment_heading": "விமர்சன அளவு & மனநிலை பங்கீடு",
        "total_reviews": "ஆய்வு செய்யப்பட்ட மொத்த விமர்சனங்கள்",
        "avg_rating": "சராசரி வாடிக்கையாளர் மதிப்பீடு",
        "sentiment_col": "மனநிலை",
        "count_col": "எண்ணிக்கை",
        "pct_col": "சதவீதம்",
        "strengths_heading": "முக்கிய நேர்மறை கருத்துகள்",
        "complaints_heading": "பொதுவான புகார்கள் & குறைபாடுகள்",
        "improvements_heading": "மேம்படுத்த வேண்டிய முக்கிய தலைப்புகள்",
        "actions_heading": "சேமிக்கப்பட்ட மேம்பாட்டு நடவடிக்கைகள் & முன்னுரிமைகள்",
        "limitations_heading": "தரவுத் தரம் & வரம்புகள்",
        "no_summary": "இந்த தரவுத்தொகுப்பிற்கு நிர்வாக சுருக்கம் எதுவும் கிடைக்கவில்லை.",
        "no_likes": "குறிப்பிடத்தக்க பாராட்டு முறைகள் எதுவும் கண்டறியப்படவில்லை.",
        "no_complaints": "குறிப்பிடத்தக்க புகார் முறைகள் எதுவும் கண்டறியப்படவில்லை.",
        "no_improvements": "குறிப்பிட்ட மேம்பாட்டு பகுதிகள் எதுவும் பதிவு செய்யப்படவில்லை.",
        "no_actions": "நடவடிக்கை கண்காணிப்பில் இதுவரை எந்த நடவடிக்கைகளும் சேமிக்கப்படவில்லை.",
        "no_limitations": "தரவுத் தரத்தில் குறிப்பிடத்தக்க வரம்புகள் எதுவும் இல்லை.",
        "evidence_quote": "வாடிக்கையாளர் ஆதார மேற்கோள்:",
        "action_title": "சிக்கல் தலைப்பு",
        "action_plan": "பரிந்துரைக்கப்பட்ட நடவடிக்கை",
        "priority": "முன்னுரிமை",
        "status": "நிலை",
        "notes": "குறிப்புகள்",
        "footer_text": "Mezy AI • வாடிக்கையாளர் விமர்சன நுண்ணறிவு அறிக்கை",
        "page": "பக்கம்",
        "of": "/",
    },
}

SENTIMENT_MAP_TAMIL = {
    "Positive": "நேர்மறை (Positive)",
    "Negative": "எதிர்மறை (Negative)",
    "Neutral": "நடுநிலை (Neutral)",
    "Mixed": "கலப்பு (Mixed)",
    "Uncertain": "நிச்சயமற்றது (Uncertain)",
}

PRIORITY_MAP_TAMIL = {
    "High": "அதிகம் (High)",
    "Medium": "நடுத்தரம் (Medium)",
    "Low": "குறைவு (Low)",
}

STATUS_MAP_TAMIL = {
    "Open": "திறந்த நிலை (Open)",
    "In Progress": "செயலில் (In Progress)",
    "Resolved": "தீர்க்கப்பட்டது (Resolved)",
}


# ── Custom ReportLab Canvas for Running Headers & Page Numbers ─────────────
class _MezyNumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page counts."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []
        self.doc_language = "English"
        self.doc_font = "Helvetica"

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_page_decorations(self, total_pages: int) -> None:
        self.saveState()
        labels = REPORT_LABELS.get(self.doc_language, REPORT_LABELS["English"])

        font_name = self.doc_font if self.doc_font in pdfmetrics.getRegisteredFontNames() else "Helvetica"
        self.setFont(font_name, 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 32, self._pagesize[0] - 36, 32)

        # Footer Left
        footer_text = labels["footer_text"]
        self.drawString(36, 20, footer_text)

        # Footer Right: Page X of Y
        page_str = f"{labels['page']} {self._pageNumber} {labels['of']} {total_pages}"
        self.drawRightString(self._pagesize[0] - 36, 20, page_str)

        self.restoreState()


# ── PDF Report Generator ───────────────────────────────────────────────────
def generate_pdf_report(
    reviews_df: Optional[pd.DataFrame] = None,
    analysis_results: Optional[Dict[str, Any]] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    language: str = "English",
) -> Tuple[bytes, Optional[str]]:
    """Generate a clean, professional PDF report using ReportLab.

    Returns:
        (pdf_bytes, warning_message)
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab library is not installed in the environment.")

    data = build_report_data(reviews_df, analysis_results, actions, language)
    lang = data["language"]
    labels = REPORT_LABELS.get(lang, REPORT_LABELS["English"])

    warning_msg: Optional[str] = None
    doc_font = "Helvetica"
    doc_font_bold = "Helvetica-Bold"

    if lang == "Tamil":
        tamil_font = discover_and_register_tamil_font()
        if tamil_font:
            doc_font = tamil_font
            doc_font_bold = f"{tamil_font}-Bold" if f"{tamil_font}-Bold" in pdfmetrics.getRegisteredFontNames() else tamil_font
        else:
            warning_msg = (
                "Tamil Unicode font is not available on this system. Tamil characters "
                "cannot be rendered correctly in PDF. Please use Word (.docx) export for "
                "complete Tamil script support."
            )

    # Document setup: Letter size with 36pt (0.5 in) margins
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "MezyTitle",
        fontName=doc_font_bold,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#312e81"),  # Indigo 900
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "MezySubtitle",
        fontName=doc_font,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "MezyH1",
        fontName=doc_font_bold,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "MezyBody",
        fontName=doc_font,
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#334155"),
    )
    body_bold = ParagraphStyle(
        "MezyBodyBold",
        fontName=doc_font_bold,
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#0f172a"),
    )
    quote_style = ParagraphStyle(
        "MezyQuote",
        fontName=doc_font,
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#475569"),
        leftIndent=12,
        fontStyle="italic",
        spaceBefore=2,
        spaceAfter=4,
    )
    table_cell = ParagraphStyle(
        "MezyTableCell",
        fontName=doc_font,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )
    table_header = ParagraphStyle(
        "MezyTableHeader",
        fontName=doc_font_bold,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#ffffff"),
    )

    story: List[Any] = []

    # 1. Header & Title Block
    story.append(Paragraph(labels["title"], title_style))
    sub_line = f"{labels['subtitle']} • {labels['gen_date']}: {data['generation_date']}"
    story.append(Paragraph(sub_line, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

    # 2. Executive Summary Box
    story.append(Paragraph(labels["exec_summary_heading"], h1_style))
    summary_text = data["executive_summary"] or labels["no_summary"]
    summary_p = Paragraph(summary_text, body_style)

    summary_table = Table([[summary_p]], colWidths=[540])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))

    # 3. Review Volume & Sentiment Distribution
    story.append(Paragraph(labels["sentiment_heading"], h1_style))

    # KPI summary bar
    rating_display = f"{data['avg_rating']} / 5.0" if data["has_ratings"] and data["avg_rating"] else "N/A"
    kpi_p1 = Paragraph(f"<b>{labels['total_reviews']}:</b> {data['total_reviews']}", body_style)
    kpi_p2 = Paragraph(f"<b>{labels['avg_rating']}:</b> {rating_display}", body_style)
    kpi_p3 = Paragraph(f"<b>Date Span:</b> {data['date_coverage']}", body_style)

    kpi_table = Table([[kpi_p1, kpi_p2, kpi_p3]], colWidths=[180, 180, 180])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 6))

    # Sentiment Breakdown Table
    if data["sentiment_breakdown"]:
        table_rows = [
            [
                Paragraph(labels["sentiment_col"], table_header),
                Paragraph(labels["count_col"], table_header),
                Paragraph(labels["pct_col"], table_header),
            ]
        ]
        for row in data["sentiment_breakdown"]:
            s_name = row["sentiment"]
            if lang == "Tamil":
                s_name = SENTIMENT_MAP_TAMIL.get(s_name, s_name)
            table_rows.append([
                Paragraph(s_name, table_cell),
                Paragraph(str(row["count"]), table_cell),
                Paragraph(f"{row['percentage']}%", table_cell),
            ])

        s_table = Table(table_rows, colWidths=[200, 170, 170])
        s_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#312e81")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(s_table)
    story.append(Spacer(1, 6))

    # Sentiment Distribution Pie Chart
    pie_bytes = generate_sentiment_pie_chart_png(data["sentiment_breakdown"], language=lang)
    if pie_bytes:
        chart_buf = io.BytesIO(pie_bytes)
        rl_chart = RLImage(chart_buf, width=4.5 * inch, height=1.88 * inch)
        rl_chart.hAlign = "CENTER"
        story.append(Spacer(1, 2))
        story.append(rl_chart)
        story.append(Spacer(1, 6))

    # 4. Main Positive Feedback & Quotes
    story.append(Paragraph(labels["strengths_heading"], h1_style))
    if data["customer_likes"]:
        for item in data["customer_likes"][:4]:
            t_title = item["topic"]
            t_summary = item["summary"]
            quote = item["evidence_quote"]
            story.append(Paragraph(f"• <b>{t_title}</b>: {t_summary}", body_style))
            if quote:
                story.append(Paragraph(f'"{quote}"', quote_style))
    else:
        story.append(Paragraph(labels["no_likes"], body_style))
    story.append(Spacer(1, 6))

    # 5. Common Complaints & Friction Points
    story.append(Paragraph(labels["complaints_heading"], h1_style))
    if data["common_complaints"]:
        for item in data["common_complaints"][:4]:
            t_title = item["topic"]
            t_summary = item["summary"]
            quote = item["evidence_quote"]
            story.append(Paragraph(f"• <b>{t_title}</b>: {t_summary}", body_style))
            if quote:
                story.append(Paragraph(f'"{quote}"', quote_style))
    else:
        story.append(Paragraph(labels["no_complaints"], body_style))
    story.append(Spacer(1, 6))

    # 6. Saved Improvement Actions Table (without Status column)
    story.append(Paragraph(labels["actions_heading"], h1_style))
    if data["saved_actions"]:
        act_rows = [
            [
                Paragraph(labels["action_title"], table_header),
                Paragraph(labels["action_plan"], table_header),
                Paragraph(labels["priority"], table_header),
                Paragraph("Evidence", table_header),
            ]
        ]
        for act in data["saved_actions"]:
            p_val = act.get("priority", "Medium")
            if lang == "Tamil":
                p_val = PRIORITY_MAP_TAMIL.get(p_val, p_val)

            ev_str = str(act.get("evidence", ""))
            if len(ev_str) > 75:
                ev_str = ev_str[:72] + "…"

            act_rows.append([
                Paragraph(str(act.get("title", "")), table_cell),
                Paragraph(str(act.get("action", "")), table_cell),
                Paragraph(p_val, table_cell),
                Paragraph(ev_str, table_cell),
            ])

        act_table = Table(act_rows, colWidths=[140, 180, 65, 155])
        act_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(act_table)
    else:
        story.append(Paragraph(labels["no_actions"], body_style))
    story.append(Spacer(1, 8))

    # Build document with custom canvas
    canvas_maker = _MezyNumberedCanvas
    canvas_maker.doc_language = lang
    canvas_maker.doc_font = doc_font

    doc.build(story, canvasmaker=canvas_maker)
    pdf_bytes = buffer.getvalue()
    return pdf_bytes, warning_msg


# ── Word Report Generator (.docx) ──────────────────────────────────────────
def _set_cell_background(cell: Any, fill_hex: str) -> None:
    """Set background color of a Word table cell using XML."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex.lstrip("#")}"/>')
    tc_pr.append(shd)


def _set_cell_margins(cell: Any, top: int = 100, bottom: int = 100, left: int = 150, right: int = 150) -> None:
    """Set padding/margins of a Word table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def generate_docx_report(
    reviews_df: Optional[pd.DataFrame] = None,
    analysis_results: Optional[Dict[str, Any]] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    language: str = "English",
) -> bytes:
    """Generate a clean, structured Word document (.docx) using python-docx.

    Tamil script is natively supported by modern Word with standard Unicode fonts.
    """
    if not DOCX_AVAILABLE:
        raise RuntimeError("python-docx library is not installed in the environment.")

    data = build_report_data(reviews_df, analysis_results, actions, language)
    lang = data["language"]
    labels = REPORT_LABELS.get(lang, REPORT_LABELS["English"])

    doc = docx.Document()

    # Page Margins: 0.75 in
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Base font setting
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Segoe UI"
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(51, 65, 85)

    # 1. Document Title
    p_title = doc.add_paragraph()
    r_title = p_title.add_run(labels["title"])
    r_title.font.name = "Segoe UI"
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(49, 46, 129)  # Indigo 900
    p_title.paragraph_format.space_after = Pt(2)

    # Subtitle with date
    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run(f"{labels['subtitle']}  |  {labels['gen_date']}: {data['generation_date']}")
    r_sub.font.size = Pt(9)
    r_sub.font.color.rgb = RGBColor(100, 116, 139)
    p_sub.paragraph_format.space_after = Pt(14)

    # 2. Executive Summary Callout
    h_exec = doc.add_paragraph()
    r_hexec = h_exec.add_run(labels["exec_summary_heading"])
    r_hexec.font.size = Pt(13)
    r_hexec.font.bold = True
    r_hexec.font.color.rgb = RGBColor(15, 23, 42)
    h_exec.paragraph_format.space_after = Pt(4)

    summary_box = doc.add_table(rows=1, cols=1)
    summary_box.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = summary_box.cell(0, 0)
    _set_cell_background(cell, "F8FAFC")
    _set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    p_sum = cell.paragraphs[0]
    p_sum.paragraph_format.space_after = Pt(0)
    r_sum_text = p_sum.add_run(data["executive_summary"] or labels["no_summary"])
    r_sum_text.font.size = Pt(9.5)
    r_sum_text.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 3. Review Volume & Sentiment
    h_sent = doc.add_paragraph()
    r_hsent = h_sent.add_run(labels["sentiment_heading"])
    r_hsent.font.size = Pt(13)
    r_hsent.font.bold = True
    r_hsent.font.color.rgb = RGBColor(15, 23, 42)
    h_sent.paragraph_format.space_after = Pt(4)

    rating_display = f"{data['avg_rating']} / 5.0" if data["has_ratings"] and data["avg_rating"] else "N/A"
    p_kpi = doc.add_paragraph()
    p_kpi.add_run(f"{labels['total_reviews']}: ").bold = True
    p_kpi.add_run(f"{data['total_reviews']}   |   ")
    p_kpi.add_run(f"{labels['avg_rating']}: ").bold = True
    p_kpi.add_run(f"{rating_display}   |   ")
    p_kpi.add_run("Date Span: ").bold = True
    p_kpi.add_run(f"{data['date_coverage']}")
    p_kpi.paragraph_format.space_after = Pt(6)

    # Sentiment Table
    if data["sentiment_breakdown"]:
        s_table = doc.add_table(rows=len(data["sentiment_breakdown"]) + 1, cols=3)
        s_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        headers = [labels["sentiment_col"], labels["count_col"], labels["pct_col"]]
        for col_idx, h_text in enumerate(headers):
            h_cell = s_table.cell(0, col_idx)
            _set_cell_background(h_cell, "312E81")
            _set_cell_margins(h_cell, top=80, bottom=80, left=120, right=120)
            p = h_cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(h_text)
            r.bold = True
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(255, 255, 255)

        for row_idx, row in enumerate(data["sentiment_breakdown"], start=1):
            s_name = row["sentiment"]
            if lang == "Tamil":
                s_name = SENTIMENT_MAP_TAMIL.get(s_name, s_name)
            vals = [s_name, str(row["count"]), f"{row['percentage']}%"]
            bg_color = "F8FAFC" if row_idx % 2 == 0 else "FFFFFF"
            for col_idx, val in enumerate(vals):
                d_cell = s_table.cell(row_idx, col_idx)
                _set_cell_background(d_cell, bg_color)
                _set_cell_margins(d_cell, top=60, bottom=60, left=120, right=120)
                p = d_cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                p.add_run(val).font.size = Pt(9)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Sentiment Distribution Pie Chart
    pie_bytes = generate_sentiment_pie_chart_png(data["sentiment_breakdown"], language=lang)
    if pie_bytes:
        pie_buf = io.BytesIO(pie_bytes)
        p_chart = doc.add_paragraph()
        p_chart.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_chart.paragraph_format.space_before = Pt(4)
        p_chart.paragraph_format.space_after = Pt(8)
        run = p_chart.add_run()
        run.add_picture(pie_buf, width=Inches(4.5))

    # 4. Key Strengths & Likes
    h_likes = doc.add_paragraph()
    r_hlikes = h_likes.add_run(labels["strengths_heading"])
    r_hlikes.font.size = Pt(13)
    r_hlikes.font.bold = True
    r_hlikes.font.color.rgb = RGBColor(15, 23, 42)
    h_likes.paragraph_format.space_after = Pt(4)

    if data["customer_likes"]:
        for item in data["customer_likes"][:5]:
            p_like = doc.add_paragraph(style="List Bullet")
            r_topic = p_like.add_run(f"{item['topic']}: ")
            r_topic.bold = True
            p_like.add_run(item["summary"])
            p_like.paragraph_format.space_after = Pt(2)
            if item["evidence_quote"]:
                p_quote = doc.add_paragraph()
                p_quote.paragraph_format.left_indent = Inches(0.35)
                p_quote.paragraph_format.space_after = Pt(4)
                r_q = p_quote.add_run(f'"{item["evidence_quote"]}"')
                r_q.italic = True
                r_q.font.size = Pt(8.5)
                r_q.font.color.rgb = RGBColor(71, 85, 105)
    else:
        doc.add_paragraph(labels["no_likes"]).paragraph_format.space_after = Pt(4)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 5. Common Complaints
    h_comp = doc.add_paragraph()
    r_hcomp = h_comp.add_run(labels["complaints_heading"])
    r_hcomp.font.size = Pt(13)
    r_hcomp.font.bold = True
    r_hcomp.font.color.rgb = RGBColor(15, 23, 42)
    h_comp.paragraph_format.space_after = Pt(4)

    if data["common_complaints"]:
        for item in data["common_complaints"][:5]:
            p_comp = doc.add_paragraph(style="List Bullet")
            r_topic = p_comp.add_run(f"{item['topic']}: ")
            r_topic.bold = True
            p_comp.add_run(item["summary"])
            p_comp.paragraph_format.space_after = Pt(2)
            if item["evidence_quote"]:
                p_quote = doc.add_paragraph()
                p_quote.paragraph_format.left_indent = Inches(0.35)
                p_quote.paragraph_format.space_after = Pt(4)
                r_q = p_quote.add_run(f'"{item["evidence_quote"]}"')
                r_q.italic = True
                r_q.font.size = Pt(8.5)
                r_q.font.color.rgb = RGBColor(71, 85, 105)
    else:
        doc.add_paragraph(labels["no_complaints"]).paragraph_format.space_after = Pt(4)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 6. Saved Actions Table (without Status column)
    h_acts = doc.add_paragraph()
    r_hacts = h_acts.add_run(labels["actions_heading"])
    r_hacts.font.size = Pt(13)
    r_hacts.font.bold = True
    r_hacts.font.color.rgb = RGBColor(15, 23, 42)
    h_acts.paragraph_format.space_after = Pt(4)

    if data["saved_actions"]:
        act_table = doc.add_table(rows=len(data["saved_actions"]) + 1, cols=4)
        act_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        act_headers = [labels["action_title"], labels["action_plan"], labels["priority"], "Evidence"]
        for col_idx, h_text in enumerate(act_headers):
            h_cell = act_table.cell(0, col_idx)
            _set_cell_background(h_cell, "1E293B")
            _set_cell_margins(h_cell, top=80, bottom=80, left=100, right=100)
            p = h_cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(h_text)
            r.bold = True
            r.font.size = Pt(8.5)
            r.font.color.rgb = RGBColor(255, 255, 255)

        for row_idx, act in enumerate(data["saved_actions"], start=1):
            p_val = act.get("priority", "Medium")
            if lang == "Tamil":
                p_val = PRIORITY_MAP_TAMIL.get(p_val, p_val)

            ev_str = str(act.get("evidence", ""))
            if len(ev_str) > 85:
                ev_str = ev_str[:82] + "…"

            vals = [
                str(act.get("title", "")),
                str(act.get("action", "")),
                p_val,
                ev_str,
            ]
            bg_color = "F8FAFC" if row_idx % 2 == 0 else "FFFFFF"
            for col_idx, val in enumerate(vals):
                d_cell = act_table.cell(row_idx, col_idx)
                _set_cell_background(d_cell, bg_color)
                _set_cell_margins(d_cell, top=60, bottom=60, left=100, right=100)
                p = d_cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                p.add_run(val).font.size = Pt(8.5)
    else:
        doc.add_paragraph(labels["no_actions"]).paragraph_format.space_after = Pt(4)

    # Output to buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
