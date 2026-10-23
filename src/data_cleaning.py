"""
src/data_cleaning.py
--------------------
Mezy CSV data validation and cleaning engine (Milestone 2).

Key capabilities:
  1. Flexible column detection: recognises 'Review', 'Reviews', 'Feedback',
     'Customer Feedback', 'Comments', 'review_text', and other common variations
     (case-insensitive, whitespace-tolerant).
  2. Unclear column handling: inspects columns and identifies candidate text
     columns so the user can select the appropriate review column.
  3. Friendly, human-understandable error messages (no technical tracebacks).
  4. Missing-value cleaning: identifies and removes empty or whitespace-only reviews.
  5. Duplicate detection: identifies and deduplicates repeated reviews.
  6. Optional field validation: parses numeric ratings (1-5) and dates safely.
  7. Structured data-quality report generation.
"""

from dataclasses import dataclass, field
import io
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd


# ── Common Review Column Aliases ───────────────────────────────────────────
# Sorted by priority; comparisons are case-insensitive and whitespace-stripped
REVIEW_COLUMN_ALIASES: List[str] = [
    "review_text",
    "review",
    "reviews",
    "feedback",
    "customer feedback",
    "customer_feedback",
    "comments",
    "comment",
    "customer comments",
    "customer_comments",
    "user review",
    "user_review",
    "user reviews",
    "review content",
    "review_content",
    "review text",
    "ratings & reviews",
    "ratings and reviews",
    "remarks",
    "customer remarks",
]

# Aliases for optional columns
RATING_ALIASES: List[str] = [
    "rating",
    "ratings",
    "score",
    "stars",
    "star_rating",
    "customer_rating",
]

DATE_ALIASES: List[str] = [
    "review_date",
    "date",
    "posted_date",
    "created_at",
    "timestamp",
    "time",
]

SOURCE_ALIASES: List[str] = [
    "source",
    "platform",
    "channel",
    "review_source",
]


@dataclass
class DataQualityReport:
    """Summary of data cleaning and quality metrics."""
    total_raw_rows: int = 0
    valid_reviews_count: int = 0
    missing_count: int = 0
    duplicate_count: int = 0
    detected_review_column: str = ""
    original_columns: List[str] = field(default_factory=list)
    has_rating: bool = False
    has_date: bool = False
    has_source: bool = False
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_raw_rows": self.total_raw_rows,
            "valid_reviews_count": self.valid_reviews_count,
            "missing_count": self.missing_count,
            "duplicate_count": self.duplicate_count,
            "detected_review_column": self.detected_review_column,
            "original_columns": self.original_columns,
            "has_rating": self.has_rating,
            "has_date": self.has_date,
            "has_source": self.has_source,
            "warnings": self.warnings,
        }


def normalize_column_name(col: str) -> str:
    """Normalize column header for robust matching."""
    return str(col).strip().lower().replace("_", " ").replace("-", " ")


def find_review_column(
    columns: List[str],
) -> Tuple[Optional[str], List[str]]:
    """
    Find the review column from available column names.

    Returns:
        (matched_column, candidate_columns)
        - matched_column: exact column name in CSV if a known alias matched, else None
        - candidate_columns: all non-empty columns that might contain text/reviews
    """
    if not columns:
        return None, []

    # Map normalized names back to original column names
    col_map = {normalize_column_name(col): col for col in columns if str(col).strip()}

    # 1. Exact alias match in priority order
    for alias in REVIEW_COLUMN_ALIASES:
        norm_alias = normalize_column_name(alias)
        if norm_alias in col_map:
            return col_map[norm_alias], list(col_map.values())

    # 2. Substring keyword match (e.g., "zomato review", "product feedback")
    keywords = ["review", "feedback", "comment"]
    for norm_col, orig_col in col_map.items():
        if any(kw in norm_col for kw in keywords):
            return orig_col, list(col_map.values())

    # 3. No match found — return candidate columns for manual selection
    return None, list(col_map.values())


def find_optional_column(columns: List[str], aliases: List[str]) -> Optional[str]:
    """Find optional column (rating, date, source) by aliases."""
    col_map = {normalize_column_name(col): col for col in columns if str(col).strip()}
    for alias in aliases:
        norm_alias = normalize_column_name(alias)
        if norm_alias in col_map:
            return col_map[norm_alias]
    return None


