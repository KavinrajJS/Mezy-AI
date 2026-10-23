"""
components/sidebar.py
---------------------
Mezy persistent sidebar — refined SaaS UI.

Visual design:
  • Crisp logo presentation with transparent brand asset inside an elevated badge
  • Prominent brand name 'Mezy' beside logo with 'Review Intelligence' below it
  • Clean navigation buttons (Overview, Review Analysis, Action Tracker)
  • Responsive dataset indicator & Reset Dataset action
  • Zero unnecessary language selector or version footer
"""

import base64
from pathlib import Path
import streamlit as st
from src.database import clear_ai_recommendation_actions
from src.translations import t

# ── Configuration ─────────────────────────────────────────────────────────

PAGES = [
    {"id": "overview",        "icon": "⊞",  "key": "nav_overview", "label": "Overview"},
    {"id": "review_analysis", "icon": "💬", "key": "nav_review_analysis", "label": "Review Analysis"},
    {"id": "action_tracker",  "icon": "✓",  "key": "nav_action_tracker", "label": "Action Tracker"},
]


@st.cache_data
def _get_logo_b64() -> str:
    """Read transparent logo file and cache as base64 string."""
    logo_path = Path(__file__).resolve().parent.parent / "assets" / "mezy_mark_alpha.png"
    if not logo_path.exists():
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "mezy_logo_alpha.png"
    if not logo_path.exists():
        logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo_transparent.png"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode("utf-8")
    return ""


def _init_state() -> None:
    defaults = {
        "current_page":     "home",
        "language":         "English",
        "reviews_df":       None,
        "analysis_results": None,
        "analysis_done":    False,
        "user_question":    "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def render_sidebar() -> None:
    """Render the polished dark sidebar."""
    _init_state()

    cur_lang = "English"

    with st.sidebar:
        # ── 1. Brand & Logo ───────────────────────────────────────────
        logo_b64 = _get_logo_b64()
        logo_img_html = (
            f'<img src="data:image/png;base64,{logo_b64}" class="sidebar-brand-logo" alt="Mezy" />'
            if logo_b64
            else '<div class="sidebar-brand-fallback">M</div>'
        )

        st.markdown(
            f"""
            <div class="sidebar-brand-container">
              <div class="sidebar-logo-badge">
                {logo_img_html}
              </div>
              <div class="sidebar-brand-info">
                <span class="sidebar-brand-title">Mezy</span>
                <span class="sidebar-brand-subtitle">Review Intelligence</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)

        # ── 2. Navigation Menu ────────────────────────────────────────
        st.markdown(f"<div class='sidebar-section-header'>{t('sidebar_main_menu', cur_lang)}</div>", unsafe_allow_html=True)

        current = st.session_state.current_page
        analysis_done = st.session_state.analysis_done

        for page in PAGES:
            pid = page["id"]
            is_active = current == pid
            is_locked = (pid != "home") and not analysis_done

            btn_type = "primary" if is_active else "secondary"
            p_label = t(page["key"], cur_lang)
            btn_label = f"{page['icon']}   {p_label}"
            if is_locked:
                btn_label = f"{page['icon']}   {p_label}   🔒"

            if st.button(
                btn_label,
                key=f"nav_btn_{pid}",
                type=btn_type,
                use_container_width=True,
            ):
                if is_locked:
                    st.toast("Upload reviews or try sample data to run analysis first!", icon="🔒")
                else:
                    st.session_state.current_page = pid
                    st.rerun()

        # ── 3. Loaded Dataset Status ──────────────────────────────────
        if st.session_state.reviews_df is not None:
            df = st.session_state.reviews_df
            st.markdown("<div class='sidebar-divider'></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='sidebar-section-header'>{t('sidebar_active_dataset', cur_lang)}</div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="sidebar-dataset-card">
                  <div class="dataset-status-row">
                    <span class="dataset-status-dot"></span>
                    <span class="dataset-count-text">{len(df)} {t('reviews_loaded', cur_lang)}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            reset_label = f"↺  {t('btn_reset', cur_lang)}"
            if st.button(reset_label, key="reset_btn", use_container_width=True):
                clear_ai_recommendation_actions()
                st.session_state.reviews_df       = None
                st.session_state.analysis_results = None
                st.session_state.analysis_done    = False
                st.session_state.user_question    = ""
                st.session_state.current_page     = "home"
                st.rerun()
