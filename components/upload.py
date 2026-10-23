"""
components/upload.py
--------------------
Mezy initial screen — Minimal AI Workspace.

Refined according to specification:
  • Official Mezy logo asset positioned at top-left
  • Main heading: "Complexity turned into Simplicity."
      - Softer color for "Complexity turned into "
      - Restrained accent color + italic style for "Simplicity."
  • Supporting description: "Turn customer reviews into clear insights and practical improvements."
  • Left and right subtle line illustrations framing the central content
  • Tasteful overlapping document visual above composer (outlines only, no large "CSV" label)
  • Single integrated chat-style composer:
      - Question input with placeholder: "Upload customer reviews and ask anything..."
      - Subtle CSV attachment button
      - Selected filename indicator with clear remove control
      - Circular dark send button (➔)
  • Bottom supporting text: "Upload customer reviews. Ask any question. Get instant AI insights."
  • Sidebar completely hidden on initial screen; revealed after successful analysis
  • Animated orb loading state during analysis
"""

import base64
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd
import streamlit as st
from components import loading_animation
from src.data_cleaning import (
    find_review_column,
    clean_and_validate_dataframe,
)
from src.database import clear_ai_recommendation_actions
from src.translations import t
from src.review_analysis import analyze_reviews_with_gemini
from src.gemini_service import GeminiServiceError

_ANALYSIS_EXECUTOR = ThreadPoolExecutor(max_workers=2)


@st.cache_data
def _get_asset_b64(filename: str) -> str:
    """Read asset file and cache as base64 string."""
    asset_path = Path(__file__).resolve().parent.parent / "assets" / filename
    if asset_path.exists():
        return base64.b64encode(asset_path.read_bytes()).decode("utf-8")
    return ""


def _css(path: Path) -> str:
    return f"<style>{path.read_text(encoding='utf-8')}</style>" if path.exists() else ""


@st.fragment(run_every=0.5)
def _poll_analysis_monitor() -> None:
    """
    Lightweight background monitor fragment (Issue 2).
    Polls the ThreadPoolExecutor future every 500ms without causing full-page reruns.
    Static elements (logo, left/right illustrations, hero, glowing orb, composer)
    remain completely stable in the DOM with zero flickering.
    """
    fut = st.session_state.get("analysis_future")
    if fut is not None and fut.done():
        try:
            analysis_results = fut.result()
            st.session_state["is_analyzing"] = False
            st.session_state["analysis_future"] = None

            # Only display results if user has not clicked Stop
            if not st.session_state.get("cancel_requested", False):
                st.session_state.reviews_df = st.session_state.get("active_cleaned_df")
                rep = st.session_state.get("active_report")
                st.session_state.data_quality_report = rep.to_dict() if rep else {}
                st.session_state.user_question = st.session_state.get("active_question", "")
                st.session_state.analysis_done = True
                st.session_state.analysis_results = analysis_results
                current_lang = st.session_state.get("language", "English")
                st.session_state["analysis_cache"] = {current_lang: analysis_results}
                st.session_state.current_page = "overview"
                st.rerun(scope="app")
        except GeminiServiceError as gerr:
            st.session_state["is_analyzing"] = False
            st.session_state["analysis_future"] = None
            st.session_state["analysis_done"] = False
            st.session_state["reviews_df"] = None
            st.session_state["analysis_results"] = None
            st.session_state["analysis_error_msg"] = str(gerr)
            st.rerun(scope="app")
        except Exception as exc:
            st.session_state["is_analyzing"] = False
            st.session_state["analysis_future"] = None
            st.session_state["analysis_done"] = False
            st.session_state["reviews_df"] = None
            st.session_state["analysis_results"] = None
            st.session_state["analysis_error_msg"] = f"AI review analysis could not be completed: {exc}"
            st.rerun(scope="app")


