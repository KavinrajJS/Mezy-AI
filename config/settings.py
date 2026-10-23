"""
config/settings.py
------------------
Central configuration for Mezy.

All constants, paths, and environment-level settings live here.
Other modules import from this file — never hardcode values elsewhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # project root

DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

# SQLite database is stored in a local data directory, not committed to Git
DB_PATH = DATA_DIR / "mezy.db"

# ── Environment ────────────────────────────────────────────────────────────
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ── Gemini model ───────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-flash-lite-latest"
FALLBACK_MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
]

# ── Analysis settings ──────────────────────────────────────────────────────
BATCH_SIZE = 15          # reviews sent to Gemini per API call
MAX_RETRIES = 3          # maximum retry attempts on API failure
RETRY_DELAY_SECONDS = 2  # initial delay between retries (exponential back-off)

# ── Supported languages ────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "English": "en",
    "Tamil": "ta",
    "Tanglish": "tanglish",
}

# ── Sentiment labels ───────────────────────────────────────────────────────
SENTIMENT_LABELS = ["Positive", "Negative", "Neutral", "Mixed", "Uncertain"]

# ── Topic categories ───────────────────────────────────────────────────────
TOPIC_CATEGORIES = [
    "Food Quality",
    "Taste",
    "Portion Size",
    "Waiting Time",
    "Delivery",
    "Staff Behaviour",
    "Cleanliness",
    "Price & Value",
    "Packaging",
    "Ambiance & Facilities",
    "Overall Experience",
]

# ── Colour palette (used by charts and CSS) ────────────────────────────────
COLOURS = {
    "positive": "#22c55e",
    "negative": "#ef4444",
    "neutral": "#94a3b8",
    "mixed": "#f59e0b",
    "uncertain": "#a78bfa",
    "primary": "#6366f1",
    "primary_light": "#818cf8",
    "surface": "#ffffff",
    "background": "#f8fafc",
    "border": "#e2e8f0",
    "text_primary": "#0f172a",
    "text_secondary": "#64748b",
}
