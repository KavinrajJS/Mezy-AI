"""
src/review_analysis.py
----------------------
Customer Review Intelligence & AI Analysis Engine for Mezy (Milestone 3).

Key responsibilities:
  1. Consumes cleaned DataFrame from Milestone 2 (src.data_cleaning).
  2. Sends grounded, structured prompts to Gemini via src.gemini_service.
  3. Enforces strict evidence grounding (no hallucination; citing actual reviews).
  4. Identifies overall sentiment (Positive, Neutral, Negative, Mixed, Uncertain).
  5. Summarises customer likes and recurring complaints with direct quotes.
  6. Detects recurring topics (Food Quality, Staff Behaviour, Pricing, Cleanliness, Delivery, etc.).
  7. Formulates practical, high-impact business recommendations.
  8. Answers user questions asked through the landing screen composer.
  9. Calculates exact counts, percentages, and metrics in Python (Pandas) for numerical accuracy.
"""

from collections import Counter
from dataclasses import dataclass, field
import json
import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from config.settings import SENTIMENT_LABELS, TOPIC_CATEGORIES
from src.gemini_service import generate_structured_content, GeminiServiceError

logger = logging.getLogger(__name__)

__all__ = [
    "SYSTEM_INSTRUCTION",
    "build_analysis_prompt",
    "parse_and_validate_ai_response",
    "compute_numerical_statistics",
    "analyze_reviews_with_gemini",
    "adapt_analysis_to_language",
]


SYSTEM_INSTRUCTION = """
You are Mezy's Senior Customer Intelligence AI for restaurants and cafés.
Analyze the provided customer reviews objectively, concisely, and with strict grounding.

CRITICAL GROUNDING & MULTILINGUAL RULES:
1. STRICT GROUNDING: Every claim, sentiment, customer like, complaint, and recommendation MUST be directly supported by the provided reviews. NEVER invent reviews, praise, or complaints not found in the input.
2. EVIDENCE CITATION: Always cite short, exact quotes from the provided customer reviews as supporting evidence. Quotes MUST be cited VERBATIM in their original text, alphabet, and script (never translate or alter customer quotes).
3. MULTILINGUAL REVIEW UNDERSTANDING: Customer reviews may be written in English, Tamil (தமிழ்), Tanglish (Tamil words written phonetically in English/Latin letters), or mixed languages. Accurately understand sentiment and topics across all of them.
4. SENTIMENT TAXONOMY:
   - "Positive": Customer was pleased or satisfied.
   - "Negative": Customer had a bad experience or complaint.
   - "Neutral": Factual or indifferent feedback without strong sentiment.
   - "Mixed": Customer expressed BOTH positive and negative aspects in the same review (e.g., "The food was delicious, but the delivery was late", "Food super ah irundhuchu, but delivery romba late", or "உணவு நன்றாக இருந்தது, ஆனால் டெலிவரி தாமதமானது").
   - "Uncertain": Review is ambiguous, incomprehensible, contradictory, gibberish, or cannot be determined with confidence (e.g. "dunno maybe yes maybe no ???", "ok ok whatever"). Do NOT guess or hallucinate sentiment.
5. TOPIC ACCURACY: Only report recurring topics (Food Quality, Taste, Portion Size, Waiting Time, Delivery, Staff Behaviour, Cleanliness, Price & Value, Packaging, Ambiance & Facilities, Overall Experience) if they actually appear in the reviews. If a topic is unmentioned, omit it.
6. TARGET OUTPUT LANGUAGE CONTROL:
   - When Target Language is English: Generate narrative text (executive_summary, summaries, recommendations, reasoning, and answers) in clear, professional business English.
   - When Target Language is Tamil: Generate narrative text in natural, fluent TAMIL script (தமிழ்).
   - When Target Language is Tanglish: Generate narrative text in natural conversational TANGLISH (Tamil words written phonetically using English/Latin alphabet, e.g. 'Food taste super-ah irukku, aana delivery romba delay aachu').
   - CRITICAL: Structural JSON keys and sentiment categories ("Positive", "Negative", "Neutral", "Mixed", "Uncertain") must ALWAYS remain in standard English for system processing. Priority categories ("High", "Medium", "Low") must also remain in English.
7. ACTIONABLE: Suggestions must be realistic, practical, and directly address patterns observed in the reviews.
8. USER QUESTION: If the user asked a question, answer it directly and thoroughly using evidence from the reviews. If no question was provided, provide a general executive overview.
9. VALID JSON: Return ONLY a valid JSON object matching the requested schema.
""".strip()