def render_home() -> None:
    """Render the minimal AI chat workspace on the initial screen."""
    css_path = Path(__file__).resolve().parent.parent / "assets" / "styles.css"
    if css_path.exists():
        st.markdown(_css(css_path), unsafe_allow_html=True)

    # Marker class to hide sidebar cleanly via CSS while on initial screen before analysis
    if not st.session_state.get("analysis_done", False):
        st.markdown('<div class="mezy-initial-screen"></div>', unsafe_allow_html=True)
    if st.session_state.get("is_analyzing", False):
        st.markdown('<div class="mezy-analyzing-screen"></div>', unsafe_allow_html=True)

    # Any error message from background analysis
    if st.session_state.get("analysis_error_msg"):
        st.error(st.session_state.pop("analysis_error_msg"))

    # ── Top Bar: Official Mezy Logo at Top-Left ─────────────────────────
    logo_b64 = _get_asset_b64("mezy_logo_alpha.png")
    if not logo_b64:
        logo_b64 = _get_asset_b64("mezy_logo_trimmed.png")
    if not logo_b64:
        logo_b64 = _get_asset_b64("mezy_logo.png")

    st.markdown(
        f"""
        <div class="top-brand-bar">
          <img src="data:image/png;base64,{logo_b64}" class="home-brand-logo" alt="Mezy" />
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Main Content Framed by Left and Right Illustrations ─────────────
    col_left, col_center, col_right = st.columns([1.1, 3.4, 1.1], vertical_alignment="center")

    # Left decorative illustration
    with col_left:
        left_b64 = _get_asset_b64("illustration_left_alpha.png")
        if not left_b64:
            left_b64 = _get_asset_b64("illustration_left.png")
        if left_b64:
            st.markdown(
                f"""
                <div class="side-illustration side-illustration-left">
                  <img src="data:image/png;base64,{left_b64}" alt="" class="side-deco-img" />
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Right decorative illustration
    with col_right:
        right_b64 = _get_asset_b64("illustration_right_alpha.png")
        if not right_b64:
            right_b64 = _get_asset_b64("illustration_right.png")
        if right_b64:
            st.markdown(
                f"""
                <div class="side-illustration side-illustration-right">
                  <img src="data:image/png;base64,{right_b64}" alt="" class="side-deco-img" />
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Central AI Workspace
    with col_center:
        # ── Hero Section ──────────────────────────────────────────────
        st.markdown(
            """
            <div class="mezy-minimal-hero">
              <h1 class="mezy-headline">
                Complexity<br>
                turned into <span class="mezy-serif-word">Simplicity.</span>
              </h1>
              <p class="mezy-description">
                Turn customer reviews into clear insights and practical improvements.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # State variables for composer and analysis control
        is_analyzing = st.session_state.get("is_analyzing", False)
        comp_v = st.session_state.get("composer_version", 0)

        # ── Document Visual: 3 Overlapping Sheets (Shown only in idle state, not during loading) ──
        if not is_analyzing:
            st.markdown(
                """
                <div class="composer-docs-anchor">
                  <div class="doc-stack">
                    <div class="doc-sheet doc-sheet-1">
                      <div class="doc-line doc-line-title"></div>
                      <div class="doc-line doc-line-lg"></div>
                      <div class="doc-line doc-line-md"></div>
                      <div class="doc-line doc-line-sm"></div>
                    </div>
                    <div class="doc-sheet doc-sheet-2">
                      <div class="doc-line doc-line-title"></div>
                      <div class="doc-line doc-line-lg"></div>
                      <div class="doc-line doc-line-md"></div>
                      <div class="doc-line doc-line-lg"></div>
                    </div>
                    <div class="doc-sheet doc-sheet-3">
                      <div class="doc-line doc-line-title"></div>
                      <div class="doc-line doc-line-md"></div>
                      <div class="doc-line doc-line-sm"></div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Brief notification if an active analysis was stopped
        if st.session_state.get("analysis_stopped_notice", False):
            st.session_state["analysis_stopped_notice"] = False
            st.info("Analysis was stopped. You can submit another file whenever you are ready.")

        # Animated glowing orb displayed smoothly during analysis (pure CSS, no repeated DOM replacement)
        if is_analyzing:
            cur_lang = st.session_state.get("language", "English")
            loading_stages = [
                t("loading_preparing", cur_lang),
                t("loading_insights", cur_lang),
                t("loading_dashboard", cur_lang),
            ]
            loading_animation.show_inline(status=loading_stages[0], stages=loading_stages)

        # ── Integrated Chat Composer Card ─────────────────────────────
        with st.container(border=True):
            # Question text input (cleared immediately after submission via dynamic key)
            question = st.text_input(
                "Ask anything",
                value="",
                placeholder="Upload customer reviews and ask anything...",
                key=f"composer_prompt_{comp_v}",
                label_visibility="collapsed",
                disabled=is_analyzing,
            )

            # Bottom toolbar: CSV Attachment (Left) + Circular Send / Stop Button (Right)
            bar_col_left, bar_col_right = st.columns([5.0, 0.8], vertical_alignment="center")

            with bar_col_left:
                if not is_analyzing:
                    uploaded_file = st.file_uploader(
                        label="Attach CSV",
                        type=["csv"],
                        key=f"file_upload_{comp_v}",
                        help="Upload a reviews CSV (e.g. columns named Review, Feedback, Comments, or review_text)",
                        label_visibility="collapsed",
                    )
                else:
                    uploaded_file = None
                    st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)

            with bar_col_right:
                if is_analyzing:
                    stop_clicked = st.button(
                        "■",
                        key="stop_btn",
                        type="primary",
                        help="Stop analysis",
                    )
                    send_clicked = False
                else:
                    send_clicked = st.button(
                        "➔",
                        key="send_btn",
                        type="primary",
                        help="Analyse reviews",
                    )
                    stop_clicked = False

        # ── Exact Supporting Text beneath composer ────────────────────
        st.markdown(
            """
            <p class="composer-subtext">
              Upload customer reviews. Ask any question. Get instant AI insights.
            </p>
            """,
            unsafe_allow_html=True,
        )

        # ── Review Column Selection if Column Name is Unclear ─────────
        chosen_review_col = None
        parsed_df = None

        if uploaded_file is not None and not is_analyzing:
            try:
                uploaded_file.seek(0)
                parsed_df = pd.read_csv(uploaded_file)
                cols = [str(c) for c in parsed_df.columns]
                matched_col, candidates = find_review_column(cols)

                if matched_col:
                    chosen_review_col = matched_col
                elif candidates:
                    st.markdown(
                        """
                        <div style="margin-top: 0.85rem; padding: 0.75rem 1rem; background: rgba(255,255,255,0.85); border: 1px solid #e2e8f0; border-radius: 10px; font-size: 0.84rem; color: #475569;">
                            <span style="font-weight: 600; color: #1e293b;">Select Review Column:</span> We noticed non-standard column headers. Please choose which column contains customer feedback:
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    chosen_review_col = st.selectbox(
                        "Review Column",
                        options=candidates,
                        key="unclear_col_select",
                        label_visibility="collapsed",
                    )
            except Exception:
                parsed_df = None

    # ── Stop Button Handler ───────────────────────────────────────────
    if stop_clicked:
        st.session_state["is_analyzing"] = False
        st.session_state["cancel_requested"] = True
        fut = st.session_state.get("analysis_future")
        if fut is not None:
            fut.cancel()
            st.session_state["analysis_future"] = None
        st.session_state["analysis_stopped_notice"] = True
        st.rerun()

    # ── Active Analysis Polling & Completion (Non-Flickering Fragment) ──
    if is_analyzing:
        # Start background worker if not already launched
        if st.session_state.get("analysis_future") is None:
            active_df = st.session_state.get("active_cleaned_df")
            active_q = st.session_state.get("active_question", "")
            current_lang = st.session_state.get("language", "English")
            if active_df is not None:
                st.session_state["analysis_future"] = _ANALYSIS_EXECUTOR.submit(
                    analyze_reviews_with_gemini,
                    active_df,
                    user_question=active_q,
                    language=current_lang,
                )

        _poll_analysis_monitor()
        return

    # ── Send Button Handler (Idle State) ──────────────────────────────
    if send_clicked:
        if uploaded_file is None:
            st.warning("Please upload a CSV file with customer reviews to begin analysis.")
            return

        if parsed_df is None:
            try:
                uploaded_file.seek(0)
                parsed_df = pd.read_csv(uploaded_file)
            except pd.errors.EmptyDataError:
                st.error("The uploaded file is empty. Please upload a CSV containing customer reviews.")
                return
            except Exception:
                st.error("We couldn't read your CSV file. Please make sure it is a valid comma-separated text file.")
                return

        # Invalidate previous analysis state immediately before cleaning/analyzing
        st.session_state["reviews_df"] = None
        st.session_state["analysis_results"] = None
        st.session_state["analysis_done"] = False
        st.session_state["data_quality_report"] = None
        st.session_state["review_filter_version"] = st.session_state.get("review_filter_version", 0) + 1
        st.session_state["applied_topic_filter"] = "All"
        st.session_state["topic_widget_version"] = 0
        st.session_state["selected_topic_in_explorer"] = "All Topics"

        # Clear AI recommendations from previous dataset while preserving user manual actions
        clear_ai_recommendation_actions()

        # Perform data cleaning and validation
        cleaned_df, report, err_msg = clean_and_validate_dataframe(
            parsed_df,
            review_column=chosen_review_col,
        )

        if err_msg:
            st.error(err_msg)
            return

        # Store validated data internally for active analysis
        st.session_state["active_cleaned_df"] = cleaned_df
        st.session_state["active_report"] = report
        st.session_state["active_question"] = question
        st.session_state["is_analyzing"] = True
        st.session_state["cancel_requested"] = False
        st.session_state["analysis_future"] = None
        # Clear the composer widgets immediately by advancing version key
        st.session_state["composer_version"] = st.session_state.get("composer_version", 0) + 1
        st.rerun()
