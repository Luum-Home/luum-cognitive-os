# SCOPE: both
"""Provider registry for the multi-provider agent loop (ADR-062).

Each provider module exposes the canonical interface:
  - is_configured() -> bool
  - get_client() -> Any (OpenAI-compat client or provider SDK)
  - MODEL_MAP: Dict[str, str]  (opus/sonnet/haiku -> provider-native model)
  - call(messages, model_hint=None, **kwargs) -> dict

Default cascade order (per ADR-062, operator preference 2026-04-24):
  Tier 1: qwen       — Alibaba Qwen Coding Plan Pro ($50/mo flat)
  Tier 2: openrouter — 100+ models, free + paid tiers
  Tier 3: gemini     — Google Gemini free tier
  Tier 4: ollama     — Local models (zero cost, requires daemon)
  Final:  claude     — Claude Code native (handled by dispatch.py ClaudeExecutor)

Opt-in (require explicit env key, not in default cascade):
  openai     — ChatGPT-5.x, paid per-token
  deepseek   — DeepSeek reasoning, paid per-token
  claude_sdk — Official Claude Agent SDK, paid per-token via ANTHROPIC_API_KEY

Advance rules (per ADR-062):
  qwen, openrouter, gemini, deepseek, ollama → advance on any failure
  openai, claude_sdk → advance ONLY on rate-limit
  claude (ClaudeExecutor) → advance ONLY on rate-limit (handled in dispatch.py)
"""

from lib.providers import (
    claude_sdk,
    deepseek,
    gemini,
    ollama,
    openai,
    openrouter,
    qwen,
)

REGISTRY: dict = {
    "qwen":       qwen,
    "openrouter": openrouter,
    "gemini":     gemini,
    "ollama":     ollama,
    "openai":     openai,
    "deepseek":   deepseek,
    "claude_sdk": claude_sdk,
}

# Providers where advance happens on ANY failure (not just rate-limit)
ADVANCE_ON_ANY_FAILURE = frozenset({"qwen", "openrouter", "gemini", "deepseek", "ollama"})

# Providers where advance happens ONLY on rate-limit
ADVANCE_ON_RATE_LIMIT_ONLY = frozenset({"openai", "claude_sdk"})

__all__ = [
    "REGISTRY",
    "ADVANCE_ON_ANY_FAILURE",
    "ADVANCE_ON_RATE_LIMIT_ONLY",
    "qwen",
    "openrouter",
    "gemini",
    "ollama",
    "openai",
    "deepseek",
    "claude_sdk",
]
