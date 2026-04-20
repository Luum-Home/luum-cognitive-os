# SCOPE: os-only
"""Centralized Model Catalog -- Single source of truth for all model metadata.

Every model known to Cognitive OS is registered here with canonical IDs,
aliases, pricing, capabilities, and provider information. Other lib modules
(model_router, cost_dashboard, consequence_engine, escalation_detector)
should import from this catalog instead of maintaining their own hardcoded
dictionaries.

Usage:
    from lib.model_catalog import ModelCatalog

    entry = ModelCatalog.get("opus")            # lookup by alias
    canon = ModelCatalog.resolve("claude-opus-4")  # -> "claude-opus-4-6"
    cost  = ModelCatalog.estimate_cost("sonnet", 10_000, 5_000)
    cheap = ModelCatalog.cheapest_for("code", min_score=6)
    down  = ModelCatalog.downgrade("claude-opus-4-6")  # -> "claude-sonnet-4"

Python 3.9+ compatible. No external dependencies.
Author: luum
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelEntry:
    """Immutable descriptor for a single model.

    Attributes:
        id: Canonical model identifier (e.g. ``"claude-opus-4-6"``).
        family: Model family for grouping (e.g. ``"opus"``).
        provider: Organisation that serves the model.
        short_name: Human-friendly short name used in dashboards/logs.
        input_price_per_m: USD cost per 1 M input tokens.
        output_price_per_m: USD cost per 1 M output tokens.
        context_window: Maximum context length in tokens.
        capabilities: Scored capabilities (``reasoning``, ``speed``,
            ``code``, etc.) on a 1-10 scale.
        local: ``True`` for models served locally (Ollama, vLLM, etc.).
        aliases: Alternative names that resolve to this model's *id*.
    """

    id: str
    family: str
    provider: str
    short_name: str
    input_price_per_m: float
    output_price_per_m: float
    context_window: int
    capabilities: Dict[str, int] = field(default_factory=dict)
    local: bool = False
    aliases: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Catalog data
# ---------------------------------------------------------------------------

# Single source of truth for all model pricing and capabilities.
# Consumer modules (cost_dashboard, model_router, etc.)
# derive their dicts from this catalog -- no manual sync needed.
# Last verified: 2026-03-27

_ENTRIES: Tuple[ModelEntry, ...] = (
    # --- Anthropic ---
    ModelEntry(
        id="claude-opus-4-6",
        family="opus",
        provider="anthropic",
        short_name="opus",
        input_price_per_m=15.0,
        output_price_per_m=75.0,
        context_window=1_000_000,
        capabilities={"reasoning": 9, "speed": 3, "code": 8},
        aliases=("opus", "claude-opus-4", "claude-opus", "claude-opus-4-20250514"),
    ),
    ModelEntry(
        id="claude-sonnet-4",
        family="sonnet",
        provider="anthropic",
        short_name="sonnet",
        input_price_per_m=3.0,
        output_price_per_m=15.0,
        context_window=200_000,
        capabilities={"reasoning": 6, "speed": 7, "code": 7},
        aliases=("sonnet", "claude-sonnet", "claude-sonnet-4-20250514", "claude-sonnet-4-6"),
    ),
    ModelEntry(
        id="claude-haiku-3.5",
        family="haiku",
        provider="anthropic",
        short_name="haiku",
        input_price_per_m=0.25,
        output_price_per_m=1.25,
        context_window=200_000,
        capabilities={"reasoning": 3, "speed": 9, "code": 4},
        aliases=("haiku", "claude-haiku-3-5", "claude-haiku", "claude-haiku-3-5-20241022", "claude-haiku-4-5"),
    ),
    # --- OpenAI ---
    ModelEntry(
        id="gpt-4o",
        family="gpt4",
        provider="openai",
        short_name="gpt-4o",
        input_price_per_m=2.5,
        output_price_per_m=10.0,
        context_window=128_000,
        capabilities={"reasoning": 7, "speed": 6, "code": 7},
        aliases=("gpt4o",),
    ),
    ModelEntry(
        id="codex-mini",
        family="codex",
        provider="openai",
        short_name="codex-mini",
        input_price_per_m=1.5,
        output_price_per_m=6.0,
        context_window=200_000,
        capabilities={"reasoning": 5, "speed": 8, "code": 8},
        aliases=("codex",),
    ),
    # --- Google ---
    ModelEntry(
        id="gemini-2.5-pro",
        family="gemini",
        provider="google",
        short_name="gemini-2.5-pro",
        input_price_per_m=1.25,
        output_price_per_m=5.0,
        context_window=1_000_000,
        capabilities={"reasoning": 8, "speed": 5, "code": 8},
        aliases=("gemini-pro", "gemini"),
    ),
    # --- DeepSeek ---
    ModelEntry(
        id="deepseek-r1",
        family="deepseek",
        provider="deepseek",
        short_name="deepseek-r1",
        input_price_per_m=0.55,
        output_price_per_m=2.19,
        context_window=128_000,
        capabilities={"reasoning": 8, "speed": 4, "code": 7},
        aliases=("deepseek",),
    ),
    # --- Local / Ollama ---
    ModelEntry(
        id="llama-3-70b",
        family="llama",
        provider="ollama",
        short_name="llama-3-70b",
        input_price_per_m=0.0,
        output_price_per_m=0.0,
        context_window=128_000,
        capabilities={"reasoning": 5, "speed": 5, "code": 6},
        local=True,
        aliases=("llama-70b", "llama3-70b"),
    ),
    ModelEntry(
        id="qwen-3-32b",
        family="qwen",
        provider="ollama",
        short_name="qwen-3-32b",
        input_price_per_m=0.0,
        output_price_per_m=0.0,
        context_window=32_000,
        capabilities={"reasoning": 4, "speed": 7, "code": 5},
        local=True,
        aliases=("qwen-32b", "qwen3-32b"),
    ),
    # --- OpenRouter ---
    ModelEntry(
        id="openrouter/free",
        family="openrouter",
        provider="openrouter",
        short_name="openrouter-free",
        input_price_per_m=0.0,
        output_price_per_m=0.0,
        context_window=128_000,
        capabilities={"reasoning": 4, "speed": 6, "code": 4},
        aliases=("openrouter-free", "free"),
    ),
    ModelEntry(
        id="qwen/qwen3-32b:free",
        family="qwen",
        provider="openrouter",
        short_name="qwen3-32b-free",
        input_price_per_m=0.0,
        output_price_per_m=0.0,
        context_window=40_960,
        capabilities={"reasoning": 5, "speed": 7, "code": 5},
        aliases=("qwen3-32b-free",),
    ),
    ModelEntry(
        id="nvidia/llama-3.1-nemotron-ultra-253b:free",
        family="nemotron",
        provider="openrouter",
        short_name="nemotron-free",
        input_price_per_m=0.0,
        output_price_per_m=0.0,
        context_window=128_000,
        capabilities={"reasoning": 6, "speed": 4, "code": 6},
        aliases=("nemotron-free", "nemotron-253b-free"),
    ),
    # --- Mistral (placeholder) ---
    ModelEntry(
        id="mistral-large",
        family="mistral",
        provider="mistral",
        short_name="mistral-large",
        input_price_per_m=2.0,
        output_price_per_m=6.0,
        context_window=128_000,
        capabilities={"reasoning": 7, "speed": 6, "code": 7},
        aliases=("mistral",),
    ),
)

# Anthropic upgrade/downgrade chain (ordered cheapest -> most expensive).
_ANTHROPIC_CHAIN: Tuple[str, ...] = (
    "openrouter/free",
    "claude-haiku-3.5",
    "claude-sonnet-4",
    "claude-opus-4-6",
)

# ---------------------------------------------------------------------------
# Advisor strategy constants
# ---------------------------------------------------------------------------

#: Beta feature name required in the ``betas`` list when using the advisor tool.
ADVISOR_BETA: str = "advisor-tool-2026-03-01"

#: Tool type string for the Anthropic Advisor Tool.
ADVISOR_TOOL_TYPE: str = "advisor_20260301"

#: The advisor tool definition injected into API requests for ``sonnet+advisor``.
#: Uses ``claude-opus-4-6`` as the advisor model.
ADVISOR_TOOL_DEF: dict = {
    "type": ADVISOR_TOOL_TYPE,
    "name": "advisor",
    "model": "claude-opus-4-6",
    "max_uses": 3,
}

#: Approximate tokens consumed per advisory call (Opus side) for cost estimation.
#: Based on typical pattern: ~500 in + ~1000 out per advice invocation.
ADVISOR_TOKENS_PER_USE: Tuple[int, int] = (500, 1_000)

#: Pricing for the ``sonnet+advisor`` virtual tier — executor uses Sonnet rates,
#: advisor uses Opus rates.  Exposed here so callers can do mixed billing.
ADVISOR_EXECUTOR_MODEL: str = "claude-sonnet-4"
ADVISOR_MODEL: str = "claude-opus-4-6"


# ---------------------------------------------------------------------------
# ModelCatalog
# ---------------------------------------------------------------------------


class ModelCatalog:
    """Class-level catalog with static lookup methods.

    All data is resolved at import time from ``_ENTRIES``.  No I/O or
    configuration is required.
    """

    # Indexed data (built once at class-body evaluation time).
    _by_id: Dict[str, ModelEntry] = {}
    _alias_map: Dict[str, str] = {}  # alias (lower) -> canonical id

    @classmethod
    def _ensure_indexed(cls) -> None:
        """Populate indices from ``_ENTRIES`` if not already done."""
        if cls._by_id:
            return
        for entry in _ENTRIES:
            cls._by_id[entry.id] = entry
            # The canonical id itself is also an alias.
            cls._alias_map[entry.id.lower()] = entry.id
            for alias in entry.aliases:
                cls._alias_map[alias.lower()] = entry.id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def get(cls, id_or_alias: str) -> ModelEntry:
        """Return the ``ModelEntry`` for a canonical ID or any known alias.

        Raises ``KeyError`` when the identifier is not recognised.
        """
        cls._ensure_indexed()
        canonical = cls._alias_map.get(id_or_alias.lower())
        if canonical is None:
            raise KeyError(
                f"Unknown model: {id_or_alias!r}. "
                f"Known aliases: {sorted(cls._alias_map.keys())}"
            )
        return cls._by_id[canonical]

    @classmethod
    def resolve(cls, id_or_alias: str) -> str:
        """Return the canonical model ID for an alias.

        Raises ``KeyError`` when the identifier is not recognised.
        """
        return cls.get(id_or_alias).id

    @classmethod
    def family(cls, id_or_alias: str) -> str:
        """Return the model family (``"opus"``, ``"sonnet"``, ...)."""
        return cls.get(id_or_alias).family

    # ------------------------------------------------------------------
    # Upgrade / Downgrade
    # ------------------------------------------------------------------

    @classmethod
    def upgrade(cls, model: str) -> Optional[str]:
        """Return the next *more capable* model in the Anthropic chain.

        Returns ``None`` when there is no higher model (already at opus).
        """
        cls._ensure_indexed()
        canonical = cls.resolve(model)
        try:
            idx = _ANTHROPIC_CHAIN.index(canonical)
        except ValueError:
            return None
        if idx + 1 < len(_ANTHROPIC_CHAIN):
            return _ANTHROPIC_CHAIN[idx + 1]
        return None

    @classmethod
    def downgrade(cls, model: str) -> Optional[str]:
        """Return the next *cheaper* model in the Anthropic chain.

        Returns ``None`` when there is no cheaper model (already at
        ``openrouter/free``).
        """
        cls._ensure_indexed()
        canonical = cls.resolve(model)
        try:
            idx = _ANTHROPIC_CHAIN.index(canonical)
        except ValueError:
            return None
        if idx - 1 >= 0:
            return _ANTHROPIC_CHAIN[idx - 1]
        return None

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    @classmethod
    def by_provider(cls, provider: str) -> List[ModelEntry]:
        """Return all models from a given provider (case-insensitive)."""
        cls._ensure_indexed()
        provider_lower = provider.lower()
        return [e for e in _ENTRIES if e.provider.lower() == provider_lower]

    @classmethod
    def by_capability(cls, capability: str, min_score: int = 1) -> List[ModelEntry]:
        """Return models whose *capability* score is >= *min_score*."""
        cls._ensure_indexed()
        return [
            e for e in _ENTRIES
            if e.capabilities.get(capability, 0) >= min_score
        ]

    @classmethod
    def cheapest_for(cls, capability: str, min_score: int = 1) -> ModelEntry:
        """Return the cheapest model meeting a minimum capability score.

        Raises ``ValueError`` when no model meets the criteria.
        """
        candidates = cls.by_capability(capability, min_score)
        if not candidates:
            raise ValueError(
                f"No model has {capability!r} >= {min_score}"
            )
        return min(
            candidates,
            key=lambda e: e.input_price_per_m + e.output_price_per_m,
        )

    # ------------------------------------------------------------------
    # Cost helpers
    # ------------------------------------------------------------------

    @classmethod
    def estimate_cost(
        cls,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate the cost in USD for a model call.

        Uses the catalog pricing.  For real post-hoc costs, always prefer
        the actual token counts returned by the API.
        """
        entry = cls.get(model)
        cost = (
            input_tokens * entry.input_price_per_m / 1_000_000
            + output_tokens * entry.output_price_per_m / 1_000_000
        )
        return round(cost, 6)

    @classmethod
    def pricing(cls, model: str) -> Tuple[float, float]:
        """Return ``(input_price_per_m, output_price_per_m)`` for a model."""
        entry = cls.get(model)
        return (entry.input_price_per_m, entry.output_price_per_m)

    @classmethod
    def estimate_advisor_cost(
        cls,
        executor_input_tokens: int,
        executor_output_tokens: int,
        advisor_uses: int = 0,
    ) -> float:
        """Estimate cost for a ``sonnet+advisor`` request.

        Mixed billing: executor tokens billed at Sonnet rates; each advisory
        call billed at Opus rates using ``ADVISOR_TOKENS_PER_USE`` as an
        approximate token count when ``advisor_uses > 0``.

        Args:
            executor_input_tokens: Input tokens consumed by the Sonnet executor.
            executor_output_tokens: Output tokens consumed by the Sonnet executor.
            advisor_uses: Number of times the advisor was actually invoked.
                          Defaults to 0 (no advisory calls).

        Returns:
            Estimated total cost in USD.
        """
        # Executor cost (Sonnet)
        exec_cost = cls.estimate_cost(
            ADVISOR_EXECUTOR_MODEL, executor_input_tokens, executor_output_tokens
        )
        # Advisor cost (Opus × number of advisory calls)
        advisor_in, advisor_out = ADVISOR_TOKENS_PER_USE
        adv_cost = cls.estimate_cost(
            ADVISOR_MODEL,
            advisor_in * advisor_uses,
            advisor_out * advisor_uses,
        )
        return round(exec_cost + adv_cost, 6)

    # ------------------------------------------------------------------
    # Enumeration
    # ------------------------------------------------------------------

    @classmethod
    def all_aliases(cls) -> Dict[str, str]:
        """Return a mapping ``alias -> canonical_id`` for every known alias."""
        cls._ensure_indexed()
        return dict(cls._alias_map)

    @classmethod
    def all_entries(cls) -> Tuple[ModelEntry, ...]:
        """Return all registered model entries."""
        cls._ensure_indexed()
        return _ENTRIES

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @classmethod
    def format_catalog(cls) -> str:
        """Return a human-readable table of all models."""
        cls._ensure_indexed()
        lines = [
            "Model Catalog",
            "=" * 100,
            (
                f"{'ID':<42} {'Provider':<12} {'Family':<10} "
                f"{'Context':>10} {'In$/1M':>8} {'Out$/1M':>9} "
                f"{'Local':>6}"
            ),
            "-" * 100,
        ]
        for entry in _ENTRIES:
            ctx = f"{entry.context_window:,}"
            lines.append(
                f"{entry.id:<42} {entry.provider:<12} {entry.family:<10} "
                f"{ctx:>10} {entry.input_price_per_m:>8.2f} "
                f"{entry.output_price_per_m:>9.2f} "
                f"{'yes' if entry.local else 'no':>6}"
            )
        lines.append("-" * 100)
        lines.append(f"Total models: {len(_ENTRIES)}")
        return "\n".join(lines)
