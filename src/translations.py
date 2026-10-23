"""
src/translations.py
--------------------
Static UI strings for English, Tamil, and Tanglish.

Only UI labels are translated here.
AI-generated content (summaries, recommendations) will use the
selected language directly via a Gemini prompt instruction.

Usage:
    from src.translations import t
    heading = t("overview_heading", lang="Tamil")
"""

_STRINGS: dict[str, dict[str, str]] = {
    # ── Navigation ────────────────────────────────────────────────────
    "nav_home":             {"English": "Home",               "Tamil": "முகப்பு",          "Tanglish": "Home"},
    "nav_overview":         {"English": "Overview",           "Tamil": "கண்ணோட்டம்",       "Tanglish": "Overview"},
    "nav_review_analysis":  {"English": "Review Analysis",    "Tamil": "விமர்சன பகுப்பாய்வு", "Tanglish": "Review Analysis"},
    "nav_topic_explorer":   {"English": "Topic Explorer",     "Tamil": "தலைப்பு ஆய்வு",    "Tanglish": "Topic Explorer"},
    "nav_action_tracker":   {"English": "Action Tracker",     "Tamil": "நடவடிக்கை கண்காணிப்பு", "Tanglish": "Action Tracker"},

    # ── Home / hero ───────────────────────────────────────────────────
    "hero_heading":         {"English": "Understand Your Customers.",
                             "Tamil":   "உங்கள் வாடிக்கையாளர்களை புரிந்துகொள்ளுங்கள்.",
                             "Tanglish":"Unga Customers-a Purinjukollunga."},
    "hero_tagline":         {"English": "Complexity turned into Simplicity.",
                             "Tamil":   "சிக்கலை எளிமையாக மாற்றுகிறோம்.",
                             "Tanglish":"Complexity-a Simplicity-a maathrom."},
    "hero_description":     {"English": "Turn customer reviews into clear insights and practical improvements for your restaurant.",
                             "Tamil":   "வாடிக்கையாளர் விமர்சனங்களை உங்கள் உணவகத்திற்கான தெளிவான நுண்ணறிவாக மாற்றுங்கள்.",
                             "Tanglish":"Customer reviews-a clear insights-a convert pannunga unga restaurant ku."},

    # ── Buttons ───────────────────────────────────────────────────────
    "btn_analyse":          {"English": "✦ Analyse Reviews",  "Tamil": "✦ பகுப்பாய்வு",    "Tanglish": "✦ Analyse Pannunga"},
    "btn_sample":           {"English": "Use Sample Data",    "Tamil": "மாதிரி தரவு",       "Tanglish": "Sample Data Upottunga"},
    "btn_export_pdf":       {"English": "Export PDF",         "Tamil": "PDF ஏற்றுமதி",      "Tanglish": "PDF Export Pannu"},
    "btn_export_word":      {"English": "Export Word",        "Tamil": "Word ஏற்றுமதி",     "Tanglish": "Word Export Pannu"},
    "btn_export_csv":       {"English": "Export CSV",         "Tamil": "CSV ஏற்றுமதி",      "Tanglish": "CSV Export Pannu"},
    "btn_new_analysis":     {"English": "🔄 New Analysis",    "Tamil": "🔄 புதிய பகுப்பாய்வு", "Tanglish": "🔄 New Analysis"},

    # ── Loading messages ───────────────────────────────────────────────
    "loading_preparing":    {"English": "Analyzing customer reviews…",
                             "Tamil":   "வாடிக்கையாளர் விமர்சனங்களை பகுப்பாய்கிறோம்…",
                             "Tanglish":"Customer reviews-a analyse pannuroam…"},
    "loading_analysing":    {"English": "Analyzing customer reviews…",
                             "Tamil":   "வாடிக்கையாளர் கருத்துகளை பகுப்பாய்கிறோம்…",
                             "Tanglish":"Customer feedback-a analyse panna paakarom…"},
    "loading_insights":     {"English": "Calculating insights…",
                             "Tamil":   "நுண்ணறிவுகளை கணக்கிடுகிறோம்…",
                             "Tanglish":"Insights calculate panna paakarom…"},
    "loading_dashboard":    {"English": "Preparing your dashboard…",
                             "Tamil":   "டாஷ்போர்டை தயாரிக்கிறோம்…",
                             "Tanglish":"Dashboard ready panna paakarom…"},
    "loading_done":         {"English": "Analysis complete ✓",
                             "Tamil":   "பகுப்பாய்வு முடிந்தது ✓",
                             "Tanglish":"Analysis complete ✓"},

    # ── Overview labels ────────────────────────────────────────────────
    "total_reviews":        {"English": "Total Reviews",      "Tamil": "மொத்த விமர்சனங்கள்",  "Tanglish": "Total Reviews"},
    "positive":             {"English": "Positive",           "Tamil": "நேர்மறை",              "Tanglish": "Positive"},
    "negative":             {"English": "Negative",           "Tamil": "எதிர்மறை",             "Tanglish": "Negative"},
    "neutral":              {"English": "Neutral",            "Tamil": "நடுநிலை",              "Tanglish": "Neutral"},
    "mixed":                {"English": "Mixed",              "Tamil": "கலப்பு",               "Tanglish": "Mixed"},
    "uncertain":            {"English": "Uncertain",          "Tamil": "நிச்சயமற்றது",         "Tanglish": "Uncertain"},
    "overview_heading":     {"English": "Executive Review Intelligence",
                             "Tamil":   "நிர்வாக விமர்சன நுண்ணறிவு",
                             "Tanglish":"Executive Review Intelligence"},
    "overview_subheading":  {"English": "AI-powered synthesized insights grounded directly in customer feedback.",
                             "Tamil":   "வாடிக்கையாளர் கருத்துகளின் அடிப்படையில் உருவாக்கப்பட்ட AI நுண்ணறிவு.",
                             "Tanglish":"Customer feedback moolamaaga uruvaakkappatta AI insights."},
    "multilingual_notice":  {"English": "AI multilingual intelligence (English, Tamil, Tanglish). Dialect phrasing may vary.",
                             "Tamil":   "பன்மொழி AI நுண்ணறிவு (ஆங்கிலம், தமிழ், தங்கிலீஷ்). வட்டார வழக்கு மாறுபடலாம்.",
                             "Tanglish":"AI multilingual intelligence (English, Tamil, Tanglish). Dialect phrasing vary aagalaam."},
    "question_inquiry":     {"English": "Question Inquiry",   "Tamil": "கேள்வி விசாரணை",      "Tanglish": "Question Inquiry"},
    "supporting_quotes":    {"English": "Supporting Quotes:", "Tamil": "ஆதார மேற்கோள்கள்:",   "Tanglish": "Supporting Quotes:"},
    "executive_summary":    {"English": "Executive Summary",  "Tamil": "நிர்வாக சுருக்கம்",     "Tanglish": "Executive Summary"},
    "sentiment_breakdown":  {"English": "Sentiment Breakdown", "Tamil": "மனநிலை முறிவு",        "Tanglish": "Sentiment Breakdown"},
    "reviews_count":        {"English": "Reviews",            "Tamil": "விமர்சனங்கள்",         "Tanglish": "Reviews"},
    "positive_label":       {"English": "Positive",           "Tamil": "நேர்மறை",              "Tanglish": "Positive"},
    "negative_label":       {"English": "Negative",           "Tamil": "எதிர்மறை",             "Tanglish": "Negative"},
    "neutral_mix_label":    {"English": "Neutral/Mix",        "Tamil": "நடுநிலை/கலப்பு",       "Tanglish": "Neutral/Mix"},
    "what_customers_like":  {"English": "✦ What Customers Like Most",
                             "Tamil":   "✦ வாடிக்கையாளர்கள் அதிகம் விரும்புவது",
                             "Tanglish":"✦ Customers Romba Like Pannuvadhu"},
    "common_complaints":    {"English": "⚠ Common Complaints & Friction",
                             "Tamil":   "⚠ பொதுவான புகார்கள் & குறைபாடுகள்",
                             "Tanglish":"⚠ Common Complaints & Friction"},
    "business_recommendations": {"English": "💡 Practical Business Recommendations",
                                 "Tamil":   "💡 பயனுள்ள வணிக பரிந்துரைகள்",
                                 "Tanglish":"💡 Practical Business Recommendations"},
    "priority_high":        {"English": "High Priority",      "Tamil": "அதிக முன்னுரிமை",       "Tanglish": "High Priority"},
    "priority_medium":      {"English": "Medium Priority",    "Tamil": "நடுத்தர முன்னுரிமை",    "Tanglish": "Medium Priority"},
    "priority_low":         {"English": "Low Priority",       "Tamil": "குறைந்த முன்னுரிமை",    "Tanglish": "Low Priority"},
    "reasoning_label":      {"English": "Reasoning:",         "Tamil": "காரணம்:",              "Tanglish": "Reasoning:"},
    "evidence_label":       {"English": "Evidence:",          "Tamil": "ஆதாரம்:",              "Tanglish": "Evidence:"},
    "no_likes_msg":         {"English": "No dominant praise patterns detected in this dataset.",
                             "Tamil":   "இந்த தரவில் குறிப்பிடத்தக்க பாராட்டு முறைகள் எதுவும் கண்டறியப்படவில்லை.",
                             "Tanglish":"Indha dataset-la periya praise patterns edhuvum illa."},
    "no_complaints_msg":    {"English": "No significant complaint patterns detected.",
                             "Tamil":   "குறிப்பிடத்தக்க புகார் முறைகள் எதுவும் கண்டறியப்படவில்லை.",
                             "Tanglish":"Periya complaint patterns edhuvum illa."},
    "sidebar_main_menu":    {"English": "MAIN MENU",          "Tamil": "முதன்மை மெனு",         "Tanglish": "MAIN MENU"},
    "sidebar_output_language": {"English": "OUTPUT LANGUAGE", "Tamil": "வெளியீட்டு மொழி",      "Tanglish": "OUTPUT LANGUAGE"},
    "sidebar_active_dataset":  {"English": "ACTIVE DATASET",  "Tamil": "செயலில் உள்ள தரவு",    "Tanglish": "ACTIVE DATASET"},
    "reviews_loaded":       {"English": "reviews loaded",     "Tamil": "விமர்சனங்கள் ஏற்றப்பட்டன", "Tanglish": "reviews loaded"},
    "btn_reset":            {"English": "Reset Dataset",      "Tamil": "தரவை மீட்டமை",         "Tanglish": "Reset Dataset"},

    # ── Error / status messages ────────────────────────────────────────
    "err_no_data":          {"English": "Please upload a CSV, paste some reviews, or use the sample data.",
                             "Tamil":   "CSV பதிவேற்றவும், சில விமர்சனங்களை ஒட்டவும், அல்லது மாதிரி தரவை பயன்படுத்தவும்.",
                             "Tanglish":"CSV upload pannunga, reviews paste pannunga, illana sample data use pannunga."},
    "err_missing_col":      {"English": "CSV must contain a 'review_text' column.",
                             "Tamil":   "CSV-ல் 'review_text' நெடுவரிசை இருக்க வேண்டும்.",
                             "Tanglish":"CSV-la 'review_text' column vennum."},

    # ── Action Tracker & Reports (Milestone 6) ─────────────────────────
    "action_tracker_title":    {"English": "Action Tracker",
                                "Tamil":   "நடவடிக்கை கண்காணிப்பு",
                                "Tanglish":"Action Tracker"},
    "action_tracker_subtitle": {"English": "Prioritize operational improvements and turn customer feedback into resolved tasks.",
                                "Tamil":   "வாடிக்கையாளர் கருத்துகளை முன்னுரிமைப்படுத்தப்பட்ட பணிகளாக மாற்றி கண்காணிக்கவும்.",
                                "Tanglish":"Customer feedback-a prioritized tasks-a maathi track pannunga."},
    "stat_total_actions":      {"English": "Total Actions",
                                "Tamil":   "மொத்த நடவடிக்கைகள்",
                                "Tanglish":"Total Actions"},
    "stat_open_actions":       {"English": "Open",
                                "Tamil":   "திறந்தவை",
                                "Tanglish":"Open"},
    "stat_in_progress":        {"English": "In Progress",
                                "Tamil":   "செயலில் உள்ளவை",
                                "Tanglish":"In Progress"},
    "stat_resolved":           {"English": "Resolved",
                                "Tamil":   "தீர்க்கப்பட்டவை",
                                "Tanglish":"Resolved"},
    "create_action_heading":   {"English": "Create New Action",
                                "Tamil":   "புதிய நடவடிக்கை உருவாக்கு",
                                "Tanglish":"New Action Create Pannu"},
    "field_title":             {"English": "Issue Title",
                                "Tamil":   "சிக்கல் தலைப்பு",
                                "Tanglish":"Issue Title"},
    "field_action":            {"English": "Suggested Action",
                                "Tamil":   "பரிந்துரைக்கப்பட்ட நடவடிக்கை",
                                "Tanglish":"Suggested Action"},
    "field_priority":          {"English": "Priority",
                                "Tamil":   "முன்னுரிமை",
                                "Tanglish":"Priority"},
    "field_status":            {"English": "Status",
                                "Tamil":   "நிலை",
                                "Tanglish":"Status"},
    "field_evidence":          {"English": "Supporting Customer Review Evidence",
                                "Tamil":   "வாடிக்கையாளர் ஆதார மேற்கோள்",
                                "Tanglish":"Customer Evidence Quote"},
    "field_notes":             {"English": "Internal Notes",
                                "Tamil":   "உள் குறிப்புகள்",
                                "Tanglish":"Internal Notes"},
    "btn_save_action":         {"English": "✓ Save Action",
                                "Tamil":   "✓ நடவடிக்கையை சேமி",
                                "Tanglish":"✓ Action Save Pannu"},
    "btn_update_action":       {"English": "Update Action",
                                "Tamil":   "நடவடிக்கையை புதுப்பி",
                                "Tanglish":"Update Action"},
    "btn_delete_action":       {"English": "Delete",
                                "Tamil":   "நீக்கு",
                                "Tanglish":"Delete"},
    "export_reports_heading":  {"English": "Download Executive Intelligence Report",
                                "Tamil":   "நிர்வாக நுண்ணறிவு அறிக்கையை பதிவிறக்கவும்",
                                "Tanglish":"Executive Intelligence Report Download"},
    "select_report_lang":      {"English": "Report Language",
                                "Tamil":   "அறிக்கை மொழி",
                                "Tanglish":"Report Language"},
    "select_report_format":    {"English": "Download Format",
                                "Tamil":   "பதிவிறக்க வடிவம்",
                                "Tanglish":"Download Format"},
    "btn_generate_report":     {"English": "📥 Generate Report",
                                "Tamil":   "📥 அறிக்கையை உருவாக்கு",
                                "Tanglish":"📥 Generate Report"},
}


def t(key: str, lang: str = "English") -> str:
    """Return the UI string for *key* in *lang*.

    Falls back to English if the key or language is missing.
    """
    entry = _STRINGS.get(key)
    if entry is None:
        return key  # return the key itself as a fallback
    return entry.get(lang, entry.get("English", key))
