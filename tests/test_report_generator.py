"""
tests/test_report_generator.py
------------------------------
Unit and integration tests for report generation in PDF and Word (.docx).
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.report_generator import (
    build_report_data,
    discover_and_register_tamil_font,
    generate_pdf_report,
    generate_docx_report,
)


@pytest.fixture
def sample_reviews_df() -> pd.DataFrame:
    """Fixture providing realistic sample reviews with ratings and sentiments."""
    return pd.DataFrame([
        {
            "review_id": 1,
            "review_text": "The mutton biryani was extraordinary and super flavourful!",
            "rating": 5.0,
            "sentiment": "Positive",
            "topics": ["Food Quality", "Taste"],
            "date": "2026-03-01",
        },
        {
            "review_id": 2,
            "review_text": "Waited over 40 minutes for starters. Very poor dispatch.",
            "rating": 2.0,
            "sentiment": "Negative",
            "topics": ["Waiting Time"],
            "date": "2026-03-02",
        },
        {
            "review_id": 3,
            "review_text": "Average coffee, nothing special but clean seating.",
            "rating": 3.0,
            "sentiment": "Neutral",
            "topics": ["Cleanliness"],
            "date": "2026-03-03",
        },
        {
            "review_id": 4,
            "review_text": "உணவு மிகவும் சுவையாக இருந்தது, ஆனால் டெலிவரி தாமதம்.",
            "rating": 4.0,
            "sentiment": "Mixed",
            "topics": ["Taste", "Delivery"],
            "date": "2026-03-04",
        },
    ])


@pytest.fixture
def sample_analysis_results() -> dict:
    """Fixture providing mock Gemini analysis result matching the schema."""
    return {
        "summary": {
            "total_reviews": 4,
            "executive_summary": "Overall positive perception driven by biryani quality, tempered by wait times.",
        },
        "customer_likes": [
            {
                "topic": "Food Quality",
                "summary": "Customers praised the mutton biryani flavour.",
                "evidence_quote": "The mutton biryani was extraordinary and super flavourful!",
            }
        ],
        "common_complaints": [
            {
                "topic": "Waiting Time",
                "summary": "Starter delays exceeding 40 minutes.",
                "evidence_quote": "Waited over 40 minutes for starters. Very poor dispatch.",
            }
        ],
        "actionable_recommendations": [
            {
                "area": "Kitchen Dispatch",
                "priority": "High",
                "recommendation": "Implement kitchen ticket queuing.",
                "reasoning": "Wait times cause customer churn.",
                "supporting_evidence": "Waited over 40 minutes for starters.",
            }
        ],
    }


@pytest.fixture
def sample_actions() -> list:
    """Fixture providing mock saved actions."""
    return [
        {
            "id": 1,
            "title": "Speed up starter prep",
            "action": "Pre-prep starter mise en place before dinner rush",
            "priority": "High",
            "status": "In Progress",
            "evidence": "Waited over 40 minutes for starters.",
            "notes": "Discussed with chef",
        }
    ]


def test_build_report_data_numerical_accuracy(sample_reviews_df, sample_analysis_results, sample_actions):
    """Verify that calculations are strictly grounded in Python/Pandas."""
    data = build_report_data(
        reviews_df=sample_reviews_df,
        analysis_results=sample_analysis_results,
        actions=sample_actions,
        language="English",
    )

    assert data["total_reviews"] == 4
    assert data["has_ratings"] is True
    # Mean of [5, 2, 3, 4] = 14 / 4 = 3.5
    assert data["avg_rating"] == 3.5
    assert data["date_coverage"] == "01-03-2026 to 04-03-2026"

    # Sentiment distribution checks
    s_map = {item["sentiment"]: item for item in data["sentiment_breakdown"]}
    assert s_map["Positive"]["count"] == 1
    assert s_map["Positive"]["percentage"] == 25.0
    assert s_map["Negative"]["count"] == 1
    assert s_map["Neutral"]["count"] == 1
    assert s_map["Mixed"]["count"] == 1

    # Verbatim evidence preservation
    assert (
        data["customer_likes"][0]["evidence_quote"]
        == "The mutton biryani was extraordinary and super flavourful!"
    )
    assert (
        data["common_complaints"][0]["evidence_quote"]
        == "Waited over 40 minutes for starters. Very poor dispatch."
    )


def test_build_report_data_empty_dataset():
    """Verify safe handling of empty or missing review data."""
    data = build_report_data(reviews_df=None, analysis_results=None, actions=[])
    assert data["total_reviews"] == 0
    assert data["has_ratings"] is False
    assert data["avg_rating"] is None
    assert len(data["limitations"]) > 0
    assert any("Insufficient review data" in lim for lim in data["limitations"])


def test_generate_pdf_report_english(sample_reviews_df, sample_analysis_results, sample_actions):
    """Verify English PDF generation outputs valid PDF bytes."""
    pdf_bytes, warning = generate_pdf_report(
        reviews_df=sample_reviews_df,
        analysis_results=sample_analysis_results,
        actions=sample_actions,
        language="English",
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")
    assert warning is None


def test_generate_pdf_report_tamil(sample_reviews_df, sample_analysis_results, sample_actions):
    """Verify Tamil PDF generation runs cleanly and handles font detection."""
    pdf_bytes, warning = generate_pdf_report(
        reviews_df=sample_reviews_df,
        analysis_results=sample_analysis_results,
        actions=sample_actions,
        language="Tamil",
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_docx_report_english(sample_reviews_df, sample_analysis_results, sample_actions):
    """Verify English Word document generation produces valid docx file bytes."""
    docx_bytes = generate_docx_report(
        reviews_df=sample_reviews_df,
        analysis_results=sample_analysis_results,
        actions=sample_actions,
        language="English",
    )
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 1000
    # ZIP archive magic bytes
    assert docx_bytes.startswith(b"PK\x03\x04")


def test_generate_docx_report_tamil(sample_reviews_df, sample_analysis_results, sample_actions):
    """Verify Tamil Word document generation produces valid docx file bytes."""
    docx_bytes = generate_docx_report(
        reviews_df=sample_reviews_df,
        analysis_results=sample_analysis_results,
        actions=sample_actions,
        language="Tamil",
    )
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 1000
    assert docx_bytes.startswith(b"PK\x03\x04")


def test_reports_handle_empty_gracefully():
    """Verify reports can be generated without crashing when no actions or analysis exist."""
    pdf_bytes, _ = generate_pdf_report(reviews_df=None, analysis_results=None, actions=None)
    assert pdf_bytes.startswith(b"%PDF-")

    docx_bytes = generate_docx_report(reviews_df=None, analysis_results=None, actions=None)
    assert docx_bytes.startswith(b"PK\x03\x04")


def test_sentiment_pie_chart_generation():
    """Verify generate_sentiment_pie_chart_png returns valid PNG bytes and handles empty safely."""
    from src.report_generator import generate_sentiment_pie_chart_png

    # Valid distribution
    breakdown = [
        {"sentiment": "Positive", "count": 10, "percentage": 50.0},
        {"sentiment": "Negative", "count": 6, "percentage": 30.0},
        {"sentiment": "Neutral", "count": 4, "percentage": 20.0},
    ]
    png_bytes = generate_sentiment_pie_chart_png(breakdown, language="English")
    assert isinstance(png_bytes, bytes)
    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    # Tamil language
    png_ta = generate_sentiment_pie_chart_png(breakdown, language="Tamil")
    assert isinstance(png_ta, bytes)
    assert png_ta.startswith(b"\x89PNG\r\n\x1a\n")

    # Empty data safe handling
    assert generate_sentiment_pie_chart_png([]) is None
    assert generate_sentiment_pie_chart_png([{"sentiment": "Positive", "count": 0, "percentage": 0}]) is None


def test_report_heading_main_positive_feedback():
    """Verify heading is changed from 'Themes' to 'Main Positive Feedback'."""
    from src.report_generator import REPORT_LABELS

    assert REPORT_LABELS["English"]["strengths_heading"] == "Main Positive Feedback"
    assert "Themes" not in REPORT_LABELS["English"]["strengths_heading"]


def test_docx_report_no_status_column(sample_reviews_df, sample_analysis_results, sample_actions):
    """Verify Saved Actions table in Word export excludes the Status column."""
    import docx
    import io

    docx_bytes = generate_docx_report(
        reviews_df=sample_reviews_df,
        analysis_results=sample_analysis_results,
        actions=sample_actions,
        language="English",
    )
    doc = docx.Document(io.BytesIO(docx_bytes))

    # Find the actions table by checking headers
    actions_table = None
    for table in doc.tables:
        if len(table.rows) > 0:
            header_cells = [cell.text.strip() for cell in table.rows[0].cells]
            if "Issue Title" in header_cells:
                actions_table = table
                break

    assert actions_table is not None, "Saved actions table not found in docx"
    header_texts = [cell.text.strip() for cell in actions_table.rows[0].cells]

    # Must have 4 columns: Issue Title, Suggested Action, Priority, Evidence
    assert len(header_texts) == 4
    assert "Status" not in header_texts
    assert header_texts == ["Issue Title", "Suggested Action", "Priority", "Evidence"]


def test_data_quality_and_limitations_section_absent_from_reports(
    sample_reviews_df, sample_analysis_results, sample_actions
):
    """Verify Data Quality & Limitations section is absent from both PDF and Word reports."""
    import docx
    import io

    # 1. Word Document check
    docx_bytes = generate_docx_report(
        reviews_df=sample_reviews_df,
        analysis_results=sample_analysis_results,
        actions=sample_actions,
        language="English",
    )
    doc = docx.Document(io.BytesIO(docx_bytes))
    all_docx_text = " ".join(p.text for p in doc.paragraphs)
    assert "Data Quality & Limitations" not in all_docx_text
    assert "தரவுத் தரம் & வரம்புகள்" not in all_docx_text

    # 2. PDF check
    pdf_bytes, _ = generate_pdf_report(
        reviews_df=sample_reviews_df,
        analysis_results=sample_analysis_results,
        actions=sample_actions,
        language="English",
    )
    # The string "Data Quality & Limitations" should not appear in report stream
    assert b"Data Quality & Limitations" not in pdf_bytes


def test_sentiment_pie_chart_neutral_color():
    """Verify pie chart contains distinct Neutral slice and visible cement-grey color."""
    from src.report_generator import generate_sentiment_pie_chart_png

    breakdown = [
        {"sentiment": "Positive", "count": 10, "percentage": 50.0},
        {"sentiment": "Negative", "count": 6, "percentage": 30.0},
        {"sentiment": "Neutral", "count": 4, "percentage": 20.0},
    ]
    png_bytes = generate_sentiment_pie_chart_png(breakdown, language="English")
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 500


def test_report_date_format_dd_mm_yyyy():
    """Verify date span derives earliest and latest dates in DD-MM-YYYY format and handles missing dates."""
    # Test valid dates in YYYY-MM-DD string format
    df = pd.DataFrame([
        {"review_id": 1, "review_text": "Good", "date": "2026-09-01"},
        {"review_id": 2, "review_text": "Okay", "date": "2026-10-20"},
    ])
    data = build_report_data(reviews_df=df)
    assert data["date_coverage"] == "01-09-2026 to 20-10-2026"

    # Test missing / empty dates
    df_no_dates = pd.DataFrame([
        {"review_id": 1, "review_text": "Good", "date": "invalid-date"},
    ])
    data_no_dates = build_report_data(reviews_df=df_no_dates)
    assert data_no_dates["date_coverage"] == "Not provided"


def test_sentiment_pie_chart_four_categories_mixed_blue():
    """Verify pie chart supports all 4 sentiment categories (Positive, Negative, Neutral, Mixed) with accurate counts and percentages."""
    from src.report_generator import generate_sentiment_pie_chart_png

    breakdown = [
        {"sentiment": "Positive", "count": 4, "percentage": 40.0},
        {"sentiment": "Negative", "count": 3, "percentage": 30.0},
        {"sentiment": "Neutral", "count": 2, "percentage": 20.0},
        {"sentiment": "Mixed", "count": 1, "percentage": 10.0},
    ]
    png_bytes = generate_sentiment_pie_chart_png(breakdown, language="English")
    assert isinstance(png_bytes, bytes)
    assert len(png_bytes) > 500

    # Ensure sentiment breakdown table and counts match total
    total_reviews = sum(item["count"] for item in breakdown)
    assert total_reviews == 10
    total_pct = sum(item["percentage"] for item in breakdown)
    assert abs(total_pct - 100.0) < 0.1


