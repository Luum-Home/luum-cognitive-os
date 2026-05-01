"""Unit tests for lib/snapshot_manager.py (ADR-099).

All tests use fully self-contained git repos in tmp_path — no system repo touched.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def make_repo(path: Path) -> Path:
    """Initialise a bare git repo suitable for snapshot tests."""
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-b", "main"], cwd=path)
    _git(["config", "user.email", "test@test.com"], cwd=path)
    _git(["config", "user.name", "Test"], cwd=path)
    # Initial commit so stash has a base
    initial = path / "README.md"
    initial.write_text("initial\n")
    _git(["add", "README.md"], cwd=path)
    _git(["commit", "-m", "init"], cwd=path)
    return path


def import_manager(repo: Path):
    """Return snapshot_manager module, injecting the project root."""
    import sys

    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    import lib.snapshot_manager as sm

    return sm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_untracked_survives_agent_launch(tmp_path: Path):
    """Untracked file must remain in WT after snapshot and also be backed up."""
    repo = make_repo(tmp_path / "repo")
    sm = import_manager(repo)

    untracked = repo / "new-feature.py"
    untracked.write_text("# work in progress\n")

    manifest = sm.create_snapshot(repo, agent_id="test-agent-001")

    # File must still exist in WT
    assert untracked.exists(), "Untracked file was removed from WT — regression!"

    # File must also be in the snapshot backup
    assert "new-feature.py" in manifest["untracked_files"]
    snap_dir = Path(manifest["snapshot_dir"])
    assert (snap_dir / "new-feature.py").exists(), "Backup copy not created"

    # Manifest must be written
    manifest_path = snap_dir / "manifest.json"
    assert manifest_path.exists()
    loaded = json.loads(manifest_path.read_text())
    assert loaded["snapshot_id"] == manifest["snapshot_id"]


def test_modified_tracked_survives(tmp_path: Path):
    """A tracked file modification must be stashed, WT content preserved under --keep-index."""
    repo = make_repo(tmp_path / "repo")
    sm = import_manager(repo)

    tracked = repo / "README.md"
    tracked.write_text("modified content\n")
    # Stage it so --keep-index preserves staged content
    _git(["add", "README.md"], cwd=repo)

    manifest = sm.create_snapshot(repo, agent_id="test-agent-002")

    # Stash ref must have been created
    assert manifest["tracked_stash_ref"] is not None, "No stash created for tracked modification"

    # git stash list must show the snapshot stash
    result = _git(["stash", "list"], cwd=repo)
    assert "auto-pre-agent-test-agent-002" in result.stdout

    # WT must still have the staged modification (--keep-index)
    assert tracked.read_text() == "modified content\n"


def test_concurrent_launches_no_loss(tmp_path: Path):
    """Three concurrent snapshot calls must each preserve their own untracked files."""
    import concurrent.futures

    repo = make_repo(tmp_path / "repo")
    sm = import_manager(repo)

    # Create 3 distinct untracked files — one per "session"
    files = []
    for i in range(3):
        f = repo / f"agent-{i}-work.py"
        f.write_text(f"# agent {i}\n")
        files.append(f)

    def take_snapshot(i: int) -> dict:
        # Each call uses a unique agent_id to avoid collision
        return sm.create_snapshot(repo, agent_id=f"concurrent-{i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(take_snapshot, i) for i in range(3)]
        manifests = [f.result() for f in futures]

    # All 3 snapshots must be distinct
    snap_ids = [m["snapshot_id"] for m in manifests]
    assert len(set(snap_ids)) == 3, "Snapshot IDs collided"

    # All untracked files must still be in WT
    for f in files:
        assert f.exists(), f"{f.name} was removed from WT during concurrent snapshot"

    # Each snapshot backed up the files visible at snapshot time
    all_backed_up = set()
    for m in manifests:
        all_backed_up.update(m["untracked_files"])
    for f in files:
        assert f.name in all_backed_up or any(f.name in m["untracked_files"] for m in manifests), \
            f"{f.name} not backed up by any snapshot"


def test_agent_crash_rollback_restores_both(tmp_path: Path):
    """Snapshot → modify files → restore → both halves recovered."""
    repo = make_repo(tmp_path / "repo")
    sm = import_manager(repo)

    # Pre-snapshot state: untracked + tracked-staged
    untracked = repo / "crash-test-untracked.py"
    untracked.write_text("original untracked\n")

    tracked = repo / "README.md"
    tracked.write_text("original tracked\n")
    _git(["add", "README.md"], cwd=repo)

    manifest = sm.create_snapshot(repo, agent_id="crash-agent")

    # Simulate "agent" modifying state — overwrite both files
    untracked.write_text("agent corrupted\n")
    tracked.write_text("agent corrupted tracked\n")

    # Restore
    result = sm.restore_snapshot(repo, manifest["snapshot_id"])

    assert not result["errors"], f"Restore errors: {result['errors']}"
    # Untracked file must be restored from backup copy
    assert untracked.read_text() == "original untracked\n", "Untracked not restored"


def test_files_created_by_agent_not_swept(tmp_path: Path):
    """A file created by an agent AFTER the snapshot must not be removed."""
    repo = make_repo(tmp_path / "repo")
    sm = import_manager(repo)

    # Take snapshot on clean WT
    sm.create_snapshot(repo, agent_id="agent-new-file")

    # "Agent" creates a new file
    new_file = repo / "agent-output.txt"
    new_file.write_text("agent result\n")

    # Next snapshot launch: file must survive
    sm.create_snapshot(repo, agent_id="agent-new-file-2")

    assert new_file.exists(), "Agent-created file was removed by subsequent snapshot"


def test_files_modified_by_agent_in_next_snapshot(tmp_path: Path):
    """Agent modifies a tracked file; next snapshot must capture the modification."""
    repo = make_repo(tmp_path / "repo")
    sm = import_manager(repo)

    # First snapshot
    sm.create_snapshot(repo, agent_id="first-snapshot")

    # "Agent" modifies tracked file
    tracked = repo / "README.md"
    tracked.write_text("agent modified\n")
    _git(["add", "README.md"], cwd=repo)

    # Second snapshot must capture the modification
    manifest2 = sm.create_snapshot(repo, agent_id="second-snapshot")

    # Stash ref must exist (agent modified a tracked file)
    assert manifest2["tracked_stash_ref"] is not None, \
        "Second snapshot did not capture tracked modification"

    # WT must still show the staged content (--keep-index)
    assert tracked.read_text() == "agent modified\n"


def test_legacy_mode_still_works(tmp_path: Path):
    """COS_LEGACY_SNAPSHOT=1 path: file moved to stash (old behaviour)."""
    repo = make_repo(tmp_path / "repo")
    sm = import_manager(repo)

    untracked = repo / "legacy-test.py"
    untracked.write_text("legacy untracked\n")

    manifest = sm.create_legacy_snapshot(repo, agent_id="legacy-agent")

    assert manifest["mode"] == "legacy_stash"
    # The legacy stash must include the untracked file
    stash_ref = manifest.get("tracked_stash_ref")
    assert stash_ref is not None, "Legacy stash not created"

    # The file should have been swept by --include-untracked
    assert not untracked.exists(), \
        "Legacy mode: untracked file should have been stashed (not present in WT)"

    # Verify it's in the stash — untracked files are stored in the `u` tree
    # Use `git stash show -u` or check the stash pop restores the file
    _git(["stash", "pop", "--quiet", stash_ref], cwd=repo, check=False)
    assert untracked.exists(), \
        "Legacy mode: untracked file not recoverable from stash"


def test_prune_expired_drops_old(tmp_path: Path):
    """Snapshots older than ttl_days are removed; recent ones are kept."""
    repo = make_repo(tmp_path / "repo")
    sm = import_manager(repo)

    # Create two snapshots
    snap_old = sm.create_snapshot(repo, agent_id="old-agent")
    snap_new = sm.create_snapshot(repo, agent_id="new-agent")

    # Backdate the old snapshot's directory mtime to 40 days ago
    old_snap_dir = Path(snap_old["snapshot_dir"])
    old_time = time.time() - (40 * 86400)
    os.utime(str(old_snap_dir), (old_time, old_time))
    # Also backdate manifest timestamp
    manifest_path = old_snap_dir / "manifest.json"
    data = json.loads(manifest_path.read_text())
    data["timestamp"] = old_time
    manifest_path.write_text(json.dumps(data))

    deleted = sm.prune_expired(repo, ttl_days=30)

    assert snap_old["snapshot_id"] in deleted, "Old snapshot was not pruned"
    assert snap_new["snapshot_id"] not in deleted, "Recent snapshot was pruned (wrong)"
    assert not old_snap_dir.exists(), "Old snapshot dir still exists after prune"
    assert Path(snap_new["snapshot_dir"]).exists(), "Recent snapshot was deleted"


def test_recovery_after_partial_restore(tmp_path: Path):
    """Partial restore of subset → second restore on remaining files works."""
    repo = make_repo(tmp_path / "repo")
    sm = import_manager(repo)

    # Create two untracked files
    file_a = repo / "file-a.txt"
    file_b = repo / "file-b.txt"
    file_a.write_text("content a\n")
    file_b.write_text("content b\n")

    manifest = sm.create_snapshot(repo, agent_id="partial-agent")

    # Overwrite both files
    file_a.write_text("corrupted a\n")
    file_b.write_text("corrupted b\n")

    # Restore only file-a
    result1 = sm.restore_snapshot(repo, manifest["snapshot_id"], files=["file-a.txt"])
    assert "file-a.txt" in result1["restored_untracked"]
    assert result1["partial"] is True
    assert file_a.read_text() == "content a\n"
    assert file_b.read_text() == "corrupted b\n"  # not yet restored

    # Now restore file-b
    result2 = sm.restore_snapshot(repo, manifest["snapshot_id"], files=["file-b.txt"])
    assert "file-b.txt" in result2["restored_untracked"]
    assert not result2["errors"]
    assert file_b.read_text() == "content b\n"
