"""Tests for the versioning system.

Validates that VERSION file exists, follows semver, and is consistent
across all locations (VERSION, Go CLI sources, docs/INDEX.md, CHANGELOG.md).
"""

import re
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestVersionFile:
    """Tests for the VERSION file."""

    def test_version_file_exists(self):
        """VERSION file must exist at project root."""
        version_file = PROJECT_ROOT / "VERSION"
        assert version_file.exists(), "VERSION file not found at project root"

    def test_version_is_not_empty(self):
        """VERSION file must not be empty."""
        version_file = PROJECT_ROOT / "VERSION"
        content = version_file.read_text().strip()
        assert len(content) > 0, "VERSION file is empty"

    def test_version_is_valid_semver(self):
        """VERSION must contain a valid semver string (X.Y.Z)."""
        version_file = PROJECT_ROOT / "VERSION"
        version = version_file.read_text().strip()
        assert re.match(
            r"^\d+\.\d+\.\d+$", version
        ), f"VERSION '{version}' is not valid semver (expected X.Y.Z)"


class TestChangelog:
    """Tests for the CHANGELOG.md file."""

    def test_changelog_exists(self):
        """CHANGELOG.md must exist at project root."""
        changelog = PROJECT_ROOT / "CHANGELOG.md"
        assert changelog.exists(), "CHANGELOG.md not found at project root"

    def test_changelog_has_current_version_entry(self):
        """CHANGELOG must have an entry for the current VERSION."""
        version = (PROJECT_ROOT / "VERSION").read_text().strip()
        changelog_content = (PROJECT_ROOT / "CHANGELOG.md").read_text()
        assert (
            f"## [{version}]" in changelog_content
        ), f"CHANGELOG.md missing entry for version [{version}]"

    def test_changelog_follows_keepachangelog_format(self):
        """CHANGELOG should reference Keep a Changelog format."""
        changelog_content = (PROJECT_ROOT / "CHANGELOG.md").read_text()
        assert (
            "keepachangelog" in changelog_content.lower()
        ), "CHANGELOG.md should reference Keep a Changelog format"

    def test_changelog_has_heading(self):
        """CHANGELOG must start with a heading."""
        changelog_content = (PROJECT_ROOT / "CHANGELOG.md").read_text()
        assert changelog_content.startswith(
            "# "
        ), "CHANGELOG.md should start with a markdown heading"


class TestVersionScript:
    """Tests for the version management script."""

    def test_version_script_exists(self):
        """scripts/version.sh must exist."""
        script = PROJECT_ROOT / "scripts" / "version.sh"
        assert script.exists(), "scripts/version.sh not found"

    def test_version_script_is_executable(self):
        """scripts/version.sh must be executable."""
        script = PROJECT_ROOT / "scripts" / "version.sh"
        assert script.exists(), "scripts/version.sh not found"
        # Check that the file has a proper shebang
        content = script.read_text()
        assert content.startswith("#!/"), "scripts/version.sh missing shebang"


class TestVersionConsistency:
    """Tests for version consistency across all locations."""

    def _get_version(self) -> str:
        return (PROJECT_ROOT / "VERSION").read_text().strip()

    def test_cos_cli_version_matches(self):
        """cos CLI version must match VERSION file."""
        version = self._get_version()
        root_go = (
            PROJECT_ROOT / "cmd" / "cos" / "internal" / "cli" / "root.go"
        )
        if not root_go.exists():
            pytest.skip("cmd/cos/internal/cli/root.go not found")
        content = root_go.read_text()
        assert (
            f'Version: "{version}"' in content
        ), f"cos CLI version does not match VERSION file ({version})"

    def test_cos_test_cli_version_matches(self):
        """cos-test CLI version must match VERSION file."""
        version = self._get_version()
        root_go = (
            PROJECT_ROOT / "cmd" / "cos-test" / "internal" / "cli" / "root.go"
        )
        if not root_go.exists():
            pytest.skip("cmd/cos-test/internal/cli/root.go not found")
        content = root_go.read_text()
        assert (
            f'Version: "{version}"' in content
        ), f"cos-test CLI version does not match VERSION file ({version})"

    def test_docs_index_contains_version(self):
        """docs/INDEX.md must contain the current version."""
        version = self._get_version()
        index_md = PROJECT_ROOT / "docs" / "INDEX.md"
        if not index_md.exists():
            pytest.skip("docs/INDEX.md not found")
        content = index_md.read_text()
        assert (
            f"v{version}" in content
        ), f"docs/INDEX.md does not contain 'v{version}'"

    def test_version_is_consistent_across_all_locations(self):
        """All version locations must report the same version."""
        version = self._get_version()
        locations_checked = ["VERSION"]
        mismatches = []

        # cos CLI
        cos_go = PROJECT_ROOT / "cmd" / "cos" / "internal" / "cli" / "root.go"
        if cos_go.exists():
            content = cos_go.read_text()
            match = re.search(r'Version:\s*"([^"]+)"', content)
            if match:
                locations_checked.append("cmd/cos root.go")
                if match.group(1) != version:
                    mismatches.append(
                        f"cmd/cos root.go has {match.group(1)}"
                    )

        # cos-test CLI
        costest_go = (
            PROJECT_ROOT / "cmd" / "cos-test" / "internal" / "cli" / "root.go"
        )
        if costest_go.exists():
            content = costest_go.read_text()
            match = re.search(r'Version:\s*"([^"]+)"', content)
            if match:
                locations_checked.append("cmd/cos-test root.go")
                if match.group(1) != version:
                    mismatches.append(
                        f"cmd/cos-test root.go has {match.group(1)}"
                    )

        # docs/INDEX.md
        index_md = PROJECT_ROOT / "docs" / "INDEX.md"
        if index_md.exists():
            content = index_md.read_text()
            locations_checked.append("docs/INDEX.md")
            if f"v{version}" not in content:
                mismatches.append("docs/INDEX.md missing version")

        assert (
            len(mismatches) == 0
        ), f"Version {version} inconsistent: {'; '.join(mismatches)} (checked: {', '.join(locations_checked)})"
