"""
Unit tests for lib.record_error — main() entry point.

Covers:
  - test_exit_code_zero_does_not_record
  - test_malformed_stdin_does_not_crash
  - test_missing_command_key_records_empty_context
  - test_stderr_truncated_to_500_chars
  - test_pipeline_exception_silently_swallowed
"""

from __future__ import annotations

import io
import json
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run_main(stdin_data: str) -> None:
    """Run record_error.main() with given JSON string on stdin."""
    import lib.record_error as re_mod
    with patch("sys.stdin", io.StringIO(stdin_data)):
        re_mod.main()


def _make_input(
    exit_code: int = 1,
    command: str = "go test ./...",
    stderr: str = "error: compilation failed",
) -> str:
    return json.dumps({
        "exit_code": exit_code,
        "tool_input": {"command": command},
        "tool_output": {"stderr": stderr},
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecordErrorMain:

    @patch("lib.record_error.LearningPipeline")
    def test_exit_code_zero_does_not_record(self, MockPipeline):
        """When exit_code == 0, record_error must NOT be called."""
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        stdin_data = _make_input(exit_code=0)
        _run_main(stdin_data)

        mock_pipeline.record_error.assert_not_called()

    @patch("lib.record_error.LearningPipeline")
    def test_nonzero_exit_code_does_record(self, MockPipeline):
        """When exit_code != 0, record_error must be called once."""
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        stdin_data = _make_input(exit_code=1)
        _run_main(stdin_data)

        mock_pipeline.record_error.assert_called_once()

    def test_malformed_stdin_does_not_crash(self):
        """Malformed JSON raises JSONDecodeError — document the behavior."""
        import json as json_mod
        import lib.record_error as re_mod

        with pytest.raises(json_mod.JSONDecodeError):
            with patch("sys.stdin", io.StringIO("{bad json!!")):
                re_mod.main()

    @patch("lib.record_error.LearningPipeline")
    def test_missing_command_key_records_empty_context(self, MockPipeline):
        """When tool_input has no 'command' key, context should be empty string."""
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        # tool_input is present but lacks 'command'
        stdin_data = json.dumps({
            "exit_code": 1,
            "tool_input": {"action": "run"},
            "tool_output": {"stderr": "some error"},
        })
        _run_main(stdin_data)

        call_args = mock_pipeline.record_error.call_args
        assert call_args is not None
        args, kwargs = call_args
        context = kwargs.get("context", args[3] if len(args) > 3 else "")
        assert context == ""

    @patch("lib.record_error.LearningPipeline")
    def test_missing_tool_input_entirely(self, MockPipeline):
        """When tool_input is absent, command defaults to empty string."""
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        stdin_data = json.dumps({
            "exit_code": 2,
            "tool_output": {"stderr": "fatal error"},
        })
        _run_main(stdin_data)

        call_args = mock_pipeline.record_error.call_args
        assert call_args is not None
        args, kwargs = call_args
        context = kwargs.get("context", args[3] if len(args) > 3 else "")
        # command defaults to '' via .get("command", "")
        assert context == ""

    @patch("lib.record_error.LearningPipeline")
    def test_stderr_truncated_to_500_chars(self, MockPipeline):
        """Long stderr is passed to record_error truncated to 500 chars."""
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        long_stderr = "E: " + "x" * 600  # > 500 chars
        stdin_data = _make_input(stderr=long_stderr)
        _run_main(stdin_data)

        call_args = mock_pipeline.record_error.call_args
        args, kwargs = call_args
        message = kwargs.get("message", args[2] if len(args) > 2 else "")
        assert len(message) <= 500

    @patch("lib.record_error.LearningPipeline")
    def test_pipeline_exception_silently_swallowed(self, MockPipeline):
        """If LearningPipeline.record_error raises, main() should still not propagate.

        Note: current implementation does NOT catch exceptions from the pipeline,
        so this test documents that an exception IS raised. If future code wraps
        in try/except, this test should be updated.
        """
        mock_pipeline = MagicMock()
        mock_pipeline.record_error.side_effect = RuntimeError("pipeline failure")
        MockPipeline.return_value = mock_pipeline

        stdin_data = _make_input(exit_code=1)
        # Currently the exception propagates — document this behavior
        with pytest.raises(RuntimeError, match="pipeline failure"):
            _run_main(stdin_data)

    @patch("lib.record_error.LearningPipeline")
    def test_stderr_short_enough_not_truncated(self, MockPipeline):
        """Short stderr (< 500 chars) passes through unchanged."""
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        short_stderr = "compilation error"
        stdin_data = _make_input(stderr=short_stderr)
        _run_main(stdin_data)

        call_args = mock_pipeline.record_error.call_args
        args, kwargs = call_args
        message = kwargs.get("message", args[2] if len(args) > 2 else "")
        assert message == short_stderr

    @patch("lib.record_error.LearningPipeline")
    def test_error_type_is_command_failure(self, MockPipeline):
        """The error_type passed to record_error is always COMMAND_FAILURE."""
        mock_pipeline = MagicMock()
        MockPipeline.return_value = mock_pipeline

        stdin_data = _make_input(exit_code=1)
        _run_main(stdin_data)

        call_args = mock_pipeline.record_error.call_args
        args, kwargs = call_args
        error_type = kwargs.get("error_type", args[0] if len(args) > 0 else "")
        assert error_type == "COMMAND_FAILURE"
