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


@pytest.mark.behavior
def test_cos_rollback_files_and_conversation_restore(project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lib.session_bus import append_session_event, read_session_events

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
    append_session_event("before", {}, project_dir=repo, session_id="s1", single_writer=True)
    append_session_event("after", {}, project_dir=repo, session_id="s1", single_writer=True)
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
        [
            str(project_root / "scripts" / "cos-rollback"),
            "--project-dir",
            str(repo),
            "--session-id",
            "s1",
            "--tree-sha",
            tree_sha,
            "--restore",
            "--mode",
            "files_and_conversation",
            "--target-seq",
            "1",
            "--preview-path",
            preview_path,
            "--yes",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert restored.returncode == 0, restored.stderr
    payload = json.loads(restored.stdout)
    assert payload["mode"] == "files_and_conversation"
    assert (repo / "file.txt").read_text(encoding="utf-8") == "before\n"
    assert [event["event_type"] for event in read_session_events("s1", project_dir=repo)] == ["before", "shadow-git-restore"]

@pytest.mark.behavior
def test_cos_rollback_prune_shadow_snapshots(project_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    pruned = subprocess.run(
        [str(project_root / "scripts" / "cos-rollback"), "--project-dir", str(repo), "--prune", "--max-age-seconds", "0", "--yes", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert pruned.returncode == 0, pruned.stderr
    payload = json.loads(pruned.stdout)
    assert payload["status"] == "ok"
    assert payload["candidates"][0]["pruned"] is True
