# SCOPE: both
"""OpenRouter provider wrapper (ADR-062 tier 2).

OpenRouter aggregates 100+ models (free + paid) behind a single OpenAI-compatible
endpoint. Default cascade tier 2 — advances on any failure (free tier has rate
limits and unavailability; treat as best-effort).

Configuration:
    OPENROUTER_API_KEY   — from openrouter.ai dashboard

Reference: docs/02-Decisions/adrs/ADR-062-multi-provider-agent-loop.md
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter/auto"

MODEL_MAP: Dict[str, str] = {
    "opus":   "anthropic/claude-3-opus",  # or openrouter/auto for cost-driven routing
    "sonnet": "meta-llama/llama-3-70b",
    "haiku":  "openrouter/auto",
}

# OpenRouter pricing is model-dependent. Using conservative estimates for the
# default model; actual billing depends on which model openrouter/auto selects.
_COST_ESTIMATES: Dict[str, tuple[float, float]] = {
    "openrouter/auto":              (1.0, 3.0),   # varies by selected model
    "anthropic/claude-3-opus":      (15.0, 75.0),
    "meta-llama/llama-3-70b":       (0.59, 0.79),
    "qwen/qwen3-32b:free":          (0.0, 0.0),
    "nvidia/llama-3.1-nemotron-ultra-253b:free": (0.0, 0.0),
}


# ── Provider interface ────────────────────────────────────────────────────────

def is_configured() -> bool:
    """True iff OPENROUTER_API_KEY is set (non-empty)."""
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def get_client() -> Any:
    """Return an OpenAI-compatible client pointed at OpenRouter.

    Returns None if openai SDK is not installed or API key is missing.
    """
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None

    return OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/luum-ai/luum-agent-os",
            "X-Title": "luum-cognitive-os",
        },
    )


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    rates = _COST_ESTIMATES.get(model)
    if rates is None:
        rates = _COST_ESTIMATES["openrouter/auto"]
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
    """Call OpenRouter with a messages array. Returns a normalized response dict.

    Note: advance on any failure — OpenRouter free tier has availability limits.
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
            "error": "OpenRouter unavailable: OPENROUTER_API_KEY unset or openai SDK missing",
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
        # OpenRouter passes the actual model used in the response
        used_model = getattr(response, "model", model) or model
        return {
            "success": True,
            "text": text,
            "model": used_model,
            "tokens_in": ti,
            "tokens_out": to,
            "cost_usd": estimate_cost(used_model, ti, to),
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
