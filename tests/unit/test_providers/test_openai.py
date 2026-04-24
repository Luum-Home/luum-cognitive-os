"""Tests for lib/providers/openai.py (ADR-062 opt-in)."""

from unittest.mock import MagicMock, patch


def test_is_configured_false_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from lib.providers import openai
    assert openai.is_configured() is False


def test_is_configured_true_when_key_set(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from lib.providers import openai
    assert openai.is_configured() is True


def test_model_map_has_all_tiers():
    from lib.providers.openai import MODEL_MAP
    assert "opus" in MODEL_MAP
    assert "sonnet" in MODEL_MAP
    assert "haiku" in MODEL_MAP


def test_call_returns_error_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from lib.providers import openai
    result = openai.call([{"role": "user", "content": "hi"}])
    assert result["success"] is False
    assert result["error"]


def test_call_with_mocked_client_normalized_response(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    mock_msg = MagicMock()
    mock_msg.content = "response from openai"
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 20
    mock_usage.completion_tokens = 40
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    from lib.providers import openai
    with patch.object(openai, "get_client", return_value=mock_client):
        result = openai.call([{"role": "user", "content": "hi"}], model_hint="sonnet")

    assert result["success"] is True
    assert result["text"] == "response from openai"
    assert result["model"] == "gpt-5.4"  # sonnet maps to gpt-5.4
    assert result["cost_usd"] > 0.0  # paid provider


def test_base_url_correct():
    from lib.providers.openai import BASE_URL
    assert "openai.com" in BASE_URL
