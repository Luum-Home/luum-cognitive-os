# SCOPE: both
"""Central policy for direct Anthropic API usage.

Claude Code native execution and direct Anthropic API execution are separate
runtime paths. A local logged-in Claude Code account should remain the default;
an ambient Anthropic API key must not silently enable pay-per-token calls.
"""

from __future__ import annotations

import os
from typing import Any, Optional

ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"


def _load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """Load cognitive-os.yaml, degrading to an empty config on errors."""
    try:
        from lib.config_loader import load_structured

        return load_structured(config_path=config_path)
    except Exception:  # noqa: BLE001 - policy checks must fail closed
        return {}


def direct_anthropic_api_enabled(config_path: Optional[str] = None) -> bool:
    """Return True when direct Anthropic API provider usage is enabled.

    The existing ``llm_providers.claude_sdk.enabled`` flag is the single
    repository-level opt-in for pay-per-token Anthropic SDK/provider calls.
    Missing config, malformed config, absent provider blocks, and non-boolean
    truthy values all fail closed.
    """
    cfg = _load_config(config_path=config_path)
    provider_cfg = (cfg.get("llm_providers") or {}).get("claude_sdk") or {}
    return provider_cfg.get("enabled") is True


def direct_anthropic_api_key_present() -> bool:
    """Return True when the direct Anthropic API credential env var is set."""
    return bool(os.environ.get(ANTHROPIC_API_KEY_ENV, "").strip())


def direct_anthropic_api_key() -> str:
    """Return the direct Anthropic API key value, or an empty string."""
    return os.environ.get(ANTHROPIC_API_KEY_ENV, "")


def advisor_strategy_enabled(config_path: Optional[str] = None) -> bool:
    """Return True when the native Anthropic advisor strategy may run.

    ``sonnet+advisor`` is executor-mode functionality. It requires the direct
    Anthropic provider opt-in plus ``ORCHESTRATOR_MODE=executor``.
    """
    return (
        direct_anthropic_api_enabled(config_path=config_path)
        and os.environ.get("ORCHESTRATOR_MODE", "").lower() == "executor"
    )
