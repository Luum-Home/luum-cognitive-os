"""Behavior tests for hooks/destructive-git-blocker.sh (ADR-003 Mechanism C).

Validates that the PreToolUse Bash hook:
- BLOCKS destructive git ops (exit 1) when CLAUDE_AGENT_ID is set
- ALLOWS safe git read-only commands (exit 0)
- WARNS but allows destructive ops when no agent context is set
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "destructive-git-blocker.sh"


def _run(
    command: str,
    tmp_path: Path,
    agent_id: str | None = "agent-under-test",
) -> subprocess.CompletedProcess:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    if agent_id is not None:
        env["CLAUDE_AGENT_ID"] = agent_id
    else:
        env.pop("CLAUDE_AGENT_ID", None)

    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


class TestHookExists:

    def test_hook_is_valid_bash(self):
        result = subprocess.run(["bash", "-n", str(HOOK)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr


class TestDestructiveBlocks:
    """All destructive ops must be blocked when an agent context is active."""

    def test_blocks_git_stash_pop(self, tmp_path: Path):
        result = _run("git stash pop", tmp_path)
        assert result.returncode == 1, f"expected block, got {result.returncode}\n{result.stderr}"
        assert "BLOCKED" in result.stderr
        assert "git stash pop" in result.stderr

    def test_blocks_git_stash_drop(self, tmp_path: Path):
        result = _run("git stash drop", tmp_path)
        assert result.returncode == 1
        assert "BLOCKED" in result.stderr

    def test_blocks_git_stash_apply(self, tmp_path: Path):
        result = _run("git stash apply", tmp_path)
        assert result.returncode == 1
        assert "BLOCKED" in result.stderr

    def test_blocks_git_reset_hard(self, tmp_path: Path):
        result = _run("git reset --hard HEAD", tmp_path)
        assert result.returncode == 1
        assert "BLOCKED" in result.stderr
        assert "git reset --hard" in result.stderr

    def test_blocks_git_checkout_dash(self, tmp_path: Path):
        result = _run("git checkout -- src/foo.py", tmp_path)
        assert result.returncode == 1
        assert "BLOCKED" in result.stderr
        assert "git checkout --" in result.stderr

    def test_blocks_git_clean_f(self, tmp_path: Path):
        result = _run("git clean -fd", tmp_path)
        assert result.returncode == 1
        assert "BLOCKED" in result.stderr

    def test_blocks_git_worktree(self, tmp_path: Path):
        result = _run("git worktree add ../foo", tmp_path)
        assert result.returncode == 1
        assert "BLOCKED" in result.stderr

    def test_blocks_git_restore(self, tmp_path: Path):
        result = _run("git restore src/foo.py", tmp_path)
        assert result.returncode == 1
        assert "BLOCKED" in result.stderr

    def test_blocks_git_revert(self, tmp_path: Path):
        result = _run("git revert HEAD", tmp_path)
        assert result.returncode == 1
        assert "BLOCKED" in result.stderr


class TestSafeOpsAllowed:
    """Safe / read-only git ops must pass through silently."""

    def test_allows_safe_git_status(self, tmp_path: Path):
        result = _run("git status", tmp_path)
        assert result.returncode == 0
        assert "BLOCKED" not in result.stderr

    def test_allows_safe_git_diff(self, tmp_path: Path):
        result = _run("git diff --name-only", tmp_path)
        assert result.returncode == 0
        assert "BLOCKED" not in result.stderr

    def test_allows_safe_git_log(self, tmp_path: Path):
        result = _run("git log --oneline -5", tmp_path)
        assert result.returncode == 0

    def test_allows_non_git_command(self, tmp_path: Path):
        result = _run("ls -la", tmp_path)
        assert result.returncode == 0

    def test_allows_git_stash_list(self, tmp_path: Path):
        # 'git stash list' is read-only, must NOT match the destructive pattern
        result = _run("git stash list", tmp_path)
        assert result.returncode == 0


class TestUserContext:
    """Without CLAUDE_AGENT_ID, destructive ops warn but are allowed."""

    def test_warns_user_context_but_allows(self, tmp_path: Path):
        result = _run("git stash pop", tmp_path, agent_id=None)
        assert result.returncode == 0, (
            f"expected allowed (exit 0) for user context, got {result.returncode}\n"
            f"stderr={result.stderr}"
        )
        assert "WARN" in result.stderr
        assert "git stash pop" in result.stderr


class TestLogging:
    """Block + warn events are recorded to the metrics log."""

    def test_block_is_logged(self, tmp_path: Path):
        result = _run("git stash pop", tmp_path, agent_id="log-test-agent")
        assert result.returncode == 1

        log = tmp_path / ".cognitive-os" / "metrics" / "git-op-blocks.jsonl"
        assert log.exists(), f"block log missing: {log}"
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert entry["event"] == "blocked"
        assert entry["agent_id"] == "log-test-agent"
        assert "git stash pop" in entry["op"]
