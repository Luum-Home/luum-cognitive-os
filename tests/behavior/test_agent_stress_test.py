"""Behavior tests for the agent stress test system.

Validates that the cognitive load monitoring infrastructure exists and is
properly structured: skill file, rule file, library, and report format.

Related: skills/agent-stress-test/SKILL.md, rules/cognitive-load.md,
         lib/cognitive_load_monitor.py
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Skill file
# ---------------------------------------------------------------------------


class TestSkillFile:
    def test_skill_file_exists(self) -> None:
        skill_path = PROJECT_ROOT / "skills" / "agent-stress-test" / "SKILL.md"
        assert skill_path.exists(), "SKILL.md for agent-stress-test must exist"

    def test_skill_has_audience_os_dev(self) -> None:
        skill_path = PROJECT_ROOT / "skills" / "agent-stress-test" / "SKILL.md"
        content = skill_path.read_text()
        assert "audience: os-dev" in content, "Skill must have audience: os-dev"

    def test_skill_references_four_phases(self) -> None:
        skill_path = PROJECT_ROOT / "skills" / "agent-stress-test" / "SKILL.md"
        content = skill_path.read_text().lower()
        assert "baseline" in content, "Skill must reference baseline phase"
        assert "load" in content, "Skill must reference load phase"
        assert "saturation" in content, "Skill must reference saturation phase"
        assert "recovery" in content, "Skill must reference recovery phase"

    def test_skill_references_phase_numbers(self) -> None:
        skill_path = PROJECT_ROOT / "skills" / "agent-stress-test" / "SKILL.md"
        content = skill_path.read_text()
        assert "Phase 1" in content
        assert "Phase 2" in content
        assert "Phase 3" in content
        assert "Phase 4" in content

    def test_skill_references_cognitive_load_monitor(self) -> None:
        skill_path = PROJECT_ROOT / "skills" / "agent-stress-test" / "SKILL.md"
        content = skill_path.read_text()
        assert "CognitiveLoadMonitor" in content

    def test_skill_has_measurement_protocol(self) -> None:
        skill_path = PROJECT_ROOT / "skills" / "agent-stress-test" / "SKILL.md"
        content = skill_path.read_text().lower()
        assert "preamble compliance" in content
        assert "hallucination" in content
        assert "tool" in content and "success" in content

    def test_skill_has_output_format(self) -> None:
        skill_path = PROJECT_ROOT / "skills" / "agent-stress-test" / "SKILL.md"
        content = skill_path.read_text()
        assert "AGENT STRESS TEST RESULTS" in content

    def test_skill_has_version(self) -> None:
        skill_path = PROJECT_ROOT / "skills" / "agent-stress-test" / "SKILL.md"
        content = skill_path.read_text()
        assert "version:" in content


# ---------------------------------------------------------------------------
# Rule file
# ---------------------------------------------------------------------------


class TestRuleFile:
    def test_rule_file_exists(self) -> None:
        rule_path = PROJECT_ROOT / "rules" / "cognitive-load.md"
        assert rule_path.exists(), "rules/cognitive-load.md must exist"

    def test_rule_has_context_thresholds(self) -> None:
        rule_path = PROJECT_ROOT / "rules" / "cognitive-load.md"
        content = rule_path.read_text()
        assert "50%" in content, "Rule must reference 50% context threshold"
        assert "70%" in content, "Rule must reference 70% context threshold"
        assert "85%" in content, "Rule must reference 85% context threshold"

    def test_rule_lists_degradation_types(self) -> None:
        rule_path = PROJECT_ROOT / "rules" / "cognitive-load.md"
        content = rule_path.read_text()
        assert "context_saturation" in content
        assert "instruction_drift" in content
        assert "hallucination_spike" in content
        assert "tool_confusion" in content
        assert "compound_degradation" in content

    def test_rule_has_contextual_trigger(self) -> None:
        rule_path = PROJECT_ROOT / "rules" / "cognitive-load.md"
        content = rule_path.read_text()
        assert "Contextual Trigger" in content

    def test_rule_references_library(self) -> None:
        rule_path = PROJECT_ROOT / "rules" / "cognitive-load.md"
        content = rule_path.read_text()
        assert "cognitive_load_monitor" in content

    def test_rule_references_wisc(self) -> None:
        rule_path = PROJECT_ROOT / "rules" / "cognitive-load.md"
        content = rule_path.read_text()
        assert "WISC" in content


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------


class TestLibrary:
    def test_cognitive_load_monitor_importable(self) -> None:
        from lib.cognitive_load_monitor import CognitiveLoadMonitor

        m = CognitiveLoadMonitor()
        assert m is not None

    def test_cognitive_snapshot_importable(self) -> None:
        from lib.cognitive_load_monitor import CognitiveSnapshot

        assert CognitiveSnapshot is not None

    def test_monitor_has_required_methods(self) -> None:
        from lib.cognitive_load_monitor import CognitiveLoadMonitor

        m = CognitiveLoadMonitor()
        assert callable(getattr(m, "record_snapshot", None))
        assert callable(getattr(m, "detect_degradation", None))
        assert callable(getattr(m, "cognitive_health_score", None))
        assert callable(getattr(m, "format_health_report", None))
        assert callable(getattr(m, "should_save_and_split", None))
        assert callable(getattr(m, "save_metrics", None))
        assert callable(getattr(m, "estimate_context_usage", None))


# ---------------------------------------------------------------------------
# Health report format
# ---------------------------------------------------------------------------


class TestHealthReportFormat:
    def test_report_has_health_header(self) -> None:
        from lib.cognitive_load_monitor import CognitiveLoadMonitor

        m = CognitiveLoadMonitor()
        for i in range(1, 11):
            m.record_snapshot(
                tool_call_number=i,
                output_length=1000,
                task_complexity="medium",
                preamble_compliance=0.95,
                hallucination_count=0,
                instruction_following=0.95,
                tool_call_success=1.0,
            )
        report = m.format_health_report()
        assert report.startswith("Cognitive Health:")

    def test_report_has_baseline_section(self) -> None:
        from lib.cognitive_load_monitor import CognitiveLoadMonitor

        m = CognitiveLoadMonitor()
        for i in range(1, 11):
            m.record_snapshot(
                tool_call_number=i,
                output_length=1000,
                task_complexity="medium",
                preamble_compliance=0.95,
                hallucination_count=0,
                instruction_following=0.95,
                tool_call_success=1.0,
            )
        report = m.format_health_report()
        assert "Baseline" in report
        assert "Current" in report
        assert "Trend" in report

    def test_report_has_signals_section(self) -> None:
        from lib.cognitive_load_monitor import CognitiveLoadMonitor

        m = CognitiveLoadMonitor()
        for i in range(1, 11):
            m.record_snapshot(
                tool_call_number=i,
                output_length=1000,
                task_complexity="medium",
                preamble_compliance=0.95,
                hallucination_count=0,
                instruction_following=0.95,
                tool_call_success=1.0,
            )
        report = m.format_health_report()
        assert "Signals:" in report

    def test_report_has_context_usage(self) -> None:
        from lib.cognitive_load_monitor import CognitiveLoadMonitor

        m = CognitiveLoadMonitor()
        for i in range(1, 11):
            m.record_snapshot(
                tool_call_number=i,
                output_length=1000,
                task_complexity="medium",
                preamble_compliance=0.95,
                hallucination_count=0,
                instruction_following=0.95,
                tool_call_success=1.0,
            )
        report = m.format_health_report()
        assert "Context usage:" in report
