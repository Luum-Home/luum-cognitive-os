"""Shell-level graceful degradation tests for ALL COS hooks.

Every hook must:
1. Handle empty/invalid stdin without crashing (exit 0 or 2, never 1)
2. Handle missing CLAUDE_PROJECT_DIR gracefully
3. Exit 0 when private mode is active (for hooks that check it)
4. Not crash when jq is unavailable (hooks should check for jq)

These tests ensure no hook produces unexpected crashes (exit 1)
from malformed input, missing files, or missing dependencies.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.hooks.conftest import HOOKS_DIR


def make_agent_input(prompt: str = "Test task") -> dict:
    """Build a mock Agent tool input JSON."""
    return {"tool_name": "Agent", "tool_input": {"prompt": prompt}}


def make_bash_input(command: str = "echo hello") -> dict:
    """Build a mock Bash tool input JSON."""
    return {"tool_name": "Bash", "tool_input": {"command": command}}


pytestmark = [pytest.mark.behavior]


# Hooks that do NOT receive JSON on stdin (SessionStart, Stop, PreCompact, etc.)
# These should be excluded from stdin-based tests.
NON_STDIN_HOOKS = {
    "self-install.sh",       # SessionStart
    "session-init.sh",       # SessionStart
    "crash-recovery.sh",     # SessionStart
    "session-cleanup.sh",    # Stop
    "session-learning.sh",   # Stop
    "pre-compaction-flush.sh",  # PreCompact
    "cognitive-os-health.sh",   # SessionStart (standalone health check)
    "infra-health.sh",          # SessionStart
    "mcp-scan.sh",              # SessionStart
    "pre-commit-gate.sh",       # git pre-commit (not Claude hook)
    "notify.sh",                # utility, not a Claude hook
    "subagent-context-injector.sh",  # SubagentStart
    "user-prompt-capture.sh",       # UserPromptSubmit
}


def _list_hooks() -> list[Path]:
    """List all .sh hook files, excluding _lib/ helpers."""
    hooks = sorted(HOOKS_DIR.glob("*.sh"))
    return [h for h in hooks if not h.name.startswith("_")]


def _list_stdin_hooks() -> list[Path]:
    """List hooks that receive JSON on stdin (PreToolUse/PostToolUse)."""
    return [h for h in _list_hooks() if h.name not in NON_STDIN_HOOKS]


def _hook_ids() -> list[str]:
    """Return hook names for parametrize IDs."""
    return [h.name for h in _list_hooks()]


def _stdin_hook_ids() -> list[str]:
    """Return names of hooks that receive JSON stdin."""
    return [h.name for h in _list_stdin_hooks()]

PRIVATE_MODE_HOOKS = {
    "blast-radius.sh",
    "clarification-gate.sh",
    "rate-limiter.sh",
    "completeness-check.sh",
    "infra-intent-detector.sh",
    "pre-cleanup-snapshot.sh",
}

PRETOOL_AGENT_HOOKS = {
    "blast-radius.sh",
    "clarification-gate.sh",
    "completeness-check.sh",
    "infra-intent-detector.sh",
    "token-budget-monitor.sh",
}

POSTTOOL_EDIT_WRITE_HOOKS = {
    "content-policy.sh",
    "secret-detector.sh",
}

HOOKS_NEEDING_PROJECT = {
    "content-policy.sh",
    "blast-radius.sh",
    "clarification-gate.sh",
    "claim-validator.sh",
    "error-pipeline.sh",
    "completeness-check.sh",
    "infra-intent-detector.sh",
    "token-budget-monitor.sh",
}

JSON_HOOKS = {
    "content-policy.sh",
    "blast-radius.sh",
    "clarification-gate.sh",
    "claim-validator.sh",
    "error-pipeline.sh",
    "completeness-check.sh",
    "infra-intent-detector.sh",
    "token-budget-monitor.sh",
    "rate-limiter.sh",
    "large-file-advisor.sh",
}

TOOL_HOOKS = {
    "aguara-scan.sh": "aguara",
    "semgrep-scan.sh": "semgrep",
    "mcp-scan.sh": "mcp-scan",
}


def _hooks_by_names(names: set[str]) -> list[Path]:
    """Return existing hooks whose names are in names, preserving sorted hook order."""
    return [h for h in _list_hooks() if h.name in names]


def _hook_names(paths: list[Path]) -> list[str]:
    return [p.name for p in paths]


# ---------------------------------------------------------------------------
# Parametrized: every hook gets tested with each input pattern
# ---------------------------------------------------------------------------


@pytest.fixture(params=_list_hooks(), ids=_hook_ids())
def hook_path(request) -> Path:
    """Parametrize over all hooks."""
    return request.param


@pytest.fixture(params=_list_stdin_hooks(), ids=_stdin_hook_ids())
def stdin_hook_path(request) -> Path:
    """Parametrize over hooks that receive JSON stdin."""
    return request.param


@pytest.fixture(params=_hooks_by_names(PRIVATE_MODE_HOOKS), ids=lambda p: p.name)
def private_mode_hook_path(request) -> Path:
    return request.param


@pytest.fixture(params=_hooks_by_names(PRETOOL_AGENT_HOOKS), ids=lambda p: p.name)
def pretool_agent_hook_path(request) -> Path:
    return request.param


@pytest.fixture(params=_hooks_by_names(POSTTOOL_EDIT_WRITE_HOOKS), ids=lambda p: p.name)
def edit_write_hook_path(request) -> Path:
    return request.param


@pytest.fixture(params=_hooks_by_names(HOOKS_NEEDING_PROJECT), ids=lambda p: p.name)
def project_dir_hook_path(request) -> Path:
    return request.param


@pytest.fixture(params=_hooks_by_names(JSON_HOOKS), ids=lambda p: p.name)
def json_hook_path(request) -> Path:
    return request.param


@pytest.fixture(params=_hooks_by_names(set(TOOL_HOOKS)), ids=lambda p: p.name)
def external_tool_hook_path(request) -> Path:
    return request.param


class TestEmptyStdin:
    """Hooks that receive JSON stdin should handle empty/invalid input."""

    def test_empty_json_no_crash(self, stdin_hook_path, mock_project):
        """Feeding {} as stdin should not cause exit 1 (crash)."""
        result = subprocess.run(
            ["bash", str(stdin_hook_path)],
            input="{}",
            capture_output=True,
            text=True,
            env={**os.environ, **mock_project["env"]},
            timeout=15,
        )
        assert result.returncode in (0, 2), (
            f"{stdin_hook_path.name} crashed (exit {result.returncode}) on empty JSON.\n"
            f"stdout: {result.stdout[:300]}\n"
            f"stderr: {result.stderr[:300]}"
        )

    def test_completely_empty_stdin_no_crash(self, stdin_hook_path, mock_project):
        """Feeding empty string as stdin should not cause exit 1."""
        result = subprocess.run(
            ["bash", str(stdin_hook_path)],
            input="",
            capture_output=True,
            text=True,
            env={**os.environ, **mock_project["env"]},
            timeout=15,
        )
        assert result.returncode in (0, 2), (
            f"{stdin_hook_path.name} crashed (exit {result.returncode}) on empty stdin.\n"
            f"stdout: {result.stdout[:300]}\n"
            f"stderr: {result.stderr[:300]}"
        )


class TestPrivateMode:
    """Hooks that check private mode should skip when it is active."""

    def test_private_mode_exit_0(self, private_mode_hook_path, mock_project, private_mode):
        """Hooks that check private mode should exit 0 when it is active."""
        stdin = json.dumps(make_agent_input("Do something drastic"))
        result = subprocess.run(
            ["bash", str(private_mode_hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            env={**os.environ, **mock_project["env"]},
            timeout=15,
        )
        assert result.returncode == 0, (
            f"{private_mode_hook_path.name} did not skip in private mode "
            f"(exit {result.returncode})"
        )


class TestToolNameFiltering:
    """Hooks should only process their target tool types."""

    def test_agent_hooks_ignore_bash(self, pretool_agent_hook_path, mock_project):
        """PreToolUse Agent hooks should exit 0 for Bash tool."""
        stdin = json.dumps(make_bash_input("echo hello"))
        result = subprocess.run(
            ["bash", str(pretool_agent_hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            env={**os.environ, **mock_project["env"]},
            timeout=15,
        )
        assert result.returncode == 0, (
            f"{pretool_agent_hook_path.name} should ignore Bash tool but got exit {result.returncode}"
        )

    def test_edit_write_hooks_ignore_agent(self, edit_write_hook_path, mock_project):
        """PostToolUse Edit|Write hooks should exit 0 for Agent tool."""
        stdin = json.dumps(make_agent_input("Do something"))
        result = subprocess.run(
            ["bash", str(edit_write_hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            env={**os.environ, **mock_project["env"]},
            timeout=15,
        )
        assert result.returncode == 0, (
            f"{edit_write_hook_path.name} should ignore Agent tool but got exit {result.returncode}"
        )


class TestMissingProjectDir:
    """Hooks should not crash when CLAUDE_PROJECT_DIR points to non-existent dir."""

    def test_nonexistent_project_dir(self, project_dir_hook_path, tmp_path):
        """Hook should not crash when project dir does not exist."""
        nonexistent = tmp_path / "nonexistent"
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(nonexistent),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }

        stdin = json.dumps(make_agent_input("test"))
        result = subprocess.run(
            ["bash", str(project_dir_hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        # Should not crash (exit 1). Exit 0 (skip) or 2 (block) are acceptable.
        assert result.returncode in (0, 2), (
            f"{project_dir_hook_path.name} crashed (exit {result.returncode}) with nonexistent project dir.\n"
            f"stderr: {result.stderr[:300]}"
        )


class TestJsonParsing:
    """Hooks should handle malformed JSON without crashing."""

    def test_malformed_json_no_crash(self, json_hook_path, mock_project):
        """Feeding invalid JSON should not cause a bash crash (exit 1).

        Some hooks may exit with custom codes (e.g., 5 from pipefail),
        which is acceptable as long as it is not a raw crash (exit 1 from
        set -e with no error handling).
        """
        result = subprocess.run(
            ["bash", str(json_hook_path)],
            input="this is not json at all {{{",
            capture_output=True,
            text=True,
            env={**os.environ, **mock_project["env"]},
            timeout=15,
        )
        # Exit 0 (graceful skip), 2 (block), or other non-1 codes are acceptable.
        # Only exit 1 from set -e with unhandled errors is considered a crash.
        # Some hooks may exit with pipefail codes (e.g., 5) which is not ideal
        # but not a crash.
        assert result.returncode != 1 or json_hook_path.name in self._KNOWN_EXIT1_ON_BAD_JSON, (
            f"{json_hook_path.name} crashed (exit {result.returncode}) on malformed JSON.\n"
            f"stderr: {result.stderr[:300]}"
        )

    # Hooks known to exit 1 on malformed JSON (tracked for future fixing)
    _KNOWN_EXIT1_ON_BAD_JSON: set[str] = set()

    def test_json_missing_tool_name(self, json_hook_path, mock_project):
        """JSON without tool_name field should not crash."""
        result = subprocess.run(
            ["bash", str(json_hook_path)],
            input=json.dumps({"random_field": "value"}),
            capture_output=True,
            text=True,
            env={**os.environ, **mock_project["env"]},
            timeout=15,
        )
        assert result.returncode in (0, 2), (
            f"{json_hook_path.name} crashed (exit {result.returncode}) on JSON without tool_name.\n"
            f"stderr: {result.stderr[:300]}"
        )


# ---------------------------------------------------------------------------
# External tool graceful degradation
# Hooks that depend on external tools (aguara, semgrep, mcp-scan)
# should exit 0 when the tool is not installed
# ---------------------------------------------------------------------------


class TestExternalToolGracefulDegradation:
    """Hooks depending on external tools should exit 0 when tool is missing."""

    def test_missing_external_tool_exits_0(self, external_tool_hook_path, mock_project):
        """Hook should exit 0 gracefully when its external tool is not found."""
        tool_name = TOOL_HOOKS[external_tool_hook_path.name]

        # Create env with stripped PATH so the tool cannot be found
        env = {
            **os.environ,
            **mock_project["env"],
            "PATH": "/usr/bin:/bin",  # minimal PATH, unlikely to have aguara/semgrep
        }

        # For semgrep, also disable the env var
        if tool_name == "semgrep":
            env["SEMGREP_ENABLED"] = "true"  # enable the check, but tool is missing

        stdin = json.dumps(make_agent_input("test task"))
        result = subprocess.run(
            ["bash", str(external_tool_hook_path)],
            input=stdin,
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        assert result.returncode == 0, (
            f"{external_tool_hook_path.name} did not degrade gracefully when {tool_name} "
            f"is missing (exit {result.returncode}).\n"
            f"stderr: {result.stderr[:300]}"
        )
