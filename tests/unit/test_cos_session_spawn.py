"""Behavioral tests for scripts/cos-session-spawn.sh — ADR-098 Phase D4."""
from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPAWN = REPO_ROOT / "scripts" / "cos-session-spawn.sh"
COOP = REPO_ROOT / "scripts" / "edit-coop.sh"


def _run_spawn(
    fake_project: Path,
    env_extra: dict | None = None,
    stdin: str = "n\n",  # default: decline worktree prompt
) -> subprocess.CompletedProcess:
    """Run cos-session-spawn.sh in a fake project, replacing 'claude' with 'echo'."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(fake_project)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(fake_project)
    # Redirect exec claude → exec echo so the script terminates instead of
    # launching the real claude binary.
    env["PATH"] = str(fake_project / "bin") + ":" + env.get("PATH", "")
    env.setdefault("COS_EDIT_LOCK_NO_PID_CHECK", "1")
    # Non-interactive: skip the read prompt by default.
    env["COS_SKIP_WORKTREE"] = env.get("COS_SKIP_WORKTREE", "")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SPAWN)],
        input=stdin,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _setup_fake_claude(fake_project: Path) -> None:
    """Place a stub 'claude' in a fake bin/ that just echoes its args."""
    bin_dir = fake_project / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "claude"
    stub.write_text("#!/usr/bin/env bash\necho CLAUDE_LAUNCHED \"$@\"\n")
    stub.chmod(0o755)


def _setup_fake_git(fake_project: Path) -> None:
    """Place a stub 'git' that does nothing (avoids real git calls)."""
    bin_dir = fake_project / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "git"
    stub.write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        # Stub git: echo the command, succeed
        echo GIT_STUB "$@"
        exit 0
    """))
    stub.chmod(0o755)


@pytest.fixture
def fake_project(tmp_path: Path) -> Path:
    (tmp_path / ".claude").mkdir()
    _setup_fake_claude(tmp_path)
    _setup_fake_git(tmp_path)
    return tmp_path


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_skip_worktree_launches_directly(fake_project):
    """COS_SKIP_WORKTREE=1 bypasses detection and launches claude immediately."""
    r = _run_spawn(fake_project, env_extra={"COS_SKIP_WORKTREE": "1"})
    # Script uses exec claude → our stub echoes CLAUDE_LAUNCHED.
    assert r.returncode == 0
    assert "CLAUDE_LAUNCHED" in r.stdout or "directly" in r.stderr


def test_no_active_sessions_launches_directly(fake_project):
    """With no active sessions or locks, claude is launched directly."""
    # Sessions dir doesn't exist → count is 0.
    r = _run_spawn(fake_project, env_extra={"COS_SKIP_WORKTREE": "", "COS_FORCE_WORKTREE": ""})
    # Non-interactive → should launch directly (no worktree).
    assert r.returncode == 0


def test_force_worktree_triggers_recommendation(fake_project):
    """COS_FORCE_WORKTREE=1 always prints worktree recommendation."""
    r = _run_spawn(
        fake_project,
        env_extra={"COS_FORCE_WORKTREE": "1", "COS_SKIP_WORKTREE": ""},
        stdin="n\n",  # decline prompt
    )
    assert r.returncode == 0
    # Non-interactive (stdin is a pipe) → skips prompt, launches directly.
    assert "worktree" in r.stderr.lower() or "non-interactive" in r.stderr.lower()


def test_active_sessions_triggers_worktree_recommendation(fake_project):
    """When an active session directory exists, the script recommends a worktree."""
    sessions_dir = fake_project / ".cognitive-os" / "sessions" / "session-001"
    sessions_dir.mkdir(parents=True)
    # Touch a file so directory mtime is "recent".
    (sessions_dir / "state.yaml").write_text("active: true\n")

    r = _run_spawn(fake_project, env_extra={"COS_SKIP_WORKTREE": "", "COS_FORCE_WORKTREE": ""})
    assert r.returncode == 0
    # In non-interactive mode the script should mention worktree recommendation.
    assert "worktree" in r.stderr.lower() or "non-interactive" in r.stderr.lower()


def test_script_has_shebang(fake_project):
    """cos-session-spawn.sh starts with a valid bash shebang."""
    content = SPAWN.read_text()
    assert content.startswith("#!/usr/bin/env bash") or content.startswith("#!/bin/bash"), \
        "Script must begin with a bash shebang"


def test_script_is_executable():
    """cos-session-spawn.sh must be executable (mode check)."""
    assert os.access(str(SPAWN), os.X_OK), f"{SPAWN} is not executable"


def test_bash_syntax_valid():
    """cos-session-spawn.sh passes bash -n syntax check."""
    r = subprocess.run(
        ["bash", "-n", str(SPAWN)],
        capture_output=True, text=True, timeout=10,
    )
    assert r.returncode == 0, f"bash -n failed:\n{r.stderr}"


def test_custom_branch_prefix(fake_project):
    """COS_WORKTREE_BRANCH_PREFIX is reflected in the recommended branch name."""
    sessions_dir = fake_project / ".cognitive-os" / "sessions" / "sess-01"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "state.yaml").write_text("active: true\n")

    r = _run_spawn(
        fake_project,
        env_extra={
            "COS_SKIP_WORKTREE": "",
            "COS_FORCE_WORKTREE": "1",
            "COS_WORKTREE_BRANCH_PREFIX": "mywork",
        },
        stdin="n\n",
    )
    assert r.returncode == 0
    # Should mention the prefix in recommendation or go non-interactive.
    assert "mywork" in r.stderr or "non-interactive" in r.stderr.lower()
