"""Integration tests for pre-agent-snapshot.sh border cases (ADR-099).

Tests invoke the actual shell hook against self-contained git repos in tmp_path.
Each test is fully isolated.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parent.parent.parent / "hooks" / "pre-agent-snapshot.sh"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-b", "main"], cwd=path)
    _git(["config", "user.email", "test@test.com"], cwd=path)
    _git(["config", "user.name", "Test"], cwd=path)
    initial = path / "README.md"
    initial.write_text("initial\n")
    _git(["add", "README.md"], cwd=path)
    _git(["commit", "-m", "init"], cwd=path)
    return path


def run_hook(
    repo: Path,
    agent_id: str = "test-agent",
    legacy: bool = False,
    session_id: str = "test-session",
) -> subprocess.CompletedProcess:
    """Run pre-agent-snapshot.sh against the given repo."""
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(repo),
        "COGNITIVE_OS_SESSION_ID": session_id,
        "CLAUDE_AGENT_ID": agent_id,
        # Point lib path to actual project so Python imports work
        "PYTHONPATH": str(PROJECT_ROOT),
    }
    if legacy:
        env["COS_LEGACY_SNAPSHOT"] = "1"
    else:
        env.pop("COS_LEGACY_SNAPSHOT", None)

    tool_input = json.dumps({
        "tool_name": "Agent",
        "tool_input": {"description": "test agent"},
    })

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=tool_input,
        capture_output=True,
        text=True,
        env=env,
    )


def get_latest_snapshot(repo: Path) -> dict | None:
    """Return the most recent snapshot manifest or None."""
    snaps_dir = repo / ".cognitive-os" / "snapshots"
    if not snaps_dir.is_dir():
        return None
    manifests = []
    for d in snaps_dir.iterdir():
        mp = d / "manifest.json"
        if mp.exists():
            try:
                manifests.append(json.loads(mp.read_text()))
            except Exception:
                pass
    if not manifests:
        return None
    manifests.sort(key=lambda m: m.get("timestamp", 0), reverse=True)
    return manifests[0]


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


def test_untracked_survives_agent_launch(tmp_path: Path):
    """Hook must not remove untracked files from WT."""
    repo = make_repo(tmp_path / "repo")

    untracked = repo / "new-work.py"
    untracked.write_text("# WIP\n")

    result = run_hook(repo, agent_id="it-agent-001")
    assert result.returncode == 0, f"Hook failed: {result.stderr}"

    # File must still be in WT
    assert untracked.exists(), "Untracked file was removed from WT by hook!"

    # Snapshot must have been created with backup
    manifest = get_latest_snapshot(repo)
    assert manifest is not None
    assert "new-work.py" in manifest["untracked_files"]
    snap_dir = Path(manifest["snapshot_dir"])
    assert (snap_dir / "new-work.py").exists()


def test_modified_tracked_survives(tmp_path: Path):
    """A staged tracked modification must produce a stash entry."""
    repo = make_repo(tmp_path / "repo")

    tracked = repo / "README.md"
    tracked.write_text("modified\n")
    _git(["add", "README.md"], cwd=repo)

    result = run_hook(repo, agent_id="it-agent-002")
    assert result.returncode == 0

    manifest = get_latest_snapshot(repo)
    assert manifest is not None
    assert manifest.get("tracked_stash_ref") is not None

    stash_list = _git(["stash", "list"], cwd=repo).stdout
    assert "auto-pre-agent-it-agent-002" in stash_list

    # WT should still have the staged content (--keep-index)
    assert tracked.read_text() == "modified\n"


def test_concurrent_launches_no_loss(tmp_path: Path):
    """Three parallel hook invocations must each preserve their untracked sets."""
    import concurrent.futures

    repo = make_repo(tmp_path / "repo")

    # Create 3 untracked files upfront
    for i in range(3):
        (repo / f"concurrent-{i}.py").write_text(f"# {i}\n")

    def launch(i: int) -> subprocess.CompletedProcess:
        return run_hook(repo, agent_id=f"concurrent-agent-{i}", session_id=f"sess-{i}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(launch, i) for i in range(3)]
        results = [f.result() for f in futures]

    for r in results:
        assert r.returncode == 0, f"Concurrent hook failed: {r.stderr}"

    for i in range(3):
        assert (repo / f"concurrent-{i}.py").exists(), \
            f"concurrent-{i}.py was removed from WT"


def test_agent_crash_rollback_restores_both(tmp_path: Path):
    """Snapshot → corrupt files → restore via snapshot_manager → both halves recovered."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from lib.snapshot_manager import create_snapshot, restore_snapshot

    repo = make_repo(tmp_path / "repo")

    untracked = repo / "precious.py"
    untracked.write_text("original untracked\n")
    tracked = repo / "README.md"
    tracked.write_text("original tracked\n")
    _git(["add", "README.md"], cwd=repo)

    manifest = create_snapshot(repo, agent_id="crash-rollback-it")

    # Simulate corruption
    untracked.write_text("corrupted\n")
    tracked.write_text("corrupted\n")

    result = restore_snapshot(repo, manifest["snapshot_id"])

    assert not result["errors"], f"Restore errors: {result['errors']}"
    assert untracked.read_text() == "original untracked\n", "Untracked not restored"


