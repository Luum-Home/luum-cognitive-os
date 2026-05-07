from __future__ import annotations

import subprocess
from pathlib import Path

from lib.stash_sha import list_stashes, resolve_sha_to_ref, resolve_top_stash_sha


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def make_repo(path: Path) -> Path:
    path.mkdir()
    _git(["init", "-b", "main"], path)
    _git(["config", "user.email", "test@example.invalid"], path)
    _git(["config", "user.name", "Test"], path)
    (path / "file.txt").write_text("base\n")
    _git(["add", "file.txt"], path)
    _git(["commit", "-m", "base"], path)
    return path


def test_resolves_stash_sha_after_position_drift(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    (repo / "file.txt").write_text("first\n")
    _git(["stash", "push", "-m", "auto-pre-agent-first", "--", "file.txt"], repo)
    first_sha = resolve_top_stash_sha(repo)
    assert first_sha

    (repo / "file.txt").write_text("second\n")
    _git(["stash", "push", "-m", "auto-pre-agent-second", "--", "file.txt"], repo)

    assert resolve_top_stash_sha(repo) != first_sha
    assert resolve_sha_to_ref(repo, first_sha) == "stash@{1}"
    entries = list_stashes(repo)
    assert any(entry.sha == first_sha and entry.ref == "stash@{1}" for entry in entries)
