from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "file.txt").write_text("before\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


@pytest.mark.behavior
def test_cos_rollback_snapshot_preview_restore_smoke(project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.setenv("COS_SHADOW_GIT_BASE", str(tmp_path / "shadow"))

    snap = subprocess.run(
        [str(project_root / "scripts" / "cos-rollback"), "--project-dir", str(repo), "--session-id", "s1", "--snapshot", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert snap.returncode == 0, snap.stderr
    tree_sha = json.loads(snap.stdout)["tree_sha"]
    (repo / "file.txt").write_text("after\n", encoding="utf-8")

    prev = subprocess.run(
        [str(project_root / "scripts" / "cos-rollback"), "--project-dir", str(repo), "--session-id", "s1", "--tree-sha", tree_sha, "--preview", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert prev.returncode == 0, prev.stderr
    preview_path = json.loads(prev.stdout)["preview_path"]

    restored = subprocess.run(
        [str(project_root / "scripts" / "cos-rollback"), "--project-dir", str(repo), "--session-id", "s1", "--tree-sha", tree_sha, "--restore", "--preview-path", preview_path, "--yes", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert restored.returncode == 0, restored.stderr
    assert (repo / "file.txt").read_text(encoding="utf-8") == "before\n"
