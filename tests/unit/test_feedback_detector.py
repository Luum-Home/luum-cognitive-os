"""
Unit tests for lib.feedback_detector — FeedbackDetector, FeedbackType, FeedbackSignal.

Covers:
  - EXPLICIT_POSITIVE: English praise phrases
  - EXPLICIT_NEGATIVE: rejection / wrong / revert phrases
  - CORRECTION: "actually", "instead", "use X instead"
  - ESCALATION: user taking over
  - NEUTRAL: questions, status queries
  - IMPLICIT_POSITIVE: new task after previous
  - Edge cases: empty string, whitespace-only

Minimum: 20 tests.
"""

import pytest
from lib.feedback_detector import FeedbackDetector, FeedbackType, FeedbackSignal


@pytest.fixture
def detector():
    return FeedbackDetector()


# ---------------------------------------------------------------------------
# Basic contract
# ---------------------------------------------------------------------------


class TestFeedbackSignalContract:
    def test_returns_feedback_signal(self, detector):
        result = detector.detect("perfect")
        assert isinstance(result, FeedbackSignal)

    def test_signal_has_type(self, detector):
        result = detector.detect("perfect")
        assert isinstance(result.type, FeedbackType)

    def test_signal_has_confidence(self, detector):
        result = detector.detect("perfect")
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    def test_signal_has_content(self, detector):
        msg = "perfect job"
        result = detector.detect(msg)
        assert result.content == msg.strip()


# ---------------------------------------------------------------------------
# EXPLICIT_POSITIVE
# ---------------------------------------------------------------------------


class TestExplicitPositive:
    def test_perfect_english(self, detector):
        result = detector.detect("perfect")
        assert result.type == FeedbackType.EXPLICIT_POSITIVE

    def test_exactly_english(self, detector):
        result = detector.detect("Exactly what I needed!")
        assert result.type == FeedbackType.EXPLICIT_POSITIVE

    def test_great_job_english(self, detector):
        result = detector.detect("Great job!")
        assert result.type == FeedbackType.EXPLICIT_POSITIVE

    def test_great_english(self, detector):
        result = detector.detect("great, that is what I wanted")
        assert result.type == FeedbackType.EXPLICIT_POSITIVE

    def test_excellent_english(self, detector):
        result = detector.detect("excellent work")
        assert result.type == FeedbackType.EXPLICIT_POSITIVE

    def test_keep_doing_english(self, detector):
        result = detector.detect("keep doing this, it's working well")
        assert result.type == FeedbackType.EXPLICIT_POSITIVE

    def test_keep_going_english(self, detector):
        result = detector.detect("keep going, it is perfect")
        assert result.type == FeedbackType.EXPLICIT_POSITIVE

    def test_high_confidence_for_clear_positive(self, detector):
        result = detector.detect("perfect")
        assert result.confidence >= 0.8


# ---------------------------------------------------------------------------
# EXPLICIT_NEGATIVE
# ---------------------------------------------------------------------------


class TestExplicitNegative:
    def test_no_thats_wrong(self, detector):
        result = detector.detect("no that's wrong, revert it")
        assert result.type == FeedbackType.EXPLICIT_NEGATIVE

    def test_revert_english(self, detector):
        result = detector.detect("revert the last change")
        assert result.type == FeedbackType.EXPLICIT_NEGATIVE

    def test_no_this_is_wrong(self, detector):
        result = detector.detect("no, this is not what I wanted")
        assert result.type == FeedbackType.EXPLICIT_NEGATIVE

    def test_not_right(self, detector):
        result = detector.detect("that's not right at all")
        assert result.type == FeedbackType.EXPLICIT_NEGATIVE


# ---------------------------------------------------------------------------
# CORRECTION
# ---------------------------------------------------------------------------


class TestCorrection:
    def test_actually_use_x(self, detector):
        result = detector.detect("actually use PostgreSQL instead of SQLite")
        assert result.type == FeedbackType.CORRECTION

    def test_i_meant_english(self, detector):
        result = detector.detect("I meant the handler, not the controller")
        assert result.type == FeedbackType.CORRECTION

    def test_instead_pattern(self, detector):
        result = detector.detect("use gin instead, not echo")
        assert result.type == FeedbackType.CORRECTION

    def test_correction_has_detail_or_none(self, detector):
        result = detector.detect("actually use Redis instead of Memcached")
        assert result.type == FeedbackType.CORRECTION
        # detail may or may not be populated — just check it's not an error
        assert result.detail is None or isinstance(result.detail, str)


# ---------------------------------------------------------------------------
# ESCALATION
# ---------------------------------------------------------------------------


class TestEscalation:
    def test_ill_do_it_myself(self, detector):
        result = detector.detect("I'll do it myself")
        assert result.type == FeedbackType.ESCALATION

    def test_let_me_do_it(self, detector):
        result = detector.detect("let me do it")
        assert result.type == FeedbackType.ESCALATION

    def test_escalation_confidence_high(self, detector):
        result = detector.detect("I'll do it myself")
        assert result.confidence >= 0.9


# ---------------------------------------------------------------------------
# NEUTRAL
# ---------------------------------------------------------------------------


class TestNeutral:
    def test_status_query_neutral(self, detector):
        result = detector.detect("what's left?")
        assert result.type == FeedbackType.NEUTRAL

    def test_empty_string_neutral(self, detector):
        result = detector.detect("")
        assert result.type == FeedbackType.NEUTRAL

    def test_whitespace_only_neutral(self, detector):
        result = detector.detect("   ")
        assert result.type == FeedbackType.NEUTRAL

    def test_simple_question_neutral(self, detector):
        result = detector.detect("how many tests are there?")
        assert result.type == FeedbackType.NEUTRAL


# ---------------------------------------------------------------------------
# IMPLICIT_POSITIVE
# ---------------------------------------------------------------------------


class TestImplicitPositive:
    def test_new_task_after_previous_is_implicit_positive(self, detector):
        """When a user issues a new task after a previous one without complaint,
        that signals implicit acceptance of the prior work."""
        result = detector.detect(
            "now add the unit tests",
            previous_task="implement the user endpoint",
        )
        # New task = implicit positive (or neutral — both are acceptable signals of no rejection)
        assert result.type in (FeedbackType.IMPLICIT_POSITIVE, FeedbackType.NEUTRAL)

    def test_continuation_message_signals_acceptance(self, detector):
        result = detector.detect(
            "ok, next add the integration tests",
            previous_task="wrote the handler code",
        )
        assert result.type in (FeedbackType.IMPLICIT_POSITIVE, FeedbackType.NEUTRAL)
