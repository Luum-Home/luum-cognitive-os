"""Behavior tests for UI platforms evaluation document completeness.

Validates that docs/ui-platforms-evaluation.md exists, contains the
summary matrix with all 8 platforms, license compatibility section,
reusable components, patterns to adopt (AGPL clean-room), and the
recommended approach section.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOC_PATH = PROJECT_ROOT / "docs" / "ui-platforms-evaluation.md"

REQUIRED_PLATFORMS = [
    "Paperclip",
    "AnythingLLM",
    "AutoMaker",
    "Aperant",
    "inngest/agent-kit",
    "AionUi",
    "Agent Zero",
    "OpenClaw",
]


def _read_doc() -> str:
    """Read the UI platforms evaluation document."""
    assert DOC_PATH.exists(), f"Document not found at {DOC_PATH}"
    return DOC_PATH.read_text()


class TestDocumentExists:
    """UI platforms evaluation document must exist and be substantive."""

    def test_document_exists(self):
        """docs/ui-platforms-evaluation.md should exist."""
        assert DOC_PATH.exists(), "docs/ui-platforms-evaluation.md is missing"

    def test_document_not_empty(self):
        """Document should contain substantial content."""
        content = _read_doc()
        assert len(content) > 2000, "Document is too short to be a comprehensive evaluation"


class TestSummaryMatrix:
    """Summary matrix must contain all 8 evaluated platforms."""

    def test_has_summary_matrix_section(self):
        """Document should have a Summary Matrix section."""
        content = _read_doc()
        assert "## Summary Matrix" in content, "Missing '## Summary Matrix' section"

    def test_all_platforms_in_matrix(self):
        """All 8 platforms should appear in the document."""
        content = _read_doc()
        for platform in REQUIRED_PLATFORMS:
            assert platform in content, f"Platform '{platform}' not found in document"

    def test_matrix_has_table_headers(self):
        """Summary matrix should have expected column headers."""
        content = _read_doc()
        # Find the summary matrix section
        matrix_start = content.index("## Summary Matrix")
        matrix_section = content[matrix_start:matrix_start + 2000]
        for header in ["Platform", "License", "Type", "COS Fit", "Recommendation"]:
            assert header in matrix_section, f"Missing column header '{header}' in summary matrix"


class TestLicenseCompatibility:
    """License compatibility section must cover all license types."""

    def test_has_license_section(self):
        """Document should have a License Compatibility section."""
        content = _read_doc()
        assert "## License Compatibility" in content, "Missing '## License Compatibility' section"

    def test_covers_mit(self):
        """License section should cover MIT."""
        content = _read_doc()
        license_start = content.index("## License Compatibility")
        license_section = content[license_start:license_start + 1500]
        assert "MIT" in license_section, "MIT license not covered in license compatibility"

    def test_covers_apache(self):
        """License section should cover Apache-2.0."""
        content = _read_doc()
        license_start = content.index("## License Compatibility")
        license_section = content[license_start:license_start + 1500]
        assert "Apache" in license_section, "Apache license not covered in license compatibility"

    def test_covers_agpl(self):
        """License section should cover AGPL-3.0 as blocked."""
        content = _read_doc()
        license_start = content.index("## License Compatibility")
        license_section = content[license_start:license_start + 1500]
        assert "AGPL" in license_section, "AGPL license not covered in license compatibility"

    def test_agpl_marked_blocked(self):
        """AGPL should be marked as BLOCKED for code adoption."""
        content = _read_doc()
        assert "BLOCKED" in content, "AGPL should be marked as BLOCKED"


class TestReusableComponents:
    """Reusable components section must list components from MIT/Apache sources."""

    def test_has_reusable_components_section(self):
        """Document should have a Reusable Components section."""
        content = _read_doc()
        assert "## Reusable Components" in content, "Missing '## Reusable Components' section"

    def test_automaker_components_listed(self):
        """AutoMaker components should be listed (MIT source)."""
        content = _read_doc()
        assert "AutoMaker" in content, "AutoMaker components not listed"
        # Check for specific component mentions
        assert "xterm" in content.lower() or "terminal" in content.lower(), \
            "Terminal emulation component from AutoMaker not mentioned"

    def test_inngest_components_listed(self):
        """inngest/agent-kit components should be listed (Apache-2.0 source)."""
        content = _read_doc()
        assert "inngest" in content, "inngest/agent-kit components not listed"


class TestPatternsToAdopt:
    """Patterns section must cover AGPL sources with clean-room approach."""

    def test_has_patterns_section(self):
        """Document should have a Patterns to Adopt section."""
        content = _read_doc()
        assert "## Patterns to Adopt" in content, "Missing '## Patterns to Adopt' section"

    def test_aperant_patterns_clean_room(self):
        """Aperant patterns should be marked as clean-room only."""
        content = _read_doc()
        # Both Aperant and clean-room should appear
        assert "Aperant" in content, "Aperant not mentioned in patterns section"
        assert "clean-room" in content.lower() or "clean room" in content.lower(), \
            "Clean-room approach not mentioned for AGPL sources"

    def test_memory_pattern_mentioned(self):
        """Memory injection pattern from Aperant should be mentioned."""
        content = _read_doc()
        assert "memory" in content.lower(), "Memory pattern from Aperant not mentioned"


class TestRecommendedApproach:
    """Recommended approach section must outline short/medium/long-term strategy."""

    def test_has_recommended_approach_section(self):
        """Document should have a Recommended Approach section."""
        content = _read_doc()
        assert "## Recommended Approach" in content, "Missing '## Recommended Approach' section"

    def test_has_short_term(self):
        """Recommended approach should include short-term strategy."""
        content = _read_doc()
        approach_start = content.index("## Recommended Approach")
        approach_section = content[approach_start:]
        assert "short-term" in approach_section.lower() or "short term" in approach_section.lower(), \
            "Short-term strategy not found in recommended approach"

    def test_has_medium_term(self):
        """Recommended approach should include medium-term strategy."""
        content = _read_doc()
        approach_start = content.index("## Recommended Approach")
        approach_section = content[approach_start:]
        assert "medium-term" in approach_section.lower() or "medium term" in approach_section.lower(), \
            "Medium-term strategy not found in recommended approach"

    def test_has_long_term(self):
        """Recommended approach should include long-term strategy."""
        content = _read_doc()
        approach_start = content.index("## Recommended Approach")
        approach_section = content[approach_start:]
        assert "long-term" in approach_section.lower() or "long term" in approach_section.lower(), \
            "Long-term strategy not found in recommended approach"

    def test_references_paperclip(self):
        """Recommended approach should reference Paperclip integration."""
        content = _read_doc()
        approach_start = content.index("## Recommended Approach")
        approach_section = content[approach_start:]
        assert "Paperclip" in approach_section, \
            "Paperclip not referenced in recommended approach"


class TestKeyPlatformReferences:
    """Key platforms must be substantively referenced throughout."""

    def test_paperclip_referenced(self):
        """Paperclip should be referenced multiple times as current solution."""
        content = _read_doc()
        assert content.count("Paperclip") >= 3, \
            "Paperclip should be referenced at least 3 times (matrix, details, approach)"

    def test_automaker_referenced(self):
        """AutoMaker should be referenced multiple times for components."""
        content = _read_doc()
        assert content.count("AutoMaker") >= 3, \
            "AutoMaker should be referenced at least 3 times (matrix, components, approach)"

    def test_aperant_referenced(self):
        """Aperant should be referenced with AGPL warning."""
        content = _read_doc()
        assert content.count("Aperant") >= 2, \
            "Aperant should be referenced at least 2 times (matrix, patterns)"
        assert "AGPL" in content, "AGPL warning should accompany Aperant references"

    def test_inngest_referenced(self):
        """inngest should be referenced for real-time capabilities."""
        content = _read_doc()
        assert content.count("inngest") >= 2, \
            "inngest should be referenced at least 2 times (matrix, components)"
