"""Behavior tests for advisory file locking.

Tests lock creation, cross-session warnings, same-session no-warning,
stale lock expiry, and dead PID lock removal.
Migrated from test-file-locking.sh.
"""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import pytest


@pytest.fixture
def guard_hook(project_root):
    """Return the concurrent-write-guard hook and skip if not executable."""
    hook = project_root / ".cognitive-os" / "hooks" / "concurrent-write-guard.sh"
    if not hook.exists() or not os.access(hook, os.X_OK):
        pytest.skip("concurrent-write-guard.sh not found or not executable")
    return hook


@pytest.fixture
def lock_env(project_root, tmp_path):
    """Set up session and lock directories for testing, cleaning up afterwards."""
    sessions_dir = project_root / ".cognitive-os" / "sessions"
    locks_dir = sessions_dir / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)

    session1 = "test-session-lock-1"
    session2 = "test-session-lock-2"
    s1_dir = sessions_dir / session1
    s2_dir = sessions_dir / session2
    (s1_dir / "metrics").mkdir(parents=True, exist_ok=True)
    (s2_dir / "metrics").mkdir(parents=True, exist_ok=True)

    yield {
        "sessions_dir": sessions_dir,
        "locks_dir": locks_dir,
        "session1": session1,
        "session2": session2,
        "project_root": project_root,
    }

    # Cleanup
    import shutil
    for d in [s1_dir, s2_dir]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    for lf in locks_dir.glob("*.lock"):
        lf.unlink(missing_ok=True)

    active = sessions_dir / "active-sessions.json"
    if active.exists():
        try:
            data = json.loads(active.read_text())
            data["sessions"] = [
                s for s in data.get("sessions", [])
                if s.get("id") not in (session1, session2)
            ]
            active.write_text(json.dumps(data))
        except Exception:
            pass


def _run_guard(guard_hook, project_root, session_id, mock_input):
    return subprocess.run(
        ["bash", str(guard_hook)],
        input=mock_input,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(project_root),
            "COGNITIVE_OS_SESSION_ID": session_id,
        },
        timeout=10,
    )


@pytest.mark.behavior
class TestFileLocking:
    """Tests for the concurrent write guard advisory locking system."""

    def test_lock_creation_on_write(self, guard_hook, lock_env):
        test_file = "/tmp/test-file-for-locking.txt"
        mock_input = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": test_file, "old_string": "a", "new_string": "b"},
        })

        result = _run_guard(
            guard_hook, lock_env["project_root"],
            lock_env["session1"], mock_input,
        )
        assert result.returncode == 0, f"guard should exit 0, got {result.returncode}"

        lock_files = list(lock_env["locks_dir"].glob("*.lock"))
        assert len(lock_files) > 0, "at least one lock file should be created"

    def test_cross_session_warning(self, guard_hook, lock_env):
        test_file = "/tmp/test-file-for-locking.txt"
        mock_input = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": test_file, "old_string": "a", "new_string": "b"},
        })

        # Session 1 acquires the lock
        _run_guard(guard_hook, lock_env["project_root"], lock_env["session1"], mock_input)

        # Session 2 should get a warning
        result = _run_guard(
            guard_hook, lock_env["project_root"],
            lock_env["session2"], mock_input,
        )
        assert result.returncode == 0, "advisory guard should exit 0"
        output = result.stdout + result.stderr
        assert any(w in output.upper() for w in ["CONCURRENT WRITE WARNING", "BEING EDITED BY SESSION"]), (
            "cross-session write should produce a warning"
        )

    def test_same_session_no_warning(self, guard_hook, lock_env):
        test_file = "/tmp/test-file-for-locking.txt"
        mock_input = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": test_file, "old_string": "a", "new_string": "b"},
        })

        # Session 1 acquires the lock
        _run_guard(guard_hook, lock_env["project_root"], lock_env["session1"], mock_input)

        # Same session should not get warning
        result = _run_guard(
            guard_hook, lock_env["project_root"],
            lock_env["session1"], mock_input,
        )
        output = result.stdout + result.stderr
        assert "WARNING" not in output.upper(), "same session should NOT get a warning"

    def test_stale_lock_auto_expires(self, guard_hook, lock_env):
        test_file = "/tmp/test-file-for-locking.txt"
        mock_input = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": test_file, "old_string": "a", "new_string": "b"},
        })

        # Session 1 acquires the lock
        _run_guard(guard_hook, lock_env["project_root"], lock_env["session1"], mock_input)

        # Find and age the lock file (set timestamp to 10 min ago)
        for lf in lock_env["locks_dir"].glob("*.lock"):
            try:
                data = json.loads(lf.read_text())
                if data.get("session_id") == lock_env["session1"]:
                    data["timestamp_epoch"] = int(time.time()) - 600
                    lf.write_text(json.dumps(data))
                    break
            except Exception:
                continue

        # Different session should not get a warning (stale lock removed)
        result = _run_guard(
            guard_hook, lock_env["project_root"],
            lock_env["session2"], mock_input,
        )
        output = result.stdout + result.stderr
        assert "WARNING" not in output.upper(), "stale lock should be auto-expired"

    def test_dead_pid_lock_removed(self, guard_hook, lock_env):
        # Find a PID that does not exist
        dead_pid = 99999
        while True:
            try:
                os.kill(dead_pid, 0)
                dead_pid += 1
            except OSError:
                break

        test_file2 = "/tmp/test-file-for-locking-2.txt"
        file_hash = hashlib.md5(test_file2.encode()).hexdigest()

        lock_data = {
            "session_id": "dead-session",
            "pid": dead_pid,
            "file_path": test_file2,
            "timestamp_epoch": int(time.time()),
        }
        lock_file = lock_env["locks_dir"] / f"{file_hash}.lock"
        lock_file.write_text(json.dumps(lock_data))

        mock_input = json.dumps({
            "tool_name": "Write",
            "tool_input": {"file_path": test_file2, "content": "test"},
        })

        result = _run_guard(
            guard_hook, lock_env["project_root"],
            lock_env["session1"], mock_input,
        )
        output = result.stdout + result.stderr
        assert "WARNING" not in output.upper(), "dead PID lock should be auto-removed"
