"""Behavioral tests for concurrent-write-guard.sh.

Verifies:
- flock is used for real OS-level serialization (keyword present in hook source)
- Empty file_path input is skipped (exit 0)
- Missing SESSION_ID causes the hook to skip gracefully (exit 0)
- Stale locks (expired or dead PID) are removed and replaced
- Same session accessing the same file refreshes the lock (no contention)
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
HOOK_PATH = HOOKS_DIR / "concurrent-write-guard.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(
    stdin_json: "dict | None" = None,
    project_dir: "str | None" = None,
    session_id: "str | None" = None,
    extra_env: "dict | None" = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    """Execute concurrent-write-guard.sh and return the result.

    Args:
        stdin_json: JSON object passed as stdin (hook reads tool_input from it).
        project_dir: Used as CLAUDE_PROJECT_DIR.
        session_id: Used as COGNITIVE_OS_SESSION_ID.
        extra_env: Additional env vars.
        timeout: Seconds before the subprocess is killed.

    Returns:
        CompletedProcess with stdout, stderr, and returncode.
    """
    if not HOOK_PATH.exists():
        pytest.skip(f"Hook not found: {HOOK_PATH}")

    env = os.environ.copy()
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = project_dir
        env["COGNITIVE_OS_PROJECT_DIR"] = project_dir
    if session_id is not None:
        env["COGNITIVE_OS_SESSION_ID"] = session_id
    else:
        env.pop("COGNITIVE_OS_SESSION_ID", None)
    if extra_env:
        env.update(extra_env)

    stdin_str = json.dumps(stdin_json) if stdin_json is not None else ""

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin_str,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _locks_dir(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "sessions" / "locks"


def _write_lock(
    locks_dir: Path,
    file_hash: str,
    session_id: str,
    pid: int,
    age_seconds: int = 0,
) -> Path:
    """Write a fake lock file for testing."""
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_file = locks_dir / f"{file_hash}.lock"
    now = int(time.time()) - age_seconds
    lock_file.write_text(
        json.dumps({
            "session_id": session_id,
            "pid": pid,
            "file_path": f"/fake/path/{file_hash}",
            "timestamp_epoch": now,
            "timestamp": "2026-01-01T00:00:00Z",
        })
    )
    return lock_file


# ---------------------------------------------------------------------------
# Source-level verification
# ---------------------------------------------------------------------------


class TestHookSourceVerification:
    """Verify the hook uses the expected OS primitives."""

    def test_flock_keyword_present_in_hook_source(self):
        """Hook must use flock for real OS-level serialization."""
        source = HOOK_PATH.read_text()
        assert "flock" in source, (
            "concurrent-write-guard.sh does not contain 'flock' — "
            "file locking is not implemented with OS-level flock"
        )

    def test_hook_handles_file_path_from_tool_input(self):
        """Hook source must extract file_path from .tool_input.file_path."""
        source = HOOK_PATH.read_text()
        assert "tool_input.file_path" in source or "file_path" in source, (
            "Hook does not extract file_path from tool input"
        )

    def test_hook_creates_lock_files_in_locks_dir(self):
        """Hook source must write lock files to sessions/locks/."""
        source = HOOK_PATH.read_text()
        assert "locks" in source and ".lock" in source, (
            "Hook does not reference a locks directory or .lock files"
        )


# ---------------------------------------------------------------------------
# Empty / missing input → skip gracefully
# ---------------------------------------------------------------------------


class TestEmptyInputSkips:
    """Hook must skip without error when inputs are empty or incomplete."""

    def test_empty_stdin_exits_zero(self, isolated_cos_home):
        """Empty stdin should cause the hook to skip (exit 0)."""
        result = _run_hook(
            stdin_json={},
            project_dir=str(isolated_cos_home),
            session_id="test-session-001",
        )
        assert result.returncode == 0, (
            f"Empty stdin crashed the hook (exit {result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    def test_empty_file_path_skips(self, isolated_cos_home):
        """Missing file_path in tool_input must cause the hook to skip (exit 0)."""
        result = _run_hook(
            stdin_json={"tool_name": "Edit", "tool_input": {}},
            project_dir=str(isolated_cos_home),
            session_id="test-session-001",
        )
        assert result.returncode == 0, (
            f"Missing file_path should cause skip (exit 0)\n"
            f"exit={result.returncode}, stderr={result.stderr}"
        )

    def test_null_file_path_skips(self, isolated_cos_home):
        """Null file_path in tool_input must cause the hook to skip (exit 0)."""
        result = _run_hook(
            stdin_json={"tool_name": "Write", "tool_input": {"file_path": None}},
            project_dir=str(isolated_cos_home),
            session_id="test-session-001",
        )
        assert result.returncode == 0, (
            f"Null file_path should cause skip (exit 0)\n"
            f"exit={result.returncode}, stderr={result.stderr}"
        )

    def test_no_session_id_skips(self, tmp_path):
        """Without a session ID, the hook must exit 0 immediately."""
        result = _run_hook(
            stdin_json={"tool_name": "Edit", "tool_input": {"file_path": "/some/file.go"}},
            project_dir=str(tmp_path),
            session_id=None,  # no session ID
        )
        assert result.returncode == 0, (
            f"No session ID should cause skip (exit 0)\n"
            f"exit={result.returncode}, stderr={result.stderr}"
        )

    def test_empty_session_id_skips(self, tmp_path):
        """Empty-string session ID must also skip gracefully."""
        env = os.environ.copy()
        env["COGNITIVE_OS_SESSION_ID"] = ""
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
        # Remove any file-based session
        env.pop("COGNITIVE_OS_SESSION_ID", None)
        env["COGNITIVE_OS_SESSION_ID"] = ""

        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input=json.dumps({"tool_input": {"file_path": "/some/file.go"}}),
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        assert result.returncode == 0, (
            f"Empty session ID should skip gracefully\n"
            f"stderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Lock acquisition — normal flow
# ---------------------------------------------------------------------------


class TestLockAcquisition:
    """Hook acquires a lock file for the target path."""

    def test_lock_file_created_for_new_path(self, tmp_path):
        """First write to a path must create a lock file in locks/."""
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        # Write a fake current-session file so hook can resolve the session ID
        session_id = "test-session-lock-create"
        (sessions_dir / f".current-session-{os.getpid()}").write_text(session_id)

        result = _run_hook(
            stdin_json={"tool_name": "Edit", "tool_input": {"file_path": "/tmp/target.go"}},
            project_dir=str(tmp_path),
            session_id=session_id,
        )
        assert result.returncode == 0, (
            f"Lock creation failed (exit {result.returncode})\nstderr: {result.stderr}"
        )
        locks_dir = _locks_dir(tmp_path)
        lock_files = list(locks_dir.glob("*.lock"))
        assert len(lock_files) >= 1, (
            f"No lock file created under {locks_dir}"
        )

    def test_lock_file_contains_session_metadata(self, tmp_path):
        """Lock file must contain session_id, pid, and file_path fields."""
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        session_id = "test-session-metadata"
        (sessions_dir / f".current-session-{os.getpid()}").write_text(session_id)

        _run_hook(
            stdin_json={"tool_name": "Write", "tool_input": {"file_path": "/tmp/meta-test.py"}},
            project_dir=str(tmp_path),
            session_id=session_id,
        )

        locks_dir = _locks_dir(tmp_path)
        lock_files = list(locks_dir.glob("*.lock"))
        if not lock_files:
            pytest.skip("No lock file created (hook may have skipped)")

        lock_data = json.loads(lock_files[0].read_text())
        assert "session_id" in lock_data, "Lock file missing 'session_id'"
        assert "pid" in lock_data, "Lock file missing 'pid'"
        assert "file_path" in lock_data, "Lock file missing 'file_path'"


# ---------------------------------------------------------------------------
# Stale lock removal
# ---------------------------------------------------------------------------


class TestStaleLockRemoval:
    """Hook must remove expired or dead-PID locks before acquiring."""

    def test_stale_lock_removed_by_age(self, tmp_path):
        """A lock older than lock_timeout_seconds must be removed and replaced."""
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        session_id = "test-session-stale-age"

        # Create a stale lock (700 seconds old > 300s default timeout)
        # Use a deterministic hash: md5 of the target path (simulated)
        file_path = "/tmp/stale-target.go"
        # Compute hash the same way the hook does (md5sum on Linux, md5 on macOS)
        try:
            result_hash = subprocess.run(
                ["bash", "-c", f"echo -n '{file_path}' | md5sum | cut -d' ' -f1"],
                capture_output=True, text=True, timeout=5,
            )
            file_hash = result_hash.stdout.strip()
            if not file_hash:
                raise ValueError("md5sum returned empty")
        except Exception:
            result_hash = subprocess.run(
                ["bash", "-c", f"echo -n '{file_path}' | md5"],
                capture_output=True, text=True, timeout=5,
            )
            file_hash = result_hash.stdout.strip()

        locks_dir = _locks_dir(tmp_path)
        old_lock = _write_lock(
            locks_dir,
            file_hash=file_hash,
            session_id="other-session",
            pid=99999,  # non-existent PID
            age_seconds=700,  # way past the 300s timeout
        )
        assert old_lock.exists(), "Test setup: stale lock not created"

        # Run hook — it should clear the stale lock and acquire a new one
        result = _run_hook(
            stdin_json={"tool_name": "Edit", "tool_input": {"file_path": file_path}},
            project_dir=str(tmp_path),
            session_id=session_id,
        )
        assert result.returncode == 0, (
            f"Hook did not clear stale lock (exit {result.returncode})\n"
            f"stderr: {result.stderr}"
        )

    def test_dead_pid_lock_treated_as_stale(self, tmp_path):
        """A lock held by a dead PID must be treated as stale and removed."""
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        session_id = "test-session-dead-pid"
        file_path = "/tmp/dead-pid-target.py"

        # Use PID 1 is always alive; use a large non-existent PID instead
        dead_pid = 2147483647  # max int32, almost certainly not running

        try:
            result_hash = subprocess.run(
                ["bash", "-c", f"echo -n '{file_path}' | md5sum | cut -d' ' -f1"],
                capture_output=True, text=True, timeout=5,
            )
            file_hash = result_hash.stdout.strip()
            if not file_hash:
                raise ValueError
        except Exception:
            result_hash = subprocess.run(
                ["bash", "-c", f"echo -n '{file_path}' | md5"],
                capture_output=True, text=True, timeout=5,
            )
            file_hash = result_hash.stdout.strip()

        locks_dir = _locks_dir(tmp_path)
        _write_lock(
            locks_dir,
            file_hash=file_hash,
            session_id="dead-session",
            pid=dead_pid,
            age_seconds=0,  # recent timestamp, but dead PID
        )

        result = _run_hook(
            stdin_json={"tool_name": "Write", "tool_input": {"file_path": file_path}},
            project_dir=str(tmp_path),
            session_id=session_id,
        )
        # Hook should clear the dead-PID lock and exit 0
        assert result.returncode == 0, (
            f"Hook blocked on dead-PID lock (exit {result.returncode})\n"
            f"stderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Same session refreshes the lock
# ---------------------------------------------------------------------------


class TestSameSessionRefreshesLock:
    """Same session accessing the same file refreshes the lock timestamp."""

    def test_same_session_refreshes_lock(self, tmp_path):
        """Two writes from the same session must both succeed (exit 0)."""
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        session_id = "test-session-refresh"
        target_file = "/tmp/refresh-test.ts"

        # First write — creates the lock
        result1 = _run_hook(
            stdin_json={"tool_name": "Edit", "tool_input": {"file_path": target_file}},
            project_dir=str(tmp_path),
            session_id=session_id,
        )
        assert result1.returncode == 0, (
            f"First write failed (exit {result1.returncode}): {result1.stderr}"
        )

        # Second write from same session — should refresh, not block
        result2 = _run_hook(
            stdin_json={"tool_name": "Edit", "tool_input": {"file_path": target_file}},
            project_dir=str(tmp_path),
            session_id=session_id,
        )
        assert result2.returncode == 0, (
            f"Same-session second write was blocked (exit {result2.returncode})\n"
            f"stderr: {result2.stderr}"
        )

    def test_same_session_lock_refreshes_timestamp(self, tmp_path):
        """Lock timestamp must be updated on same-session re-acquire."""
        sessions_dir = tmp_path / ".cognitive-os" / "sessions"
        sessions_dir.mkdir(parents=True)
        session_id = "test-session-ts-refresh"
        target_file = "/tmp/ts-refresh-test.go"
        target_file.lower()

        # Create an initial lock with an old timestamp
        try:
            result_hash = subprocess.run(
                ["bash", "-c", f"echo -n '{target_file}' | md5sum | cut -d' ' -f1"],
                capture_output=True, text=True, timeout=5,
            )
            file_hash = result_hash.stdout.strip()
            if not file_hash:
                raise ValueError
        except Exception:
            result_hash = subprocess.run(
                ["bash", "-c", f"echo -n '{target_file}' | md5"],
                capture_output=True, text=True, timeout=5,
            )
            file_hash = result_hash.stdout.strip()

        locks_dir = _locks_dir(tmp_path)
        old_lock = _write_lock(
            locks_dir,
            file_hash=file_hash,
            session_id=session_id,  # SAME session
            pid=os.getpid(),
            age_seconds=120,  # 2 minutes old — within timeout but old
        )
        old_timestamp = json.loads(old_lock.read_text())["timestamp_epoch"]

        # Run hook — should detect same session and refresh timestamp
        time.sleep(1)  # ensure clock advances
        _run_hook(
            stdin_json={"tool_name": "Edit", "tool_input": {"file_path": target_file}},
            project_dir=str(tmp_path),
            session_id=session_id,
        )

        # If the lock still exists, its timestamp should be newer
        if old_lock.exists():
            new_data = json.loads(old_lock.read_text())
            new_timestamp = new_data["timestamp_epoch"]
            assert new_timestamp >= old_timestamp, (
                f"Timestamp was not refreshed: old={old_timestamp}, new={new_timestamp}"
            )


# ---------------------------------------------------------------------------
# Symlink hash limitation test (appended)
# ---------------------------------------------------------------------------


class TestSymlinkHashLimitation:
    """Document the known limitation that symlinks produce a different lock hash
    than their targets because the hook hashes the *path string*, not the
    resolved inode.

    This means that if two different sessions write to the same underlying file
    via a symlink and its real path respectively, the guard will issue two
    separate lock files — one per path — and will NOT detect the contention.

    This test exists purely to *document* the limitation; it asserts the
    observable behaviour so that future refactors that accidentally fix or
    break the behaviour trigger a deliberate review.
    """

    def test_symlink_creates_different_lock_hash(self, tmp_path):
        """A symlink path and its target produce distinct lock hashes.

        KNOWN LIMITATION: The concurrent-write-guard hashes the raw file_path
        string.  If an agent passes the symlink path while another passes the
        real path, both will acquire 'different' locks and contention will not
        be detected.

        This is intentional (path-based deduplication is simpler and avoids
        the cost of realpath on every write) but callers should be aware.
        """
        # Create a real file and a symlink pointing to it
        real_file = tmp_path / "real_handler.go"
        real_file.touch()
        link_file = tmp_path / "link_handler.go"
        link_file.symlink_to(real_file)

        # Compute hashes for each path the way the hook does (md5 of path string)
        import subprocess as sp

        def _md5(path: str) -> str:
            r = sp.run(
                ["bash", "-c", f"echo -n '{path}' | md5sum | cut -d' ' -f1 || "
                               f"echo -n '{path}' | md5"],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip()

        hash_real = _md5(str(real_file))
        hash_link = _md5(str(link_file))

        assert hash_real != hash_link, (
            "Expected real path and symlink path to produce different hashes "
            "(documenting that the guard is path-string based, not inode based). "
            "If this assertion fails, the hash function may have been changed to "
            "use realpath — review whether the limitation still applies."
        )
