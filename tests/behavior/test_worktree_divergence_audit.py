from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "lib" / "worktree_audit.py"
pytestmark = pytest.mark.behavior


def run(cmd: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init", "-q", "-b", "main"], repo)
    run(["git", "config", "user.email", "test@example.invalid"], repo)
    run(["git", "config", "user.name", "Test User"], repo)
    (repo / "app.txt").write_text("base\n")
    run(["git", "add", "app.txt"], repo)
    run(["git", "commit", "-q", "-m", "base"], repo)
    return repo


def audit(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDIT), "--project-dir", str(repo), "--json", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_worktree_audit_blocks_when_stale_worktree_dirty_path_was_changed_on_main(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    run(["git", "checkout", "-q", "-b", "agent-work"], repo)
    worktree = tmp_path / "agent-worktree"
    run(["git", "checkout", "-q", "main"], repo)
    run(["git", "worktree", "add", "-q", str(worktree), "agent-work"], repo)

    (worktree / "app.txt").write_text("agent local wip\n")
    (repo / "app.txt").write_text("fix on main\n")
    run(["git", "add", "app.txt"], repo)
    run(["git", "commit", "-q", "-m", "main fix"], repo)

    result = audit(repo, "--against", "main", "--strict")
    assert result.returncode == 2, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "block"
    assert any(f["code"] == "path-conflict-pending" for f in payload["findings"])
    conflict = next(f for f in payload["findings"] if f["code"] == "path-conflict-pending")
    assert "app.txt" in conflict["detail"]


def test_worktree_audit_warns_when_worktree_is_behind_without_local_overlap(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    run(["git", "checkout", "-q", "-b", "agent-work"], repo)
    worktree = tmp_path / "agent-worktree"
    run(["git", "checkout", "-q", "main"], repo)
    run(["git", "worktree", "add", "-q", str(worktree), "agent-work"], repo)

    (repo / "other.txt").write_text("main-only\n")
    run(["git", "add", "other.txt"], repo)
    run(["git", "commit", "-q", "-m", "main adds other"], repo)

    result = audit(repo, "--against", "main", "--strict")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "warn"
    assert any(f["code"] == "silent-worktree-divergence" for f in payload["findings"])
