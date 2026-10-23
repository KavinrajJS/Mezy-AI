"""
tests/test_review_analysis.py
-----------------------------
Unit tests for Gemini AI Review Analysis (Milestone 3).

Tests verify:
  1. Secure API key configuration & client initialization.
  2. Grounded prompt generation with review texts, IDs, ratings, and questions.
  3. Safe JSON parsing with markdown codeblock stripping and error recovery.
  4. Exact numerical calculations for sentiment counts, percentages, and topics.
  5. Customer likes, common complaints, and actionable recommendations extraction.
  6. Question answering grounded in review evidence.
  7. Graceful error handling for missing keys, malformed responses, and network issues.
"""

import json
import sys
from pathlib import Path
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.gemini_service import (
    get_gemini_client,
    generate_structured_content,
    verify_api_connectivity,
    GeminiServiceError,
)
from src.review_analysis import (
    build_analysis_prompt,
    parse_and_validate_ai_response,
    compute_numerical_statistics,
    analyze_reviews_with_gemini,
)


# ── 1. Secure API Configuration Tests ──────────────────────────────────────

def test_gemini_client_initialization_with_valid_key():
    """Verify Gemini client initializes cleanly when API key is configured."""
    client = get_gemini_client()
    assert client is not None


def test_missing_api_key_raises_gemini_service_error(monkeypatch):
    """Verify informative GeminiServiceError is raised if key is missing."""
    import config.settings
    monkeypatch.setattr(config.settings, "GEMINI_API_KEY", "")
    with pytest.raises(GeminiServiceError) as exc_info:
        get_gemini_client()
    assert "not configured" in str(exc_info.value).lower()


# ── 2. Grounded Prompt Generation Tests ───────────────────────────────────

def test_build_analysis_prompt_structure():
    """Verify prompt formatting, review citations, and question inclusion."""
    df = pd.DataFrame({
        "review_id": [1, 2],
        "review_text": [
            "Super delicious biryani and cold curd chutney.",
            "Delivery was 45 minutes late, packaging was ruined.",
        ],
        "rating": [5, 1],
    })
    prompt = build_analysis_prompt(df, user_question="Why was delivery late?")
    assert "Review #1" in prompt
    assert "Super delicious biryani" in prompt
    assert "Rating: 5/5" in prompt
    assert "Why was delivery late?" in prompt
    assert "STRICT GROUNDING" in prompt or "valid JSON" in prompt


# ── 3. AI Response Parsing & Validation Tests ─────────────────────────────

def test_parse_json_with_markdown_fences():
    """Verify JSON wrapped in ```json ``` codeblock is parsed cleanly."""
    raw = """```json
    {
      "executive_summary": "Great food, slow delivery.",
      "customer_likes": [{"topic": "Food", "summary": "Delicious", "evidence_quote": "Super delicious"}],
      "common_complaints": [{"topic": "Delivery", "summary": "Late", "evidence_quote": "45 minutes late"}]
    }
    ```"""
    data = parse_and_validate_ai_response(raw)
    assert data["executive_summary"] == "Great food, slow delivery."
    assert len(data["customer_likes"]) == 1
    assert data["customer_likes"][0]["evidence_quote"] == "Super delicious"


def test_parse_malformed_json_raises_clean_error():
    """Malformed non-JSON string raises GeminiServiceError without tracebacks."""
    with pytest.raises(GeminiServiceError) as exc_info:
        parse_and_validate_ai_response("This is not JSON at all.")
    assert "could not parse" in str(exc_info.value).lower() or "malformed" in str(exc_info.value).lower()


# ── 4. Numerical Accuracy Calculation Tests ────────────────────────────────

def test_compute_numerical_statistics():
    """Verify exact mathematical percentages calculated in Python."""
    df = pd.DataFrame({
        "review_id": [1, 2, 3, 4],
        "review_text": ["Good", "Great", "Bad", "Okay"],
        "rating": [4, 5, 1, 3],
    })
    ai_mock_data = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Positive", "topics": ["Food Quality"]},
            {"review_id": 2, "sentiment": "Positive", "topics": ["Food Quality", "Taste"]},
            {"review_id": 3, "sentiment": "Negative", "topics": ["Waiting Time"]},
            {"review_id": 4, "sentiment": "Neutral", "topics": ["Price & Value"]},
        ]
    }
    stats = compute_numerical_statistics(df, ai_mock_data)

    assert stats["total_reviews"] == 4
    assert stats["average_rating"] == 3.25
    sent_metrics = stats["sentiment_metrics"]
    assert sent_metrics["positive"] == 2
    assert sent_metrics["negative"] == 1
    assert sent_metrics["neutral"] == 1
    assert sent_metrics["positive_pct"] == 50.0
    assert sent_metrics["negative_pct"] == 25.0
    assert sent_metrics["neutral_pct"] == 25.0
    assert sent_metrics["primary_sentiment"] == "Positive"
    assert stats["topic_counts"]["Food Quality"] == 2


# ── 5. Live Gemini API End-to-End Test ────────────────────────────────────

def test_live_gemini_api_connectivity():
    """Verify real connectivity to the Gemini API."""
    ok, msg = verify_api_connectivity()
    assert ok is True, f"Gemini connection failed: {msg}"


def test_live_analysis_on_sample_reviews():
    """Verify live Gemini analysis pipeline executes and returns structured data."""
    df = pd.DataFrame({
        "review_id": [1, 2],
        "review_text": [
            "The filter coffee is the best in town! Soft dosas and fresh chutneys.",
            "AC was not cooling and staff were inattentive. Left with a headache.",
        ],
        "rating": [5, 2],
    })
    results = analyze_reviews_with_gemini(df, user_question="What should we fix first?")

    assert results["summary"]["status"] == "completed"
    assert results["summary"]["total_reviews"] == 2
    assert len(results["summary"]["executive_summary"]) > 10
    assert "positive_pct" in results["sentiment_stats"]
    assert len(results["customer_likes"]) > 0
    assert len(results["common_complaints"]) > 0
    assert len(results["actionable_recommendations"]) > 0
    assert results["question_response"]["answer"] != ""
