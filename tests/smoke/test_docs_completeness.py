"""Behavior tests for documentation completeness.

Verifies that all required documentation files exist and contain
the expected sections and content.

Python 3.9+ compatible.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

# Project root is three levels up from this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


class TestResearchLog:
    """Verify docs/research-log.md exists and has evaluation table."""

    def test_file_exists(self) -> None:
        """research-log.md exists in docs/."""
        assert (DOCS_DIR / "research-log.md").exists(), (
            "docs/research-log.md is missing"
        )

    def test_has_evaluation_table(self) -> None:
        """research-log.md contains an evaluation summary table."""
        content = (DOCS_DIR / "research-log.md").read_text()
        assert "| Tool |" in content or "| Tool" in content, (
            "research-log.md does not contain an evaluation summary table"
        )
        # Should have at least 5 tool evaluations
        tool_rows = [
            line for line in content.splitlines()
            if line.startswith("|") and "HOLD" in line or "ADOPT" in line or "TRIAL" in line or "Reference" in line
        ]
        assert len(tool_rows) >= 5, (
            f"research-log.md has {len(tool_rows)} tool evaluations, expected at least 5"
        )


class TestPatternsAdopted:
    """Verify docs/patterns-adopted.md exists and has all source categories."""

    def test_file_exists(self) -> None:
        """patterns-adopted.md exists in docs/."""
        assert (DOCS_DIR / "patterns-adopted.md").exists(), (
            "docs/patterns-adopted.md is missing"
        )

    def test_has_all_source_categories(self) -> None:
        """patterns-adopted.md covers all 6 external sources."""
        content = (DOCS_DIR / "patterns-adopted.md").read_text()
        expected_sources = [
            "SuperClaude",
            "Sprut Agent Kit",
            "ClaudeClaw",
            "QuinotoSpec",
            "Sazonia Archive",
            "Anthropic Engineering",
        ]
        for source in expected_sources:
            assert source in content, (
                f"patterns-adopted.md is missing source category: {source}"
            )


class TestSafetyMesh:
    """Verify docs/safety-mesh.md exists and has all 9 layers."""

    def test_file_exists(self) -> None:
        """safety-mesh.md exists in docs/."""
        assert (DOCS_DIR / "safety-mesh.md").exists(), (
            "docs/safety-mesh.md is missing"
        )

    def test_has_all_9_layers(self) -> None:
        """safety-mesh.md documents all 9 safety layers."""
        content = (DOCS_DIR / "safety-mesh.md").read_text()
        expected_hooks = [
            "clarification-gate",
            "blast-radius",
            "dry-run-preview",
            "scope-proportionality",
            "assumption-tracker",
            "trust-score-validator",
            "confidence-gate",
            "clarification-interceptor",
            "auto-rollback-trigger",
        ]
        for hook in expected_hooks:
            assert hook in content, (
                f"safety-mesh.md is missing layer for hook: {hook}"
            )


class TestCosPackageManager:
    """Verify docs/cos-package-manager.md exists."""

    def test_file_exists(self) -> None:
        """cos-package-manager.md exists in docs/."""
        assert (DOCS_DIR / "cos-package-manager.md").exists(), (
            "docs/cos-package-manager.md is missing"
        )

    def test_has_content(self) -> None:
        """cos-package-manager.md is not empty."""
        content = (DOCS_DIR / "cos-package-manager.md").read_text()
        assert len(content) > 100, (
            "docs/cos-package-manager.md appears to be empty or minimal"
        )


class TestArchitecture:
    """Verify docs/architecture.md exists."""

    def test_file_exists(self) -> None:
        """architecture.md exists in docs/."""
        assert (DOCS_DIR / "architecture.md").exists(), (
            "docs/architecture.md is missing"
        )


class TestFaq:
    """Verify docs/faq.md exists and has substantial content."""

    def test_file_exists(self) -> None:
        """faq.md exists in docs/."""
        assert (DOCS_DIR / "faq.md").exists(), (
            "docs/faq.md is missing"
        )

    def test_has_questions(self) -> None:
        """faq.md has at least 20 questions (## or ### headings with ?)."""
        content = (DOCS_DIR / "faq.md").read_text()
        # Count lines that look like questions (headings or Q: patterns)
        question_lines = [
            line for line in content.splitlines()
            if ("?" in line and line.strip().startswith("#"))
            or line.strip().startswith("Q:")
            or (line.strip().startswith("**") and "?" in line)
        ]
        assert len(question_lines) >= 20, (
            f"faq.md has {len(question_lines)} questions, expected at least 20"
        )


class TestRoadmap:
    """Verify docs/roadmap.md exists and has phase content."""

    def test_file_exists(self) -> None:
        """roadmap.md exists in docs/."""
        assert (DOCS_DIR / "roadmap.md").exists(), (
            "docs/roadmap.md is missing"
        )

    def test_has_phases(self) -> None:
        """roadmap.md mentions multiple phases."""
        content = (DOCS_DIR / "roadmap.md").read_text()
        # Should have at least 3 phase references
        phase_count = content.lower().count("phase")
        assert phase_count >= 3, (
            f"roadmap.md mentions 'phase' {phase_count} times, expected at least 3"
        )


class TestTesting:
    """Verify docs/testing.md exists."""

    def test_file_exists(self) -> None:
        """testing.md exists in docs/."""
        assert (DOCS_DIR / "testing.md").exists(), (
            "docs/testing.md is missing"
        )


class TestGettingStarted:
    """Verify docs/getting-started.md exists."""

    def test_file_exists(self) -> None:
        """getting-started.md exists in docs/."""
        assert (DOCS_DIR / "getting-started.md").exists(), (
            "docs/getting-started.md is missing"
        )


class TestIndex:
    """Verify docs/INDEX.md references all major docs."""

    def test_file_exists(self) -> None:
        """INDEX.md exists in docs/."""
        assert (DOCS_DIR / "INDEX.md").exists(), (
            "docs/INDEX.md is missing"
        )

    def test_references_key_docs(self) -> None:
        """INDEX.md references all key documentation files."""
        content = (DOCS_DIR / "INDEX.md").read_text()
        key_docs = [
            "getting-started.md",
            "architecture.md",
            "roadmap.md",
            "faq.md",
            "testing.md",
            "research-log.md",
            "patterns-adopted.md",
            "safety-mesh.md",
        ]
        for doc in key_docs:
            assert doc in content, (
                f"INDEX.md does not reference {doc}"
            )
