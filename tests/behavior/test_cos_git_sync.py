from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNC = REPO_ROOT / "scripts" / "cos-git-sync.sh"


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check, timeout=30)


def init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-b", "main"], path)
    run(["git", "config", "user.email", "test@example.invalid"], path)
    run(["git", "config", "user.name", "Test User"], path)


def commit_file(repo: Path, rel: str, content: str, message: str) -> str:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run(["git", "add", rel], repo)
    run(["git", "commit", "-m", message], repo)
    return run(["git", "rev-parse", "HEAD"], repo).stdout.strip()


@pytest.fixture
def remote_and_clone(tmp_path: Path) -> tuple[Path, Path, Path]:
    remote = tmp_path / "remote.git"
    run(["git", "init", "--bare", str(remote)], tmp_path)

    seed = tmp_path / "seed"
    init_repo(seed)
    commit_file(seed, "README.md", "initial\n", "initial")
    run(["git", "remote", "add", "origin", str(remote)], seed)
    run(["git", "push", "-u", "origin", "main"], seed)

    clone = tmp_path / "clone"
    run(["git", "clone", str(remote), str(clone)], tmp_path)
    run(["git", "config", "user.email", "test@example.invalid"], clone)
    run(["git", "config", "user.name", "Test User"], clone)
    return remote, seed, clone


def test_safe_sync_fast_forwards_when_possible(remote_and_clone: tuple[Path, Path, Path]) -> None:
    _, seed, clone = remote_and_clone
    remote_tip = commit_file(seed, "remote.txt", "remote\n", "remote update")
    run(["git", "push", "origin", "main"], seed)

    result = run(["bash", str(SYNC), "--repo", str(clone)], clone)

    assert result.returncode == 0
    assert "Action: fast-forward" in result.stdout
    assert run(["git", "rev-parse", "HEAD"], clone).stdout.strip() == remote_tip


def test_safe_sync_blocks_divergence_without_rebase(remote_and_clone: tuple[Path, Path, Path]) -> None:
    _, seed, clone = remote_and_clone
    local_tip = commit_file(clone, "local.txt", "local\n", "local update")
    commit_file(seed, "remote.txt", "remote\n", "remote update")
    run(["git", "push", "origin", "main"], seed)

    result = run(["bash", str(SYNC), "--repo", str(clone)], clone, check=False)

    assert result.returncode == 3
    assert "Status: BLOCK" in result.stdout
    assert "Action: diverged" in result.stdout
    assert "No rebase was performed" in result.stdout
    assert run(["git", "rev-parse", "HEAD"], clone).stdout.strip() == local_tip


def test_safe_sync_allows_explicit_merge_commit(remote_and_clone: tuple[Path, Path, Path]) -> None:
    _, seed, clone = remote_and_clone
    commit_file(clone, "local.txt", "local\n", "local update")
    commit_file(seed, "remote.txt", "remote\n", "remote update")
    run(["git", "push", "origin", "main"], seed)

    result = run(["bash", str(SYNC), "--repo", str(clone), "--merge"], clone)

    assert result.returncode == 0
    assert "Action: merge" in result.stdout
    parents = run(["git", "rev-list", "--parents", "-n", "1", "HEAD"], clone).stdout.split()
    assert len(parents) == 3


def test_safe_sync_reports_local_ahead_without_push_or_rebase(remote_and_clone: tuple[Path, Path, Path]) -> None:
    _, _, clone = remote_and_clone
    local_tip = commit_file(clone, "local.txt", "local\n", "local update")

    result = run(["bash", str(SYNC), "--repo", str(clone)], clone)

    assert result.returncode == 0
    assert "Status: WARN" in result.stdout
    assert "Action: local-ahead" in result.stdout
    assert run(["git", "rev-parse", "HEAD"], clone).stdout.strip() == local_tip
