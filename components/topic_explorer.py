"""
components/topic_explorer.py
-----------------------------
Interactive Topic Explorer for Mezy (Milestone 4).

Allows restaurant & café operators to:
  1. Inspect customer feedback segmented by specific operational topic.
  2. See exact sentiment proportions and average ratings per topic.
  3. View AI-synthesized intelligence and direct evidence quotes for each topic.
  4. Filter within each topic by sentiment, star rating, and text keywords.
  5. Read 100% of the original review text without alterations or AI summarization.
  6. Explicitly identify reviews with uncertain sentiment or unassigned topics.
"""

from typing import Any, Dict, List, Optional
import html
import pandas as pd
import streamlit as st

from src.analytics import (
    prepare_enriched_reviews,
    filter_reviews,
    get_topic_summary_metrics,
    get_topic_ai_evidence,
    compute_topic_distribution,
    COLOR_POSITIVE,
    COLOR_NEGATIVE,
    COLOR_NEUTRAL,
    COLOR_MIXED,
    COLOR_UNCERTAIN,
)


def render_topic_explorer() -> None:
    """Render the Topic Explorer page."""
    # ── 1. Guard against unanalyzed state ──────────────────────────────
    if not st.session_state.get("analysis_done"):
        st.markdown(
            """
            <div style="margin-bottom: 1.25rem;">
              <h2 style="font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0; font-size: 1.6rem;">
                🗂️ Topic Explorer
              </h2>
              <p style="color: #64748b; font-size: 0.9rem; margin: 0;">
                Inspect individual customer reviews organized by operational topics.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("Analysis has not run yet. Please return to **Home**, attach your reviews CSV, and start analysis.")
        return

    reviews_df = st.session_state.get("reviews_df")
    analysis_results = st.session_state.get("analysis_results")

    if reviews_df is None or reviews_df.empty:
        st.warning("No review records found in memory. Please run analysis from Home.")
        return

    # Prepare enriched review dataset (cached / pure merge)
    enriched_df = prepare_enriched_reviews(reviews_df, analysis_results)
    total_reviews = len(enriched_df)

    # ── 2. Page Header ────────────────────────────────────────────────
    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
          <h2 style="font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0; font-size: 1.6rem; letter-spacing: -0.02em;">
            Topic Explorer
          </h2>
          <p style="color: #64748b; font-size: 0.9rem; margin: 0;">
            Explore feedback themes in depth. Select any operational topic to examine underlying customer reviews, sentiment splits, and cited evidence.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 3. Discovered Topics & Distribution ───────────────────────────
    topic_distribution = compute_topic_distribution(enriched_df)

    # Build selectable list with counts
    topic_options_map: Dict[str, str] = {"All Topics": f"All Topics ({total_reviews} reviews)"}
    for item in topic_distribution:
        t_name = item["topic"]
        t_count = item["count"]
        topic_options_map[t_name] = f"{t_name} ({t_count} reviews)"

    # Determine default selected topic
    stored_topic = st.session_state.get("selected_topic_in_explorer", "All Topics")
    if stored_topic not in topic_options_map:
        stored_topic = "All Topics"

    topic_keys_list = list(topic_options_map.keys())
    default_idx = topic_keys_list.index(stored_topic) if stored_topic in topic_keys_list else 0

    # ── 4. Topic Selection & Filter Bar ───────────────────────────────
    with st.container(border=True):
        st.markdown(
            """
            <div style="font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #4338ca; margin-bottom: 0.5rem;">
              Select Operational Topic to Inspect
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_topic_select, col_search = st.columns([2.5, 2], gap="medium")

        with col_topic_select:
            selected_topic_label = st.selectbox(
                "Choose Topic",
                options=[topic_options_map[k] for k in topic_keys_list],
                index=default_idx,
                key="topic_explorer_select",
                label_visibility="collapsed",
            )
            # Reverse lookup selected key
            selected_topic = next(
                k for k, v in topic_options_map.items() if v == selected_topic_label
            )
            st.session_state["selected_topic_in_explorer"] = selected_topic

        with col_search:
            topic_search_query = st.text_input(
                "Search in topic reviews",
                value="",
                placeholder="Search within this topic (e.g. delicious, slow, price)...",
                key="topic_explorer_search",
                label_visibility="collapsed",
            )

        # Sub-filters: Sentiment & Star Rating
        sub_col1, sub_col2, sub_col3 = st.columns([1.5, 1.5, 1], gap="small")

        with sub_col1:
            sent_filter = st.selectbox(
                "Filter Sentiment",
                options=["All Sentiments", "Positive", "Negative", "Neutral", "Mixed", "Uncertain"],
                index=0,
                key="topic_explorer_sent_filter",
            )
            selected_sent = None if sent_filter == "All Sentiments" else sent_filter

        with sub_col2:
            # Check ratings
            has_ratings = "rating" in enriched_df.columns and enriched_df["rating"].notna().any()
            rating_opts = ["All Ratings", "5 Stars", "4 Stars", "3 Stars", "2 Stars", "1 Star"] if has_ratings else ["Ratings Not Available"]
            rating_filter = st.selectbox(
                "Filter Star Rating",
                options=rating_opts,
                index=0,
                key="topic_explorer_rating_filter",
                disabled=not has_ratings,
            )
            selected_rating = None
            if has_ratings and rating_filter != "All Ratings":
                try:
                    selected_rating = int(rating_filter.split()[0])
                except Exception:
                    selected_rating = None

        with sub_col3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("↺ Reset Filters", key="topic_explorer_reset", use_container_width=True):
                st.session_state["selected_topic_in_explorer"] = "All Topics"
                st.session_state["topic_explorer_search"] = ""
                st.rerun()

    # ── 5. Selected Topic Intelligence Summary Card ───────────────────
    metrics = get_topic_summary_metrics(enriched_df, selected_topic)
    ai_evidence = get_topic_ai_evidence(analysis_results, selected_topic)

    topic_title_display = "All Topics (Combined Dataset)" if selected_topic == "All Topics" else selected_topic

    with st.container(border=True):
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem; margin-bottom: 0.75rem;">
              <div>
                <div style="font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b;">
                  Topic Summary
                </div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #0f172a; margin-top: 0.15rem;">
                  {html.escape(topic_title_display)}
                </div>
              </div>
              <div style="display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;">
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 12px; text-align: center;">
                  <span style="font-size: 0.72rem; color: #64748b; font-weight: 600; display: block;">REVIEWS</span>
                  <span style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">{metrics['total_reviews']}</span>
                </div>
                <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 6px 12px; text-align: center;">
                  <span style="font-size: 0.72rem; color: #16a34a; font-weight: 600; display: block;">POSITIVE</span>
                  <span style="font-size: 1.1rem; font-weight: 700; color: #16a34a;">{metrics['sentiment_pcts']['Positive']}%</span>
                </div>
                <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 6px 12px; text-align: center;">
                  <span style="font-size: 0.72rem; color: #dc2626; font-weight: 600; display: block;">NEGATIVE</span>
                  <span style="font-size: 1.1rem; font-weight: 700; color: #dc2626;">{metrics['sentiment_pcts']['Negative']}%</span>
                </div>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px 12px; text-align: center;">
                  <span style="font-size: 0.72rem; color: #64748b; font-weight: 600; display: block;">NEUTRAL/MIXED</span>
                  <span style="font-size: 1.1rem; font-weight: 700; color: #475569;">{round(metrics['sentiment_pcts']['Neutral'] + metrics['sentiment_pcts']['Mixed'], 1)}%</span>
                </div>
                {f'''<div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 6px 12px; text-align: center;">
                  <span style="font-size: 0.72rem; color: #d97706; font-weight: 600; display: block;">AVG RATING</span>
                  <span style="font-size: 1.1rem; font-weight: 700; color: #b45309;">★ {metrics["avg_rating"]}</span>
                </div>''' if metrics['avg_rating'] is not None else ''}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # AI Grounded Evidence for this topic (if available)
        if ai_evidence:
            st.markdown(
                """
                <div style="margin-top: 0.65rem; padding-top: 0.65rem; border-top: 1px solid #f1f5f9;">
                  <span style="font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #4338ca;">
                    Executive Intelligence & Citations
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            for ev in ai_evidence[:3]:
                ev_source = ev.get("source", "Topic Analysis")
                ev_summary = ev.get("summary", "")
                ev_quote = ev.get("evidence_quote", "")
                ev_sent = ev.get("sentiment", "Neutral")

                badge_col = "#16a34a" if ev_sent == "Positive" else ("#dc2626" if ev_sent == "Negative" else "#64748b")
                badge_bg = "#f0fdf4" if ev_sent == "Positive" else ("#fef2f2" if ev_sent == "Negative" else "#f8fafc")

                st.markdown(
                    f"""
                    <div style="background: {badge_bg}; border: 1px solid #e2e8f0; border-left: 3px solid {badge_col}; border-radius: 6px; padding: 8px 12px; margin-top: 0.4rem; font-size: 0.85rem;">
                      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                        <span style="font-weight: 600; color: #1e293b;">{html.escape(ev_source)}</span>
                        <span style="font-size: 0.72rem; font-weight: 700; color: {badge_col};">{html.escape(ev_sent)}</span>
                      </div>
                      {f'<div style="color: #334155; margin-bottom: 4px;">{html.escape(ev_summary)}</div>' if ev_summary else ''}
                      {f'<div style="color: #64748b; font-style: italic; font-size: 0.8rem;">"{html.escape(ev_quote)}"</div>' if ev_quote else ''}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── 6. Filter Records for this Topic ──────────────────────────────
    filtered_topic_df = filter_reviews(
        df=enriched_df,
        sentiment=selected_sent if selected_sent else "All",
        topic=selected_topic if selected_topic != "All Topics" else "All",
        rating=selected_rating if selected_rating is not None else "All",
        search_query=topic_search_query,
    )

    match_count = len(filtered_topic_df)

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 1.25rem 0.2rem 0.75rem; font-size: 0.86rem; color: #64748b;">
          <div>
            Showing <strong style="color: #0f172a;">{match_count}</strong> {f'of {metrics["total_reviews"]}' if match_count != metrics['total_reviews'] else ''} reviews for <strong>{html.escape(topic_title_display)}</strong>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 7. Review Cards ───────────────────────────────────────────────
    if filtered_topic_df.empty:
        st.markdown(
            f"""
            <div style="padding: 2.5rem 1.5rem; background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 12px; text-align: center; color: #64748b; margin-top: 0.5rem;">
              <div style="font-size: 1.6rem; margin-bottom: 0.4rem;">🔍</div>
              <strong style="font-size: 0.95rem; color: #1e293b;">No reviews found matching the selected criteria in this topic.</strong><br>
              <span style="font-size: 0.84rem;">Try adjusting the sentiment or rating filter, clearing the search box, or selecting a different topic above.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Render individual review cards
    for _, row in filtered_topic_df.iterrows():
        rid = row.get("review_id", "")
        text = str(row.get("review_text", ""))
        sentiment = row.get("sentiment", "Neutral")
        rating = row.get("rating")
        review_date = row.get("review_date")
        source = row.get("source", "Direct")
        topics = row.get("topics", [])

        # Sentiment badge styling
        if sentiment == "Positive":
            sent_bg, sent_col, sent_border = "#f0fdf4", COLOR_POSITIVE, "#bbf7d0"
        elif sentiment == "Negative":
            sent_bg, sent_col, sent_border = "#fef2f2", COLOR_NEGATIVE, "#fecaca"
        elif sentiment == "Mixed":
            sent_bg, sent_col, sent_border = "#fffbeb", COLOR_MIXED, "#fde68a"
        elif sentiment == "Uncertain":
            sent_bg, sent_col, sent_border = "#f1f5f9", COLOR_UNCERTAIN, "#cbd5e1"
        else:
            sent_bg, sent_col, sent_border = "#f8fafc", COLOR_NEUTRAL, "#e2e8f0"

        # Star Rating
        if pd.notna(rating):
            try:
                r_int = int(round(float(rating)))
                star_str = "★" * r_int + "☆" * (5 - r_int)
                rating_html = f"<span style='color: #f59e0b; font-weight: 600; font-size: 0.85rem;'>{star_str}</span> <span style='font-size: 0.78rem; color: #64748b;'>({rating}/5)</span>"
            except Exception:
                rating_html = f"<span style='font-size: 0.78rem; color: #64748b;'>Rating: {rating}</span>"
        else:
            rating_html = "<span style='font-size: 0.75rem; color: #94a3b8; font-style: italic;'>Unrated</span>"

        # Review Date
        if pd.notna(review_date):
            try:
                date_str = pd.to_datetime(review_date).strftime("%b %d, %Y")
            except Exception:
                date_str = str(review_date)
            date_html = f"<span style='font-size: 0.78rem; color: #64748b;'>• {html.escape(date_str)}</span>"
        else:
            date_html = "<span style='font-size: 0.75rem; color: #94a3b8; font-style: italic;'>• Date unrecorded</span>"

        # Topic tags highlighting selected topic
        if topics:
            topics_html_list = []
            for t in topics:
                is_curr = (t.strip().lower() == selected_topic.strip().lower())
                bg = "#4338ca" if is_curr else "#e0e7ff"
                color = "#ffffff" if is_curr else "#4338ca"
                weight = "700" if is_curr else "500"
                topics_html_list.append(
                    f"<span style='display: inline-block; font-size: 0.72rem; font-weight: {weight}; color: {color}; background: {bg}; padding: 2px 7px; border-radius: 4px; margin-right: 4px;'>{html.escape(str(t))}</span>"
                )
            topics_html = " ".join(topics_html_list)
        else:
            topics_html = "<span style='font-size: 0.72rem; font-weight: 600; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; padding: 2px 6px; border-radius: 4px;'>⚠️ No valid topic assigned (Unassigned)</span>"

        # Uncertain sentiment notice
        uncertain_notice = ""
        if sentiment == "Uncertain":
            uncertain_notice = "<div style='font-size: 0.75rem; color: #64748b; font-style: italic; margin-top: 4px;'>⚠️ Note: Review tone is ambiguous or conflicting, classified as uncertain sentiment.</div>"

        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem;">
                  <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                    <span style="font-weight: 700; font-size: 0.82rem; color: #1e293b;">#{rid}</span>
                    {rating_html}
                    {date_html}
                    <span style="font-size: 0.74rem; color: #94a3b8;">({html.escape(str(source))})</span>
                  </div>
                  <span style="font-size: 0.72rem; font-weight: 700; color: {sent_col}; background: {sent_bg}; border: 1px solid {sent_border}; padding: 2px 8px; border-radius: 6px;">
                    {html.escape(str(sentiment))}
                  </span>
                </div>
                <div style="font-size: 0.92rem; color: #1e293b; line-height: 1.5; margin-bottom: 0.5rem;">
                  "{html.escape(text)}"
                </div>
                {uncertain_notice}
                <div style="display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; margin-top: 0.35rem;">
                  <span style="font-size: 0.74rem; color: #64748b; font-weight: 600;">Topics:</span>
                  {topics_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
