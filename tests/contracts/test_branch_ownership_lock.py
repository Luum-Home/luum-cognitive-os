from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from lib.branch_lock import acquire, holder, release, renew

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "branch-ownership-lock.sh"


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, stdout=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=path, check=True, stdout=subprocess.PIPE)


def test_second_session_is_blocked_from_destructive_git(tmp_path: Path) -> None:
    init_repo(tmp_path)
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=tmp_path, text=True).strip()
    first = acquire(tmp_path, branch=branch, session_id="s1", pid=os.getpid(), worktree=tmp_path)
    assert first["status"] == "acquired"

    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "s2"}
    res = subprocess.run(["bash", str(HOOK)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)

    assert res.returncode == 2
    assert "BRANCH OWNERSHIP LOCK" in res.stderr
    assert "s1" in res.stderr


def test_release_and_renew(tmp_path: Path) -> None:
    result = acquire(tmp_path, branch="session/test", session_id="s1", pid=os.getpid(), worktree=tmp_path, ttl_seconds=60)
    assert result["status"] == "acquired"
    before = holder(tmp_path, "session/test")
    assert before
    assert renew(tmp_path, branch="session/test", session_id="s1", ttl_seconds=120) is True
    after = holder(tmp_path, "session/test")
    assert after and after["expires_at_epoch"] >= before["expires_at_epoch"]
    assert release(tmp_path, branch="session/test", session_id="s1") is True
    assert holder(tmp_path, "session/test") is None
