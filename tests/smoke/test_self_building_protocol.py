"""Tests for the Self-Building Protocol documentation.

Validates that docs/self-building-protocol.md exists and contains
all required sections, tool references, and integration points.
"""

from pathlib import Path

import pytest

PROTOCOL_PATH = Path(__file__).resolve().parents[2] / "docs" / "self-building-protocol.md"


@pytest.fixture
def protocol_content() -> str:
    """Read the protocol document."""
    assert PROTOCOL_PATH.exists(), (
        f"Self-building protocol not found at {PROTOCOL_PATH}. "
        "Run the protocol generation first."
    )
    return PROTOCOL_PATH.read_text(encoding="utf-8")


class TestProtocolExists:
    """Verify the protocol document exists and is non-trivial."""

    def test_protocol_file_exists(self):
        assert PROTOCOL_PATH.exists(), "docs/self-building-protocol.md must exist"

    def test_protocol_is_not_empty(self, protocol_content: str):
        assert len(protocol_content) > 1000, (
            "Protocol document is too short to be meaningful"
        )


class TestSkillRouterReference:
    """Verify skill_router is referenced as a mandatory integration."""

    def test_references_skill_router(self, protocol_content: str):
        assert "skill_router" in protocol_content, (
            "Protocol must reference skill_router for auto-skill selection"
        )

    def test_references_best_match(self, protocol_content: str):
        assert "best_match" in protocol_content, (
            "Protocol must reference skill_router.best_match() method"
        )

    def test_skill_router_is_mandatory(self, protocol_content: str):
        # Check that skill_router appears in a mandatory context
        lower = protocol_content.lower()
        assert "must" in lower and "skill_router" in protocol_content, (
            "skill_router usage must be MANDATORY, not optional"
        )


class TestWorkloadSchedulerReference:
    """Verify WorkloadScheduler is referenced for batch dispatch."""

    def test_references_workload_scheduler(self, protocol_content: str):
        assert "WorkloadScheduler" in protocol_content, (
            "Protocol must reference WorkloadScheduler for batch agent dispatch"
        )

    def test_references_plan_method(self, protocol_content: str):
        # Check for the .plan() method reference
        assert ".plan(" in protocol_content or "plan(tasks)" in protocol_content, (
            "Protocol must reference WorkloadScheduler.plan() method"
        )

    def test_scheduler_threshold(self, protocol_content: str):
        # The scheduler should be required when launching > 3 agents
        assert "> 3" in protocol_content or ">3" in protocol_content, (
            "Protocol must specify the agent count threshold for scheduling"
        )


class TestEscalationReference:
    """Verify escalation detection is referenced."""

    def test_references_escalation_detector(self, protocol_content: str):
        assert "EscalationDetector" in protocol_content or "escalation_detector" in protocol_content, (
            "Protocol must reference EscalationDetector for stuck detection"
        )

    def test_references_stuck_detection(self, protocol_content: str):
        lower = protocol_content.lower()
        assert "stuck" in lower, (
            "Protocol must address the 'stuck' scenario with escalation"
        )

    def test_references_escalation_signals(self, protocol_content: str):
        lower = protocol_content.lower()
        # At least one escalation signal type should be mentioned
        signals = ["loop_detected", "no_progress", "error_repeat", "confidence_drop"]
        found = any(s in lower for s in signals)
        assert found, (
            "Protocol must reference at least one escalation signal type"
        )


class TestReverseEngineerReference:
    """Verify reverse-engineer is referenced for investigation tasks."""

    def test_references_reverse_engineer(self, protocol_content: str):
        assert "reverse-engineer" in protocol_content or "reverse_engineer" in protocol_content, (
            "Protocol must reference /reverse-engineer for dependency investigation"
        )

    def test_reverse_engineer_before_trial_and_error(self, protocol_content: str):
        lower = protocol_content.lower()
        assert "trial-and-error" in lower or "trial and error" in lower, (
            "Protocol must specify reverse-engineer BEFORE trial-and-error"
        )


class TestKPISection:
    """Verify the protocol includes self-usage KPI tracking."""

    def test_has_kpi_section(self, protocol_content: str):
        assert "KPI" in protocol_content, (
            "Protocol must include a KPI section for self-usage measurement"
        )

    def test_has_usage_rate_target(self, protocol_content: str):
        assert "50%" in protocol_content, (
            "Protocol must specify the >50% relevant tool usage target"
        )

    def test_has_alert_threshold(self, protocol_content: str):
        assert "30%" in protocol_content, (
            "Protocol must specify the <30% alert threshold"
        )

    def test_has_going_manual_concept(self, protocol_content: str):
        assert "going manual" in protocol_content.lower(), (
            "Protocol must warn about the orchestrator 'going manual'"
        )


class TestMandatoryProtocolSection:
    """Verify the mandatory protocol section for CLAUDE.md integration."""

    def test_has_mandatory_section(self, protocol_content: str):
        assert "MANDATORY" in protocol_content, (
            "Protocol must have a MANDATORY section for CLAUDE.md integration"
        )

    def test_references_prompt_classifier(self, protocol_content: str):
        assert "prompt_classifier" in protocol_content, (
            "Protocol must reference prompt_classifier for intent capture"
        )

    def test_references_trust_report(self, protocol_content: str):
        lower = protocol_content.lower()
        assert "trust report" in lower or "trust_report" in lower, (
            "Protocol must reference trust report validation"
        )

    def test_references_code_reviewer(self, protocol_content: str):
        assert "code_reviewer" in protocol_content, (
            "Protocol must reference code_reviewer for post-completion review"
        )

    def test_references_cost_dashboard(self, protocol_content: str):
        assert "CostDashboard" in protocol_content or "cost_dashboard" in protocol_content, (
            "Protocol must reference CostDashboard for session cost reporting"
        )

    def test_references_cognitive_load_monitor(self, protocol_content: str):
        assert "CognitiveLoadMonitor" in protocol_content or "cognitive_load_monitor" in protocol_content, (
            "Protocol must reference CognitiveLoadMonitor for quality tracking"
        )


class TestToolIntegrationMap:
    """Verify the protocol maps all major tools to integration points."""

    EXPECTED_TOOLS = [
        "skill_router",
        "prompt_classifier",
        "workload_scheduler",
        "reverse_engineer",
        "escalation_detector",
        "cognitive_load_monitor",
        "trust_report_parser",
        "code_reviewer",
        "cost_dashboard",
        "model_router",
    ]

    @pytest.mark.parametrize("tool_name", EXPECTED_TOOLS)
    def test_tool_referenced(self, protocol_content: str, tool_name: str):
        assert tool_name in protocol_content.lower() or tool_name.replace("_", " ") in protocol_content.lower(), (
            f"Protocol must reference {tool_name} in the tool integration map"
        )


class TestPhaseStructure:
    """Verify the protocol covers all execution phases."""

    EXPECTED_PHASES = [
        "Message Reception",
        "Task Planning",
        "Investigation",
        "Agent Execution",
        "Post-Completion",
        "When Stuck",
    ]

    @pytest.mark.parametrize("phase", EXPECTED_PHASES)
    def test_phase_covered(self, protocol_content: str, phase: str):
        assert phase.lower() in protocol_content.lower(), (
            f"Protocol must cover phase: {phase}"
        )
