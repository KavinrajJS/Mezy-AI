"""
src/analytics.py
----------------
Analytics, filtering, and chart preparation engine for Mezy (Milestone 4).

Key responsibilities:
  1. Enriches cleaned reviews with AI-generated breakdown without re-running Gemini.
  2. Multi-criteria review filtering (sentiment, topic, rating, date range, search query).
  3. Python-based arithmetic calculations for sentiment distribution, multi-topic counts,
     and topic-wise sentiment breakdown.
  4. Interactive Plotly chart builders adhering to Mezy design system tokens.
  5. Graceful handling of missing dates, missing ratings, multi-topic reviews, and empty results.
"""

from collections import Counter
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Design Tokens & Color Palette ──────────────────────────────────────────
COLOR_POSITIVE = "#16a34a"
COLOR_NEGATIVE = "#dc2626"
COLOR_NEUTRAL  = "#64748b"
COLOR_MIXED    = "#d97706"
COLOR_UNCERTAIN= "#94a3b8"
COLOR_PRIMARY  = "#4f46e5"

SENTIMENT_COLOR_MAP = {
    "Positive":  COLOR_POSITIVE,
    "Negative":  COLOR_NEGATIVE,
    "Neutral":   COLOR_NEUTRAL,
    "Mixed":     COLOR_MIXED,
    "Uncertain": COLOR_UNCERTAIN,
}


# ── Topic Normalization & Taxonomy ─────────────────────────────────────────
TOPIC_SYNONYM_MAP: Dict[str, str] = {
    # Price & Value
    "pricing": "Price & Value",
    "price": "Price & Value",
    "price & value": "Price & Value",
    "value": "Price & Value",
    "cost": "Price & Value",
    "billing": "Price & Value",
    "bill": "Price & Value",
    "money": "Price & Value",
    "expensive": "Price & Value",
    "overpriced": "Price & Value",
    "cheap": "Price & Value",
    "pocket friendly": "Price & Value",
    # Food Quality & Taste
    "food quality": "Food Quality",
    "food": "Food Quality",
    "quality": "Food Quality",
    "taste": "Taste",
    "flavor": "Taste",
    "flavour": "Taste",
    "spicy": "Taste",
    "portion": "Portion Size",
    "portion size": "Portion Size",
    # Staff & Service
    "staff behaviour": "Staff Behaviour",
    "staff behavior": "Staff Behaviour",
    "staff": "Staff Behaviour",
    "service": "Staff Behaviour",
    "hospitality": "Staff Behaviour",
    "waiter": "Staff Behaviour",
    "server": "Staff Behaviour",
    # Cleanliness & Hygiene
    "cleanliness": "Cleanliness",
    "hygiene": "Cleanliness",
    "clean": "Cleanliness",
    "dirty": "Cleanliness",
    "washroom": "Cleanliness",
    "restroom": "Cleanliness",
    "sanitation": "Cleanliness",
    # Delivery & Speed
    "delivery": "Delivery",
    "delivery service": "Delivery",
    "delivery speed": "Delivery",
    "courier": "Delivery",
    "rider": "Delivery",
    "waiting time": "Waiting Time",
    "wait time": "Waiting Time",
    "speed": "Waiting Time",
    "delay": "Waiting Time",
    "slow service": "Waiting Time",
    # Packaging
    "packaging": "Packaging",
    "packing": "Packaging",
    "package": "Packaging",
    "spill": "Packaging",
    # Ambiance & Facilities
    "ambiance": "Ambiance & Facilities",
    "ambience": "Ambiance & Facilities",
    "atmosphere": "Ambiance & Facilities",
    "ac": "Ambiance & Facilities",
    "air conditioning": "Ambiance & Facilities",
    "parking": "Ambiance & Facilities",
    "seating": "Ambiance & Facilities",
    "facilities": "Ambiance & Facilities",
    # Overall Experience
    "overall experience": "Overall Experience",
    "overall": "Overall Experience",
    "experience": "Overall Experience",
}


def normalize_topic_name(topic: str) -> str:
    """Normalize topic variations and synonyms to canonical taxonomy names."""
    if not topic or not isinstance(topic, str):
        return ""
    t_clean = topic.strip()
    return TOPIC_SYNONYM_MAP.get(t_clean.lower(), t_clean)


