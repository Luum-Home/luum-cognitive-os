# SCOPE: both
"""OpenAI provider wrapper (ADR-062 opt-in).

Uses OpenAI's native API for ChatGPT-5.x/Codex. Opt-in only — requires
OPENAI_API_KEY to be set. Paid per-token.

Advance policy: advance ONLY on rate-limit errors (paid tier — failures are
usually real errors, not transient). Setting COS_DISABLE_LLM_FALLBACK=1 will
prevent advance even on rate limits.

Configuration:
    OPENAI_API_KEY  — from platform.openai.com

Reference: docs/02-Decisions/adrs/ADR-062-multi-provider-agent-loop.md
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o"  # fallback if model_hint is unrecognized

MODEL_MAP: Dict[str, str] = {
    "opus":   "gpt-5.5",
    "sonnet": "gpt-5.4",
    "haiku":  "gpt-5.4-mini",
}

_COST_ESTIMATES: Dict[str, tuple[float, float]] = {
    "gpt-5.5":      (15.0, 75.0),
    "gpt-5.4":      (3.0,  15.0),
    "gpt-5.4-mini": (0.15,  0.60),
    "gpt-4o":       (2.50, 10.0),
    "gpt-4o-mini":  (0.15,  0.60),
}


# ── Provider interface ────────────────────────────────────────────────────────

def is_configured() -> bool:
    """True iff OPENAI_API_KEY is set (non-empty).

    This is an opt-in provider — key must be explicitly provided.
    """
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def get_client() -> Any:
    """Return an OpenAI client. Returns None if SDK not installed or key missing."""
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    return OpenAI(api_key=api_key, base_url=BASE_URL)


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    rates = _COST_ESTIMATES.get(model)
    if rates is None:
        rates = _COST_ESTIMATES["gpt-4o"]
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
    """Call OpenAI API. Returns a normalized response dict.

    Advance policy: ONLY advance on rate-limit errors. Paid tier — real
    errors (auth, content policy, model unavailable) should not silently
    degrade to a cheaper provider.
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
            "error": "OpenAI unavailable: OPENAI_API_KEY unset or openai SDK missing",
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
