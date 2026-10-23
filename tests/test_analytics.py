"""
tests/test_analytics.py
-----------------------
Unit tests for Milestone 4 analytics, filtering, and chart generation.

Tests verify:
  1. Correct sentiment counts and percentages calculated in Python.
  2. Multi-topic counting logic where each topic increments independently.
  3. Combined filters (sentiment, topic, rating, date range, search text).
  4. Empty filter results handled gracefully without exceptions.
  5. Missing ratings and missing dates handled gracefully without failure.
  6. Filter resetting and ensuring the original dataset is never mutated.
  7. Confirming that analytics operations do NOT trigger Gemini API calls.
"""

import sys
from pathlib import Path
from datetime import date, datetime
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.analytics import (
    prepare_enriched_reviews,
    filter_reviews,
    compute_sentiment_distribution,
    compute_topic_distribution,
    compute_topic_sentiment_breakdown,
    compute_timeline_trends,
    compute_average_customer_rating,
    create_sentiment_donut_chart,
    create_topics_bar_chart,
    create_topic_sentiment_stacked_chart,
    create_review_activity_chart,
    create_trend_line_chart,
)


@pytest.fixture
def sample_reviews_data():
    """Create sample reviews DataFrame and AI breakdown results for testing."""
    df = pd.DataFrame({
        "review_id": [1, 2, 3, 4, 5],
        "review_text": [
            "The biryani was delicious, best food quality in town!",
            "Service was terribly slow and delivery was late.",
            "Average experience. Price was fair, coffee was okay.",
            "Rude staff and very dirty tables. Would not recommend.",
            "Loved the crispy dosas and clean ambiance! Friendly staff.",
        ],
        "rating": [5.0, 1.0, 3.0, 1.0, 5.0],
        "review_date": pd.to_datetime([
            "2024-01-10",
            "2024-01-12",
            "2024-01-15",
            "2024-01-18",
            "2024-01-20",
        ]),
        "source": ["Google", "Swiggy", "Zomato", "Google", "Direct"],
    })

    ai_results = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Positive", "topics": ["Food Quality", "Taste"]},
            {"review_id": 2, "sentiment": "Negative", "topics": ["Waiting Time", "Delivery"]},
            {"review_id": 3, "sentiment": "Neutral", "topics": ["Price & Value", "Taste"]},
            {"review_id": 4, "sentiment": "Negative", "topics": ["Staff Behaviour", "Cleanliness"]},
            {"review_id": 5, "sentiment": "Positive", "topics": ["Food Quality", "Cleanliness", "Staff Behaviour"]},
        ]
    }
    return df, ai_results


# ── 1. Data Enrichment & Immutability Tests ─────────────────────────────────

def test_prepare_enriched_reviews(sample_reviews_data):
    """Verify enrichment assigns sentiments and topics properly without mutating original df."""
    df, ai_results = sample_reviews_data
    original_copy = df.copy(deep=True)

    enriched = prepare_enriched_reviews(df, ai_results)

    assert len(enriched) == 5
    assert "sentiment" in enriched.columns
    assert "topics" in enriched.columns

    # Check mapping
    row1 = enriched.loc[enriched["review_id"] == 1].iloc[0]
    assert row1["sentiment"] == "Positive"
    assert "Food Quality" in row1["topics"]
    assert "Taste" in row1["topics"]

    # Original DataFrame must remain untouched
    pd.testing.assert_frame_equal(df, original_copy)


# ── 2. Sentiment Counts and Percentages Tests ───────────────────────────────

def test_compute_sentiment_distribution(sample_reviews_data):
    """Verify exact sentiment counts and percentages calculated in Python."""
    df, ai_results = sample_reviews_data
    enriched = prepare_enriched_reviews(df, ai_results)

    stats = compute_sentiment_distribution(enriched)
    counts = stats["counts"]
    pcts = stats["percentages"]

    assert counts["Positive"] == 2
    assert counts["Negative"] == 2
    assert counts["Neutral"] == 1
    assert counts["Mixed"] == 0
    assert stats["total"] == 5

    assert pcts["Positive"] == 40.0
    assert pcts["Negative"] == 40.0
    assert pcts["Neutral"] == 20.0
    assert pcts["Mixed"] == 0.0


# ── 3. Multi-Topic Distribution Tests ──────────────────────────────────────

def test_multi_topic_distribution(sample_reviews_data):
    """
    Verify reviews mentioning multiple topics increment each topic independently
    without forcing topic sums to equal total reviews.
    """
    df, ai_results = sample_reviews_data
    enriched = prepare_enriched_reviews(df, ai_results)

    topic_counts = compute_topic_distribution(enriched)
    topic_map = {item["topic"]: item["count"] for item in topic_counts}

    # "Food Quality" is in review 1 and review 5 -> count 2
    assert topic_map["Food Quality"] == 2
    # "Cleanliness" is in review 4 and review 5 -> count 2
    assert topic_map["Cleanliness"] == 2
    # "Staff Behaviour" is in review 4 and review 5 -> count 2
    assert topic_map["Staff Behaviour"] == 2
    # "Taste" is in review 1 and review 3 -> count 2
    assert topic_map["Taste"] == 2
    # "Waiting Time" is in review 2 -> count 1
    assert topic_map["Waiting Time"] == 1

    # Sum of topic mentions (11) exceeds total review count (5) — expected for multi-label data
    total_mentions = sum(item["count"] for item in topic_counts)
    assert total_mentions == 11
    assert len(enriched) == 5