def infer_fallback_topic(review_text: str) -> Optional[str]:
    """
    Infer an operational category for unassigned feedback when the text clearly
    discusses identifiable operations (e.g. incorrect change -> Price & Value,
    washroom signage -> Cleanliness, parking/ac -> Ambiance & Facilities).

    Does NOT force a category on generic reviews (e.g. 'Good place', 'Average').
    """
    if not review_text or not isinstance(review_text, str):
        return None

    import re
    t_lower = review_text.lower()

    # 1. Billing, change, or pricing issues
    if re.search(r"\b(incorrect change|short change|wrong change|extra charge|overcharged|billing|bill|receipt|money worth|expensive|price|pricing|cost|kasu|panam|vila|costly|jaasthi)\b", t_lower):
        return "Price & Value"

    # 2. Washroom, restroom, cleanliness, hygiene
    if re.search(r"\b(washroom|restroom|toilet|bathroom|signage|hygiene|sticky floor|unclean|dirty|cockroach|fly|insect|cleanliness|suththam|azhukku)\b", t_lower):
        return "Cleanliness"

    # 3. Facilities, AC, parking, seating, ambiance
    if re.search(r"\b(ac|air conditioning|air conditioner|parking|valet|seating|chairs|tables|noise|lighting|ambiance|ambience)\b", t_lower):
        return "Ambiance & Facilities"

    # 4. Delivery
    if re.search(r"\b(delivery|swiggy|zomato|courier|rider|driver|delivered|anuppa)\b", t_lower):
        return "Delivery"

    # 5. Waiting time / delays
    if re.search(r"\b(waiting time|waited|wait time|took too long|slow service|delay|delayed|queue|line|romba neram|late|minutes wait|hour wait)\b", t_lower):
        return "Waiting Time"

    # 6. Staff / Service
    if re.search(r"\b(waiter|waitress|server|cashier|manager|staff|rude|hospitality)\b", t_lower):
        return "Staff Behaviour"

    # 7. Packaging
    if re.search(r"\b(packaging|packed|packing|spilled|spill|leakage|container|box)\b", t_lower):
        return "Packaging"

    # 8. Food Quality / Taste / Freshness / Temperature
    if re.search(r"\b(food|taste|flavor|flavour|delicious|tasty|bland|stale|salty|sweet|sour|spicy|raw|undercooked|overcooked|cold food|burnt|burned|fresh|dish|curry|biryani|chicken|paneer|pizza|burger|meal|portion|saapadu|suvai)\b", t_lower):
        return "Food Quality"

    return None


def prepare_enriched_reviews(
    reviews_df: Optional[pd.DataFrame],
    analysis_results: Optional[Dict[str, Any]],
) -> pd.DataFrame:
    """
    Merge cleaned review rows with AI breakdown classifications.
    Applies topic normalization and identifiable fallback association.
    Never modifies the original reviews_df or analysis_results.
    """
    if reviews_df is None or reviews_df.empty:
        return pd.DataFrame(columns=[
            "review_id", "review_text", "rating", "review_date", "source",
            "sentiment", "topics", "is_general_feedback", "has_fallback_applied"
        ])

    df = reviews_df.copy()

    # Standardize review_id
    if "review_id" not in df.columns:
        df["review_id"] = df.index + 1

    # Extract per_review_breakdown lookup
    breakdown_list = []
    if analysis_results and isinstance(analysis_results, dict):
        breakdown_list = analysis_results.get("per_review_breakdown", [])

    breakdown_lookup: Dict[int, Dict[str, Any]] = {}
    for item in breakdown_list:
        if isinstance(item, dict) and "review_id" in item:
            try:
                rid = int(item["review_id"])
                breakdown_lookup[rid] = item
            except (ValueError, TypeError):
                continue

    has_orig_lang = "language" in df.columns
    detected_languages: List[Optional[str]] = []
    sentiments: List[str] = []
    topics_col: List[List[str]] = []
    is_general_col: List[bool] = []
    fallback_applied_col: List[bool] = []

    for _, row in df.iterrows():
        rid = row.get("review_id")
        ai_data = breakdown_lookup.get(rid, {})

        # Language extraction (if detected in AI breakdown)
        raw_lang = ai_data.get("language")
        if raw_lang and isinstance(raw_lang, str) and raw_lang.strip():
            detected_languages.append(raw_lang.strip().capitalize())
        else:
            detected_languages.append(None)

        # Sentiment extraction & normalization
        raw_sent = str(ai_data.get("sentiment", "Neutral")).strip().capitalize()
        if raw_sent not in ["Positive", "Negative", "Neutral", "Mixed", "Uncertain"]:
            raw_sent = "Neutral"
        sentiments.append(raw_sent)

        # Topics extraction (multi-topic support & normalization)
        raw_topics = ai_data.get("topics", [])
        clean_topics: List[str] = []
        if isinstance(raw_topics, list):
            clean_topics = [
                normalize_topic_name(str(t))
                for t in raw_topics
                if str(t).strip()
            ]
        elif isinstance(raw_topics, str) and raw_topics.strip():
            clean_topics = [normalize_topic_name(raw_topics)]

        # If empty, attempt fallback inference for identifiable operational feedback
        is_general = False
        has_fallback = False
        if not clean_topics:
            review_text_str = str(row.get("review_text", ""))
            inferred = infer_fallback_topic(review_text_str)
            if inferred:
                clean_topics = [inferred]
                has_fallback = True
            else:
                is_general = True

        # Deduplicate while preserving order
        deduped = list(dict.fromkeys(clean_topics))
        topics_col.append(deduped)
        is_general_col.append(is_general)
        fallback_applied_col.append(has_fallback)

    df["sentiment"] = sentiments
    df["topics"] = topics_col
    df["is_general_feedback"] = is_general_col
    df["has_fallback_applied"] = fallback_applied_col

    if not has_orig_lang and any(l is not None for l in detected_languages):
        df["language"] = [l if l else "English" for l in detected_languages]

    # Ensure review_date is datetime if present
    if "review_date" in df.columns:
        df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")

    return df


