"""Behavior tests for ecosystem comparison documentation.

Validates that docs/ecosystem-comparison.md exists, references all required
frameworks, and contains the expected structure for comparing COS with
Agent Zero and OpenClaw.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COMPARISON_PATH = PROJECT_ROOT / "docs" / "ecosystem-comparison.md"
SOURCES_PATH = PROJECT_ROOT / "docs" / "component-sources.md"


def _read_comparison() -> str:
    """Read the ecosystem comparison content."""
    assert COMPARISON_PATH.exists(), f"Ecosystem comparison doc not found at {COMPARISON_PATH}"
    return COMPARISON_PATH.read_text()


def _read_sources() -> str:
    """Read the component sources content."""
    assert SOURCES_PATH.exists(), f"Component sources doc not found at {SOURCES_PATH}"
    return SOURCES_PATH.read_text()


class TestEcosystemComparisonExists:
    """docs/ecosystem-comparison.md must exist and be substantial."""

    def test_doc_exists(self):
        """Ecosystem comparison file should exist."""
        assert COMPARISON_PATH.exists(), "docs/ecosystem-comparison.md is missing"

    def test_doc_not_empty(self):
        """Documentation should contain substantial content."""
        content = _read_comparison()
        assert len(content) > 2000, "Ecosystem comparison doc is too short"


class TestReferencesAgentZero:
    """Document must reference Agent Zero framework."""

    def test_agent_zero_mentioned(self):
        """Should reference Agent Zero."""
        content = _read_comparison()
        assert "Agent Zero" in content, "Missing Agent Zero reference"

    def test_agent_zero_repo_url(self):
        """Should include Agent Zero repository URL."""
        content = _read_comparison()
        assert "agent0ai/agent-zero" in content, "Missing Agent Zero repo URL"

    def test_agent_zero_plugins_index(self):
        """Should reference the Agent Zero plugins index repo."""
        content = _read_comparison()
        assert "a0-plugins" in content, "Missing a0-plugins index repo reference"


class TestReferencesOpenClaw:
    """Document must reference OpenClaw framework."""

    def test_openclaw_mentioned(self):
        """Should reference OpenClaw."""
        content = _read_comparison()
        assert "OpenClaw" in content, "Missing OpenClaw reference"


class TestFeatureMatrix:
    """Document must contain a feature comparison matrix."""

    def test_feature_matrix_section(self):
        """Should have a Feature Matrix section."""
        content = _read_comparison()
        assert "## Feature Matrix" in content, "Missing Feature Matrix section"

    def test_feature_matrix_has_table(self):
        """Feature matrix should be a markdown table with all three systems."""
        content = _read_comparison()
        # Check the table header contains all three systems
        assert "| COS" in content or "| COS (" in content, "Feature matrix table missing COS column"
        assert "Agent Zero" in content, "Feature matrix table missing Agent Zero column"
        assert "OpenClaw" in content, "Feature matrix table missing OpenClaw column"

    def test_key_features_compared(self):
        """Feature matrix should compare key features."""
        content = _read_comparison()
        key_features = ["Security", "Memory", "Multi-agent", "Plugin", "package"]
        found = sum(1 for f in key_features if f.lower() in content.lower())
        assert found >= 3, f"Feature matrix should compare at least 3 key features, found {found}"


class TestPatternsAdopted:
    """Document must have a Patterns Adopted section."""

    def test_patterns_adopted_section(self):
        """Should have a Patterns Adopted section."""
        content = _read_comparison()
        assert "Patterns Adopted" in content, "Missing 'Patterns Adopted' section"

    def test_patterns_have_source(self):
        """Patterns should reference their source framework."""
        content = _read_comparison()
        assert "Source" in content, "Patterns table missing Source column"

    def test_patterns_have_cos_implementation(self):
        """Patterns should describe COS implementation."""
        content = _read_comparison()
        assert "COS Implementation" in content, "Patterns table missing COS Implementation column"


class TestArchitectureComparison:
    """Document should contain architecture comparison."""

    def test_architecture_section(self):
        """Should have an Architecture Comparison section."""
        content = _read_comparison()
        assert "Architecture Comparison" in content or "Architecture" in content, (
            "Missing architecture comparison section"
        )


class TestComponentSourcesReferencesAgentZero:
    """component-sources.md must reference Agent Zero."""

    def test_agent_zero_in_sources(self):
        """component-sources.md should reference Agent Zero."""
        content = _read_sources()
        assert "Agent Zero" in content, "component-sources.md missing Agent Zero reference"

    def test_agent_zero_url_in_sources(self):
        """component-sources.md should include Agent Zero URL."""
        content = _read_sources()
        assert "agent0ai/agent-zero" in content, (
            "component-sources.md missing Agent Zero repo URL"
        )