def build_analysis_prompt(
    reviews_df: pd.DataFrame,
    user_question: Optional[str] = None,
    max_reviews: int = 50,
    language: str = "English",
) -> str:
    """Build grounded prompt containing customer reviews, user question, and target output language."""
    reviews_subset = reviews_df.head(max_reviews)

    reviews_text_list = []
    for idx, row in reviews_subset.iterrows():
        r_id = row.get("review_id", idx + 1)
        r_text = str(row.get("review_text", "")).strip()
        r_rating = row.get("rating", None)
        rating_str = f" [Rating: {r_rating}/5]" if pd.notna(r_rating) else ""
        reviews_text_list.append(f"Review #{r_id}{rating_str}: \"{r_text}\"")

    formatted_reviews = "\n".join(reviews_text_list)
    question_str = user_question.strip() if user_question and user_question.strip() else "None provided (give general business intelligence summary)"

    target_lang = language.strip() if language else "English"
    if target_lang not in ["English", "Tamil", "Tanglish"]:
        target_lang = "English"

    if target_lang == "Tamil":
        lang_instruction = (
            "TARGET OUTPUT LANGUAGE: Tamil (தமிழ்).\n"
            "Please write all narrative content (executive_summary, sentiment_overview aspects, "
            "summaries in customer_likes and common_complaints, recurring_topics summaries, "
            "actionable_recommendations fields, and question_response answer) in natural, fluent TAMIL script (தமிழ்).\n"
            "Keep JSON keys and sentiment labels (Positive/Negative/Neutral/Mixed/Uncertain) in English. "
            "Keep evidence_quote and supporting_evidence verbatim in their original uploaded text.\n"
        )
    elif target_lang == "Tanglish":
        lang_instruction = (
            "TARGET OUTPUT LANGUAGE: Tanglish (Tamil in English letters).\n"
            "Please write all narrative content (executive_summary, sentiment_overview aspects, "
            "summaries in customer_likes and common_complaints, recurring_topics summaries, "
            "actionable_recommendations fields, and question_response answer) in natural conversational TANGLISH "
            "(Tamil words written phonetically in English/Latin letters, e.g. 'Food romba nallarku aana delivery late', 'Service speed improve pannanum').\n"
            "Keep JSON keys and sentiment labels (Positive/Negative/Neutral/Mixed/Uncertain) in English. "
            "Keep evidence_quote and supporting_evidence verbatim in their original uploaded text.\n"
        )
    else:
        lang_instruction = (
            "TARGET OUTPUT LANGUAGE: English.\n"
            "Generate all narrative content in clear, professional English.\n"
            "Keep JSON keys and sentiment labels in English. Keep evidence_quote verbatim.\n"
        )

    prompt = f"""
Analyze the following customer reviews for this restaurant/café:

--- CUSTOMER REVIEWS (Total: {len(reviews_subset)}) ---
{formatted_reviews}
--- END OF REVIEWS ---

USER QUESTION / FOCUS:
"{question_str}"

{lang_instruction}

Please perform a comprehensive intelligence analysis and return a valid JSON object with the following structure:
{{
  "executive_summary": "2-3 concise sentences summarizing overall customer perception and main takeaway in {target_lang}.",
  "sentiment_overview": {{
    "primary_sentiment": "Positive" | "Neutral" | "Negative" | "Mixed",
    "positive_aspects": "Key strengths mentioned by customers in {target_lang}.",
    "neutral_aspects": "Areas where customers felt indifferent or mixed in {target_lang}.",
    "negative_aspects": "Core pain points and disappointments in {target_lang}."
  }},
  "customer_likes": [
    {{
      "topic": "Name of topic (e.g. Food Quality, Taste, Hospitality)",
      "summary": "Concise summary of what customers enjoyed in {target_lang}",
      "evidence_quote": "Exact short quote verbatim from a review"
    }}
  ],
  "common_complaints": [
    {{
      "topic": "Name of topic (e.g. Waiting Time, Delivery, Pricing, Cleanliness)",
      "summary": "Concise summary of the complaint in {target_lang}",
      "evidence_quote": "Exact short quote verbatim from a review"
    }}
  ],
  "recurring_topics": [
    {{
      "topic": "Name of recurring topic (e.g. Food Quality, Taste, Portion Size, Waiting Time, Delivery, Staff Behaviour, Cleanliness, Price & Value, Packaging, Overall Experience)",
      "sentiment": "Positive" | "Negative" | "Neutral" | "Mixed",
      "summary": "What customers say regarding this topic in {target_lang}",
      "evidence_quote": "Exact quote verbatim from review"
    }}
  ],
  "actionable_recommendations": [
    {{
      "area": "Operational area (e.g. Kitchen Speed, Staff Training, Hygiene, Packaging)",
      "priority": "High" | "Medium" | "Low",
      "recommendation": "Concrete, practical action for the business owner in {target_lang}",
      "reasoning": "Why this should be addressed based on review patterns in {target_lang}",
      "supporting_evidence": "Exact quote verbatim from a customer review"
    }}
  ],
  "question_response": {{
    "question": "{question_str}",
    "answer": "Direct, evidence-backed answer to the user question in {target_lang}.",
    "supporting_evidence": ["Exact quote 1", "Exact quote 2"]
  }},
  "per_review_breakdown": [
    {{
      "review_id": 1,
      "sentiment": "Positive" | "Negative" | "Neutral" | "Mixed" | "Uncertain",
      "topics": ["Food Quality"],
      "language": "English" | "Tamil" | "Tanglish" | "Mixed"
    }}
  ]
}}
""".strip()
    return prompt