# ── 4. Combined Filtering & Search Tests ────────────────────────────────────

def test_combined_filters(sample_reviews_data):
    """Verify filters work together accurately (AND combination)."""
    df, ai_results = sample_reviews_data
    enriched = prepare_enriched_reviews(df, ai_results)

    # Filter 1: Positive reviews only
    pos_filtered = filter_reviews(enriched, sentiment="Positive")
    assert len(pos_filtered) == 2

    # Filter 2: Positive + Topic "Food Quality"
    fq_pos = filter_reviews(enriched, sentiment="Positive", topic="Food Quality")
    assert len(fq_pos) == 2

    # Filter 3: Positive + Topic "Cleanliness"
    clean_pos = filter_reviews(enriched, sentiment="Positive", topic="Cleanliness")
    assert len(clean_pos) == 1
    assert clean_pos.iloc[0]["review_id"] == 5

    # Filter 4: Text search inside filtered results
    search_biryani = filter_reviews(enriched, search_query="biryani")
    assert len(search_biryani) == 1
    assert search_biryani.iloc[0]["review_id"] == 1

    # Filter 5: Rating filter (Rating = 1.0)
    rating_1 = filter_reviews(enriched, rating="1")
    assert len(rating_1) == 2
    assert set(rating_1["review_id"]) == {2, 4}

    # Filter 6: Date range filter
    date_filtered = filter_reviews(
        enriched,
        start_date="2024-01-11",
        end_date="2024-01-16",
    )
    assert len(date_filtered) == 2
    assert set(date_filtered["review_id"]) == {2, 3}


# ── 5. Empty Filter Results & Resetting Tests ───────────────────────────────

def test_empty_filter_results(sample_reviews_data):
    """Verify filtering that matches 0 rows returns an empty DataFrame cleanly."""
    df, ai_results = sample_reviews_data
    enriched = prepare_enriched_reviews(df, ai_results)

    # Search query that does not exist in dataset
    no_matches = filter_reviews(enriched, search_query="nonexistent_keyword_xyz")
    assert len(no_matches) == 0
    assert isinstance(no_matches, pd.DataFrame)


def test_reset_filters_restores_complete_dataset(sample_reviews_data):
    """Verify passing default 'All' filters returns the entire dataset."""
    df, ai_results = sample_reviews_data
    enriched = prepare_enriched_reviews(df, ai_results)

    # Filter first
    filtered = filter_reviews(enriched, sentiment="Negative", rating="1")
    assert len(filtered) == 2

    # Reset (default parameters)
    reset = filter_reviews(
        enriched,
        sentiment="All",
        topic="All",
        rating="All",
        start_date=None,
        end_date=None,
        search_query="",
    )
    assert len(reset) == 5
    pd.testing.assert_frame_equal(reset, enriched)


# ── 6. Missing Dates and Ratings Graceful Handling ──────────────────────────

def test_missing_ratings_and_dates_handling():
    """Verify dataset with missing ratings or dates does not throw errors."""
    df_missing = pd.DataFrame({
        "review_id": [1, 2],
        "review_text": ["Great place!", "Too expensive."],
        "rating": [None, None],
        "review_date": [None, None],
    })
    ai_results = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Positive", "topics": ["Food Quality"]},
            {"review_id": 2, "sentiment": "Negative", "topics": ["Price & Value"]},
        ]
    }

    enriched = prepare_enriched_reviews(df_missing, ai_results)
    assert len(enriched) == 2

    # Filtering on missing dates returns empty if date filter provided
    filtered_date = filter_reviews(enriched, start_date="2024-01-01", end_date="2024-01-31")
    assert len(filtered_date) == 0

    # Filtering on sentiment works perfectly even without ratings or dates
    filtered_pos = filter_reviews(enriched, sentiment="Positive")
    assert len(filtered_pos) == 1

    # Trend computation gracefully returns None when dates are absent
    trend = compute_timeline_trends(enriched)
    assert trend is None

    # Trend chart returns None gracefully
    trend_chart = create_trend_line_chart(enriched)
    assert trend_chart is None


# ── 7. Interactive Chart Builders Non-Throwing Tests ────────────────────────

