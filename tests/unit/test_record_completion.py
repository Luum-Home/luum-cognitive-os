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
        """No crash when Langfuse is not configured."""
        import lib.record_completion as rc
        original = rc._langfuse_client
        try:
            rc._langfuse_client = None
            # Should return silently, no exception
            rc._send_langfuse_trace("skill", "impl", 82, 5000, True, "task-1")
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
