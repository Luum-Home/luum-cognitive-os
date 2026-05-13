"""Unit tests for escalation detection wiring.

Covers:
1. EscalationDetector produces an ESCALATION: marker in its output format.
2. Clean agent output does not trigger an escalation signal.
3. agent-preamble.md contains escalation instructions (Severity field, signals, format).
4. EscalationDetector.save_metrics writes to the expected JSONL file.
"""
import json
import re
from pathlib import Path

import pytest

from tests.unit._helpers import assert_preamble_contains_concepts

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PREAMBLE_PATH = Path(__file__).parents[2] / "templates" / "agent-preamble.md"


def _make_detector(**kwargs):
    from lib.escalation_detector import EscalationDetector

    return EscalationDetector(**kwargs)


# ---------------------------------------------------------------------------
# Test 1: ESCALATION: marker is produced in formatted output
# ---------------------------------------------------------------------------


class TestEscalationMarkerInOutput:
    """EscalationDetector.format_escalation returns the ESCALATION: marker."""

    def test_escalation_marker_present_when_loop_detected(self):
        d = _make_detector()
        # Edit the same file 3 times to trigger loop_detected
        for _ in range(3):
            d.record_tool_call("Edit", success=False, target_file="src/foo.go")

        signal = d.check_should_escalate()
        assert signal is not None, "Expected an escalation signal for loop_detected"
        output = d.format_escalation(signal)

        assert output.startswith("ESCALATION:"), (
            f"Output must start with 'ESCALATION:', got: {output[:40]!r}"
        )
        assert "Type:" in output
        assert "Severity:" in output
        assert "Evidence:" in output
        assert "Diagnosis:" in output

    def test_escalation_type_is_loop_detected(self):
        d = _make_detector()
        for _ in range(3):
            d.record_tool_call("Edit", success=False, target_file="lib/handler.py")

        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.type == "loop_detected"

    def test_escalation_severity_field_present(self):
        d = _make_detector()
        for _ in range(3):
            d.record_tool_call("Edit", success=True, target_file="hooks/gate.sh")

        signal = d.check_should_escalate()
        assert signal is not None
        formatted = d.format_escalation(signal)
        # Severity line must be present
        assert re.search(r"Severity:\s+(suggest|recommend|urgent)", formatted), (
            f"Severity field missing or invalid in:\n{formatted}"
        )

    def test_error_repeat_signal_produced(self):
        """Same error twice triggers error_repeat."""
        d = _make_detector(max_same_error=2)
        err = "cannot import name 'foo' from 'bar'"
        d.record_tool_call("Bash", success=False, error_msg=err)
        d.record_tool_call("Bash", success=False, error_msg=err)

        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.type == "error_repeat"

    def test_no_progress_signal_produced(self):
        """11 tool calls without a PROGRESS marker triggers no_progress."""
        d = _make_detector(max_tool_calls_before_check=10)
        for _ in range(11):
            d.record_tool_call("Read", success=True)

        signal = d.check_should_escalate()
        assert signal is not None
        assert signal.type == "no_progress"


# ---------------------------------------------------------------------------
# Test 2: Clean output does not produce an escalation
# ---------------------------------------------------------------------------


class TestNoEscalationInCleanOutput:
    """Successful agent runs should not trigger escalation signals."""

    def test_no_escalation_on_zero_calls(self):
        d = _make_detector()
        signal = d.check_should_escalate()
        assert signal is None

    def test_no_escalation_on_single_file_edit(self):
        d = _make_detector()
        d.record_tool_call("Edit", success=True, target_file="src/main.go")
        signal = d.check_should_escalate()
        assert signal is None

    def test_no_escalation_when_progress_markers_present(self):
        """Progress markers reset the no-progress counter."""
        d = _make_detector(max_tool_calls_before_check=10)
        for i in range(5):
            d.record_tool_call("Read", success=True)
        d.record_progress("step 1/3: read files")
        for i in range(5):
            d.record_tool_call("Edit", success=True, target_file=f"src/file_{i}.go")
        # Still within 10 calls since last marker → no no_progress signal
        signal = d.check_should_escalate()
        # Only loop_detected could fire if same file; with unique files it should be None
        if signal is not None:
            assert signal.type != "no_progress", (
                "no_progress should not fire when progress markers are present"
            )

    def test_no_escalation_on_high_success_rate(self):
        """Mostly-successful runs with varied files do not escalate."""
        d = _make_detector(max_tool_calls_before_check=20)
        for i in range(8):
            d.record_tool_call("Edit", success=True, target_file=f"src/file{i}.go")
            d.record_progress(f"step {i+1}: done")
        signal = d.check_should_escalate()
        assert signal is None


# ---------------------------------------------------------------------------
# Test 3: agent-preamble.md contains escalation instructions
# ---------------------------------------------------------------------------


