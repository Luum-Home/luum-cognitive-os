"""Tests for lib/openai_compatible_agent_loop.py (ADR-062)."""

from __future__ import annotations

from unittest.mock import MagicMock


def _make_mock_client(text: str = "done", tool_calls: list | None = None):
    """Return a mock OpenAI-compatible client that produces the given response."""
    mock_msg = MagicMock()
    mock_msg.content = text
    mock_msg.tool_calls = tool_calls or []
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
    return mock_client


def test_run_agent_success_no_tools():
    from lib.openai_compatible_agent_loop import run_agent
    client = _make_mock_client(text="hello world")
    result = run_agent(task="say hi", provider="qwen", client=client)
    assert result.success is True
    assert result.text == "hello world"
    assert result.stop_reason == "finished"
    assert result.iterations == 1


def test_run_agent_provider_stored_in_result():
    from lib.openai_compatible_agent_loop import run_agent
    client = _make_mock_client(text="hi")
    result = run_agent(task="hi", provider="openrouter", client=client)
    assert result.provider == "openrouter"


def test_run_agent_different_provider_clients():
    """Verify loop is client-agnostic: same logic works with different provider mocks."""
    from lib.openai_compatible_agent_loop import run_agent

    for provider in ("qwen", "openrouter", "gemini", "ollama"):
        client = _make_mock_client(text=f"response from {provider}")
        result = run_agent(task="test", provider=provider, client=client)
        assert result.success is True, f"Loop failed for provider={provider}"
        assert provider in result.text


def test_run_agent_unknown_tool_in_allowed_list():
    from lib.openai_compatible_agent_loop import run_agent
    client = _make_mock_client(text="hi")
    result = run_agent(task="hi", provider="qwen", client=client, tools_allowed=["nonexistent_tool"])
    assert result.success is False
    assert "unknown tool" in result.error


def test_run_agent_no_client_returns_error():
    from lib.openai_compatible_agent_loop import run_agent
    from unittest.mock import patch
    from lib import providers
    # Make sure the provider registry returns None client
    with patch("lib.openai_compatible_agent_loop._resolve_client", return_value=None):
        result = run_agent(task="hi", provider="qwen")
    assert result.success is False
    assert "unavailable" in result.error.lower() or "not configured" in result.error.lower()


def test_run_agent_token_budget_enforced():
    from lib.openai_compatible_agent_loop import run_agent
    # Mock a client that always returns tokens but no tool calls (will finish iter 1)
    mock_msg = MagicMock()
    mock_msg.content = "done"
    mock_msg.tool_calls = []
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 60_000
    mock_usage.completion_tokens = 60_000  # exceeds budget=100K
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    result = run_agent(task="hi", provider="qwen", client=mock_client, token_budget=100_000)
    # Budget exceeded on first iter (120K > 100K)
    assert result.stop_reason == "budget"
    assert result.success is False


def test_run_agent_max_iterations_enforced():
    from lib.openai_compatible_agent_loop import run_agent

    # Tool call that keeps looping: mock always returns a read_file tool call
    call_count = [0]

    def make_response_with_tool_call():
        tc = MagicMock()
        tc.id = f"call_{call_count[0]}"
        tc.function.name = "read_file"
        tc.function.arguments = '{"path": "/tmp/test.txt"}'
        mock_msg = MagicMock()
        mock_msg.content = ""
        mock_msg.tool_calls = [tc]
        mock_choice = MagicMock()
        mock_choice.message = mock_msg
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 5
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        call_count[0] += 1
        return mock_response

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = lambda **kwargs: make_response_with_tool_call()

    result = run_agent(task="read loop", provider="qwen", client=mock_client, max_iterations=3)
    assert result.stop_reason == "max_iterations"
    assert result.iterations == 3
