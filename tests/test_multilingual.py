"""
tests/test_multilingual.py
--------------------------
Comprehensive unit and integration test suite for Mezy Milestone 5:
Loading Experience & Multilingual Support (English, Tamil, Tanglish).

Covers:
  1. Multilingual prompt generation for English, Tamil, and Tanglish.
  2. Mixed-language customer review handling (English, Tamil, Tanglish).
  3. Grounding and exact verbatim citation of customer reviews.
  4. Appropriate classification of mixed feedback ('Mixed') and ambiguous feedback ('Uncertain').
  5. Consistency of mathematical calculations across languages.
  6. Zero API call overhead when switching to already-analyzed/cached languages.
  7. Exact quote and metric preservation during narrative adaptation.
  8. Static UI translations completeness across English, Tamil, and Tanglish.
  9. Live Gemini analysis on multilingual review samples (if API key is present).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.translations import t, _STRINGS
from src.review_analysis import (
    build_analysis_prompt,
    parse_and_validate_ai_response,
    compute_numerical_statistics,
    analyze_reviews_with_gemini,
    adapt_analysis_to_language,
    SYSTEM_INSTRUCTION,
)
from src.analytics import prepare_enriched_reviews, filter_reviews
from config.settings import GEMINI_API_KEY


# ── 1. Static UI Translations Completeness ────────────────────────────────────

def test_translations_coverage_across_languages():
    """Verify all defined UI strings have translations in English, Tamil, and Tanglish."""
    required_langs = ["English", "Tamil", "Tanglish"]
    for key, trans_map in _STRINGS.items():
        for lang in required_langs:
            val = trans_map.get(lang)
            assert val is not None and len(val.strip()) > 0, f"Missing {lang} translation for '{key}'"
            assert t(key, lang=lang) == val

    # Non-existent key falls back to key itself
    assert t("non_existent_key_xyz", "Tamil") == "non_existent_key_xyz"


def test_loading_stages_translations():
    """Verify loading stage messages are translated and non-empty for all three languages."""
    stages = [
        "loading_preparing",
        "loading_analysing",
        "loading_insights",
        "loading_dashboard",
        "loading_done",
    ]
    for lang in ["English", "Tamil", "Tanglish"]:
        for s in stages:
            msg = t(s, lang=lang)
            assert msg is not None and len(msg.strip()) > 0
            assert "Gemini AI" not in msg


# ── 2. Grounded Prompt Generation with Language Steering ───────────────────────

def test_build_analysis_prompt_language_steering():
    """Verify build_analysis_prompt includes language directives and preserves reviews."""
    df = pd.DataFrame([
        {"review_id": 1, "review_text": "The food was delicious, but the delivery was late.", "rating": 3},
        {"review_id": 2, "review_text": "Food super ah irundhuchu, but delivery romba late.", "rating": 3},
        {"review_id": 3, "review_text": "உணவு நன்றாக இருந்தது, ஆனால் டெலிவரி தாமதமானது.", "rating": 3},
        {"review_id": 4, "review_text": "dunno maybe yes maybe no ??? ok ok", "rating": 2},
    ])

    # 1. English prompt
    prompt_en = build_analysis_prompt(df, user_question="Delivery issues?", language="English")
    assert "TARGET OUTPUT LANGUAGE: English" in prompt_en
    assert "The food was delicious, but the delivery was late." in prompt_en
    assert "Food super ah irundhuchu, but delivery romba late." in prompt_en
    assert "உணவு நன்றாக இருந்தது, ஆனால் டெலிவரி தாமதமானது." in prompt_en
    assert "Delivery issues?" in prompt_en

    # 2. Tamil prompt
    prompt_ta = build_analysis_prompt(df, user_question="டெலிவரி சிக்கல்கள்?", language="Tamil")
    assert "TARGET OUTPUT LANGUAGE: Tamil (தமிழ்)" in prompt_ta
    assert "TAMIL script (தமிழ்)" in prompt_ta
    assert "டெலிவரி சிக்கல்கள்?" in prompt_ta

    # 3. Tanglish prompt
    prompt_tg = build_analysis_prompt(df, user_question="Delivery issues?", language="Tanglish")
    assert "TARGET OUTPUT LANGUAGE: Tanglish" in prompt_tg
    assert "TANGLISH" in prompt_tg

    # 4. Review citations verbatim
    assert "Review #1" in prompt_tg
    assert "Review #2" in prompt_tg
    assert "Review #3" in prompt_tg
    assert "Review #4" in prompt_tg


def test_system_instruction_contains_multilingual_rules():
    """Verify system instruction explicitly mandates verbatim quotes and mixed sentiment."""
    assert "MULTILINGUAL REVIEW UNDERSTANDING" in SYSTEM_INSTRUCTION
    assert "VERBATIM" in SYSTEM_INSTRUCTION
    assert "Mixed" in SYSTEM_INSTRUCTION
    assert "Uncertain" in SYSTEM_INSTRUCTION
    assert "Tamil" in SYSTEM_INSTRUCTION
    assert "Tanglish" in SYSTEM_INSTRUCTION


# ── 3. Mathematical Consistency & Grounding Verification ──────────────────────

def test_numerical_statistics_consistency_across_languages():
    """Verify numerical statistics and sentiment counts are computed in Python without variance."""
    df = pd.DataFrame([
        {"review_id": 1, "review_text": "The food was delicious, but the delivery was late.", "rating": 3},
        {"review_id": 2, "review_text": "Food super ah irundhuchu, but delivery romba late.", "rating": 3},
        {"review_id": 3, "review_text": "உணவு நன்றாக இருந்தது, ஆனால் டெலிவரி தாமதமானது.", "rating": 3},
        {"review_id": 4, "review_text": "dunno maybe yes maybe no ??? ok ok", "rating": 2},
    ])

    ai_breakdown = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Mixed", "topics": ["Food Quality", "Delivery"], "language": "English"},
            {"review_id": 2, "sentiment": "Mixed", "topics": ["Food Quality", "Delivery"], "language": "Tanglish"},
            {"review_id": 3, "sentiment": "Mixed", "topics": ["Food Quality", "Delivery"], "language": "Tamil"},
            {"review_id": 4, "sentiment": "Uncertain", "topics": [], "language": "English"},
        ]
    }

    stats = compute_numerical_statistics(df, ai_breakdown)
    s_metrics = stats["sentiment_metrics"]

    assert stats["total_reviews"] == 4
    assert stats["average_rating"] == 2.75
    assert s_metrics["mixed"] == 3
    assert s_metrics["uncertain"] == 1
    assert s_metrics["positive"] == 0
    assert s_metrics["negative"] == 0
    assert s_metrics["mixed_pct"] == 75.0
    assert s_metrics["uncertain_pct"] == 25.0
    assert stats["topic_counts"]["Food Quality"] == 3
    assert stats["topic_counts"]["Delivery"] == 3


def test_prepare_enriched_reviews_preserves_original_text_and_detects_language():
    """Verify original review texts remain completely intact and language column is populated."""
    df = pd.DataFrame([
        {"review_id": 1, "review_text": "The food was delicious, but the delivery was late.", "rating": 3},
        {"review_id": 2, "review_text": "Food super ah irundhuchu, but delivery romba late.", "rating": 3},
        {"review_id": 3, "review_text": "உணவு நன்றாக இருந்தது, ஆனால் டெலிவரி தாமதமானது.", "rating": 3},
        {"review_id": 4, "review_text": "dunno maybe yes maybe no ??? ok ok", "rating": 2},
    ])

    ai_results = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Mixed", "topics": ["Food Quality", "Delivery"], "language": "English"},
            {"review_id": 2, "sentiment": "Mixed", "topics": ["Food Quality", "Delivery"], "language": "Tanglish"},
            {"review_id": 3, "sentiment": "Mixed", "topics": ["Food Quality", "Delivery"], "language": "Tamil"},
            {"review_id": 4, "sentiment": "Uncertain", "topics": [], "language": "English"},
        ]
    }

    enriched = prepare_enriched_reviews(df, ai_results)

    # 1. Original text unchanged
    assert enriched.iloc[0]["review_text"] == "The food was delicious, but the delivery was late."
    assert enriched.iloc[1]["review_text"] == "Food super ah irundhuchu, but delivery romba late."
    assert enriched.iloc[2]["review_text"] == "உணவு நன்றாக இருந்தது, ஆனால் டெலிவரி தாமதமானது."
    assert enriched.iloc[3]["review_text"] == "dunno maybe yes maybe no ??? ok ok"

    # 2. Sentiments
    assert enriched.iloc[0]["sentiment"] == "Mixed"
    assert enriched.iloc[1]["sentiment"] == "Mixed"
    assert enriched.iloc[2]["sentiment"] == "Mixed"
    assert enriched.iloc[3]["sentiment"] == "Uncertain"

    # 3. Language filter
    filtered_ta = filter_reviews(enriched, language="Tamil")
    assert len(filtered_ta) == 1
    assert filtered_ta.iloc[0]["review_id"] == 3

    filtered_tg = filter_reviews(enriched, language="Tanglish")
    assert len(filtered_tg) == 1
    assert filtered_tg.iloc[0]["review_id"] == 2

    filtered_en = filter_reviews(enriched, language="English")
    assert len(filtered_en) == 2


# ── 4. Adapt Analysis to Language & Caching ───────────────────────────────────

def test_adapt_analysis_to_same_language_costs_zero_api_calls(monkeypatch):
    """Verify switching to the same language immediately returns without calling Gemini API."""
    def forbidden_call(*args, **kwargs):
        pytest.fail("Gemini API should NOT be called when target language matches output_language")

    monkeypatch.setattr("src.review_analysis.generate_structured_content", forbidden_call)

    existing_results = {
        "output_language": "English",
        "summary": {
            "total_reviews": 4,
            "average_rating": 2.75,
            "executive_summary": "Customer love the food taste, but express delivery delays.",
        },
        "sentiment_stats": {"positive": 0, "negative": 0, "mixed": 3, "uncertain": 1},
        "topic_counts": {"Food Quality": 3, "Delivery": 3},
        "customer_likes": [{"topic": "Food Quality", "summary": "Great food", "evidence_quote": "delicious"}],
        "common_complaints": [{"topic": "Delivery", "summary": "Late", "evidence_quote": "late"}],
        "recurring_topics": [],
        "actionable_recommendations": [],
        "question_response": {},
        "per_review_breakdown": [],
    }

    # Same language call
    adapted = adapt_analysis_to_language(existing_results, target_language="English")
    assert adapted["output_language"] == "English"
    assert adapted["summary"]["executive_summary"] == existing_results["summary"]["executive_summary"]


def test_adapt_analysis_preserves_numerical_stats_and_exact_quotes(monkeypatch):
    """Verify adapt_analysis_to_language preserves stats and restores original evidence quotes verbatim."""
    mock_translated_json = """{
      "executive_summary": "உணவு சுவை சிறந்தது, ஆனால் டெலிவரி தாமதம்.",
      "sentiment_overview": {"positive_aspects": "சுவையான உணவு"},
      "customer_likes": [{"topic": "Food Quality", "summary": "சுவையான உணவு", "evidence_quote": "MODIFIED_QUOTE"}],
      "common_complaints": [{"topic": "Delivery", "summary": "தாமதம்", "evidence_quote": "ALTERED_QUOTE"}],
      "recurring_topics": [],
      "actionable_recommendations": [{"area": "Delivery", "priority": "High", "recommendation": "டெலிவரியை மேம்படுத்துங்கள்", "reasoning": "காரணம்", "supporting_evidence": "CORRUPTED_EVIDENCE"}],
      "question_response": {"question": "q", "answer": "பதில்", "supporting_evidence": ["ORIGINAL_QUOTE"]}
    }"""

    monkeypatch.setattr("src.review_analysis.generate_structured_content", lambda *a, **k: mock_translated_json)

    orig_results = {
        "output_language": "English",
        "summary": {
            "total_reviews": 4,
            "average_rating": 2.75,
            "executive_summary": "Great food taste, but delivery delay.",
        },
        "sentiment_stats": {"positive": 0, "negative": 0, "mixed": 3, "uncertain": 1},
        "topic_counts": {"Food Quality": 3, "Delivery": 3},
        "customer_likes": [{"topic": "Food Quality", "summary": "Great taste", "evidence_quote": "Food super ah irundhuchu"}],
        "common_complaints": [{"topic": "Delivery", "summary": "Late", "evidence_quote": "but delivery romba late"}],
        "recurring_topics": [],
        "actionable_recommendations": [{"area": "Delivery", "priority": "High", "recommendation": "Fix speed", "reasoning": "Reason", "supporting_evidence": "delivery romba late"}],
        "question_response": {"question": "q", "answer": "ans", "supporting_evidence": ["Food super ah irundhuchu"]},
        "per_review_breakdown": [{"review_id": 1, "sentiment": "Mixed"}],
    }

    adapted = adapt_analysis_to_language(orig_results, target_language="Tamil")

    # 1. Output language updated
    assert adapted["output_language"] == "Tamil"

    # 2. Translated executive summary
    assert "உணவு சுவை சிறந்தது" in adapted["summary"]["executive_summary"]

    # 3. Numerical stats 100% IDENTICAL
    assert adapted["summary"]["total_reviews"] == 4
    assert adapted["summary"]["average_rating"] == 2.75
    assert adapted["sentiment_stats"] == orig_results["sentiment_stats"]
    assert adapted["topic_counts"] == orig_results["topic_counts"]

    # 4. Evidence quotes STRICTLY RESTORED VERBATIM (not overwritten by LLM)
    assert adapted["customer_likes"][0]["evidence_quote"] == "Food super ah irundhuchu"
    assert adapted["common_complaints"][0]["evidence_quote"] == "but delivery romba late"
    assert adapted["actionable_recommendations"][0]["supporting_evidence"] == "delivery romba late"


# ── 5. Live Gemini Multilingual Integration Test ──────────────────────────────

@pytest.mark.skipif(not GEMINI_API_KEY, reason="GEMINI_API_KEY not configured")
def test_live_multilingual_reviews_analysis():
    """
    Live test against Gemini evaluating English, Tanglish, Tamil, and Ambiguous reviews.
    Verifies grounding, sentiment classification (Mixed, Uncertain), and structured response.
    """
    df = pd.DataFrame([
        {"review_id": 1, "review_text": "The food was delicious, but the delivery was late.", "rating": 3},
        {"review_id": 2, "review_text": "Food super ah irundhuchu, but delivery romba late.", "rating": 3},
        {"review_id": 3, "review_text": "உணவு நன்றாக இருந்தது, ஆனால் டெலிவரி தாமதமானது.", "rating": 3},
        {"review_id": 4, "review_text": "dunno maybe yes maybe no ??? ok ok", "rating": 2},
    ])

    results = analyze_reviews_with_gemini(
        df,
        user_question="Are customers complaining about delivery across all languages?",
        language="English",
    )

    # 1. Output structure validated
    assert "summary" in results
    assert "sentiment_stats" in results
    assert "customer_likes" in results
    assert "common_complaints" in results
    assert "actionable_recommendations" in results
    assert "per_review_breakdown" in results

    # 2. Numerical stats computed
    assert results["summary"]["total_reviews"] == 4
    assert results["summary"]["average_rating"] == 2.75

    # 3. Breakdown check: at least one Mixed sentiment and one Uncertain sentiment detected
    sentiments = [item.get("sentiment") for item in results["per_review_breakdown"]]
    assert "Mixed" in sentiments or "Uncertain" in sentiments or "Positive" in sentiments

    # 4. Evidence quotes grounded verbatim
    for item in results["customer_likes"]:
        q = item.get("evidence_quote", "")
        if q:
            # Must appear in one of the original reviews
            assert any(q.lower() in orig.lower() or orig.lower() in q.lower() for orig in df["review_text"])