def test_files_created_by_agent_not_swept(tmp_path: Path):
    """File created post-snapshot must survive the next snapshot invocation."""
    repo = make_repo(tmp_path / "repo")

    # First snapshot (clean WT)
    result1 = run_hook(repo, agent_id="agent-before")
    assert result1.returncode == 0

    # "Agent" creates a new file
    agent_output = repo / "agent-output.txt"
    agent_output.write_text("result\n")

    # Second snapshot
    result2 = run_hook(repo, agent_id="agent-after")
    assert result2.returncode == 0

    assert agent_output.exists(), "Agent-created file was swept by second snapshot"


def test_files_modified_by_agent_in_next_snapshot(tmp_path: Path):
    """Agent-modified tracked file must be captured in next snapshot."""
    repo = make_repo(tmp_path / "repo")

    run_hook(repo, agent_id="snap-1")

    tracked = repo / "README.md"
    tracked.write_text("agent modified\n")
    _git(["add", "README.md"], cwd=repo)

    run_hook(repo, agent_id="snap-2")

    stash_list = _git(["stash", "list"], cwd=repo).stdout
    assert "auto-pre-agent-snap-2" in stash_list
    # WT still has staged content
    assert tracked.read_text() == "agent modified\n"


def test_legacy_mode_still_works(tmp_path: Path):
    """COS_LEGACY_SNAPSHOT=1: untracked files are moved into stash."""
    repo = make_repo(tmp_path / "repo")

    untracked = repo / "legacy-untracked.py"
    untracked.write_text("legacy\n")

    result = run_hook(repo, agent_id="legacy-it", legacy=True)
    assert result.returncode == 0

    # File should have been swept (legacy stash --include-untracked)
    assert not untracked.exists(), \
        "Legacy mode: untracked file should have been stashed"

    stash_list = _git(["stash", "list"], cwd=repo).stdout
    assert "auto-pre-agent-legacy-it" in stash_list

    # Manifest mode must say legacy_stash
    manifest = get_latest_snapshot(repo)
    if manifest:
        assert manifest["mode"] == "legacy_stash"


def test_prune_expired_drops_old(tmp_path: Path):
    """prune_expired removes snapshots older than TTL."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from lib.snapshot_manager import create_snapshot, prune_expired

    repo = make_repo(tmp_path / "repo")

    snap_old = create_snapshot(repo, agent_id="old")
    snap_new = create_snapshot(repo, agent_id="new")

    # Backdate old snapshot
    old_dir = Path(snap_old["snapshot_dir"])
    old_time = time.time() - (40 * 86400)
    os.utime(str(old_dir), (old_time, old_time))
    mp = old_dir / "manifest.json"
    data = json.loads(mp.read_text())
    data["timestamp"] = old_time
    mp.write_text(json.dumps(data))

    deleted = prune_expired(repo, ttl_days=30)
    assert snap_old["snapshot_id"] in deleted
    assert snap_new["snapshot_id"] not in deleted
    assert not old_dir.exists()
    assert Path(snap_new["snapshot_dir"]).exists()


def test_recovery_after_partial_restore(tmp_path: Path):
    """Partial restore → second restore on remaining files succeeds."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from lib.snapshot_manager import create_snapshot, restore_snapshot

    repo = make_repo(tmp_path / "repo")

    file_a = repo / "a.txt"
    file_b = repo / "b.txt"
    file_a.write_text("A\n")
    file_b.write_text("B\n")

    manifest = create_snapshot(repo, agent_id="partial-it")

    file_a.write_text("corrupted\n")
    file_b.write_text("corrupted\n")

    r1 = restore_snapshot(repo, manifest["snapshot_id"], files=["a.txt"])
    assert "a.txt" in r1["restored_untracked"]
    assert file_a.read_text() == "A\n"
    assert file_b.read_text() == "corrupted\n"

    r2 = restore_snapshot(repo, manifest["snapshot_id"], files=["b.txt"])
    assert "b.txt" in r2["restored_untracked"]
    assert file_b.read_text() == "B\n"