def filter_reviews(
    df: pd.DataFrame,
    sentiment: Optional[str] = "All",
    topic: Optional[str] = "All",
    rating: Optional[Union[int, str]] = "All",
    start_date: Optional[Union[date, datetime, str]] = None,
    end_date: Optional[Union[date, datetime, str]] = None,
    search_query: Optional[str] = None,
    language: Optional[str] = "All",
) -> pd.DataFrame:
    """
    Apply combined filters to the enriched reviews DataFrame.
    Returns a filtered subset; never mutates the original DataFrame.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    filtered = df.copy()

    # 1. Sentiment filter
    if sentiment and sentiment != "All":
        filtered = filtered[filtered["sentiment"].str.lower() == sentiment.strip().lower()]

    # 2. Topic filter
    if topic and topic != "All":
        if topic in ["General Feedback", "Unassigned / No Topic", "Unassigned", "General"]:
            filtered = filtered[filtered["topics"].apply(lambda t: len(t) == 0)]
        else:
            t_lower = topic.strip().lower()
            filtered = filtered[
                filtered["topics"].apply(lambda t_list: any(str(t).lower() == t_lower for t in t_list))
            ]

    # 3. Star rating filter
    if rating and rating != "All":
        try:
            r_num = float(rating)
            filtered = filtered[filtered["rating"] == r_num]
        except (ValueError, TypeError):
            pass

    # 4. Date range filter (only if valid review_date is available)
    if "review_date" in filtered.columns and (start_date or end_date):
        valid_dates_mask = filtered["review_date"].notna()
        date_mask = pd.Series(True, index=filtered.index)

        if start_date:
            s_dt = pd.to_datetime(start_date)
            date_mask &= (filtered["review_date"] >= s_dt)

        if end_date:
            e_dt = pd.to_datetime(end_date)
            # Compare up to end of selected day
            date_mask &= (filtered["review_date"] <= e_dt)

        # Retain rows within date range, exclude rows with null dates if user explicitly filtered by date
        filtered = filtered[valid_dates_mask & date_mask]

    # 5. Search query filter
    if search_query and search_query.strip():
        q = search_query.strip().lower()
        filtered = filtered[
            filtered["review_text"].astype(str).str.lower().str.contains(q, regex=False, na=False)
        ]

    # 6. Language filter (only if language column is present in dataset)
    if language and language != "All" and "language" in filtered.columns:
        filtered = filtered[
            filtered["language"].astype(str).str.lower() == language.strip().lower()
        ]

    return filtered


def get_topic_summary_metrics(df: pd.DataFrame, topic: str) -> Dict[str, Any]:
    """
    Compute granular metrics for a specific topic across the dataset.
    Handles 'All Topics', specific topics, and 'Unassigned / No Topic'.
    """
    if df is None or df.empty:
        return {
            "topic": topic,
            "total_reviews": 0,
            "sentiment_counts": {"Positive": 0, "Negative": 0, "Neutral": 0, "Mixed": 0, "Uncertain": 0},
            "sentiment_pcts": {"Positive": 0.0, "Negative": 0.0, "Neutral": 0.0, "Mixed": 0.0, "Uncertain": 0.0},
            "avg_rating": None,
        }

    # Filter to topic reviews
    if topic in ["All", "All Topics"]:
        topic_df = df
    elif topic in ["General Feedback", "Unassigned / No Topic", "Unassigned"]:
        topic_df = df[df["topics"].apply(lambda t: len(t) == 0)]
    else:
        t_lower = topic.strip().lower()
        topic_df = df[
            df["topics"].apply(lambda t_list: any(str(t).lower() == t_lower for t in t_list))
        ]

    total = len(topic_df)
    counts = Counter(topic_df["sentiment"])
    sent_counts = {
        "Positive": counts.get("Positive", 0),
        "Negative": counts.get("Negative", 0),
        "Neutral": counts.get("Neutral", 0),
        "Mixed": counts.get("Mixed", 0),
        "Uncertain": counts.get("Uncertain", 0),
    }
    sent_pcts = {
        k: round(100.0 * v / total, 1) if total > 0 else 0.0
        for k, v in sent_counts.items()
    }

    avg_rating = None
    if "rating" in topic_df.columns and topic_df["rating"].notna().any():
        valid_r = topic_df["rating"].dropna()
        if len(valid_r) > 0:
            avg_rating = round(float(valid_r.mean()), 1)

    return {
        "topic": topic,
        "total_reviews": total,
        "sentiment_counts": sent_counts,
        "sentiment_pcts": sent_pcts,
        "avg_rating": avg_rating,
    }


def get_topic_ai_evidence(
    analysis_results: Optional[Dict[str, Any]],
    topic: str,
) -> List[Dict[str, Any]]:
    """
    Extract relevant AI summaries and cited evidence quotes from analysis_results for a specific topic.
    """
    if not analysis_results or not isinstance(analysis_results, dict):
        return []

    evidence_list: List[Dict[str, Any]] = []
    t_lower = topic.strip().lower()

    # Check recurring_topics
    for item in analysis_results.get("recurring_topics", []):
        if isinstance(item, dict):
            item_topic = str(item.get("topic", "")).strip().lower()
            if t_lower in item_topic or item_topic in t_lower or topic in ["All", "All Topics"]:
                evidence_list.append({
                    "source": "Recurring Topic",
                    "topic": item.get("topic", topic),
                    "sentiment": item.get("sentiment", "Neutral"),
                    "summary": item.get("summary", ""),
                    "evidence_quote": item.get("evidence_quote", ""),
                })

    # Check customer_likes
    for item in analysis_results.get("customer_likes", []):
        if isinstance(item, dict):
            item_topic = str(item.get("topic", "")).strip().lower()
            if t_lower in item_topic or item_topic in t_lower or topic in ["All", "All Topics"]:
                evidence_list.append({
                    "source": "Customer Praise",
                    "topic": item.get("topic", topic),
                    "sentiment": "Positive",
                    "summary": item.get("summary", ""),
                    "evidence_quote": item.get("evidence_quote", ""),
                })

    # Check common_complaints
    for item in analysis_results.get("common_complaints", []):
        if isinstance(item, dict):
            item_topic = str(item.get("topic", "")).strip().lower()
            if t_lower in item_topic or item_topic in t_lower or topic in ["All", "All Topics"]:
                evidence_list.append({
                    "source": "Customer Complaint",
                    "topic": item.get("topic", topic),
                    "sentiment": "Negative",
                    "summary": item.get("summary", ""),
                    "evidence_quote": item.get("evidence_quote", ""),
                })

    return evidence_list



def compute_sentiment_distribution(df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate sentiment counts and exact percentages from current records."""
    if df is None or df.empty:
        return {
            "counts": {"Positive": 0, "Negative": 0, "Neutral": 0, "Mixed": 0, "Uncertain": 0},
            "percentages": {"Positive": 0.0, "Negative": 0.0, "Neutral": 0.0, "Mixed": 0.0, "Uncertain": 0.0},
            "total": 0,
        }

    total = len(df)
    counts = Counter(df["sentiment"])
    data_counts = {
        "Positive": counts.get("Positive", 0),
        "Negative": counts.get("Negative", 0),
        "Neutral": counts.get("Neutral", 0),
        "Mixed": counts.get("Mixed", 0),
        "Uncertain": counts.get("Uncertain", 0),
    }
    percentages = {
        k: round(100.0 * v / total, 1) for k, v in data_counts.items()
    }

    return {
        "counts": data_counts,
        "percentages": percentages,
        "total": total,
    }


