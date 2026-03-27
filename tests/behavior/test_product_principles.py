"""
Product Principles Tests

Validates that product and launch strategy documentation exists
and contains the required sections for guiding entrepreneurial decisions.
"""

import re
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    """Read file content, returning empty string on error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProductPrinciples:
    """Validate product-principles.md exists and has required content."""

    def test_product_principles_exists(self):
        """product-principles.md must exist in docs/."""
        path = DOCS_DIR / "product-principles.md"
        assert path.is_file(), (
            f"Missing {path}. Product principles documentation is required."
        )

    def test_has_numbered_principles(self):
        """product-principles.md must contain numbered product principles."""
        content = _read_text(DOCS_DIR / "product-principles.md")
        # Check for either "10 Product Principles" heading or numbered principles
        has_heading = "10 Product Principles" in content
        has_numbered = bool(re.search(r"###\s+\d+\.", content))
        assert has_heading or has_numbered, (
            "product-principles.md must contain '10 Product Principles' "
            "heading or numbered principle sections (### N.)"
        )

    def test_has_launch_anti_patterns_table(self):
        """product-principles.md must have a launch anti-patterns table."""
        content = _read_text(DOCS_DIR / "product-principles.md")
        assert "Anti-Pattern" in content and "What We Did" in content, (
            "product-principles.md must contain a launch anti-patterns table "
            "with 'Anti-Pattern' and 'What We Did' columns."
        )

    def test_has_value_proposition(self):
        """product-principles.md must include a value proposition section."""
        content = _read_text(DOCS_DIR / "product-principles.md")
        assert "Value Proposition" in content, (
            "product-principles.md must contain a 'Value Proposition' section."
        )


class TestLaunchStrategy:
    """Validate launch-strategy.md exists and has required content."""

    def test_launch_strategy_exists(self):
        """launch-strategy.md must exist in docs/."""
        path = DOCS_DIR / "launch-strategy.md"
        assert path.is_file(), (
            f"Missing {path}. Launch strategy documentation is required."
        )

    def test_has_phased_launch_plan(self):
        """launch-strategy.md must contain a phased launch plan."""
        content = _read_text(DOCS_DIR / "launch-strategy.md")
        has_phases = (
            "Phase 0" in content
            and "Phase 1" in content
            and "Phase 2" in content
        )
        assert has_phases, (
            "launch-strategy.md must contain a phased launch plan "
            "with at least Phase 0, Phase 1, and Phase 2."
        )
