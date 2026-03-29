"""Behavior tests for Agent Teams documentation completeness.

Validates that docs/agent-teams.md exists, contains required sections,
and covers all critical integration points between COS and Agent Teams.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOC_PATH = PROJECT_ROOT / "docs" / "agent-teams.md"


def _read_doc() -> str:
    """Read the agent-teams documentation content."""
    assert DOC_PATH.exists(), f"Agent Teams doc not found at {DOC_PATH}"
    return DOC_PATH.read_text()


class TestDocExists:
    """docs/agent-teams.md must exist and be substantial."""

    def test_doc_exists(self):
        """Agent Teams documentation file should exist."""
        assert DOC_PATH.exists(), "docs/agent-teams.md is missing"

    def test_doc_not_empty(self):
        """Documentation should contain substantial content."""
        content = _read_doc()
        assert len(content) > 2000, "Agent Teams doc is too short to be useful"


class TestAgentTeamsEnableConfig:
    """Documentation must reference how to enable Agent Teams."""

    def test_env_var_mentioned(self):
        """Should reference the experimental env var."""
        content = _read_doc()
        assert "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" in content, (
            "Missing CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS env var reference"
        )

    def test_settings_json_config(self):
        """Should show settings.json configuration."""
        content = _read_doc()
        assert "settings.json" in content, (
            "Missing settings.json configuration example"
        )

    def test_enable_value(self):
        """Should specify the enable value is '1'."""
        content = _read_doc()
        assert '"1"' in content, (
            "Missing enable value '1' for the env var"
        )


class TestComparisonTable:
    """Documentation must have a comparison table between subagents and teams."""

    def test_comparison_section_exists(self):
        """Should have a subagents vs agent teams section."""
        content = _read_doc()
        assert "Subagent" in content and "Agent Teams" in content, (
            "Missing comparison between Subagents and Agent Teams"
        )

    def test_comparison_has_table(self):
        """Comparison should be in table format."""
        content = _read_doc()
        # Find the comparison section and check for table markers
        assert "| Dimension" in content or "| dimension" in content.lower(), (
            "Missing comparison table with dimensions"
        )

    def test_comparison_covers_communication(self):
        """Comparison should cover communication differences."""
        content = _read_doc()
        assert "lateral" in content.lower() or "direct" in content.lower(), (
            "Missing lateral/direct communication in comparison"
        )

    def test_comparison_covers_context(self):
        """Comparison should cover context window differences."""
        content = _read_doc()
        assert "1M" in content or "context" in content.lower(), (
            "Missing context window information in comparison"
        )

    def test_comparison_covers_cost(self):
        """Comparison should cover cost differences."""
        content = _read_doc()
        assert "3-5x" in content or "cost" in content.lower(), (
            "Missing cost comparison"
        )


class TestCOSIntegrationSection:
    """Documentation must cover COS integration points."""

    def test_integration_section_exists(self):
        """Should have a COS integration section."""
        content = _read_doc()
        assert "COS Integration" in content or "Integration Point" in content, (
            "Missing COS Integration section"
        )

    def test_subagent_start_hook(self):
        """Should reference SubagentStart hook for preamble injection."""
        content = _read_doc()
        assert "SubagentStart" in content, (
            "Missing SubagentStart hook reference"
        )

    def test_task_created_hook(self):
        """Should reference TaskCreated hook for quality gates."""
        content = _read_doc()
        assert "TaskCreated" in content, (
            "Missing TaskCreated hook reference"
        )

    def test_task_completed_hook(self):
        """Should reference TaskCompleted hook for acceptance criteria."""
        content = _read_doc()
        assert "TaskCompleted" in content, (
            "Missing TaskCompleted hook reference"
        )

    def test_teammate_idle_hook(self):
        """Should reference TeammateIdle hook."""
        content = _read_doc()
        assert "TeammateIdle" in content, (
            "Missing TeammateIdle hook reference"
        )

    def test_engram_integration(self):
        """Should reference Engram for shared memory."""
        content = _read_doc()
        assert "Engram" in content or "engram" in content, (
            "Missing Engram integration reference"
        )

    def test_rate_limiter_integration(self):
        """Should reference rate limiting for cost control."""
        content = _read_doc()
        assert "rate limit" in content.lower() or "Rate limiter" in content, (
            "Missing rate limiter integration"
        )

    def test_security_hooks_integration(self):
        """Should reference security hooks applying to teammates."""
        content = _read_doc()
        assert "security" in content.lower() and "hook" in content.lower(), (
            "Missing security hooks integration"
        )

    def test_active_tasks_integration(self):
        """Should reference active-tasks.json synchronization."""
        content = _read_doc()
        assert "active-tasks" in content or "active_tasks" in content, (
            "Missing active-tasks.json integration reference"
        )


class TestLimitationsSection:
    """Documentation must cover known limitations."""

    def test_limitations_section_exists(self):
        """Should have a limitations section."""
        content = _read_doc()
        assert "Limitation" in content, (
            "Missing Limitations section"
        )

    def test_no_resume_limitation(self):
        """Should document the no-resume limitation."""
        content = _read_doc()
        assert "resum" in content.lower(), (
            "Missing session resumption limitation"
        )

    def test_task_lag_limitation(self):
        """Should document task status lag."""
        content = _read_doc()
        assert "lag" in content.lower() or "fail to mark" in content.lower(), (
            "Missing task status lag limitation"
        )

    def test_one_team_limitation(self):
        """Should document one-team-per-session limitation."""
        content = _read_doc()
        assert "one team" in content.lower() or "One team" in content, (
            "Missing one-team-per-session limitation"
        )

    def test_cost_limitation(self):
        """Should document higher token cost."""
        content = _read_doc()
        assert "3-5x" in content, (
            "Missing 3-5x token cost documentation"
        )


class TestWhenToUseSection:
    """Documentation should guide when to use Teams vs Subagents."""

    def test_when_to_use_section(self):
        """Should have a when-to-use decision section."""
        content = _read_doc()
        assert "When to Use" in content, (
            "Missing 'When to Use' section"
        )

    def test_scenario_table(self):
        """Should have a scenario-based decision table."""
        content = _read_doc()
        assert "| Scenario" in content or "| scenario" in content.lower(), (
            "Missing scenario-based decision table"
        )


class TestBestPracticesSection:
    """Documentation should include best practices."""

    def test_best_practices_section(self):
        """Should have a best practices section."""
        content = _read_doc()
        assert "Best Practice" in content or "best practice" in content.lower(), (
            "Missing Best Practices section"
        )

    def test_team_sizing_guidance(self):
        """Should recommend 3-5 teammates."""
        content = _read_doc()
        assert "3-5" in content, (
            "Missing 3-5 teammates recommendation"
        )


class TestCostSection:
    """Documentation should cover cost implications."""

    def test_cost_section(self):
        """Should have a cost implications section."""
        content = _read_doc()
        assert "Cost" in content, (
            "Missing Cost section"
        )

    def test_cost_multiplier_table(self):
        """Should show cost multiplier by team size."""
        content = _read_doc()
        assert "Multiplier" in content or "multiplier" in content, (
            "Missing cost multiplier information"
        )
