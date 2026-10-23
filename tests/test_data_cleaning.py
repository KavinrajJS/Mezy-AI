"""
tests/test_data_cleaning.py
----------------------------
Comprehensive unit tests for CSV upload validation and data cleaning (Milestone 2).

Tests cover:
  1. Recognition of common review column alternatives:
     - Review, Reviews, Feedback, Customer Feedback, Comments, review_text, etc.
  2. Case-insensitivity and whitespace tolerance in headers.
  3. Unclear column handling and user selection resolution.
  4. Friendly error messages for invalid, empty, or unreadable CSVs.
  5. Missing-value cleaning and counting.
  6. Duplicate detection and deduplication.
  7. Optional columns (rating range 1-5, date parsing, source).
  8. End-to-end loading on sample reviews.
"""

import io
import sys
from pathlib import Path
import pandas as pd
import pytest

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.data_cleaning import (
    find_review_column,
    find_optional_column,
    clean_and_validate_dataframe,
    load_and_validate_csv,
    normalize_column_name,
    DataQualityReport,
    REVIEW_COLUMN_ALIASES,
)


# ── 1. Column Alias Recognition Tests ──────────────────────────────────────

@pytest.mark.parametrize(
    "col_name",
    [
        "review_text",
        "Review",
        "Reviews",
        "Feedback",
        "Customer Feedback",
        "Comments",
        "Comment",
        "customer comments",
        "user review",
        "review content",
    ],
)
def test_recognize_required_and_common_aliases(col_name: str):
    """Verify recognition of all specified aliases."""
    columns = ["id", col_name, "date"]
    matched, candidates = find_review_column(columns)
    assert matched == col_name
    assert candidates == columns


@pytest.mark.parametrize(
    "col_name",
    [
        "REVIEW",
        "  reviews  ",
        "cUsToMeR FeEdBaCk",
        "customer_feedback",
        "   Comments   ",
        "REVIEW_TEXT",
    ],
)
def test_alias_case_insensitivity_and_whitespace(col_name: str):
    """Verify case-insensitivity and whitespace tolerance."""
    columns = ["user_id", col_name, "stars"]
    matched, _ = find_review_column(columns)
    assert matched == col_name


def test_keyword_matching_for_uncommon_review_headers():
    """Verify columns containing review keywords are recognized."""
    columns = ["order_id", "zomato customer feedback", "delivery_time"]
    matched, _ = find_review_column(columns)
    assert matched == "zomato customer feedback"


# ── 2. Unclear Column Resolution Tests ────────────────────────────────────

def test_unclear_columns_returns_none_and_candidates():
    """When headers don't match any aliases, return None and candidate list."""
    columns = ["order_id", "guest_experience", "store_location"]
    matched, candidates = find_review_column(columns)
    assert matched is None
    assert candidates == columns


def test_clean_with_user_selected_column():
    """Verify dataframe can be cleaned when user manually chooses the column."""
    raw_df = pd.DataFrame({
        "order_id": [101, 102],
        "guest_experience": [
            "Great coffee and delicious croissants!",
            "Waited 30 minutes, table was not cleaned.",
        ],
    })
    cleaned_df, report, err = clean_and_validate_dataframe(
        raw_df,
        review_column="guest_experience",
    )
    assert err is None
    assert cleaned_df is not None
    assert report is not None
    assert "review_text" in cleaned_df.columns
    assert len(cleaned_df) == 2
    assert report.detected_review_column == "guest_experience"


# ── 3. Friendly Error Handling Tests ───────────────────────────────────────

def test_empty_dataframe_returns_friendly_error():
    """Empty dataframe produces understandable error message."""
    raw_df = pd.DataFrame()
    cleaned_df, report, err = clean_and_validate_dataframe(raw_df)
    assert cleaned_df is None
    assert err is not None
    assert "no data rows" in err.lower() or "empty" in err.lower()


def test_no_suitable_column_returns_friendly_error():
    """Dataframe without identifiable review column produces helpful message."""
    raw_df = pd.DataFrame({
        "user_id": [1, 2, 3],
        "zip_code": [600001, 600002, 600003],
    })
    cleaned_df, report, err = clean_and_validate_dataframe(raw_df)
    assert cleaned_df is None
    assert err is not None
    assert "select the column" in err.lower() or "could not identify" in err.lower()


def test_all_empty_reviews_returns_friendly_error():
    """When all review entries are missing or blank, return friendly error."""
    raw_df = pd.DataFrame({
        "Review": ["", "   ", None, "nan"],
    })
    cleaned_df, report, err = clean_and_validate_dataframe(raw_df)
    assert cleaned_df is None
    assert err is not None
    assert "empty or missing" in err.lower()


