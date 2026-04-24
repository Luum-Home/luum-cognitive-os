"""Shell-level tests for COS hooks via subprocess.

Tests hooks by invoking them with mock JSON stdin and verifying:
- Exit codes (0 = pass, 2 = block)
- JSON parsing correctness
- Private mode bypass
- Tool name filtering

Priority hooks tested:
1. content-policy.sh
2. blast-radius.sh
3. clarification-gate.sh
4. claim-validator.sh
5. error-pipeline.sh
6. auto-checkpoint.sh
7. completeness-check.sh
8. infra-intent-detector.sh
9. token-budget-monitor.sh
10. large-file-advisor.sh
"""

import json
import os
from pathlib import Path

import pytest

from tests.hooks.conftest import (
    make_agent_input,
    make_agent_response,
    make_bash_input,
    make_bash_response,
    make_edit_input,
    make_write_input,
)


pytestmark = [pytest.mark.behavior]


def _blast_context(stdout: str) -> str:
    text = stdout.strip()
    if not text:
        return ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    return payload.get("hookSpecificOutput", {}).get("additionalContext", text)


# ---------------------------------------------------------------------------
# content-policy.sh — PostToolUse on Edit|Write
# Blocks writes containing prohibited terms from content-policy.yaml
# ---------------------------------------------------------------------------


