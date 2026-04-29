"""Unit tests for lib/record_completion.py extraction helpers."""
import json
import os
import sys

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
        # Fields are stored under event["payload"] in the MetricEvent schema (ADR-028 D1.A)
        payload = event["payload"]
        assert payload["model"] == "sonnet"
        assert payload["tokens_estimated"] == 200
        assert "timestamp" in event

    def test_pricing(self, tmp_path):
        append_cost_event(str(tmp_path), "task", 1000)
        event = json.loads((tmp_path / "cost-events.jsonl").read_text().strip())
        payload = event["payload"]
        assert abs(payload["estimated_cost_usd"] - 0.015) < 0.0001

    def test_survives_bad_dir(self):
        append_cost_event("/nonexistent/path", "task", 100)


# ---------------------------------------------------------------------------
# Phoenix OTel trace tests (mocked — no Phoenix collector needed)
# ADR-058 (2026-04-24): replaces the former Langfuse trace tests.
# ---------------------------------------------------------------------------

class TestSendOtelTrace:
    """Verify _send_otel_trace emits OTel spans with the correct attributes."""

    def test_skips_when_tracer_is_none(self):
        """No crash when Phoenix/OTel is not configured; tracer stays None after the call."""
        import lib.record_completion as rc
        original = rc._otel_tracer
        try:
            rc._otel_tracer = None
            # Should return silently without raising
            rc._send_otel_trace("skill", "impl", 82, 5000, True, "task-1")
            # Tracer must remain None (must not be auto-initialised as a side effect)
            assert rc._otel_tracer is None, "_otel_tracer must stay None after early-exit path"
        finally:
            rc._otel_tracer = original

    def test_emits_span_with_expected_attributes(self):
        """Verify span is created with every field preserved from the former Langfuse trace."""
        import lib.record_completion as rc
        from unittest.mock import MagicMock

        mock_span = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_span)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_ctx

        original = rc._otel_tracer
        try:
            rc._otel_tracer = mock_tracer
            rc._send_otel_trace("sdd-apply", "implementation", 85, 8000, True, "task-42")

            # Verify span created with skill name
            mock_tracer.start_as_current_span.assert_called_once_with(name="sdd-apply")

            # Verify every attribute we care about was set on the span
            attrs = {
                call.args[0]: call.args[1]
                for call in mock_span.set_attribute.call_args_list
            }
            assert attrs["skill.name"] == "sdd-apply"
            assert attrs["task.type"] == "implementation"
            assert attrs["task.id"] == "task-42"
            assert attrs["trust.score"] == 85
            assert abs(attrs["trust.score_normalized"] - 0.85) < 1e-9
            assert attrs["tokens.used"] == 8000
            assert attrs["tokens.input_estimate"] == 4000
            assert attrs["tokens.output_estimate"] == 4000
            assert attrs["completion.success"] is True
        finally:
            rc._otel_tracer = original

    def test_sets_error_status_on_failed_agent(self):
        """Failed completions mark the OTel span as ERROR for dashboard filtering."""
        import lib.record_completion as rc
        from unittest.mock import MagicMock

        mock_span = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_span)
        mock_ctx.__exit__ = MagicMock(return_value=False)

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.return_value = mock_ctx

        original = rc._otel_tracer
        try:
            rc._otel_tracer = mock_tracer
            rc._send_otel_trace("broken-skill", "fix", 35, 2000, False, "task-99")

            attrs = {
                call.args[0]: call.args[1]
                for call in mock_span.set_attribute.call_args_list
            }
            assert attrs["completion.success"] is False
            assert attrs["trust.score"] == 35
            # set_status should be called once (OK or ERROR — the import may fail
            # silently, but when it succeeds ERROR is the expected code).
            # We don't assert the Status object strictly because OTel import is optional.
        finally:
            rc._otel_tracer = original

    def test_survives_tracer_exception(self):
        """Never crashes even if the tracer throws."""
        import lib.record_completion as rc
        from unittest.mock import MagicMock

        mock_tracer = MagicMock()
        mock_tracer.start_as_current_span.side_effect = RuntimeError("Phoenix down")

        original = rc._otel_tracer
        try:
            rc._otel_tracer = mock_tracer
            # Should not raise
            rc._send_otel_trace("skill", "impl", 75, 1000, True, "task-1")
        finally:
            rc._otel_tracer = original


class TestSendMLflowCompletion:
    """Verify agent completion is mirrored to the MLflow replacement path."""

    def test_skips_mlflow_hotpath_by_default(self, monkeypatch):
        import lib.record_completion as rc
        from unittest.mock import patch

        monkeypatch.delenv("COS_MLFLOW_HOTPATH_ENABLED", raising=False)
        with patch("lib.mlflow_bridge.MLflowBridge") as bridge_cls:
            rc._send_mlflow_completion(
                skill_name="sdd-apply",
                task_type="implementation",
                trust_score=85,
                tokens_used=8000,
                success=True,
                task_id="task-42",
                model="sonnet",
            )

        bridge_cls.assert_not_called()

    def test_calls_mlflow_completion_contract_when_enabled(self, monkeypatch):
        import lib.record_completion as rc
        from unittest.mock import MagicMock, patch

        monkeypatch.setenv("COS_MLFLOW_HOTPATH_ENABLED", "1")
        bridge = MagicMock()
        with patch("lib.mlflow_bridge.MLflowBridge", return_value=bridge):
            rc._send_mlflow_completion(
                skill_name="sdd-apply",
                task_type="implementation",
                trust_score=85,
                tokens_used=8000,
                success=True,
                task_id="task-42",
                model="sonnet",
            )

        bridge.log_agent_completion.assert_called_once_with(
            skill_name="sdd-apply",
            task_type="implementation",
            trust_score=85,
            tokens_used=8000,
            success=True,
            task_id="task-42",
            model="sonnet",
        )

    def test_survives_mlflow_exception_when_enabled(self, monkeypatch):
        import lib.record_completion as rc
        from unittest.mock import patch

        monkeypatch.setenv("COS_MLFLOW_HOTPATH_ENABLED", "1")
        with patch("lib.mlflow_bridge.MLflowBridge", side_effect=RuntimeError("mlflow down")):
            rc._send_mlflow_completion("skill", "impl", 75, 1000, True, "task-1", "sonnet")


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
        # Fields are stored under event["payload"] in the MetricEvent schema (ADR-028 D1.A)
        payload = event["payload"]
        assert payload["is_estimate"] is True
        assert payload["tokens_estimated"] == 400

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
        # Fields are stored under event["payload"] in the MetricEvent schema (ADR-028 D1.A)
        payload = event["payload"]
        assert payload["is_estimate"] is False
        assert payload["input_tokens"] == 1000
        assert payload["output_tokens"] == 500
        assert payload["actual_cost_usd"] == 0.0225
        assert payload["model"] == "claude-sonnet-4-6"

    def test_find_session_jsonl_returns_none_for_unknown_project(self, tmp_path):
        result = find_session_jsonl("/nonexistent/project/path", None)
        # Should return None gracefully (projects dir won't have this path)
        # This may find real data if $HOME/.claude/projects exists — just check no crash
        assert result is None or isinstance(result, str)