def parse_and_validate_ai_response(raw_text: str) -> Dict[str, Any]:
    """Parse JSON string safely and validate required sections."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error(f"Failed to parse AI response as JSON: {exc}")
        # Try finding JSON block between outermost curly braces
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except Exception:
                raise GeminiServiceError("AI analysis returned malformed structure. Please retry.")
        else:
            raise GeminiServiceError("Could not parse AI analysis results. Please retry.")

    if not isinstance(data, dict):
        raise GeminiServiceError("AI response was not a structured dictionary.")

    # Fill defaults for required fields if missing
    data.setdefault("executive_summary", "Review analysis completed.")
    data.setdefault("sentiment_overview", {})
    data.setdefault("customer_likes", [])
    data.setdefault("common_complaints", [])
    data.setdefault("recurring_topics", [])
    data.setdefault("actionable_recommendations", [])
    data.setdefault("question_response", {"question": "", "answer": "", "supporting_evidence": []})
    data.setdefault("per_review_breakdown", [])

    return data


def compute_numerical_statistics(
    reviews_df: pd.DataFrame,
    ai_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate numerical statistics in Python using Pandas for guaranteed accuracy.
    Never relies on LLM for arithmetic.
    """
    total_reviews = len(reviews_df)
    breakdown = ai_data.get("per_review_breakdown", [])

    # Count sentiments
    sentiments = []
    topics_list = []
    for item in breakdown:
        s = str(item.get("sentiment", "Neutral")).capitalize()
        if s not in SENTIMENT_LABELS:
            s = "Neutral"
        sentiments.append(s)
        for t in item.get("topics", []):
            if t:
                topics_list.append(t.strip())

    sent_counts = Counter(sentiments)
    positive_count = sent_counts.get("Positive", 0)
    negative_count = sent_counts.get("Negative", 0)
    neutral_count = sent_counts.get("Neutral", 0)
    mixed_count = sent_counts.get("Mixed", 0)
    uncertain_count = sent_counts.get("Uncertain", 0)

    # In case breakdown didn't cover all reviews or was empty
    classified_total = max(1, len(sentiments))

    sentiment_metrics = {
        "positive": positive_count,
        "negative": negative_count,
        "neutral": neutral_count,
        "mixed": mixed_count,
        "uncertain": uncertain_count,
        "positive_pct": round(100.0 * positive_count / classified_total, 1),
        "negative_pct": round(100.0 * negative_count / classified_total, 1),
        "neutral_pct": round(100.0 * neutral_count / classified_total, 1),
        "mixed_pct": round(100.0 * mixed_count / classified_total, 1),
        "uncertain_pct": round(100.0 * uncertain_count / classified_total, 1),
    }

    # Primary sentiment
    if positive_count >= max(negative_count, neutral_count):
        primary = "Positive"
    elif negative_count >= max(positive_count, neutral_count):
        primary = "Negative"
    else:
        primary = "Neutral"
    sentiment_metrics["primary_sentiment"] = primary

    # Topic frequency counts
    topic_counts = dict(Counter(topics_list).most_common(8))

    # Rating stats if available
    avg_rating = None
    if "rating" in reviews_df.columns:
        valid_ratings = reviews_df["rating"].dropna()
        if not valid_ratings.empty:
            avg_rating = round(float(valid_ratings.mean()), 2)

    return {
        "total_reviews": total_reviews,
        "average_rating": avg_rating,
        "sentiment_metrics": sentiment_metrics,
        "topic_counts": topic_counts,
    }


