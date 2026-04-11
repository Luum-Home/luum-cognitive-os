"""Unit tests for lib/release_analyzer.py."""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from lib.release_analyzer import ReleaseAnalyzer, _bump


# ---------------------------------------------------------------------------
# _bump helper
# ---------------------------------------------------------------------------

class TestBumpHelper:
    def test_bump_patch(self):
        assert _bump("1.2.3", "patch") == "1.2.4"

    def test_bump_minor(self):
        assert _bump("1.2.3", "minor") == "1.3.0"

    def test_bump_major(self):
        assert _bump("1.2.3", "major") == "2.0.0"

    def test_bump_with_v_prefix(self):
        assert _bump("v1.0.0", "patch") == "1.0.1"

    def test_bump_zero_version(self):
        assert _bump("0.0.0", "minor") == "0.1.0"


# ---------------------------------------------------------------------------
# classify_changes
# ---------------------------------------------------------------------------

class TestClassifyLibFiles:
    def test_classify_lib_files(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["lib/foo.py", "lib/bar.py"])
        assert result["core"]["libs"] == ["lib/foo.py", "lib/bar.py"]
        assert result["core"]["hooks"] == []

    def test_classify_hook_files(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["hooks/my-hook.sh", "hooks/other.sh"])
        assert result["core"]["hooks"] == ["hooks/my-hook.sh", "hooks/other.sh"]

    def test_classify_rule_files(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["rules/my-rule.md"])
        assert result["core"]["rules"] == ["rules/my-rule.md"]

    def test_classify_package_files(self, tmp_path):
        # Create a cos-package.yaml for the package so version is readable
        pkg_dir = tmp_path / "packages" / "foo"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "cos-package.yaml").write_text('version: "1.0.0"\n')

        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["packages/foo/SKILL.md", "packages/foo/hooks/run.sh"])
        assert "foo" in result["packages"]
        assert len(result["packages"]["foo"]["files"]) == 2
        assert result["packages"]["foo"]["current_version"] == "1.0.0"

    def test_classify_test_files(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["tests/unit/test_foo.py", "tests/integration/test_bar.py"])
        assert "tests/unit/test_foo.py" in result["core"]["tests"]
        assert "tests/integration/test_bar.py" in result["core"]["tests"]

    def test_classify_doc_files(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["docs/guide.md"])
        assert "docs/guide.md" in result["core"]["docs"]

    def test_classify_config_files(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["cognitive-os.yaml", "settings.json"])
        assert "cognitive-os.yaml" in result["core"]["config"]
        assert "settings.json" in result["core"]["config"]

    def test_classify_template_files(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["templates/agent-preamble.md"])
        assert "templates/agent-preamble.md" in result["core"]["templates"]

    def test_classify_script_files(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["scripts/install-foo.sh"])
        assert "scripts/install-foo.sh" in result["core"]["scripts"]

    def test_classify_mixed(self, tmp_path):
        pkg_dir = tmp_path / "packages" / "bar"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "cos-package.yaml").write_text('version: "0.2.0"\n')

        a = ReleaseAnalyzer(str(tmp_path))
        files = [
            "lib/thing.py",
            "hooks/my.sh",
            "packages/bar/SKILL.md",
            "tests/unit/test_thing.py",
        ]
        result = a.classify_changes(files)
        assert result["core"]["libs"] == ["lib/thing.py"]
        assert result["core"]["hooks"] == ["hooks/my.sh"]
        assert result["core"]["tests"] == ["tests/unit/test_thing.py"]
        assert "bar" in result["packages"]

    def test_new_package_no_yaml(self, tmp_path):
        """Package with no cos-package.yaml → current_version is None."""
        pkg_dir = tmp_path / "packages" / "newpkg"
        pkg_dir.mkdir(parents=True)

        a = ReleaseAnalyzer(str(tmp_path))
        result = a.classify_changes(["packages/newpkg/SKILL.md"])
        assert result["packages"]["newpkg"]["current_version"] is None


# ---------------------------------------------------------------------------
# determine_version_bumps
# ---------------------------------------------------------------------------

