"""Behavior tests for user prompt capture protocol.

Validates that the rule file exists, references mem_save_prompt correctly,
the classifier module is importable, and the integration between
classifier decisions and engram persistence works.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.behavior


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Rule file existence and content
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Classifier module importability
# ---------------------------------------------------------------------------


class TestClassifierModule:
    """Verify the classifier library is importable and has the expected API."""

    def test_module_importable(self):
        from lib.prompt_classifier import classify_prompt, should_capture_prompt
        assert callable(classify_prompt)
        assert callable(should_capture_prompt)

    def test_classification_result_has_expected_fields(self):
        from lib.prompt_classifier import classify_prompt
        result = classify_prompt("Build the auth module")
        assert hasattr(result, "category")
        assert hasattr(result, "should_capture")
        assert hasattr(result, "confidence")

    def test_prompt_category_enum_values(self):
        from lib.prompt_classifier import PromptCategory
        expected = {
            "task_request", "decision", "feedback", "context",
            "status_query", "navigation", "acknowledgment", "unknown",
        }
        actual = {member.value for member in PromptCategory}
        assert expected == actual

    def test_classifier_returns_bool_for_should_capture(self):
        from lib.prompt_classifier import classify_prompt
        result = classify_prompt("ok")
        assert isinstance(result.should_capture, bool)

    def test_classifier_returns_float_confidence(self):
        from lib.prompt_classifier import classify_prompt
        result = classify_prompt("Build the feature")
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# Integration: classifier + mem_save_prompt mock
# ---------------------------------------------------------------------------


class TestIntegration:
    """Simulate the orchestrator's prompt capture flow with a mocked engram."""

    def test_task_request_triggers_save(self):
        """A task request should trigger mem_save_prompt."""
        from lib.prompt_classifier import classify_prompt

        mock_save = MagicMock()
        message = "Build the authentication module for payments"
        result = classify_prompt(message)

        if result.should_capture:
            mock_save(content=message, project="test-project", session_id="sess-001")

        mock_save.assert_called_once_with(
            content=message,
            project="test-project",
            session_id="sess-001",
        )

    def test_acknowledgment_skips_save(self):
        """An acknowledgment should NOT trigger mem_save_prompt."""
        from lib.prompt_classifier import classify_prompt

        mock_save = MagicMock()
        message = "ok"
        result = classify_prompt(message)

        if result.should_capture:
            mock_save(content=message, project="test-project", session_id="sess-001")

        mock_save.assert_not_called()

    def test_decision_triggers_save(self):
        """A decision prompt should trigger mem_save_prompt."""
        from lib.prompt_classifier import classify_prompt

        mock_save = MagicMock()
        message = "Let's go with PostgreSQL for the new database"
        result = classify_prompt(message)

        if result.should_capture:
            mock_save(content=message, project="test-project", session_id="sess-001")

        mock_save.assert_called_once()

    def test_status_query_skips_save(self):
        """A status query should NOT trigger mem_save_prompt."""
        from lib.prompt_classifier import classify_prompt

        mock_save = MagicMock()
        message = "What's the status?"
        result = classify_prompt(message)

        if result.should_capture:
            mock_save(content=message, project="test-project", session_id="sess-001")

        mock_save.assert_not_called()

    def test_full_flow_multiple_messages(self):
        """Simulate a sequence of user messages in a session."""
        from lib.prompt_classifier import classify_prompt

        mock_save = MagicMock()
        messages = [
            ("Build the user service", True),
            ("ok", False),
            ("Use PostgreSQL for the database", True),
            ("What's left?", False),
            ("The deadline is Friday", True),
            ("dale", False),
            ("Show me the handler file", False),
            ("Don't use huma, switch to ginext", True),
        ]

        for message, expected_capture in messages:
            result = classify_prompt(message)
            if result.should_capture:
                mock_save(content=message)
            assert result.should_capture == expected_capture, (
                f"Message '{message}' expected capture={expected_capture}, "
                f"got {result.should_capture} (category={result.category})"
            )

        assert mock_save.call_count == 4
