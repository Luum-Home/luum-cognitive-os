# SCOPE: os-only
"""Gateway Selector — Dual-gateway routing with health checks and failover.

Encapsulates the logic for choosing between Bifrost (fast path), LiteLLM
(feature-rich fallback), and ClaudeExecutor (direct Claude execution).

Priority order:
1. Claude models -> ClaudeExecutor (always, no proxy)
2. Bifrost-supported models -> Bifrost (if available, 11us overhead)
3. Everything else -> LiteLLM (if available, broader model support)
4. Fallback -> ClaudeExecutor with best Claude model

Usage:
    from lib.gateway_selector import select_gateway, get_gateway_status

    gateway = select_gateway("gpt-4o")
    # gateway.name == "bifrost" | "litellm" | "claude"
    # gateway.base_url == the URL to use

Python 3.9+ compatible.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GatewayConfig:
    """Configuration and status for a gateway."""

    name: str          # "bifrost" | "litellm" | "claude"
    base_url: str
    is_available: bool = False
    latency_ms: float = 0.0   # Last measured health check latency
    last_checked: float = 0.0  # Timestamp of last health check


# Health check cache: avoid hammering health endpoints on every call.
# Cache validity in seconds.
_HEALTH_CACHE_TTL = 30.0
_health_cache: Dict[str, GatewayConfig] = {}


def _check_bifrost_health() -> GatewayConfig:
    """Check Bifrost health with caching."""
    cached = _health_cache.get("bifrost")
    now = time.time()
    if cached and (now - cached.last_checked) < _HEALTH_CACHE_TTL:
        return cached

    from lib.bifrost_client import (
        DEFAULT_BIFROST_URL,
        is_bifrost_available,
        is_bifrost_enabled,
    )
    import os

    base_url = os.environ.get("BIFROST_URL", DEFAULT_BIFROST_URL)

    if not is_bifrost_enabled():
        config = GatewayConfig(
            name="bifrost",
            base_url=base_url,
            is_available=False,
            last_checked=now,
        )
        _health_cache["bifrost"] = config
        return config

    start = time.time()
    available = is_bifrost_available(url=base_url, timeout=3.0)
    latency = (time.time() - start) * 1000

    config = GatewayConfig(
        name="bifrost",
        base_url=base_url,
        is_available=available,
        latency_ms=round(latency, 2),
        last_checked=now,
    )
    _health_cache["bifrost"] = config
    return config


def _check_litellm_health() -> GatewayConfig:
    """Check LiteLLM health with caching."""
    cached = _health_cache.get("litellm")
    now = time.time()
    if cached and (now - cached.last_checked) < _HEALTH_CACHE_TTL:
        return cached

    from lib.litellm_client import (
        DEFAULT_LITELLM_URL,
        is_litellm_available,
        is_litellm_enabled,
    )
    import os

    base_url = os.environ.get("LITELLM_URL", DEFAULT_LITELLM_URL)

    if not is_litellm_enabled():
        config = GatewayConfig(
            name="litellm",
            base_url=base_url,
            is_available=False,
            last_checked=now,
        )
        _health_cache["litellm"] = config
        return config

    start = time.time()
    available = is_litellm_available(url=base_url, timeout=3.0)
    latency = (time.time() - start) * 1000

    config = GatewayConfig(
        name="litellm",
        base_url=base_url,
        is_available=available,
        latency_ms=round(latency, 2),
        last_checked=now,
    )
    _health_cache["litellm"] = config
    return config


def select_gateway(
    model: str,
    exclude: Optional[List[str]] = None,
) -> GatewayConfig:
    """Pick the best gateway for a model.

    Priority:
    1. Claude models -> ClaudeExecutor (always, no proxy)
    2. Bifrost-supported models -> Bifrost (if available and not excluded)
    3. Everything else -> LiteLLM (if available and not excluded)
    4. Fallback -> ClaudeExecutor with signal to use Claude fallback

    Args:
        model: Model identifier (e.g., "gpt-4o", "claude-opus-4-6").
        exclude: List of gateway names to exclude (e.g., ["bifrost"] to skip Bifrost).

    Returns:
        GatewayConfig indicating which gateway to use.
    """
    excluded = set(exclude or [])

    # Step 1: Claude models always go direct
    from lib.litellm_client import CLAUDE_MODELS
    model_lower = model.lower()
    is_claude = any(c in model_lower for c in CLAUDE_MODELS) or "claude" in model_lower
    if is_claude:
        return GatewayConfig(
            name="claude",
            base_url="",
            is_available=True,
        )

    # Step 2: Try Bifrost for supported models
    if "bifrost" not in excluded:
        from lib.bifrost_client import is_model_bifrost_routable
        if is_model_bifrost_routable(model):
            bifrost = _check_bifrost_health()
            if bifrost.is_available:
                return bifrost
            logger.debug("Bifrost not available for model %s, trying LiteLLM", model)

    # Step 3: Try LiteLLM
    if "litellm" not in excluded:
        from lib.litellm_client import is_model_litellm_routable
        if is_model_litellm_routable(model):
            litellm = _check_litellm_health()
            if litellm.is_available:
                return litellm
            logger.debug("LiteLLM not available for model %s", model)

    # Step 4: Fallback to Claude
    logger.warning(
        "No gateway available for model %s (excluded=%s), falling back to Claude",
        model,
        excluded,
    )
    return GatewayConfig(
        name="claude",
        base_url="",
        is_available=True,
    )


def get_gateway_status() -> Dict[str, GatewayConfig]:
    """Return health status of all gateways for monitoring.

    Returns:
        Dict mapping gateway name to its current GatewayConfig.
    """
    return {
        "bifrost": _check_bifrost_health(),
        "litellm": _check_litellm_health(),
        "claude": GatewayConfig(
            name="claude",
            base_url="",
            is_available=True,  # Claude CLI is always "available"
        ),
    }


def invalidate_health_cache(gateway: Optional[str] = None) -> None:
    """Invalidate the health check cache for a specific gateway or all gateways.

    Call this after a gateway failure to force a fresh health check on the
    next select_gateway() call.

    Args:
        gateway: Gateway name to invalidate, or None to invalidate all.
    """
    if gateway:
        _health_cache.pop(gateway, None)
    else:
        _health_cache.clear()


def format_gateway_status() -> str:
    """Generate a human-readable gateway status report.

    Returns:
        Formatted multi-line string with gateway health.
    """
    status = get_gateway_status()
    lines = [
        "Gateway Status",
        "=" * 60,
        f"{'Gateway':<12} {'Available':<12} {'Latency':<12} {'URL'}",
        "-" * 60,
    ]
    for name in ("bifrost", "litellm", "claude"):
        gw = status[name]
        avail = "yes" if gw.is_available else "NO"
        latency = f"{gw.latency_ms:.1f}ms" if gw.latency_ms > 0 else "n/a"
        url = gw.base_url or "(direct CLI)"
        lines.append(f"{name:<12} {avail:<12} {latency:<12} {url}")
    return "\n".join(lines)
