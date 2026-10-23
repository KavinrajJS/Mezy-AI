"""
app.py
------
Mezy — AI-powered customer review intelligence for restaurants & cafés.

Entry point: run with `streamlit run app.py`

This file wires together:
  - Page configuration
  - CSS injection
  - Sidebar navigation
  - Page routing (home → overview → review_analysis → topic_explorer → action_tracker)

Each page is a separate component in the `components/` package.
"""

import streamlit as st
from pathlib import Path

# ── Page config (must be the very first Streamlit call) ─────────────────
st.set_page_config(
    page_title="Mezy — Customer Review Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "**Mezy** — AI-powered review analytics for restaurants and cafés.",
    },
)

# ── CSS injection ────────────────────────────────────────────────────────
_CSS_PATH = Path(__file__).resolve().parent / "assets" / "styles.css"
if _CSS_PATH.exists():
    st.markdown(
        f"<style>{_CSS_PATH.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )

# ── Component imports ────────────────────────────────────────────────────
import importlib
import src.translations
import src.review_analysis
import src.analytics
import components.sidebar
import components.upload
import components.dashboard
import components.review_table
import components.topic_explorer
import components.action_tracker
import src.database
import src.report_generator

importlib.reload(src.translations)
importlib.reload(src.review_analysis)
importlib.reload(src.analytics)
importlib.reload(src.database)
importlib.reload(src.report_generator)
importlib.reload(components.sidebar)
importlib.reload(components.upload)
importlib.reload(components.dashboard)
importlib.reload(components.review_table)
importlib.reload(components.topic_explorer)
importlib.reload(components.action_tracker)

from components.sidebar import render_sidebar
from components.upload import render_home
from components.dashboard import render_overview
from components.review_table import render_review_table
from components.topic_explorer import render_topic_explorer
from components.action_tracker import render_action_tracker

# ── Session state defaults ───────────────────────────────────────────────
_DEFAULTS = {
    "current_page":     "home",
    "language":         "English",
    "reviews_df":       None,
    "analysis_results": None,
    "analysis_done":    False,
    "user_question":    "",
    "is_analyzing":     False,
    "composer_version": 0,
}
for _key, _val in _DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val

# ── Sidebar (only shown after successful analysis) ────────────────────────
if st.session_state.get("analysis_done", False):
    render_sidebar()

# ── Page router ──────────────────────────────────────────────────────────
_page = st.session_state.current_page

if st.session_state.get("_prev_active_page") != _page:
    st.session_state["_prev_active_page"] = _page
    if _page == "action_tracker":
        st.session_state.pop("last_generated_report", None)
        st.session_state.pop("report_gen_success_msg", None)
        st.session_state.pop("rep_export_language", None)
        st.session_state.pop("rep_export_format", None)

if _page == "home":
    render_home()

elif _page == "overview":
    render_overview()

elif _page in ["review_analysis", "topic_explorer"]:
    render_review_table()

elif _page == "action_tracker":
    render_action_tracker()

else:
    # Fallback
    st.session_state.current_page = "overview" if st.session_state.get("analysis_done") else "home"
    st.rerun()
