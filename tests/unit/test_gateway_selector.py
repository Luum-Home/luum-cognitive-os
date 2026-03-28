"""Unit tests for lib/gateway_selector.py

Validates gateway selection logic, health caching, failover behavior,
and status reporting.
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

from lib.gateway_selector import (
    GatewayConfig,
    format_gateway_status,
    get_gateway_status,
    invalidate_health_cache,
    select_gateway,
)

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_health_cache():
    """Clear the health cache before and after each test."""
    invalidate_health_cache()
    yield
    invalidate_health_cache()


# ---------------------------------------------------------------------------
# select_gateway — Claude models
# ---------------------------------------------------------------------------


class TestSelectGatewayClaude:
    """Claude models should always route to ClaudeExecutor."""

    def test_claude_opus(self):
        gw = select_gateway("claude-opus-4-6")
        assert gw.name == "claude"

    def test_claude_sonnet(self):
        gw = select_gateway("claude-sonnet-4")
        assert gw.name == "claude"

    def test_claude_haiku(self):
        gw = select_gateway("claude-haiku-3.5")
        assert gw.name == "claude"

    def test_claude_unknown_version(self):
        gw = select_gateway("claude-future-model-9")
        assert gw.name == "claude"


# ---------------------------------------------------------------------------
# select_gateway — Bifrost path
# ---------------------------------------------------------------------------


class TestSelectGatewayBifrost:
    """When Bifrost is available and model is supported, use Bifrost."""

    @patch("lib.gateway_selector._check_bifrost_health")
    def test_bifrost_when_available(self, mock_health):
        mock_health.return_value = GatewayConfig(
            name="bifrost",
            base_url="http://localhost:8081",
            is_available=True,
            latency_ms=5.0,
            last_checked=time.time(),
        )
        gw = select_gateway("gpt-4o")
        assert gw.name == "bifrost"

    @patch("lib.gateway_selector._check_litellm_health")
    @patch("lib.gateway_selector._check_bifrost_health")
    def test_litellm_fallback_when_bifrost_down(self, mock_bifrost, mock_litellm):
        mock_bifrost.return_value = GatewayConfig(
            name="bifrost",
            base_url="http://localhost:8081",
            is_available=False,
            last_checked=time.time(),
        )
        mock_litellm.return_value = GatewayConfig(
            name="litellm",
            base_url="http://localhost:4000",
            is_available=True,
            latency_ms=10.0,
            last_checked=time.time(),
        )
        gw = select_gateway("gpt-4o")
        assert gw.name == "litellm"


# ---------------------------------------------------------------------------
# select_gateway — LiteLLM path
# ---------------------------------------------------------------------------


class TestSelectGatewayLiteLLM:
    """Models not supported by Bifrost should go to LiteLLM."""

    @patch("lib.gateway_selector._check_litellm_health")
    def test_openrouter_goes_to_litellm(self, mock_litellm):
        mock_litellm.return_value = GatewayConfig(
            name="litellm",
            base_url="http://localhost:4000",
            is_available=True,
            latency_ms=10.0,
            last_checked=time.time(),
        )
        gw = select_gateway("openrouter/free")
        # OpenRouter is excluded from Bifrost, should go to LiteLLM or Claude
        # Since it's also not a Claude model, it should try LiteLLM
        assert gw.name in ("litellm", "claude")

    @patch("lib.gateway_selector._check_litellm_health")
    def test_local_model_goes_to_litellm(self, mock_litellm):
        mock_litellm.return_value = GatewayConfig(
            name="litellm",
            base_url="http://localhost:4000",
            is_available=True,
            latency_ms=10.0,
            last_checked=time.time(),
        )
        gw = select_gateway("llama-3-70b")
        assert gw.name in ("litellm", "claude")


# ---------------------------------------------------------------------------
# select_gateway — Exclusion
# ---------------------------------------------------------------------------


class TestSelectGatewayExclusion:
    """Gateway exclusion should skip specified gateways."""

    @patch("lib.gateway_selector._check_litellm_health")
    @patch("lib.gateway_selector._check_bifrost_health")
    def test_exclude_bifrost(self, mock_bifrost, mock_litellm):
        mock_bifrost.return_value = GatewayConfig(
            name="bifrost",
            base_url="http://localhost:8081",
            is_available=True,
            last_checked=time.time(),
        )
        mock_litellm.return_value = GatewayConfig(
            name="litellm",
            base_url="http://localhost:4000",
            is_available=True,
            last_checked=time.time(),
        )
        gw = select_gateway("gpt-4o", exclude=["bifrost"])
        assert gw.name == "litellm"

    @patch("lib.gateway_selector._check_litellm_health")
    @patch("lib.gateway_selector._check_bifrost_health")
    def test_exclude_both_falls_to_claude(self, mock_bifrost, mock_litellm):
        gw = select_gateway("gpt-4o", exclude=["bifrost", "litellm"])
        assert gw.name == "claude"


# ---------------------------------------------------------------------------
# select_gateway — Full fallback chain
# ---------------------------------------------------------------------------


class TestSelectGatewayFallback:
    """When all gateways are down, fall back to Claude."""

    @patch("lib.gateway_selector._check_litellm_health")
    @patch("lib.gateway_selector._check_bifrost_health")
    def test_all_gateways_down(self, mock_bifrost, mock_litellm):
        mock_bifrost.return_value = GatewayConfig(
            name="bifrost",
            base_url="http://localhost:8081",
            is_available=False,
            last_checked=time.time(),
        )
        mock_litellm.return_value = GatewayConfig(
            name="litellm",
            base_url="http://localhost:4000",
            is_available=False,
            last_checked=time.time(),
        )
        gw = select_gateway("gpt-4o")
        assert gw.name == "claude"
        assert gw.is_available is True  # Claude CLI is always "available"


# ---------------------------------------------------------------------------
# Health cache
# ---------------------------------------------------------------------------


class TestHealthCache:
    """Tests for health check caching behavior."""

    def test_invalidate_specific(self):
        """Invalidating a specific gateway should clear only that cache."""
        from lib.gateway_selector import _health_cache
        _health_cache["bifrost"] = GatewayConfig(
            name="bifrost", base_url="", is_available=True, last_checked=time.time()
        )
        _health_cache["litellm"] = GatewayConfig(
            name="litellm", base_url="", is_available=True, last_checked=time.time()
        )
        invalidate_health_cache("bifrost")
        assert "bifrost" not in _health_cache
        assert "litellm" in _health_cache

    def test_invalidate_all(self):
        """Invalidating all should clear the entire cache."""
        from lib.gateway_selector import _health_cache
        _health_cache["bifrost"] = GatewayConfig(
            name="bifrost", base_url="", is_available=True, last_checked=time.time()
        )
        invalidate_health_cache()
        assert len(_health_cache) == 0


# ---------------------------------------------------------------------------
# get_gateway_status
# ---------------------------------------------------------------------------


class TestGetGatewayStatus:
    """Tests for get_gateway_status()."""

    @patch("lib.gateway_selector._check_litellm_health")
    @patch("lib.gateway_selector._check_bifrost_health")
    def test_returns_all_three_gateways(self, mock_bifrost, mock_litellm):
        mock_bifrost.return_value = GatewayConfig(
            name="bifrost", base_url="http://localhost:8081",
            is_available=True, last_checked=time.time(),
        )
        mock_litellm.return_value = GatewayConfig(
            name="litellm", base_url="http://localhost:4000",
            is_available=True, last_checked=time.time(),
        )
        status = get_gateway_status()
        assert "bifrost" in status
        assert "litellm" in status
        assert "claude" in status

    @patch("lib.gateway_selector._check_litellm_health")
    @patch("lib.gateway_selector._check_bifrost_health")
    def test_claude_always_available(self, mock_bifrost, mock_litellm):
        mock_bifrost.return_value = GatewayConfig(
            name="bifrost", base_url="", is_available=False, last_checked=time.time(),
        )
        mock_litellm.return_value = GatewayConfig(
            name="litellm", base_url="", is_available=False, last_checked=time.time(),
        )
        status = get_gateway_status()
        assert status["claude"].is_available is True


# ---------------------------------------------------------------------------
# format_gateway_status
# ---------------------------------------------------------------------------


class TestFormatGatewayStatus:
    """Tests for format_gateway_status()."""

    @patch("lib.gateway_selector._check_litellm_health")
    @patch("lib.gateway_selector._check_bifrost_health")
    def test_returns_string(self, mock_bifrost, mock_litellm):
        mock_bifrost.return_value = GatewayConfig(
            name="bifrost", base_url="http://localhost:8081",
            is_available=True, latency_ms=5.0, last_checked=time.time(),
        )
        mock_litellm.return_value = GatewayConfig(
            name="litellm", base_url="http://localhost:4000",
            is_available=True, latency_ms=10.0, last_checked=time.time(),
        )
        result = format_gateway_status()
        assert isinstance(result, str)
        assert "Gateway Status" in result
        assert "bifrost" in result
        assert "litellm" in result
        assert "claude" in result

    @patch("lib.gateway_selector._check_litellm_health")
    @patch("lib.gateway_selector._check_bifrost_health")
    def test_shows_availability(self, mock_bifrost, mock_litellm):
        mock_bifrost.return_value = GatewayConfig(
            name="bifrost", base_url="http://localhost:8081",
            is_available=False, last_checked=time.time(),
        )
        mock_litellm.return_value = GatewayConfig(
            name="litellm", base_url="http://localhost:4000",
            is_available=True, latency_ms=10.0, last_checked=time.time(),
        )
        result = format_gateway_status()
        assert "NO" in result  # Bifrost unavailable
        assert "yes" in result  # LiteLLM available
