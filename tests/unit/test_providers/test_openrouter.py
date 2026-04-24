"""Tests for lib/providers/openrouter.py (ADR-062)."""

from unittest.mock import MagicMock, patch


def test_is_configured_false_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from lib.providers import openrouter
    assert openrouter.is_configured() is False


def test_is_configured_true_when_key_set(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    from lib.providers import openrouter
    assert openrouter.is_configured() is True


def test_model_map_has_all_tiers():
    from lib.providers.openrouter import MODEL_MAP
    assert "opus" in MODEL_MAP
    assert "sonnet" in MODEL_MAP
    assert "haiku" in MODEL_MAP


def test_call_returns_error_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from lib.providers import openrouter
    result = openrouter.call([{"role": "user", "content": "hi"}])
    assert result["success"] is False
    assert result["error"]


def test_call_with_mocked_client_normalized_response(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    mock_msg = MagicMock()
    mock_msg.content = "response from openrouter"
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 15
    mock_usage.completion_tokens = 30
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    mock_response.model = "meta-llama/llama-3-70b"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    from lib.providers import openrouter
    with patch.object(openrouter, "get_client", return_value=mock_client):
        result = openrouter.call([{"role": "user", "content": "hi"}], model_hint="sonnet")

    assert result["success"] is True
    assert result["text"] == "response from openrouter"
    assert result["tokens_in"] == 15
    assert result["tokens_out"] == 30


def test_base_url_correct():
    from lib.providers.openrouter import BASE_URL
    assert "openrouter.ai" in BASE_URL
