# SCOPE: both
"""Google Gemini provider wrapper via OpenAI-compat endpoint (ADR-062 tier 3).

Google exposes an OpenAI-compatible endpoint for Gemini models.
Default cascade tier 3 — advances on any failure (free tier has rate limits).

Quirk: Gemini model names use a different naming scheme ("gemini-2.0-flash"
vs openai "gpt-4o"). The MODEL_MAP handles this translation. The endpoint
requires the API key in the standard Authorization header, which the OpenAI
SDK handles correctly.

Configuration:
    GEMINI_API_KEY   — from Google AI Studio (aistudio.google.com)

Reference: docs/02-Decisions/adrs/ADR-062-multi-provider-agent-loop.md
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-2.0-flash"

MODEL_MAP: Dict[str, str] = {
    "opus":   "gemini-2.0-pro",
    "sonnet": "gemini-2.0-flash",
    "haiku":  "gemini-2.0-flash-lite",
}

# Gemini pricing (free tier is rate-limited; paid is per 1M tokens)
_COST_ESTIMATES: Dict[str, tuple[float, float]] = {
    "gemini-2.0-pro":        (3.50, 10.50),
    "gemini-2.0-flash":      (0.10,  0.40),
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-1.5-pro":        (3.50, 10.50),
    "gemini-1.5-flash":      (0.35,  1.05),
}


# ── Provider interface ────────────────────────────────────────────────────────

def is_configured() -> bool:
    """True iff GEMINI_API_KEY is set (non-empty)."""
    return bool(os.environ.get("GEMINI_API_KEY", "").strip())


def get_client() -> Any:
    """Return an OpenAI-compatible client pointed at Google's Gemini endpoint.

    Returns None if openai SDK is not installed or API key is missing.

    Note: Gemini's OpenAI-compat endpoint uses the same Authorization header
    format as OpenAI. The openai SDK handles this transparently via base_url.
    """
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    return OpenAI(api_key=api_key, base_url=BASE_URL)


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    rates = _COST_ESTIMATES.get(model)
    if rates is None:
        rates = _COST_ESTIMATES["gemini-2.0-flash"]
    return (tokens_in * rates[0] + tokens_out * rates[1]) / 1_000_000


def call(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: float = 120.0,
    model_hint: Optional[str] = None,
    **kwargs: Any,
) -> dict:
    """Call Gemini via OpenAI-compat endpoint. Returns a normalized response dict.

    Quirk: Gemini's compat endpoint may return different finish_reason values
    ("STOP" vs "stop"). The response parser handles this defensively.

    Note: advance on any failure — free tier is rate-limited.
    """
    if model_hint:
        model = MODEL_MAP.get(model_hint, DEFAULT_MODEL)

    client = get_client()
    if client is None:
        return {
            "success": False,
            "text": "",
            "model": model,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "error": "Gemini unavailable: GEMINI_API_KEY unset or openai SDK missing",
        }

    call_kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "timeout": timeout,
    }
    if max_tokens is not None:
        call_kwargs["max_tokens"] = max_tokens
    if temperature is not None:
        call_kwargs["temperature"] = temperature

    try:
        response = client.chat.completions.create(**call_kwargs)
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "text": "",
            "model": model,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "error": str(exc)[:500],
        }

    try:
        choices = getattr(response, "choices", None) or []
        text = ""
        if choices:
            msg = getattr(choices[0], "message", None)
            text = getattr(msg, "content", "") or "" if msg else ""
        usage = getattr(response, "usage", None)
        ti = getattr(usage, "prompt_tokens", 0) if usage else 0
        to = getattr(usage, "completion_tokens", 0) if usage else 0
        return {
            "success": True,
            "text": text,
            "model": model,
            "tokens_in": ti,
            "tokens_out": to,
            "cost_usd": estimate_cost(model, ti, to),
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "text": "",
            "model": model,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "error": f"response-parse error: {exc!r}"[:500],
        }