def compute_topic_distribution(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calculate topic mentions across all reviews.
    Reviews with multiple topics increment each topic independently.
    """
    if df is None or df.empty:
        return []

    all_topics: List[str] = []
    unassigned_count = 0

    for topics_list in df["topics"]:
        if topics_list:
            all_topics.extend(topics_list)
        else:
            unassigned_count += 1

    counts = Counter(all_topics)
    result = [{"topic": topic, "count": count} for topic, count in counts.most_common()]

    if unassigned_count > 0:
        result.append({"topic": "General Feedback", "count": unassigned_count})

    return result


def compute_topic_sentiment_breakdown(
    df: pd.DataFrame,
    top_n: Optional[int] = 8,
    include_unassigned: bool = False,
) -> pd.DataFrame:
    """
    Build stacked sentiment matrix for operational topics.
    Does NOT mix unassigned or general feedback into the operational topics comparison.
    Returns DataFrame ready for stacked bar plotting.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["Topic", "Sentiment", "Count"])

    # Collect topic-sentiment pairs for genuine operational topics
    records: List[Dict[str, str]] = []
    for _, row in df.iterrows():
        s = row.get("sentiment", "Neutral")
        topics = row.get("topics", [])
        if topics:
            for t in topics:
                if t and t not in ["General Feedback", "Unassigned", "Uncategorized"]:
                    records.append({"Topic": t, "Sentiment": s})
        elif include_unassigned:
            records.append({"Topic": "Reviews needing topic review", "Sentiment": s})

    if not records:
        return pd.DataFrame(columns=["Topic", "Sentiment", "Count"])

    pair_df = pd.DataFrame(records)
    # Find top topics by total volume
    topic_order = pair_df["Topic"].value_counts()
    if top_n and top_n > 0:
        top_topics = topic_order.head(top_n).index.tolist()
        pair_df = pair_df[pair_df["Topic"].isin(top_topics)]

    grouped = pair_df.groupby(["Topic", "Sentiment"]).size().reset_index(name="Count")
    return grouped


