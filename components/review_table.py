"""
components/review_table.py
--------------------------
Review Analysis & Interactive Analytics page for Mezy (Milestone 4).

Features:
  1. Interactive Charts:
     • Sentiment Distribution (counts & percentages with brand color tokens)
     • Most Discussed Topics (horizontal bars, multi-topic aware)
     • Topic-wise Sentiment (stacked bars comparing sentiment per topic)
     • Review Trends Over Time (time-series volume & rating when valid dates exist)
  2. Advanced Review Filters:
     • Sentiment (All, Positive, Negative, Neutral, Mixed, Uncertain)
     • Topic (All, individual detected topics, Unassigned)
     • Star rating (All, 1 to 5 stars)
     • Date range selector (when valid dates exist in dataset)
     • Keyword text search across customer reviews
     • Instant "Reset Filters" action
     • Live matching count indicator & graceful empty state
  3. Filtered Customer Reviews Table:
     • Full original review text preserved 100%
     • Sentiment badge, star rating, review date, source, and topic tags
"""

from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

from src.analytics import (
    prepare_enriched_reviews,
    filter_reviews,
    compute_sentiment_distribution,
    create_sentiment_donut_chart,
    create_topics_bar_chart,
    create_topic_sentiment_stacked_chart,
    create_trend_line_chart,
)

# Resilient imports for review activity and average rating KPI
try:
    from src.analytics import create_review_activity_chart
except ImportError:
    create_review_activity_chart = create_trend_line_chart

try:
    from src.analytics import compute_average_customer_rating
