"""Behavior tests for competitive analysis documentation.

Validates that docs/competitive-analysis.md exists, contains the required
sections (Non-Replaceable, Replaceable, Strategic Positioning, Metrics,
Roadmap), and references all key competitors (Agent Zero, OpenClaw,
Claude Code).
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ANALYSIS_PATH = PROJECT_ROOT / "docs" / "competitive-analysis.md"


def _read_analysis() -> str:
    """Read the competitive analysis content."""
    assert ANALYSIS_PATH.exists(), f"Competitive analysis doc not found at {ANALYSIS_PATH}"
    return ANALYSIS_PATH.read_text()


class TestDocumentExists:
    """docs/competitive-analysis.md must exist and be substantial."""

    def test_doc_exists(self):
        """Competitive analysis file should exist."""
        assert ANALYSIS_PATH.exists(), "docs/competitive-analysis.md is missing"

    def test_doc_not_empty(self):
        """Documentation should contain substantial content."""
        content = _read_analysis()
        assert len(content) > 1000, "Competitive analysis doc is too short"


class TestNonReplaceableSection:
    """Document must have a 'Non-Replaceable' section."""

    def test_non_replaceable_section_exists(self):
        """Should have a section about what makes COS non-replaceable."""
        content = _read_analysis()
        assert "Non-Replaceable" in content, "Missing 'Non-Replaceable' section"

    def test_non_replaceable_has_table(self):
        """Non-replaceable section should contain a comparison table."""
        content = _read_analysis()
        # Find the section and verify it has a table
        idx = content.find("Non-Replaceable")
        assert idx != -1
        section = content[idx:idx + 2000]
        assert "| Differentiator" in section or "| COS" in section, (
            "Non-Replaceable section should contain a comparison table"
        )

    def test_non_replaceable_mentions_quality_governance(self):
        """Non-replaceable section should mention quality governance."""
        content = _read_analysis()
        assert "Quality governance" in content or "quality governance" in content, (
            "Non-Replaceable section should mention quality governance"
        )

    def test_non_replaceable_mentions_sdd(self):
        """Non-replaceable section should mention SDD pipeline."""
        content = _read_analysis()
        assert "SDD" in content, "Non-Replaceable section should mention SDD pipeline"


class TestReplaceableSection:
    """Document must have a 'Replaceable' section."""

    def test_replaceable_section_exists(self):
        """Should have a section about where COS is replaceable."""
        content = _read_analysis()
        assert "Replaceable" in content, "Missing 'Replaceable' section"

    def test_replaceable_has_table(self):
        """Replaceable section should contain a comparison table."""
        content = _read_analysis()
        idx = content.find("IS Replaceable")
        if idx == -1:
            idx = content.find("Replaceable")
        assert idx != -1
        section = content[idx:idx + 2000]
        assert "| Area" in section or "| Who Does It Better" in section, (
            "Replaceable section should contain a comparison table"
        )

    def test_replaceable_mentions_ui(self):
        """Replaceable section should mention UI as a weakness."""
        content = _read_analysis()
        assert "UI" in content or "Dashboard" in content, (
            "Replaceable section should mention UI/Dashboard weakness"
        )


class TestStrategicPositioningSection:
    """Document must have a 'Strategic Positioning' section."""

    def test_strategic_positioning_exists(self):
        """Should have a Strategic Positioning section."""
        content = _read_analysis()
        assert "Strategic Positioning" in content, "Missing 'Strategic Positioning' section"

    def test_strategic_positioning_explains_differentiation(self):
        """Strategic positioning should explain how COS differs from competitors."""
        content = _read_analysis()
        idx = content.find("Strategic Positioning")
        assert idx != -1
        section = content[idx:idx + 3000]
        # Should explain the positioning relative to at least two competitors
        competitors_mentioned = sum(1 for c in ["Agent Zero", "OpenClaw", "Claude Code"]
                                    if c in section)
        assert competitors_mentioned >= 2, (
            f"Strategic Positioning should reference at least 2 competitors, found {competitors_mentioned}"
        )

    def test_replaceable_risk_discussed(self):
        """Should discuss what would make COS replaceable."""
        content = _read_analysis()
        assert "Replaceable" in content, "Should discuss replaceability risk"


class TestCompetitorReferences:
    """Document must reference all key competitors."""

    def test_references_agent_zero(self):
        """Should reference Agent Zero."""
        content = _read_analysis()
        assert "Agent Zero" in content, "Missing Agent Zero reference"

    def test_references_openclaw(self):
        """Should reference OpenClaw."""
        content = _read_analysis()
        assert "OpenClaw" in content, "Missing OpenClaw reference"

    def test_references_claude_code(self):
        """Should reference Claude Code."""
        content = _read_analysis()
        assert "Claude Code" in content, "Missing Claude Code reference"


class TestMetricsComparison:
    """Document must have a metrics comparison table."""

    def test_metrics_section_exists(self):
        """Should have a Metrics Comparison section."""
        content = _read_analysis()
        assert "Metrics Comparison" in content or "Metrics" in content, (
            "Missing Metrics Comparison section"
        )

    def test_metrics_has_table(self):
        """Metrics section should contain a comparison table."""
        content = _read_analysis()
        idx = content.find("Metrics Comparison")
        if idx == -1:
            idx = content.find("Metrics")
        assert idx != -1
        section = content[idx:idx + 2000]
        assert "| Metric" in section or "| COS" in section, (
            "Metrics section should contain a comparison table"
        )

    def test_metrics_includes_stars(self):
        """Metrics should compare GitHub stars."""
        content = _read_analysis()
        assert "Stars" in content or "stars" in content, (
            "Metrics should compare GitHub stars"
        )

    def test_metrics_includes_tests(self):
        """Metrics should compare test counts."""
        content = _read_analysis()
        assert "Tests" in content or "tests" in content or "4099" in content, (
            "Metrics should compare test counts"
        )


class TestRoadmapSection:
    """Document must have a roadmap section."""

    def test_roadmap_section_exists(self):
        """Should have a Roadmap section."""
        content = _read_analysis()
        assert "Roadmap" in content, "Missing Roadmap section"

    def test_roadmap_has_priorities(self):
        """Roadmap should include priority levels."""
        content = _read_analysis()
        idx = content.find("Roadmap")
        assert idx != -1
        section = content[idx:idx + 2000]
        assert "P1" in section or "P2" in section or "Priority" in section, (
            "Roadmap should include priority levels"
        )

    def test_roadmap_has_plan(self):
        """Roadmap should include plans for closing gaps."""
        content = _read_analysis()
        idx = content.find("Roadmap")
        assert idx != -1
        section = content[idx:idx + 2000]
        assert "Plan" in section or "plan" in section, (
            "Roadmap should include plans for closing gaps"
        )
