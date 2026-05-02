from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-session-branch.sh"


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    (path / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=path, check=True, capture_output=True, text=True)


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), "--repo", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_creates_deterministic_session_branch(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    result = _run(tmp_path, "--session-id", "abc123", "--slug", "Claim Gate Fix", "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["branch"] == "session/abc123-claim-gate-fix"


def test_switch_moves_to_session_branch(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    result = _run(tmp_path, "--session-id", "s1", "--slug", "work", "--switch")
    assert result.returncode == 0, result.stderr
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert branch == "session/s1-work"


def test_dirty_worktree_blocks_by_default(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    result = _run(tmp_path, "--session-id", "s1", "--slug", "dirty")
    assert result.returncode == 3
    assert "dirty worktree" in result.stderr


def test_existing_branch_is_idempotent(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    first = _run(tmp_path, "--session-id", "s1", "--slug", "repeat", "--json")
    second = _run(tmp_path, "--session-id", "s1", "--slug", "repeat", "--json")
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["action"] == "exists"
