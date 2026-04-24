"""Tests for lib/providers/qwen.py (ADR-062)."""

import os
from unittest.mock import MagicMock, patch


def test_is_configured_false_when_no_key(monkeypatch):
    monkeypatch.delenv("ALIBABA_QWEN_API_KEY", raising=False)
    monkeypatch.setenv("_COS_QWEN_DOTENV_LOADED", "1")  # prevent .env loading
    from lib.providers import qwen
    assert qwen.is_configured() is False


def test_is_configured_true_when_key_set(monkeypatch):
    monkeypatch.setenv("ALIBABA_QWEN_API_KEY", "test-key")
    monkeypatch.setenv("_COS_QWEN_DOTENV_LOADED", "1")
    from lib.providers import qwen
    assert qwen.is_configured() is True


def test_model_map_has_all_tiers():
    from lib.providers.qwen import MODEL_MAP
    assert "opus" in MODEL_MAP
    assert "sonnet" in MODEL_MAP
    assert "haiku" in MODEL_MAP


def test_call_returns_error_when_no_client(monkeypatch):
    monkeypatch.delenv("ALIBABA_QWEN_API_KEY", raising=False)
    monkeypatch.setenv("_COS_QWEN_DOTENV_LOADED", "1")
    from lib.providers import qwen
    result = qwen.call([{"role": "user", "content": "hi"}])
    assert result["success"] is False
    assert "error" in result
    assert result["error"]


def test_call_with_mocked_client_returns_normalized_response(monkeypatch):
    monkeypatch.setenv("ALIBABA_QWEN_API_KEY", "test-key")
    monkeypatch.setenv("_COS_QWEN_DOTENV_LOADED", "1")

    mock_msg = MagicMock()
    mock_msg.content = "hello from qwen"
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 20
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    from lib.providers import qwen
    with patch.object(qwen, "get_client", return_value=mock_client):
        result = qwen.call([{"role": "user", "content": "hi"}], model_hint="sonnet")

    assert result["success"] is True
    assert result["text"] == "hello from qwen"
    assert result["tokens_in"] == 10
    assert result["tokens_out"] == 20
    assert "model" in result
    assert "cost_usd" in result


def test_model_hint_maps_to_native_model():
    from lib.providers.qwen import MODEL_MAP, call
    # model_hint="sonnet" should resolve to MODEL_MAP["sonnet"]
    # We just verify the map itself is correct
    assert MODEL_MAP["sonnet"] == "qwen3-coder-plus"
    assert MODEL_MAP["opus"] == "qwen3.6-plus"


def test_estimate_cost_zero_for_unknown_model():
    from lib.providers.qwen import estimate_cost
    assert estimate_cost("unknown-model", 1000, 1000) == 0.0


def test_estimate_cost_positive_for_known_model():
    from lib.providers.qwen import estimate_cost
    cost = estimate_cost("qwen3.6-plus", 100_000, 10_000)
    assert cost > 0.0
