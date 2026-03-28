"""Unit tests for the prompt-quality hook, rule, and template.

Validates hook syntax, file existence, permissions, documentation
completeness, and advisory-only behavior.
"""

import os
import subprocess
import stat

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOK_PATH = os.path.join(PROJECT_ROOT, "hooks", "prompt-quality.sh")
RULE_PATH = os.path.join(PROJECT_ROOT, "rules", "prompt-quality.md")
TEMPLATE_PATH = os.path.join(PROJECT_ROOT, "templates", "generator-validator-pair.md")


class TestPromptQualityHook:
    """Tests for hooks/prompt-quality.sh."""

    def test_hook_syntax_valid(self):
        """Hook script must pass bash -n syntax check."""
        result = subprocess.run(
            ["bash", "-n", HOOK_PATH],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error in hook: {result.stderr}"

    def test_hook_exists_and_executable(self):
        """Hook file must exist and have executable permission."""
        assert os.path.isfile(HOOK_PATH), f"Hook not found at {HOOK_PATH}"
        file_stat = os.stat(HOOK_PATH)
        is_executable = file_stat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        assert is_executable, "Hook is not executable"

    def test_hook_is_advisory(self):
        """Hook must always exit 0 (never block). Must not contain exit 2."""
        with open(HOOK_PATH, "r") as f:
            content = f.read()
        assert "exit 0" in content, "Hook must contain 'exit 0' for advisory behavior"
        assert "exit 2" not in content, "Hook must not contain 'exit 2' — it is advisory only"

    def test_hook_sources_common(self):
        """Hook must source common.sh for shared utilities."""
        with open(HOOK_PATH, "r") as f:
            content = f.read()
        assert "_lib/common.sh" in content, "Hook must source _lib/common.sh"

    def test_hook_sources_safe_jsonl(self):
        """Hook must source safe-jsonl.sh for safe metric writes."""
        with open(HOOK_PATH, "r") as f:
            content = f.read()
        assert "_lib/safe-jsonl.sh" in content, "Hook must source _lib/safe-jsonl.sh"

    def test_hook_checks_private_mode(self):
        """Hook must check private mode and skip if active."""
        with open(HOOK_PATH, "r") as f:
            content = f.read()
        assert "check_private_mode" in content, "Hook must check private mode"

    def test_hook_checks_capability_level(self):
        """Hook must check capability level for auto-disable."""
        with open(HOOK_PATH, "r") as f:
            content = f.read()
        assert "check_capability_level" in content, "Hook must check capability level"

    def test_hook_logs_to_prompt_quality_jsonl(self):
        """Hook must log to prompt-quality.jsonl."""
        with open(HOOK_PATH, "r") as f:
            content = f.read()
        assert "prompt-quality.jsonl" in content, "Hook must log to prompt-quality.jsonl"


class TestPromptQualityRule:
    """Tests for rules/prompt-quality.md."""

    def test_rule_exists(self):
        """Rule file must exist."""
        assert os.path.isfile(RULE_PATH), f"Rule not found at {RULE_PATH}"

    def test_quality_signals_documented(self):
        """Rule must mention all 5 quality dimensions."""
        with open(RULE_PATH, "r") as f:
            content = f.read().lower()
        dimensions = ["specificity", "actionability", "context", "measurability", "scope clarity"]
        for dim in dimensions:
            assert dim in content, f"Rule must document the '{dim}' dimension"

    def test_rule_documents_advisory_behavior(self):
        """Rule must state that the hook is advisory only."""
        with open(RULE_PATH, "r") as f:
            content = f.read().lower()
        assert "advisory" in content, "Rule must document advisory-only behavior"

    def test_rule_documents_scoring_ranges(self):
        """Rule must document the three scoring ranges."""
        with open(RULE_PATH, "r") as f:
            content = f.read()
        assert "< 30" in content or "<30" in content, "Rule must document score < 30 range"
        assert "30-60" in content, "Rule must document score 30-60 range"
        assert "> 60" in content or ">60" in content, "Rule must document score > 60 range"


class TestGeneratorValidatorTemplate:
    """Tests for templates/generator-validator-pair.md."""

    def test_template_exists(self):
        """Template file must exist."""
        assert os.path.isfile(TEMPLATE_PATH), f"Template not found at {TEMPLATE_PATH}"

    def test_template_has_generator_section(self):
        """Template must document the generator pattern."""
        with open(TEMPLATE_PATH, "r") as f:
            content = f.read()
        assert "Generator" in content, "Template must have a Generator section"

    def test_template_has_validator_section(self):
        """Template must document the validator pattern."""
        with open(TEMPLATE_PATH, "r") as f:
            content = f.read()
        assert "Validator" in content, "Template must have a Validator section"

    def test_template_has_examples(self):
        """Template must include domain examples."""
        with open(TEMPLATE_PATH, "r") as f:
            content = f.read()
        assert "Dockerfile" in content, "Template must include Dockerfile example"
        assert "Terraform" in content or "Kubernetes" in content, "Template must include infra examples"

    def test_template_mentions_staged_verification(self):
        """Template must reference the staged verification pattern."""
        with open(TEMPLATE_PATH, "r") as f:
            content = f.read().lower()
        assert "staged" in content or "cheapest" in content, "Template must reference staged/cheapest-first verification"

    def test_template_mentions_graceful_degradation(self):
        """Template must document graceful degradation."""
        with open(TEMPLATE_PATH, "r") as f:
            content = f.read().lower()
        assert "graceful" in content or "skipped" in content, "Template must document graceful degradation"
