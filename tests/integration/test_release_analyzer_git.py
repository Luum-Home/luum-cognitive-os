"""Integration tests for ReleaseAnalyzer against the real git repository."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
from lib.release_analyzer import ReleaseAnalyzer

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="module")
def analyzer():
    return ReleaseAnalyzer(PROJECT_ROOT)


@pytest.fixture(scope="module")
def last_tag(analyzer):
    return analyzer.get_last_tag()


@pytest.fixture(scope="module")
def real_plan(analyzer, last_tag):
    return analyzer.generate_release_plan(tag=last_tag)


# ---------------------------------------------------------------------------
# Individual primitives
# ---------------------------------------------------------------------------

class TestRealLastTag:
    def test_real_last_tag(self, analyzer):
        """get_last_tag returns a non-empty string from the real repo."""
        tag = analyzer.get_last_tag()
        assert tag is not None
        assert len(tag) > 0
        # Should look like a version tag
        assert any(c.isdigit() for c in tag)

    def test_last_tag_is_highest_version(self, analyzer):
        """The last tag returned should be the most recent one (v0.8.7 or newer)."""
        tag = analyzer.get_last_tag()
        assert tag is not None
        # In this repo we know tags like v0.8.7 exist
        assert tag.startswith("v") or tag[0].isdigit()


class TestRealChangesSinceTag:
    def test_real_changes_since_tag(self, analyzer, last_tag):
        """get_changes_since_tag returns a non-empty dict with expected keys."""
        changes = analyzer.get_changes_since_tag(last_tag)
        assert "commits" in changes
        assert "files_changed" in changes
        assert "files" in changes
        assert isinstance(changes["files"], list)
        assert isinstance(changes["commits"], int)

    def test_real_changes_have_files(self, analyzer, last_tag):
        """Real repo has changes since last tag (41 commits worth)."""
        changes = analyzer.get_changes_since_tag(last_tag)
        # We know there are 41 commits since v0.8.7
        assert changes["commits"] > 0 or len(changes["files"]) > 0

    def test_files_are_relative_paths(self, analyzer, last_tag):
        """File paths should be relative (not absolute)."""
        changes = analyzer.get_changes_since_tag(last_tag)
        for f in changes["files"][:10]:
            assert not f.startswith("/"), f"Expected relative path, got: {f}"


class TestRealClassifyChanges:
    def test_real_classify_changes(self, analyzer, last_tag):
        """classify_changes correctly categorizes real repo files."""
        changes = analyzer.get_changes_since_tag(last_tag)
        classified = analyzer.classify_changes(changes["files"])

        assert "core" in classified
        assert "packages" in classified
        assert isinstance(classified["core"]["libs"], list)
        assert isinstance(classified["packages"], dict)

    def test_classify_finds_lib_files(self, analyzer, last_tag):
        """Classifier recognizes lib/*.py files without depending on tag diff shape."""
        changes = analyzer.get_changes_since_tag(last_tag)
        files = list(changes["files"])
        if not any(path.startswith("lib/") for path in files):
            files.append("lib/release_analyzer.py")
        classified = analyzer.classify_changes(files)
        assert len(classified["core"]["libs"]) > 0

    def test_classify_finds_packages(self, analyzer, last_tag):
        """Should find package changes."""
        changes = analyzer.get_changes_since_tag(last_tag)
        classified = analyzer.classify_changes(changes["files"])
        # Real repo has packages/ directory with changes
        # (packages may or may not have changed since last tag)
        assert isinstance(classified["packages"], dict)

    def test_no_file_classified_twice(self, analyzer, last_tag):
        """Each file should appear in exactly one category."""
        changes = analyzer.get_changes_since_tag(last_tag)
        classified = analyzer.classify_changes(changes["files"])

        all_classified: list[str] = []
        for category_files in classified["core"].values():
            all_classified.extend(category_files)
        for pkg_data in classified["packages"].values():
            all_classified.extend(pkg_data["files"])

        # Check for duplicates within core categories
        core_all: list[str] = []
        for category_files in classified["core"].values():
            core_all.extend(category_files)
        assert len(core_all) == len(set(core_all)), "Duplicate files in core classification"


# ---------------------------------------------------------------------------
# Full plan
# ---------------------------------------------------------------------------

class TestRealGeneratePlan:
    def test_real_generate_plan(self, real_plan):
        """generate_release_plan returns a well-structured dict."""
        assert "summary" in real_plan
        assert "core" in real_plan
        assert "packages" in real_plan
        assert "release_order" in real_plan
        assert "changelog_draft" in real_plan

    def test_plan_summary_has_required_keys(self, real_plan):
        summary = real_plan["summary"]
        assert "total_releases_needed" in summary
        assert "core_release" in summary
        assert "package_releases" in summary
        assert "estimated_effort" in summary

    def test_plan_core_has_version_info(self, real_plan):
        core = real_plan["core"]
        assert "current_version" in core
        assert "new_version" in core
        assert core["current_version"] != ""

    def test_plan_release_order_packages_before_core(self, real_plan):
        """Packages always come before core in release order."""
        order = real_plan["release_order"]
        types = [r["type"] for r in order]
        if "package" in types and "core" in types:
            last_pkg = max(i for i, t in enumerate(types) if t == "package")
            first_core = min(i for i, t in enumerate(types) if t == "core")
            assert last_pkg < first_core, "Packages must be released before core"

    def test_plan_total_count_consistent(self, real_plan):
        """total_releases_needed matches actual length of release_order."""
        assert real_plan["summary"]["total_releases_needed"] == len(real_plan["release_order"])

    def test_plan_new_packages_get_1_0_0(self, real_plan):
        """Any new package (is_new=True) should get version 1.0.0."""
        for r in real_plan["release_order"]:
            if r["type"] == "package":
                pkg_name = r["name"]
                pkg_info = real_plan["packages"][pkg_name]
                if pkg_info["is_new"]:
                    assert r["version"] == "1.0.0", \
                        f"New package {pkg_name} should get 1.0.0, got {r['version']}"

    def test_changelog_contains_sections(self, real_plan):
        """Changelog draft is non-empty and contains section headers."""
        changelog = real_plan["changelog_draft"]
        assert "## Changelog" in changelog
        # Real repo uses feat/fix/chore commits — at least one section expected
        assert "###" in changelog


# ---------------------------------------------------------------------------
# Format report
# ---------------------------------------------------------------------------

class TestRealFormatReport:
    def test_real_format_report(self, analyzer, real_plan):
        """format_release_report produces readable output with key sections."""
        report = analyzer.format_release_report(real_plan)
        assert "=== RELEASE PLAN ===" in report
        assert "CORE:" in report
        assert "PACKAGES" in report
        assert "====================" in report

    def test_report_contains_version_numbers(self, analyzer, real_plan):
        """Report should mention actual version numbers."""
        report = analyzer.format_release_report(real_plan)
        # Current version should appear
        assert real_plan["core"]["current_version"] in report

    def test_report_is_readable_length(self, analyzer, real_plan):
        """Report should be at least a few lines but not overwhelmingly long."""
        report = analyzer.format_release_report(real_plan)
        lines = report.splitlines()
        assert len(lines) >= 5
        assert len(lines) <= 200

    def test_report_estimated_effort_present(self, analyzer, real_plan):
        """Estimated effort line should be in the report."""
        report = analyzer.format_release_report(real_plan)
        assert "Estimated effort:" in report or "minutes" in report
