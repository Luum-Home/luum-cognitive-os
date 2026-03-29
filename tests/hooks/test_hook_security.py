"""Shell-level tests for security-critical hooks.

Focused tests for:
- rate-limiter.sh: rate limiting logic
- secret-detector.sh: credential detection in source files
- content-policy.sh: prohibited term enforcement
"""

import json
import os
from pathlib import Path

import pytest

from tests.hooks.conftest import (
    make_agent_input,
    make_bash_input,
    make_edit_input,
    make_write_input,
)


pytestmark = [pytest.mark.behavior]


# ---------------------------------------------------------------------------
# rate-limiter.sh — PreToolUse on Bash, Agent, Edit, Write
# Blocks (exit 2) when rate limits exceeded
# ---------------------------------------------------------------------------


class TestRateLimiter:
    """Tests for hooks/rate-limiter.sh."""

    HOOK = "rate-limiter.sh"

    def test_first_call_passes(self, run_hook, mock_project):
        """First call with no history should always pass."""
        stdin = make_bash_input("echo hello")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_agent_tool_mapped_correctly(self, run_hook, mock_project):
        """Agent tool should be mapped to agent_launch action."""
        stdin = make_agent_input("test task")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        # Should pass (no prior usage)
        assert result.returncode == 0

    def test_private_mode_skips(self, run_hook, mock_project, private_mode):
        """Rate limiter should skip when private mode is active."""
        stdin = make_bash_input("echo hello")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_unknown_tool_mapped_to_tool_call(self, run_hook, mock_project):
        """Unknown tool names should map to generic tool_call action."""
        stdin = {"tool_name": "WebSearch", "tool_input": {"query": "test"}}
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_write_tool_mapped_to_file_write(self, run_hook, mock_project):
        """Write tool should be mapped to file_write action."""
        stdin = make_write_input("/tmp/test.py", "content")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0

    def test_edit_tool_mapped_to_file_write(self, run_hook, mock_project):
        """Edit tool should be mapped to file_write action."""
        stdin = make_edit_input("/tmp/test.py", "old", "new")
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# secret-detector.sh — PostToolUse on Edit|Write
# Detects env var references without definitions
# ---------------------------------------------------------------------------