def test_plotly_charts_build_successfully(sample_reviews_data):
    """Verify all 4 chart builders generate valid Plotly Figure objects."""
    df, ai_results = sample_reviews_data
    enriched = prepare_enriched_reviews(df, ai_results)

    # Sentiment Donut
    fig_sent = create_sentiment_donut_chart(enriched)
    assert fig_sent is not None

    # Most Discussed Topics Bar
    fig_topics = create_topics_bar_chart(enriched)
    assert fig_topics is not None

    # Topic-wise Sentiment Stacked Bar
    fig_topic_sent = create_topic_sentiment_stacked_chart(enriched)
    assert fig_topic_sent is not None

    # Trends Line Chart
    fig_trend = create_trend_line_chart(enriched)
    assert fig_trend is not None


# ── 8. API Isolation Guarantee (No Gemini Calls on Analytics) ───────────────

def test_analytics_never_calls_gemini_api(monkeypatch, sample_reviews_data):
    """Verify that viewing charts and filtering data NEVER triggers Gemini API calls."""
    df, ai_results = sample_reviews_data

    # Mock Gemini client to fail loudly if invoked
    def mock_gemini_call(*args, **kwargs):
        raise AssertionError("Gemini API was called unexpectedly during analytics/filtering!")

    monkeypatch.setattr("src.gemini_service.generate_structured_content", mock_gemini_call)

    # Run complete analytics workflow
    enriched = prepare_enriched_reviews(df, ai_results)
    filtered = filter_reviews(enriched, sentiment="Positive", search_query="biryani")
    stats = compute_sentiment_distribution(filtered)
    topics = compute_topic_distribution(filtered)
    chart1 = create_sentiment_donut_chart(filtered)
    chart2 = create_topics_bar_chart(filtered)

    assert len(filtered) == 1
    assert stats["counts"]["Positive"] == 1
    assert chart1 is not None
    assert chart2 is not None


# ── 9. Topic Summary Metrics & AI Evidence Tests ────────────────────────────

def test_topic_summary_metrics_and_ai_evidence(sample_reviews_data):
    """Verify topic-specific metric extraction and AI evidence mapping."""
    from src.analytics import get_topic_summary_metrics, get_topic_ai_evidence

    df, ai_results = sample_reviews_data
    # Augment ai_results with recurring topics and customer likes for evidence testing
    ai_results["recurring_topics"] = [
        {
            "topic": "Food Quality",
            "sentiment": "Positive",
            "summary": "Customers love the authentic taste and quality.",
            "evidence_quote": "The biryani was delicious, best food quality in town!",
        }
    ]
    ai_results["customer_likes"] = [
        {
            "topic": "Food Quality",
            "summary": "Praise for biryani and crispy dosas.",
            "evidence_quote": "Loved the crispy dosas and clean ambiance!",
        }
    ]

    enriched = prepare_enriched_reviews(df, ai_results)

    # Food Quality metrics (reviews 1 and 5)
    fq_metrics = get_topic_summary_metrics(enriched, "Food Quality")
    assert fq_metrics["total_reviews"] == 2
    assert fq_metrics["sentiment_counts"]["Positive"] == 2
    assert fq_metrics["sentiment_counts"]["Negative"] == 0
    assert fq_metrics["sentiment_pcts"]["Positive"] == 100.0
    assert fq_metrics["avg_rating"] == 5.0

    # Cleanliness metrics (reviews 4 and 5)
    clean_metrics = get_topic_summary_metrics(enriched, "Cleanliness")
    assert clean_metrics["total_reviews"] == 2
    assert clean_metrics["sentiment_counts"]["Positive"] == 1
    assert clean_metrics["sentiment_counts"]["Negative"] == 1
    assert clean_metrics["avg_rating"] == 3.0

    # All Topics metrics
    all_metrics = get_topic_summary_metrics(enriched, "All Topics")
    assert all_metrics["total_reviews"] == 5

    # AI Evidence matching
    evidence = get_topic_ai_evidence(ai_results, "Food Quality")
    assert len(evidence) == 2
    assert any("biryani was delicious" in ev["evidence_quote"] for ev in evidence)
    assert any("crispy dosas" in ev["evidence_quote"] for ev in evidence)


# ── 10. Language Filtering & Uncertain Sentiment Handling ───────────────────

def test_language_filter_and_uncertain_sentiment():
    """Verify optional language filtering and uncertain sentiment classification."""
    df_lang = pd.DataFrame([
        {"review_id": 1, "review_text": "Super food romba nallarku", "rating": 5, "language": "Tamil"},
        {"review_id": 2, "review_text": "Good taste, nice packaging", "rating": 4, "language": "English"},
        {"review_id": 3, "review_text": "Not sure if I liked it or not", "rating": 3, "language": "English"},
    ])
    ai_results = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Positive", "topics": ["Food Quality"]},
            {"review_id": 2, "sentiment": "Positive", "topics": ["Packaging"]},
            {"review_id": 3, "sentiment": "Uncertain", "topics": []},
        ]
    }

    enriched = prepare_enriched_reviews(df_lang, ai_results)

    # Language filter
    filtered_tamil = filter_reviews(enriched, language="Tamil")
    assert len(filtered_tamil) == 1
    assert filtered_tamil.iloc[0]["review_id"] == 1

    filtered_english = filter_reviews(enriched, language="English")
    assert len(filtered_english) == 2

    # Uncertain sentiment filter
    filtered_uncertain = filter_reviews(enriched, sentiment="Uncertain")
    assert len(filtered_uncertain) == 1
    assert filtered_uncertain.iloc[0]["review_id"] == 3

    # Unassigned topic filter
    filtered_no_topic = filter_reviews(enriched, topic="Unassigned / No Topic")
    assert len(filtered_no_topic) == 1
    assert filtered_no_topic.iloc[0]["review_id"] == 3