def compute_timeline_trends(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Group review volume over time if valid dates exist.
    Formats dates in DD/MM/YYYY. Groups by week if many dates exist (>20 distinct dates).
    Returns None if dates are unavailable or invalid.
    """
    if df is None or df.empty or "review_date" not in df.columns:
        return None

    valid_dates = df.dropna(subset=["review_date"]).copy()
    if valid_dates.empty:
        return None

    valid_dates["review_date"] = pd.to_datetime(valid_dates["review_date"], errors="coerce")
    valid_dates = valid_dates.dropna(subset=["review_date"])
    if valid_dates.empty:
        return None

    valid_dates["date_only"] = valid_dates["review_date"].dt.date
    unique_dates_count = valid_dates["date_only"].nunique()

    if unique_dates_count > 20:
        # Group by week (start of week Monday)
        valid_dates["week_start"] = valid_dates["review_date"].dt.to_period("W").apply(lambda r: r.start_time.date())
        grouped = valid_dates.groupby("week_start").size().reset_index(name="Review Count")
        grouped["date_only"] = pd.to_datetime(grouped["week_start"])
        grouped["date_label"] = grouped["date_only"].dt.strftime("%d/%m/%Y")
        grouped.sort_values("date_only", inplace=True)
    else:
        grouped = valid_dates.groupby("date_only").size().reset_index(name="Review Count")
        grouped["date_only"] = pd.to_datetime(grouped["date_only"])
        grouped["date_label"] = grouped["date_only"].dt.strftime("%d/%m/%Y")
        grouped.sort_values("date_only", inplace=True)

    if "rating" in valid_dates.columns and valid_dates["rating"].notna().any():
        group_col = "week_start" if unique_dates_count > 20 else "date_only"
        avg_ratings = valid_dates.groupby(group_col)["rating"].mean().reset_index(name="Avg Rating")
        avg_ratings["date_only"] = pd.to_datetime(avg_ratings[group_col])
        grouped = pd.merge(grouped, avg_ratings[["date_only", "Avg Rating"]], on="date_only", how="left")
        grouped["Avg Rating"] = grouped["Avg Rating"].round(2)

    return grouped


def compute_average_customer_rating(df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Calculate the average customer star rating for valid numeric ratings between 1 and 5.
    Returns None if no valid ratings exist in the dataset or filter context.
    """
    if df is None or df.empty or "rating" not in df.columns:
        return None

    valid_ratings = pd.to_numeric(df["rating"], errors="coerce").dropna()
    valid_ratings = valid_ratings[(valid_ratings >= 1.0) & (valid_ratings <= 5.0)]

    if valid_ratings.empty:
        return None

    avg_val = round(float(valid_ratings.mean()), 1)
    count = int(len(valid_ratings))

    return {
        "average": avg_val,
        "count": count,
        "formatted": f"{avg_val:.1f} / 5",
    }


# ── Plotly Interactive Visualizations ──────────────────────────────────────

def create_sentiment_donut_chart(df: pd.DataFrame) -> go.Figure:
    """Donut chart of sentiment distribution using Mezy color tokens."""
    data = compute_sentiment_distribution(df)
    counts = data["counts"]

    # Filter out categories with 0 count for a crisp visual
    labels = [k for k, v in counts.items() if v > 0]
    values = [counts[k] for k in labels]
    colors = [SENTIMENT_COLOR_MAP.get(k, "#94a3b8") for k in labels]

    if not values:
        fig = go.Figure()
        fig.add_annotation(
            text="No reviews available for sentiment chart",
            showarrow=False,
            font=dict(size=14, color="#64748b"),
        )
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
        return fig

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=colors, line=dict(color="#ffffff", width=2)),
                textinfo="percent+label",
                textposition="inside",
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        height=280,
        margin=dict(l=10, r=10, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color="#334155"),
    )
    return fig