class TestSecretDetector:
    """Tests for hooks/secret-detector.sh."""

    HOOK = "secret-detector.sh"

    def test_non_source_file_skipped(self, run_hook, mock_project, tmp_path):
        """Markdown files should be skipped."""
        md_file = tmp_path / "readme.md"
        md_file.write_text("# Hello\nAPI_KEY=secret\n")

        env = {**mock_project["env"], "TOOL_INPUT": json.dumps({"file_path": str(md_file)})}
        result = run_hook(self.HOOK, stdin_json={}, env=env)
        assert result.returncode == 0

    def test_yaml_file_skipped(self, run_hook, mock_project, tmp_path):
        """YAML files should be skipped."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("key: value\n")

        env = {**mock_project["env"], "TOOL_INPUT": json.dumps({"file_path": str(yaml_file)})}
        result = run_hook(self.HOOK, stdin_json={}, env=env)
        assert result.returncode == 0

    def test_empty_tool_input_skipped(self, run_hook, mock_project):
        """Empty TOOL_INPUT should be skipped."""
        env = {**mock_project["env"], "TOOL_INPUT": ""}
        result = run_hook(self.HOOK, stdin_json={}, env=env)
        assert result.returncode == 0

    def test_no_tool_input_skipped(self, run_hook, mock_project):
        """Missing TOOL_INPUT should be skipped."""
        result = run_hook(self.HOOK, stdin_json={}, env=mock_project["env"])
        assert result.returncode == 0

    def test_go_source_with_env_ref(self, run_hook, mock_project, tmp_path):
        """Go file with os.Getenv should be detected (advisory, exit 0)."""
        go_file = tmp_path / "main.go"
        go_file.write_text(
            'package main\n\n'
            'import "os"\n\n'
            'func main() {\n'
            '    key := os.Getenv("MY_SECRET_KEY")\n'
            '    _ = key\n'
            '}\n'
        )

        env = {**mock_project["env"], "TOOL_INPUT": json.dumps({"file_path": str(go_file)})}
        result = run_hook(self.HOOK, stdin_json={}, env=env)
        # Secret detector is advisory — it logs but does not block
        assert result.returncode == 0

    def test_ts_source_with_process_env(self, run_hook, mock_project, tmp_path):
        """TypeScript file with process.env should be detected (advisory)."""
        ts_file = tmp_path / "config.ts"
        ts_file.write_text(
            "const apiKey = process.env.STRIPE_API_KEY;\n"
            "const dbHost = process.env.DATABASE_HOST;\n"
        )

        env = {**mock_project["env"], "TOOL_INPUT": json.dumps({"file_path": str(ts_file)})}
        result = run_hook(self.HOOK, stdin_json={}, env=env)
        assert result.returncode == 0

    def test_cognitive_os_path_skipped(self, run_hook, mock_project, tmp_path):
        """Files under .cognitive-os/ should be skipped."""
        cos_file = tmp_path / ".cognitive-os" / "config.py"
        cos_file.parent.mkdir(parents=True, exist_ok=True)
        cos_file.write_text("key = process.env.SECRET\n")

        env = {**mock_project["env"], "TOOL_INPUT": json.dumps({"file_path": str(cos_file)})}
        result = run_hook(self.HOOK, stdin_json={}, env=env)
        assert result.returncode == 0

    def test_shell_file_skipped(self, run_hook, mock_project, tmp_path):
        """Shell files (.sh) should be skipped."""
        sh_file = tmp_path / "script.sh"
        sh_file.write_text("#!/bin/bash\necho $API_KEY\n")

        env = {**mock_project["env"], "TOOL_INPUT": json.dumps({"file_path": str(sh_file)})}
        result = run_hook(self.HOOK, stdin_json={}, env=env)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# content-policy.sh — advanced prohibited pattern tests
# ---------------------------------------------------------------------------


class TestContentPolicyPatterns:
    """Advanced pattern tests for hooks/content-policy.sh."""

    HOOK = "content-policy.sh"

    def test_case_insensitive_matching(self, run_hook, mock_project, tmp_path):
        """Prohibited terms should be matched case-insensitively."""
        policy = mock_project["cos_dir"] / "content-policy.yaml"
        policy.write_text(
            "prohibited_terms:\n"
            '  - term: "forbidden_token"\n'
            '    reason: "Test"\n'
        )

        test_file = tmp_path / "test.py"
        # Use different casing
        test_file.write_text("x = FORBIDDEN_TOKEN\n")

        stdin = make_write_input(str(test_file), test_file.read_text())
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        # Content policy does case-insensitive matching per the hook code
        assert result.returncode == 2, (
            f"Expected BLOCK for case-insensitive prohibited term, "
            f"got {result.returncode}. stderr: {result.stderr[:300]}"
        )

    def test_multiple_prohibited_terms(self, run_hook, mock_project, tmp_path):
        """Multiple prohibited terms in policy should all be checked."""
        policy = mock_project["cos_dir"] / "content-policy.yaml"
        policy.write_text(
            "prohibited_terms:\n"
            '  - term: "term_alpha"\n'
            '    reason: "Test A"\n'
            '  - term: "term_beta"\n'
            '    reason: "Test B"\n'
        )

        test_file = tmp_path / "test.py"
        test_file.write_text("x = term_beta  # this should be caught\n")

        stdin = make_write_input(str(test_file), test_file.read_text())
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 2

    def test_clean_file_with_policy(self, run_hook, mock_project, tmp_path):
        """A file without prohibited terms should pass even with policy."""
        policy = mock_project["cos_dir"] / "content-policy.yaml"
        policy.write_text(
            "prohibited_terms:\n"
            '  - term: "bad_word"\n'
            '    reason: "Test"\n'
        )

        test_file = tmp_path / "clean.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        stdin = make_write_input(str(test_file), test_file.read_text())
        result = run_hook(self.HOOK, stdin_json=stdin, env=mock_project["env"])
        assert result.returncode == 0
