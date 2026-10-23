"""
components/action_tracker.py
-----------------------------
Action Tracker page with SQLite persistence, AI recommendations import,
manual action creation, saved action management, and executive report downloads.

Milestone 6 implementation:
  • Structured page order:
      1. Action Tracker heading & summary cards
      2. AI Recommendations (grounded, duplicate-protected)
      3. Create New Action (manual form with validation)
      4. Saved Actions & action management (edit, status, delete confirmation)
      5. Download Business Report (English / Tamil, PDF / Word)
  • Parameterized SQLite queries via src/database.py.
  • Streamlit 1.66+ compatible widgets (using `height` instead of `rows`).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import streamlit as st

from src.database import (
    action_exists,
    clear_ai_recommendation_actions,
    create_action,
    delete_action,
    get_action_by_id,
    get_action_statistics,
    get_all_actions,
    update_action,
    update_action_status_and_notes,
)
from src.report_generator import generate_docx_report, generate_pdf_report
from src.translations import t


def render_action_tracker(db_path: Optional[Union[Path, str]] = None) -> None:
    """Render the spacious, structured Action Tracker page and report export options."""
    lang = st.session_state.get("language", "English")

    # Reset report export state on fresh entry to Action Tracker page
    current_page = st.session_state.get("current_page", "action_tracker")
    if st.session_state.get("_action_tracker_active_page") != current_page:
        st.session_state["_action_tracker_active_page"] = current_page
        st.session_state.pop("last_generated_report", None)
        st.session_state.pop("report_gen_success_msg", None)
        st.session_state.pop("rep_export_language", None)
        st.session_state.pop("rep_export_format", None)

    # 1. Retrieve all saved actions from persistent storage first
    load_error: Optional[str] = None
    try:
        all_saved_actions = get_all_actions(db_path=db_path)
    except Exception as ex:
        all_saved_actions = []
        load_error = str(ex)

    # ═════════════════════════════════════════════════════════════════════════
    # 1. Page Header & Summary Cards
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem;">
          <h2 style="font-family: 'Plus Jakarta Sans', Sora, sans-serif; font-weight: 700; color: #0f172a; margin: 0 0 0.35rem 0; font-size: 1.65rem; letter-spacing: -0.02em;">
            ✅ {t("action_tracker_title", lang)}
          </h2>
          <p style="color: #64748b; font-size: 0.95rem; margin: 0; line-height: 1.5;">
            {t("action_tracker_subtitle", lang)}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if load_error:
        st.error(f"Error loading saved actions: {load_error}")

    kpi_col, _ = st.columns([1.6, 4.4])
    with kpi_col:
        st.markdown(
            f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.1rem 1.4rem; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
              <div style="font-size: 1.85rem; font-weight: 700; color: #0f172a; line-height: 1.2;">{len(all_saved_actions)}</div>
              <div style="font-size: 0.8rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.35rem;">{t("stat_total_actions", lang)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 1.75rem;'></div>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # 2. AI Recommendations
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown(
        """
        <div style="margin-bottom: 0.75rem;">
          <h3 style="font-family: 'Plus Jakarta Sans', Sora, sans-serif; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0; font-size: 1.25rem;">
            💡 AI Recommendations
          </h3>
          <p style="color: #64748b; font-size: 0.88rem; margin: 0;">
            Prioritized operational suggestions derived directly from verified customer feedback.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "action_tracker_feedback" in st.session_state:
        fb_msg, fb_type = st.session_state.pop("action_tracker_feedback")
        if fb_type == "success":
            st.success(fb_msg)
        elif fb_type == "info":
            st.info(fb_msg)
        elif fb_type == "error":
            st.error(fb_msg)

    analysis_results = st.session_state.get("analysis_results")
    if analysis_results and isinstance(analysis_results, dict):
        recommendations = analysis_results.get("actionable_recommendations", [])
        if recommendations:
            for idx, rec in enumerate(recommendations):
                area = str(rec.get("area", "Improvement Area")).strip()
                p_val = str(rec.get("priority", "Medium")).capitalize()
                if p_val not in ["High", "Medium", "Low"]:
                    p_val = "Medium"
                action_text = str(rec.get("recommendation", "")).strip()
                evidence_text = str(rec.get("supporting_evidence", "")).strip()
                notes_text = str(rec.get("reasoning", "")).strip()

                # Determine if this recommendation is currently saved in persistent storage
                is_already_added = any(
                    (
                        str(a.get("title", "")).strip().lower() == area.lower()
                        and str(a.get("action", "")).strip().lower() == action_text.lower()
                    )
                    or (
                        str(a.get("action", "")).strip().lower() == action_text.lower()
                        and action_text != ""
                    )
                    for a in all_saved_actions
                )

                p_color = "#dc2626" if p_val == "High" else ("#d97706" if p_val == "Medium" else "#2563eb")
                p_bg = "#fef2f2" if p_val == "High" else ("#fffbeb" if p_val == "Medium" else "#eff6ff")
                p_label = t(f"priority_{p_val.lower()}", lang)

                with st.container(border=True):
                    # Header: Title + Distinct Priority Badge
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; margin-bottom: 0.75rem;">
                          <div style="font-weight: 700; font-size: 1.08rem; color: #0f172a; line-height: 1.35;">
                            {area}
                          </div>
                          <span style="font-size: 0.75rem; font-weight: 700; color: {p_color}; background: {p_bg}; border: 1px solid {p_color}30; padding: 3px 10px; border-radius: 6px; text-transform: uppercase; letter-spacing: 0.04em; white-space: nowrap;">
                            {p_label}
                          </span>
                        </div>
                        <div style="font-size: 0.96rem; color: #1e293b; line-height: 1.6; margin-bottom: 0.9rem;">
                          {action_text}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if notes_text:
                        st.markdown(
                            f"""
                            <div style="margin-bottom: 0.9rem; line-height: 1.6; font-size: 0.88rem; color: #334155;">
                              <span style="display: inline-block; font-weight: 700; background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 4px; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; margin-right: 8px;">Reasoning</span>
                              <span>{notes_text}</span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    if evidence_text:
                        st.markdown(
                            f"""
                            <div style="border-left: 3px solid #6366f1; background: #f8fafc; padding: 0.75rem 1rem; border-radius: 0 6px 6px 0; margin-top: 0.9rem; margin-bottom: 1rem;">
                              <span style="font-size: 0.75rem; font-weight: 700; color: #4338ca; text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 0.35rem;">Customer Evidence:</span>
                              <div style="font-size: 0.88rem; color: #334155; font-style: italic; line-height: 1.6;">"{evidence_text}"</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Action Button Row (aligned right, consistent standard application button design)
                    st.markdown("<hr style='border: none; border-top: 1px solid #f1f5f9; margin: 0.75rem 0 0.85rem 0;' />", unsafe_allow_html=True)
                    col_rec_space, col_rec_action = st.columns([3.4, 1.6], gap="small")
                    with col_rec_action:
                        if is_already_added:
                            st.button(
                                "✓ Added to Tracker",
                                key=f"rec_added_btn_{idx}",
                                disabled=True,
                                use_container_width=True,
                            )
                        else:
                            if st.button(
                                "+ Add to Tracker",
                                key=f"rec_add_btn_{idx}",
                                use_container_width=True,
                            ):
                                try:
                                    # Prevent duplicate addition against persistent storage
                                    already_saved = any(
                                        (
                                            str(a.get("title", "")).strip().lower() == area.lower()
                                            and str(a.get("action", "")).strip().lower() == action_text.lower()
                                        )
                                        or (
                                            str(a.get("action", "")).strip().lower() == action_text.lower()
                                            and action_text != ""
                                        )
                                        for a in all_saved_actions
                                    )
                                    if not already_saved:
                                        create_action(
                                            title=area,
                                            action=action_text,
                                            priority=p_val,
                                            evidence=evidence_text,
                                            notes=notes_text,
                                            status="Open",
                                            db_path=db_path,
                                            source="ai_recommendation",
                                        )
                                        # Reset priority/search filters so the newly added action is immediately visible
                                        st.session_state["act_filter_priority"] = "All"
                                        st.session_state["act_filter_search"] = ""
                                        st.session_state["action_tracker_feedback"] = (f"Added '{area}' to Action Tracker!", "success")
                                    else:
                                        st.session_state["action_tracker_feedback"] = (f"'{area}' is already in Action Tracker.", "info")
                                    st.rerun()
                                except Exception as ex:
                                    st.session_state["action_tracker_feedback"] = (f"Failed to add action: {ex}", "error")
                                    st.rerun()

                st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
        else:
            st.info(
                "No recommendations found in the current analysis. Run review analysis with your customer feedback to generate operational insights."
            )
    else:
        st.info(
            "AI recommendations will appear here after analyzing your customer reviews. Return to **Home** to attach review data and start analysis."
        )

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # 3. Create New Action (Manual)
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"""
        <div style="margin-bottom: 0.75rem;">
          <h3 style="font-family: 'Plus Jakarta Sans', Sora, sans-serif; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0; font-size: 1.25rem;">
            ➕ {t("create_action_heading", lang)}
          </h3>
          <p style="color: #64748b; font-size: 0.88rem; margin: 0;">
            Add custom operational tasks and improvements independently of AI recommendations.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("➕ Add New Action Item", expanded=(len(all_saved_actions) == 0)):
        with st.form("create_action_form", clear_on_submit=True):
            col_t1, col_t2 = st.columns([3, 1], gap="medium")
            with col_t1:
                new_title = st.text_input(
                    f"{t('field_title', lang)} *",
                    placeholder="e.g. Reduce dinner peak wait times",
                )
            with col_t2:
                new_priority = st.selectbox(
                    t("field_priority", lang),
                    options=["High", "Medium", "Low"],
                    index=1,
                )

            new_action = st.text_area(
                f"{t('field_action', lang)} *",
                placeholder="e.g. Introduce pre-portioned starters and order ticket display in kitchen.",
                height=85,
            )

            st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)
            col_sub1, col_sub2 = st.columns(2, gap="medium")
            with col_sub1:
                new_evidence = st.text_area(
                    t("field_evidence", lang),
                    placeholder='e.g. Customer quote: "Starters took over 40 minutes on Saturday evening."',
                    height=75,
                )
            with col_sub2:
                new_notes = st.text_area(
                    t("field_notes", lang),
                    placeholder="e.g. Assign to head chef; check progress next Tuesday.",
                    height=75,
                )

            st.markdown("<div style='height: 0.65rem;'></div>", unsafe_allow_html=True)
            submit_btn = st.form_submit_button(
                t("btn_save_action", lang),
                type="primary",
            )
            if submit_btn:
                if not new_title.strip():
                    st.error("Please enter an issue title.")
                elif not new_action.strip():
                    st.error("Please enter a suggested action.")
                else:
                    try:
                        create_action(
                            title=new_title,
                            action=new_action,
                            priority=new_priority,
                            evidence=new_evidence,
                            notes=new_notes,
                            status="Open",
                            db_path=db_path,
                            source="manual",
                        )
                        st.session_state["act_filter_priority"] = "All"
                        st.session_state["act_filter_search"] = ""
                        st.session_state["action_tracker_feedback"] = ("Action created and saved successfully in SQLite database!", "success")
                        st.rerun()
                    except Exception as err:
                        st.error(f"Error saving action: {err}")

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # 4. Saved Actions & Action Management
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown(
        """
        <div style="margin-bottom: 0.75rem;">
          <h3 style="font-family: 'Plus Jakarta Sans', Sora, sans-serif; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0; font-size: 1.25rem;">
            📋 Saved Actions & Progress
          </h3>
          <p style="color: #64748b; font-size: 0.88rem; margin: 0;">
            Track, prioritize, and manage ongoing and completed operational improvements.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filter toolbar (Status dropdown removed)
    col_flt_prio, col_search = st.columns([1.5, 3.5], gap="medium")
    with col_flt_prio:
        priority_filter = st.selectbox(
            "Filter by Priority",
            options=["All", "High", "Medium", "Low"],
            key="act_filter_priority",
        )
    with col_search:
        search_kw = st.text_input(
            "Search actions",
            placeholder="Search title, action, evidence, notes...",
            key="act_filter_search",
        )

    # Filter the retrieved saved actions
    filtered_actions = all_saved_actions
    if priority_filter and priority_filter != "All":
        filtered_actions = [a for a in filtered_actions if a.get("priority") == priority_filter]
    if search_kw and search_kw.strip():
        kw = search_kw.strip().lower()
        filtered_actions = [
            a for a in filtered_actions
            if kw in str(a.get("title", "")).lower()
            or kw in str(a.get("action", "")).lower()
            or kw in str(a.get("evidence", "")).lower()
            or kw in str(a.get("notes", "")).lower()
        ]

    if not all_saved_actions:
        st.info("No saved actions yet. Use '+ Add to Tracker' on an AI recommendation above or create a new action.")
    elif not filtered_actions:
        st.info("No saved actions match the selected filters. Try changing or clearing your priority and search filters.")
    else:
        for act in filtered_actions:
            act_id = act["id"]
            prio = act["priority"]

            p_color = "#dc2626" if prio == "High" else ("#d97706" if prio == "Medium" else "#2563eb")
            p_bg = "#fef2f2" if prio == "High" else ("#fffbeb" if prio == "Medium" else "#eff6ff")

            with st.container(border=True):
                # Header row: Title + Priority badge (Status badge removed)
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                      <div>
                        <span style="font-weight: 700; font-size: 1.06rem; color: #0f172a;">{act['title']}</span>
                        <span style="font-size: 0.75rem; color: #94a3b8; margin-left: 0.5rem;">#{act_id}</span>
                      </div>
                      <span style="font-size: 0.75rem; font-weight: 700; color: {p_color}; background: {p_bg}; border: 1px solid {p_color}30; padding: 3px 10px; border-radius: 6px; text-transform: uppercase; letter-spacing: 0.04em;">
                        {prio}
                      </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Suggested action text
                st.markdown(
                    f"<div style='font-size: 0.95rem; color: #1e293b; line-height: 1.6; margin-bottom: 0.85rem;'>{act['action']}</div>",
                    unsafe_allow_html=True,
                )

                # Evidence quote (if present)
                if act.get("evidence"):
                    st.markdown(
                        f"""
                        <div style="border-left: 3px solid #6366f1; background: #f8fafc; padding: 0.75rem 1rem; border-radius: 0 6px 6px 0; margin-bottom: 0.85rem;">
                          <span style="font-size: 0.75rem; font-weight: 700; color: #4338ca; text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 0.25rem;">Customer Evidence:</span>
                          <div style="font-size: 0.88rem; color: #334155; font-style: italic; line-height: 1.6;">"{act['evidence']}"</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Notes (if present)
                if act.get("notes"):
                    st.markdown(
                        f"""
                        <div style="font-size: 0.88rem; color: #475569; line-height: 1.55; margin-bottom: 0.85rem; background: #f8fafc; padding: 0.6rem 0.95rem; border-radius: 6px; border: 1px solid #e2e8f0;">
                          <strong style="color: #334155;">Notes:</strong> {act['notes']}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Action controls row: Edit Details and Delete buttons (Status dropdown removed from card)
                st.markdown("<hr style='border: none; border-top: 1px solid #f1f5f9; margin: 0.5rem 0 0.75rem 0;' />", unsafe_allow_html=True)
                col_ctrl_space, col_ctrl_edit, col_ctrl_del = st.columns([3.4, 1.2, 0.9], gap="small")

                with col_ctrl_edit:
                    edit_key = f"toggle_edit_{act_id}"
                    if st.button("✏️ Edit Details", key=edit_key, use_container_width=True):
                        st.session_state[f"editing_{act_id}"] = not st.session_state.get(f"editing_{act_id}", False)
                        st.rerun()

                with col_ctrl_del:
                    del_btn_key = f"del_btn_{act_id}"
                    if st.button("🗑️ Delete", key=del_btn_key, use_container_width=True):
                        st.session_state[f"confirm_delete_{act_id}"] = True
                        st.rerun()

                # Delete Confirmation Dialog Box
                if st.session_state.get(f"confirm_delete_{act_id}", False):
                    st.warning(f"⚠️ Are you sure you want to permanently delete action #{act_id}: '{act['title']}'?")
                    col_cdel1, col_cdel2 = st.columns(2)
                    with col_cdel1:
                        if st.button("✓ Yes, Confirm Delete", key=f"yes_del_{act_id}", type="primary", use_container_width=True):
                            try:
                                delete_action(act_id, db_path=db_path)
                                st.session_state.pop(f"confirm_delete_{act_id}", None)
                                st.session_state["action_tracker_feedback"] = (f"Action #{act_id} deleted successfully.", "success")
                                st.rerun()
                            except Exception as ex:
                                st.session_state["action_tracker_feedback"] = (f"Failed to delete action: {ex}", "error")
                                st.rerun()
                    with col_cdel2:
                        if st.button("Cancel", key=f"cancel_del_{act_id}", use_container_width=True):
                            st.session_state.pop(f"confirm_delete_{act_id}", None)
                            st.rerun()

                # Inline Edit Form (Status selectbox removed, preserving existing status in database)
                if st.session_state.get(f"editing_{act_id}", False):
                    with st.form(f"edit_form_{act_id}"):
                        st.markdown(f"**Editing Action #{act_id}**")
                        e_title = st.text_input("Title", value=act["title"])
                        e_action = st.text_area("Suggested Action", value=act["action"], height=80)
                        e_prio = st.selectbox(
                            "Priority",
                            options=["High", "Medium", "Low"],
                            index=["High", "Medium", "Low"].index(prio),
                        )
                        e_evid = st.text_area("Evidence Quote", value=act.get("evidence", ""), height=70)
                        e_notes = st.text_area("Internal Notes", value=act.get("notes", ""), height=70)

                        col_esub1, col_esub2 = st.columns(2)
                        with col_esub1:
                            if st.form_submit_button("Save Changes", type="primary", use_container_width=True):
                                if not e_title.strip() or not e_action.strip():
                                    st.error("Title and Suggested Action are required.")
                                else:
                                    try:
                                        update_action(
                                            action_id=act_id,
                                            title=e_title,
                                            action=e_action,
                                            priority=e_prio,
                                            status=act.get("status", "Open"),
                                            evidence=e_evid,
                                            notes=e_notes,
                                            db_path=db_path,
                                        )
                                        st.session_state[f"editing_{act_id}"] = False
                                        st.session_state["action_tracker_feedback"] = (f"Action #{act_id} updated successfully!", "success")
                                        st.rerun()
                                    except Exception as ex:
                                        st.error(f"Error updating action: {ex}")
                        with col_esub2:
                            if st.form_submit_button("Cancel", use_container_width=True):
                                st.session_state[f"editing_{act_id}"] = False
                                st.rerun()

                st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # 5. Download Business Report (Dedicated Section at the Bottom)
    # ═════════════════════════════════════════════════════════════════════════
    st.markdown("<div style='height: 3rem;'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 0 0 2rem 0;' />", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
          <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
            <span style="font-size: 1.35rem;">📊</span>
            <h3 style="font-family: 'Plus Jakarta Sans', Sora, sans-serif; font-weight: 700; color: #0f172a; margin: 0; font-size: 1.35rem; letter-spacing: -0.01em;">
              Download Business Report
            </h3>
          </div>
          <p style="color: #64748b; font-size: 0.92rem; margin: 0;">
            Generate publication-ready executive reports combining verified review sentiment analysis and prioritized improvement actions.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        col_rlang, col_rfmt = st.columns(2, gap="large")

        def _on_report_settings_change() -> None:
            st.session_state.pop("last_generated_report", None)
            st.session_state.pop("report_gen_success_msg", None)

        with col_rlang:
            st.markdown("**Step 1 — Choose Report Language**")
            rep_lang = st.selectbox(
                "Report Language",
                options=["English", "Tamil"],
                index=0,
                help="Select report language. Headings and narrative summaries will use the selected language. Original customer review quotes remain verbatim.",
                label_visibility="collapsed",
                key="rep_export_language",
                on_change=_on_report_settings_change,
            )

        with col_rfmt:
            st.markdown("**Step 2 — Choose Download Format**")
            rep_format = st.selectbox(
                "Download Format",
                options=["PDF (.pdf)", "Word (.docx)"],
                index=0,
                help="PDF documents use ReportLab with Tamil Unicode font detection. Word (.docx) documents use python-docx.",
                label_visibility="collapsed",
                key="rep_export_format",
                on_change=_on_report_settings_change,
            )

        # Clear stale report state if current dropdown selections do not match the generated report
        last_rep = st.session_state.get("last_generated_report")
        if last_rep and isinstance(last_rep, dict):
            if last_rep.get("lang") != rep_lang or last_rep.get("format") != rep_format:
                st.session_state.pop("last_generated_report", None)
                st.session_state.pop("report_gen_success_msg", None)
                last_rep = None

        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)
        st.markdown("**Step 3 — Generate and Download**")

        is_generating = st.session_state.get("_report_generating", False)

        gen_btn = st.button(
            "⏳ Generating Report..." if is_generating else "📥 Generate Report",
            type="primary",
            use_container_width=True,
            key="btn_generate_report_exec",
            disabled=is_generating,
        )

        if gen_btn and not is_generating:
            # Clear previous report state immediately to avoid stale downloads
            st.session_state.pop("last_generated_report", None)
            st.session_state.pop("report_gen_success_msg", None)
            last_rep = None

            st.session_state["_report_generating"] = True
            try:
                with st.spinner(f"Generating publication {rep_lang} {rep_format} report from verified review intelligence..."):
                    reviews_df = st.session_state.get("reviews_df")
                    analysis_results = st.session_state.get("analysis_results")
                    all_actions = get_all_actions(db_path=db_path)

                    is_pdf = "PDF" in rep_format
                    ext = "pdf" if is_pdf else "docx"
                    mime_type = (
                        "application/pdf"
                        if is_pdf
                        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                    warning_notice: Optional[str] = None
                    file_bytes: bytes

                    if is_pdf:
                        file_bytes, warning_notice = generate_pdf_report(
                            reviews_df=reviews_df,
                            analysis_results=analysis_results,
                            actions=all_actions,
                            language=rep_lang,
                        )
                    else:
                        file_bytes = generate_docx_report(
                            reviews_df=reviews_df,
                            analysis_results=analysis_results,
                            actions=all_actions,
                            language=rep_lang,
                        )

                    if not file_bytes or len(file_bytes) == 0:
                        raise ValueError("Report generation produced empty content.")

                    if warning_notice:
                        st.warning(f"⚠️ {warning_notice}")

                    # Store generated file in session state only upon successful generation
                    st.session_state["last_generated_report"] = {
                        "bytes": file_bytes,
                        "filename": f"mezy_intelligence_report_{rep_lang.lower()}.{ext}",
                        "mime": mime_type,
                        "lang": rep_lang,
                        "format": rep_format,
                    }
                    st.session_state["report_gen_success_msg"] = (
                        f"✓ {rep_lang} {rep_format} report successfully generated! Click below to download."
                    )
                    last_rep = st.session_state["last_generated_report"]
            except Exception as exp:
                st.session_state.pop("last_generated_report", None)
                st.session_state.pop("report_gen_success_msg", None)
                last_rep = None
                st.error(f"Report generation could not be completed: {exp}")
            finally:
                st.session_state["_report_generating"] = False

        # Render download button strictly only when report exists and matches current selection
        if (
            last_rep
            and isinstance(last_rep, dict)
            and last_rep.get("lang") == rep_lang
            and last_rep.get("format") == rep_format
            and last_rep.get("bytes")
        ):
            success_msg = st.session_state.get("report_gen_success_msg")
            if success_msg:
                st.success(success_msg)
            st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
            st.download_button(
                label=f"⬇ Download {last_rep['lang']} {last_rep['format']} Report",
                data=last_rep["bytes"],
                file_name=last_rep["filename"],
                mime=last_rep["mime"],
                key=f"download_report_ready_btn_{last_rep['lang'].lower()}_{'pdf' if 'PDF' in last_rep['format'] else 'docx'}",
                type="secondary",
                use_container_width=True,
            )
