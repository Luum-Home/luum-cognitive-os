"""Tests for lib/providers/gemini.py (ADR-062)."""

from unittest.mock import MagicMock, patch


def test_is_configured_false_when_no_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from lib.providers import gemini
    assert gemini.is_configured() is False


def test_is_configured_true_when_key_set(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "ai-test-key")
    from lib.providers import gemini
    assert gemini.is_configured() is True


def test_model_map_has_all_tiers():
    from lib.providers.gemini import MODEL_MAP
    assert "opus" in MODEL_MAP
    assert "sonnet" in MODEL_MAP
    assert "haiku" in MODEL_MAP
    assert "gemini" in MODEL_MAP["opus"].lower()
    assert "gemini" in MODEL_MAP["sonnet"].lower()


def test_call_returns_error_when_no_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from lib.providers import gemini
    result = gemini.call([{"role": "user", "content": "hi"}])
    assert result["success"] is False
    assert result["error"]


def test_call_with_mocked_client_normalized_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "ai-test-key")

    mock_msg = MagicMock()
    mock_msg.content = "response from gemini"
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 12
    mock_usage.completion_tokens = 25
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    from lib.providers import gemini
    with patch.object(gemini, "get_client", return_value=mock_client):
        result = gemini.call([{"role": "user", "content": "hi"}], model_hint="haiku")

    assert result["success"] is True
    assert result["text"] == "response from gemini"
    assert result["model"] == "gemini-2.0-flash-lite"  # haiku maps to flash-lite


def test_base_url_points_to_google():
    from lib.providers.gemini import BASE_URL
    assert "generativelanguage.googleapis.com" in BASE_URL
