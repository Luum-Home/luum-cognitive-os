"""Tests for lib/providers/ollama.py (ADR-062)."""

from unittest.mock import MagicMock, patch


def test_is_configured_false_when_daemon_unreachable():
    from lib.providers import ollama
    with patch.object(ollama, "_check_daemon_reachable", return_value=False):
        assert ollama.is_configured() is False


def test_is_configured_true_when_daemon_reachable():
    from lib.providers import ollama
    with patch.object(ollama, "_check_daemon_reachable", return_value=True):
        assert ollama.is_configured() is True


def test_model_map_has_all_tiers():
    from lib.providers.ollama import MODEL_MAP
    assert "opus" in MODEL_MAP
    assert "sonnet" in MODEL_MAP
    assert "haiku" in MODEL_MAP


def test_call_returns_error_when_no_client():
    from lib.providers import ollama
    with patch.object(ollama, "get_client", return_value=None):
        result = ollama.call([{"role": "user", "content": "hi"}])
    assert result["success"] is False
    assert result["error"]


def test_call_with_mocked_client_normalized_response():
    mock_msg = MagicMock()
    mock_msg.content = "response from ollama"
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 8
    mock_usage.completion_tokens = 16
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    from lib.providers import ollama
    with patch.object(ollama, "get_client", return_value=mock_client):
        result = ollama.call([{"role": "user", "content": "hi"}], model_hint="haiku")

    assert result["success"] is True
    assert result["text"] == "response from ollama"
    assert result["cost_usd"] == 0.0  # local = free


def test_estimate_cost_always_zero():
    from lib.providers.ollama import estimate_cost
    assert estimate_cost("any-model", 1_000_000, 1_000_000) == 0.0


def test_default_base_url():
    from lib.providers import ollama
    url = ollama._base_url()
    assert "11434" in url
