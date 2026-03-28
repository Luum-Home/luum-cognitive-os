"""Dynamic Model Routing — Multi-provider model selection with dual-gateway support.

Provides intelligent model selection based on task requirements, budget constraints,
and model capabilities. Supports both cloud and local models.

Dual-gateway architecture:
- Bifrost (primary, 11us overhead): for OpenAI, Anthropic, Google, Groq, Mistral, Cohere
- LiteLLM (fallback, feature-rich): for OpenRouter, local models, and all providers
- ClaudeExecutor (direct): for Claude models via CLI

When both gateways are enabled, the router tries Bifrost first for supported
models, falls back to LiteLLM, then to ClaudeExecutor.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# IMPORTANT: These are DEFAULT prices used when no historical data exists.
# The CostPredictor (lib/cost_predictor.py) calculates REAL prices from actual
# API responses. These defaults should be updated when providers change pricing.
# Source: https://docs.anthropic.com/en/docs/about-claude/models
# Last verified: 2026-03-27
MODEL_CAPABILITIES: Dict[str, dict] = {
    "claude-opus-4-6": {
        "reasoning": 9,
        "speed": 3,
        "code": 8,
        "cost_per_1m_in": 15.0,
        "cost_per_1m_out": 75.0,
        "context": 1_000_000,
    },
    "claude-sonnet-4": {
        "reasoning": 6,
        "speed": 7,
        "code": 7,
        "cost_per_1m_in": 3.0,
        "cost_per_1m_out": 15.0,
        "context": 200_000,
    },
    "claude-haiku-3.5": {
        "reasoning": 3,
        "speed": 9,
        "code": 4,
        "cost_per_1m_in": 0.25,
        "cost_per_1m_out": 1.25,
        "context": 200_000,
    },
    "gpt-4o": {
        "reasoning": 7,
        "speed": 6,
        "code": 7,
        "cost_per_1m_in": 2.5,
        "cost_per_1m_out": 10.0,
        "context": 128_000,
    },
    "gemini-2.5-pro": {
        "reasoning": 8,
        "speed": 5,
        "code": 8,
        "cost_per_1m_in": 1.25,
        "cost_per_1m_out": 5.0,
        "context": 1_000_000,
    },
    "deepseek-r1": {
        "reasoning": 8,
        "speed": 4,
        "code": 7,
        "cost_per_1m_in": 0.55,
        "cost_per_1m_out": 2.19,
        "context": 128_000,
    },
    "llama-3-70b": {
        "reasoning": 5,
        "speed": 5,
        "code": 6,
        "cost_per_1m_in": 0,
        "cost_per_1m_out": 0,
        "context": 128_000,
        "local": True,
    },
    "qwen-3-32b": {
        "reasoning": 4,
        "speed": 7,
        "code": 5,
        "cost_per_1m_in": 0,
        "cost_per_1m_out": 0,
        "context": 32_000,
        "local": True,
    },
    "openrouter/free": {
        "reasoning": 4,
        "speed": 6,
        "code": 4,
        "cost_per_1m_in": 0,
        "cost_per_1m_out": 0,
        "context": 128_000,
        "note": "Auto-selects best available free model. Degraded quality but zero cost.",
    },
    "qwen/qwen3-32b:free": {
        "reasoning": 5,
        "speed": 7,
        "code": 5,
        "cost_per_1m_in": 0,
        "cost_per_1m_out": 0,
        "context": 40_960,
    },
    "nvidia/llama-3.1-nemotron-ultra-253b:free": {
        "reasoning": 6,
        "speed": 4,
        "code": 6,
        "cost_per_1m_in": 0,
        "cost_per_1m_out": 0,
        "context": 128_000,
    },
}

TASK_REQUIREMENTS: Dict[str, List[str]] = {
    "reasoning": [
        "sdd-propose",
        "sdd-design",
        "systematic-debugging",
        "sdd-improve",
    ],
    "speed": [
        "sdd-archive",
        "doc-sync",
        "format",
    ],
    "code": [
        "sdd-apply",
        "sdd-tasks",
        "test-driven-development",
    ],
    "long_context": [
        "sdd-explore",
        "eval-repo",
        "exhaustive-prompt",
    ],
    "budget": [
        "document-feature",
        "skill-creator",
        "openrouter/free",
    ],
}

# Reverse map: task_type -> primary capability needed
_TASK_TO_CAPABILITY: Dict[str, str] = {}
for capability, tasks in TASK_REQUIREMENTS.items():
    for task in tasks:
        _TASK_TO_CAPABILITY[task] = capability


def get_model_capabilities(model: str) -> dict:
    """Get the capability profile for a model.

    Args:
        model: Model identifier (e.g., "claude-opus-4-6").

    Returns:
        Dictionary with capability scores and cost info.

    Raises:
        KeyError: If the model is not in MODEL_CAPABILITIES.
    """
    if model not in MODEL_CAPABILITIES:
        raise KeyError(f"Unknown model: {model}. Available: {list(MODEL_CAPABILITIES.keys())}")
    return dict(MODEL_CAPABILITIES[model])


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate the cost of a model call.

    Args:
        model: Model identifier.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.

    Returns:
        Estimated cost in USD.

    Raises:
        KeyError: If the model is not known.
    """
    caps = get_model_capabilities(model)
    cost = (
        input_tokens * caps["cost_per_1m_in"] / 1_000_000
        + output_tokens * caps["cost_per_1m_out"] / 1_000_000
    )
    return round(cost, 6)


