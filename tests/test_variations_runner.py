"""
tests/test_variations_runner.py
-------------------------------
Direct runner testing various CSV formats and column headers.
"""

import io
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.data_cleaning import (
    load_and_validate_csv,
    clean_and_validate_dataframe,
    find_review_column,
)

def run_all_variations():
    test_cases = [
        ("review_text", "review_text,rating\n\"Great food!\",5\n\"Slow service\",2\n"),
        ("Review", "Review,rating\n\"Awesome dosa!\",5\n\"Could be better\",3\n"),
        ("Reviews", "Reviews,source\n\"Best coffee in town!\",Swiggy\n"),
        ("Feedback", "Feedback,date\n\"Polite staff and clean tables\",2024-01-01\n"),
        ("Customer Feedback", "Customer Feedback,rating\n\"Loved the dessert!\",5\n"),
        ("Comments", "Comments\n\"Biryani was super spicy and delicious\"\n"),
        ("Unclear Column (guest_notes)", "guest_id,guest_notes\n101,\"Staff was very helpful\"\n"),
        ("Empty File", ""),
        ("No Review Columns", "col_a,col_b\n123,456\n"),
        ("Duplicates & Missing", "Review,rating\n\"Great!\",5\n\"\",4\n\"Great!\",5\n   ,1\n"),
    ]

    print("=== TESTING CSV VARIATIONS ===")
    for name, content in test_cases:
        if name == "Empty File":
            cleaned, report, err, cols = load_and_validate_csv(io.StringIO(content))
            assert err is not None
            print(f"[PASS] {name} -> Friendly error: {err}")
        elif name == "No Review Columns":
            df = pd.read_csv(io.StringIO(content))
            matched, candidates = find_review_column(list(df.columns))
            assert matched is None
            cleaned, report, err = clean_and_validate_dataframe(df)
            assert err is not None
            print(f"[PASS] {name} -> Prompted selection / error: {err}")
        elif "Unclear" in name:
            df = pd.read_csv(io.StringIO(content))
            matched, candidates = find_review_column(list(df.columns))
            assert matched is None
            assert "guest_notes" in candidates
            cleaned, report, err = clean_and_validate_dataframe(df, review_column="guest_notes")
            assert err is None
            assert cleaned["review_text"].iloc[0] == "Staff was very helpful"
            print(f"[PASS] {name} -> Candidates: {candidates}, Cleaned with selected 'guest_notes'")
        elif name == "Duplicates & Missing":
            cleaned, report, err, cols = load_and_validate_csv(io.StringIO(content))
            assert err is None
            assert len(cleaned) == 1
            assert report.missing_count == 2
            assert report.duplicate_count == 1
            print(f"[PASS] {name} -> Kept 1 valid row, removed {report.missing_count} missing and {report.duplicate_count} duplicate")
        else:
            cleaned, report, err, cols = load_and_validate_csv(io.StringIO(content))
            assert err is None
            assert len(cleaned) >= 1
            assert "review_text" in cleaned.columns
            print(f"[PASS] {name} -> Detected: '{report.detected_review_column}', Rows: {len(cleaned)}")

    print("\n=== ALL 10 CSV VARIATION CHECKS PASSED ===")

if __name__ == "__main__":
    run_all_variations()
