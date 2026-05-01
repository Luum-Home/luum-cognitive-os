# SCOPE: both
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

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from lib.execution_profile import resolve_execution_profile
from lib.model_catalog import ModelCatalog

# Model capabilities dict — derived from ModelCatalog (single source of truth).
# Kept as a module-level dict for backward compatibility with external importers
# and the format_routing_table() function.
MODEL_CAPABILITIES: Dict[str, dict] = {
    e.id: {
        **{k: v for k, v in e.capabilities.items()},
        "cost_per_1m_in": e.input_price_per_m,
        "cost_per_1m_out": e.output_price_per_m,
        "context": e.context_window,
        **({"local": True} if e.local else {}),
    }
    for e in ModelCatalog.all_entries()
}

# ---------------------------------------------------------------------------
# Advisor strategy routing
# ---------------------------------------------------------------------------

#: Tasks that benefit from the sonnet+advisor strategy.
#: These are tasks that previously routed to opus but don't strictly need it —
#: Sonnet executes with optional Opus advisory for architecture/edge-case calls.
ADVISOR_TASKS: frozenset = frozenset({
    "sdd-apply",
    "sdd-verify",
    "systematic-debugging",
})

#: Sentinel returned by select_model() when the advisor strategy should be used.
SONNET_ADVISOR_TIER: str = "sonnet+advisor"

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
        "repo-scout",
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


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    advisor_uses: int = 0,
) -> float:
    """Estimate the cost of a model call.

    For the ``"sonnet+advisor"`` virtual tier, uses mixed billing:
    executor tokens at Sonnet rates + advisory calls at Opus rates.

    Args:
        model: Model identifier or ``"sonnet+advisor"`` for the advisor tier.
        input_tokens: Number of input tokens (executor side).
        output_tokens: Number of output tokens (executor side).
        advisor_uses: Number of advisory calls made (only relevant for
            ``"sonnet+advisor"``; ignored for standard models).

    Returns:
        Estimated cost in USD.

    Raises:
        KeyError: If the model is not known and is not the advisor tier.
    """
    if model == SONNET_ADVISOR_TIER:
        return ModelCatalog.estimate_advisor_cost(input_tokens, output_tokens, advisor_uses)
    return ModelCatalog.estimate_cost(model, input_tokens, output_tokens)


def is_advisor_available() -> bool:
    """Return True when the sonnet+advisor strategy can be used.

    The advisor strategy requires direct Anthropic API access (executor mode)
    and is not available through CLI subprocess or LiteLLM gateway. Direct
    Anthropic API access follows the existing provider configuration:
    ``llm_providers.claude_sdk.enabled`` in ``cognitive-os.yaml``.
    """
    from lib.anthropic_direct_policy import advisor_strategy_enabled

    return advisor_strategy_enabled()


def select_model(
    task_type: str,
    budget_remaining: Optional[float] = None,
    prefer_local: bool = False,
    use_advisor: Optional[bool] = None,
) -> str:
    """Pick the best model for a given task type.

    Selection logic:
    1. Check if the task qualifies for the sonnet+advisor strategy
    2. Determine the primary capability needed for the task type
    3. Filter models by budget constraint (if provided)
    4. Filter for local models only (if prefer_local=True)
    5. Score remaining models by the required capability
    6. Break ties with cost efficiency (lower cost wins)

    Args:
        task_type: The type of task (e.g., "sdd-propose", "sdd-archive").
        budget_remaining: Optional remaining budget in USD. If provided,
            excludes models whose estimated cost exceeds this amount.
            Uses a reference call of 10K input + 5K output tokens.
        prefer_local: If True, only consider local models (cost=0).
        use_advisor: Advisor strategy preference. ``None`` and ``True`` both
            use the advisor tier only when it is available according to policy.
            Pass ``False`` to disable it for this call.

    Returns:
        Model identifier string, or ``SONNET_ADVISOR_TIER`` (``"sonnet+advisor"``)
        when the advisor strategy is selected.
    """
    # Advisor strategy: return the virtual tier sentinel when eligible
    _use_advisor = use_advisor is not False and is_advisor_available()
    if (
        _use_advisor
        and task_type in ADVISOR_TASKS
        and not prefer_local
    ):
        return SONNET_ADVISOR_TIER

    profile = resolve_execution_profile(
        task_type,
        budget_remaining=budget_remaining,
        prefer_local=prefer_local,
    )

    candidates = dict(MODEL_CAPABILITIES)
    profile_matches = {
        model_name: caps
        for model_name, caps in candidates.items()
        if profile.matches_capabilities(caps)
    }
    if profile_matches:
        candidates = profile_matches

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

    scored = sorted(
        candidates.items(),
        key=lambda x: profile.rank_key(x[1]),
        reverse=True,
    )

    return scored[0][0]


def _total_cost(caps: dict) -> float:
    """Calculate a normalized cost score for sorting. Lower is cheaper."""
    return caps.get("cost_per_1m_in", 0) + caps.get("cost_per_1m_out", 0)


# ---------------------------------------------------------------------------
# Consequence-driven model override
# ---------------------------------------------------------------------------

# Simple downgrade chain for consequence-based routing
_DOWNGRADE_CHAIN: Dict[str, Optional[str]] = {
    "opus": "sonnet",
    "claude-opus-4-6": "claude-sonnet-4",
    "sonnet": "haiku",
    "claude-sonnet-4": "claude-haiku-3.5",
    "haiku": None,
    "claude-haiku-3.5": None,
}

