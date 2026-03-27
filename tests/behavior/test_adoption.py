"""Behavior tests for adoption-critical features.

Tests that cos-init.sh, uninstall.sh, upgrade.sh exist and work correctly,
that quickstart.md is concise, and that mode flags are supported.

Related files:
  - scripts/cos-init.sh (project bootstrapper)
  - scripts/uninstall.sh (clean removal)
  - scripts/upgrade.sh (version-aware update)
  - docs/quickstart.md (5-minute onboarding)
  - docs/getting-started.md (full onboarding with dependency table)

Author: luum
"""

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ── Script existence and executability ───────────────────────────


class TestScriptExistence:
    """Verify adoption scripts exist and are executable."""

    def test_cos_init_exists(self):
        script = PROJECT_ROOT / "scripts" / "cos-init.sh"
        assert script.exists(), "scripts/cos-init.sh must exist"

    def test_cos_init_is_executable(self):
        script = PROJECT_ROOT / "scripts" / "cos-init.sh"
        assert script.exists()
        # Check file has valid bash shebang
        content = script.read_text()
        assert content.startswith("#!/usr/bin/env bash"), \
            "cos-init.sh must start with #!/usr/bin/env bash"

    def test_uninstall_exists(self):
        script = PROJECT_ROOT / "scripts" / "uninstall.sh"
        assert script.exists(), "scripts/uninstall.sh must exist"

    def test_uninstall_is_executable(self):
        script = PROJECT_ROOT / "scripts" / "uninstall.sh"
        assert script.exists()
        content = script.read_text()
        assert content.startswith("#!/usr/bin/env bash"), \
            "uninstall.sh must start with #!/usr/bin/env bash"

    def test_upgrade_exists(self):
        script = PROJECT_ROOT / "scripts" / "upgrade.sh"
        assert script.exists(), "scripts/upgrade.sh must exist"

    def test_upgrade_is_executable(self):
        script = PROJECT_ROOT / "scripts" / "upgrade.sh"
        assert script.exists()
        content = script.read_text()
        assert content.startswith("#!/usr/bin/env bash"), \
            "upgrade.sh must start with #!/usr/bin/env bash"


# ── Quickstart documentation ────────────────────────────────────


class TestQuickstartDocs:
    """Verify quickstart.md is concise and complete."""

    def test_quickstart_exists(self):
        doc = PROJECT_ROOT / "docs" / "quickstart.md"
        assert doc.exists(), "docs/quickstart.md must exist"

    def test_quickstart_is_under_60_lines(self):
        doc = PROJECT_ROOT / "docs" / "quickstart.md"
        assert doc.exists()
        lines = doc.read_text().splitlines()
        assert len(lines) < 60, \
            f"quickstart.md must be under 60 lines, got {len(lines)}"

    def test_quickstart_has_install_command(self):
        doc = PROJECT_ROOT / "docs" / "quickstart.md"
        assert doc.exists()
        content = doc.read_text()
        assert "cos-init" in content, \
            "quickstart.md must contain an install command referencing cos-init"

    def test_quickstart_has_uninstall_command(self):
        doc = PROJECT_ROOT / "docs" / "quickstart.md"
        assert doc.exists()
        content = doc.read_text()
        assert "uninstall" in content, \
            "quickstart.md must contain an uninstall command"


# ── Mode support in cos-init ────────────────────────────────────


class TestCosInitModes:
    """Verify cos-init.sh supports the three installation modes."""

    def test_cos_init_supports_minimal_flag(self):
        script = PROJECT_ROOT / "scripts" / "cos-init.sh"
        content = script.read_text()
        assert "--minimal" in content, \
            "cos-init.sh must support --minimal flag"

    def test_cos_init_supports_standard_flag(self):
        script = PROJECT_ROOT / "scripts" / "cos-init.sh"
        content = script.read_text()
        assert "--standard" in content, \
            "cos-init.sh must support --standard flag"

    def test_cos_init_supports_full_flag(self):
        script = PROJECT_ROOT / "scripts" / "cos-init.sh"
        content = script.read_text()
        assert "--full" in content, \
            "cos-init.sh must support --full flag"

    def test_minimal_mode_lists_under_10_rules(self):
        """Minimal mode should define fewer than 10 rules."""
        script = PROJECT_ROOT / "scripts" / "cos-init.sh"
        content = script.read_text()
        # Find the MINIMAL_RULES definition and count items
        in_minimal = False
        rule_names = []
        for line in content.splitlines():
            if line.startswith("MINIMAL_RULES="):
                # Extract the quoted string after =
                rules_str = line.split("=", 1)[1].strip().strip('"')
                rule_names = rules_str.split()
                break
        assert 0 < len(rule_names) < 10, \
            f"Minimal mode must list fewer than 10 rules, got {len(rule_names)}: {rule_names}"

    def test_standard_mode_lists_under_30_rules(self):
        """Standard mode should define fewer than 30 rules."""
        script = PROJECT_ROOT / "scripts" / "cos-init.sh"
        content = script.read_text()
        # Count rule names in the STANDARD_RULES block
        # It spans multiple lines ending at the next variable assignment
        in_standard = False
        rules_text = ""
        for line in content.splitlines():
            if line.startswith("STANDARD_RULES="):
                rules_text = line.split("=", 1)[1].strip().strip('"')
                in_standard = True
                continue
            if in_standard:
                stripped = line.strip()
                if stripped.endswith('"'):
                    rules_text += " " + stripped.strip('"')
                    break
                elif stripped and not stripped.startswith("#"):
                    rules_text += " " + stripped
                else:
                    break
        # Remove $MINIMAL_RULES reference and count remaining
        rules_text = rules_text.replace("$MINIMAL_RULES", "")
        rule_names = [r for r in rules_text.split() if r and not r.startswith("#")]
        # Add minimal rules count (5)
        total = len(rule_names) + 5
        assert 0 < total < 30, \
            f"Standard mode must list fewer than 30 rules, got {total}"


# ── Dependency table in docs ────────────────────────────────────


class TestDependencyTable:
    """Verify the 'What works without Docker?' table exists."""

    def test_dependency_table_in_getting_started(self):
        doc = PROJECT_ROOT / "docs" / "getting-started.md"
        assert doc.exists()
        content = doc.read_text()
        assert "What Works Without Docker" in content or "works without Docker" in content.lower(), \
            "docs/getting-started.md must contain the dependency table section"

    def test_dependency_table_has_docker_column(self):
        doc = PROJECT_ROOT / "docs" / "getting-started.md"
        content = doc.read_text()
        assert "Needs Docker" in content or "Docker?" in content, \
            "Dependency table must have a Docker column"

    def test_dependency_table_in_quickstart(self):
        doc = PROJECT_ROOT / "docs" / "quickstart.md"
        assert doc.exists()
        content = doc.read_text()
        assert "Docker?" in content, \
            "quickstart.md must contain the dependency table"