# ── 11. Component Render Guards & Session Isolation ─────────────────────────

def test_component_render_guards_without_api_calls(monkeypatch, sample_reviews_data):
    """Verify render_review_table and render_topic_explorer behave gracefully."""
    import streamlit as st
    from components.review_table import render_review_table
    from components.topic_explorer import render_topic_explorer

    # Mock Gemini client to ensure zero API calls occur during rendering
    def fail_if_gemini_called(*args, **kwargs):
        raise AssertionError("Gemini was invoked during component rendering!")

    monkeypatch.setattr("src.gemini_service.generate_structured_content", fail_if_gemini_called)

    # 1. Unanalyzed state: should return gracefully without errors
    st.session_state.clear()
    st.session_state["analysis_done"] = False
    render_review_table()
    render_topic_explorer()

    # 2. Analyzed state: should render components using stored data without calling Gemini
    df, ai_results = sample_reviews_data
    st.session_state["analysis_done"] = True
    st.session_state["reviews_df"] = df
    st.session_state["analysis_results"] = ai_results
    st.session_state["review_filter_version"] = 0
    st.session_state["selected_topic_in_explorer"] = "All Topics"

    render_review_table()
    render_topic_explorer()


# ── 12. Stale Data Invalidation & Two Datasets Verification ──────────────────

def test_two_different_datasets_produce_independent_analytics():
    """Verify that switching or analyzing two different datasets never leaks stale data."""
    # Dataset 1: Café reviews
    df1 = pd.DataFrame({
        "review_id": [1, 2],
        "review_text": ["Great espresso and croissant", "Cold coffee was sour"],
        "rating": [5.0, 2.0],
        "review_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
        "source": ["Google", "Google"],
    })
    ai1 = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Positive", "topics": ["Food Quality"]},
            {"review_id": 2, "sentiment": "Negative", "topics": ["Taste"]},
        ]
    }

    # Dataset 2: Pizza place reviews
    df2 = pd.DataFrame({
        "review_id": [1, 2, 3],
        "review_text": ["Pizza was burned", "Delivery took 2 hours", "Free garlic bread was nice"],
        "rating": [1.0, 1.0, 4.0],
        "review_date": pd.to_datetime(["2024-02-01", "2024-02-02", "2024-02-03"]),
        "source": ["Swiggy", "Swiggy", "Swiggy"],
    })
    ai2 = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Negative", "topics": ["Food Quality"]},
            {"review_id": 2, "sentiment": "Negative", "topics": ["Delivery", "Waiting Time"]},
            {"review_id": 3, "sentiment": "Positive", "topics": ["Food Quality"]},
        ]
    }

    enriched1 = prepare_enriched_reviews(df1, ai1)
    enriched2 = prepare_enriched_reviews(df2, ai2)

    assert len(enriched1) == 2
    assert len(enriched2) == 3

    stats1 = compute_sentiment_distribution(enriched1)
    stats2 = compute_sentiment_distribution(enriched2)

    # Dataset 1 has 1 Pos, 1 Neg; Dataset 2 has 1 Pos, 2 Neg
    assert stats1["counts"]["Positive"] == 1
    assert stats1["counts"]["Negative"] == 1
    assert stats2["counts"]["Positive"] == 1
    assert stats2["counts"]["Negative"] == 2

    topics1 = {t["topic"]: t["count"] for t in compute_topic_distribution(enriched1)}
    topics2 = {t["topic"]: t["count"] for t in compute_topic_distribution(enriched2)}

    assert "Delivery" not in topics1
    assert topics2["Delivery"] == 1


# ── 13. Zero-Matches Keyword Filter Verification ────────────────────────────

