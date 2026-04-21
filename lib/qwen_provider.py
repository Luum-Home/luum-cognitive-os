# SCOPE: both
"""Alibaba Qwen Coding Plan Pro — direct-SDK dispatch.

Implements the single selected overflow provider per ADR-049. Uses the
`openai` SDK with a `base_url` override pointing at Alibaba's OpenAI-
compatible workspace endpoint. No proxy, no LiteLLM, no Bifrost.

Configuration (read from environment at call time):

    ALIBABA_QWEN_API_KEY       — API key from Alibaba Cloud Model Studio
    ALIBABA_QWEN_BASE_URL      — workspace-scoped OpenAI-compatible endpoint
                                  (default: ap-southeast-1 workspace)
    ALIBABA_QWEN_DEFAULT_MODEL — default model (default: qwen3.6-plus)

ToS reminder: Qwen Coding Plan Pro is restricted to interactive coding
tools (IDEs, coding agents). Automated/batch/backend use is prohibited.
This dispatcher is intended for sub-agents spawned DURING a Claude Code
session in response to user prompts. Do NOT call from cron, unattended
pipelines, or application backends.

Reference: docs/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default values — override via env or per-call args.
DEFAULT_BASE_URL = (
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)
DEFAULT_MODEL = "qwen3.6-plus"

# Recommended models per the Coding Plan Pro bundle. Ordered by capability.
# Vision-capable flagged for callers that need multimodal.
RECOMMENDED_MODELS = {
    "qwen3.6-plus":   {"vision": True,  "context": 1_000_000, "role": "primary"},
    "kimi-k2.5":      {"vision": True,  "context": 200_000,   "role": "alt-reasoning"},
    "glm-5":          {"vision": False, "context": 200_000,   "role": "alt-code"},
    "minimax-m2.5":   {"vision": False, "context": 200_000,   "role": "bulk"},
    "qwen3.5-plus":   {"vision": True,  "context": 128_000,   "role": "fallback"},
    "qwen3-max-2026-01-23": {"vision": False, "context": 256_000, "role": "flagship-qwen"},
    "qwen3-coder-next":     {"vision": False, "context": 256_000, "role": "code-specialist"},
    "qwen3-coder-plus":     {"vision": False, "context": 256_000, "role": "code-tier2"},
    "glm-4.7":        {"vision": False, "context": 128_000,   "role": "code-older"},
}

# Approximate pricing per 1M tokens — conservative estimates from OpenRouter
# passthrough; real billing is quota-based under the subscription (not metered).
# Only used by estimate_cost() for dry-run budget projections.
_COST_ESTIMATES = {
    "qwen3.6-plus":   (0.325, 1.95),
    "kimi-k2.5":      (0.50,  2.00),
    "glm-5":          (1.40,  4.40),
    "minimax-m2.5":   (0.30,  1.20),
    "qwen3.5-plus":   (0.28,  1.70),
    "qwen3-max-2026-01-23": (0.40, 2.00),
    "qwen3-coder-next":     (0.35, 1.80),
    "qwen3-coder-plus":     (0.30, 1.60),
    "glm-4.7":        (0.80,  2.40),
}


@dataclass
class QwenResult:
    """Result from a Qwen provider call."""

    success: bool
    text: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    error: str = ""
    raw: Optional[Dict[str, Any]] = None


def _env(name: str, default: str = "") -> str:
    """Read env var with a safe default. Separated for test monkeypatching."""
    return os.environ.get(name, default)


def is_configured() -> bool:
    """True iff ALIBABA_QWEN_API_KEY is set in env (non-empty)."""
    return bool(_env("ALIBABA_QWEN_API_KEY"))


def _get_openai_client():
    """Lazy-import the openai SDK. Returns None if not installed.

    Keeps this module importable in environments without the optional
    `openai` dependency (e.g. test runners, minimal installs).
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
    """Estimate USD cost for a call (dry-run budget projection).

    Note: real billing is quota-based under the Coding Plan Pro subscription
    ($50/mo flat, 90K requests/mo). This estimate is ONLY for comparison
    against pay-per-use providers, not actual accounting.
    """
    rates = _COST_ESTIMATES.get(model)
    if rates is None:
        return 0.0
    input_rate, output_rate = rates
    return (tokens_in * input_rate + tokens_out * output_rate) / 1_000_000


