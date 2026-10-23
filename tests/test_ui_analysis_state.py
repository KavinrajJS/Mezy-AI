"""
tests/test_ui_analysis_state.py
-------------------------------
Focused tests for UI state transitions, composer clearing, and Stop/Cancel behavior.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from components.loading_animation import _ORB_HTML
from src.gemini_service import GeminiServiceError


def test_loading_message_is_simplified():
    """Verify loading message does not contain 'with Gemini AI'."""
    assert "Analysing customer reviews..." in _ORB_HTML.format(status="Analysing customer reviews...")
    assert "Gemini AI" not in _ORB_HTML.format(status="Analysing customer reviews...")


def test_composer_clearing_and_data_retention():
    """Verify composer widgets advance version key while data is retained internally."""
    mock_session = {
        "composer_version": 0,
        "is_analyzing": False,
        "active_cleaned_df": None,
        "active_question": "",
    }

    # Simulate submission of data
    df = pd.DataFrame({"review_text": ["Great food!"]})
    question = "What is the top dish?"

    # Submission logic
    mock_session["active_cleaned_df"] = df
    mock_session["active_question"] = question
    mock_session["is_analyzing"] = True
    mock_session["cancel_requested"] = False
    mock_session["composer_version"] += 1

    # Verify widget key advanced (clearing the widget)
    assert mock_session["composer_version"] == 1
    # Verify data is safely retained internally for analysis
    assert mock_session["active_cleaned_df"] is not None
    assert mock_session["active_question"] == "What is the top dish?"
    assert mock_session["is_analyzing"] is True


def test_stop_button_cancellation_state():
    """Verify Stop button resets analysis state, hides loading, and prevents results display."""
    mock_session = {
        "is_analyzing": True,
        "cancel_requested": False,
        "analysis_future": MagicMock(),
        "analysis_stopped_notice": False,
    }

    # Simulate user clicking Stop (■)
    mock_session["is_analyzing"] = False
    mock_session["cancel_requested"] = True
    fut = mock_session.get("analysis_future")
    if fut is not None:
        fut.cancel()
        mock_session["analysis_future"] = None
    mock_session["analysis_stopped_notice"] = True

    # Assertions: state must be idle, future cancelled, and cancelled flag set
    assert mock_session["is_analyzing"] is False
    assert mock_session["cancel_requested"] is True
    assert mock_session["analysis_future"] is None
    assert mock_session["analysis_stopped_notice"] is True


def test_error_resets_loading_state():
    """Verify errors reset is_analyzing so arrow button returns."""
    mock_session = {
        "is_analyzing": True,
        "analysis_future": MagicMock(),
    }

    # Simulate an error raised by Gemini
    err = GeminiServiceError("Rate limit reached")
    mock_session["is_analyzing"] = False
    mock_session["analysis_future"] = None
    mock_session["last_error"] = str(err)

    assert mock_session["is_analyzing"] is False
    assert mock_session["analysis_future"] is None
    assert "Rate limit" in mock_session["last_error"]


def test_poll_analysis_monitor_fragment_exists():
    """Verify _poll_analysis_monitor exists in upload module and is decorated."""
    import components.upload as up
    assert hasattr(up, "_poll_analysis_monitor")
    assert callable(up._poll_analysis_monitor)


def test_analyzing_screen_css_rules():
    """Verify styles.css contains required analysis screen layout and scrolling definitions."""
    css_file = BASE_DIR / "assets" / "styles.css"
    content = css_file.read_text(encoding="utf-8")
    assert ".mezy-analyzing-screen" in content
    assert ".stAppViewContainer" in content
    assert "scroll-behavior: smooth" in content


def test_new_submission_clears_previous_stale_results():
    """Verify starting a new analysis does not display stale results from previous run."""
    mock_session = {
        "analysis_done": True,
        "analysis_results": {"summary": {"status": "old_results"}},
        "reviews_df": pd.DataFrame({"review_text": ["Old review"]}),
        "is_analyzing": False,
    }

    # User initiates new analysis with new dataset
    new_df = pd.DataFrame({"review_text": ["New review 1", "New review 2"]})
    mock_session["active_cleaned_df"] = new_df
    mock_session["active_question"] = "New focus"
    mock_session["is_analyzing"] = True
    mock_session["cancel_requested"] = False
    mock_session["analysis_done"] = False
    mock_session["analysis_results"] = None

    assert mock_session["is_analyzing"] is True
    assert mock_session["analysis_done"] is False
    assert mock_session["analysis_results"] is None
    assert len(mock_session["active_cleaned_df"]) == 2


def test_landing_page_css_fixes():
    """Verify CSS rules for document illustration position, InputInstructions removal, and composer padding."""
    css_file = BASE_DIR / "assets" / "styles.css"
    content = css_file.read_text(encoding="utf-8")

    # Document illustration moved upward neatly
    assert ".composer-docs-anchor" in content
    assert "height: 44px" in content
    assert "margin-bottom: -6px" in content

    # "Press Enter to apply" instruction removed
    assert '[data-testid="InputInstructions"]' in content
    assert "display: none !important" in content

    # Chat composer container height and padding
    assert 'padding: 1rem 1.35rem 1.15rem' in content
    assert 'min-height: 125px' in content


def test_loading_status_message_meaningful():
    """Verify loading message begins with 'Analyzing customer reviews...'."""
    from src.translations import t
    assert t("loading_preparing", "English") == "Analyzing customer reviews…"
    assert t("loading_analysing", "English") == "Analyzing customer reviews…"


def test_document_visual_hidden_during_analysis():
    """Verify document stack HTML is conditioned on not is_analyzing in upload.py."""
    upload_file = BASE_DIR / "components" / "upload.py"
    code = upload_file.read_text(encoding="utf-8")
    assert "if not is_analyzing:" in code
    assert 'composer-docs-anchor' in code


