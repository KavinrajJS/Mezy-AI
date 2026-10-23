"""
src/gemini_service.py
---------------------
Secure wrapper for the Google Gemini API using the official `google-genai` SDK.

Key features:
  - Secure API key ingestion from `.env` via `config.settings`
  - Never logs, prints, or exposes API keys in exceptions or logs
  - Automatic exponential backoff retries for transient 503 / 429 errors
  - Automatic model fallback progression
  - Clean error propagation with friendly, actionable human-readable messages
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

import os
import config.settings
from config.settings import (
    GEMINI_MODEL,
    FALLBACK_MODELS,
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """Custom user-friendly exception for Gemini API failures."""
    pass


def get_gemini_client() -> genai.Client:
    """
    Initialize and return a Gemini API client securely.

    Raises:
        GeminiServiceError: If GEMINI_API_KEY is missing or invalid.
    """
    key = str(getattr(config.settings, "GEMINI_API_KEY", "")).strip()
    if not key or key == "your_actual_api_key_here":
        raise GeminiServiceError(
            "Gemini API key is not configured. "
            "Please add your actual GEMINI_API_KEY in the .env file."
        )

    try:
        return genai.Client(api_key=key)
    except Exception as exc:
        raise GeminiServiceError(
            f"Failed to initialize AI client. Please verify your API key in .env. ({type(exc).__name__})"
        )


def generate_structured_content(
    prompt: str,
    system_instruction: Optional[str] = None,
    preferred_model: Optional[str] = None,
) -> str:
    """
    Call Gemini with exponential backoff retry and model fallback.

    Args:
        prompt: User prompt content
        system_instruction: Optional system instruction for grounding
        preferred_model: Optional override for Gemini model

    Returns:
        Generated text string (usually JSON)

    Raises:
        GeminiServiceError: If all retries and fallback models fail.
    """
    client = get_gemini_client()

    models_to_try: List[str] = []
    if preferred_model:
        models_to_try.append(preferred_model)
    if GEMINI_MODEL not in models_to_try:
        models_to_try.append(GEMINI_MODEL)
    for fm in FALLBACK_MODELS:
        if fm not in models_to_try:
            models_to_try.append(fm)

    last_error_msg = ""

    for model_name in models_to_try:
        delay = RETRY_DELAY_SECONDS
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    system_instruction=system_instruction if system_instruction else None,
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )

                if response and response.text:
                    return response.text.strip()
                else:
                    raise GeminiServiceError("The AI model returned an empty response. Please retry.")

            except genai_errors.ClientError as exc:
                err_str = str(exc)
                if "404" in err_str:
                    # Model deprecated or unavailable for this tier — break to next model in fallback
                    last_error_msg = f"Model {model_name} is unavailable."
                    break
                elif "400" in err_str or "API_KEY_INVALID" in err_str or "403" in err_str:
                    raise GeminiServiceError(
                        "Your Gemini API key appears to be invalid or lacks permissions. "
                        "Please verify your key at aistudio.google.com and update your .env file."
                    )
                elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    last_error_msg = f"Rate limit reached for {model_name}."
                    if "quota" in err_str.lower():
                        # Daily quota exceeded for this model, immediately move to fallback model
                        break
                    if attempt < MAX_RETRIES:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        break
                else:
                    last_error_msg = f"AI request error: {type(exc).__name__}"
                    if attempt < MAX_RETRIES:
                        time.sleep(delay)
                        delay *= 1.5

            except genai_errors.ServerError as exc:
                # 503 high demand or temporary server hiccup — back off and retry
                last_error_msg = f"Temporary service spike ({type(exc).__name__}). Retrying..."
                if attempt < MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 2
                else:
                    break

            except Exception as exc:
                last_error_msg = f"Unexpected error during AI analysis: {type(exc).__name__}"
                if attempt < MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 1.5

    raise GeminiServiceError(
        f"Unable to complete AI analysis at this time. {last_error_msg} "
        "Please check your internet connection or try again in a few moments."
    )


def verify_api_connectivity() -> Tuple[bool, str]:
    """
    Quick non-throwing connectivity check for testing.

    Returns:
        (success: bool, status_message: str)
    """
    try:
        resp = generate_structured_content(
            prompt='Return a JSON object: {"status": "connected", "service": "Mezy AI"}',
            system_instruction="You are Mezy review analyzer. Respond with valid JSON only.",
        )
        data = json.loads(resp)
        if data.get("status") == "connected":
            return True, "Successfully connected to Gemini API."
        return True, f"Connected with response: {resp[:60]}"
    except Exception as exc:
        return False, str(exc)