def select_model(
    task_type: str,
    budget_remaining: Optional[float] = None,
    prefer_local: bool = False,
) -> str:
    """Pick the best model for a given task type.

    Selection logic:
    1. Determine the primary capability needed for the task type
    2. Filter models by budget constraint (if provided)
    3. Filter for local models only (if prefer_local=True)
    4. Score remaining models by the required capability
    5. Break ties with cost efficiency (lower cost wins)

    Args:
        task_type: The type of task (e.g., "sdd-propose", "sdd-archive").
        budget_remaining: Optional remaining budget in USD. If provided,
            excludes models whose estimated cost exceeds this amount.
            Uses a reference call of 10K input + 5K output tokens.
        prefer_local: If True, only consider local models (cost=0).

    Returns:
        Model identifier string.
    """
    primary_capability = _TASK_TO_CAPABILITY.get(task_type)

    candidates = dict(MODEL_CAPABILITIES)

    # Filter for local models if preferred
    if prefer_local:
        candidates = {k: v for k, v in candidates.items() if v.get("local", False)}
        if not candidates:
            # Fall back to cheapest cloud model if no local models available
            candidates = dict(MODEL_CAPABILITIES)

    # Filter by budget constraint using a reference call estimate
    if budget_remaining is not None:
        # When budget is effectively zero, prefer free models (OpenRouter + local)
        if budget_remaining <= 0.01:
            free_models = {
                k: v for k, v in candidates.items()
                if v.get("cost_per_1m_in", 0) == 0 and v.get("cost_per_1m_out", 0) == 0
            }
            if free_models:
                candidates = free_models

        ref_input = 10_000
        ref_output = 5_000
        affordable = {}
        for model_name, caps in candidates.items():
            cost = (
                ref_input * caps["cost_per_1m_in"] / 1_000_000
                + ref_output * caps["cost_per_1m_out"] / 1_000_000
            )
            if cost <= budget_remaining:
                affordable[model_name] = caps
        if affordable:
            candidates = affordable
        # If nothing is affordable, keep all candidates (best effort)

    if not candidates:
        candidates = dict(MODEL_CAPABILITIES)

    # Score and rank
    if primary_capability == "long_context":
        # For long context tasks, prioritize context window size
        scored = sorted(
            candidates.items(),
            key=lambda x: (-x[1].get("context", 0), _total_cost(x[1])),
        )
    elif primary_capability == "budget":
        # For budget tasks, prioritize cost efficiency
        scored = sorted(
            candidates.items(),
            key=lambda x: (_total_cost(x[1]), -x[1].get("code", 0)),
        )
    elif primary_capability in ("reasoning", "code", "speed"):
        # Score by the primary capability, break ties with cost
        scored = sorted(
            candidates.items(),
            key=lambda x: (-x[1].get(primary_capability, 0), _total_cost(x[1])),
        )
    else:
        # Unknown task type: default to best reasoning model
        scored = sorted(
            candidates.items(),
            key=lambda x: (-x[1].get("reasoning", 0), _total_cost(x[1])),
        )

    return scored[0][0]


def _total_cost(caps: dict) -> float:
    """Calculate a normalized cost score for sorting. Lower is cheaper."""
    return caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)


def format_routing_table() -> str:
    """Generate a pretty-printed routing table showing task-to-model mapping.

    Returns:
        Formatted multi-line string with the routing table.
    """
    lines = [
        "Dynamic Model Routing Table",
        "=" * 80,
        f"{'Task Type':<30} {'Primary Cap':<15} {'Selected Model':<25} {'Est. Cost/Call'}",
        "-" * 80,
    ]

    # Collect all task types
    all_tasks = sorted(_TASK_TO_CAPABILITY.keys())

    for task in all_tasks:
        capability = _TASK_TO_CAPABILITY[task]
        model = select_model(task)
        cost = estimate_cost(model, 10_000, 5_000)
        lines.append(f"{task:<30} {capability:<15} {model:<25} ${cost:.4f}")

    lines.append("-" * 80)
    lines.append("")
    lines.append("Model Capabilities:")
    lines.append(f"{'Model':<25} {'Reasoning':>9} {'Speed':>6} {'Code':>5} {'Context':>10} {'Cost(In/Out)':>15} {'Local':>6}")
    lines.append("-" * 80)

    for model_name, caps in sorted(MODEL_CAPABILITIES.items()):
        local = "yes" if caps.get("local", False) else "no"
        cost_str = f"${caps['cost_per_1m_in']:.2f}/${caps['cost_per_1m_out']:.2f}"
        context = f"{caps['context']:,}"
        lines.append(
            f"{model_name:<25} {caps['reasoning']:>9} {caps['speed']:>6} "
            f"{caps['code']:>5} {context:>10} {cost_str:>15} {local:>6}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LiteLLM-integrated execution
# ---------------------------------------------------------------------------


@dataclass
class RoutedResult:
    """Result from a routed model call (via LiteLLM or ClaudeExecutor)."""

    success: bool
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    provider: str = ""  # "litellm" or "claude"
    error: str = ""


def _select_claude_fallback() -> str:
    """Select the best Claude model as a fallback.

    Returns:
        Claude model identifier string.
    """
    claude_candidates = {
        k: v for k, v in MODEL_CAPABILITIES.items() if "claude" in k.lower()
    }
    if claude_candidates:
        return sorted(
            claude_candidates.items(),
            key=lambda x: (-x[1].get("reasoning", 0), _total_cost(x[1])),
        )[0][0]
    return "claude-sonnet-4"


def _extract_response(response: Dict[str, Any], model: str, provider: str) -> RoutedResult:
    """Extract a RoutedResult from an OpenAI-format response dict.

    Args:
        response: OpenAI-compatible response dict.
        model: Model identifier used.
        provider: Gateway name ("bifrost" or "litellm").

    Returns:
        RoutedResult with extracted text, tokens, and cost.
    """
    choices = response.get("choices", [])
    text = ""
    if choices:
        text = choices[0].get("message", {}).get("content", "")

    usage = response.get("usage", {})
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)

    cost = estimate_cost(model, tokens_in, tokens_out)

    return RoutedResult(
        success=True,
        text=text,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost,
        provider=provider,
    )


