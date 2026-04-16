"""Behavioral tests for subagent-context-injector.sh hook.

Verifies that every sub-agent receives mandatory project rules
via additionalContext. These tests execute the actual hook with
real JSON input and verify the output contains critical rules.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "subagent-context-injector.sh"
MANDATORY_RULES_PATH = PROJECT_ROOT / "templates" / "agent-mandatory-rules.md"


def _run_hook(stdin_json: dict, env_overrides: dict | None = None) -> dict:
    """Execute the hook with given JSON stdin and return parsed output."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(PROJECT_ROOT)
    env["COS_SESSION_DIR"] = "/tmp/cos-test-session"
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )

    # Hook should always exit 0
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"

    # Parse JSON output (may be empty if no context to inject)
    stdout = result.stdout.strip()
    if not stdout:
        return {}
    return json.loads(stdout)


class TestMandatoryRulesInjection:
    """Every sub-agent MUST receive mandatory project rules."""

    def test_hook_returns_additional_context(self):
        """The hook must return a JSON object with additionalContext."""
        output = _run_hook({"prompt": "test agent prompt"})
        assert "additionalContext" in output, (
            "Hook did not return additionalContext — sub-agents will not receive project rules"
        )

    def test_symlink_rules_injected(self):
        """The symlink warning MUST be in every sub-agent's context."""
        output = _run_hook({"prompt": "audit the codebase"})
        context = output.get("additionalContext", "")
        assert "readlink -f" in context, (
            "Symlink resolution rule not injected — agents will report false 'missing' files"
        )
        assert "file_exists_strict" in context or "file_checker" in context, (
            "file_checker.sh reference not injected"
        )

    def test_no_structural_tests_rule_injected(self):
        """The rule against structural-only tests MUST be injected."""
        output = _run_hook({"prompt": "write tests for the module"})
        context = output.get("additionalContext", "")
        assert "verify file existence" in context.lower() or "execute code" in context.lower(), (
            "Test quality rule not injected — agents may create structural-only tests"
        )

    def test_no_dead_metadata_rule_injected(self):
        """The rule against dead metadata MUST be injected."""
        output = _run_hook({"prompt": "add a new field to skills"})
        context = output.get("additionalContext", "")
        assert "metadata" in context.lower() and "consume" in context.lower(), (
            "Dead metadata prevention rule not injected"
        )

    def test_performance_rules_injected(self):
        """The rule against O(n) subprocess spawns MUST be injected."""
        output = _run_hook({"prompt": "create a new hook"})
        context = output.get("additionalContext", "")
        assert "python3" in context and "while" in context.lower(), (
            "Performance anti-pattern rule not injected — agents may create O(n) subprocess hooks"
        )

    def test_engram_save_rule_injected(self):
        """The rule to save discoveries to engram MUST be injected."""
        output = _run_hook({"prompt": "investigate the bug"})
        context = output.get("additionalContext", "")
        assert "engram" in context.lower() and "mem_save" in context.lower(), (
            "Engram save rule not injected — agents will not persist discoveries"
        )


class TestMandatoryRulesFileIntegrity:
    """The mandatory rules template must exist and contain all critical sections."""

    def test_template_file_exists(self):
        """templates/agent-mandatory-rules.md must exist."""
        assert MANDATORY_RULES_PATH.exists(), (
            "Mandatory rules template missing — sub-agents will use inline fallback"
        )

    def test_template_has_symlink_section(self):
        """Template must have symlink rules."""
        content = MANDATORY_RULES_PATH.read_text()
        assert "Symlinks" in content
        assert "readlink" in content

    def test_template_has_auditing_section(self):
        """Template must have auditing rules."""
        content = MANDATORY_RULES_PATH.read_text()
        assert "Auditing" in content
        assert "Cross-validate" in content or "cross-validate" in content

    def test_template_has_code_quality_section(self):
        """Template must have code quality rules."""
        content = MANDATORY_RULES_PATH.read_text()
        assert "Code Quality" in content
        assert "execute code" in content.lower() or "verify behavior" in content.lower()

    def test_template_has_performance_section(self):
        """Template must have performance rules."""
        content = MANDATORY_RULES_PATH.read_text()
        assert "Performance" in content
        assert "python3" in content


class TestHookDoesNotBlock:
    """The hook must never block sub-agent launch."""

    def test_exit_code_always_zero(self):
        """Hook must exit 0 even with empty input."""
        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT)},
        )
        assert result.returncode == 0

    def test_exit_code_zero_with_invalid_json(self):
        """Hook must exit 0 even with invalid JSON."""
        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input="not json at all",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT)},
        )
        assert result.returncode == 0

    def test_completes_under_3_seconds(self):
        """Hook must complete within 3 seconds."""
        import time
        start = time.time()
        _run_hook({"prompt": "test prompt"})
        elapsed = time.time() - start
        assert elapsed < 3.0, f"Hook took {elapsed:.1f}s — must be under 3s"
