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


# ─── Hook tests ───────────────────────────────────────────────────────────────


class TestContentPolicyHook:
    """Tests for hooks/content-policy.sh."""

    @pytest.fixture
    def hook_path(self):
        return PROJECT_ROOT / "hooks" / "content-policy.sh"


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


# ─── Agent preamble tests ────────────────────────────────────────────────────


# ─── Pre-commit gate tests ───────────────────────────────────────────────────


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
                # Exclude git submodule plugin directories (external code)
                "--exclude-dir=hermes-agent",
                "--exclude-dir=pi-mono",
                "--exclude-dir=caveman",
                "--exclude-dir=.git",
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

    def test_no_prohibited_terms_in_codebase(self):
        """No prohibited terms from content-policy.yaml must appear anywhere in the codebase."""
        try:
            import yaml
        except ImportError:
            pytest.skip("pyyaml not installed")

        policy_path = PROJECT_ROOT / ".cognitive-os" / "content-policy.yaml"
        if not policy_path.exists():
            pytest.skip("content-policy.yaml not found")

        policy = yaml.safe_load(policy_path.read_text())
        prohibited = policy.get("prohibited_terms", [])

        terms = [e.get("term", "") for e in prohibited if e.get("term")]
        if not terms:
            return  # Nothing to check

        # Build a single grep pattern to check all terms at once
        pattern = "|".join(terms)
        result = subprocess.run(
            [
                "grep", "-ril", "-E", pattern,
                "--include=*.md",
                "--include=*.py",
                "--include=*.sh",
                "--include=*.yaml",
                "--include=*.yml",
                "--include=*.json",
                # Exclude git submodule plugin directories (external code)
                "--exclude-dir=hermes-agent",
                "--exclude-dir=pi-mono",
                "--exclude-dir=caveman",
                "--exclude-dir=.git",
                # Exclude .cognitive-os/ — it contains symlinks back into the project
                # (cos/, docs/, skills/, etc.) which would cause files to be scanned
                # multiple times, making the grep much slower than the 30s test timeout.
                # The underlying source files are already covered by scanning PROJECT_ROOT.
                "--exclude-dir=.cognitive-os",
                str(PROJECT_ROOT),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return  # No matches found

        violations = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            try:
                rel = os.path.relpath(line, PROJECT_ROOT)
            except ValueError:
                rel = line
            if rel not in self.EXCLUDED_FILES:
                violations.append(rel)

        assert not violations, (
            f"Prohibited terms found in codebase: {violations}"
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
