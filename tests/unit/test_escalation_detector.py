"""Unit tests for lib/escalation_detector.py

Validates escalation detection: loop detection, error repeat, confidence drop,
no-progress detection, timeout risk, formatting, and metrics.

Python 3.9+ compatible.
"""

import json
from pathlib import Path

import pytest

from lib.escalation_detector import (
    DEFAULT_MAX_CALLS_BEFORE_CHECK,
    DEFAULT_MAX_SAME_ERROR,
    SAME_COMMAND_THRESHOLD,
    SAME_FILE_EDIT_THRESHOLD,
    EscalationDetector,
    EscalationSignal,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def detector() -> EscalationDetector:
    """Return a fresh EscalationDetector with defaults."""
    return EscalationDetector()


@pytest.fixture()
def small_budget_detector() -> EscalationDetector:
    """Return a detector with a small tool call budget for timeout_risk tests."""
    return EscalationDetector(tool_call_budget=10)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _record_healthy_calls(d: EscalationDetector, count: int) -> None:
    """Record N successful tool calls with progress markers every 5 calls."""
    for i in range(count):
        d.record_tool_call("Read", success=True)
        if (i + 1) % 5 == 0:
            d.record_progress(f"step {(i + 1) // 5}")


def _record_failing_calls(d: EscalationDetector, count: int, error: str = "some error") -> None:
    """Record N failing tool calls."""
    for _ in range(count):
        d.record_tool_call("Bash", success=False, error_msg=error)


# ---------------------------------------------------------------------------
# Tests: No escalation on healthy flow
# ---------------------------------------------------------------------------


class TestNoEscalationWhenHealthy:
    """Verify no signals fire during normal productive work."""

    def test_empty_detector(self, detector: EscalationDetector) -> None:
        """No tool calls -> no escalation."""
        assert detector.check_should_escalate() is None

    def test_few_successful_calls(self, detector: EscalationDetector) -> None:
        """A handful of successful calls should not trigger anything."""
        for i in range(5):
            detector.record_tool_call("Read", success=True)
        detector.record_progress("step 1")
        assert detector.check_should_escalate() is None

    def test_healthy_flow_with_progress(self, detector: EscalationDetector) -> None:
        """Normal flow with regular progress markers stays clean."""
        _record_healthy_calls(detector, 20)
        assert detector.check_should_escalate() is None

    def test_different_files_edited(self, detector: EscalationDetector) -> None:
        """Editing different files does not trigger loop detection."""
        for i in range(5):
            detector.record_tool_call("Edit", success=True, target_file=f"file_{i}.py")
        assert detector.check_should_escalate() is None

    def test_occasional_failure_is_fine(self, detector: EscalationDetector) -> None:
        """One failure among many successes is normal."""
        for i in range(8):
            detector.record_tool_call("Bash", success=True)
            detector.record_progress(f"step {i}")
        detector.record_tool_call("Bash", success=False, error_msg="oops")
        detector.record_tool_call("Bash", success=True)
        assert detector.check_should_escalate() is None


# ---------------------------------------------------------------------------
# Tests: loop_detected -- same file edited multiple times
# ---------------------------------------------------------------------------


class TestLoopDetectedFile:
    """Same file edited SAME_FILE_EDIT_THRESHOLD+ times triggers loop_detected."""

    def test_triggers_at_threshold(self, detector: EscalationDetector) -> None:
        for _ in range(SAME_FILE_EDIT_THRESHOLD):
            detector.record_tool_call("Edit", success=False, target_file="src/foo.py")
        signal = detector.check_should_escalate()
        assert signal is not None
        assert signal.type == "loop_detected"
        assert "src/foo.py" in signal.evidence
        assert f"edited {SAME_FILE_EDIT_THRESHOLD} times" in signal.evidence

    def test_does_not_trigger_below_threshold(self, detector: EscalationDetector) -> None:
        for _ in range(SAME_FILE_EDIT_THRESHOLD - 1):
            detector.record_tool_call("Edit", success=False, target_file="src/foo.py")
        assert detector.check_should_escalate() is None

    def test_severity_increases_with_count(self, detector: EscalationDetector) -> None:
        """More edits -> higher severity."""
        # At threshold -> suggest
        for _ in range(SAME_FILE_EDIT_THRESHOLD):
            detector.record_tool_call("Edit", success=False, target_file="src/bar.py")
        signal = detector.check_should_escalate()
        assert signal is not None
        assert signal.severity == "suggest"

        # At 2x threshold -> recommend
        d2 = EscalationDetector()
        for _ in range(SAME_FILE_EDIT_THRESHOLD * 2):
            d2.record_tool_call("Edit", success=False, target_file="src/bar.py")
        signal2 = d2.check_should_escalate()
        assert signal2 is not None
        assert signal2.severity == "recommend"


# ---------------------------------------------------------------------------
# Tests: loop_detected -- same command run multiple times
# ---------------------------------------------------------------------------


class TestLoopDetectedCommand:
    """Same command run SAME_COMMAND_THRESHOLD+ times triggers loop_detected."""

    def test_triggers_at_threshold(self, detector: EscalationDetector) -> None:
        cmd = "python -m pytest tests/unit/test_foo.py"
        for _ in range(SAME_COMMAND_THRESHOLD):
            detector.record_tool_call("Bash", success=False, command=cmd)
        signal = detector.check_should_escalate()
        assert signal is not None
        assert signal.type == "loop_detected"
        assert cmd[:50] in signal.evidence

    def test_different_commands_no_trigger(self, detector: EscalationDetector) -> None:
        for i in range(5):
            detector.record_tool_call("Bash", success=True, command=f"cmd_{i}")
        assert detector.check_should_escalate() is None


# ---------------------------------------------------------------------------
# Tests: no_progress
# ---------------------------------------------------------------------------


class TestNoProgress:
    """More than max_tool_calls_before_check calls without PROGRESS triggers no_progress."""

    def test_triggers_after_threshold(self, detector: EscalationDetector) -> None:
        for _ in range(DEFAULT_MAX_CALLS_BEFORE_CHECK + 1):
            detector.record_tool_call("Read", success=True)
        signal = detector.check_should_escalate()
        assert signal is not None
        assert signal.type == "no_progress"

    def test_does_not_trigger_at_threshold(self, detector: EscalationDetector) -> None:
        for _ in range(DEFAULT_MAX_CALLS_BEFORE_CHECK):
            detector.record_tool_call("Read", success=True)
        assert detector.check_should_escalate() is None

    def test_progress_resets_counter(self, detector: EscalationDetector) -> None:
        """A PROGRESS marker resets the no-progress counter."""
        for _ in range(DEFAULT_MAX_CALLS_BEFORE_CHECK - 1):
            detector.record_tool_call("Read", success=True)
        # Just before threshold, record progress.
        detector.record_progress("step 1: done")
        # Now do a few more calls -- should not trigger.
        for _ in range(5):
            detector.record_tool_call("Read", success=True)
        assert detector.check_should_escalate() is None

    def test_severity_escalates_with_duration(self) -> None:
        """Longer stuck duration -> higher severity."""
        d = EscalationDetector(max_tool_calls_before_check=5)
        # 16 calls without progress -> recommend (>15 threshold).
        for _ in range(16):
            d.record_tool_call("Read", success=True)
        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.severity == "recommend"


# ---------------------------------------------------------------------------
# Tests: confidence_drop
# ---------------------------------------------------------------------------


class TestConfidenceDrop:
    """Error rate >50% in last CONFIDENCE_WINDOW calls triggers confidence_drop."""

    def test_triggers_on_high_error_rate(self, detector: EscalationDetector) -> None:
        # Need at least CONFIDENCE_WINDOW calls.
        # Record progress first to avoid no_progress.
        detector.record_progress("starting")
        # Record 3 failures and 2 successes in CONFIDENCE_WINDOW=5 calls -> 60% error.
        detector.record_tool_call("Bash", success=False, error_msg="err1")
        detector.record_tool_call("Bash", success=True)
        detector.record_tool_call("Bash", success=False, error_msg="err2")
        detector.record_tool_call("Bash", success=False, error_msg="err3")
        detector.record_tool_call("Bash", success=True)
        signal = detector.check_should_escalate()
        assert signal is not None
        assert signal.type == "confidence_drop"

    def test_does_not_trigger_on_low_error_rate(self, detector: EscalationDetector) -> None:
        detector.record_progress("starting")
        detector.record_tool_call("Bash", success=True)
        detector.record_tool_call("Bash", success=True)
        detector.record_tool_call("Bash", success=True)
        detector.record_tool_call("Bash", success=True)
        detector.record_tool_call("Bash", success=False, error_msg="one error")
        # 1/5 = 20% error rate -> should not trigger.
        assert detector.check_should_escalate() is None

    def test_not_enough_calls(self, detector: EscalationDetector) -> None:
        """Fewer than CONFIDENCE_WINDOW calls -> no confidence check."""
        detector.record_tool_call("Bash", success=False, error_msg="err1")
        detector.record_tool_call("Bash", success=False, error_msg="err2")
        assert detector.check_should_escalate() is None


# ---------------------------------------------------------------------------
# Tests: error_repeat
# ---------------------------------------------------------------------------


class TestErrorRepeat:
    """Same error message seen max_same_error+ times triggers error_repeat."""

    def test_triggers_on_repeated_error(self, detector: EscalationDetector) -> None:
        detector.record_progress("starting")
        error = "ModuleNotFoundError: No module named 'foo'"
        for _ in range(DEFAULT_MAX_SAME_ERROR):
            detector.record_tool_call("Bash", success=False, error_msg=error)
        signal = detector.check_should_escalate()
        assert signal is not None
        assert signal.type == "error_repeat"
        assert "ModuleNotFoundError" in signal.evidence

    def test_different_errors_no_trigger(self, detector: EscalationDetector) -> None:
        detector.record_progress("starting")
        detector.record_tool_call("Bash", success=False, error_msg="error A")
        detector.record_tool_call("Bash", success=False, error_msg="error B")
        detector.record_tool_call("Bash", success=False, error_msg="error C")
        # All different -> no repeat signal (may trigger confidence_drop though).
        signal = detector.check_should_escalate()
        if signal:
            assert signal.type != "error_repeat"

    def test_severity_increases_at_3_repeats(self) -> None:
        """3+ repeats of the same error -> recommend severity."""
        d = EscalationDetector()
        d.record_progress("starting")
        error = "ConnectionRefusedError"
        for _ in range(3):
            d.record_tool_call("Bash", success=False, error_msg=error)
        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.type == "error_repeat"
        assert signal.severity == "recommend"


# ---------------------------------------------------------------------------
# Tests: timeout_risk
# ---------------------------------------------------------------------------


class TestTimeoutRisk:
    """Budget usage >80% triggers timeout_risk."""

    def test_triggers_at_80_percent(self, small_budget_detector: EscalationDetector) -> None:
        # Budget=10, need >8 calls.
        for _ in range(9):
            small_budget_detector.record_tool_call("Read", success=True)
            small_budget_detector.record_progress(f"step")
        signal = small_budget_detector.check_should_escalate()
        assert signal is not None
        assert signal.type == "timeout_risk"

    def test_does_not_trigger_below_threshold(self, small_budget_detector: EscalationDetector) -> None:
        # Budget=10, 7 calls = 70%.
        for _ in range(7):
            small_budget_detector.record_tool_call("Read", success=True)
            small_budget_detector.record_progress("step")
        assert small_budget_detector.check_should_escalate() is None

    def test_severity_increases_near_limit(self) -> None:
        """Usage >95% -> urgent."""
        d = EscalationDetector(tool_call_budget=10)
        for i in range(10):
            d.record_tool_call("Read", success=True)
            d.record_progress(f"step {i}")
        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.severity == "urgent"


# ---------------------------------------------------------------------------
# Tests: format_escalation
# ---------------------------------------------------------------------------


class TestFormatEscalation:
    """Verify format_escalation output has all required fields."""

    def test_format_has_required_fields(self, detector: EscalationDetector) -> None:
        signal = EscalationSignal(
            type="loop_detected",
            severity="recommend",
            evidence="File foo.py edited 4 times",
            tool_calls_so_far=15,
            diagnosis="Fix not converging",
            recommendation="Try different approach",
        )
        output = detector.format_escalation(signal)
        assert "ESCALATION:" in output
        assert "Type: loop_detected" in output
        assert "Severity: recommend" in output
        assert "Evidence: File foo.py edited 4 times" in output
        assert "Tool calls: 15" in output
        assert "Diagnosis: Fix not converging" in output
        assert "Recommendation: Try different approach" in output

    def test_format_without_optional_fields(self, detector: EscalationDetector) -> None:
        signal = EscalationSignal(
            type="no_progress",
            severity="suggest",
            evidence="12 calls without progress",
            tool_calls_so_far=12,
        )
        output = detector.format_escalation(signal)
        assert "ESCALATION:" in output
        assert "Type: no_progress" in output
        # Diagnosis and Recommendation should not appear when empty.
        assert "Diagnosis:" not in output
        assert "Recommendation:" not in output


# ---------------------------------------------------------------------------
# Tests: get_escalation_metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    """Verify get_escalation_metrics returns correct counts."""

    def test_initial_metrics(self, detector: EscalationDetector) -> None:
        metrics = detector.get_escalation_metrics()
        assert metrics["escalation_count"] == 0
        assert metrics["tool_calls_total"] == 0
        assert metrics["progress_markers"] == 0
        assert metrics["error_rate"] == 0.0
        assert metrics["error_count"] == 0
        assert metrics["files_modified_unique"] == 0
        assert metrics["stuck_duration"] == 0
        assert metrics["escalation_types"] == {}

    def test_metrics_after_activity(self, detector: EscalationDetector) -> None:
        detector.record_tool_call("Edit", success=True, target_file="a.py")
        detector.record_tool_call("Edit", success=True, target_file="b.py")
        detector.record_tool_call("Bash", success=False, error_msg="fail")
        detector.record_progress("done step 1")

        metrics = detector.get_escalation_metrics()
        assert metrics["tool_calls_total"] == 3
        assert metrics["progress_markers"] == 1
        assert metrics["error_count"] == 1
        assert metrics["error_rate"] == round(1 / 3, 3)
        assert metrics["files_modified_unique"] == 2
        assert metrics["stuck_duration"] == 0  # progress was recorded at call 3

    def test_metrics_after_escalation(self, detector: EscalationDetector) -> None:
        for _ in range(SAME_FILE_EDIT_THRESHOLD):
            detector.record_tool_call("Edit", success=False, target_file="x.py")
        signal = detector.check_should_escalate()
        assert signal is not None

        metrics = detector.get_escalation_metrics()
        assert metrics["escalation_count"] == 1
        assert "loop_detected" in metrics["escalation_types"]

    def test_save_metrics(self, detector: EscalationDetector, tmp_path: Path) -> None:
        detector.record_tool_call("Read", success=True)
        detector.save_metrics(str(tmp_path))

        metrics_file = tmp_path / "escalation-events.jsonl"
        assert metrics_file.exists()
        data = json.loads(metrics_file.read_text().strip())
        assert "timestamp" in data
        assert data["tool_calls_total"] == 1


# ---------------------------------------------------------------------------
# Tests: severity levels
# ---------------------------------------------------------------------------


class TestSeverityLevels:
    """Verify suggest/recommend/urgent are assigned correctly."""

    def test_suggest_is_default(self) -> None:
        """At the exact threshold, severity should be suggest."""
        d = EscalationDetector()
        for _ in range(SAME_FILE_EDIT_THRESHOLD):
            d.record_tool_call("Edit", success=False, target_file="f.py")
        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.severity == "suggest"

    def test_recommend_at_double_threshold(self) -> None:
        d = EscalationDetector()
        for _ in range(SAME_FILE_EDIT_THRESHOLD * 2):
            d.record_tool_call("Edit", success=False, target_file="f.py")
        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.severity == "recommend"

    def test_urgent_at_triple_threshold(self) -> None:
        d = EscalationDetector()
        for _ in range(SAME_FILE_EDIT_THRESHOLD * 3):
            d.record_tool_call("Edit", success=False, target_file="f.py")
        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.severity == "urgent"


# ---------------------------------------------------------------------------
# Tests: EscalationSignal dataclass
# ---------------------------------------------------------------------------


class TestEscalationSignal:
    """Verify the EscalationSignal data class."""

    def test_to_dict(self) -> None:
        sig = EscalationSignal(
            type="error_repeat",
            severity="suggest",
            evidence="Same error 2x",
            tool_calls_so_far=10,
            diagnosis="root cause",
            recommendation="try X",
        )
        d = sig.to_dict()
        assert d["type"] == "error_repeat"
        assert d["severity"] == "suggest"
        assert d["evidence"] == "Same error 2x"
        assert d["tool_calls_so_far"] == 10
        assert d["diagnosis"] == "root cause"
        assert d["recommendation"] == "try X"

    def test_default_optional_fields(self) -> None:
        sig = EscalationSignal(
            type="no_progress",
            severity="suggest",
            evidence="15 calls",
            tool_calls_so_far=15,
        )
        assert sig.diagnosis == ""
        assert sig.recommendation == ""
