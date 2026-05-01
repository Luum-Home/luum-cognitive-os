"""Unit tests for packages/advisor-mcp/advisor_server.py

Validates:
- Tool definition / registration
- Provider routing logic (all providers mocked)
- Cost logging format
- Graceful fallback when SDK not installed
- max_tokens is forwarded to providers
- Unknown provider returns error string
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGE_DIR = PROJECT_ROOT / "packages" / "advisor-mcp"
sys.path.insert(0, str(PACKAGE_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# Helper: run a coroutine synchronously (no pytest-asyncio needed)
# ---------------------------------------------------------------------------

def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def advisor():
    """Import advisor_server fresh per test (avoids module-level side effects)."""
    if "advisor_server" in sys.modules:
        del sys.modules["advisor_server"]
    import advisor_server as mod
    return mod


# ---------------------------------------------------------------------------
# Tool definition tests
# ---------------------------------------------------------------------------


class TestToolDefinition:
    """The MCP server must expose exactly one tool: consult_advisor."""

    def test_mcp_server_name(self, advisor):
        assert advisor.mcp.name == "advisor"

    def test_consult_advisor_is_callable(self, advisor):
        assert callable(advisor.consult_advisor)

    def test_tool_is_async(self, advisor):
        import inspect
        assert inspect.iscoroutinefunction(advisor.consult_advisor)

    def test_tool_parameters_present(self, advisor):
        import inspect
        sig = inspect.signature(advisor.consult_advisor)
        params = set(sig.parameters.keys())
        assert "context" in params
        assert "question" in params
        assert "provider" in params
        assert "model" in params
        assert "max_tokens" in params

    def test_default_provider_is_local(self, advisor):
        import inspect
        sig = inspect.signature(advisor.consult_advisor)
        assert sig.parameters["provider"].default == "local"

    def test_default_max_tokens_is_500(self, advisor):
        import inspect
        sig = inspect.signature(advisor.consult_advisor)
        assert sig.parameters["max_tokens"].default == 500

    def test_default_model_is_empty_string(self, advisor):
        import inspect
        sig = inspect.signature(advisor.consult_advisor)
        assert sig.parameters["model"].default == ""


# ---------------------------------------------------------------------------
# Provider routing tests
# ---------------------------------------------------------------------------


class TestProviderRouting:
    """Each provider routes to the correct backend function."""

    def test_routes_to_anthropic(self, advisor):
        mock_reply = ("Use write-through.", 100, 20)
        with patch.object(advisor, "_call_anthropic", new=AsyncMock(return_value=mock_reply)):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="anthropic"
            ))
        assert result == "Use write-through."

    def test_routes_to_openai(self, advisor):
        mock_reply = ("Consider a saga pattern.", 80, 15)
        with patch.object(advisor, "_call_openai", new=AsyncMock(return_value=mock_reply)):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="openai"
            ))
        assert result == "Consider a saga pattern."

    def test_routes_to_google(self, advisor):
        mock_reply = ("Prefer event sourcing.", 90, 18)
        with patch.object(advisor, "_call_google", new=AsyncMock(return_value=mock_reply)):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="google"
            ))
        assert result == "Prefer event sourcing."

    def test_routes_to_litellm(self, advisor):
        mock_reply = ("Use circuit breaker.", 60, 12)
        with patch.object(advisor, "_call_litellm", new=AsyncMock(return_value=mock_reply)):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="litellm"
            ))
        assert result == "Use circuit breaker."

    def test_routes_to_local(self, advisor):
        mock_reply = ("Apply bulkhead isolation.", 50, 10)
        with patch.object(advisor, "_call_local", new=AsyncMock(return_value=mock_reply)):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="local"
            ))
        assert result == "Apply bulkhead isolation."

    def test_unknown_provider_returns_error(self, advisor):
        result = _run(advisor.consult_advisor(
            context="ctx", question="q?", provider="unknown_provider"
        ))
        assert result.startswith("ERROR:")
        assert "unknown_provider" in result

    def test_provider_is_case_insensitive(self, advisor):
        mock_reply = ("Advice here.", 50, 10)
        with patch.object(advisor, "_call_anthropic", new=AsyncMock(return_value=mock_reply)):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="ANTHROPIC"
            ))
        assert result == "Advice here."

    def test_model_override_forwarded(self, advisor):
        """Explicit model override must be passed to the provider function."""
        captured_model: list[str] = []

        async def fake_call(context, question, model, max_tokens):
            captured_model.append(model)
            return ("ok", 10, 5)

        with patch.object(advisor, "_call_anthropic", new=fake_call):
            _run(advisor.consult_advisor(
                context="ctx",
                question="q?",
                provider="anthropic",
                model="claude-sonnet-4",
            ))
        assert captured_model == ["claude-sonnet-4"]

    def test_default_model_used_when_empty(self, advisor):
        """Empty model string → default for provider."""
        captured_model: list[str] = []

        async def fake_call(context, question, model, max_tokens):
            captured_model.append(model)
            return ("ok", 10, 5)

        with patch.object(advisor, "_call_anthropic", new=fake_call):
            _run(advisor.consult_advisor(
                context="ctx",
                question="q?",
                provider="anthropic",
                model="",
            ))
        assert captured_model == [advisor._DEFAULT_MODELS["anthropic"]]

    def test_max_tokens_forwarded_to_provider(self, advisor):
        """max_tokens must be passed through to the backend call."""
        captured_max: list[int] = []

        async def fake_call(context, question, model, max_tokens):
            captured_max.append(max_tokens)
            return ("ok", 10, 5)

        with patch.object(advisor, "_call_openai", new=fake_call):
            _run(advisor.consult_advisor(
                context="ctx",
                question="q?",
                provider="openai",
                max_tokens=123,
            ))
        assert captured_max == [123]


# ---------------------------------------------------------------------------
# Graceful degradation tests
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """Missing SDK → error string, not exception."""

    def test_anthropic_sdk_missing_returns_error(self, advisor):
        """Simulate anthropic not installed."""
        async def missing_sdk(ctx, q, model, max_tokens):
            return ("ERROR: 'anthropic' SDK not installed. Run: pip install anthropic", 0, 0)

        with patch.object(advisor, "_call_anthropic", new=missing_sdk):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="anthropic"
            ))
        assert "ERROR:" in result
        assert "anthropic" in result.lower()

    def test_anthropic_provider_disabled_by_config(self, advisor):
        """Anthropic direct API cannot run unless the shared policy enables it."""
        with patch(
            "lib.anthropic_direct_policy.direct_anthropic_api_enabled",
            return_value=False,
        ):
            result = _run(advisor._call_anthropic(
                context="ctx",
                question="q?",
                model="claude-opus-4-6",
                max_tokens=50,
            ))
        assert result[0].startswith("ERROR:")
        assert "disabled" in result[0]

    def test_openai_sdk_missing_returns_error(self, advisor):
        async def missing_sdk(ctx, q, model, max_tokens):
            return ("ERROR: 'openai' SDK not installed. Run: pip install openai", 0, 0)

        with patch.object(advisor, "_call_openai", new=missing_sdk):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="openai"
            ))
        assert "ERROR:" in result

    def test_google_sdk_missing_returns_error(self, advisor):
        async def missing_sdk(ctx, q, model, max_tokens):
            return ("ERROR: 'google-generativeai' SDK not installed.", 0, 0)

        with patch.object(advisor, "_call_google", new=missing_sdk):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="google"
            ))
        assert "ERROR:" in result

    def test_api_exception_returns_error_string(self, advisor):
        """Provider raises an exception → error string, not crash."""
        async def failing_call(ctx, q, model, max_tokens):
            raise ConnectionError("timeout")

        with patch.object(advisor, "_call_anthropic", new=failing_call):
            result = _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="anthropic"
            ))
        assert result.startswith("ERROR:")
        assert "ConnectionError" in result


# ---------------------------------------------------------------------------
# Cost logging tests
# ---------------------------------------------------------------------------


class TestCostLogging:
    """Consultation records must be written with the correct schema."""

    def test_log_written_on_success(self, advisor, tmp_path):
        """A successful consultation produces a JSONL entry."""
        log_path = tmp_path / ".cognitive-os" / "metrics" / "advisor-consultations.jsonl"
        mock_reply = ("Use CQRS.", 200, 50)

        with patch.object(advisor, "PROJECT_ROOT", tmp_path), \
             patch.object(advisor, "_call_anthropic", new=AsyncMock(return_value=mock_reply)):
            _run(advisor.consult_advisor(
                context="some context",
                question="Which pattern for this?",
                provider="anthropic",
            ))

        assert log_path.exists(), "Log file must be created"
        records = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
        assert len(records) == 1
        rec = records[0]
        assert rec["provider"] == "anthropic"
        assert rec["model"] == advisor._DEFAULT_MODELS["anthropic"]
        assert rec["input_tokens"] == 200
        assert rec["output_tokens"] == 50
        assert "estimated_cost_usd" in rec
        assert isinstance(rec["estimated_cost_usd"], float)
        assert "timestamp" in rec
        assert "question_preview" in rec
        assert len(rec["question_preview"]) <= 100

    def test_no_log_on_error_reply(self, advisor, tmp_path):
        """Error replies (SDK missing etc.) must NOT be logged."""
        log_path = tmp_path / ".cognitive-os" / "metrics" / "advisor-consultations.jsonl"

        async def error_reply(ctx, q, model, max_tokens):
            return ("ERROR: SDK not installed", 0, 0)

        with patch.object(advisor, "PROJECT_ROOT", tmp_path), \
             patch.object(advisor, "_call_anthropic", new=error_reply):
            _run(advisor.consult_advisor(
                context="ctx", question="q?", provider="anthropic"
            ))

        assert not log_path.exists(), "Log must NOT be written for error replies"

    def test_question_preview_truncated_to_100_chars(self, advisor, tmp_path):
        """question_preview must be at most 100 characters."""
        long_question = "x" * 200
        log_path = tmp_path / ".cognitive-os" / "metrics" / "advisor-consultations.jsonl"
        mock_reply = ("Advice.", 100, 20)

        with patch.object(advisor, "PROJECT_ROOT", tmp_path), \
             patch.object(advisor, "_call_anthropic", new=AsyncMock(return_value=mock_reply)):
            _run(advisor.consult_advisor(
                context="ctx",
                question=long_question,
                provider="anthropic",
            ))

        rec = json.loads(log_path.read_text().strip())
        assert len(rec["question_preview"]) == 100

    def test_cost_estimation_anthropic_opus(self, advisor):
        """Spot-check cost formula for claude-opus-4-6."""
        # 1M input @ $15 + 1M output @ $75 = $90
        cost = advisor._estimate_cost("claude-opus-4-6", 1_000_000, 1_000_000)
        assert abs(cost - 90.0) < 0.001

    def test_cost_estimation_unknown_model_is_zero(self, advisor):
        cost = advisor._estimate_cost("some-unknown-model", 1_000_000, 1_000_000)
        assert cost == 0.0

    def test_log_appends_multiple_records(self, advisor, tmp_path):
        """Multiple consultations append multiple lines."""
        log_path = tmp_path / ".cognitive-os" / "metrics" / "advisor-consultations.jsonl"
        mock_reply = ("ok", 50, 10)

        async def _two_calls():
            with patch.object(advisor, "PROJECT_ROOT", tmp_path), \
                 patch.object(advisor, "_call_anthropic", new=AsyncMock(return_value=mock_reply)):
                await advisor.consult_advisor(context="c", question="q1", provider="anthropic")
                await advisor.consult_advisor(context="c", question="q2", provider="anthropic")

        _run(_two_calls())

        records = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
        assert len(records) == 2


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------


class TestSystemPrompt:
    """The advisor system prompt must enforce the no-code contract."""

    def test_system_prompt_forbids_code_writing(self, advisor):
        assert "do NOT write code" in advisor.ADVISOR_SYSTEM_PROMPT

    def test_system_prompt_mentions_200_words(self, advisor):
        assert "200 words" in advisor.ADVISOR_SYSTEM_PROMPT

    def test_system_prompt_mentions_numbered_steps(self, advisor):
        assert "numbered steps" in advisor.ADVISOR_SYSTEM_PROMPT
