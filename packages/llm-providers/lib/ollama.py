# SCOPE: both
"""Ollama local LLM provider wrapper (ADR-062 tier 4).

Ollama runs local models via an OpenAI-compatible endpoint. Default cascade tier 4
(zero cost, quality varies by hardware and installed models).

No API key required. is_configured() checks if the Ollama daemon is reachable at
http://localhost:11434/v1/models. Returns False if the daemon is not running or
not reachable — this allows the cascade to skip Ollama gracefully.

Configuration:
    OLLAMA_BASE_URL  — optional override (default: http://localhost:11434/v1)
    OLLAMA_HOST      — optional hostname override (default: localhost)
    OLLAMA_PORT      — optional port override (default: 11434)

No API key needed. Set enabled: true in cognitive-os.yaml.

Advance policy: advance on timeout (local can be slow or unavailable).

Model availability depends on what the operator has pulled. Default model map
assumes large-RAM machine (40GB+). Smaller defaults can be set via env.

Reference: docs/02-Decisions/adrs/ADR-062-multi-provider-agent-loop.md
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

def _base_url() -> str:
    if os.environ.get("OLLAMA_BASE_URL"):
        return os.environ["OLLAMA_BASE_URL"].rstrip("/")
    host = os.environ.get("OLLAMA_HOST", "localhost")
    port = os.environ.get("OLLAMA_PORT", "11434")
    return f"http://{host}:{port}/v1"


DEFAULT_MODEL = "qwen3:32b"

MODEL_MAP: Dict[str, str] = {
    "opus":   "llama3.3:70b",   # requires ~40GB RAM
    "sonnet": "qwen3:32b",       # ~20GB RAM
    "haiku":  "llama3.2:3b",    # ~2GB RAM
}

# Ollama is free (local compute only). Cost is 0.
_COST_ESTIMATES: Dict[str, tuple[float, float]] = {}


# ── Provider interface ────────────────────────────────────────────────────────

def _check_daemon_reachable(timeout: float = 3.0) -> bool:
    """Return True if Ollama daemon responds at the configured endpoint."""
    try:
        import urllib.request
        import urllib.error
        url = _base_url().rstrip("/v1").rstrip("/") + "/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


def is_configured() -> bool:
    """True iff Ollama daemon is reachable at the configured endpoint.

    No API key required — checks liveness of the local daemon.
    """
    return _check_daemon_reachable()


def get_client() -> Any:
    """Return an OpenAI-compatible client pointed at the Ollama endpoint.

    Returns None if openai SDK is not installed or daemon is not reachable.
    """
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None

    # Ollama accepts any non-empty string as API key
    return OpenAI(api_key="ollama", base_url=_base_url())


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:  # noqa: ARG001
    """Ollama is free (local compute). Always returns 0.0."""
    return 0.0


def call(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: float = 120.0,
    model_hint: Optional[str] = None,
    **kwargs: Any,
) -> dict:
    """Call Ollama local model. Returns a normalized response dict.

    Note: Ollama model must be installed (`ollama pull <model>`) before use.
    Advance policy: advance on timeout or any failure.
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
            "error": "Ollama unavailable: daemon not reachable or openai SDK missing",
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
            "cost_usd": 0.0,
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
