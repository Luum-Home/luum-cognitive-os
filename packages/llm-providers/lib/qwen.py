# SCOPE: both
"""Alibaba Qwen provider wrapper (ADR-062).

Extracted from lib/qwen_provider.py — that module remains as a backward-compat
shim that re-exports everything from here. This wrapper exposes the canonical
provider interface: is_configured(), get_client(), MODEL_MAP, call().

Reference: docs/adrs/ADR-062-multi-provider-agent-loop.md
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3.6-plus"

MODEL_MAP: Dict[str, str] = {
    "opus":   "qwen3.6-plus",
    "sonnet": "qwen3-coder-plus",
    "haiku":  "qwen3-coder-plus",  # minimax-m2.5 not callable on current plan
}

# Approximate cost per 1M tokens (quota-based subscription, used only for estimates)
_COST_ESTIMATES: Dict[str, tuple[float, float]] = {
    "qwen3.6-plus":          (0.325, 1.95),
    "qwen3-coder-plus":      (0.30,  1.60),
    "qwen3-coder-next":      (0.35,  1.80),
    "qwen3-max-2026-01-23":  (0.40,  2.00),
    "qwen3.5-plus":          (0.28,  1.70),
    "kimi-k2.5":             (0.50,  2.00),
    "glm-5":                 (1.40,  4.40),
    "minimax-m2.5":          (0.30,  1.20),
    "glm-4.7":               (0.80,  2.40),
}


# ── Env helpers ───────────────────────────────────────────────────────────────

def _load_dotenv_once() -> None:
    """Best-effort: load .env ALIBABA_QWEN_* vars into os.environ (idempotent)."""
    flag = "_COS_QWEN_DOTENV_LOADED"
    if os.environ.get(flag) == "1":
        return
    try:
        from pathlib import Path as _P
        env_path = _P(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key.startswith("ALIBABA_QWEN_") and key not in os.environ:
                    os.environ[key] = val
    except Exception:  # noqa: BLE001
        pass
    os.environ[flag] = "1"


def _env(name: str, default: str = "") -> str:
    if name.startswith("ALIBABA_QWEN_"):
        _load_dotenv_once()
    return os.environ.get(name, default)


# ── Provider interface ────────────────────────────────────────────────────────

def is_configured() -> bool:
    """True iff ALIBABA_QWEN_API_KEY is set (non-empty)."""
    return bool(_env("ALIBABA_QWEN_API_KEY"))


def get_client() -> Any:
    """Return an OpenAI-compatible client pointed at Alibaba's endpoint.

    Returns None if openai SDK is not installed or API key is missing.
    """
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        return None

    api_key = _env("ALIBABA_QWEN_API_KEY")
    if not api_key:
        return None

    base_url = _env("ALIBABA_QWEN_BASE_URL", DEFAULT_BASE_URL)
    return OpenAI(api_key=api_key, base_url=base_url)


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate USD cost (dry-run only — billing is flat-rate subscription)."""
    rates = _COST_ESTIMATES.get(model)
    if rates is None:
        return 0.0
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
    """Call Qwen with a messages array. Returns a normalized response dict.

    Args:
        messages: OpenAI-format message list.
        model: model name. Ignored if model_hint is provided.
        max_tokens: optional completion cap.
        temperature: optional sampling temperature.
        timeout: request timeout in seconds.
        model_hint: abstract tier ("opus"/"sonnet"/"haiku") — mapped via MODEL_MAP.

    Returns:
        dict with keys: success, text, model, tokens_in, tokens_out, cost_usd, error.
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
            "error": "Qwen unavailable: ALIBABA_QWEN_API_KEY unset or openai SDK missing",
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


# ── Legacy compatibility helpers (used by qwen_provider.py shim) ─────────────

CLAUDE_TO_QWEN_MAP = MODEL_MAP  # alias for backward compat

RECOMMENDED_MODELS: Dict[str, Any] = {
    "qwen3.6-plus":          {"vision": True,  "context": 1_000_000, "role": "primary"},
    "kimi-k2.5":             {"vision": True,  "context": 200_000,   "role": "alt-reasoning"},
    "glm-5":                 {"vision": False, "context": 200_000,   "role": "alt-code"},
    "minimax-m2.5":          {"vision": False, "context": 200_000,   "role": "bulk"},
    "qwen3.5-plus":          {"vision": True,  "context": 128_000,   "role": "fallback"},
    "qwen3-max-2026-01-23":  {"vision": False, "context": 256_000,   "role": "flagship-qwen"},
    "qwen3-coder-next":      {"vision": False, "context": 256_000,   "role": "code-specialist"},
    "qwen3-coder-plus":      {"vision": False, "context": 256_000,   "role": "code-tier2"},
    "glm-4.7":               {"vision": False, "context": 128_000,   "role": "code-older"},
}


def map_claude_model_to_qwen(claude_model: Optional[str]) -> str:
    """Map a Claude model tier or full model name to Qwen bundle equivalent."""
    if not claude_model:
        return DEFAULT_MODEL
    name = claude_model.lower()
    for tier, qwen_m in MODEL_MAP.items():
        if tier in name:
            return qwen_m
    return DEFAULT_MODEL


def select_model(
    task: str = "general",
    need_vision: bool = False,
    need_long_context: bool = False,
    claude_model_hint: Optional[str] = None,
) -> str:
    """Pick a model from the subscription bundle based on task needs."""
    if claude_model_hint and not need_long_context and not need_vision:
        return map_claude_model_to_qwen(claude_model_hint)
    if need_long_context:
        return "qwen3.6-plus"
    if need_vision:
        vision_models = [m for m, c in RECOMMENDED_MODELS.items() if c["vision"]]
        return "qwen3.6-plus" if "qwen3.6-plus" in vision_models else (vision_models[0] if vision_models else DEFAULT_MODEL)
    prefs: Dict[str, List[str]] = {
        "code":      ["qwen3-coder-plus", "qwen3-coder-next", "qwen3.6-plus", "glm-4.7"],
        "reasoning": ["qwen3.6-plus", "kimi-k2.5", "glm-5"],
        "bulk":      ["minimax-m2.5", "qwen3.5-plus"],
        "general":   ["qwen3.6-plus", "qwen3-max-2026-01-23", "qwen3.5-plus"],
    }
    return prefs.get(task, prefs["general"])[0]