def test_zero_matches_keyword_filter_and_empty_charts(sample_reviews_data):
    """Verify that a keyword matching zero reviews returns empty DataFrame and all charts show clean empty states."""
    df, ai_results = sample_reviews_data
    enriched = prepare_enriched_reviews(df, ai_results)

    # Keyword matching 0 reviews
    zero_df = filter_reviews(enriched, search_query="nonexistent_xyz_biryani_never_exists")
    assert len(zero_df) == 0

    # Sentiment distribution must be 0
    stats = compute_sentiment_distribution(zero_df)
    assert stats["total"] == 0
    assert stats["counts"]["Positive"] == 0
    assert stats["counts"]["Negative"] == 0

    # Donut chart shows clean empty annotation without error
    fig_sent = create_sentiment_donut_chart(zero_df)
    assert len(fig_sent.layout.annotations) > 0

    # Topics bar chart shows clean empty annotation without error
    fig_topics = create_topics_bar_chart(zero_df)
    assert len(fig_topics.layout.annotations) > 0

    # Stacked bar chart shows clean empty annotation without error
    fig_stacked = create_topic_sentiment_stacked_chart(zero_df)
    assert len(fig_stacked.layout.annotations) > 0

    # Trends chart returns None
    fig_trend = create_trend_line_chart(zero_df)
    assert fig_trend is None


# ── 14. Horizontal Stacked Bar Chart Properties ─────────────────────────────

def test_horizontal_stacked_bar_chart_structure(sample_reviews_data):
    """Verify topic-wise sentiment comparison is a horizontal stacked bar with top legend."""
    df, ai_results = sample_reviews_data
    enriched = prepare_enriched_reviews(df, ai_results)

    fig = create_topic_sentiment_stacked_chart(enriched, max_topics=6)

    # Verify horizontal orientation
    for trace in fig.data:
        assert trace.orientation == "h"

    # Verify stacked layout
    assert fig.layout.barmode == "stack"

    # Verify legend is placed at the top above the chart
    assert fig.layout.legend.yanchor == "bottom"
    assert fig.layout.legend.y >= 1.0


# ── 15. Topic Normalization & Fallback Inference ────────────────────────────

def test_topic_normalization_and_fallback_inference():
    """Verify topic synonyms map to canonical names and identifiable feedback is associated without guessing."""
    from src.analytics import infer_fallback_topic, normalize_topic_name

    # Synonyms normalization
    assert normalize_topic_name("pricing") == "Price & Value"
    assert normalize_topic_name("billing") == "Price & Value"
    assert normalize_topic_name("service") == "Staff Behaviour"
    assert normalize_topic_name("hygiene") == "Cleanliness"
    assert normalize_topic_name("washroom") == "Cleanliness"
    assert normalize_topic_name("ac") == "Ambiance & Facilities"

    # Identifiable feedback inference
    assert infer_fallback_topic("Waiter gave me incorrect change at billing") == "Price & Value"
    assert infer_fallback_topic("Washroom signage was missing and toilet was dirty") == "Cleanliness"
    assert infer_fallback_topic("AC was broken and no parking available") == "Ambiance & Facilities"
    assert infer_fallback_topic("Delivery guy was rude and late") == "Delivery"

    # Generic feedback must NOT be forced into an artificial topic
    assert infer_fallback_topic("Average experience, nothing special") is None
    assert infer_fallback_topic("Good overall") is None
    assert infer_fallback_topic("Will think about coming back") is None


# ── 16. Date Formatting DD/MM/YYYY ──────────────────────────────────────────

def test_date_formatting_dd_mm_yyyy():
    """Verify dates format in DD/MM/YYYY order without reversing range or affecting date values."""
    dt = pd.to_datetime("2026-09-01")
    formatted = dt.strftime("%d/%m/%Y")
    assert formatted == "01/09/2026"

    # Ensure chronological filtering still works correctly
    df = pd.DataFrame({
        "review_id": [1, 2],
        "review_text": ["Old review", "New review"],
        "review_date": pd.to_datetime(["2024-01-05", "2024-02-15"]),
        "sentiment": ["Positive", "Positive"],
        "topics": [["Food Quality"], ["Food Quality"]],
    })
    filtered = filter_reviews(df, start_date="2024-02-01", end_date="2024-02-28")
    assert len(filtered) == 1
    assert filtered.iloc[0]["review_id"] == 2


# ── 17. Simplified Navigation Validation ────────────────────────────────────

def test_simplified_main_navigation_contains_only_three_pages():
    """Verify main navigation menu contains strictly Overview, Review Analysis, and Action Tracker."""
    from components.sidebar import PAGES

    page_ids = [p["id"] for p in PAGES]
    page_labels = [p["label"] for p in PAGES]

    assert len(PAGES) == 3
    assert page_ids == ["overview", "review_analysis", "action_tracker"]
    assert page_labels == ["Overview", "Review Analysis", "Action Tracker"]
    assert "home" not in page_ids
    assert "topic_explorer" not in page_ids


# ── 18. Topic Filter Button State & Consecutive Filters ─────────────────────