class TestVersionBumps:
    def _make_analyzer(self, tmp_path, core_version="0.8.7"):
        a = ReleaseAnalyzer(str(tmp_path))
        # Patch read_core_version to return a fixed version
        a.read_core_version = lambda: core_version
        return a

    def test_bump_new_package(self, tmp_path):
        a = self._make_analyzer(tmp_path)
        classified = {
            "core": {k: [] for k in ("libs", "hooks", "rules", "templates",
                                     "scripts", "tests", "docs", "config")},
            "packages": {
                "mypkg": {"files": ["packages/mypkg/SKILL.md"],
                           "current_version": None, "cos_package_yaml": None},
            },
        }
        result = a.determine_version_bumps(classified)
        assert result["packages"]["mypkg"]["new_version"] == "1.0.0"
        assert result["packages"]["mypkg"]["is_new"] is True
        assert result["packages"]["mypkg"]["needs_release"] is True

    def test_bump_minor_new_features(self, tmp_path):
        a = self._make_analyzer(tmp_path, "0.8.7")
        classified = {
            "core": {
                "libs": ["lib/foo.py", "lib/bar.py"],
                "hooks": [], "rules": [], "templates": [],
                "scripts": [], "tests": [], "docs": [], "config": [],
            },
            "packages": {},
        }
        result = a.determine_version_bumps(classified)
        assert result["core"]["recommended_bump"] == "minor"
        assert result["core"]["new_version"] == "0.9.0"
        assert result["core"]["needs_release"] is True

    def test_bump_patch_docs_only(self, tmp_path):
        a = self._make_analyzer(tmp_path, "0.8.7")
        classified = {
            "core": {
                "libs": [], "hooks": [], "rules": [], "templates": [],
                "scripts": [], "tests": [], "docs": ["docs/guide.md"], "config": [],
            },
            "packages": {},
        }
        result = a.determine_version_bumps(classified)
        assert result["core"]["recommended_bump"] == "patch"
        assert result["core"]["new_version"] == "0.8.8"

    def test_bump_skip_test_only(self, tmp_path):
        a = self._make_analyzer(tmp_path, "0.8.7")
        classified = {
            "core": {
                "libs": [], "hooks": [], "rules": [], "templates": [],
                "scripts": [], "tests": ["tests/unit/test_foo.py"],
                "docs": [], "config": [],
            },
            "packages": {},
        }
        result = a.determine_version_bumps(classified)
        assert result["core"]["needs_release"] is False

    def test_bump_package_patch_docs_only(self, tmp_path):
        a = self._make_analyzer(tmp_path)
        classified = {
            "core": {k: [] for k in ("libs", "hooks", "rules", "templates",
                                     "scripts", "tests", "docs", "config")},
            "packages": {
                "mypkg": {
                    "files": ["packages/mypkg/README.md"],
                    "current_version": "1.0.0",
                    "cos_package_yaml": None,
                },
            },
        }
        result = a.determine_version_bumps(classified)
        assert result["packages"]["mypkg"]["recommended_bump"] == "patch"
        assert result["packages"]["mypkg"]["new_version"] == "1.0.1"

    def test_bump_package_minor_new_features(self, tmp_path):
        a = self._make_analyzer(tmp_path)
        classified = {
            "core": {k: [] for k in ("libs", "hooks", "rules", "templates",
                                     "scripts", "tests", "docs", "config")},
            "packages": {
                "mypkg": {
                    "files": ["packages/mypkg/hooks/new-hook.sh",
                              "packages/mypkg/README.md"],
                    "current_version": "1.0.0",
                    "cos_package_yaml": None,
                },
            },
        }
        result = a.determine_version_bumps(classified)
        assert result["packages"]["mypkg"]["recommended_bump"] == "minor"
        assert result["packages"]["mypkg"]["new_version"] == "1.1.0"

    def test_bump_package_test_only_skipped(self, tmp_path):
        a = self._make_analyzer(tmp_path)
        classified = {
            "core": {k: [] for k in ("libs", "hooks", "rules", "templates",
                                     "scripts", "tests", "docs", "config")},
            "packages": {
                "mypkg": {
                    "files": ["packages/mypkg/tests/test_foo.py"],
                    "current_version": "1.0.0",
                    "cos_package_yaml": None,
                },
            },
        }
        result = a.determine_version_bumps(classified)
        assert result["packages"]["mypkg"]["needs_release"] is False


# ---------------------------------------------------------------------------
# release order
# ---------------------------------------------------------------------------