def test_load_empty_csv_bytes():
    """Empty CSV file produces human-friendly error."""
    empty_csv = io.StringIO("")
    cleaned_df, report, err, cols = load_and_validate_csv(empty_csv)
    assert cleaned_df is None
    assert err is not None
    assert "empty" in err.lower()


# ── 4. Missing-Value Handling Tests ────────────────────────────────────────

def test_missing_values_filtered_and_counted():
    """Ensure null, NaN, and whitespace-only reviews are removed."""
    raw_df = pd.DataFrame({
        "Customer Feedback": [
            "Outstanding biryani and quick service!",
            "",           # empty string
            "   ",        # whitespace only
            None,         # None
            float("nan"), # NaN
            "Loved the cold brew!",
            "nan",        # string literal 'nan'
        ],
        "rating": [5, 2, 3, 4, 1, 5, 2],
    })
    cleaned_df, report, err = clean_and_validate_dataframe(raw_df)
    assert err is None
    assert cleaned_df is not None
    assert len(cleaned_df) == 2
    assert report.missing_count == 5
    assert report.valid_reviews_count == 2
    assert len(report.warnings) > 0


# ── 5. Duplicate Detection Tests ───────────────────────────────────────────

def test_duplicate_reviews_identified_and_removed():
    """Exact and case-insensitive duplicates are removed and counted."""
    raw_df = pd.DataFrame({
        "Comments": [
            "Best filter coffee in the city!",
            "Great service, polite staff.",
            "best filter coffee in the city!",  # Duplicate with different casing
            "Best filter coffee in the city! ", # Duplicate with trailing space
            "Dosa was crispy and chutney was fresh.",
        ],
    })
    cleaned_df, report, err = clean_and_validate_dataframe(raw_df)
    assert err is None
    assert cleaned_df is not None
    assert len(cleaned_df) == 3
    assert report.duplicate_count == 2
    assert report.valid_reviews_count == 3


# ── 6. Optional Columns Validation Tests ────────────────────────────────────

def test_rating_range_validation():
    """Ratings are converted to numeric; out-of-range values capped/nullified."""
    raw_df = pd.DataFrame({
        "Review": [
            "Good food",
            "Bad service",
            "Average experience",
            "Outstanding meal",
        ],
        "Rating": [5, 1, 10, "invalid_num"],  # 10 is >5, string is invalid
    })
    cleaned_df, report, err = clean_and_validate_dataframe(raw_df)
    assert err is None
    assert report.has_rating is True
    # First two ratings are valid
    assert cleaned_df["rating"].iloc[0] == 5.0
    assert cleaned_df["rating"].iloc[1] == 1.0
    # Out of range or invalid coerced to None / NaN
    assert pd.isna(cleaned_df["rating"].iloc[2])
    assert pd.isna(cleaned_df["rating"].iloc[3])


def test_date_parsing_validation():
    """Review dates are safely parsed to datetime objects."""
    raw_df = pd.DataFrame({
        "Feedback": ["Nice ambiance", "Loved the music"],
        "date": ["2024-01-15", "invalid-date-string"],
    })
    cleaned_df, report, err = clean_and_validate_dataframe(raw_df)
    assert err is None
    assert report.has_date is True
    assert not pd.isna(cleaned_df["review_date"].iloc[0])
    assert pd.isna(cleaned_df["review_date"].iloc[1])


# ── 7. Integration with Realistic CSV files ────────────────────────────────

def test_sample_reviews_csv_file():
    """Test loading and cleaning the actual sample_reviews.csv in data/."""
    sample_path = BASE_DIR / "data" / "sample_reviews.csv"
    assert sample_path.exists()

    with open(sample_path, "r", encoding="utf-8") as f:
        content = f.read()

    cleaned_df, report, err, cols = load_and_validate_csv(io.StringIO(content))
    assert err is None
    assert cleaned_df is not None
    assert report is not None
    assert len(cleaned_df) > 0
    assert "review_text" in cleaned_df.columns
    assert "review_id" in cleaned_df.columns
    assert report.detected_review_column == "review_text"
    assert report.has_rating is True
    assert report.has_date is True
    assert report.has_source is True


def test_end_to_end_with_different_column_names_csv():
    """Test full workflow with CSVs containing Review, Feedback, Comments."""
    csv_feedback = """Feedback,score,source
"Fantastic burger and crispy fries!",5,Swiggy
"Too much salt in the gravy.",2,Zomato
"Fantastic burger and crispy fries!",5,Swiggy
"""
    cleaned_df, report, err, cols = load_and_validate_csv(io.StringIO(csv_feedback))
    assert err is None
    assert cleaned_df is not None
    assert report.detected_review_column == "Feedback"
    assert report.duplicate_count == 1
    assert len(cleaned_df) == 2
