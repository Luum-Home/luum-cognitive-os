"""
UX Principles Tests

Validates that docs/ux-principles.md exists and contains all required principles,
anti-patterns table, and architecture mapping table.
"""

from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UX_DOC = PROJECT_ROOT / "docs" / "ux-principles.md"


def _read_ux_doc() -> str:
    """Read the UX principles document."""
    assert UX_DOC.is_file(), f"docs/ux-principles.md not found at {UX_DOC}"
    return UX_DOC.read_text(encoding="utf-8")


class TestUXPrinciplesDocExists:
    """docs/ux-principles.md must exist."""

    def test_ux_principles_file_exists(self):
        assert UX_DOC.is_file(), "docs/ux-principles.md must exist"


class TestUXPrinciplesContent:
    """All seven principles must be present."""

    def test_has_invisible_safety_principle(self):
        content = _read_ux_doc()
        assert "Invisible Safety" in content, (
            "docs/ux-principles.md must contain the 'Invisible Safety' principle"
        )

    def test_has_progressive_disclosure_principle(self):
        content = _read_ux_doc()
        assert "Progressive Disclosure" in content, (
            "docs/ux-principles.md must contain the 'Progressive Disclosure' principle"
        )

    def test_has_ai_is_the_driver_principle(self):
        content = _read_ux_doc()
        assert "The AI Is the Driver" in content, (
            "docs/ux-principles.md must contain the 'The AI Is the Driver' principle"
        )

    def test_has_speak_only_when_valuable_principle(self):
        content = _read_ux_doc()
        assert "Speak Only When Valuable" in content, (
            "docs/ux-principles.md must contain the 'Speak Only When Valuable' principle"
        )

    def test_has_cost_transparency_principle(self):
        content = _read_ux_doc()
        assert "Cost Transparency" in content, (
            "docs/ux-principles.md must contain the 'Cost Transparency' principle"
        )

    def test_has_anti_patterns_table(self):
        content = _read_ux_doc()
        assert "Anti-Pattern" in content and "Why It Is Bad" in content, (
            "docs/ux-principles.md must contain an anti-patterns table "
            "with 'Anti-Pattern' and 'Why It Is Bad' columns"
        )

    def test_has_architecture_mapping_table(self):
        content = _read_ux_doc()
        assert "User Visibility" in content and "Layer" in content, (
            "docs/ux-principles.md must contain an architecture mapping table "
            "with 'Layer' and 'User Visibility' columns"
        )

    def test_has_error_messages_principle(self):
        content = _read_ux_doc()
        assert "Error Messages Are Teaching Moments" in content, (
            "docs/ux-principles.md must contain the "
            "'Error Messages Are Teaching Moments' principle"
        )
