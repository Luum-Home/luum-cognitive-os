"""Unit tests for hooks/destructive-git-blocker.sh — ADR-055b block elevation.

Verifies the block-by-default semantics introduced in ADR-055b (decision #6,
r5-stash-residue closure):

- Destructive git ops are BLOCKED in BOTH agent and user context
- Overrides: COS_ALLOW_DESTRUCTIVE_GIT=1 env, `--allow-destructive` inline flag
- Bypass contexts: CI=1, PYTEST_CURRENT_TEST, COS_GIT_BYPASS=1
- New ops covered: git branch -D, git rebase --abort
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "destructive-git-blocker.sh"

# Base env: scrub every variable the hook checks for bypass/override, so each
# test starts from a clean baseline and only re-adds what it needs.
SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_GIT_BYPASS",
    "COS_ALLOW_DESTRUCTIVE_GIT",
    "CLAUDE_AGENT_ID",
    "COGNITIVE_OS_SESSION_ID",
    "ORCHESTRATOR_MODE",
)


def _run(
    command: str,
    tmp_path: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    env = os.environ.copy()
    for var in SCRUB_VARS:
        env.pop(var, None)
    env.update({
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
    })
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Destructive ops blocked in user context (ADR-055b elevation)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command,expected_op_fragment",
    [
        ("git reset --hard HEAD~1", "git reset --hard"),
        ("git checkout -- src/foo.py", "git checkout --"),
        ("git checkout HEAD -- src/foo.py", "git checkout --"),
        ("git clean -fd", "git clean -f"),
        ("git clean -fdx", "git clean -f"),
        ("git branch -D feature-x", "git branch -D"),
        ("git stash pop", "git stash pop"),
        ("git stash drop", "git stash drop"),
        ("git stash apply", "git stash apply"),
        ("git rebase --abort", "git rebase --abort"),
        ("git restore src/foo.py", "git restore"),
        ("git revert HEAD", "git revert"),
        ("git worktree add ../foo", "git worktree"),
    ],
)
def test_user_context_blocks_destructive_op(
    tmp_path: Path, command: str, expected_op_fragment: str
):
    """Every destructive op pattern is blocked (exit 2) in user context."""
    result = _run(command, tmp_path)
    assert result.returncode == 2, (
        f"expected block (exit 2) for `{command}`, got {result.returncode}\n"
        f"stderr={result.stderr}"
    )
    assert "BLOCKED" in result.stderr
    assert expected_op_fragment in result.stderr


# ---------------------------------------------------------------------------
# Override mechanisms
# ---------------------------------------------------------------------------


def test_env_override_allows_destructive_op(tmp_path: Path):
    """COS_ALLOW_DESTRUCTIVE_GIT=1 permits the command (exit 0)."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"COS_ALLOW_DESTRUCTIVE_GIT": "1"},
    )
    assert result.returncode == 0, result.stderr
    assert "OVERRIDE ACCEPTED" in result.stderr


def test_inline_flag_override_allows_destructive_op(tmp_path: Path):
    """`--allow-destructive` token in command permits (exit 0)."""
    result = _run("git reset --hard HEAD~1 --allow-destructive", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "OVERRIDE ACCEPTED" in result.stderr


def test_inline_flag_override_anywhere_in_command(tmp_path: Path):
    """Flag is recognized as a whole token regardless of position."""
    result = _run("git --allow-destructive reset --hard HEAD~1", tmp_path)
    assert result.returncode == 0, result.stderr


def test_env_override_non_one_value_still_blocks(tmp_path: Path):
    """Only literal COS_ALLOW_DESTRUCTIVE_GIT=1 unlocks; other truthy strings block."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"COS_ALLOW_DESTRUCTIVE_GIT": "true"},
    )
    assert result.returncode == 2, (
        f"only literal '1' should override; got {result.returncode}\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Bypass contexts (SO-internal — not user-initiated)
# ---------------------------------------------------------------------------


def test_ci_bypass_allows_destructive_op(tmp_path: Path):
    """CI=1 bypass lets CI jobs reset/checkout without override flags."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"CI": "1"},
    )
    assert result.returncode == 0, result.stderr