except ImportError:
    def compute_average_customer_rating(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        if df is None or df.empty or "rating" not in df.columns:
            return None
        valid_ratings = pd.to_numeric(df["rating"], errors="coerce").dropna()
        valid_ratings = valid_ratings[(valid_ratings >= 1.0) & (valid_ratings <= 5.0)]
        if valid_ratings.empty:
            return None
        avg_val = round(float(valid_ratings.mean()), 1)
        return {"average": avg_val, "count": int(len(valid_ratings)), "formatted": f"{avg_val:.1f} / 5"}


def render_review_table() -> None:
    """Render the Review Analysis page with interactive charts & advanced filters."""
    if not st.session_state.get("analysis_done"):
        st.info(
            "Analysis has not run yet. "
            "Please return to **Home**, attach your reviews CSV, and start analysis."
        )
        return

    reviews_df = st.session_state.get("reviews_df")
    analysis_results = st.session_state.get("analysis_results")

    if reviews_df is None or reviews_df.empty:
        st.warning("No review records found in memory. Please run analysis from Home.")
        return

    # Prepare enriched review dataset (cached in session state to avoid recalculating)
    enriched_df = prepare_enriched_reviews(reviews_df, analysis_results)
    total_reviews = len(enriched_df)

    # ── Page Header ───────────────────────────────────────────────────
    st.markdown(
        """
        <div style="margin-bottom: 1.25rem;">
          <h2 style="font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; color: #0f172a; margin: 0 0 0.25rem 0; font-size: 1.6rem; letter-spacing: -0.02em;">
            Interactive Review Analytics
          </h2>
          <p style="color: #64748b; font-size: 0.9rem; margin: 0;">
            Explore sentiment distributions, recurring topic patterns, and granular customer feedback.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Available Filter Options ──────────────────────────────────────
    # Available sentiments
    available_sentiments = ["All"] + sorted([
        s for s in enriched_df["sentiment"].unique() if s and s != "All"
    ])

    # Available topics (flatten multi-topic lists)
    all_topics_set = set()
    has_unassigned = False
    for t_list in enriched_df["topics"]:
        if t_list:
            all_topics_set.update(t_list)
        else:
            has_unassigned = True
    available_topics = ["All"] + sorted(list(all_topics_set))
    if has_unassigned:
        available_topics.append("General Feedback")

    # Available star ratings
    has_ratings = "rating" in enriched_df.columns and enriched_df["rating"].notna().any()
    available_ratings = ["All"]
    if has_ratings:
        valid_ratings = sorted([int(r) for r in enriched_df["rating"].dropna().unique() if 1 <= r <= 5], reverse=True)
        available_ratings += [f"{r} Stars" for r in valid_ratings]

    # Available languages (only if column is present in dataset)
    has_languages = "language" in enriched_df.columns and enriched_df["language"].notna().any()
    available_languages = ["All"]
    if has_languages:
        available_languages += sorted([str(l) for l in enriched_df["language"].dropna().unique() if str(l)])

    # Available date range
    has_dates = "review_date" in enriched_df.columns and enriched_df["review_date"].notna().any()
    min_date = None
    max_date = None
    if has_dates:
        valid_dates = enriched_df["review_date"].dropna()
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

    # ── Filter State Management ───────────────────────────────────────
    if "applied_topic_filter" not in st.session_state:
        st.session_state["applied_topic_filter"] = "All"
    if "topic_widget_version" not in st.session_state:
        st.session_state["topic_widget_version"] = 0

    filter_version = st.session_state.get("review_filter_version", 0)
    topic_widget_ver = st.session_state.get("topic_widget_version", 0)

    # Resolve applied topic index
    current_topic = st.session_state.get("applied_topic_filter", "All")
    if current_topic not in available_topics:
        current_topic = "All"
        st.session_state["applied_topic_filter"] = "All"
    topic_idx = available_topics.index(current_topic)

    # ── Filter Controls Container ─────────────────────────────────────
    with st.container(border=True):
        st.markdown(
            """
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem;">
              <span style="font-size: 0.76rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: #4338ca;">
                Advanced Review Filters
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        row1_col1, row1_col2, row1_col3 = st.columns([2.2, 1.2, 1.4], gap="small")

        with row1_col1:
            search_query = st.text_input(
                "Search in reviews",
                value="",
                placeholder="Search keywords (e.g. biryani, wait, staff, clean)...",
                key=f"filter_search_{filter_version}",
                label_visibility="collapsed",
            )

        with row1_col2:
            selected_sentiment = st.selectbox(
                "Sentiment",
                options=available_sentiments,
                key=f"filter_sentiment_{filter_version}",
                label_visibility="collapsed",
            )

        with row1_col3:
            selected_topic = st.selectbox(
                "Topic",
                options=available_topics,
                index=topic_idx,
                key=f"filter_topic_{filter_version}_{topic_widget_ver}",
                label_visibility="collapsed",
            )
            # Synchronize state when user changes the top selectbox manually
            st.session_state["applied_topic_filter"] = selected_topic

        # Row 2: Ratings, Date Range, Language (if present), Reset
        date_range = None
        selected_language = "All"

        if has_languages:
            row2_col1, row2_col2, row2_col3, row2_col4 = st.columns([1.3, 2.0, 1.3, 1.1], gap="small")
        else:
            row2_col1, row2_col2, row2_col3 = st.columns([1.5, 2.1, 1.2], gap="small")
            row2_col4 = None

        with row2_col1:
            selected_rating_label = st.selectbox(
                "Star Rating",
                options=available_ratings,
                key=f"filter_rating_{filter_version}",
                label_visibility="collapsed",
                disabled=not has_ratings,
            )
            # Parse rating
            selected_rating_val = "All"
            if selected_rating_label != "All":
                try:
                    selected_rating_val = int(selected_rating_label.split()[0])
                except Exception:
                    selected_rating_val = "All"

        with row2_col2:
            if has_dates and min_date and max_date:
                if min_date == max_date:
                    date_range = (min_date, max_date)
                    st.text_input("Date", value=min_date.strftime("%d/%m/%Y"), disabled=True, label_visibility="collapsed")
                else:
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_date, max_date),
                        min_value=min_date,
                        max_value=max_date,
                        key=f"filter_dates_{filter_version}",
                        label_visibility="collapsed",
                        format="DD/MM/YYYY",
                    )
            else:
                date_range = None
                st.text_input("Date Range", value="Dates not available in CSV", disabled=True, label_visibility="collapsed")

        if has_languages:
            with row2_col3:
                selected_language = st.selectbox(
                    "Language",
                    options=available_languages,
                    key=f"filter_language_{filter_version}",
                    label_visibility="collapsed",
                )
            reset_col = row2_col4
        else:
            reset_col = row2_col3

        with reset_col:
            reset_clicked = st.button("↺ Reset Filters", key="btn_reset_filters", use_container_width=True)
            if reset_clicked:
                st.session_state["review_filter_version"] = filter_version + 1
                st.session_state["applied_topic_filter"] = "All"
                st.session_state["topic_widget_version"] = 0
                st.rerun()

    # Parse start and end date safely from range picker (handles unset, 1 date, 2 dates, single date)
    filter_start = None
    filter_end = None
    if date_range is not None:
        if isinstance(date_range, (list, tuple)):
            if len(date_range) == 2:
                filter_start, filter_end = date_range[0], date_range[1]
            elif len(date_range) == 1:
                filter_start = date_range[0]
                filter_end = date_range[0]
        elif hasattr(date_range, "year"):
            filter_start = date_range
            filter_end = date_range

    # ── Execute Filtering ─────────────────────────────────────────────
    filtered_df = filter_reviews(
        df=enriched_df,
        sentiment=selected_sentiment,
        topic=selected_topic,
        rating=selected_rating_val,
        start_date=filter_start,
        end_date=filter_end,
        search_query=search_query,
        language=selected_language,
    )

    filtered_count = len(filtered_df)

    # ── Match Counter & Active Status ─────────────────────────────────
    active_filters_applied = (
        (search_query and search_query.strip())
        or (selected_sentiment != "All")
        or (selected_topic != "All")
        or (selected_rating_val != "All")
        or (has_dates and filter_start and filter_start != min_date)
        or (has_dates and filter_end and filter_end != max_date)
    )

    filter_notice = (
        f"Showing <strong style='color:#0f172a;'>{filtered_count}</strong> of {total_reviews} reviews matching active filters"
        if active_filters_applied
        else f"Displaying all <strong style='color:#0f172a;'>{total_reviews}</strong> analyzed customer reviews"
    )

    st.markdown(
        f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.85rem 0.2rem 1.15rem; font-size: 0.86rem; color: #64748b;">
          <div>{filter_notice}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Interactive Visualizations Section ────────────────────────────
    st.markdown(
        """
        <div style="font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin-bottom: 0.65rem;">
          Dataset Analytics & Visualizations
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Visualizations use filtered_df so all charts reflect active filters consistently
    chart_df = filtered_df

    # Top Row: Sentiment Donut (Left) + Most Discussed Topics (Right)
    viz_col_left, viz_col_right = st.columns(2, gap="medium")

    with viz_col_left:
        with st.container(border=True):
            st.markdown(
                """
                <div style="font-size: 0.88rem; font-weight: 600; color: #0f172a; margin-bottom: 0.2rem;">
                  Sentiment Distribution
                </div>
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 0.5rem;">
                  Overall customer perception breakdown
                </div>
                """,
                unsafe_allow_html=True,
            )
            fig_sent = create_sentiment_donut_chart(chart_df)
            st.plotly_chart(fig_sent, use_container_width=True, config={"displayModeBar": False})

    with viz_col_right:
        with st.container(border=True):
            st.markdown(
                """
                <div style="font-size: 0.88rem; font-weight: 600; color: #0f172a; margin-bottom: 0.2rem;">
                  Most Discussed Topics
                </div>
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 0.5rem;">
                  Themes customers mention most frequently
                </div>
                """,
                unsafe_allow_html=True,
            )
            fig_topics = create_topics_bar_chart(chart_df, max_topics=8)
            st.plotly_chart(
                fig_topics,
                use_container_width=True,
                config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
            )

            # Interactive topic quick filter inside Review Analysis
            top_selectable = [t for t in available_topics if t != "All"]
            if top_selectable:
                q_col1, q_col2 = st.columns([2.3, 1.3], gap="small")
                with q_col1:
                    st.selectbox(
                        "Filter by Topic",
                        options=top_selectable,
                        key="quick_topic_select",
                        label_visibility="collapsed",
                    )
                with q_col2:
                    def on_quick_filter_topic():
                        chosen = st.session_state.get("quick_topic_select")
                        if chosen:
                            st.session_state["applied_topic_filter"] = chosen
                            st.session_state["topic_widget_version"] = st.session_state.get("topic_widget_version", 0) + 1

                    st.button(
                        "Filter ➜",
                        key="btn_quick_filter_topic",
                        use_container_width=True,
                        on_click=on_quick_filter_topic,
                    )

    # Bottom Row: Topic-wise Sentiment (Left) + Trend Timeline (Right)
    viz2_col_left, viz2_col_right = st.columns(2, gap="medium")

    with viz2_col_left:
        with st.container(border=True):
            st.markdown(
                """
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem;">
                  <div style="font-size: 0.88rem; font-weight: 600; color: #0f172a;">
                    Topic-wise Sentiment Comparison
                  </div>
                </div>
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 0.5rem;">
                  Positive vs. Negative sentiment across operational themes
                </div>
                """,
                unsafe_allow_html=True,
            )
            fig_stacked = create_topic_sentiment_stacked_chart(chart_df)
            st.plotly_chart(
                fig_stacked,
                use_container_width=True,
                config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
            )

    with viz2_col_right:
        with st.container(border=True):
            st.markdown(
                """
                <div style="font-size: 0.88rem; font-weight: 600; color: #0f172a; margin-bottom: 0.2rem;">
                  Review Activity & Ratings
                </div>
                <div style="font-size: 0.75rem; color: #64748b; margin-bottom: 0.85rem;">
                  Review volume over time and average customer rating
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Separate Average Customer Rating KPI Card
            avg_rating_info = compute_average_customer_rating(chart_df)
            if avg_rating_info is not None:
                rating_val = avg_rating_info["average"]
                rating_cnt = avg_rating_info["count"]
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.7rem 0.95rem; margin-top: 0.2rem; margin-bottom: 1.05rem;">
                      <div>
                        <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b;">
                          Average Customer Rating
                        </div>
                        <div style="font-size: 1.28rem; font-weight: 800; color: #0f172a; margin-top: 0.15rem; line-height: 1.2;">
                          <span style="color: #f59e0b;">★</span> {rating_val:.1f} <span style="font-size: 0.82rem; font-weight: 500; color: #64748b;">/ 5</span>
                        </div>
                      </div>
                      <div style="font-size: 0.76rem; color: #64748b; text-align: right;">
                        Based on <strong>{rating_cnt}</strong> rated review{'s' if rating_cnt != 1 else ''}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.7rem 0.95rem; margin-top: 0.2rem; margin-bottom: 1.05rem;">
                      <div>
                        <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b;">
                          Average Customer Rating
                        </div>
                        <div style="font-size: 1.05rem; font-weight: 600; color: #64748b; margin-top: 0.15rem;">
                          Not Available
                        </div>
                      </div>
                      <div style="font-size: 0.76rem; color: #94a3b8; text-align: right;">
                        No star ratings in dataset
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Simple Column Chart for Review Activity
            fig_activity = create_review_activity_chart(chart_df)
            if fig_activity is not None:
                st.plotly_chart(
                    fig_activity,
                    use_container_width=True,
                    config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
                )
            else:
                st.markdown(
                    """
                    <div style="padding: 2.2rem 1rem; text-align: center; color: #94a3b8; font-size: 0.86rem;">
                      <div style="font-size: 1.4rem; margin-bottom: 0.4rem;">📅</div>
                      <strong style="color: #475569;">Review activity timeline unavailable</strong><br>
                      The uploaded reviews dataset does not contain valid review dates.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ── Detailed Customer Reviews List ────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 0.74rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; margin: 1.75rem 0 0.75rem 0;">
          Customer Review Records
        </div>
        """,
        unsafe_allow_html=True,
    )

    if filtered_df.empty:
        st.markdown(
            """
            <div style="padding: 2.5rem 1.5rem; background: #ffffff; border: 1px dashed #cbd5e1; border-radius: 12px; text-align: center; color: #64748b;">
              <div style="font-size: 1.6rem; margin-bottom: 0.4rem;">🔍</div>
              <strong style="font-size: 0.95rem; color: #1e293b;">No reviews match your selected filters.</strong><br>
              <span style="font-size: 0.84rem;">Try adjusting your keyword search, selecting "All" topics/sentiments, or click Reset Filters above.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Render review cards
    import html
    for _, row in filtered_df.iterrows():
        rid = row.get("review_id", "")
        text = str(row.get("review_text", ""))
        sentiment = row.get("sentiment", "Neutral")
        rating = row.get("rating")
        review_date = row.get("review_date")
        source = row.get("source", "Direct")
        topics = row.get("topics", [])

        # Sentiment badge styling
        if sentiment == "Positive":
            sent_bg, sent_col, sent_border = "#f0fdf4", "#16a34a", "#bbf7d0"
        elif sentiment == "Negative":
            sent_bg, sent_col, sent_border = "#fef2f2", "#dc2626", "#fecaca"
        elif sentiment == "Mixed":
            sent_bg, sent_col, sent_border = "#fffbeb", "#d97706", "#fde68a"
        elif sentiment == "Uncertain":
            sent_bg, sent_col, sent_border = "#f1f5f9", "#94a3b8", "#cbd5e1"
        else:
            sent_bg, sent_col, sent_border = "#f8fafc", "#64748b", "#e2e8f0"

        # Uncertain notice
        uncertain_notice = ""
        if sentiment == "Uncertain":
            uncertain_notice = "<div style='font-size: 0.75rem; color: #64748b; font-style: italic; margin-top: 4px;'>⚠️ Note: Review tone is ambiguous or conflicting, classified as uncertain sentiment.</div>"

        # Rating stars
        if pd.notna(rating):
            try:
                r_int = int(round(float(rating)))
                star_str = "★" * r_int + "☆" * (5 - r_int)
                rating_html = f"<span style='color: #f59e0b; font-weight: 600; font-size: 0.85rem;'>{star_str}</span> <span style='font-size: 0.78rem; color: #64748b;'>({rating}/5)</span>"
            except Exception:
                rating_html = f"<span style='font-size: 0.78rem; color: #64748b;'>Rating: {rating}</span>"
        else:
            rating_html = "<span style='font-size: 0.75rem; color: #94a3b8; font-style: italic;'>Unrated</span>"

        # Date string in DD/MM/YYYY
        if pd.notna(review_date):
            try:
                date_str = pd.to_datetime(review_date).strftime("%d/%m/%Y")
            except Exception:
                date_str = str(review_date)
            date_html = f"<span style='font-size: 0.78rem; color: #64748b;'>• {html.escape(date_str)}</span>"
        else:
            date_html = ""

        # Topic tags with clean spacing, gaps, and line wrapping
        if topics:
            topics_html = " ".join([
                f"<span style='display: inline-flex; align-items: center; font-size: 0.73rem; font-weight: 500; color: #3730a3; background: #eef2ff; border: 1px solid #c7d2fe; padding: 2.5px 8px; border-radius: 6px; white-space: nowrap; line-height: 1.3;'>{html.escape(t)}</span>"
                for t in topics
            ])
        else:
            topics_html = "<span style='display: inline-flex; align-items: center; font-size: 0.73rem; font-weight: 500; color: #475569; background: #f1f5f9; border: 1px solid #cbd5e1; padding: 2.5px 8px; border-radius: 6px; white-space: nowrap; line-height: 1.3;'>General Feedback</span>"

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
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem 0.45rem; margin-top: 0.55rem;">
                  <span style="font-size: 0.75rem; color: #64748b; font-weight: 600; margin-right: 0.25rem;">Topics:</span>
                  {topics_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
