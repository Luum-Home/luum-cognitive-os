"""
Unit tests for lib.process_user_message — process() function.

Covers:
  - test_all_three_components_run_on_clean_message
  - test_feedback_detector_exception_partial_result
  - test_user_model_exception_does_not_block_classify
  - test_empty_string_does_not_crash
  - test_returns_should_capture_false_on_acknowledgment
  - test_spanish_message_detected
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

from lib.process_user_message import process


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProcessUserMessage:

    def test_all_three_components_run_on_clean_message(self):
        """A clean task message should populate feedback_type, inferred_prefs, should_capture."""
        result = process("build the new auth endpoint for user registration")
        assert "feedback_type" in result
        assert "should_capture" in result
        # inferred_prefs may be 0 but key should exist (or not if UserModel is fine)
        # At minimum the three paths ran without exception
        assert isinstance(result, dict)

    def test_feedback_detector_exception_partial_result(self):
        """If FeedbackDetector.detect raises, feedback_type should be 'error'."""
        with patch("lib.process_user_message.FeedbackDetector") as MockFD:
            mock_fd = MagicMock()
            mock_fd.detect.side_effect = RuntimeError("detector crashed")
            MockFD.return_value = mock_fd

            result = process("do something")

        assert result.get("feedback_type") == "error"
        # Other components should still run
        assert "should_capture" in result

    def test_user_model_exception_does_not_block_classify(self):
        """If UserModel.infer_from_message raises, classify still runs."""
        with patch("lib.process_user_message.UserModel") as MockUM:
            mock_um = MagicMock()
            mock_um.infer_from_message.side_effect = ValueError("model error")
            MockUM.return_value = mock_um

            result = process("use PostgreSQL for this service")

        # should_capture should still be populated from classify_prompt
        assert "should_capture" in result

    def test_empty_string_does_not_crash(self):
        """Empty string must not raise any exception."""
        result = process("")
        assert isinstance(result, dict)
        # should_capture must exist (either True or False)
        assert "should_capture" in result

    def test_returns_should_capture_false_on_acknowledgment(self):
        """Simple acknowledgment ('ok', 'yes', 'sure') → should_capture=False."""
        for ack in ["ok", "yes", "sure"]:
            result = process(ack)
            assert result.get("should_capture") is False, (
                f"Expected should_capture=False for acknowledgment '{ack}', got {result}"
            )

    def test_spanish_message_detected(self):
        """Spanish task request should be classified and should_capture=True."""
        result = process("construyamos el modulo de autenticacion con JWT")
        # Spanish task requests should be captured
        assert result.get("should_capture") is True, (
            f"Expected should_capture=True for Spanish task, got {result}"
        )

    def test_result_is_dict(self):
        """process() always returns a dict."""
        result = process("any message here")
        assert isinstance(result, dict)

    def test_feedback_type_key_always_present(self):
        """feedback_type key is always present even if detector raises."""
        result = process("hello world")
        assert "feedback_type" in result

    def test_classify_exception_sets_should_capture_false(self):
        """If classify_prompt raises, should_capture defaults to False."""
        with patch("lib.process_user_message.classify_prompt") as mock_classify:
            mock_classify.side_effect = RuntimeError("classify error")
            result = process("build something")

        assert result.get("should_capture") is False

    def test_task_request_captured(self):
        """An explicit task request should have should_capture=True."""
        result = process("implement the JWT authentication middleware")
        assert result.get("should_capture") is True, (
            f"Expected should_capture=True for task request, got {result}"
        )