class TestReleaseOrder:
    def test_release_order_packages_first(self, tmp_path):
        """Packages always appear before core in release_order."""
        pkg_dir = tmp_path / "packages" / "alpha"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "cos-package.yaml").write_text('version: "1.0.0"\n')

        a = ReleaseAnalyzer(str(tmp_path))
        a.read_core_version = lambda: "0.8.7"

        # Mock get_changes_since_tag to return controlled data
        with patch.object(a, "get_changes_since_tag", return_value={
            "commits": 5,
            "files_changed": 4,
            "insertions": 100,
            "deletions": 10,
            "files": ["lib/foo.py", "packages/alpha/SKILL.md"],
        }):
            plan = a.generate_release_plan(tag="v0.8.7")

        types = [r["type"] for r in plan["release_order"]]
        if "package" in types and "core" in types:
            assert types.index("package") < types.index("core")

    def test_no_packages_only_core(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        a.read_core_version = lambda: "0.8.7"

        with patch.object(a, "get_changes_since_tag", return_value={
            "commits": 3,
            "files_changed": 2,
            "insertions": 50,
            "deletions": 5,
            "files": ["lib/foo.py"],
        }):
            plan = a.generate_release_plan(tag="v0.8.7")

        assert plan["core"]["needs_release"] is True
        assert any(r["type"] == "core" for r in plan["release_order"])


# ---------------------------------------------------------------------------
# format_release_report
# ---------------------------------------------------------------------------

class TestFormatReport:
    def test_format_report_structure(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        a.read_core_version = lambda: "0.8.7"

        with patch.object(a, "get_changes_since_tag", return_value={
            "commits": 41,
            "files_changed": 183,
            "insertions": 23000,
            "deletions": 2000,
            "files": ["lib/foo.py", "hooks/bar.sh", "rules/my.md"],
        }):
            plan = a.generate_release_plan(tag="v0.8.7")

        report = a.format_release_report(plan)
        assert "=== RELEASE PLAN ===" in report
        assert "v0.8.7" in report
        assert "41 commits" in report
        assert "183 files" in report
        assert "CORE:" in report
        assert "PACKAGES" in report
        assert "====================" in report

    def test_format_report_no_releases(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        a.read_core_version = lambda: "0.8.7"

        with patch.object(a, "get_changes_since_tag", return_value={
            "commits": 1, "files_changed": 1, "insertions": 5, "deletions": 0,
            "files": ["tests/unit/test_foo.py"],
        }):
            plan = a.generate_release_plan(tag="v0.8.7")

        report = a.format_release_report(plan)
        assert "no release needed" in report.lower()


# ---------------------------------------------------------------------------
# changelog generation
# ---------------------------------------------------------------------------

class TestGenerateChangelog:
    def test_generate_changelog_groups_by_type(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        fake_log = "\n".join([
            "feat(lib): add new analyzer",
            "fix: repair broken hook",
            "chore: update deps",
            "docs: improve readme",
            "test: add unit tests",
        ])
        with patch("lib.release_analyzer._run", return_value=fake_log):
            changelog = a.generate_changelog(tag="v0.8.7")

        assert "### Features" in changelog
        assert "add new analyzer" in changelog
        assert "### Bug Fixes" in changelog
        assert "repair broken hook" in changelog
        assert "### Chores" in changelog
        assert "update deps" in changelog
        assert "### Documentation" in changelog

    def test_changelog_empty_log(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        with patch("lib.release_analyzer._run", return_value=""):
            changelog = a.generate_changelog(tag="v0.8.7")
        assert "## Changelog" in changelog


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_changes(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        a.read_core_version = lambda: "0.8.7"

        with patch.object(a, "get_changes_since_tag", return_value={
            "commits": 0, "files_changed": 0, "insertions": 0, "deletions": 0,
            "files": [],
        }):
            plan = a.generate_release_plan(tag="v0.8.7")

        assert plan["summary"]["total_releases_needed"] == 0
        assert plan["release_order"] == []

    def test_plan_summary_counts(self, tmp_path):
        pkg_dir = tmp_path / "packages" / "pkg1"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "cos-package.yaml").write_text('version: "1.0.0"\n')

        a = ReleaseAnalyzer(str(tmp_path))
        a.read_core_version = lambda: "0.8.7"

        with patch.object(a, "get_changes_since_tag", return_value={
            "commits": 10,
            "files_changed": 5,
            "insertions": 100,
            "deletions": 10,
            "files": ["lib/new.py", "packages/pkg1/hooks/run.sh"],
        }):
            plan = a.generate_release_plan(tag="v0.8.7")

        assert plan["summary"]["total_releases_needed"] >= 1
        assert isinstance(plan["summary"]["package_releases"], int)
        assert isinstance(plan["summary"]["core_release"], bool)

    def test_read_core_version_from_yaml(self, tmp_path):
        """read_core_version reads from cognitive-os.yaml when present."""
        yaml_file = tmp_path / "cognitive-os.yaml"
        yaml_file.write_text("version: '1.2.3'\n")
        a = ReleaseAnalyzer(str(tmp_path))
        with patch.object(a, "get_last_tag", return_value="v0.0.1"):
            v = a.read_core_version()
        assert v == "1.2.3"

    def test_read_core_version_from_tag(self, tmp_path):
        """read_core_version falls back to git tag when no yaml version."""
        yaml_file = tmp_path / "cognitive-os.yaml"
        yaml_file.write_text("project:\n  name: test\n")
        a = ReleaseAnalyzer(str(tmp_path))
        with patch.object(a, "get_last_tag", return_value="v0.8.7"):
            v = a.read_core_version()
        assert v == "0.8.7"

    def test_read_package_version(self, tmp_path):
        pkg_dir = tmp_path / "packages" / "mypkg"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "cos-package.yaml").write_text('version: "2.3.4"\n')
        a = ReleaseAnalyzer(str(tmp_path))
        assert a.read_package_version("mypkg") == "2.3.4"

    def test_read_package_version_missing(self, tmp_path):
        a = ReleaseAnalyzer(str(tmp_path))
        assert a.read_package_version("nonexistent") is None
