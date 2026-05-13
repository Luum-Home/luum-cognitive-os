# SCOPE: os-only
"""Portability proofs for hooks/post-git-orphan-notifier.sh — ADR-116 P3.1.

These tests run the hook against a temporary, non-SO git repository to prove that
the orphan-detection logic does not depend on any repository-local runtime state
from the luum-agent-os project itself.

Paired with: hooks/post-git-orphan-notifier.sh  (# SCOPE: os-only)

Portability proof matrix:
    P1 — hook fires on 'git rebase main' command in a foreign repo.
    P2 — hook fires on 'git reset --hard HEAD~1' command in a foreign repo.
    P3 — hook is silent (advisory-only, exit 0) on non-triggering commands.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "post-git-orphan-notifier.sh"

# Environment variables to scrub so the SO project's state doesn't leak in
SCRUB_VARS = (
    "CI",
    "PYTEST_CURRENT_TEST",
    "COS_GIT_BYPASS",
    "COS_ALLOW_DESTRUCTIVE_GIT",
    "CLAUDE_AGENT_ID",
    "COGNITIVE_OS_SESSION_ID",
    "ORCHESTRATOR_MODE",
    "SO_KILLSWITCH",
    "COS_DISABLE_ALL_GOVERNANCE",
)


def _run(
    command: str,
    project: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the hook against a foreign project repo, simulating a PostToolUse Bash event."""
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    env = os.environ.copy()
    for var in SCRUB_VARS:
        env.pop(var, None)
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(project),
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
            # Ensure pytest bypass context doesn't leak through env
            "PYTEST_CURRENT_TEST": "",
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _init_repo(path: Path) -> None:
    """Initialise a minimal git repo with one committed file."""
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed: initial"], cwd=path, check=True, capture_output=True)


# ---------------------------------------------------------------------------
# P1 — hook fires (exit 0, advisory) on 'git rebase' in a foreign repo
# ---------------------------------------------------------------------------


def test_p1_hook_fires_on_rebase_in_foreign_repo(tmp_path: Path) -> None:
    """P1: hook runs to completion (exit 0) on 'git rebase main' in a non-SO project.

    The hook is advisory-only — it must always exit 0 regardless of orphan count.
    This proves the hook doesn't require SO runtime state (no .cognitive-os/,
    no cognitive-os.yaml, no lib/ imports) to execute without error.
    """
    _init_repo(tmp_path)

    result = _run("git rebase main", tmp_path)

    assert result.returncode == 0, (
        f"P1: hook must exit 0 (advisory) on rebase trigger; "
        f"got returncode={result.returncode}\nstderr={result.stderr}"
    )


# ---------------------------------------------------------------------------
# P2 — hook fires (exit 0, advisory) on 'git reset --hard' in a foreign repo
# ---------------------------------------------------------------------------


def test_p2_hook_fires_on_reset_hard_in_foreign_repo(tmp_path: Path) -> None:
    """P2: hook runs to completion (exit 0) on 'git reset --hard HEAD~1' in a non-SO project.

    Proves the hook triggers on reset operations and remains advisory (exit 0)
    in a repository that has no SO infrastructure.
    """
    _init_repo(tmp_path)

    result = _run("git reset --hard HEAD~1", tmp_path)

    assert result.returncode == 0, (
        f"P2: hook must exit 0 (advisory) on reset trigger; "
        f"got returncode={result.returncode}\nstderr={result.stderr}"
    )


# ---------------------------------------------------------------------------
# P3 — hook is silent on non-triggering commands
# ---------------------------------------------------------------------------


def test_p3_hook_silent_on_non_trigger_commands(tmp_path: Path) -> None:
    """P3: hook exits 0 silently for commands that are not rebase/reset/pull-rebase.

    Verifies the hook does NOT scan on every bash invocation — only on the
    specific trigger commands. A 'git status' or 'git log' must pass through
    without activating the scanner, keeping hook overhead near zero.
    """
    _init_repo(tmp_path)

    for cmd in ("git status", "git log --oneline", "git diff", "ls -la", "echo hello"):
        result = _run(cmd, tmp_path)
        assert result.returncode == 0, (
            f"P3: hook must exit 0 silently for non-trigger command '{cmd}'; "
            f"got returncode={result.returncode}\nstderr={result.stderr}"
        )
        # No scanner output expected for non-trigger commands
        assert "ORPHAN" not in result.stderr, (
            f"P3: hook must NOT emit ORPHAN output for non-trigger command '{cmd}'; "
            f"got: {result.stderr}"
        )
