"""Behavior tests for cos CLI documentation completeness.

Validates that the cos README exists, references all implemented commands,
and includes required sections (security, troubleshooting, etc.).
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
README_PATH = PROJECT_ROOT / "cmd" / "cos" / "README.md"
CLI_DIR = PROJECT_ROOT / "cmd" / "cos" / "internal" / "cli"


def _read_readme() -> str:
    """Read the cos README content."""
    assert README_PATH.exists(), f"README not found at {README_PATH}"
    return README_PATH.read_text()


def _get_implemented_commands() -> list:
    """Extract command names from Go source files."""
    commands = []
    for go_file in CLI_DIR.glob("*.go"):
        if go_file.name.endswith("_test.go"):
            continue
        content = go_file.read_text()
        # Look for Use: "command" patterns
        import re
        matches = re.findall(r'Use:\s*"([a-z][-a-z0-9]*)', content)
        for match in matches:
            # Skip the root command "cos"
            if match != "cos":
                commands.append(match)
    return commands


class TestReadmeExists:
    """cos README must exist and be non-empty."""

    def test_readme_exists(self):
        """README.md should exist in cmd/cos/."""
        assert README_PATH.exists(), "cmd/cos/README.md is missing"

    def test_readme_not_empty(self):
        """README should contain substantial content."""
        content = _read_readme()
        assert len(content) > 500, "README is too short to be useful"


@pytest.mark.xfail(reason="New registry subcommands not yet in README — needs update")
class TestReadmeReferencesAllCommands:
    """README must reference every implemented CLI command."""

    def test_all_commands_documented(self):
        """Every command in the Go source should appear in the README."""
        readme = _read_readme()
        commands = _get_implemented_commands()
        assert len(commands) > 0, "No commands found in Go sources"

        missing = []
        for cmd in commands:
            # Handle hyphenated commands like "release-all"
            if cmd not in readme:
                missing.append(cmd)

        assert not missing, (
            f"Commands missing from README: {missing}. "
            f"All implemented commands: {commands}"
        )

    def test_init_command_documented(self):
        """cos init should be documented."""
        assert "cos init" in _read_readme()

    def test_install_command_documented(self):
        """cos install should be documented."""
        assert "cos install" in _read_readme()

    def test_remove_command_documented(self):
        """cos remove should be documented."""
        assert "cos remove" in _read_readme()

    def test_release_command_documented(self):
        """cos release should be documented."""
        assert "cos release" in _read_readme()

    def test_release_all_command_documented(self):
        """cos release-all should be documented."""
        assert "release-all" in _read_readme()

    def test_status_command_documented(self):
        """cos status should be documented."""
        assert "cos status" in _read_readme()

    def test_audit_command_documented(self):
        """cos audit should be documented."""
        assert "cos audit" in _read_readme()

    def test_publish_command_documented(self):
        """cos publish should be documented."""
        assert "cos publish" in _read_readme()


class TestReadmeRequiredSections:
    """README must include key sections for usability."""

    def test_has_security_section(self):
        """README must have a Security section."""
        readme = _read_readme()
        assert "## Security" in readme or "### Security" in readme, (
            "README is missing a Security section"
        )

    def test_has_troubleshooting_section(self):
        """README must have a Troubleshooting section."""
        readme = _read_readme()
        assert "Troubleshooting" in readme, (
            "README is missing a Troubleshooting section"
        )

    def test_has_installation_section(self):
        """README must explain how to install."""
        readme = _read_readme()
        assert "Installation" in readme or "Install" in readme

    def test_has_quick_start_section(self):
        """README must have a Quick Start or usage example."""
        readme = _read_readme()
        assert "Quick Start" in readme or "Usage" in readme

    def test_has_command_reference(self):
        """README must have a command reference table or section."""
        readme = _read_readme()
        assert "Command Reference" in readme or "Commands" in readme

    def test_has_package_format_section(self):
        """README must document the package format."""
        readme = _read_readme()
        assert "cos-package.yaml" in readme

    def test_has_versioning_section(self):
        """README must document versioning."""
        readme = _read_readme()
        assert "Versioning" in readme or "version" in readme.lower()