# Shorthand aliases used in routing (normalize to simple names)
_MODEL_FAMILY: Dict[str, str] = {
    "claude-opus-4-6": "opus",
    "claude-sonnet-4": "sonnet",
    "claude-haiku-3.5": "haiku",
}


def _downgrade_model(model: str) -> Optional[str]:
    """Return the next cheaper model in the downgrade chain, or None if already at floor."""
    # Normalize to family name first, then downgrade
    family = _MODEL_FAMILY.get(model, model)
    downgraded_family = _DOWNGRADE_CHAIN.get(family)
    if downgraded_family is None:
        return None
    # Try to return a full model ID if available in MODEL_CAPABILITIES
    for model_id in MODEL_CAPABILITIES:
        if downgraded_family in model_id.lower():
            return model_id
    return downgraded_family


def get_consequence_override(
    skill_name: str,
    metrics_dir: Optional[str] = None,
) -> Optional[str]:
    """Check consequence history and return model override for a skill.

    Rules:
    - DISABLED: return None (caller should BLOCK the launch)
    - DEGRADED: force downgrade (opus→sonnet, sonnet→haiku)
    - PROMOTED: prefer the model that scored highest (opus for high-value tasks)
    - No record: return sentinel "no-override"

    Args:
        skill_name: The skill or agent name to check.
        metrics_dir: Optional path to .cognitive-os/metrics. Auto-detected if None.

    Returns:
        - None          → skill is DISABLED, do not launch
        - "no-override" → no consequence data, proceed normally
        - model string  → use this model (DEGRADED downgrade or PROMOTED preference)
    """
    _NO_OVERRIDE = "no-override"

    # Locate the consequence history file
    if metrics_dir is None:
        # NOTE: custom resolution — differs from lib.paths.project_root() (Pattern A').
        # See tests/unit/test_project_dir_resolution.py for rationale.
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get(
            "COGNITIVE_OS_PROJECT_DIR", "."
        )
        metrics_dir = os.path.join(project_dir, ".cognitive-os", "metrics")

    history_path = Path(metrics_dir) / "consequence-history.jsonl"
    if not history_path.exists():
        return _NO_OVERRIDE

    # Read all records for the skill, in chronological order
    records: List[Dict[str, Any]] = []
    try:
        with open(history_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # Match on agent_or_skill (performance records) or target (action records)
                target = entry.get("agent_or_skill") or entry.get("target", "")
                if target == skill_name:
                    records.append(entry)
    except OSError:
        return _NO_OVERRIDE

    if not records:
        return _NO_OVERRIDE

    # Determine the most recent significant action
    # Walk backwards to find the last disable / re-enable / degradation / promotion
    latest_disable_ts: Optional[datetime] = None
    latest_reenable_ts: Optional[datetime] = None
    latest_degrade_ts: Optional[datetime] = None
    latest_promote_ts: Optional[datetime] = None

    def _parse_ts(ts_str: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            return None

    for entry in records:
        rt = entry.get("record_type", "")
        ts = _parse_ts(entry.get("timestamp", ""))
        if ts is None:
            continue
        if rt == "disable":
            if latest_disable_ts is None or ts > latest_disable_ts:
                latest_disable_ts = ts
        elif rt == "re-enable":
            if latest_reenable_ts is None or ts > latest_reenable_ts:
                latest_reenable_ts = ts
        elif rt == "degradation":
            if latest_degrade_ts is None or ts > latest_degrade_ts:
                latest_degrade_ts = ts
        elif rt == "promotion":
            if latest_promote_ts is None or ts > latest_promote_ts:
                latest_promote_ts = ts

    # DISABLED check: most recent disable is after most recent re-enable
    if latest_disable_ts is not None:
        if latest_reenable_ts is None or latest_disable_ts > latest_reenable_ts:
            return None  # Caller should BLOCK

    # DEGRADED check: most recent degradation not superseded by promotion
    if latest_degrade_ts is not None:
        if latest_promote_ts is None or latest_degrade_ts > latest_promote_ts:
            # Get the task-type model for this skill and downgrade it
            from lib.dispatch_model_advisor import classify_task_type, _TASK_MODEL_MAP
            task_type = classify_task_type(skill_name)
            base_model = _TASK_MODEL_MAP.get(task_type, "sonnet")
            downgraded = _downgrade_model(base_model)
            return downgraded if downgraded is not None else "haiku"

    # PROMOTED check: most recent promotion
    if latest_promote_ts is not None:
        if latest_degrade_ts is None or latest_promote_ts > latest_degrade_ts:
            # For promoted skills, use opus (highest quality model)
            # Find the best opus-family model available
            for model_id in MODEL_CAPABILITIES:
                if "opus" in model_id.lower():
                    return model_id
            return "opus"

    return _NO_OVERRIDE


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
    from lib.gateway_selector import invalidate_health_cache, select_gateway_for_profile

    profile = resolve_execution_profile(
        task_type,
        budget_remaining=budget_remaining,
        prefer_local=prefer_local,
    )
    model = select_model(task_type, budget_remaining=budget_remaining, prefer_local=prefer_local)

    # Use gateway selector to pick the best path
    gateway = select_gateway_for_profile(model, profile)

    if gateway.name == "unavailable":
        return RoutedResult(
            success=False,
            text="",
            model=model,
            provider="none",
            error=f"No gateway available for execution profile {profile.id}",
        )

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
            fallback_gw = select_gateway_for_profile(model, profile, exclude=["bifrost"])
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
