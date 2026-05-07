from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from lib.shadow_git import RestorePreviewRequired, preview, restore, shadow_repo_path, snapshot  # noqa: E402


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "tracked.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


def test_snapshot_is_stable_off_repo_and_does_not_touch_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "untracked.txt").write_text("u1\n", encoding="utf-8")
    monkeypatch.setenv("COS_SHADOW_GIT_BASE", str(tmp_path / "shadow"))
    index_before = (repo / ".git" / "index").read_bytes()

    first = snapshot(repo, "s1")
    second = snapshot(repo, "s1")

    assert first.tree_sha == second.tree_sha
    assert Path(first.shadow_repo).is_dir()
    assert not Path(first.shadow_repo).resolve().is_relative_to(repo.resolve())
    assert (repo / ".git" / "index").read_bytes() == index_before
    assert subprocess.run(["git", "-C", str(repo), "stash", "list"], capture_output=True, text=True).stdout == ""


def test_preview_and_restore_files_only_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "untracked.txt").write_text("u1\n", encoding="utf-8")
    monkeypatch.setenv("COS_SHADOW_GIT_BASE", str(tmp_path / "shadow"))

    snap = snapshot(repo, "s1")
    (repo / "tracked.txt").write_text("v2\n", encoding="utf-8")
    (repo / "untracked.txt").unlink()
    (repo / "new.txt").write_text("new\n", encoding="utf-8")

    preview_path = preview(repo, "s1", snap.tree_sha)
    assert preview_path.is_file()
    with pytest.raises(RestorePreviewRequired):
        restore(repo, "s1", snap.tree_sha, preview_path=preview_path, yes=False)

    restore(repo, "s1", snap.tree_sha, preview_path=preview_path, yes=True)
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "v1\n"
    assert (repo / "untracked.txt").read_text(encoding="utf-8") == "u1\n"
    assert not (repo / "new.txt").exists()


def test_prune_path_is_session_scoped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.setenv("COS_SHADOW_GIT_BASE", str(tmp_path / "shadow"))
    snap = snapshot(repo, "s1")
    assert shadow_repo_path(repo, "s1") == Path(snap.shadow_repo)
