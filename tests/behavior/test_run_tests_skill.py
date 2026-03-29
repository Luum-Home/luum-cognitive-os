"""Behavior tests for the /run-tests skill.

Validates that the skill file exists, has correct metadata, references
the detection library, and is properly cataloged.

Related: skills/run-tests/SKILL.md, lib/test_framework_detector.py, skills/CATALOG.md
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SKILL_PATH = PROJECT_ROOT / "skills" / "run-tests" / "SKILL.md"
CATALOG_PATH = PROJECT_ROOT / "skills" / "CATALOG.md"
LIB_PATH = PROJECT_ROOT / "lib" / "test_framework_detector.py"


class TestSkillFileExists:
    """The skill file must exist with correct structure."""

    def test_skill_file_exists(self):
        assert SKILL_PATH.is_file(), f"SKILL.md not found at {SKILL_PATH}"

    def test_skill_has_frontmatter(self):
        content = SKILL_PATH.read_text()
        assert content.startswith("---"), "SKILL.md must start with YAML frontmatter"
        parts = content.split("---", 2)
        assert len(parts) >= 3, "SKILL.md must have complete frontmatter (--- ... ---)"

    def test_skill_audience_is_project(self):
        content = SKILL_PATH.read_text()
        parts = content.split("---", 2)
        frontmatter = parts[1]
        assert "audience: project" in frontmatter, (
            "run-tests skill must have audience: project"
        )

    def test_skill_has_invoke(self):
        content = SKILL_PATH.read_text()
        parts = content.split("---", 2)
        frontmatter = parts[1]
        assert "invoke: /run-tests" in frontmatter

    def test_skill_has_version(self):
        content = SKILL_PATH.read_text()
        parts = content.split("---", 2)
        frontmatter = parts[1]
        assert re.search(r"version:\s*\d+\.\d+\.\d+", frontmatter), (
            "SKILL.md must have a semver version"
        )


class TestSkillContent:
    """The skill content must reference auto-detection and key features."""

    def test_references_auto_detection(self):
        content = SKILL_PATH.read_text()
        assert "test_framework_detector" in content, (
            "Skill must reference the detection library"
        )

    def test_has_coverage_option(self):
        content = SKILL_PATH.read_text()
        assert "--coverage" in content, "Skill must document --coverage option"

    def test_has_watch_option(self):
        content = SKILL_PATH.read_text()
        assert "--watch" in content, "Skill must document --watch option"

    def test_has_path_option(self):
        content = SKILL_PATH.read_text()
        # Should mention running a specific path/file
        assert "path" in content.lower(), "Skill must support running specific test paths"

    def test_has_framework_detection_table(self):
        content = SKILL_PATH.read_text()
        # Should list at least pytest, jest, go
        assert "pytest" in content
        assert "jest" in content
        assert "go" in content.lower()

    def test_no_cos_dependency_claim(self):
        """Skill should work standalone without COS infrastructure."""
        content = SKILL_PATH.read_text()
        assert "standalone" in content.lower() or "no dependency" in content.lower() or "NO dependency" in content, (
            "Skill should note it works without COS infrastructure"
        )


class TestDetectorLibrary:
    """The detection library must exist and be importable."""

    def test_lib_file_exists(self):
        assert LIB_PATH.is_file(), f"Library not found at {LIB_PATH}"

    def test_importable(self):
        from lib.test_framework_detector import (
            DetectedFramework,
            TestFrameworkDetector,
        )

        assert DetectedFramework is not None
        assert TestFrameworkDetector is not None

    def test_detector_has_detect(self):
        from lib.test_framework_detector import TestFrameworkDetector

        detector = TestFrameworkDetector()
        assert hasattr(detector, "detect")
        assert hasattr(detector, "detect_primary")
        assert hasattr(detector, "format_detection")


class TestCatalogEntry:
    """The skill must be listed in CATALOG.md."""

    def test_catalog_has_run_tests(self):
        assert CATALOG_PATH.is_file(), "CATALOG.md must exist"
        content = CATALOG_PATH.read_text()
        assert "run-tests" in content, "run-tests must be listed in CATALOG.md"

    def test_catalog_entry_has_project_audience(self):
        content = CATALOG_PATH.read_text()
        # Find the line with run-tests and check it contains project
        for line in content.splitlines():
            if "run-tests" in line and "|" in line:
                assert "project" in line.lower(), (
                    "CATALOG.md entry for run-tests must show project audience"
                )
                break
        else:
            pytest.fail("run-tests entry not found as a table row in CATALOG.md")
