"""Tests for lib/providers/claude_sdk.py (ADR-062 opt-in, ADR-063)."""

from unittest.mock import patch


def test_is_configured_false_when_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from lib.providers import claude_sdk
    assert claude_sdk.is_configured() is False


def test_is_configured_false_when_sdk_not_installed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from lib.providers import claude_sdk
    # Temporarily remove the sdk from sys.modules to simulate not installed
    with patch("lib.anthropic_direct_policy.direct_anthropic_api_enabled", return_value=True):
        with patch.object(claude_sdk, "_sdk_available", return_value=False):
            assert claude_sdk.is_configured() is False


def test_is_configured_false_when_config_disabled(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from lib.providers import claude_sdk
    with patch.object(claude_sdk, "_sdk_available", return_value=True):
        assert claude_sdk.is_configured() is False


def test_is_configured_true_when_config_key_and_sdk_available(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from lib.providers import claude_sdk
    with patch("lib.anthropic_direct_policy.direct_anthropic_api_enabled", return_value=True):
        with patch.object(claude_sdk, "_sdk_available", return_value=True):
            assert claude_sdk.is_configured() is True


def test_model_map_has_all_tiers():
    from lib.providers.claude_sdk import MODEL_MAP
    assert "opus" in MODEL_MAP
    assert "sonnet" in MODEL_MAP
    assert "haiku" in MODEL_MAP
    assert "claude" in MODEL_MAP["opus"].lower()
    assert "claude" in MODEL_MAP["sonnet"].lower()


def test_call_returns_error_when_not_configured(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from lib.providers import claude_sdk
    result = claude_sdk.call([{"role": "user", "content": "hi"}])
    assert result["success"] is False
    assert "error" in result
    assert result["error"]


def test_call_returns_error_when_sdk_not_installed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from lib.providers import claude_sdk
    with patch("lib.anthropic_direct_policy.direct_anthropic_api_enabled", return_value=True):
        with patch.object(claude_sdk, "get_client", return_value=None):
            result = claude_sdk.call([{"role": "user", "content": "hi"}])
    assert result["success"] is False
    assert "not installed" in result["error"] or "unavailable" in result["error"]


def test_estimate_cost_positive_for_known_model():
    from lib.providers.claude_sdk import estimate_cost
    cost = estimate_cost("claude-sonnet-4-6", 10_000, 5_000)
    assert cost > 0.0


def test_estimate_cost_uses_default_for_unknown_model():
    from lib.providers.claude_sdk import estimate_cost
    # Unknown model falls back to sonnet pricing
    cost = estimate_cost("unknown-claude-model", 10_000, 5_000)
    assert cost > 0.0  # should not return 0 (uses default)