def test_topic_filter_button_state_and_consecutive_filters(sample_reviews_data):
    """
    Verify:
      1. Selecting 'Cleanliness' and triggering the quick filter applies cleanly without StreamlitWidgetAlreadyInstantiatedError.
      2. Consecutive topic selection (e.g. 'Food Quality') updates filter correctly.
      3. Resetting filters restores complete dataset without session state errors.
      4. Displayed reviews and analytics correspond to the active topic.
    """
    import streamlit as st
    from components.review_table import render_review_table

    df, ai_results = sample_reviews_data
    st.session_state["analysis_done"] = True
    st.session_state["reviews_df"] = df
    st.session_state["analysis_results"] = ai_results
    st.session_state["review_filter_version"] = 0
    st.session_state["topic_widget_version"] = 0
    st.session_state["applied_topic_filter"] = "All"

    # Initial render
    render_review_table()
    assert st.session_state["applied_topic_filter"] == "All"

    # 1. Select 'Cleanliness' and trigger quick filter callback
    st.session_state["quick_topic_select"] = "Cleanliness"
    # Simulate on_quick_filter_topic callback
    chosen = st.session_state.get("quick_topic_select")
    st.session_state["applied_topic_filter"] = chosen
    st.session_state["topic_widget_version"] = st.session_state.get("topic_widget_version", 0) + 1

    # Render again - must NOT raise StreamlitWidgetAlreadyInstantiatedError
    render_review_table()
    assert st.session_state["applied_topic_filter"] == "Cleanliness"

    # Filtered reviews must strictly include Cleanliness
    enriched = prepare_enriched_reviews(df, ai_results)
    filtered_clean = filter_reviews(enriched, topic="Cleanliness")
    assert len(filtered_clean) == 2
    for _, row in filtered_clean.iterrows():
        assert "Cleanliness" in row["topics"]

    # 2. Select another topic 'Food Quality' subsequently and trigger quick filter
    st.session_state["quick_topic_select"] = "Food Quality"
    chosen_2 = st.session_state.get("quick_topic_select")
    st.session_state["applied_topic_filter"] = chosen_2
    st.session_state["topic_widget_version"] = st.session_state.get("topic_widget_version", 0) + 1

    # Render again - must succeed seamlessly
    render_review_table()
    assert st.session_state["applied_topic_filter"] == "Food Quality"

    filtered_food = filter_reviews(enriched, topic="Food Quality")
    assert len(filtered_food) == 2
    for _, row in filtered_food.iterrows():
        assert "Food Quality" in row["topics"]

    # 3. Reset filters
    st.session_state["review_filter_version"] = st.session_state.get("review_filter_version", 0) + 1
    st.session_state["applied_topic_filter"] = "All"
    st.session_state["topic_widget_version"] = 0

    render_review_table()
    assert st.session_state["applied_topic_filter"] == "All"
    filtered_all = filter_reviews(enriched, topic="All")
    assert len(filtered_all) == len(df)


# ── 19. Topic Sentiment Stacked Chart & Unassigned Review Separation ─────────

def test_topic_wise_sentiment_stacked_chart_excludes_unassigned_reviews():
    """
    Verify:
      1. Operational-topic sentiment breakdown excludes 'Unassigned' and 'General Feedback'.
      2. Unassigned review counts can be tracked and displayed separately.
      3. Horizontal stacked bar chart displays accurate counts, Mezy colors, and clean tooltips.
    """
    df = pd.DataFrame({
        "review_id": [1, 2, 3, 4],
        "review_text": [
            "Spotless restaurant, loved the cleanliness!",
            "Dirty washrooms and sticky tables.",
            "Average experience overall.",
            "Just an okay place.",
        ],
        "rating": [5.0, 1.0, 3.0, 3.0],
        "review_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]),
    })
    ai_results = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Positive", "topics": ["Cleanliness"]},
            {"review_id": 2, "sentiment": "Negative", "topics": ["Cleanliness"]},
            {"review_id": 3, "sentiment": "Neutral", "topics": []},  # Unassigned / General
            {"review_id": 4, "sentiment": "Neutral", "topics": []},  # Unassigned / General
        ]
    }
    enriched = prepare_enriched_reviews(df, ai_results)

    # 1. Operational topics breakdown must NOT include Unassigned/General Feedback
    matrix = compute_topic_sentiment_breakdown(enriched, include_unassigned=False)
    assert not matrix.empty
    assert "Cleanliness" in matrix["Topic"].values
    assert "General Feedback" not in matrix["Topic"].values
    assert "Unassigned" not in matrix["Topic"].values

    # Cleanliness has 1 Positive, 1 Negative
    clean_pos = matrix[(matrix["Topic"] == "Cleanliness") & (matrix["Sentiment"] == "Positive")]
    clean_neg = matrix[(matrix["Topic"] == "Cleanliness") & (matrix["Sentiment"] == "Negative")]
    assert clean_pos.iloc[0]["Count"] == 1
    assert clean_neg.iloc[0]["Count"] == 1

    # 2. Unassigned review count can be counted separately
    unassigned_count = len(enriched[enriched["topics"].apply(lambda t: not t or len(t) == 0)])
    assert unassigned_count == 2

    # 3. Horizontal stacked bar chart structure
    fig = create_topic_sentiment_stacked_chart(enriched)
    assert fig is not None
    assert fig.layout.barmode == "stack"
    for trace in fig.data:
        assert trace.orientation == "h"
        assert "Sentiment:" in trace.hovertemplate
        assert "Count:" in trace.hovertemplate


