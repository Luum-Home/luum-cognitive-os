from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from lib.shadow_git import snapshot  # noqa: E402


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "file.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


@pytest.mark.audit
def test_shadow_git_snapshot_does_not_create_stash_or_mutate_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "file.txt").write_text("dirty\n", encoding="utf-8")
    monkeypatch.setenv("COS_SHADOW_GIT_BASE", str(tmp_path / "shadow"))
    index_before = (repo / ".git" / "index").read_bytes()

    snapshot(repo, "s1")

    assert (repo / ".git" / "index").read_bytes() == index_before
    assert subprocess.run(["git", "-C", str(repo), "stash", "list"], capture_output=True, text=True).stdout == ""
