"""Behavior tests for the open-source strategy document.

Validates that the strategy document exists and contains all required
sections for a complete open-source decision analysis.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STRATEGY_PATH = PROJECT_ROOT / "docs" / "open-source-strategy.md"


def _read_strategy() -> str:
    """Read the strategy document content."""
    assert STRATEGY_PATH.exists(), f"Strategy document not found at {STRATEGY_PATH}"
    return STRATEGY_PATH.read_text()


class TestOpenSourceStrategyExists:
    """Verify the document exists and has minimum content."""

    def test_document_exists(self):
        """Strategy document must exist at docs/open-source-strategy.md."""
        assert STRATEGY_PATH.exists()

    def test_document_not_empty(self):
        """Strategy document must have substantial content."""
        content = _read_strategy()
        assert len(content) > 2000, (
            f"Strategy document is only {len(content)} chars; "
            "expected substantial analysis (>2000 chars)"
        )


class TestRequiredSections:
    """Verify all required sections are present."""

    def test_has_current_state_section(self):
        content = _read_strategy()
        assert "Current State" in content, "Missing 'Current State' section"

    def test_has_why_open_source_section(self):
        content = _read_strategy()
        assert "Why Open Source" in content, "Missing 'Why Open Source' section"

    def test_has_why_not_open_source_section(self):
        content = _read_strategy()
        assert "Why NOT Open Source" in content or "Why Not Open Source" in content, (
            "Missing 'Why NOT Open Source' section"
        )

    def test_has_license_options_section(self):
        content = _read_strategy()
        assert "License" in content, "Missing license analysis section"
        # Must discuss at least 3 license types
        license_types = ["MIT", "Apache", "AGPL"]
        found = sum(1 for lt in license_types if lt in content)
        assert found >= 3, (
            f"License section only mentions {found}/3 required license types "
            f"(MIT, Apache, AGPL)"
        )

    def test_has_monetization_section(self):
        content = _read_strategy()
        assert "Monetization" in content or "monetization" in content, (
            "Missing monetization analysis section"
        )

    def test_has_recommendation_section(self):
        content = _read_strategy()
        assert "Recommendation" in content or "recommendation" in content, (
            "Missing recommendation section"
        )

    def test_has_roadmap_section(self):
        content = _read_strategy()
        assert "Roadmap" in content or "roadmap" in content, (
            "Missing roadmap section"
        )


class TestLicenseAnalysis:
    """Verify the license analysis is substantive."""

    def test_license_table_present(self):
        """License comparison should include a structured table."""
        content = _read_strategy()
        # Check for pipe-delimited table rows mentioning licenses
        lines = content.split("\n")
        table_rows_with_license = [
            line for line in lines
            if "|" in line and any(
                lic in line for lic in ["MIT", "Apache", "AGPL", "BSL"]
            )
        ]
        assert len(table_rows_with_license) >= 3, (
            f"Expected at least 3 license table rows, found {len(table_rows_with_license)}"
        )

    def test_discusses_patent_protection(self):
        """Patent considerations should be addressed."""
        content = _read_strategy()
        assert "patent" in content.lower(), (
            "License analysis should discuss patent protection"
        )

    def test_discusses_enterprise_acceptance(self):
        """Enterprise adoption implications should be discussed."""
        content = _read_strategy()
        assert "enterprise" in content.lower(), (
            "License analysis should discuss enterprise acceptance"
        )


class TestMonetization:
    """Verify monetization analysis covers multiple models."""

    def test_multiple_models_discussed(self):
        """At least 3 monetization models should be analyzed."""
        content = _read_strategy()
        models = [
            "open core",
            "support",
            "consulting",
            "hosting",
            "SaaS",
            "enterprise",
            "dual license",
            "premium",
            "managed",
        ]
        found = sum(1 for m in models if m.lower() in content.lower())
        assert found >= 3, (
            f"Expected at least 3 monetization models discussed, found {found}"
        )

    def test_pros_and_cons_present(self):
        """Each model should have pros and cons analysis."""
        content = _read_strategy()
        assert "Pros" in content and "Cons" in content, (
            "Monetization models should include pros and cons"
        )


class TestRecommendation:
    """Verify the recommendation is clear and justified."""

    def test_recommendation_includes_license_choice(self):
        """Recommendation must state the chosen license."""
        content = _read_strategy()
        rec_idx = content.find("Recommendation")
        assert rec_idx > 0, "Recommendation section not found"
        rec_section = content[rec_idx:rec_idx + 3000]
        license_mentioned = any(
            lic in rec_section
            for lic in ["MIT", "Apache", "AGPL", "BSL"]
        )
        assert license_mentioned, (
            "Recommendation section must state a specific license choice"
        )

    def test_recommendation_includes_monetization_choice(self):
        """Recommendation must state a monetization approach."""
        content = _read_strategy()
        rec_idx = content.find("Recommendation")
        assert rec_idx > 0
        rec_section = content[rec_idx:rec_idx + 3000]
        monetization_terms = [
            "open core", "support", "hosting", "SaaS",
            "enterprise", "premium", "managed", "consulting",
        ]
        mentioned = any(
            term.lower() in rec_section.lower() for term in monetization_terms
        )
        assert mentioned, (
            "Recommendation must include a monetization approach"
        )


class TestRoadmap:
    """Verify the roadmap has actionable phases."""

    def test_has_multiple_phases(self):
        """Roadmap should have at least 3 phases."""
        content = _read_strategy()
        phase_count = content.lower().count("phase")
        assert phase_count >= 3, (
            f"Roadmap should have at least 3 phases, found {phase_count} mentions"
        )

    def test_includes_cleanup_phase(self):
        """Roadmap must include a cleanup/audit phase."""
        content = _read_strategy()
        cleanup_terms = ["cleanup", "clean up", "audit", "scrub", "review"]
        found = any(term in content.lower() for term in cleanup_terms)
        assert found, "Roadmap must include a cleanup or audit phase"

    def test_includes_launch_phase(self):
        """Roadmap must include a launch/announcement phase."""
        content = _read_strategy()
        launch_terms = ["launch", "announce", "hacker news", "product hunt"]
        found = any(term in content.lower() for term in launch_terms)
        assert found, "Roadmap must include a launch or announcement phase"


class TestCompetitiveContext:
    """Verify competitors are analyzed."""

    def test_mentions_competitors(self):
        """Document should reference the competitive landscape."""
        content = _read_strategy()
        competitors = ["Agent Zero", "OpenClaw"]
        found = sum(1 for c in competitors if c in content)
        assert found >= 1, (
            "Strategy should reference at least one competitor (Agent Zero, OpenClaw)"
        )

    def test_mentions_community_gap(self):
        """Document should acknowledge the community gap."""
        content = _read_strategy()
        community_terms = ["community", "contributor", "adoption"]
        found = sum(1 for t in community_terms if t in content.lower())
        assert found >= 2, (
            "Strategy should discuss community and adoption gaps"
        )