# ── 20. Simplified Review Activity Column Chart & Average Rating KPI ─────────

def test_simplified_review_activity_and_average_rating_kpi():
    """
    Verify:
      1. Review Activity is a simple column chart with single vertical axis 'Number of Reviews'.
      2. No secondary axis (yaxis2) exists on the chart.
      3. Dates format in DD/MM/YYYY.
      4. Average Customer Rating KPI is calculated accurately from valid ratings.
    """
    df = pd.DataFrame({
        "review_id": [1, 2, 3, 4],
        "review_text": ["Great food", "Slow service", "Delicious dinner", "Nice ambiance"],
        "rating": [5.0, 2.0, 4.0, 5.0],
        "review_date": pd.to_datetime(["2024-01-05", "2024-01-05", "2024-01-12", "2024-01-19"]),
    })

    # Average rating KPI
    rating_kpi = compute_average_customer_rating(df)
    assert rating_kpi is not None
    assert rating_kpi["average"] == 4.0  # (5 + 2 + 4 + 5) / 4 = 4.0
    assert rating_kpi["count"] == 4
    assert rating_kpi["formatted"] == "4.0 / 5"

    # Timeline trends
    trend_df = compute_timeline_trends(df)
    assert trend_df is not None
    assert "date_label" in trend_df.columns
    assert trend_df["date_label"].iloc[0] == "05/01/2024"
    assert trend_df["Review Count"].iloc[0] == 2

    # Simple column chart
    fig_activity = create_review_activity_chart(df)
    assert fig_activity is not None
    assert len(fig_activity.data) == 1
    assert fig_activity.data[0].type == "bar"  # Column chart
    assert fig_activity.layout.yaxis.title.text == "Number of Reviews"

    # Strict check: NO secondary axis on review activity chart
    assert "yaxis2" not in fig_activity.layout or fig_activity.layout.yaxis2 is None or fig_activity.layout.yaxis2.title is None


# ── 21. Missing Dates & Missing Ratings Graceful Handling ───────────────────

def test_missing_dates_and_ratings_graceful_handling():
    """
    Verify:
      1. When review_date is absent or all null, compute_timeline_trends and create_review_activity_chart return None.
      2. When rating is absent or all null, compute_average_customer_rating returns None.
      3. None of these trigger an unhandled exception.
    """
    # Dataset with no dates and no ratings
    df_no_dates_ratings = pd.DataFrame({
        "review_id": [1, 2],
        "review_text": ["Nice place", "Loved the coffee"],
        "sentiment": ["Positive", "Positive"],
        "topics": [["Ambiance & Facilities"], ["Food Quality"]],
    })

    assert compute_timeline_trends(df_no_dates_ratings) is None
    assert create_review_activity_chart(df_no_dates_ratings) is None
    assert compute_average_customer_rating(df_no_dates_ratings) is None

    # Dataset with NaN dates and ratings
    df_nan = pd.DataFrame({
        "review_id": [1],
        "review_text": ["Test review"],
        "rating": [None],
        "review_date": [pd.NaT],
    })
    assert compute_timeline_trends(df_nan) is None
    assert create_review_activity_chart(df_nan) is None
    assert compute_average_customer_rating(df_nan) is None


# ── 22. Strict Gemini API Isolation on Analytics & Filters ───────────────────

def test_filtering_and_charts_never_trigger_gemini_api(monkeypatch, sample_reviews_data):
    """
    Verify that selecting topics, toggling filters, resetting filters,
    and rendering all charts never call the Gemini AI API.
    """
    df, ai_results = sample_reviews_data

    def forbidden_gemini_call(*args, **kwargs):
        raise RuntimeError("CRITICAL ERROR: Gemini API was unexpectedly called during analytics/filtering!")

    monkeypatch.setattr("google.genai.Client", forbidden_gemini_call)

    # 1. Enriched review preparation
    enriched = prepare_enriched_reviews(df, ai_results)

    # 2. Filter operations
    filter_reviews(enriched, topic="Cleanliness")
    filter_reviews(enriched, topic="Food Quality")
    filter_reviews(enriched, topic="All")

    # 3. Chart creations
    create_sentiment_donut_chart(enriched)
    create_topics_bar_chart(enriched)
    create_topic_sentiment_stacked_chart(enriched)
    create_review_activity_chart(enriched)
    create_trend_line_chart(enriched)

    # 4. KPI calculations
    compute_average_customer_rating(enriched)
    compute_timeline_trends(enriched)


# ── 23. Review Table Date Range & Language Filter Regression Test ────────────