def test_ci_bypass_true_value_also_works(tmp_path: Path):
    """CI='true' (GitHub Actions default) also bypasses."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"CI": "true"},
    )
    assert result.returncode == 0, result.stderr


def test_pytest_bypass_allows_destructive_op(tmp_path: Path):
    """PYTEST_CURRENT_TEST set → bypass (tests may clean up state)."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"PYTEST_CURRENT_TEST": "some::test"},
    )
    assert result.returncode == 0, result.stderr


def test_cos_git_bypass_allows_destructive_op(tmp_path: Path):
    """COS_GIT_BYPASS=1 for reaper/watchdog/sandbox contexts."""
    result = _run(
        "git reset --hard HEAD~1",
        tmp_path,
        extra_env={"COS_GIT_BYPASS": "1"},
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Safe ops and non-git commands pass through silently
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git diff",
        "git log --oneline -5",
        "git show HEAD",
        "git stash list",
        "git branch --list",  # non-destructive (no -D)
        "git rebase --continue",  # non-destructive rebase subcommand
        "ls -la",
        "pwd",
    ],
)
def test_safe_ops_pass_through(tmp_path: Path, command: str):
    """Safe commands exit 0 with no BLOCKED message."""
    result = _run(command, tmp_path)
    assert result.returncode == 0, (
        f"expected pass-through for `{command}`, got {result.returncode}\n"
        f"stderr={result.stderr}"
    )
    assert "BLOCKED" not in result.stderr


# ---------------------------------------------------------------------------
# Override error-message contents (human-friendly guidance)
# ---------------------------------------------------------------------------


def test_block_message_includes_rationale(tmp_path: Path):
    result = _run("git stash pop", tmp_path)
    assert result.returncode == 2
    assert "Rationale:" in result.stderr
    # Specific rationale for stash ops mentions r5
    assert "r5" in result.stderr.lower() or "stash" in result.stderr.lower()


def test_block_message_includes_override_instructions(tmp_path: Path):
    result = _run("git reset --hard", tmp_path)
    assert result.returncode == 2
    assert "COS_ALLOW_DESTRUCTIVE_GIT" in result.stderr
    assert "--allow-destructive" in result.stderr


# ---------------------------------------------------------------------------
# JSONL audit trail
# ---------------------------------------------------------------------------


def test_user_context_block_is_logged(tmp_path: Path):
    result = _run("git stash pop", tmp_path)
    assert result.returncode == 2
    log = tmp_path / ".cognitive-os" / "metrics" / "git-op-blocks.jsonl"
    assert log.exists(), f"block log missing: {log}"
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    entry = json.loads(lines[-1])
    assert entry["event"] == "blocked"
    assert entry["context"] == "user"


def test_override_is_logged_with_reason(tmp_path: Path):
    result = _run(
        "git reset --hard",
        tmp_path,
        extra_env={"COS_ALLOW_DESTRUCTIVE_GIT": "1"},
    )
    assert result.returncode == 0
    log = tmp_path / ".cognitive-os" / "metrics" / "git-op-blocks.jsonl"
    assert log.exists()
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    entry = json.loads(lines[-1])
    assert entry["event"] == "override"
    assert entry["reason"] == "session_env"


def test_bypass_is_logged(tmp_path: Path):
    result = _run(
        "git reset --hard",
        tmp_path,
        extra_env={"CI": "1"},
    )
    assert result.returncode == 0
    log = tmp_path / ".cognitive-os" / "metrics" / "git-op-blocks.jsonl"
    assert log.exists()
    lines = [l for l in log.read_text().splitlines() if l.strip()]
    entry = json.loads(lines[-1])
    assert entry["event"] == "bypassed"
    assert entry["reason"] == "so_internal_context"
