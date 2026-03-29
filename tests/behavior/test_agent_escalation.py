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


class TestRuleFile:
    """Verify rules/agent-escalation.md exists with required content."""

    def test_rule_file_exists(self) -> None:
        rule_path = PROJECT_ROOT / "rules" / "agent-escalation.md"
        assert rule_path.exists(), "rules/agent-escalation.md must exist"

    def test_rule_defines_escalation_types(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-escalation.md").read_text()
        for signal_type in [
            "loop_detected",
            "no_progress",
            "confidence_drop",
            "error_repeat",
            "timeout_risk",
        ]:
            assert signal_type in content, f"Rule must define signal type: {signal_type}"

    def test_rule_defines_severity_levels(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-escalation.md").read_text()
        for severity in ["suggest", "recommend", "urgent"]:
            assert severity in content, f"Rule must define severity: {severity}"

    def test_rule_defines_orchestrator_response(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-escalation.md").read_text()
        assert "Orchestrator Response" in content, "Rule must define orchestrator response protocol"

    def test_rule_defines_anti_patterns(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-escalation.md").read_text()
        assert "Anti-Pattern" in content, "Rule must define anti-patterns"

    def test_rule_references_closed_loop(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-escalation.md").read_text()
        assert "closed-loop" in content.lower() or "closed_loop" in content.lower(), (
            "Rule must reference closed-loop-prompts for integration"
        )


# ---------------------------------------------------------------------------
# Preamble includes escalation section
# ---------------------------------------------------------------------------


class TestPreamble:
    """Verify templates/agent-preamble.md includes escalation instructions."""

    def test_preamble_has_escalation_section(self) -> None:
        content = (PROJECT_ROOT / "templates" / "agent-preamble.md").read_text()
        assert "Escalation Protocol" in content, "Preamble must have Escalation Protocol section"

    def test_preamble_has_escalation_marker(self) -> None:
        content = (PROJECT_ROOT / "templates" / "agent-preamble.md").read_text()
        assert "ESCALATION:" in content, "Preamble must show the ESCALATION: marker format"

    def test_preamble_lists_signal_types(self) -> None:
        content = (PROJECT_ROOT / "templates" / "agent-preamble.md").read_text()
        assert "loop_detected" in content, "Preamble must list loop_detected signal"
        assert "no_progress" in content, "Preamble must list no_progress signal"
        assert "error_repeat" in content, "Preamble must list error_repeat signal"

    def test_preamble_mentions_early_escalation(self) -> None:
        content = (PROJECT_ROOT / "templates" / "agent-preamble.md").read_text()
        assert "better to escalate early" in content.lower() or "escalate early" in content.lower(), (
            "Preamble must encourage early escalation over spinning"
        )


# ---------------------------------------------------------------------------
# agent-kpis.md includes escalation KPIs
# ---------------------------------------------------------------------------


class TestKPIs:
    """Verify rules/agent-kpis.md includes escalation KPIs."""

    def test_kpis_has_escalation_section(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-kpis.md").read_text()
        assert "Escalation Health" in content, "agent-kpis.md must have Escalation Health section"

    def test_kpis_has_escalation_rate(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-kpis.md").read_text()
        assert "Escalation Rate" in content, "Must define Escalation Rate KPI"

    def test_kpis_has_resolution_rate(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-kpis.md").read_text()
        assert "Resolution Rate" in content or "Escalation Resolution Rate" in content, (
            "Must define Escalation Resolution Rate KPI"
        )

    def test_kpis_has_time_to_escalate(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-kpis.md").read_text()
        assert "Time-to-Escalate" in content, "Must define Time-to-Escalate KPI"

    def test_kpis_has_false_escalation_rate(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-kpis.md").read_text()
        assert "False Escalation Rate" in content or "False escalation rate" in content, (
            "Must define False Escalation Rate KPI"
        )

    def test_kpis_in_okr_table(self) -> None:
        content = (PROJECT_ROOT / "rules" / "agent-kpis.md").read_text()
        assert "Escalation Health" in content, "Escalation Health must appear in OKR table"


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