def route_and_execute(
    task_type: str,
    messages: List[Dict[str, str]],
    budget_remaining: Optional[float] = None,
    prefer_local: bool = False,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> RoutedResult:
    """Select the best model for a task and execute via the appropriate gateway.

    Dual-gateway routing:
    1. Claude models -> signal ClaudeExecutor (caller handles execution)
    2. Bifrost-supported models -> try Bifrost first (11us overhead)
    3. Fall back to LiteLLM if Bifrost unavailable or unsupported
    4. Fall back to Claude if both gateways are down

    Args:
        task_type: Task type for model selection (e.g., "sdd-propose").
        messages: Chat messages in OpenAI format.
        budget_remaining: Optional budget constraint in USD.
        prefer_local: If True, prefer local models.
        temperature: Optional sampling temperature.
        max_tokens: Optional max output tokens.

    Returns:
        RoutedResult with the response or routing guidance.
    """
    from lib.gateway_selector import invalidate_health_cache, select_gateway

    model = select_model(task_type, budget_remaining=budget_remaining, prefer_local=prefer_local)

    # Use gateway selector to pick the best path
    gateway = select_gateway(model)

    # --- Claude path (direct CLI) ---
    if gateway.name == "claude":
        return RoutedResult(
            success=False,
            text="",
            model=model,
            provider="claude",
            error="Use ClaudeExecutor for this model",
        )

    # --- Bifrost path ---
    if gateway.name == "bifrost":
        try:
            from lib.bifrost_client import (
                BifrostClient,
                BifrostError,
                BifrostUnavailable,
                get_bifrost_model_name,
            )

            bifrost_model = get_bifrost_model_name(model)
            client = BifrostClient()
            response = client.chat_completion(
                model=bifrost_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return _extract_response(response, model, "bifrost")

        except (Exception,) as e:
            # Bifrost failed — invalidate cache and fall through to LiteLLM
            logger.warning("Bifrost failed for model %s: %s. Falling back to LiteLLM.", model, e)
            invalidate_health_cache("bifrost")

            # Try LiteLLM as fallback
            fallback_gw = select_gateway(model, exclude=["bifrost"])
            if fallback_gw.name == "litellm":
                gateway = fallback_gw
                # Fall through to LiteLLM execution below
            else:
                # Both gateways down, fall back to Claude
                return RoutedResult(
                    success=False,
                    text="",
                    model=_select_claude_fallback(),
                    provider="claude",
                    error=f"Bifrost failed ({e}), LiteLLM unavailable, falling back to Claude",
                )

    # --- LiteLLM path ---
    if gateway.name == "litellm":
        from lib.litellm_client import (
            LiteLLMClient,
            LiteLLMError,
            LiteLLMUnavailable,
        )

        try:
            client = LiteLLMClient()
            response = client.chat_completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return _extract_response(response, model, "litellm")

        except LiteLLMUnavailable as e:
            logger.warning("LiteLLM became unavailable during execution: %s", e)
            invalidate_health_cache("litellm")
            return RoutedResult(
                success=False,
                text="",
                model=_select_claude_fallback(),
                provider="claude",
                error=f"LiteLLM unavailable: {e}",
            )

        except LiteLLMError as e:
            logger.error("LiteLLM error: %s", e)
            return RoutedResult(
                success=False,
                text="",
                model=model,
                provider="litellm",
                error=f"LiteLLM error: {e}",
            )

    # Should not reach here, but handle gracefully
    return RoutedResult(
        success=False,
        text="",
        model=_select_claude_fallback(),
        provider="claude",
        error=f"Unknown gateway: {gateway.name}",
    )
