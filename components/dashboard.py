"""
components/dashboard.py
-----------------------
Overview page for Mezy AI Customer Review Intelligence.

In Milestone 3, this renders the real Gemini-generated customer intelligence:
  • Executive summary & user question response
  • Sentiment distribution breakdown (Positive, Neutral, Negative)
  • Customer highlights: Top likes & recurring complaints with evidence quotes
  • Recurring topics with sentiment tags
  • Practical, prioritized recommendations for restaurant & café owners

Milestone 4 will introduce full interactive charts, filters, and review data explorer.
"""

from typing import Any, Dict, List
import streamlit as st
from src.translations import t


def render_overview() -> None:
    """Render the customer intelligence overview page."""
    if not st.session_state.get("analysis_done"):
        st.info(
            "Analysis has not run yet. "
            "Please return to **Home**, attach your reviews CSV, and click ➔ to begin."
        )
        return

    results = st.session_state.get("analysis_results")
    if not results or not isinstance(results, dict):
        st.warning("No analysis results found. Please return to Home and run review analysis.")
        return

    lang = st.session_state.get("language", "English")

    summary = results.get("summary", {})
    sentiment_stats = results.get("sentiment_stats", {})
    user_q = summary.get("user_question", "")
    q_resp = results.get("question_response", {})

    # ── Header ────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="margin-bottom: 1.25rem;">
          <h2 style="font-family: 'Plus Jakarta Sans', Sora, sans-serif; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0; font-size: 1.6rem; letter-spacing: -0.02em;">
            {t("overview_heading", lang)}
          </h2>
          <p style="color: #64748b; font-size: 0.9rem; margin: 0 0 0.35rem 0;">
            {t("overview_subheading", lang)}
          </p>
          <div style="font-size: 0.76rem; color: #94a3b8; font-style: italic;">
            {t("multilingual_notice", lang)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── User Question Answer Card (if question was asked) ─────────────
    if user_q and user_q not in ["General review analysis", "None provided"]:
        answer_text = q_resp.get("answer", "")
        evidence_list = q_resp.get("supporting_evidence", [])
        if answer_text:
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="margin-bottom: 0.35rem;">
                      <span style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #4338ca; background: #e0e7ff; padding: 2px 8px; border-radius: 4px;">
                        {t("question_inquiry", lang)}
                      </span>
                    </div>
                    <div style="font-weight: 600; font-size: 1.05rem; color: #1e293b; margin-bottom: 0.5rem;">
                      "{user_q}"
                    </div>
                    <div style="color: #334155; font-size: 0.95rem; line-height: 1.5; margin-bottom: 0.5rem;">
                      {answer_text}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if evidence_list:
                    quotes_items = "".join(
                        f'<li style="margin-bottom: 0.5rem; color: #334155; font-size: 0.9rem; line-height: 1.5; font-style: italic; padding-left: 0.25rem;">"{eq}"</li>'
                        for eq in evidence_list[:3]
                    )
                    st.markdown(
                        f"""
                        <div style="margin-top: 0.85rem; padding-top: 0.25rem;">
                          <div style="font-size: 0.82rem; color: #64748b; font-weight: 600; margin-bottom: 0.55rem;">
                            {t("supporting_quotes", lang)}
                          </div>
                          <ul style="margin: 0; padding-left: 1.25rem; list-style-type: disc;">
                            {quotes_items}
                          </ul>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ── Executive Summary & Sentiment Cards ───────────────────────────
    col_summary, col_sentiment = st.columns([1.5, 1.1], gap="medium")

    with col_summary:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="padding: 0.35rem 0.25rem 0.25rem;">
                  <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; margin-bottom: 0.55rem;">
                    {t("executive_summary", lang)}
                  </div>
                  <p style="color: #1e293b; font-size: 0.95rem; line-height: 1.6; margin: 0;">
                    {summary.get("executive_summary", "Review analysis completed successfully.")}
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_sentiment:
        pos_pct = sentiment_stats.get("positive_pct", 0)
        neg_pct = sentiment_stats.get("negative_pct", 0)
        neu_pct = sentiment_stats.get("neutral_pct", 0)
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="padding: 0.35rem 0.25rem 0.25rem;">
                  <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; margin-bottom: 0.85rem;">
                    {t("sentiment_breakdown", lang)} ({summary.get("total_reviews", 0)} {t("reviews_count", lang)})
                  </div>
                  <div style="display: flex; gap: 0.85rem; align-items: stretch; justify-content: space-between;">
                    <div style="flex: 1; text-align: center; padding: 0.75rem 0.5rem; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; display: flex; flex-direction: column; justify-content: center;">
                      <div style="font-size: 1.3rem; font-weight: 700; color: #16a34a; line-height: 1.2; margin-bottom: 0.3rem;">{pos_pct}%</div>
                      <div style="font-size: 0.76rem; color: #15803d; font-weight: 600;">{t("positive_label", lang)}</div>
                    </div>
                    <div style="flex: 1; text-align: center; padding: 0.75rem 0.5rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px; display: flex; flex-direction: column; justify-content: center;">
                      <div style="font-size: 1.3rem; font-weight: 700; color: #dc2626; line-height: 1.2; margin-bottom: 0.3rem;">{neg_pct}%</div>
                      <div style="font-size: 0.76rem; color: #b91c1c; font-weight: 600;">{t("negative_label", lang)}</div>
                    </div>
                    <div style="flex: 1; text-align: center; padding: 0.75rem 0.5rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; display: flex; flex-direction: column; justify-content: center;">
                      <div style="font-size: 1.3rem; font-weight: 700; color: #64748b; line-height: 1.2; margin-bottom: 0.3rem;">{neu_pct}%</div>
                      <div style="font-size: 0.76rem; color: #475569; font-weight: 600;">{t("neutral_mix_label", lang)}</div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Customer Likes & Common Complaints ────────────────────────────
    col_likes, col_complaints = st.columns(2, gap="medium")

    with col_likes:
        st.markdown(
            f"<h4 style='font-size: 1.05rem; font-weight: 700; color: #15803d; margin: 1.25rem 0 0.55rem 0;'>{t('what_customers_like', lang)}</h4>",
            unsafe_allow_html=True,
        )
        likes = results.get("customer_likes", [])
        if likes:
            for item in likes[:4]:
                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style="padding: 0.15rem 0.1rem;">
                          <div style="font-weight: 600; font-size: 0.92rem; color: #1e293b; margin-bottom: 0.3rem;">
                            {item.get("topic", "Highlight")}
                          </div>
                          <div style="font-size: 0.88rem; color: #475569; line-height: 1.45; margin-bottom: 0.4rem;">
                            {item.get("summary", "")}
                          </div>
                          <div style="font-size: 0.82rem; color: #15803d; font-style: italic; line-height: 1.4;">
                            "{item.get("evidence_quote", "")}"
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info(t("no_likes_msg", lang))

    with col_complaints:
        st.markdown(
            f"<h4 style='font-size: 1.05rem; font-weight: 700; color: #b91c1c; margin: 1.25rem 0 0.55rem 0;'>{t('common_complaints', lang)}</h4>",
            unsafe_allow_html=True,
        )
        complaints = results.get("common_complaints", [])
        if complaints:
            for item in complaints[:4]:
                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style="padding: 0.15rem 0.1rem;">
                          <div style="font-weight: 600; font-size: 0.92rem; color: #1e293b; margin-bottom: 0.3rem;">
                            {item.get("topic", "Complaint Area")}
                          </div>
                          <div style="font-size: 0.88rem; color: #475569; line-height: 1.45; margin-bottom: 0.4rem;">
                            {item.get("summary", "")}
                          </div>
                          <div style="font-size: 0.82rem; color: #b91c1c; font-style: italic; line-height: 1.4;">
                            "{item.get("evidence_quote", "")}"
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info(t("no_complaints_msg", lang))

    # ── Actionable Recommendations ────────────────────────────────────
    st.markdown(
        f"<h4 style='font-size: 1.05rem; font-weight: 700; color: #0f172a; margin: 1.5rem 0 0.55rem 0;'>{t('business_recommendations', lang)}</h4>",
        unsafe_allow_html=True,
    )
    recommendations = results.get("actionable_recommendations", [])
    if recommendations:
        for rec in recommendations[:4]:
            priority = str(rec.get("priority", "Medium")).capitalize()
            p_color = "#dc2626" if priority == "High" else ("#f59e0b" if priority == "Medium" else "#2563eb")
            p_bg = "#fef2f2" if priority == "High" else ("#fffbeb" if priority == "Medium" else "#eff6ff")
            p_label = t(f"priority_{priority.lower()}", lang)

            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="padding: 0.15rem 0.1rem;">
                      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                        <span style="font-weight: 600; font-size: 0.95rem; color: #0f172a;">{rec.get("area", "Improvement Area")}</span>
                        <span style="font-size: 0.72rem; font-weight: 700; color: {p_color}; background: {p_bg}; padding: 2px 8px; border-radius: 4px;">
                          {p_label}
                        </span>
                      </div>
                      <div style="font-size: 0.9rem; color: #1e293b; font-weight: 500; line-height: 1.45; margin-bottom: 0.35rem;">
                        {rec.get("recommendation", "")}
                      </div>
                      <div style="font-size: 0.84rem; color: #64748b; line-height: 1.4; margin-bottom: 0.35rem;">
                        <strong style="color: #475569;">{t("reasoning_label", lang)}</strong> {rec.get("reasoning", "")}
                      </div>
                      <div style="font-size: 0.82rem; color: #475569; font-style: italic; line-height: 1.4;">
                        {t("evidence_label", lang)} "{rec.get("supporting_evidence", "")}"
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