class TestPreambleContainsEscalationInstructions:
    """The agent-preamble template must teach agents how to escalate."""

    def _load_preamble(self) -> str:
        assert PREAMBLE_PATH.exists(), f"Preamble not found at {PREAMBLE_PATH}"
        return PREAMBLE_PATH.read_text(encoding="utf-8")

    def test_escalation_section_header_present(self):
        """Preamble must document escalation concepts.

        The compact preamble may use the full '## Escalation Protocol' heading
        or inline escalation instructions.  What matters is that the ESCALATION:
        marker is present and that agents know when to escalate.
        """
        text = self._load_preamble()
        assert_preamble_contains_concepts(
            text,
            [
                "## Escalation Protocol",
                "Escalation Protocol",
                "ESCALATION:",
                "escalat",
            ],
        )

    def test_escalation_marker_documented(self):
        text = self._load_preamble()
        assert "ESCALATION:" in text, (
            "Preamble must document the ESCALATION: output marker"
        )

    def test_severity_field_documented(self):
        """Preamble must document severity or reference the escalation rules file.

        The compact preamble delegates detail to rules/agent-escalation.md.
        Acceptable: explicit 'Severity:' field OR a reference to the rules file.
        """
        text = self._load_preamble()
        assert_preamble_contains_concepts(
            text,
            [
                "Severity:",
                "severity",
                "agent-escalation.md",
                "escalation.md",
                "suggest",
                "recommend",
                "urgent",
            ],
        )

    def test_severity_values_documented(self):
        """Preamble or referenced rules must document severity values.

        The compact preamble references rules/agent-escalation.md which
        contains the full severity table.  Acceptable: any one of the
        severity values present OR the rules-file reference present.
        """
        text = self._load_preamble()
        assert_preamble_contains_concepts(
            text,
            [
                "suggest",
                "recommend",
                "urgent",
                "agent-escalation.md",
            ],
        )

    def test_escalation_signal_types_documented(self):
        """Preamble must document the conditions that trigger escalation.

        The compact preamble may not list all signal type names explicitly;
        it may describe them inline (e.g. 'same error 2×' instead of
        'error_repeat') or reference agent-escalation.md.
        """
        text = self._load_preamble()
        # Check that the intent is communicated: same-file/same-error/no-progress
        assert_preamble_contains_concepts(
            text,
            [
                "loop_detected",
                "no_progress",
                "error_repeat",
                "same file",
                "same error",
                "no progress",
                "agent-escalation.md",
            ],
        )

    def test_save_to_engram_instruction_present(self):
        text = self._load_preamble()
        assert "Engram" in text or "engram" in text, (
            "Preamble should instruct agents to save partial progress to Engram"
        )


# ---------------------------------------------------------------------------
# Test 4: Escalation metrics are saved to the JSONL file
# ---------------------------------------------------------------------------


class TestEscalationLoggedToMetrics:
    """EscalationDetector.save_metrics writes a JSONL entry."""

    def test_save_metrics_creates_file(self, tmp_path):
        d = _make_detector()
        # Trigger a signal so _escalations is populated
        for _ in range(3):
            d.record_tool_call("Edit", success=False, target_file="src/broken.py")
        d.check_should_escalate()

        d.save_metrics(str(tmp_path))

        metrics_file = tmp_path / "escalation-events.jsonl"
        assert metrics_file.exists(), "escalation-events.jsonl must be created"

    def test_save_metrics_writes_valid_json(self, tmp_path):
        d = _make_detector()
        for _ in range(3):
            d.record_tool_call("Edit", success=False, target_file="src/broken.py")
        d.check_should_escalate()

        d.save_metrics(str(tmp_path))

        metrics_file = tmp_path / "escalation-events.jsonl"
        lines = metrics_file.read_text().strip().splitlines()
        assert len(lines) >= 1, "At least one line must be written"
        record = json.loads(lines[-1])
        assert "timestamp" in record
        assert "escalation_count" in record
        assert "tool_calls_total" in record

    def test_save_metrics_records_escalation_count(self, tmp_path):
        d = _make_detector()
        for _ in range(3):
            d.record_tool_call("Edit", success=False, target_file="src/broken.py")
        d.check_should_escalate()

        d.save_metrics(str(tmp_path))

        metrics_file = tmp_path / "escalation-events.jsonl"
        record = json.loads(metrics_file.read_text().strip().splitlines()[-1])
        assert record["escalation_count"] >= 1, (
            "escalation_count must be >= 1 after a triggered signal"
        )

    def test_save_metrics_without_escalation_still_writes(self, tmp_path):
        """save_metrics writes even when no escalation was triggered."""
        d = _make_detector()
        d.record_tool_call("Read", success=True)
        # Do NOT call check_should_escalate — no signal in _escalations
        d.save_metrics(str(tmp_path))

        metrics_file = tmp_path / "escalation-events.jsonl"
        assert metrics_file.exists()
        record = json.loads(metrics_file.read_text().strip())
        assert record["escalation_count"] == 0

    def test_save_metrics_appends_on_multiple_calls(self, tmp_path):
        """Multiple save_metrics calls produce multiple lines."""
        for _ in range(2):
            d = _make_detector()
            d.record_tool_call("Read", success=True)
            d.save_metrics(str(tmp_path))

        metrics_file = tmp_path / "escalation-events.jsonl"
        lines = metrics_file.read_text().strip().splitlines()
        assert len(lines) == 2, "Each save_metrics call must append one line"
