"""Unit tests for lib/prompt_classifier.py

Validates prompt classification across categories, capture decisions,
confidence scoring, bilingual support, and edge cases.
"""

import pytest

from lib.prompt_classifier import (
    ClassificationResult,
    PromptCategory,
    classify_prompt,
    should_capture_prompt,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Task Request classification
# ---------------------------------------------------------------------------


class TestTaskRequest:
    """Prompts that contain action verbs targeting work."""

    def test_build_command(self):
        result = classify_prompt("Build the auth module for the payments service")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True
        assert result.confidence >= 0.5

    def test_fix_command(self):
        result = classify_prompt("Fix the broken test in user_handler_test.go")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True

    def test_add_command(self):
        result = classify_prompt("Add JWT support to all endpoints")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True

    def test_implement_command(self):
        result = classify_prompt("Implement the GetUserByID use case")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True

    def test_create_command(self):
        result = classify_prompt("Create a new service for notifications")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True

    def test_refactor_command(self):
        result = classify_prompt("Refactor the payment handler to use clean architecture")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True

    def test_sdd_command(self):
        result = classify_prompt("/sdd-new add-biometrics")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True
        assert result.confidence >= 0.8

    def test_polite_request(self):
        result = classify_prompt("Can you implement the login endpoint?")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True

    def test_build_request(self):
        result = classify_prompt("Build the authentication module")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True

    def test_fix_request(self):
        result = classify_prompt("Fix the broken test")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True

    def test_english_build(self):
        result = classify_prompt("Build the users endpoint")
        assert result.category == PromptCategory.TASK_REQUEST
        assert result.should_capture is True


# ---------------------------------------------------------------------------
# Decision classification
# ---------------------------------------------------------------------------


class TestDecision:
    """Prompts that contain decision language."""

    def test_use_decision(self):
        result = classify_prompt("Use PostgreSQL for the new service")
        assert result.category == PromptCategory.DECISION
        assert result.should_capture is True

    def test_go_with_decision(self):
        result = classify_prompt("Let's go with REST instead of GraphQL")
        assert result.category == PromptCategory.DECISION
        assert result.should_capture is True

    def test_prefer_decision(self):
        result = classify_prompt("I prefer approach A over approach B")
        assert result.category == PromptCategory.DECISION
        assert result.should_capture is True

    def test_switch_to_decision(self):
        result = classify_prompt("Switch to the repository pattern for data access")
        assert result.category == PromptCategory.DECISION
        assert result.should_capture is True

    def test_use_decision_request(self):
        result = classify_prompt("Use PostgreSQL for the new service")
        assert result.category == PromptCategory.DECISION
        assert result.should_capture is True

    def test_go_with_approach(self):
        result = classify_prompt("Go with approach A")
        assert result.category == PromptCategory.DECISION
        assert result.should_capture is True


# ---------------------------------------------------------------------------
# Feedback classification
# ---------------------------------------------------------------------------


class TestFeedback:
    """Prompts that contain correction or praise."""

    def test_negative_dont(self):
        result = classify_prompt("Don't use sed for documentation files")
        assert result.category == PromptCategory.FEEDBACK
        assert result.should_capture is True

    def test_negative_wrong(self):
        result = classify_prompt("That's wrong, revert it")
        assert result.category == PromptCategory.FEEDBACK
        assert result.should_capture is True

    def test_negative_stop(self):
        result = classify_prompt("Stop adding unnecessary abstractions")
        assert result.category == PromptCategory.FEEDBACK
        assert result.should_capture is True

    def test_positive_keep(self):
        result = classify_prompt("Keep doing that approach, it works well")
        assert result.category == PromptCategory.FEEDBACK
        assert result.should_capture is True

    def test_correction(self):
        result = classify_prompt("Actually, I meant the other handler")
        assert result.category == PromptCategory.FEEDBACK
        assert result.should_capture is True

    def test_spanish_no_hagas(self):
        result = classify_prompt("No hagas eso, esta mal")
        assert result.category == PromptCategory.FEEDBACK
        assert result.should_capture is True

    def test_spanish_perfecto(self):
        result = classify_prompt("Perfecto, segui asi con ese enfoque")
        assert result.category == PromptCategory.FEEDBACK
        assert result.should_capture is True


# ---------------------------------------------------------------------------
# Context classification
# ---------------------------------------------------------------------------


class TestContext:
    """Prompts that provide project context or background."""

    def test_working_on(self):
        result = classify_prompt("We're working on the payments service migration")
        assert result.category == PromptCategory.CONTEXT
        assert result.should_capture is True

    def test_goal(self):
        result = classify_prompt("The goal is to reduce latency below 200ms")
        assert result.category == PromptCategory.CONTEXT
        assert result.should_capture is True

    def test_deadline(self):
        result = classify_prompt("The deadline for this feature is next Friday")
        assert result.category == PromptCategory.CONTEXT
        assert result.should_capture is True

    def test_fyi(self):
        result = classify_prompt("FYI the database was migrated yesterday")
        assert result.category == PromptCategory.CONTEXT
        assert result.should_capture is True

    def test_spanish_trabajando(self):
        result = classify_prompt("Estamos trabajando en el servicio de pagos")
        assert result.category == PromptCategory.CONTEXT
        assert result.should_capture is True


# ---------------------------------------------------------------------------
# Status Query classification (should NOT capture)
# ---------------------------------------------------------------------------


class TestStatusQuery:
    """Prompts that ask about current state -- should not be captured."""

    def test_whats_left(self):
        result = classify_prompt("What's left to do?")
        assert result.should_capture is False

    def test_status(self):
        result = classify_prompt("What's the status?")
        assert result.should_capture is False

    def test_progress(self):
        result = classify_prompt("How's the progress on the migration?")
        assert result.should_capture is False

    def test_spanish_que_falta(self):
        result = classify_prompt("Que falta?")
        assert result.should_capture is False

    def test_spanish_como_va(self):
        result = classify_prompt("Como va el progreso?")
        assert result.should_capture is False


# ---------------------------------------------------------------------------
# Navigation classification (should NOT capture)
# ---------------------------------------------------------------------------


class TestNavigation:
    """Prompts that reference file browsing -- should not be captured."""

    def test_show_me(self):
        result = classify_prompt("Show me the handler.go file")
        assert result.should_capture is False

    def test_read_file(self):
        result = classify_prompt("Read file internal/users/handler.go")
        assert result.should_capture is False

    def test_check_logs(self):
        result = classify_prompt("Check the error logs")
        assert result.should_capture is False


# ---------------------------------------------------------------------------
# Acknowledgment classification (should NOT capture)
# ---------------------------------------------------------------------------


class TestAcknowledgment:
    """Short affirmations -- should not be captured."""

    def test_ok(self):
        result = classify_prompt("ok")
        assert result.category == PromptCategory.ACKNOWLEDGMENT
        assert result.should_capture is False

    def test_yes(self):
        result = classify_prompt("yes")
        assert result.should_capture is False

    def test_sure(self):
        result = classify_prompt("sure")
        assert result.should_capture is False

    def test_got_it(self):
        result = classify_prompt("got it")
        assert result.should_capture is False

    def test_dale(self):
        result = classify_prompt("dale")
        assert result.category == PromptCategory.ACKNOWLEDGMENT
        assert result.should_capture is False

    def test_si(self):
        result = classify_prompt("si")
        assert result.should_capture is False

    def test_go_ahead(self):
        result = classify_prompt("go ahead")
        assert result.should_capture is False

    def test_listo(self):
        result = classify_prompt("listo")
        assert result.should_capture is False

    def test_bueno(self):
        result = classify_prompt("bueno")
        assert result.should_capture is False

    def test_continue(self):
        result = classify_prompt("continue")
        assert result.should_capture is False


# ---------------------------------------------------------------------------
# Mixed prompts (task + context, decision + task, etc.)
# ---------------------------------------------------------------------------


class TestMixedPrompts:
    """Prompts that combine multiple categories -- should capture the dominant one."""

    def test_task_with_context(self):
        result = classify_prompt(
            "We're working on payments. Build the checkout endpoint."
        )
        assert result.should_capture is True
        # Either task_request or context is fine; both are captured
        assert result.category in (PromptCategory.TASK_REQUEST, PromptCategory.CONTEXT)

    def test_decision_with_task(self):
        result = classify_prompt("Use ginext and implement the new controller")
        assert result.should_capture is True

    def test_feedback_with_task(self):
        result = classify_prompt("Don't use huma, refactor to use ginext instead")
        assert result.should_capture is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_empty_string(self):
        result = classify_prompt("")
        assert result.category == PromptCategory.UNKNOWN
        assert result.should_capture is False
        assert result.confidence == 0.0

    def test_whitespace_only(self):
        result = classify_prompt("   ")
        assert result.category == PromptCategory.UNKNOWN
        assert result.should_capture is False

    def test_long_unknown_message(self):
        # Long messages with no pattern matches default to context (captured)
        long_text = "Here is some information about the system that does not match any particular pattern but is quite long and contains many words that provide useful background"
        result = classify_prompt(long_text)
        assert result.should_capture is True
        assert result.confidence > 0.0

    def test_single_word_unknown(self):
        result = classify_prompt("banana")
        assert result.should_capture is False

    def test_classification_result_str(self):
        result = ClassificationResult(
            category=PromptCategory.TASK_REQUEST,
            should_capture=True,
            confidence=0.75,
        )
        s = str(result)
        assert "task_request" in s
        assert "0.75" in s


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


class TestShouldCapturePrompt:
    """Tests for the convenience wrapper."""

    def test_captures_task(self):
        assert should_capture_prompt("Build the auth module") is True

    def test_skips_ack(self):
        assert should_capture_prompt("ok") is False

    def test_skips_empty(self):
        assert should_capture_prompt("") is False

    def test_captures_decision(self):
        assert should_capture_prompt("Let's go with approach B") is True