def clean_and_validate_dataframe(
    df: pd.DataFrame,
    review_column: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[DataQualityReport], Optional[str]]:
    """
    Clean and validate a loaded DataFrame.

    Args:
        df: Raw pandas DataFrame
        review_column: Name of the review column (optional, auto-detected if None)

    Returns:
        (cleaned_df, report, friendly_error_message)
    """
    # Check for empty dataframe
    if df is None or df.empty:
        return (
            None,
            None,
            "The uploaded file contains no data rows. Please upload a CSV with customer reviews.",
        )

    columns = [str(c) for c in df.columns]
    if not columns:
        return (
            None,
            None,
            "The uploaded file has no columns or headers. Please upload a valid CSV file.",
        )

    # Resolve review column
    chosen_col = review_column
    if not chosen_col or chosen_col not in df.columns:
        matched_col, candidates = find_review_column(columns)
        if matched_col:
            chosen_col = matched_col
        else:
            return (
                None,
                None,
                "Could not identify a customer review column in your file. "
                "Please select the column containing your reviews.",
            )

    report = DataQualityReport()
    report.total_raw_rows = len(df)
    report.original_columns = columns
    report.detected_review_column = chosen_col

    # Create working copy
    cleaned = df.copy()

    # ── 1. Standardize review text & handle missing values ──────────────────
    # Convert chosen review column to string, strip whitespace, handle NaN/None
    raw_series = cleaned[chosen_col]
    cleaned["review_text"] = raw_series.astype(str).str.strip()

    # Mask invalid/missing strings: "nan", "none", "null", or empty strings
    is_missing = (
        raw_series.isna()
        | cleaned["review_text"].str.lower().isin(["nan", "none", "null", ""])
        | (cleaned["review_text"].str.len() == 0)
    )

    missing_count = int(is_missing.sum())
    report.missing_count = missing_count
    if missing_count > 0:
        report.warnings.append(
            f"Removed {missing_count} row{'s' if missing_count > 1 else ''} with empty or missing review text."
        )

    # Filter out missing reviews
    cleaned = cleaned[~is_missing].copy()

    if cleaned.empty:
        return (
            None,
            report,
            "All reviews in the selected column were empty or missing. "
            "Please check your file and upload one with actual customer review text.",
        )

    # ── 2. Handle Duplicates ────────────────────────────────────────────────
    # Check for duplicate review text (case-insensitive duplicate check)
    lower_reviews = cleaned["review_text"].str.lower()
    dup_mask = lower_reviews.duplicated(keep="first")
    duplicate_count = int(dup_mask.sum())
    report.duplicate_count = duplicate_count

    if duplicate_count > 0:
        report.warnings.append(
            f"Removed {duplicate_count} duplicate review{'s' if duplicate_count > 1 else ''}."
        )
        cleaned = cleaned[~dup_mask].copy()

    report.valid_reviews_count = len(cleaned)

    # ── 3. Validate Optional Fields ─────────────────────────────────────────
    # Rating
    rating_col = find_optional_column(columns, RATING_ALIASES)
    if rating_col and rating_col in cleaned.columns:
        report.has_rating = True
        try:
            cleaned["rating"] = pd.to_numeric(cleaned[rating_col], errors="coerce")
            # Cap / validate standard 1-5 ratings
            invalid_ratings = (cleaned["rating"] < 1) | (cleaned["rating"] > 5)
            if invalid_ratings.any():
                cleaned.loc[invalid_ratings, "rating"] = None
                report.warnings.append("Some ratings fell outside the 1–5 range and were marked as unrated.")
        except Exception:
            cleaned["rating"] = None
    else:
        cleaned["rating"] = None

    # Review Date
    date_col = find_optional_column(columns, DATE_ALIASES)
    if date_col and date_col in cleaned.columns:
        report.has_date = True
        try:
            cleaned["review_date"] = pd.to_datetime(cleaned[date_col], errors="coerce")
        except Exception:
            cleaned["review_date"] = None
    else:
        cleaned["review_date"] = None

    # Source
    source_col = find_optional_column(columns, SOURCE_ALIASES)
    if source_col and source_col in cleaned.columns:
        report.has_source = True
        cleaned["source"] = cleaned[source_col].astype(str).str.strip().replace({"nan": "Direct", "None": "Direct", "": "Direct"})
    else:
        cleaned["source"] = "Direct"

    # Reset index and ensure review_id exists
    cleaned.reset_index(drop=True, inplace=True)
    cleaned["review_id"] = cleaned.index + 1

    return cleaned, report, None


def load_and_validate_csv(
    file_or_bytes: Union[str, bytes, io.BytesIO, Any],
    selected_column: Optional[str] = None,
) -> Tuple[Optional[pd.DataFrame], Optional[DataQualityReport], Optional[str], List[str]]:
    """
    Safely read and validate an uploaded CSV file.

    Returns:
        (cleaned_df, report, error_message, available_columns)
        - If error_message is not None and available_columns is non-empty,
          the caller can prompt the user to choose the review column.
    """
    try:
        if hasattr(file_or_bytes, "seek"):
            file_or_bytes.seek(0)
        df = pd.read_csv(file_or_bytes)
    except pd.errors.EmptyDataError:
        return (
            None,
            None,
            "The uploaded file is empty. Please upload a CSV containing customer reviews.",
            [],
        )
    except UnicodeDecodeError:
        try:
            if hasattr(file_or_bytes, "seek"):
                file_or_bytes.seek(0)
            df = pd.read_csv(file_or_bytes, encoding="latin-1")
        except Exception:
            return (
                None,
                None,
                "Could not read the CSV file due to text encoding issues. Please save your file as UTF-8 CSV.",
                [],
            )
    except Exception as exc:
        return (
            None,
            None,
            f"We couldn't read your CSV file. Please make sure it is a valid comma-separated text file. ({str(exc)})",
            [],
        )

    if df.empty:
        return (
            None,
            None,
            "The uploaded CSV file contains no data rows. Please check your file.",
            [],
        )

    available_cols = [str(c) for c in df.columns]

    # Check review column
    chosen_col = selected_column
    if not chosen_col or chosen_col not in df.columns:
        matched_col, candidates = find_review_column(available_cols)
        if matched_col:
            chosen_col = matched_col
        else:
            # Column name is unclear — return available candidates so user can select
            return (
                None,
                None,
                "Please select the column that contains your customer reviews to continue.",
                available_cols,
            )

    cleaned_df, report, err = clean_and_validate_dataframe(df, review_column=chosen_col)
    return cleaned_df, report, err, available_cols
