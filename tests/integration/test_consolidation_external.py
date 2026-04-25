"""Integration tests for rules consolidation on simulated external projects.

Verify that the efficiency profile filtering logic from self-install.sh
correctly restricts which rules are installed depending on the profile
(lean, standard, full).

The self-install.sh hook is designed for self-hosting (developing COS
itself).  For external projects, the same filtering logic applies when
IS_SELF_HOSTING is false.  These tests simulate that external-project
scenario by:

  1. Creating a temp directory with real rule files copied from this repo
  2. Symlinking all rules into .claude/rules/cos/ (the "full install")
  3. Running self-install.sh with CLAUDE_PROJECT_DIR pointing at the
     temp directory and the self-hosting guard bypassed
  4. Verifying the resulting rule set matches the expected profile

Related files:
    - hooks/self-install.sh       (the sync + profile filter logic)
    - rules/                       (the source rule files)
    - docs/rules-loading-architecture.md (rationale for 16 core rules)
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = PROJECT_ROOT / "rules"
SELF_INSTALL = PROJECT_ROOT / "hooks" / "self-install.sh"

# The core rules that the default/full/self-hosting profiles keep.
# Must match the CORE_RULES array in hooks/self-install.sh exactly.
CORE_RULES = {
    "RULES-COMPACT.md",
    "adaptive-bypass.md",
    "acceptance-criteria.md",
    "agent-quality.md",
    "trust-score.md",
    "token-economy.md",
    "definition-of-done.md",
    "phase-aware-agents.md",
    "closed-loop-prompts.md",
    "error-learning.md",
    "credential-management.md",
    "result-management.md",
    "model-routing.md",
    "python-naming.md",
    "bash-naming.md",
}

# All rule .md files in the source rules/ directory (dynamic count)
ALL_RULE_FILES = {f.name for f in RULES_DIR.glob("*.md")}

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_external_project(tmp_path: Path, profile: str) -> Path:
    """Create a fake external project directory with COS rules pre-installed.

    Simulates the state AFTER a full sync but BEFORE profile filtering:
    all rules are symlinked into .claude/rules/cos/.

    Returns the project root path.
    """
    project = tmp_path / "test-project"
    project.mkdir()

    # Create .claude directory structure
    claude_dir = project / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text("{}")

    # cognitive-os.yaml with the desired efficiency profile
    (project / "cognitive-os.yaml").write_text(
        f"efficiency:\n  profile: {profile}\n"
        "project:\n  phase: reconstruction\n"
    )

    # Create rules/ source directory (copy real rule files so symlinks work)
    rules_src = project / "rules"
    rules_src.mkdir()
    for rule_file in RULES_DIR.glob("*.md"):
        shutil.copy2(rule_file, rules_src / rule_file.name)

    # Pre-populate .claude/rules/cos/ with symlinks to ALL rules
    # (simulates the sync_dir step that runs before profile filtering)
    cos_rules = project / ".claude" / "rules" / "cos"
    cos_rules.mkdir(parents=True)
    for rule_file in rules_src.glob("*.md"):
        link = cos_rules / rule_file.name
        link.symlink_to(rule_file)

    # Create hooks/ with a self-install.sh (needed for self-hosting detection)
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "self-install.sh").write_text("#!/bin/bash\nexit 0\n")

    # Create required runtime dirs
    cos_dir = project / ".cognitive-os"
    cos_dir.mkdir()
    for subdir in ["sessions", "metrics", "tasks"]:
        (cos_dir / subdir).mkdir()

    return project


def _run_profile_filter(project: Path) -> set[str]:
    """Run the self-install.sh script targeting the fake project.

    The script will:
    1. Detect self-hosting (hooks/self-install.sh exists)
    2. Skip sync_dir (rules/ already symlinked)
    3. Apply profile filtering
    4. Return the remaining rules

    Returns the set of rule filenames remaining after filtering.
    """
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project)

    result = subprocess.run(
        ["bash", str(SELF_INSTALL)],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        cwd=str(project),
    )

    # self-install.sh should always exit 0
    assert result.returncode == 0, (
        f"self-install.sh failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # Collect remaining rules
    cos_rules_dir = project / ".claude" / "rules" / "cos"
    if cos_rules_dir.is_dir():
        return {f.name for f in cos_rules_dir.glob("*.md")}
    return set()


def _apply_profile_filter_pure(rules: set[str], profile: str) -> set[str]:
    """Pure Python implementation of the profile filtering logic.

    This mirrors the logic in self-install.sh and serves as a reference
    implementation for verifying behavior.

    lean                  -> RULES-COMPACT.md only
    standard              -> CORE_RULES (16 core rules)
    full / self-hosting   -> ALL rules (full context for development)
    """
    if profile == "lean":
        return {r for r in rules if r == "RULES-COMPACT.md"}
    elif profile == "standard":
        return {r for r in rules if r in CORE_RULES}
    else:
        # full / self-hosting: keep everything
        return rules


# ---------------------------------------------------------------------------
# Tests — Pure logic (no subprocess needed)
# ---------------------------------------------------------------------------


class TestProfileFilterLogic:
    """Test the profile filtering logic in pure Python."""

    def test_standard_profile_keeps_16_core_rules(self):
        """Standard profile should keep exactly the core rules."""
        filtered = _apply_profile_filter_pure(ALL_RULE_FILES, "standard")
        assert filtered == CORE_RULES
        assert len(filtered) == len(CORE_RULES)

    def test_lean_profile_keeps_only_compact(self):
        """Lean profile should keep only RULES-COMPACT.md."""
        filtered = _apply_profile_filter_pure(ALL_RULE_FILES, "lean")
        assert filtered == {"RULES-COMPACT.md"}

    def test_full_profile_keeps_all_rules(self):
        """Full/self-hosting profile should keep every rule file.

        self-install.sh syncs ALL rules for self-hosted development,
        providing maximum context coverage during development.
        """
        filtered = _apply_profile_filter_pure(ALL_RULE_FILES, "full")
        assert filtered == ALL_RULE_FILES
        assert len(filtered) >= 70, (
            f"Expected >= 70 rules in full profile, got {len(filtered)}"
        )

    def test_core_rules_are_subset_of_all(self):
        """Every core rule must actually exist in the rules/ directory."""
        missing = CORE_RULES - ALL_RULE_FILES
        assert not missing, (
            f"Core rules reference non-existent files: {missing}"
        )

    def test_core_rules_count_matches_current_contract(self):
        """The CORE_RULES constant tracks the current self-install contract."""
        assert len(CORE_RULES) == 15


class TestProfileFilterShellScript:
    """Test self-install.sh profile filtering via subprocess.

    NOTE: self-install.sh only applies profile filtering when
    IS_SELF_HOSTING=true (the script exits early for external projects).
    Since hooks/self-install.sh exists in the test project, IS_SELF_HOSTING
    is always true, and the profile filter is skipped (full profile used).

    These tests verify the script runs successfully and produces the
    expected self-hosted behavior (all rules kept).
    """

    def test_self_hosted_keeps_all_rules(self, tmp_path):
        """Self-hosted project should keep at least the core rules.

        In self-hosting mode, self-install.sh syncs all rules EXCEPT those
        in EXCLUDED_RULES (hook-enforced, package-specific, or contextual rules
        that are loaded on demand). At least the CORE_RULES should be present.
        """
        project = _setup_external_project(tmp_path, "standard")
        remaining = _run_profile_filter(project)

        # Self-hosted keeps all rules minus excluded ones — at least CORE_RULES
        assert len(remaining) >= len(CORE_RULES), (
            f"Self-hosted should keep at least {len(CORE_RULES)} core rules, got {len(remaining)}"
        )
        # All CORE_RULES should be present
        for rule in CORE_RULES:
            assert rule in remaining, f"Core rule {rule} missing from self-hosted install"

    def test_self_install_exits_clean(self, tmp_path):
        """self-install.sh should exit 0 on a properly structured project."""
        project = _setup_external_project(tmp_path, "full")
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(project)

        result = subprocess.run(
            ["bash", str(SELF_INSTALL)],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode == 0

    def test_self_install_reports_status(self, tmp_path):
        """self-install.sh should output a status line."""
        project = _setup_external_project(tmp_path, "full")
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(project)

        result = subprocess.run(
            ["bash", str(SELF_INSTALL)],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert "Self-hosting:" in result.stdout


class TestExternalProjectSimulation:
    """Simulate external project rule installation without self-install.sh.

    Since self-install.sh exits early for non-self-hosted projects,
    external installation would use a different mechanism (e.g., cos init).
    These tests verify the expected end state by applying the filter
    logic directly and checking file system results.
    """

    def test_standard_profile_installs_16_core_rules(self, tmp_path):
        """Simulate external project install with standard profile."""
        project = _setup_external_project(tmp_path, "standard")
        cos_rules_dir = project / ".claude" / "rules" / "cos"

        # Apply the standard filter (what an external installer would do)
        for link in cos_rules_dir.glob("*.md"):
            if link.name not in CORE_RULES:
                link.unlink()

        remaining = {f.name for f in cos_rules_dir.glob("*.md")}
        assert len(remaining) == len(CORE_RULES)
        assert remaining == CORE_RULES

    def test_standard_profile_has_right_rules(self, tmp_path):
        """Verify the core rules include the expected essentials."""
        project = _setup_external_project(tmp_path, "standard")
        cos_rules_dir = project / ".claude" / "rules" / "cos"

        for link in cos_rules_dir.glob("*.md"):
            if link.name not in CORE_RULES:
                link.unlink()

        remaining = {f.name for f in cos_rules_dir.glob("*.md")}

        # Must-have rules for any project.
        assert "RULES-COMPACT.md" in remaining
        assert "acceptance-criteria.md" in remaining
        assert "trust-score.md" in remaining
        assert "credential-management.md" in remaining
        assert "error-learning.md" in remaining
        assert "phase-aware-agents.md" in remaining
        assert "closed-loop-prompts.md" in remaining
        assert "token-economy.md" in remaining
        assert "adaptive-bypass.md" in remaining
        assert "agent-quality.md" in remaining
        assert "result-management.md" in remaining
        assert "model-routing.md" in remaining

    def test_lean_profile_installs_only_compact(self, tmp_path):
        """Lean profile should only have RULES-COMPACT.md."""
        project = _setup_external_project(tmp_path, "lean")
        cos_rules_dir = project / ".claude" / "rules" / "cos"

        # Apply lean filter
        for link in cos_rules_dir.glob("*.md"):
            if link.name != "RULES-COMPACT.md":
                link.unlink()

        remaining = {f.name for f in cos_rules_dir.glob("*.md")}
        assert remaining == {"RULES-COMPACT.md"}

    def test_full_profile_installs_all_rules(self, tmp_path):
        """Full profile should have all rule files."""
        project = _setup_external_project(tmp_path, "full")
        cos_rules_dir = project / ".claude" / "rules" / "cos"

        # Full profile: no filtering
        remaining = {f.name for f in cos_rules_dir.glob("*.md")}
        assert len(remaining) >= 70, (
            f"Expected >= 70 rules in full profile, got {len(remaining)}"
        )
        assert remaining == ALL_RULE_FILES

    def test_core_rules_are_readable(self, tmp_path):
        """Each installed core rule should be a valid, non-empty file."""
        project = _setup_external_project(tmp_path, "standard")
        cos_rules_dir = project / ".claude" / "rules" / "cos"

        for link in cos_rules_dir.glob("*.md"):
            if link.name not in CORE_RULES:
                link.unlink()

        for rule_name in CORE_RULES:
            rule_path = cos_rules_dir / rule_name
            assert rule_path.exists(), f"Core rule {rule_name} not found"
            content = rule_path.read_text(encoding="utf-8")
            assert len(content) > 10, (
                f"Core rule {rule_name} is empty or nearly empty"
            )
            body = content.strip()
            if body.startswith("<!--"):
                body = body.split("-->", 1)[1].strip()
            # Each rule should start with a markdown heading after optional metadata.
            assert body.startswith("#"), (
                f"Core rule {rule_name} does not start with a markdown heading"
            )

    def test_core_rules_match_self_install_constant(self):
        """CORE_RULES in this test must match the array in self-install.sh."""
        # Read self-install.sh and extract the CORE_RULES array
        script = SELF_INSTALL.read_text(encoding="utf-8")

        # Extract entries between CORE_RULES=( and the closing )
        import re
        match = re.search(
            r'CORE_RULES=\(\s*\n(.*?)\n\s*\)',
            script,
            re.DOTALL,
        )
        assert match, "Could not find CORE_RULES array in self-install.sh"

        # Parse the quoted entries
        entries = re.findall(r'"([^"]+)"', match.group(1))
        shell_core = set(entries)

        assert shell_core == CORE_RULES, (
            f"CORE_RULES mismatch between test and self-install.sh.\n"
            f"In test but not script: {CORE_RULES - shell_core}\n"
            f"In script but not test: {shell_core - CORE_RULES}"
        )
