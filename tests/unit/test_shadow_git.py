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


def test_restore_conversation_only_truncates_session_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lib.session_bus import append_session_event, read_session_events

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.setenv("COS_SHADOW_GIT_BASE", str(tmp_path / "shadow"))
    snap = snapshot(repo, "s1")
    append_session_event("step-one", {"n": 1}, project_dir=repo, session_id="s1", single_writer=True)
    append_session_event("step-two", {"n": 2}, project_dir=repo, session_id="s1", single_writer=True)
    append_session_event("step-three", {"n": 3}, project_dir=repo, session_id="s1", single_writer=True)

    result = restore(repo, "s1", snap.tree_sha, mode="conversation_only", target_seq=2, yes=True)

    events = read_session_events("s1", project_dir=repo)
    assert result["event_seq"] == 3
    assert [event["event_type"] for event in events] == ["step-one", "step-two", "shadow-git-restore"]
    assert events[-1]["payload"]["file_tree_sha"] == snap.tree_sha


def test_restore_files_and_conversation_is_single_operation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lib.session_bus import append_session_event, read_session_events

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.setenv("COS_SHADOW_GIT_BASE", str(tmp_path / "shadow"))
    (repo / "note.txt").write_text("checkpoint\n", encoding="utf-8")
    snap = snapshot(repo, "s1")
    append_session_event("before", {}, project_dir=repo, session_id="s1", single_writer=True)
    append_session_event("after", {}, project_dir=repo, session_id="s1", single_writer=True)
    (repo / "tracked.txt").write_text("mutated\n", encoding="utf-8")
    (repo / "note.txt").unlink()
    (repo / "later.txt").write_text("later\n", encoding="utf-8")
    preview_path = preview(repo, "s1", snap.tree_sha)

    result = restore(
        repo,
        "s1",
        snap.tree_sha,
        mode="files_and_conversation",
        preview_path=preview_path,
        target_seq=1,
        yes=True,
    )

    assert result["event_seq"] == 2
    assert (repo / "tracked.txt").read_text(encoding="utf-8") == "v1\n"
    assert (repo / "note.txt").read_text(encoding="utf-8") == "checkpoint\n"
    assert not (repo / "later.txt").exists()
    events = read_session_events("s1", project_dir=repo)
    assert [event["event_type"] for event in events] == ["before", "shadow-git-restore"]
    assert events[-1]["payload"]["mode"] == "files_and_conversation"


def test_snapshot_event_wires_file_tree_sha_into_event_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lib.session_bus import read_session_events
    from lib.shadow_git import snapshot_event

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.setenv("COS_SHADOW_GIT_BASE", str(tmp_path / "shadow"))

    event = snapshot_event(repo, "s1", "governance-check", {"status": "pass"})

    assert event["payload"]["status"] == "pass"
    assert len(event["payload"]["file_tree_sha"]) == 40
    assert read_session_events("s1", project_dir=repo)[0]["payload"]["file_tree_sha"] == event["payload"]["file_tree_sha"]


def test_prune_expired_snapshots_dry_run_and_execute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from lib.shadow_git import prune_expired_snapshots

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.setenv("COS_SHADOW_GIT_BASE", str(tmp_path / "shadow"))
    snap = snapshot(repo, "s-old")

    dry = prune_expired_snapshots(repo, max_age_seconds=0, execute=False)
    assert dry["count"] == 1
    assert Path(snap.shadow_repo).exists()

    executed = prune_expired_snapshots(repo, max_age_seconds=0, execute=True)
    assert executed["candidates"][0]["pruned"] is True
    assert not Path(snap.shadow_repo).exists()
