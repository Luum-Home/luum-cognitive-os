"""Tests for the Content Policy system.

Validates that:
- content-policy.yaml exists and has required sections
- content-policy hook exists and is valid bash
- hook is registered in settings.json
- rule file exists
- agent-preamble mentions content policy
- pre-commit-gate checks content policy
- no current violations exist in codebase (excluding policy/preamble files)
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ─── Config file tests ────────────────────────────────────────────────────────


class TestContentPolicyConfig:
    """Tests for .cognitive-os/content-policy.yaml."""

    @pytest.fixture
    def policy_path(self):
        return PROJECT_ROOT / ".cognitive-os" / "content-policy.yaml"

    def test_content_policy_yaml_exists(self, policy_path):
        """content-policy.yaml must exist."""
        assert policy_path.exists(), f"Missing: {policy_path}"

    def test_has_prohibited_terms_section(self, policy_path):
        """content-policy.yaml must have prohibited_terms section."""
        content = policy_path.read_text()
        assert "prohibited_terms:" in content, (
            "content-policy.yaml missing prohibited_terms section"
        )

    def test_has_prohibited_patterns_section(self, policy_path):
        """content-policy.yaml must have prohibited_patterns section."""
        content = policy_path.read_text()
        assert "prohibited_patterns:" in content, (
            "content-policy.yaml missing prohibited_patterns section"
        )

    def test_has_required_values_section(self, policy_path):
        """content-policy.yaml must have required_values section."""
        content = policy_path.read_text()
        assert "required_values:" in content, (
            "content-policy.yaml missing required_values section"
        )

    def test_has_content_rules_section(self, policy_path):
        """content-policy.yaml must have content_rules section."""
        content = policy_path.read_text()
        assert "content_rules:" in content, (
            "content-policy.yaml missing content_rules section"
        )


# ─── Hook tests ───────────────────────────────────────────────────────────────


class TestContentPolicyHook:
    """Tests for hooks/content-policy.sh."""

    @pytest.fixture
    def hook_path(self):
        return PROJECT_ROOT / "hooks" / "content-policy.sh"

    def test_hook_exists(self, hook_path):
        """content-policy.sh hook must exist."""
        assert hook_path.exists(), f"Missing: {hook_path}"

    def test_hook_is_valid_bash(self, hook_path):
        """content-policy.sh must be valid bash syntax."""
        result = subprocess.run(
            ["bash", "-n", str(hook_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Bash syntax error in content-policy.sh: {result.stderr}"
        )

    def test_hook_registered_in_settings(self):
        """content-policy.sh must be registered in .claude/settings.json."""
        settings_path = PROJECT_ROOT / ".claude" / "settings.json"
        assert settings_path.exists(), "Missing .claude/settings.json"

        settings = json.loads(settings_path.read_text())

        # Find the hook in PostToolUse with Edit|Write matcher
        post_hooks = settings.get("hooks", {}).get("PostToolUse", [])
        found = False
        for group in post_hooks:
            matcher = group.get("matcher", "")
            if "Edit" in matcher and "Write" in matcher:
                for hook in group.get("hooks", []):
                    cmd = hook.get("command", "")
                    if "content-policy.sh" in cmd:
                        found = True
                        break
            if found:
                break

        assert found, (
            "content-policy.sh not registered in settings.json "
            "under PostToolUse with Edit|Write matcher"
        )


# ─── Rule tests ───────────────────────────────────────────────────────────────


class TestContentPolicyRule:
    """Tests for rules/content-policy.md."""

    def test_rule_exists(self):
        """rules/content-policy.md must exist."""
        rule_path = PROJECT_ROOT / "rules" / "content-policy.md"
        assert rule_path.exists(), f"Missing: {rule_path}"


# ─── Agent preamble tests ────────────────────────────────────────────────────


class TestAgentPreamble:
    """Tests for content policy in agent-preamble.md."""

    def test_preamble_mentions_content_policy(self):
        """agent-preamble.md must mention content policy."""
        preamble_path = PROJECT_ROOT / "templates" / "agent-preamble.md"
        assert preamble_path.exists(), f"Missing: {preamble_path}"

        content = preamble_path.read_text()
        assert "Content Policy" in content, (
            "agent-preamble.md does not mention Content Policy"
        )

    def test_preamble_lists_prohibited_terms(self):
        """agent-preamble.md must list the prohibited terms."""
        preamble_path = PROJECT_ROOT / "templates" / "agent-preamble.md"
        content = preamble_path.read_text()
        assert "Prohibited" in content or "prohibited" in content, (
            "agent-preamble.md does not list prohibited terms"
        )


# ─── Pre-commit gate tests ───────────────────────────────────────────────────


class TestPreCommitGate:
    """Tests for content policy integration in pre-commit-gate.sh."""

    def test_precommit_checks_content_policy(self):
        """pre-commit-gate.sh must include content policy check."""
        gate_path = PROJECT_ROOT / "hooks" / "pre-commit-gate.sh"
        assert gate_path.exists(), f"Missing: {gate_path}"

        content = gate_path.read_text()
        assert "content-policy" in content.lower() or "POLICY_FILE" in content, (
            "pre-commit-gate.sh does not check content policy"
        )


# ─── Codebase violation tests ────────────────────────────────────────────────


class TestNoViolations:
    """Verify no prohibited terms exist in the codebase (excluding policy files)."""

    # Files that legitimately contain the terms (policy definition, preamble listing)
    EXCLUDED_FILES = {
        ".cognitive-os/content-policy.yaml",
        "templates/agent-preamble.md",
        "rules/content-policy.md",
        "tests/behavior/test_content_policy.py",
    }

    def _search_term(self, term):
        """Search for a term in the codebase, excluding allowed files."""
        result = subprocess.run(
            [
                "grep", "-ril", term,
                "--include=*.md",
                "--include=*.py",
                "--include=*.sh",
                "--include=*.yaml",
                "--include=*.yml",
                "--include=*.json",
                str(PROJECT_ROOT),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return []

        matches = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            # Convert to relative path for comparison
            try:
                rel = os.path.relpath(line, PROJECT_ROOT)
            except ValueError:
                rel = line
            if rel not in self.EXCLUDED_FILES:
                matches.append(rel)
        return matches

    def test_no_hyperagents_in_codebase(self):
        """'HyperAgents' must not appear anywhere in the codebase."""
        matches = self._search_term("HyperAgents")
        assert not matches, (
            f"'HyperAgents' found in: {matches}"
        )

    def test_no_facebookresearch_in_codebase(self):
        """'facebookresearch' must not appear anywhere in the codebase."""
        matches = self._search_term("facebookresearch")
        assert not matches, (
            f"'facebookresearch' found in: {matches}"
        )

    def test_no_gentleman_programming_in_codebase(self):
        """'gentleman-programming' must not appear anywhere in the codebase."""
        matches = self._search_term("gentleman-programming")
        assert not matches, (
            f"'gentleman-programming' found in: {matches}"
        )

    def test_no_meta_research_in_codebase(self):
        """'META Research' must not appear anywhere in the codebase."""
        matches = self._search_term("META Research")
        assert not matches, (
            f"'META Research' found in: {matches}"
        )

    def test_author_fields_are_luum(self):
        """Author fields in Python files should be 'luum'."""
        result = subprocess.run(
            [
                "grep", "-rn", "Author:",
                "--include=*.py",
                str(PROJECT_ROOT / "lib"),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            # No author fields found — acceptable
            return

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            # Check that author is luum
            assert "luum" in line.lower(), (
                f"Author field not set to 'luum': {line}"
            )
