"""Behavior tests for skills/install-recommended/SKILL.md

Validates that the install-recommended skill exists with correct metadata,
references stack detection, and is listed in CATALOG.md.

Related files:
  - skills/install-recommended/SKILL.md
  - lib/stack_skill_recommender.py
  - skills/CATALOG.md

Author: luum
"""

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = PROJECT_ROOT / "skills" / "install-recommended" / "SKILL.md"
CATALOG_PATH = PROJECT_ROOT / "skills" / "CATALOG.md"


class TestSkillExists:
    """Verify the install-recommended skill file exists and has correct structure."""

    def test_skill_file_exists(self):
        assert SKILL_PATH.exists(), f"SKILL.md not found at {SKILL_PATH}"

    def test_skill_has_frontmatter(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
        # Find closing ---
        second_dash = content.index("---", 3)
        assert second_dash > 3, "SKILL.md must have closing frontmatter delimiter"

    def test_skill_has_audience_project(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        assert "audience: project" in content, "install-recommended must have audience: project"

    def test_skill_has_invoke_command(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        assert "invoke: /install-recommended" in content, "Must have invoke: /install-recommended"

    def test_skill_has_name(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        assert "name: install-recommended" in content, "Must have name: install-recommended"

    def test_skill_has_description(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        assert "description:" in content, "Must have a description field"


class TestSkillReferencesStackDetection:
    """Verify the skill references the stack detection library."""

    def test_skill_references_stack_skill_recommender(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        assert "StackSkillRecommender" in content, (
            "SKILL.md must reference StackSkillRecommender"
        )

    def test_skill_references_detect_stack(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        assert "detect_stack" in content or "detect" in content.lower(), (
            "SKILL.md must reference stack detection"
        )

    def test_skill_references_recommend(self):
        content = SKILL_PATH.read_text(encoding="utf-8")
        assert "recommend" in content.lower(), (
            "SKILL.md must reference skill recommendation"
        )


class TestSkillInCatalog:
    """Verify the skill is listed in CATALOG.md."""

    def test_catalog_exists(self):
        assert CATALOG_PATH.exists(), f"CATALOG.md not found at {CATALOG_PATH}"

    def test_skill_listed_in_catalog(self):
        catalog = CATALOG_PATH.read_text(encoding="utf-8")
        assert "install-recommended" in catalog, (
            "install-recommended must be listed in skills/CATALOG.md"
        )

    def test_catalog_has_invoke_command(self):
        catalog = CATALOG_PATH.read_text(encoding="utf-8")
        assert "/install-recommended" in catalog, (
            "/install-recommended invoke command must appear in CATALOG.md"
        )


class TestLibraryExists:
    """Verify the supporting library exists."""

    def test_stack_skill_recommender_module_exists(self):
        lib_path = PROJECT_ROOT / "lib" / "stack_skill_recommender.py"
        assert lib_path.exists(), f"Library not found at {lib_path}"

    def test_stack_skill_recommender_importable(self):
        """The module can be imported without errors."""
        import importlib
        import sys

        # Ensure project root is in path for import.
        str_root = str(PROJECT_ROOT)
        if str_root not in sys.path:
            sys.path.insert(0, str_root)

        mod = importlib.import_module("lib.stack_skill_recommender")
        assert hasattr(mod, "StackSkillRecommender")
        assert hasattr(mod, "SkillRecommendation")
