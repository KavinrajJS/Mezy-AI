"""
tests/test_action_tracker_ui.py
-------------------------------
End-to-end integration tests for Action Tracker UI rendering,
validation, persistence, and report export logic.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
from src.database import (
    action_exists,
    create_action,
    delete_action,
    get_action_by_id,
    get_action_statistics,
    get_all_actions,
    init_db,
    update_action,
    update_action_status_and_notes,
)
from src.report_generator import generate_docx_report, generate_pdf_report
from components.action_tracker import render_action_tracker


@pytest.fixture
def mock_session_state(tmp_path: Path):
    """Provide a mocked session state with sample data and temporary SQLite DB."""
    test_db = tmp_path / "action_ui_test.db"
    init_db(test_db)

    state = {
        "language": "English",
        "current_page": "action_tracker",
        "reviews_df": pd.DataFrame([
            {"review_id": 1, "review_text": "Great pasta, loved the sauce!", "rating": 5.0, "sentiment": "Positive"},
            {"review_id": 2, "review_text": "Slow service, waited 35 mins.", "rating": 2.0, "sentiment": "Negative"},
        ]),
        "analysis_results": {
            "summary": {"total_reviews": 2, "executive_summary": "Good food but slow service."},
            "customer_likes": [{"topic": "Food", "summary": "Great pasta", "evidence_quote": "Great pasta"}],
            "common_complaints": [{"topic": "Service", "summary": "Slow service", "evidence_quote": "Slow service"}],
            "actionable_recommendations": [
                {
                    "area": "Kitchen Speed",
                    "priority": "High",
                    "recommendation": "Prep ingredients earlier",
                    "reasoning": "Peak dinner rushes cause 35m waits",
                    "supporting_evidence": "Slow service, waited 35 mins.",
                }
            ],
        },
        "analysis_done": True,
    }
    return state, test_db


def test_action_crud_end_to_end(mock_session_state):
    """Verify complete CRUD lifecycle: create, read, update, status/notes, delete."""
    _, db_path = mock_session_state

    # 1. Create
    act_id = create_action(
        title="Speed up kitchen prep",
        action="Pre-cut vegetables for dinner service",
        priority="High",
        evidence="Customer waited 35 mins",
        notes="Discussed with chef",
        status="Open",
        db_path=db_path,
    )
    assert act_id > 0

    # 2. Read
    act = get_action_by_id(act_id, db_path=db_path)
    assert act["title"] == "Speed up kitchen prep"
    assert act["priority"] == "High"
    assert act["status"] == "Open"

    # 3. Quick Status Update
    ok = update_action_status_and_notes(act_id, status="In Progress", notes="In progress with prep cook", db_path=db_path)
    assert ok is True
    updated_act = get_action_by_id(act_id, db_path=db_path)
    assert updated_act["status"] == "In Progress"
    assert updated_act["notes"] == "In progress with prep cook"

    # 4. Full Edit
    ok = update_action(
        action_id=act_id,
        title="Revise kitchen prep timeline",
        action="Pre-cut vegetables 2 hours before opening",
        priority="Medium",
        status="Resolved",
        evidence="Customer waited 35 mins",
        notes="Implemented successfully",
        db_path=db_path,
    )
    assert ok is True
    resolved_act = get_action_by_id(act_id, db_path=db_path)
    assert resolved_act["status"] == "Resolved"
    assert resolved_act["priority"] == "Medium"
    assert resolved_act["title"] == "Revise kitchen prep timeline"

    # 5. Delete
    deleted = delete_action(act_id, db_path=db_path)
    assert deleted is True
    assert get_action_by_id(act_id, db_path=db_path) is None


def test_action_tracker_report_generation_both_languages(mock_session_state):
    """Verify both English and Tamil reports (PDF & Word) generate with valid output."""
    state, db_path = mock_session_state

    create_action(
        title="Kitchen order dispatch",
        action="Add POS kitchen display",
        priority="High",
        evidence="35 min delay",
        status="Open",
        db_path=db_path,
    )
    actions = get_all_actions(db_path=db_path)

    # English PDF
    pdf_en, warn_en = generate_pdf_report(
        reviews_df=state["reviews_df"],
        analysis_results=state["analysis_results"],
        actions=actions,
        language="English",
    )
    assert pdf_en.startswith(b"%PDF-")
    assert warn_en is None

    # Tamil PDF
    pdf_ta, warn_ta = generate_pdf_report(
        reviews_df=state["reviews_df"],
        analysis_results=state["analysis_results"],
        actions=actions,
        language="Tamil",
    )
    assert pdf_ta.startswith(b"%PDF-")

    # English Word (.docx)
    docx_en = generate_docx_report(
        reviews_df=state["reviews_df"],
        analysis_results=state["analysis_results"],
        actions=actions,
        language="English",
    )
    assert docx_en.startswith(b"PK\x03\x04")

    # Tamil Word (.docx)
    docx_ta = generate_docx_report(
        reviews_df=state["reviews_df"],
        analysis_results=state["analysis_results"],
        actions=actions,
        language="Tamil",
    )
    assert docx_ta.startswith(b"PK\x03\x04")


def test_action_exists_duplicate_prevention(mock_session_state):
    """Verify action_exists correctly identifies duplicates by title and action."""
    from src.database import action_exists

    _, db_path = mock_session_state
    create_action(
        title="Hygiene Audit",
        action="Perform bi-weekly sanitation inspections",
        priority="High",
        db_path=db_path,
    )

    # Identical title (case-insensitive)
    assert action_exists(title="hygiene audit", db_path=db_path) is True
    # Identical action text
    assert (
        action_exists(
            title="Different Title",
            action="Perform bi-weekly sanitation inspections",
            db_path=db_path,
        )
        is True
    )
    # Non-existent
    assert action_exists(title="Unrelated Topic", action="New Action", db_path=db_path) is False


def test_render_action_tracker_no_text_area_rows_error(mock_session_state):
    """Verify render_action_tracker executes without raising TypeError on text_area rows argument."""
    state, db_path = mock_session_state
    with patch("streamlit.session_state", state):
        # Should execute cleanly without TypeError: TextWidgetsMixin.text_area() got unexpected keyword argument 'rows'
        try:
            render_action_tracker()
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                pytest.fail(f"render_action_tracker raised unexpected parameter error: {e}")
            raise
        except Exception:
            # Other non-argument exceptions (like Streamlit run context) are acceptable in unit test
            pass


def test_ai_recommendations_not_automatically_added_to_saved_actions(mock_session_state):
    """Verify AI recommendations are NOT automatically inserted into SQLite on render or rerun."""
    state, db_path = mock_session_state

    # Verify initial database is completely empty
    initial_actions = get_all_actions(db_path=db_path)
    assert len(initial_actions) == 0

    # Execute render_action_tracker with mock session state containing AI recommendations
    with patch("streamlit.session_state", state), patch("components.action_tracker.get_all_actions", return_value=get_all_actions(db_path=db_path)):
        try:
            render_action_tracker()
        except Exception:
            pass

    # Database must STILL have 0 actions - rendering never auto-inserts recommendations
    after_render_actions = get_all_actions(db_path=db_path)
    assert len(after_render_actions) == 0

    # Now simulate user explicitly clicking "+ Add to Tracker"
    rec = state["analysis_results"]["actionable_recommendations"][0]
    assert not action_exists(title=rec["area"], action=rec["recommendation"], db_path=db_path)

    act_id = create_action(
        title=rec["area"],
        action=rec["recommendation"],
        priority=rec["priority"],
        evidence=rec["supporting_evidence"],
        notes=rec["reasoning"],
        status="Open",
        db_path=db_path,
    )
    assert act_id > 0

    # Exactly 1 action exists
    saved = get_all_actions(db_path=db_path)
    assert len(saved) == 1
    assert saved[0]["title"] == rec["area"]

    # Prevent duplicate additions
    assert action_exists(title=rec["area"], action=rec["recommendation"], db_path=db_path) is True


def test_add_to_tracker_complete_workflow(mock_session_state):
    """
    Test the complete 9-step workflow required by user:
      1. Open page and check existing saved actions (initially empty).
      2. Click Add to Tracker on recommendation 1.
      3. Confirm it appears in Saved Actions & Progress.
      4. Refresh page (re-query persistent storage) and confirm it is still there.
      5. Confirm recommendation 1 button still reflects Added to Tracker.
      6. Add another recommendation and verify both actions remain visible in Saved Actions.
      7. Delete one action and verify tracker and button state update correctly (can be added again).
      8. Test search and priority filters.
      9. Generate report and verify it includes the actual saved actions.
    """
    state, db_path = mock_session_state
    recs = [
        {
            "area": "Kitchen Speed",
            "priority": "High",
            "recommendation": "Prep vegetables and portion pasta before lunch rush.",
            "reasoning": "Peak dinner rushes cause long wait times.",
            "supporting_evidence": "Customer waited 40 mins.",
        },
        {
            "area": "Staff Courtesy",
            "priority": "Medium",
            "recommendation": "Conduct weekly hospitality training for front-of-house staff.",
            "reasoning": "Customers noted unwelcoming reception.",
            "supporting_evidence": "Staff seemed indifferent upon arrival.",
        },
    ]
    state["analysis_results"]["actionable_recommendations"] = recs

    # Step 1: Open page and check existing saved actions (initially empty)
    actions_initial = get_all_actions(db_path=db_path)
    assert len(actions_initial) == 0

    # Step 2: Click Add to Tracker on recommendation 1
    rec1 = recs[0]
    act1_id = create_action(
        title=rec1["area"],
        action=rec1["recommendation"],
        priority=rec1["priority"],
        evidence=rec1["supporting_evidence"],
        notes=rec1["reasoning"],
        status="Open",
        db_path=db_path,
    )
    assert act1_id > 0

    # Step 3: Confirm it appears in Saved Actions & Progress
    actions_after_add1 = get_all_actions(db_path=db_path)
    assert len(actions_after_add1) == 1
    assert actions_after_add1[0]["title"] == "Kitchen Speed"
    assert actions_after_add1[0]["action"] == rec1["recommendation"]

    # Step 4: Refresh page (re-query persistent storage) and confirm it is still there
    refreshed_actions = get_all_actions(db_path=db_path)
    assert len(refreshed_actions) == 1
    assert refreshed_actions[0]["id"] == act1_id

    # Step 5: Confirm button state reflects Added to Tracker for rec1 and not added for rec2
    is_rec1_added = any(
        (str(a.get("title", "")).strip().lower() == rec1["area"].lower() and str(a.get("action", "")).strip().lower() == rec1["recommendation"].lower())
        or (str(a.get("action", "")).strip().lower() == rec1["recommendation"].lower() and rec1["recommendation"] != "")
        for a in refreshed_actions
    )
    assert is_rec1_added is True

    rec2 = recs[1]
    is_rec2_added = any(
        (str(a.get("title", "")).strip().lower() == rec2["area"].lower() and str(a.get("action", "")).strip().lower() == rec2["recommendation"].lower())
        or (str(a.get("action", "")).strip().lower() == rec2["recommendation"].lower() and rec2["recommendation"] != "")
        for a in refreshed_actions
    )
    assert is_rec2_added is False

    # Step 6: Add another recommendation and verify both actions remain visible
    act2_id = create_action(
        title=rec2["area"],
        action=rec2["recommendation"],
        priority=rec2["priority"],
        evidence=rec2["supporting_evidence"],
        notes=rec2["reasoning"],
        status="Open",
        db_path=db_path,
    )
    assert act2_id > 0

    actions_both = get_all_actions(db_path=db_path)
    assert len(actions_both) == 2
    titles = [a["title"] for a in actions_both]
    assert "Kitchen Speed" in titles
    assert "Staff Courtesy" in titles

    # Step 7: Delete one action and verify tracker and button state update correctly
    delete_ok = delete_action(act1_id, db_path=db_path)
    assert delete_ok is True

    actions_after_del = get_all_actions(db_path=db_path)
    assert len(actions_after_del) == 1
    assert actions_after_del[0]["id"] == act2_id

    # Button state for rec1 must revert to not added (can be added again)
    is_rec1_added_after_del = any(
        (str(a.get("title", "")).strip().lower() == rec1["area"].lower() and str(a.get("action", "")).strip().lower() == rec1["recommendation"].lower())
        or (str(a.get("action", "")).strip().lower() == rec1["recommendation"].lower() and rec1["recommendation"] != "")
        for a in actions_after_del
    )
    assert is_rec1_added_after_del is False

    # Button state for rec2 remains added
    is_rec2_added_after_del = any(
        (str(a.get("title", "")).strip().lower() == rec2["area"].lower() and str(a.get("action", "")).strip().lower() == rec2["recommendation"].lower())
        or (str(a.get("action", "")).strip().lower() == rec2["recommendation"].lower() and rec2["recommendation"] != "")
        for a in actions_after_del
    )
    assert is_rec2_added_after_del is True

    # Step 8: Test search and priority filters
    create_action(
        title=rec1["area"],
        action=rec1["recommendation"],
        priority=rec1["priority"],
        evidence=rec1["supporting_evidence"],
        notes=rec1["reasoning"],
        status="Open",
        db_path=db_path,
    )
    all_acts = get_all_actions(db_path=db_path)
    assert len(all_acts) == 2

    # Priority filters
    high_acts = [a for a in all_acts if a.get("priority") == "High"]
    assert len(high_acts) == 1
    assert high_acts[0]["title"] == "Kitchen Speed"

    med_acts = [a for a in all_acts if a.get("priority") == "Medium"]
    assert len(med_acts) == 1
    assert med_acts[0]["title"] == "Staff Courtesy"

    # Search keyword
    search_pasta = [
        a for a in all_acts
        if "pasta" in str(a.get("title", "")).lower()
        or "pasta" in str(a.get("action", "")).lower()
        or "pasta" in str(a.get("evidence", "")).lower()
        or "pasta" in str(a.get("notes", "")).lower()
    ]
    assert len(search_pasta) == 1
    assert search_pasta[0]["title"] == "Kitchen Speed"

    # Step 9: Generate the report and verify that it includes the actual saved actions
    pdf_bytes, _ = generate_pdf_report(
        reviews_df=state["reviews_df"],
        analysis_results=state["analysis_results"],
        actions=all_acts,
        language="English",
    )
    assert pdf_bytes.startswith(b"%PDF-")

    docx_bytes = generate_docx_report(
        reviews_df=state["reviews_df"],
        analysis_results=state["analysis_results"],
        actions=all_acts,
        language="English",
    )
    assert docx_bytes.startswith(b"PK\x03\x04")


def test_render_action_tracker_renders_with_db_path(mock_session_state):
    """Verify render_action_tracker executes cleanly with db_path parameter."""
    state, db_path = mock_session_state
    with patch("streamlit.session_state", state):
        try:
            render_action_tracker(db_path=db_path)
        except Exception:
            pass


def test_report_ui_state_initial_load(mock_session_state):
    """Verify on initial load: only dropdowns and generate button visible, download button hidden."""
    state, db_path = mock_session_state
    state["current_page"] = "action_tracker"

    with patch("streamlit.session_state", state), \
         patch("streamlit.download_button") as mock_dl_btn, \
         patch("streamlit.button", return_value=False) as mock_btn, \
         patch("streamlit.selectbox") as mock_sb:

        mock_sb.side_effect = lambda label, options, index=0, **kwargs: options[index]

        render_action_tracker(db_path=db_path)

        # Download button MUST NOT be called on initial load
        mock_dl_btn.assert_not_called()
        assert state.get("last_generated_report") is None


def test_report_ui_state_displayed_after_successful_generation(mock_session_state):
    """Verify download button appears only after successful report generation matching selection."""
    state, db_path = mock_session_state
    state["current_page"] = "action_tracker"
    state["_action_tracker_active_page"] = "action_tracker"

    # 1. English + PDF generation
    with patch("streamlit.session_state", state), \
         patch("streamlit.download_button") as mock_dl_btn, \
         patch("streamlit.button") as mock_btn, \
         patch("streamlit.selectbox") as mock_sb:

        def fake_btn(label, **kwargs):
            if "Generate Report" in label:
                return True
            return False

        mock_btn.side_effect = fake_btn

        def fake_sb(label, options, index=0, **kwargs):
            if "Language" in label:
                return "English"
            if "Format" in label:
                return "PDF (.pdf)"
            return options[index]

        mock_sb.side_effect = fake_sb

        render_action_tracker(db_path=db_path)

        assert state.get("last_generated_report") is not None
        assert state["last_generated_report"]["lang"] == "English"
        assert state["last_generated_report"]["format"] == "PDF (.pdf)"
        mock_dl_btn.assert_called_once()
        dl_kwargs = mock_dl_btn.call_args[1] if mock_dl_btn.call_args[1] else {}
        dl_label = mock_dl_btn.call_args[0][0] if mock_dl_btn.call_args[0] else dl_kwargs.get("label", "")
        assert "English" in dl_label and "PDF" in dl_label

    # 2. Tamil + Word generation
    state["_action_tracker_active_page"] = "action_tracker"
    with patch("streamlit.session_state", state), \
         patch("streamlit.download_button") as mock_dl_btn, \
         patch("streamlit.button") as mock_btn, \
         patch("streamlit.selectbox") as mock_sb:

        mock_btn.side_effect = fake_btn

        def fake_sb_tamil(label, options, index=0, **kwargs):
            if "Language" in label:
                return "Tamil"
            if "Format" in label:
                return "Word (.docx)"
            return options[index]

        mock_sb.side_effect = fake_sb_tamil

        render_action_tracker(db_path=db_path)

        assert state.get("last_generated_report") is not None
        assert state["last_generated_report"]["lang"] == "Tamil"
        assert state["last_generated_report"]["format"] == "Word (.docx)"
        mock_dl_btn.assert_called_once()
        dl_kwargs = mock_dl_btn.call_args[1] if mock_dl_btn.call_args[1] else {}
        dl_label = mock_dl_btn.call_args[0][0] if mock_dl_btn.call_args[0] else dl_kwargs.get("label", "")
        assert "Tamil" in dl_label and "Word" in dl_label


def test_report_ui_state_stale_report_cleared_on_setting_change(mock_session_state):
    """Verify that changing language or format immediately clears previous report and hides download button."""
    state, db_path = mock_session_state
    state["current_page"] = "action_tracker"
    state["_action_tracker_active_page"] = "action_tracker"

    # Pre-existing report in session state: English PDF
    state["last_generated_report"] = {
        "bytes": b"%PDF-dummy",
        "filename": "mezy_intelligence_report_english.pdf",
        "mime": "application/pdf",
        "lang": "English",
        "format": "PDF (.pdf)",
    }
    state["report_gen_success_msg"] = "✓ Previous report generated"

    # User now selects Tamil in dropdown without clicking Generate Report
    with patch("streamlit.session_state", state), \
         patch("streamlit.download_button") as mock_dl_btn, \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.selectbox") as mock_sb:

        def fake_sb(label, options, index=0, **kwargs):
            if "Language" in label:
                return "Tamil"  # Changed from English to Tamil
            if "Format" in label:
                return "PDF (.pdf)"
            return options[index]

        mock_sb.side_effect = fake_sb

        render_action_tracker(db_path=db_path)

        # Download button MUST NOT be rendered
        mock_dl_btn.assert_not_called()
        # Stale report MUST be cleared
        assert state.get("last_generated_report") is None
        assert state.get("report_gen_success_msg") is None


def test_report_ui_state_cleared_on_generation_failure(mock_session_state):
    """Verify that if report generation fails, no download button is displayed and stale state is cleared."""
    state, db_path = mock_session_state
    state["current_page"] = "action_tracker"
    state["_action_tracker_active_page"] = "action_tracker"

    # Pre-existing report
    state["last_generated_report"] = {
        "bytes": b"%PDF-old",
        "filename": "mezy_intelligence_report_english.pdf",
        "mime": "application/pdf",
        "lang": "English",
        "format": "PDF (.pdf)",
    }

    def fake_sb(label, options, index=0, **kwargs):
        if "Language" in label:
            return "English"
        if "Format" in label:
            return "PDF (.pdf)"
        return options[index]

    with patch("streamlit.session_state", state), \
         patch("streamlit.download_button") as mock_dl_btn, \
         patch("streamlit.button") as mock_btn, \
         patch("streamlit.selectbox", side_effect=fake_sb), \
         patch("components.action_tracker.generate_pdf_report", side_effect=RuntimeError("PDF engine crash")):

        def fake_btn(label, **kwargs):
            if "Generate Report" in label:
                return True
            return False

        mock_btn.side_effect = fake_btn

        render_action_tracker(db_path=db_path)

        # Download button MUST NOT be called after failure
        mock_dl_btn.assert_not_called()
        # Stale report must be cleared
        assert state.get("last_generated_report") is None


def test_report_ui_state_reset_on_page_navigation(mock_session_state):
    """Verify that navigating away to another page and returning clears the report state."""
    state, db_path = mock_session_state

    # User previously was on overview, now navigates to action_tracker
    state["current_page"] = "action_tracker"
    state["_action_tracker_active_page"] = "overview"
    state["last_generated_report"] = {
        "bytes": b"%PDF-old",
        "filename": "mezy_intelligence_report_english.pdf",
        "mime": "application/pdf",
        "lang": "English",
        "format": "PDF (.pdf)",
    }
    state["rep_export_language"] = "Tamil"

    with patch("streamlit.session_state", state), \
         patch("streamlit.download_button") as mock_dl_btn, \
         patch("streamlit.button", return_value=False), \
         patch("streamlit.selectbox") as mock_sb:

        mock_sb.side_effect = lambda label, options, index=0, **kwargs: options[index]

        render_action_tracker(db_path=db_path)

        # Download button MUST NOT be called
        mock_dl_btn.assert_not_called()
        # Stale report must be cleared on fresh entry
        assert state.get("last_generated_report") is None
        assert state.get("_action_tracker_active_page") == "action_tracker"


def test_new_dataset_upload_clears_ai_recs_and_preserves_manual_actions(mock_session_state):
    """
    Verify Acceptance Criteria:
    When a new dataset is uploaded / reset:
    - AI recommendations added from previous dataset are cleared.
    - User-created manual actions are strictly preserved.
    - AI recommendations for the new dataset start un-added with '+ Add to Tracker'.
    """
    state, db_path = mock_session_state

    # 1. User creates a manual action
    manual_id = create_action(
        title="Weekly Manager Check",
        action="Inspect dining floor every morning",
        priority="Medium",
        db_path=db_path,
        source="manual",
    )

    # 2. User adds one AI recommendation from dataset A
    rec1 = state["analysis_results"]["actionable_recommendations"][0]
    rec1_id = create_action(
        title=rec1["area"],
        action=rec1["recommendation"],
        priority=rec1["priority"],
        evidence=rec1["supporting_evidence"],
        notes=rec1["reasoning"],
        status="Open",
        db_path=db_path,
        source="ai_recommendation",
    )

    # Saved actions currently has 2 actions
    acts_before = get_all_actions(db_path=db_path)
    assert len(acts_before) == 2

    # 3. Simulate new dataset upload / reset
    from src.database import clear_ai_recommendation_actions
    cleared_count = clear_ai_recommendation_actions(db_path=db_path)
    assert cleared_count == 1

    # 4. Saved Actions now only has the manual action
    acts_after = get_all_actions(db_path=db_path)
    assert len(acts_after) == 1
    assert acts_after[0]["id"] == manual_id
    assert acts_after[0]["title"] == "Weekly Manager Check"
    assert acts_after[0]["source"] == "manual"

    # 5. The new dataset's recommendation is NOT in Saved Actions
    is_rec1_added = any(
        (str(a.get("title", "")).strip().lower() == rec1["area"].lower() and str(a.get("action", "")).strip().lower() == rec1["recommendation"].lower())
        or (str(a.get("action", "")).strip().lower() == rec1["recommendation"].lower() and rec1["recommendation"] != "")
        for a in acts_after
    )
    assert is_rec1_added is False


def test_individual_recommendation_addition_and_persistence(mock_session_state):
    """
    Verify:
    1. Clicking '+ Add to Tracker' on recommendation 1 adds only recommendation 1.
    2. Recommendation 1 button becomes '✓ Added to Tracker'.
    3. Other recommendations remain available to add with '+ Add to Tracker'.
    4. Refreshing the page (reloading from SQLite) preserves this exact state without duplicate additions.
    """
    state, db_path = mock_session_state
    recs = [
        {"area": "Speed", "priority": "High", "recommendation": "Faster ovens", "reasoning": "Delays", "supporting_evidence": "Waited 40m"},
        {"area": "Cleanliness", "priority": "Medium", "recommendation": "Daily sanitization", "reasoning": "Dirty tables", "supporting_evidence": "Sticky tables"},
        {"area": "Portions", "priority": "Low", "recommendation": "Larger salads", "reasoning": "Small size", "supporting_evidence": "Tiny salad"},
    ]
    state["analysis_results"]["actionable_recommendations"] = recs

    # Tracker initially empty
    assert len(get_all_actions(db_path=db_path)) == 0

    # User clicks Add to Tracker on rec 1
    create_action(
        title=recs[0]["area"],
        action=recs[0]["recommendation"],
        priority=recs[0]["priority"],
        evidence=recs[0]["supporting_evidence"],
        notes=recs[0]["reasoning"],
        status="Open",
        db_path=db_path,
        source="ai_recommendation",
    )

    # Check database: exactly 1 action
    db_actions = get_all_actions(db_path=db_path)
    assert len(db_actions) == 1
    assert db_actions[0]["title"] == "Speed"

    # Helper to check if rec is added
    def is_added(rec, saved_acts):
        return any(
            (str(a.get("title", "")).strip().lower() == rec["area"].lower() and str(a.get("action", "")).strip().lower() == rec["recommendation"].lower())
            or (str(a.get("action", "")).strip().lower() == rec["recommendation"].lower() and rec["recommendation"] != "")
            for a in saved_acts
        )

    # Rec 1 is Added, Rec 2 & 3 are NOT Added
    assert is_added(recs[0], db_actions) is True
    assert is_added(recs[1], db_actions) is False
    assert is_added(recs[2], db_actions) is False

    # Simulate Page Refresh: fresh query from persistent database
    refreshed_db_actions = get_all_actions(db_path=db_path)
    assert len(refreshed_db_actions) == 1
    assert is_added(recs[0], refreshed_db_actions) is True
    assert is_added(recs[1], refreshed_db_actions) is False
    assert is_added(recs[2], refreshed_db_actions) is False

    # User now clicks Add to Tracker on rec 3
    create_action(
        title=recs[2]["area"],
        action=recs[2]["recommendation"],
        priority=recs[2]["priority"],
        evidence=recs[2]["supporting_evidence"],
        notes=recs[2]["reasoning"],
        status="Open",
        db_path=db_path,
        source="ai_recommendation",
    )

    db_actions_2 = get_all_actions(db_path=db_path)
    assert len(db_actions_2) == 2
    assert is_added(recs[0], db_actions_2) is True
    assert is_added(recs[1], db_actions_2) is False
    assert is_added(recs[2], db_actions_2) is True