def test_review_table_renders_without_unbound_local_error(monkeypatch):
    """
    Regression test for Milestone 5 UnboundLocalError on date_range.
    Verifies render_review_table executes cleanly when:
      1. Dataset has language column and no dates.
      2. Dataset has both language and date columns.
      3. Dataset has neither language nor dates.
    """
    import streamlit as st
    from components.review_table import render_review_table

    # Case 1: Dataset with language column, no review_date
    df_lang_no_date = pd.DataFrame([
        {"review_id": 1, "review_text": "Food was great", "rating": 5, "language": "English"},
        {"review_id": 2, "review_text": "Food romba late", "rating": 2, "language": "Tanglish"},
    ])
    ai_results = {
        "per_review_breakdown": [
            {"review_id": 1, "sentiment": "Positive", "topics": ["Food Quality"], "language": "English"},
            {"review_id": 2, "sentiment": "Negative", "topics": ["Delivery"], "language": "Tanglish"},
        ]
    }
    st.session_state.clear()
    st.session_state["analysis_done"] = True
    st.session_state["reviews_df"] = df_lang_no_date
    st.session_state["analysis_results"] = ai_results
    st.session_state["review_filter_version"] = 1
    # This must execute without UnboundLocalError
    render_review_table()

    # Case 2: Dataset with both language and valid review_date
    df_both = pd.DataFrame([
        {"review_id": 1, "review_text": "Good taste", "rating": 4, "language": "English", "review_date": pd.to_datetime("2024-05-01")},
        {"review_id": 2, "review_text": "Bad service", "rating": 1, "language": "Tamil", "review_date": pd.to_datetime("2024-05-10")},
    ])
    st.session_state["reviews_df"] = df_both
    st.session_state["review_filter_version"] = 2
    render_review_table()

    # Case 3: Dataset with single-day date range (min_date == max_date)
    df_single_date = pd.DataFrame([
        {"review_id": 1, "review_text": "Same day 1", "rating": 4, "language": "English", "review_date": pd.to_datetime("2024-06-01")},
        {"review_id": 2, "review_text": "Same day 2", "rating": 5, "language": "English", "review_date": pd.to_datetime("2024-06-01")},
    ])
    st.session_state["reviews_df"] = df_single_date
    st.session_state["review_filter_version"] = 3
    render_review_table()


# ── 24. Chart Cursor & Zoom Prevention Verification ──────────────────────────

def test_dashboard_charts_cursor_and_zoom_disabled(sample_reviews_data):
    """
    Verify:
      1. Most Discussed Topics chart has dragmode=False, fixedrange=True on x and y axes.
      2. Topic-wise Sentiment Comparison chart has dragmode=False, fixedrange=True on x and y axes.
      3. Review Activity & Ratings chart has dragmode=False, fixedrange=True on x and y axes.
      4. Hovertooltips (hovertemplate) remain intact.
      5. CSS rules in styles.css guarantee default cursor across chart drag layers.
    """
    df, ai_results = sample_reviews_data
    enriched = prepare_enriched_reviews(df, ai_results)

    # 1. Most Discussed Topics Bar Chart
    fig_topics = create_topics_bar_chart(enriched)
    assert fig_topics.layout.dragmode is False
    assert fig_topics.layout.xaxis.fixedrange is True
    assert fig_topics.layout.yaxis.fixedrange is True
    assert fig_topics.data[0].hovertemplate is not None

    # 2. Topic-wise Sentiment Stacked Chart
    fig_stacked = create_topic_sentiment_stacked_chart(enriched)
    assert fig_stacked.layout.dragmode is False
    assert fig_stacked.layout.xaxis.fixedrange is True
    assert fig_stacked.layout.yaxis.fixedrange is True
    for trace in fig_stacked.data:
        assert trace.hovertemplate is not None

    # 3. Review Activity Chart
    fig_activity = create_review_activity_chart(enriched)
    assert fig_activity.layout.dragmode is False
    assert fig_activity.layout.xaxis.fixedrange is True
    assert fig_activity.layout.yaxis.fixedrange is True
    assert fig_activity.data[0].hovertemplate is not None

    # 4. Empty state charts also have dragmode=False and fixedrange=True
    empty_df = pd.DataFrame(columns=["review_id", "review_text", "topics", "sentiment", "rating", "review_date"])
    empty_topics = create_topics_bar_chart(empty_df)
    assert empty_topics.layout.dragmode is False
    assert empty_topics.layout.xaxis.fixedrange is True
    assert empty_topics.layout.yaxis.fixedrange is True

    empty_stacked = create_topic_sentiment_stacked_chart(empty_df)
    assert empty_stacked.layout.dragmode is False
    assert empty_stacked.layout.xaxis.fixedrange is True
    assert empty_stacked.layout.yaxis.fixedrange is True

    # 5. CSS styles check
    css_path = BASE_DIR / "assets" / "styles.css"
    css_content = css_path.read_text(encoding="utf-8")
    assert ".js-plotly-plot .plotly .nsewdrag" in css_content
    assert "cursor: default !important;" in css_content