def create_topics_bar_chart(df: pd.DataFrame, max_topics: int = 8) -> go.Figure:
    """Horizontal bar chart of most discussed topics."""
    topics_data = compute_topic_distribution(df)
    if not topics_data:
        fig = go.Figure()
        fig.add_annotation(
            text="No topics identified in current records",
            showarrow=False,
            font=dict(size=14, color="#64748b"),
        )
        fig.update_layout(
            height=280,
            margin=dict(l=10, r=10, t=10, b=10),
            dragmode=False,
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True),
        )
        return fig

    top_topics = topics_data[:max_topics]
    # Reverse so top is at the top of horizontal chart
    top_topics.reverse()

    topics = [item["topic"] for item in top_topics]
    counts = [item["count"] for item in top_topics]

    fig = go.Figure(
        data=[
            go.Bar(
                x=counts,
                y=topics,
                orientation="h",
                marker=dict(
                    color="#6366f1",
                    line=dict(color="#4f46e5", width=1),
                    opacity=0.9,
                ),
                text=counts,
                textposition="auto",
                hovertemplate="<b>%{y}</b><br>Mentions: %{x}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        dragmode=False,
        height=280,
        margin=dict(l=10, r=20, t=10, b=20),
        xaxis=dict(title="Mentions", showgrid=True, gridcolor="#f1f5f9", fixedrange=True),
        yaxis=dict(title="", showgrid=False, fixedrange=True),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color="#334155"),
    )
    return fig


def create_topic_sentiment_stacked_chart(df: pd.DataFrame, max_topics: Optional[int] = 6) -> go.Figure:
    """
    Horizontal stacked bar chart displaying sentiment breakdown per operational topic.
    Sorted consistently by mention count with top legend and clean readable labels.
    Unassigned reviews are kept separate from the operational topics comparison.
    """
    if df is None or df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No topic sentiment data for current filter",
            showarrow=False,
            font=dict(size=13, color="#64748b"),
        )
        fig.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            dragmode=False,
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True),
        )
        return fig

    matrix = compute_topic_sentiment_breakdown(df, top_n=max_topics, include_unassigned=False)

    if matrix.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No operational topic data for current filter",
            showarrow=False,
            font=dict(size=13, color="#64748b"),
        )
        fig.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            dragmode=False,
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True),
        )
        return fig

    # Calculate total mentions per topic for sorting (ascending so highest count renders at top of horizontal chart)
    topic_totals = matrix.groupby("Topic")["Count"].sum().sort_values(ascending=True)
    sorted_topics = topic_totals.index.tolist()

    fig = go.Figure()

    # Fixed sentiment order for visual consistency: Positive, Negative, Neutral, Mixed, Uncertain
    sentiment_order = ["Positive", "Negative", "Neutral", "Mixed", "Uncertain"]
    available_sentiments = [s for s in sentiment_order if s in matrix["Sentiment"].unique()]
    for s in matrix["Sentiment"].unique():
        if s not in available_sentiments:
            available_sentiments.append(s)

    for sent in available_sentiments:
        sent_sub = matrix[matrix["Sentiment"] == sent].set_index("Topic")
        counts = [int(sent_sub.loc[t, "Count"]) if t in sent_sub.index else 0 for t in sorted_topics]
        color = SENTIMENT_COLOR_MAP.get(sent, "#94a3b8")

        fig.add_trace(
            go.Bar(
                name=sent,
                y=sorted_topics,
                x=counts,
                orientation="h",
                marker=dict(color=color, opacity=0.9),
                text=[str(c) if c > 0 else "" for c in counts],
                textposition="inside",
                insidetextanchor="middle",
                hovertemplate=f"<b>%{{y}}</b><br>Sentiment: {sent}<br>Count: %{{x}} reviews<extra></extra>",
            )
        )

    num_topics = len(sorted_topics)
    chart_height = max(260, num_topics * 42 + 65)
    max_count = topic_totals.max() if not topic_totals.empty else 1

    fig.update_layout(
        barmode="stack",
        dragmode=False,
        height=chart_height,
        bargap=0.35,
        margin=dict(l=10, r=20, t=35, b=25),
        xaxis=dict(
            title="Mentions",
            showgrid=True,
            gridcolor="#f1f5f9",
            fixedrange=True,
            dtick=max(1, int(max_count / 5)) if max_count > 4 else 1,
            tickfont=dict(family="Inter, sans-serif", size=11, color="#475569"),
            title_font=dict(size=12, color="#334155"),
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            fixedrange=True,
            tickfont=dict(family="Inter, sans-serif", size=12, color="#1e293b"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="right",
            x=1.0,
            font=dict(family="Inter, sans-serif", size=11, color="#334155"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color="#334155"),
    )
    return fig


def create_review_activity_chart(df: pd.DataFrame) -> Optional[go.Figure]:
    """
    Simple column chart showing customer review volume over time with DD/MM/YYYY date labels.
    Never combines rating lines on a dual axis.
    Returns None if valid dates are unavailable.
    """
    trend_df = compute_timeline_trends(df)
    if trend_df is None or trend_df.empty:
        return None

    dates = trend_df["date_label"].tolist() if "date_label" in trend_df.columns else trend_df["date_only"].dt.strftime("%d/%m/%Y").tolist()
    counts = trend_df["Review Count"].tolist()

    fig = go.Figure(
        data=[
            go.Bar(
                x=dates,
                y=counts,
                marker=dict(
                    color="#6366f1",
                    line=dict(color="#4f46e5", width=1),
                    opacity=0.9,
                ),
                text=[str(c) for c in counts],
                textposition="auto",
                hovertemplate="<b>Date: %{x}</b><br>Number of Reviews: %{y}<extra></extra>",
            )
        ]
    )

    max_count = max(counts) if counts else 1
    dtick_val = 1 if max_count <= 8 else max(1, int(max_count / 5))

    fig.update_layout(
        dragmode=False,
        height=240,
        margin=dict(l=10, r=15, t=10, b=30),
        xaxis=dict(
            title="",
            type="category",
            showgrid=False,
            fixedrange=True,
            tickfont=dict(family="Inter, sans-serif", size=11, color="#475569"),
        ),
        yaxis=dict(
            title="Number of Reviews",
            showgrid=True,
            gridcolor="#f1f5f9",
            fixedrange=True,
            dtick=dtick_val,
            tickfont=dict(family="Inter, sans-serif", size=11, color="#475569"),
            title_font=dict(size=12, color="#334155"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=11, color="#334155"),
    )
    return fig


def create_trend_line_chart(df: pd.DataFrame) -> Optional[go.Figure]:
    """
    Review activity chart over time (alias for create_review_activity_chart to ensure backward compatibility).
    """
    return create_review_activity_chart(df)
