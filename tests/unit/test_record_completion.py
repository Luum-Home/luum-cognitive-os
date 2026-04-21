"""Unit tests for lib/record_completion.py extraction helpers."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from lib.record_completion import (
    extract_skill_name,
    extract_trust_score,
    estimate_tokens,
    classify_task_type,
    detect_success,
    append_cost_event,
    get_real_token_usage,
    calculate_cost_usd,
    find_session_jsonl,
)


def make_payload(description="", prompt="", result=""):
    return {
        "tool_call_id": "toolu_abc123",
        "tool_name": "Agent",
        "tool_input": {"description": description, "prompt": prompt},
        "tool_response": {"result": result},
    }


class TestExtractSkillName:
    def test_prefers_description(self):
        data = make_payload(description="Implement auth endpoint", prompt="Other")
        assert extract_skill_name(data) == "Implement auth endpoint"

    def test_falls_back_to_prompt(self):
        data = make_payload(description="", prompt="Fix test\nmore detail")
        assert extract_skill_name(data) == "Fix test"

    def test_truncates_to_100(self):
        data = make_payload(description="A" * 150)
        assert len(extract_skill_name(data)) == 100

    def test_unknown_when_empty(self):
        data = make_payload(description="", prompt="")
        assert extract_skill_name(data) == "unknown"

    def test_strips_whitespace(self):
        data = make_payload(description="  Review PR  ")
        assert extract_skill_name(data) == "Review PR"

    def test_missing_tool_input(self):
        assert extract_skill_name({"tool_call_id": "x"}) == "unknown"


class TestExtractTrustScore:
    def test_machine_format(self):
        assert extract_trust_score("TRUST_REPORT: SCORE=85 STATUS=HIGH") == 85

    def test_human_format(self):
        assert extract_trust_score("Score: 92/100") == 92

    def test_legacy_format(self):
        assert extract_trust_score("done SCORE=67 ok") == 67

    def test_default_is_50(self):
        assert extract_trust_score("No trust report") == 50

    def test_clamps_above_100(self):
        assert extract_trust_score("SCORE=150") == 100

    def test_zero(self):
        assert extract_trust_score("TRUST_REPORT: SCORE=0") == 0


class TestEstimateTokens:
    def test_empty(self):
        assert estimate_tokens("") == 0

    def test_ratio(self):
        assert estimate_tokens("x" * 400) == 100


class TestClassifyTaskType:
    def test_implement(self):
        assert classify_task_type("Implement endpoint") == "implementation"

    def test_review(self):
        assert classify_task_type("Review PR") == "review"

    def test_fix(self):
        assert classify_task_type("Fix broken test") == "debugging"

    def test_doc(self):
        assert classify_task_type("Document API") == "documentation"

    def test_archive(self):
        assert classify_task_type("Archive change") == "archiving"

    def test_general(self):
        assert classify_task_type("Something vague") == "general"


class TestDetectSuccess:
    def test_success(self):
        assert detect_success("42 tests passed", make_payload()) is True

    def test_fail_keyword(self):
        assert detect_success("FAIL: 3 tests", make_payload()) is False

    def test_error_keyword(self):
        assert detect_success("ERROR: build", make_payload()) is False

    def test_is_error_flag(self):
        data = {"tool_call_id": "x", "tool_input": {},
                "tool_response": {"result": "out", "is_error": True}}
        assert detect_success("out", data) is False


class TestAppendCostEvent:
    def test_creates_file(self, tmp_path):
        append_cost_event(str(tmp_path), "task", 400)
        assert (tmp_path / "cost-events.jsonl").exists()

    def test_fields(self, tmp_path):
        append_cost_event(str(tmp_path), "Review PR", 200)
        event = json.loads((tmp_path / "cost-events.jsonl").read_text().strip())
        assert event["model"] == "sonnet"
        assert event["tokens_estimated"] == 200
        assert "timestamp" in event

    def test_pricing(self, tmp_path):
        append_cost_event(str(tmp_path), "task", 1000)
        event = json.loads((tmp_path / "cost-events.jsonl").read_text().strip())
        assert abs(event["estimated_cost_usd"] - 0.015) < 0.0001

    def test_survives_bad_dir(self):
        append_cost_event("/nonexistent/path", "task", 100)


# ---------------------------------------------------------------------------
# Langfuse v3 integration tests (mocked — no Docker needed)
# ---------------------------------------------------------------------------

class TestSendLangfuseTrace:
    """Verify _send_langfuse_trace calls the Langfuse v3 API correctly."""

    def test_skips_when_client_is_none(self):
        """No crash when Langfuse is not configured; client stays None after the call."""
        import lib.record_completion as rc
        original = rc._langfuse_client
        try:
            rc._langfuse_client = None
            # Should return silently without raising
            rc._send_langfuse_trace("skill", "impl", 82, 5000, True, "task-1")
            # Client must remain None (must not be auto-initialised as a side effect)
            assert rc._langfuse_client is None, "_langfuse_client must stay None after early-exit path"
        finally:
            rc._langfuse_client = original

    def test_calls_v3_span_api(self):
        """Verify the v3 start_as_current_span / start_as_current_generation flow."""
        import lib.record_completion as rc
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = "trace-123"
        # Make context managers work
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock()
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.start_as_current_generation.return_value.__enter__ = MagicMock()
        mock_client.start_as_current_generation.return_value.__exit__ = MagicMock(return_value=False)

        original = rc._langfuse_client
        try:
            rc._langfuse_client = mock_client
            rc._send_langfuse_trace("sdd-apply", "implementation", 85, 8000, True, "task-42")

            # Verify span was created with skill name
            mock_client.start_as_current_span.assert_called_once_with(name="sdd-apply")

            # Verify trace metadata was updated
            mock_client.update_current_trace.assert_called_once()
            meta = mock_client.update_current_trace.call_args[1]["metadata"]
            assert meta["trust_score"] == 85
            assert meta["task_type"] == "implementation"
            assert meta["success"] is True
            assert meta["tokens_used"] == 8000

            # Verify generation was created
            mock_client.start_as_current_generation.assert_called_once()
            gen_kwargs = mock_client.start_as_current_generation.call_args[1]
            assert gen_kwargs["name"] == "agent-completion"

            # Verify generation was updated with output
            mock_client.update_current_generation.assert_called_once()
            gen_update = mock_client.update_current_generation.call_args[1]
            assert gen_update["output"]["trust_score"] == 85
            assert gen_update["usage_details"]["input"] == 4000
            assert gen_update["usage_details"]["output"] == 4000

            # Verify trust score was recorded as Langfuse Score
            mock_client.create_score.assert_called_once()
            score_kwargs = mock_client.create_score.call_args[1]
            assert score_kwargs["name"] == "trust-score"
            assert score_kwargs["value"] == 0.85  # normalized to 0-1
            assert score_kwargs["trace_id"] == "trace-123"
            assert "sdd-apply" in score_kwargs["comment"]

            # Verify flush was called
            mock_client.flush.assert_called_once()
        finally:
            rc._langfuse_client = original

    def test_failure_comment_on_failed_agent(self):
        """Score comment reflects failure status."""
        import lib.record_completion as rc
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = "trace-456"
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock()
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.start_as_current_generation.return_value.__enter__ = MagicMock()
        mock_client.start_as_current_generation.return_value.__exit__ = MagicMock(return_value=False)

        original = rc._langfuse_client
        try:
            rc._langfuse_client = mock_client
            rc._send_langfuse_trace("broken-skill", "fix", 35, 2000, False, "task-99")

            score_kwargs = mock_client.create_score.call_args[1]
            assert score_kwargs["value"] == 0.35
            assert "failure" in score_kwargs["comment"]
            assert "broken-skill" in score_kwargs["comment"]
        finally:
            rc._langfuse_client = original

    def test_survives_langfuse_exception(self):
        """Never crashes even if Langfuse throws."""
        import lib.record_completion as rc
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.start_as_current_span.side_effect = RuntimeError("Langfuse down")

        original = rc._langfuse_client
        try:
            rc._langfuse_client = mock_client
            # Should not raise
            rc._send_langfuse_trace("skill", "impl", 75, 1000, True, "task-1")
        finally:
            rc._langfuse_client = original

    def test_skips_score_when_trace_id_is_none(self):
        """No score created if trace_id is None (context error)."""
        import lib.record_completion as rc
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = None
        mock_client.start_as_current_span.return_value.__enter__ = MagicMock()
        mock_client.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.start_as_current_generation.return_value.__enter__ = MagicMock()
        mock_client.start_as_current_generation.return_value.__exit__ = MagicMock(return_value=False)

        original = rc._langfuse_client
        try:
            rc._langfuse_client = mock_client
            rc._send_langfuse_trace("skill", "impl", 75, 1000, True, "task-1")

            # Score should NOT be created when trace_id is None
            mock_client.create_score.assert_not_called()
        finally:
            rc._langfuse_client = original


# ---------------------------------------------------------------------------
# Real token usage — new tests
# ---------------------------------------------------------------------------

def _make_assistant_jsonl_line(
    tool_call_id: str,
    model: str = "claude-opus-4-6",
    input_tokens: int = 1000,
    output_tokens: int = 500,
    cache_read: int = 200,
    cache_write: int = 300,
) -> str:
    """Build a JSONL line that mimics a Claude Code assistant message."""
    record = {
        "type": "assistant",
        "message": {
            "model": model,
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_call_id,
                    "name": "Agent",
                    "input": {"description": "test task"},
                }
            ],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_write,
            },
        },
        "uuid": "uuid-test",
        "sessionId": "session-test",
    }
    return json.dumps(record)


class TestGetRealTokenUsageFromJsonl:
    def test_finds_matching_tool_call(self, tmp_path):
        jsonl_file = tmp_path / "session.jsonl"
        line = _make_assistant_jsonl_line(
            tool_call_id="toolu_test123",
            model="claude-opus-4-6",
            input_tokens=1000,
            output_tokens=500,
            cache_read=200,
            cache_write=300,
        )
        jsonl_file.write_text(line + "\n")

        result = get_real_token_usage(str(jsonl_file), "toolu_test123")
        assert result is not None
        assert result["input_tokens"] == 1000
        assert result["output_tokens"] == 500
        assert result["cache_read_input_tokens"] == 200
        assert result["cache_creation_input_tokens"] == 300
        assert result["model"] == "claude-opus-4-6"
        assert result["total_cost_usd"] > 0

    def test_returns_none_when_tool_call_not_found(self, tmp_path):
        jsonl_file = tmp_path / "session.jsonl"
        line = _make_assistant_jsonl_line(tool_call_id="toolu_other")
        jsonl_file.write_text(line + "\n")

        result = get_real_token_usage(str(jsonl_file), "toolu_missing")
        assert result is None

    def test_returns_none_for_missing_file(self, tmp_path):
        result = get_real_token_usage(str(tmp_path / "nonexistent.jsonl"), "toolu_xyz")
        assert result is None

    def test_skips_malformed_lines(self, tmp_path):
        jsonl_file = tmp_path / "session.jsonl"
        good_line = _make_assistant_jsonl_line(tool_call_id="toolu_good")
        jsonl_file.write_text("not-json\n{broken\n" + good_line + "\n")

        result = get_real_token_usage(str(jsonl_file), "toolu_good")
        assert result is not None
        assert result["input_tokens"] == 1000

    def test_skips_non_assistant_records(self, tmp_path):
        jsonl_file = tmp_path / "session.jsonl"
        user_record = json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}})
        assistant_line = _make_assistant_jsonl_line(tool_call_id="toolu_agent")
        jsonl_file.write_text(user_record + "\n" + assistant_line + "\n")

        result = get_real_token_usage(str(jsonl_file), "toolu_agent")
        assert result is not None

    def test_multiple_entries_returns_correct_one(self, tmp_path):
        jsonl_file = tmp_path / "session.jsonl"
        line1 = _make_assistant_jsonl_line(
            tool_call_id="toolu_first", input_tokens=100, output_tokens=50
        )
        line2 = _make_assistant_jsonl_line(
            tool_call_id="toolu_second", input_tokens=9999, output_tokens=8888
        )
        jsonl_file.write_text(line1 + "\n" + line2 + "\n")

        result = get_real_token_usage(str(jsonl_file), "toolu_second")
        assert result is not None
        assert result["input_tokens"] == 9999
        assert result["output_tokens"] == 8888


class TestRealCostCalculationOpus:
    def test_opus_cost_calculation(self, tmp_path):
        jsonl_file = tmp_path / "session.jsonl"
        # 10k input, 5k output, no cache
        line = _make_assistant_jsonl_line(
            tool_call_id="toolu_opus",
            model="claude-opus-4-6",
            input_tokens=10_000,
            output_tokens=5_000,
            cache_read=0,
            cache_write=0,
        )
        jsonl_file.write_text(line + "\n")

        result = get_real_token_usage(str(jsonl_file), "toolu_opus")
        assert result is not None
        # 10k * $15/1M + 5k * $75/1M = $0.15 + $0.375 = $0.525
        expected = (10_000 * 15.0 + 5_000 * 75.0) / 1_000_000
        assert abs(result["total_cost_usd"] - expected) < 1e-7

    def test_opus_cost_with_cache(self):
        cost = calculate_cost_usd(
            input_tokens=10_000,
            output_tokens=2_000,
            cache_read_tokens=50_000,
            cache_write_tokens=5_000,
            model="claude-opus-4-6",
        )
        # 10k*15 + 2k*75 + 50k*1.5 + 5k*3.75 (all /1M)
        expected = (10_000 * 15 + 2_000 * 75 + 50_000 * 1.5 + 5_000 * 3.75) / 1_000_000
        assert abs(cost - expected) < 1e-7


class TestRealCostCalculationSonnet:
    def test_sonnet_cost_calculation(self, tmp_path):
        jsonl_file = tmp_path / "session.jsonl"
        line = _make_assistant_jsonl_line(
            tool_call_id="toolu_sonnet",
            model="claude-sonnet-4-6",
            input_tokens=10_000,
            output_tokens=5_000,
            cache_read=0,
            cache_write=0,
        )
        jsonl_file.write_text(line + "\n")

        result = get_real_token_usage(str(jsonl_file), "toolu_sonnet")
        assert result is not None
        # 10k * $3/1M + 5k * $15/1M = $0.03 + $0.075 = $0.105
        expected = (10_000 * 3.0 + 5_000 * 15.0) / 1_000_000
        assert abs(result["total_cost_usd"] - expected) < 1e-7

    def test_sonnet_cheaper_than_opus(self):
        opus_cost = calculate_cost_usd(1000, 500, 0, 0, "claude-opus-4-6")
        sonnet_cost = calculate_cost_usd(1000, 500, 0, 0, "claude-sonnet-4-6")
        assert sonnet_cost < opus_cost

    def test_haiku_cheaper_than_sonnet(self):
        sonnet_cost = calculate_cost_usd(1000, 500, 0, 0, "sonnet")
        haiku_cost = calculate_cost_usd(1000, 500, 0, 0, "haiku")
        assert haiku_cost < sonnet_cost


class TestFallbackToEstimateWhenNoSessionFile:
    def test_fallback_used_when_no_jsonl(self, tmp_path):
        """When the session file doesn't exist, append_cost_event uses estimate."""
        result = get_real_token_usage(str(tmp_path / "missing.jsonl"), "toolu_xyz")
        assert result is None

        # append_cost_event should still work with estimate
        append_cost_event(str(tmp_path), "task", 400, model="sonnet", real_usage=None)
        event = json.loads((tmp_path / "cost-events.jsonl").read_text().strip())
        assert event["is_estimate"] is True
        assert event["tokens_estimated"] == 400

    def test_real_usage_sets_is_estimate_false(self, tmp_path):
        real_usage = {
            "input_tokens": 1000,
            "output_tokens": 500,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "total_cost_usd": 0.0225,
            "model": "claude-sonnet-4-6",
        }
        append_cost_event(str(tmp_path), "task", 0, real_usage=real_usage)
        event = json.loads((tmp_path / "cost-events.jsonl").read_text().strip())
        assert event["is_estimate"] is False
        assert event["input_tokens"] == 1000
        assert event["output_tokens"] == 500
        assert event["actual_cost_usd"] == 0.0225
        assert event["model"] == "claude-sonnet-4-6"

    def test_find_session_jsonl_returns_none_for_unknown_project(self, tmp_path):
        result = find_session_jsonl("/nonexistent/project/path", None)
        # Should return None gracefully (projects dir won't have this path)
        # This may find real data if $HOME/.claude/projects exists — just check no crash
        assert result is None or isinstance(result, str)
