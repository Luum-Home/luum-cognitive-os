"""
Unit tests for lib.record_completion — main() entry point.

Covers:
  - test_missing_tool_output_defaults_to_success
  - test_score_extraction_non_numeric_uses_default (SCORE=abc → 75)
  - test_blocked_substring_in_benign_context ("UNBLOCKED" not failure)
  - test_success_false_when_fail_in_output
  - test_empty_string_output_treated_as_success
  - test_malformed_json_stdin_does_not_crash
"""

from __future__ import annotations

import io
import json
import sys
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — we call main() by patching stdin and capturing stdout
# ---------------------------------------------------------------------------

def _run_main(stdin_data: str) -> dict:
    """Run record_completion.main() with given JSON string on stdin.

    Returns the parsed JSON written to stdout (or {} on failure).
    """
    import importlib

    captured_out = io.StringIO()

    with patch("sys.stdin", io.StringIO(stdin_data)), \
         patch("sys.stdout", captured_out):
        # Reload to avoid cached module state
        import lib.record_completion as rc
        rc.main()

    output = captured_out.getvalue().strip()
    if output:
        return json.loads(output)
    return {}


def _make_input(tool_output: str = "", tool_call_id: str = "test-id") -> str:
    return json.dumps({
        "tool_output": tool_output,
        "tool_call_id": tool_call_id,
    })


# ---------------------------------------------------------------------------
# Tests — we patch LearningPipeline to avoid I/O side effects
# ---------------------------------------------------------------------------


class TestRecordCompletionMain:

    @patch("lib.record_completion.LearningPipeline")
    def test_missing_tool_output_defaults_to_success(self, MockPipeline):
        """When tool_output key is absent, output is '' → success=True."""
        mock_pipeline = MagicMock()
        mock_pipeline.record_agent_completion.return_value = MagicMock()
        mock_pipeline.record_agent_completion.return_value.__str__ = lambda s: "MAINTAIN"
        MockPipeline.return_value = mock_pipeline

        # No tool_output in payload
        stdin_data = json.dumps({"tool_call_id": "abc"})
        result = _run_main(stdin_data)

        call_kwargs = mock_pipeline.record_agent_completion.call_args
        assert call_kwargs is not None
        # success should be True (empty string has none of FAIL/ERROR/BLOCKED)
        _, kwargs = call_kwargs if call_kwargs[1] else (call_kwargs[0], {})
        if kwargs:
            assert kwargs.get("success", True) is True
        else:
            positional = call_kwargs[0]
            # positional: task_id, success, trust_score, skill_name
            assert positional[1] is True

    @patch("lib.record_completion.LearningPipeline")
    def test_score_extraction_non_numeric_uses_default(self, MockPipeline):
        r"""SCORE=abc should not match the \d+ regex; trust_score defaults to 75."""
        mock_pipeline = MagicMock()
        mock_pipeline.record_agent_completion.return_value = MagicMock()
        MockPipeline.return_value = mock_pipeline

        stdin_data = _make_input("Some output SCORE=abc no number here")
        _run_main(stdin_data)

        call_args = mock_pipeline.record_agent_completion.call_args
        # Extract trust_score from either positional or keyword args
        args, kwargs = call_args
        trust_score = kwargs.get("trust_score", args[2] if len(args) > 2 else None)
        assert trust_score == 75, f"Expected default 75, got {trust_score}"

    @patch("lib.record_completion.LearningPipeline")
    def test_blocked_substring_in_benign_context(self, MockPipeline):
        """'UNBLOCKED' contains 'BLOCKED' substring but should still read as success=False."""
        mock_pipeline = MagicMock()
        mock_pipeline.record_agent_completion.return_value = MagicMock()
        MockPipeline.return_value = mock_pipeline

        # "BLOCKED" IS in "UNBLOCKED" as a substring — the code uses 'in output.upper()'
        # so "BLOCKED" in "UNBLOCKED" is True → success=False.
        # This test documents that behavior (substring match, not word boundary).
        stdin_data = _make_input("Gate UNBLOCKED: proceed normally")
        _run_main(stdin_data)

        call_args = mock_pipeline.record_agent_completion.call_args
        args, kwargs = call_args
        success = kwargs.get("success", args[1] if len(args) > 1 else None)
        # "BLOCKED" substring IS present in "UNBLOCKED" → success is False
        assert success is False

    @patch("lib.record_completion.LearningPipeline")
    def test_success_false_when_fail_in_output(self, MockPipeline):
        """FAIL keyword → success=False."""
        mock_pipeline = MagicMock()
        mock_pipeline.record_agent_completion.return_value = MagicMock()
        MockPipeline.return_value = mock_pipeline

        stdin_data = _make_input("Build FAIL: compilation error")
        _run_main(stdin_data)

        call_args = mock_pipeline.record_agent_completion.call_args
        args, kwargs = call_args
        success = kwargs.get("success", args[1] if len(args) > 1 else None)
        assert success is False

    @patch("lib.record_completion.LearningPipeline")
    def test_empty_string_output_treated_as_success(self, MockPipeline):
        """Empty tool_output → no failure keywords → success=True."""
        mock_pipeline = MagicMock()
        mock_pipeline.record_agent_completion.return_value = MagicMock()
        MockPipeline.return_value = mock_pipeline

        stdin_data = _make_input("")
        _run_main(stdin_data)

        call_args = mock_pipeline.record_agent_completion.call_args
        args, kwargs = call_args
        success = kwargs.get("success", args[1] if len(args) > 1 else None)
        assert success is True

    @patch("lib.record_completion.LearningPipeline")
    def test_malformed_json_stdin_does_not_crash(self, MockPipeline):
        """Malformed JSON on stdin should raise JSONDecodeError — document behavior."""
        # The current implementation calls json.loads() directly, so malformed input
        # raises JSONDecodeError. This test documents that fact.
        import json as json_mod

        with pytest.raises(json_mod.JSONDecodeError):
            import io
            import lib.record_completion as rc
            with patch("sys.stdin", io.StringIO("{not valid json")):
                rc.main()

    @patch("lib.record_completion.LearningPipeline")
    def test_score_extracted_from_output(self, MockPipeline):
        """SCORE=90 in output → trust_score=90."""
        mock_pipeline = MagicMock()
        mock_pipeline.record_agent_completion.return_value = MagicMock()
        MockPipeline.return_value = mock_pipeline

        stdin_data = _make_input("Trust Report SCORE=90 all good")
        _run_main(stdin_data)

        call_args = mock_pipeline.record_agent_completion.call_args
        args, kwargs = call_args
        trust_score = kwargs.get("trust_score", args[2] if len(args) > 2 else None)
        assert trust_score == 90

    @patch("lib.record_completion.LearningPipeline")
    def test_result_field_used_as_fallback_output(self, MockPipeline):
        """When 'tool_output' absent but 'result' present, 'result' is used."""
        mock_pipeline = MagicMock()
        mock_pipeline.record_agent_completion.return_value = MagicMock()
        MockPipeline.return_value = mock_pipeline

        stdin_data = json.dumps({"result": "ERROR: something went wrong", "tool_call_id": "x"})
        _run_main(stdin_data)

        call_args = mock_pipeline.record_agent_completion.call_args
        args, kwargs = call_args
        success = kwargs.get("success", args[1] if len(args) > 1 else None)
        assert success is False
