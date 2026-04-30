"""Behavioral tests for scripts/git-coop.sh (ADR-089 Layer 2).

Tests execute the shell script directly and assert on observable behavior:
exit codes, lock file presence, and diagnostic output.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "git-coop.sh"


def _run(
    subcmd: str,
    *args: str,
    env: dict[str, str] | None = None,
    project_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run git-coop.sh <subcmd> [args] and return the result."""
    base_env = {**os.environ}
    if project_dir:
        base_env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    if env:
        base_env.update(env)
    # Provide a stable session ID so acquire/release within the same test match.
    base_env.setdefault("COGNITIVE_OS_SESSION_ID", "test-session-pytest")
    return subprocess.run(
        ["bash", str(SCRIPT), subcmd, *args],
        capture_output=True,
        text=True,
        env=base_env,
    )


def _lock_dir(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "runtime" / "git-index.lock"


def _meta_file(project_dir: Path) -> Path:
    return _lock_dir(project_dir) / "meta.json"


# ── Existence ─────────────────────────────────────────────────────────────────


def test_script_exists():
    assert SCRIPT.exists(), f"git-coop.sh not found at {SCRIPT}"
    assert os.access(str(SCRIPT), os.X_OK), "git-coop.sh is not executable"


# ── Status on clean state ─────────────────────────────────────────────────────


def test_status_when_unlocked(tmp_path: Path):
    result = _run("status", project_dir=tmp_path)
    assert result.returncode == 0
    assert "UNLOCKED" in result.stderr


# ── Acquire creates lock directory and metadata ───────────────────────────────


def test_acquire_creates_lock(tmp_path: Path):
    result = _run("acquire", "test-operation", project_dir=tmp_path)
    assert result.returncode == 0, result.stderr
    assert _lock_dir(tmp_path).is_dir(), "lock directory not created"
    assert _meta_file(tmp_path).exists(), "meta.json not created"
    meta = json.loads(_meta_file(tmp_path).read_text())
    assert meta["session_id"] == "test-session-pytest"
    assert meta["operation"] == "test-operation"
    assert "pid" in meta
    assert "timestamp" in meta


def test_acquire_sets_status_locked(tmp_path: Path):
    _run("acquire", "op", project_dir=tmp_path)
    result = _run("status", project_dir=tmp_path)
    assert "LOCKED" in result.stderr


# ── Release removes lock ──────────────────────────────────────────────────────


def test_release_removes_lock(tmp_path: Path):
    _run("acquire", "op", project_dir=tmp_path)
    assert _lock_dir(tmp_path).is_dir()
    result = _run("release", project_dir=tmp_path)
    assert result.returncode == 0, result.stderr
    assert not _lock_dir(tmp_path).exists(), "lock directory should be gone after release"


def test_release_without_lock_succeeds(tmp_path: Path):
    result = _run("release", project_dir=tmp_path)
    assert result.returncode == 0
    assert "not held" in result.stderr


# ── Idempotency: same session re-acquires without blocking ───────────────────


def test_same_session_reacquire_is_noop(tmp_path: Path):
    r1 = _run("acquire", "first-op", project_dir=tmp_path)
    assert r1.returncode == 0
    r2 = _run("acquire", "second-op", project_dir=tmp_path)
    assert r2.returncode == 0
    assert "already held" in r2.stderr


# ── Different session blocks ──────────────────────────────────────────────────


def test_different_session_blocks_and_times_out(tmp_path: Path):
    """A second session cannot acquire a live lock and times out."""
    # Acquire with session A
    r1 = _run(
        "acquire", "session-a-op",
        project_dir=tmp_path,
        env={"COGNITIVE_OS_SESSION_ID": "session-A", "COS_GIT_LOCK_TIMEOUT": "3"},
    )
    assert r1.returncode == 0, r1.stderr

    # Write a live PID into the meta so the stale check doesn't clear it.
    # The lock was created with PPID/$$; we'll re-write meta with a live PID.
    meta = json.loads(_meta_file(tmp_path).read_text())
    meta["pid"] = os.getpid()  # current test process — definitely alive
    meta["session_id"] = "session-A"
    _meta_file(tmp_path).write_text(json.dumps(meta))

    # Session B should time out (TTL=3s, so this runs fast)
    r2 = _run(
        "acquire", "session-b-op",
        project_dir=tmp_path,
        env={"COGNITIVE_OS_SESSION_ID": "session-B", "COS_GIT_LOCK_TIMEOUT": "3"},
    )
    assert r2.returncode == 1
    assert "timed out" in r2.stderr
    assert "session-A" in r2.stderr


# ── Stale lock auto-clears ────────────────────────────────────────────────────


def test_stale_lock_is_auto_cleared(tmp_path: Path):
    """A lock with dead PID is cleared on the next acquire attempt."""
    lock_dir = _lock_dir(tmp_path)
    lock_dir.mkdir(parents=True)
    meta = {
        "session_id": "dead-session",
        "pid": 999999999,          # almost certainly not a live PID
        "timestamp": "2000-01-01T00:00:00Z",   # ancient — definitely stale
        "operation": "old-op",
    }
    (lock_dir / "meta.json").write_text(json.dumps(meta))

    result = _run("acquire", "fresh-op", project_dir=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "stale" in result.stderr
    # New metadata should reflect fresh acquisition
    new_meta = json.loads(_meta_file(tmp_path).read_text())
    assert new_meta["session_id"] == "test-session-pytest"
    assert new_meta["operation"] == "fresh-op"


# ── Force unlock ──────────────────────────────────────────────────────────────


def test_force_unlock_clears_any_lock(tmp_path: Path):
    _run("acquire", "op", project_dir=tmp_path, env={"COGNITIVE_OS_SESSION_ID": "other-session"})
    # Lock is held by another session — normal release would refuse.
    result = _run("force_unlock", project_dir=tmp_path)
    assert result.returncode == 0
    assert not _lock_dir(tmp_path).exists()


# ── Bypass flag ───────────────────────────────────────────────────────────────


def test_bypass_flag_skips_lock(tmp_path: Path):
    result = _run("acquire", "op", project_dir=tmp_path, env={"COS_BYPASS_GIT_LOCK": "1"})
    assert result.returncode == 0
    # Lock dir must NOT have been created (bypass skips acquisition)
    assert not _lock_dir(tmp_path).exists()


# ── Concurrent acquire: two threads compete, one wins, other blocks/retries ───


def test_concurrent_acquire_serializes(tmp_path: Path):
    """Two concurrent acquires from different sessions: exactly one succeeds
    immediately, the other eventually acquires after the first releases."""
    errors: list[str] = []

    def try_acquire_release(session_id: str, hold_seconds: float = 0.2) -> str:
        r = _run(
            "acquire", f"op-{session_id}",
            project_dir=tmp_path,
            env={
                "COGNITIVE_OS_SESSION_ID": session_id,
                "COS_GIT_LOCK_TIMEOUT": "10",
                "COS_GIT_LOCK_TTL": "30",
            },
        )
        if r.returncode != 0:
            errors.append(f"{session_id}: {r.stderr}")
            return f"FAILED:{session_id}"
        time.sleep(hold_seconds)
        _run("release", project_dir=tmp_path, env={"COGNITIVE_OS_SESSION_ID": session_id})
        return f"OK:{session_id}"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(try_acquire_release, "sess-alpha"),
            pool.submit(try_acquire_release, "sess-beta"),
        ]
        results = [f.result() for f in as_completed(futures)]

    # Both should succeed (one after the other)
    assert not errors, f"Acquire errors: {errors}"
    ok_results = [r for r in results if r.startswith("OK:")]
    assert len(ok_results) == 2, f"Expected both to succeed: {results}"
    # Lock must be released at the end
    assert not _lock_dir(tmp_path).exists(), "Lock should be released after both sessions complete"