def analyze_reviews_with_gemini(
    reviews_df: pd.DataFrame,
    user_question: Optional[str] = None,
    language: str = "English",
) -> Dict[str, Any]:
    """
    Main entry point for AI Customer Review Analysis with multilingual output support.

    Args:
        reviews_df: Cleaned reviews DataFrame from Milestone 2
        user_question: Optional user inquiry from composer
        language: Target output language ("English", "Tamil", or "Tanglish")

    Returns:
        Structured analysis results dictionary ready for session_state

    Raises:
        GeminiServiceError: On any unrecoverable API error with friendly message
    """
    if reviews_df is None or reviews_df.empty:
        raise GeminiServiceError("No customer reviews available to analyze.")

    target_lang = language.strip().capitalize() if language else "English"
    if target_lang not in ["English", "Tamil", "Tanglish"]:
        target_lang = "English"

    # 1. Build strictly grounded prompt in target output language
    prompt = build_analysis_prompt(
        reviews_df,
        user_question=user_question,
        language=target_lang,
    )

    # 2. Call Gemini service with exponential backoff & model fallback
    raw_ai_text = generate_structured_content(
        prompt=prompt,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    # 3. Parse and validate JSON structure
    ai_data = parse_and_validate_ai_response(raw_ai_text)

    # 4. Calculate mathematical metrics in Python
    stats = compute_numerical_statistics(reviews_df, ai_data)

    # 5. Assemble final unified payload
    final_results = {
        "output_language": target_lang,
        "summary": {
            "total_reviews": stats["total_reviews"],
            "average_rating": stats["average_rating"],
            "user_question": user_question or "General review analysis",
            "executive_summary": ai_data.get("executive_summary", ""),
            "status": "completed",
        },
        "sentiment_stats": stats["sentiment_metrics"],
        "topic_counts": stats["topic_counts"],
        "sentiment_overview": ai_data.get("sentiment_overview", {}),
        "customer_likes": ai_data.get("customer_likes", []),
        "common_complaints": ai_data.get("common_complaints", []),
        "recurring_topics": ai_data.get("recurring_topics", []),
        "actionable_recommendations": ai_data.get("actionable_recommendations", []),
        "question_response": ai_data.get("question_response", {}),
        "per_review_breakdown": ai_data.get("per_review_breakdown", []),
    }

    return final_results


def adapt_analysis_to_language(
    results: Dict[str, Any],
    target_language: str = "English",
) -> Dict[str, Any]:
    """
    Adapt/translate existing analysis narratives into target_language (English, Tamil, Tanglish).
    Reuses existing breakdown, topic counts, ratings, and numerical statistics with zero alteration.
    Preserves all original customer review quotes verbatim.
    """
    if not results or not isinstance(results, dict):
        return results

    target_lang = target_language.strip().capitalize() if target_language else "English"
    if target_lang not in ["English", "Tamil", "Tanglish"]:
        target_lang = "English"

    # If already in the target language, return as-is (0 API calls)
    if results.get("output_language") == target_lang:
        return results

    import copy
    new_results = copy.deepcopy(results)
    new_results["output_language"] = target_lang

    narrative_payload = {
        "executive_summary": new_results.get("summary", {}).get("executive_summary", ""),
        "sentiment_overview": new_results.get("sentiment_overview", {}),
        "customer_likes": [
            {
                "topic": item.get("topic", ""),
                "summary": item.get("summary", ""),
                "evidence_quote": item.get("evidence_quote", ""),
            }
            for item in new_results.get("customer_likes", [])
        ],
        "common_complaints": [
            {
                "topic": item.get("topic", ""),
                "summary": item.get("summary", ""),
                "evidence_quote": item.get("evidence_quote", ""),
            }
            for item in new_results.get("common_complaints", [])
        ],
        "recurring_topics": [
            {
                "topic": item.get("topic", ""),
                "sentiment": item.get("sentiment", ""),
                "summary": item.get("summary", ""),
                "evidence_quote": item.get("evidence_quote", ""),
            }
            for item in new_results.get("recurring_topics", [])
        ],
        "actionable_recommendations": [
            {
                "area": item.get("area", ""),
                "priority": item.get("priority", ""),
                "recommendation": item.get("recommendation", ""),
                "reasoning": item.get("reasoning", ""),
                "supporting_evidence": item.get("supporting_evidence", ""),
            }
            for item in new_results.get("actionable_recommendations", [])
        ],
        "question_response": new_results.get("question_response", {}),
    }

    if target_lang == "Tamil":
        lang_rules = (
            "Translate all narrative summaries, recommendations, reasoning, and answers into natural, fluent TAMIL script (தமிழ்).\n"
            "CRITICAL: Keep all evidence_quote and supporting_evidence strings exactly as they are without modifying a single letter.\n"
            "Keep all JSON keys, priority values ('High', 'Medium', 'Low'), and sentiment categories in English."
        )
    elif target_lang == "Tanglish":
        lang_rules = (
            "Translate all narrative summaries, recommendations, reasoning, and answers into natural conversational TANGLISH "
            "(Tamil written phonetically in English/Latin letters, e.g. 'Food romba nallarku aana delivery late', 'Service speed improve pannanum').\n"
            "CRITICAL: Keep all evidence_quote and supporting_evidence strings exactly as they are without modifying a single letter.\n"
            "Keep all JSON keys, priority values ('High', 'Medium', 'Low'), and sentiment categories in English."
        )
    else:
        lang_rules = (
            "Translate all narrative summaries, recommendations, reasoning, and answers into clear, professional English.\n"
            "CRITICAL: Keep all evidence_quote and supporting_evidence strings exactly as they are without modifying a single letter.\n"
            "Keep all JSON keys, priority values ('High', 'Medium', 'Low'), and sentiment categories in English."
        )

    adaptation_prompt = f"""
You are Mezy's Multilingual Restaurant Review Intelligence translator.
Target output language: {target_lang}.

RULES:
{lang_rules}

Translate the following JSON object into the target language ({target_lang}).
Return ONLY a valid JSON object with the exact same structure:

{json.dumps(narrative_payload, ensure_ascii=False, indent=2)}
""".strip()

    try:
        raw_text = generate_structured_content(
            prompt=adaptation_prompt,
            system_instruction="You are Mezy's Multilingual Restaurant Review Intelligence translator. Return valid JSON only.",
        )
        adapted_data = parse_and_validate_ai_response(raw_text)

        # Merge adapted fields while strictly preserving numerical stats and verbatim evidence
        if "executive_summary" in adapted_data and adapted_data["executive_summary"]:
            new_results["summary"]["executive_summary"] = adapted_data["executive_summary"]

        if "sentiment_overview" in adapted_data and adapted_data["sentiment_overview"]:
            new_results["sentiment_overview"] = adapted_data["sentiment_overview"]

        if "customer_likes" in adapted_data and adapted_data["customer_likes"]:
            for idx, item in enumerate(adapted_data["customer_likes"]):
                if idx < len(new_results["customer_likes"]):
                    orig_quote = new_results["customer_likes"][idx].get("evidence_quote", "")
                    if orig_quote:
                        item["evidence_quote"] = orig_quote
            new_results["customer_likes"] = adapted_data["customer_likes"]

        if "common_complaints" in adapted_data and adapted_data["common_complaints"]:
            for idx, item in enumerate(adapted_data["common_complaints"]):
                if idx < len(new_results["common_complaints"]):
                    orig_quote = new_results["common_complaints"][idx].get("evidence_quote", "")
                    if orig_quote:
                        item["evidence_quote"] = orig_quote
            new_results["common_complaints"] = adapted_data["common_complaints"]

        if "recurring_topics" in adapted_data and adapted_data["recurring_topics"]:
            for idx, item in enumerate(adapted_data["recurring_topics"]):
                if idx < len(new_results["recurring_topics"]):
                    orig_quote = new_results["recurring_topics"][idx].get("evidence_quote", "")
                    orig_sent = new_results["recurring_topics"][idx].get("sentiment", "")
                    if orig_quote:
                        item["evidence_quote"] = orig_quote
                    if orig_sent:
                        item["sentiment"] = orig_sent
            new_results["recurring_topics"] = adapted_data["recurring_topics"]

        if "actionable_recommendations" in adapted_data and adapted_data["actionable_recommendations"]:
            for idx, item in enumerate(adapted_data["actionable_recommendations"]):
                if idx < len(new_results["actionable_recommendations"]):
                    orig_ev = new_results["actionable_recommendations"][idx].get("supporting_evidence", "")
                    orig_p = new_results["actionable_recommendations"][idx].get("priority", "")
                    if orig_ev:
                        item["supporting_evidence"] = orig_ev
                    if orig_p:
                        item["priority"] = orig_p
            new_results["actionable_recommendations"] = adapted_data["actionable_recommendations"]

        if "question_response" in adapted_data and adapted_data["question_response"]:
            orig_ev_list = new_results.get("question_response", {}).get("supporting_evidence", [])
            if orig_ev_list:
                adapted_data["question_response"]["supporting_evidence"] = orig_ev_list
            new_results["question_response"] = adapted_data["question_response"]

    except Exception as exc:
        logger.warning(f"AI translation to {target_lang} failed: {exc}. Keeping original analysis content.")

    return new_results