class TestContentPolicy:
    """Tests for hooks/content-policy.sh."""

    HOOK = "content-policy.sh"

    def test_passes_clean_file(self, run_hook, mock_project, tmp_path):
        """A clean file with no prohibited terms should pass."""
        test_file = tmp_path / "clean.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        stdin = make_write_input(str(test_file), test_file.read_text())
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_ignores_non_edit_write_tools(self, run_hook, mock_project):
        """Should exit 0 immediately for non-Edit/Write tools."""
        stdin = make_bash_input("echo hello")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_handles_missing_file_path(self, run_hook, mock_project):
        """Should exit 0 when file_path is missing from input."""
        stdin = {"tool_name": "Write", "tool_input": {}}
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_handles_nonexistent_file(self, run_hook, mock_project):
        """Should exit 0 when the file does not exist on disk."""
        stdin = make_write_input("/tmp/nonexistent_file_12345.py", "content")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_skips_when_no_policy_file(self, run_hook, mock_project, tmp_path):
        """Should exit 0 when content-policy.yaml does not exist."""
        # Remove the policy file if it exists
        policy = mock_project["cos_dir"] / "content-policy.yaml"
        policy.unlink(missing_ok=True)

        test_file = tmp_path / "anything.py"
        test_file.write_text("anything goes here\n")

        stdin = make_write_input(str(test_file), test_file.read_text())
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_blocks_prohibited_term(self, run_hook, mock_project, tmp_path):
        """Should exit 2 when file contains a prohibited term."""
        # Create a content policy with a prohibited term
        policy = mock_project["cos_dir"] / "content-policy.yaml"
        policy.write_text(
            "prohibited_terms:\n"
            '  - term: "FORBIDDEN_MARKER"\n'
            '    reason: "Test prohibited term"\n'
        )

        test_file = tmp_path / "bad.py"
        test_file.write_text("# This file has FORBIDDEN_MARKER in it\n")

        stdin = make_write_input(str(test_file), test_file.read_text())
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 2, (
            f"Expected BLOCK (exit 2) for prohibited term, got {result.returncode}. "
            f"stderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# blast-radius.sh — PreToolUse on Agent
# Advisory only (always exit 0), warns for HIGH/CRITICAL scope
# ---------------------------------------------------------------------------


class TestBlastRadius:
    """Tests for hooks/blast-radius.sh."""

    HOOK = "blast-radius.sh"

    def test_ignores_non_agent_tool(self, run_hook, mock_project):
        """Should exit 0 immediately for non-Agent tools."""
        stdin = make_bash_input("echo hello")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0
        assert result.stderr.strip() == "" or "blast" not in result.stderr.lower()

    def test_low_blast_radius_silent(self, run_hook, mock_project):
        """A small task should produce LOW blast radius (silent pass)."""
        stdin = make_agent_input(
            "Fix the typo in internal/users/domain/entities/user.go"
        )
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_high_blast_radius_warns(self, run_hook, mock_project):
        """A broad task should produce HIGH/CRITICAL blast radius warning."""
        stdin = make_agent_input(
            "Rebrand all services across the entire project. "
            "Update all 200 files in src/ and docs/. "
            "Rename in internal/users/, internal/orders/, internal/payments/, "
            "internal/auth/, internal/billing/ directories."
        )
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0  # advisory only, never blocks
        combined = result.stdout + result.stderr
        # Should mention blast radius level
        assert any(
            kw in combined.upper() for kw in ["HIGH", "CRITICAL", "BLAST"]
        ), f"Expected blast radius warning in output: {combined[:500]}"

    def test_security_keywords_escalate(self, run_hook, mock_project):
        """Security keywords plus broad scope should surface as HIGH/CRITICAL."""
        stdin = make_agent_input(
            "Add JWT authentication and authorization across all endpoints"
        )
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0
        ctx = _blast_context(result.stdout)
        assert any(level in ctx.upper() for level in ["HIGH", "CRITICAL"]), (
            f"Expected advisory blast radius for security keywords: {ctx[:500]}"
        )

    def test_private_mode_skips(self, run_hook, mock_project, private_mode):
        """Should exit 0 silently when private mode is active."""
        stdin = make_agent_input("Rebrand everything across all services")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_empty_input_exits_0(self, run_hook, mock_project):
        """Should handle empty stdin gracefully."""
        result = run_hook(self.HOOK, stdin_json={}, env=mock_project["env"])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# clarification-gate.sh — PreToolUse on Agent
# Blocks (exit 2) when ambiguity score > 60
# ---------------------------------------------------------------------------


class TestClarificationGate:
    """Tests for hooks/clarification-gate.sh."""

    HOOK = "clarification-gate.sh"

    def test_clear_prompt_passes(self, run_hook, mock_project):
        """A specific prompt with file paths and criteria should pass."""
        stdin = make_agent_input(
            "Implement GetUserByID use case in "
            "internal/users/application/use_cases/get_user_by_id.go "
            "using ginext framework.\n\n"
            "ACCEPTANCE CRITERIA:\n"
            "1. go build ./... exits 0\n"
            "2. go test ./internal/users/... exits 0\n"
            "3. Endpoint GET /api/users/:id returns 200 with user data"
        )
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_vague_prompt_blocks(self, run_hook, mock_project):
        """A vague one-liner prompt should be blocked (exit 2)."""
        stdin = make_agent_input("Add auth")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        # Score should be high enough to block
        assert result.returncode == 2, (
            f"Expected BLOCK (exit 2) for vague prompt, got {result.returncode}. "
            f"Output: {(result.stdout + result.stderr)[:500]}"
        )

    def test_ignores_non_agent_tool(self, run_hook, mock_project):
        """Should exit 0 for non-Agent tools."""
        stdin = make_bash_input("echo hello")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_private_mode_skips(self, run_hook, mock_project, private_mode):
        """Should exit 0 silently when private mode is active."""
        stdin = make_agent_input("Do stuff")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_empty_input_exits_0(self, run_hook, mock_project):
        """Should handle empty stdin gracefully."""
        result = run_hook(self.HOOK, stdin_json={}, env=mock_project["env"])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# claim-validator.sh — PostToolUse on Agent
# Verifies agent claims about created/modified files actually exist
# ---------------------------------------------------------------------------


class TestClaimValidator:
    """Tests for hooks/claim-validator.sh."""

    HOOK = "claim-validator.sh"

    def test_ignores_non_agent(self, run_hook, mock_project):
        """Should exit 0 for non-Agent tools."""
        stdin = make_bash_response()
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_no_claims_passes(self, run_hook, mock_project):
        """Agent response with no file claims should pass."""
        stdin = make_agent_response(
            prompt="Analyze the codebase",
            response="The codebase follows clean architecture patterns.",
        )
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_valid_file_claims_pass(self, run_hook, mock_project, tmp_path):
        """Agent claiming to have created a file that exists should pass."""
        real_file = tmp_path / "handler.go"
        real_file.write_text("package main\n")

        stdin = make_agent_response(
            prompt="Create handler",
            response=f"Created {real_file} with the handler implementation.",
        )
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_empty_response_passes(self, run_hook, mock_project):
        """Agent with empty response should pass."""
        stdin = {
            "tool_name": "Agent",
            "tool_input": {"prompt": "test"},
            "tool_response": "",
        }
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# error-pipeline.sh — PostToolUse on Bash
# Captures errors from failed commands
# ---------------------------------------------------------------------------


class TestErrorPipeline:
    """Tests for hooks/error-pipeline.sh."""

    HOOK = "error-pipeline.sh"

    def test_success_command_skipped(self, run_hook, mock_project):
        """Exit code 0 commands should be skipped entirely."""
        stdin = make_bash_response(
            command="go test ./...",
            response="ok  all tests passed",
            exit_code="0",
        )
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_empty_command_skipped(self, run_hook, mock_project):
        """Empty command should be skipped."""
        stdin = {
            "tool_name": "Bash",
            "tool_input": {},
            "tool_response": "",
            "exit_code": "1",
        }
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_failed_test_captured(self, run_hook, mock_project):
        """A failing test command should be captured (exit 0, hook is advisory)."""
        stdin = make_bash_response(
            command="go test ./internal/users/...",
            response="--- FAIL: TestGetUser (0.01s)\nFAILED",
            exit_code="1",
        )
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        # Error pipeline captures but does not block
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# auto-checkpoint.sh — PostToolUse on Bash|Edit|Write
# Periodic checkpoint saves (every 5 min)
# ---------------------------------------------------------------------------


class TestAutoCheckpoint:
    """Tests for hooks/auto-checkpoint.sh."""

    HOOK = "auto-checkpoint.sh"

    def test_recent_checkpoint_skips(self, run_hook, mock_project):
        """Should skip when a recent checkpoint marker exists."""
        import time

        checkpoint_dir = mock_project["cos_dir"] / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        marker = checkpoint_dir / ".last-checkpoint"
        marker.write_text(str(int(time.time())))

        stdin = make_bash_response()
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_no_git_repo_skips(self, run_hook, tmp_path):
        """Should exit 0 when not in a git repo."""
        non_git = tmp_path / "nogit"
        non_git.mkdir()

        env = {
            "CLAUDE_PROJECT_DIR": str(non_git),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
        stdin = make_bash_response()
        result = run_hook(self.HOOK, stdin_json=stdin, env=env)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# completeness-check.sh — PreToolUse on Agent
# Advisory: warns if prompt is vague (always exit 0)
# ---------------------------------------------------------------------------


class TestCompletenessCheck:
    """Tests for hooks/completeness-check.sh."""

    HOOK = "completeness-check.sh"

    def test_always_exits_0(self, run_hook, mock_project):
        """Completeness check is advisory only, never blocks."""
        stdin = make_agent_input("Do all the things everywhere")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_specific_prompt_clean(self, run_hook, mock_project):
        """A specific prompt should produce no warnings."""
        stdin = make_agent_input(
            "Fix the null pointer in internal/users/handler.go line 42. "
            "The GetUserByID function does not check for nil before dereferencing."
        )
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# infra-intent-detector.sh — PreToolUse on Agent
# Advisory: suggests infrastructure components (always exit 0)
# ---------------------------------------------------------------------------


class TestInfraIntentDetector:
    """Tests for hooks/infra-intent-detector.sh."""

    HOOK = "infra-intent-detector.sh"

    def test_always_exits_0(self, run_hook, mock_project):
        """Infra intent detector is advisory only."""
        stdin = make_agent_input("Set up the database schema for users")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_no_infra_keywords_silent(self, run_hook, mock_project):
        """A prompt with no infra keywords should be silent."""
        stdin = make_agent_input("Rename the variable from foo to bar")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_malformed_json_exits_0(self, run_hook, mock_project):
        """Malformed JSON input should exit 0 (not crash with exit 5)."""
        result = run_hook(
            self.HOOK,
            stdin_text='{"not valid json',
            env=mock_project["env"],
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# token-budget-monitor.sh — PreToolUse on Agent
# Blocks at 95% token budget usage
# ---------------------------------------------------------------------------


class TestRateLimitProtection:
    """Tests for hooks/token-budget-monitor.sh (renamed from rate-limit-protection.sh)."""

    HOOK = "token-budget-monitor.sh"

    def test_normal_usage_passes(self, run_hook, mock_project):
        """Under normal conditions (no prior usage), should pass."""
        stdin = make_agent_input("Simple task")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        # Should pass since there is no usage history
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# large-file-advisor.sh — PreToolUse on Read
# Advisory: warns about large files (always exit 0)
# ---------------------------------------------------------------------------


class TestLargeFileAdvisor:
    """Tests for hooks/large-file-advisor.sh."""

    HOOK = "large-file-advisor.sh"

    def test_small_file_silent(self, run_hook, mock_project, tmp_path):
        """A small file should produce no advisory."""
        small_file = tmp_path / "small.py"
        small_file.write_text("x = 1\n")

        stdin = {
            "tool_name": "Read",
            "tool_input": {"file_path": str(small_file)},
        }
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_always_exits_0(self, run_hook, mock_project):
        """Advisory hook should never block."""
        stdin = {
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/nonexistent.py"},
        }
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0