def call(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    timeout: float = 120.0,
) -> QwenResult:
    """Call Alibaba Qwen with a messages array (OpenAI chat format).

    Returns QwenResult with either success=True + text/tokens/cost or
    success=False + error string. Never raises — errors are captured in
    the result so callers can implement fallback cascades without try/except
    around every call.

    Args:
        messages: OpenAI-format message list, e.g.
            [{"role": "user", "content": "..."}]
        model: model name (default: qwen3.6-plus). Must be one of
            RECOMMENDED_MODELS or explicitly provided by caller.
        max_tokens: optional completion cap. Qwen3.6-plus supports up to
            65,536 output tokens.
        temperature: optional sampling temperature.
        timeout: per-request timeout in seconds.

    Returns:
        QwenResult.
    """
    client = _get_openai_client()
    if client is None:
        if not is_configured():
            return QwenResult(
                success=False,
                model=model,
                error="ALIBABA_QWEN_API_KEY not set in environment",
            )
        return QwenResult(
            success=False,
            model=model,
            error="openai SDK not installed (run: uv sync --extra direct_providers)",
        )

    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "timeout": timeout,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    if temperature is not None:
        kwargs["temperature"] = temperature

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:  # noqa: BLE001 — capture all SDK errors into result
        return QwenResult(success=False, model=model, error=str(exc)[:500])

    # Response is a pydantic model (OpenAI SDK v1+). Extract fields defensively.
    try:
        choices = getattr(response, "choices", None) or []
        text = ""
        if choices:
            msg = getattr(choices[0], "message", None)
            if msg is not None:
                text = getattr(msg, "content", "") or ""

        usage = getattr(response, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
        tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0

        return QwenResult(
            success=True,
            text=text,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=estimate_cost(model, tokens_in, tokens_out),
            raw=None,  # omit raw pydantic model to keep result picklable
        )
    except Exception as exc:  # noqa: BLE001
        return QwenResult(
            success=False,
            model=model,
            error=f"response-parse error: {exc!r}"[:500],
        )


# Mapping of Claude model tier → best-match model in the Qwen Coding Plan
# Pro bundle. Consulted by callers that know the skill's declared Claude
# model (via frontmatter `model:` key) and want to route the fallback
# sensibly rather than always landing on qwen3.6-plus.
#
# Rationale per tier:
#   opus   — frontier reasoning/code   → qwen3.6-plus (1M ctx, SWE-bench 64.8, vision)
#   sonnet — balanced code + reason    → qwen3-coder-plus (code-specialist, cheaper)
#   haiku  — cheap + fast + simple     → minimax-m2.5 (cheapest in bundle)
#
# Unknown tier → qwen3.6-plus (safe default — highest quality available).
CLAUDE_TO_QWEN_MAP = {
    "opus": "qwen3.6-plus",
    "sonnet": "qwen3-coder-plus",
    "haiku": "minimax-m2.5",
}


def map_claude_model_to_qwen(claude_model: Optional[str]) -> str:
    """Map a Claude model tier or full model name to a Qwen bundle equivalent.

    Accepts short names (opus/sonnet/haiku) or full model IDs (claude-opus-4-7,
    claude-sonnet-4-6, claude-haiku-4-5) — matches by substring.

    Returns the best-match model name from the Qwen Coding Plan Pro bundle.
    Falls back to qwen3.6-plus if input is None, empty, or unrecognized.
    """
    if not claude_model:
        return DEFAULT_MODEL
    name = claude_model.lower()
    # Substring match so "claude-opus-4-7" and "opus" both map to opus bucket
    for claude_tier, qwen_model in CLAUDE_TO_QWEN_MAP.items():
        if claude_tier in name:
            return qwen_model
    return DEFAULT_MODEL


def select_model(
    task: str = "general",
    need_vision: bool = False,
    need_long_context: bool = False,
    claude_model_hint: Optional[str] = None,
) -> str:
    """Pick a model from the subscription bundle based on task needs.

    Args:
        task: "general" | "code" | "reasoning" | "bulk"
        need_vision: if True, only vision-capable models are returned
        need_long_context: if True, prefers 1M context models (qwen3.6-plus)
        claude_model_hint: if provided, takes priority over task heuristic.
            Maps the Claude tier (opus/sonnet/haiku or full model ID) to
            the best-match Qwen bundle model. Used by the orchestrator
            fallback to honor skill frontmatter `model:` declarations.

    Returns:
        Model name string.
    """
    # Claude hint takes priority — we're in fallback context, honor the
    # skill's declared tier rather than guessing from task category.
    # long_context + vision still override because they're hard requirements.
    if claude_model_hint and not need_long_context and not need_vision:
        return map_claude_model_to_qwen(claude_model_hint)

    if need_long_context:
        # Only qwen3.6-plus has 1M context
        return "qwen3.6-plus"

    if need_vision:
        vision_models = [m for m, c in RECOMMENDED_MODELS.items() if c["vision"]]
        # qwen3.6-plus leads for vision by both quality and context
        if "qwen3.6-plus" in vision_models:
            return "qwen3.6-plus"
        return vision_models[0] if vision_models else DEFAULT_MODEL

    task_preferences = {
        "code":      ["qwen3-coder-plus", "qwen3-coder-next", "qwen3.6-plus", "glm-4.7"],
        "reasoning": ["qwen3.6-plus", "kimi-k2.5", "glm-5"],
        "bulk":      ["minimax-m2.5", "qwen3.5-plus"],
        "general":   ["qwen3.6-plus", "qwen3-max-2026-01-23", "qwen3.5-plus"],
    }
    candidates = task_preferences.get(task, task_preferences["general"])
    return candidates[0]
