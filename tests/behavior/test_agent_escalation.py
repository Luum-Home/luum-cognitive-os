"""Behavior tests for the agent escalation protocol.

Validates that all components of the escalation protocol exist and are
properly integrated: rule file, preamble updates, KPI additions, and
the EscalationDetector library.

Python 3.9+ compatible.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Rule file exists with escalation types
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Preamble includes escalation section
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# agent-kpis.md includes escalation KPIs
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# EscalationDetector is importable and functional
# ---------------------------------------------------------------------------


class TestDetectorImport:
    """Verify the EscalationDetector library is importable and has expected API."""

    def test_import(self) -> None:
        from lib.escalation_detector import EscalationDetector, EscalationSignal

        assert EscalationDetector is not None
        assert EscalationSignal is not None

    def test_detector_api(self) -> None:
        from lib.escalation_detector import EscalationDetector

        d = EscalationDetector()
        assert hasattr(d, "record_tool_call")
        assert hasattr(d, "record_progress")
        assert hasattr(d, "check_should_escalate")
        assert hasattr(d, "format_escalation")
        assert hasattr(d, "get_escalation_metrics")
        assert hasattr(d, "save_metrics")

    def test_detector_signal_types(self) -> None:
        """Detector should be capable of producing all 5 signal types."""
        from lib.escalation_detector import EscalationDetector

        # These are the documented signal types from the rule.
        expected_types = {
            "loop_detected",
            "no_progress",
            "confidence_drop",
            "error_repeat",
            "timeout_risk",
        }
        # We verify by checking the method names exist for each check.
        d = EscalationDetector()
        for check_name in [
            "_check_loop_detected",
            "_check_no_progress",
            "_check_confidence_drop",
            "_check_error_repeat",
            "_check_timeout_risk",
        ]:
            assert hasattr(d, check_name), f"Detector must have method {check_name}"


# ---------------------------------------------------------------------------
# Format includes ESCALATION: marker
# ---------------------------------------------------------------------------


class TestFormatMarker:
    """Verify the formatted output uses the ESCALATION: marker."""

    def test_format_starts_with_marker(self) -> None:
        from lib.escalation_detector import EscalationDetector, EscalationSignal

        d = EscalationDetector()
        signal = EscalationSignal(
            type="no_progress",
            severity="suggest",
            evidence="15 tool calls without progress",
            tool_calls_so_far=15,
        )
        output = d.format_escalation(signal)
        assert output.startswith("ESCALATION:"), "Formatted output must start with ESCALATION: marker"

    def test_format_parseable(self) -> None:
        """The output should be parseable by splitting on 'ESCALATION:' and reading key-value pairs."""
        from lib.escalation_detector import EscalationDetector, EscalationSignal

        d = EscalationDetector()
        signal = EscalationSignal(
            type="error_repeat",
            severity="recommend",
            evidence="Same error seen 3 times",
            tool_calls_so_far=12,
            diagnosis="Root cause is X",
            recommendation="Try approach Y",
        )
        output = d.format_escalation(signal)
        lines = output.strip().split("\n")
        # First line is marker, rest are key-value.
        assert lines[0] == "ESCALATION:"
        keys_found = set()
        for line in lines[1:]:
            key = line.strip().split(":")[0].strip()
            keys_found.add(key)
        assert "Type" in keys_found
        assert "Severity" in keys_found
        assert "Evidence" in keys_found
        assert "Tool calls" in keys_found
        assert "Diagnosis" in keys_found
        assert "Recommendation" in keys_found
