# SCOPE: both
"""DeepSeek provider wrapper (ADR-062 opt-in).

DeepSeek exposes an OpenAI-compatible API with strong reasoning (deepseek-reasoner)
and cost-effective coding (deepseek-chat). Opt-in only — requires DEEPSEEK_API_KEY.

Advance policy: advance on any failure (cost-effective but less reliable than
Claude or OpenAI for production use; treat failures as transient).

Configuration:
    DEEPSEEK_API_KEY  — from platform.deepseek.com

Reference: docs/adrs/ADR-062-multi-provider-agent-loop.md
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

MODEL_MAP: Dict[str, str] = {
    "opus":   "deepseek-reasoner",
    "sonnet": "deepseek-chat",
    "haiku":  "deepseek-chat",
}

_COST_ESTIMATES: Dict[str, tuple[float, float]] = {
    "deepseek-reasoner": (0.55, 2.19),
    "deepseek-chat":     (0.014, 0.28),  # cache-miss pricing (off-peak)
}


# ── Provider interface ────────────────────────────────────────────────────────

def is_configured() -> bool:
    """True iff DEEPSEEK_API_KEY is set (non-empty)."""
    return bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())


def get_client() -> Any:
    """Return an OpenAI-compatible client pointed at DeepSeek.

    Returns None if openai SDK is not installed or API key is missing.
    """
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None

    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return None

    return OpenAI(api_key=api_key, base_url=BASE_URL)


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    rates = _COST_ESTIMATES.get(model)
    if rates is None:
        rates = _COST_ESTIMATES["deepseek-chat"]
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
    """Call DeepSeek API. Returns a normalized response dict.

    Note: deepseek-reasoner produces chain-of-thought; content field contains
    the final answer only (reasoning_content is stripped for cost efficiency).
    Advance on any failure.
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
            "error": "DeepSeek unavailable: DEEPSEEK_API_KEY unset or openai SDK missing",
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
            if msg is not None:
                # Prefer content (final answer) over reasoning_content
                text = getattr(msg, "content", "") or ""
                if not text:
                    # Fallback: some deepseek-reasoner responses put answer in reasoning_content
                    text = getattr(msg, "reasoning_content", "") or ""
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
