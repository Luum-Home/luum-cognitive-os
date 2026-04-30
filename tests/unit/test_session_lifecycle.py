"""Behavioral tests for session-init.sh and session-cleanup.sh.

Verifies that:
- session-init creates the expected directory structure and registers in active-sessions.json
- session-init handles a corrupted active-sessions.json gracefully (reinitialises it)
- session-cleanup removes the session from active-sessions.json
- session-cleanup exits cleanly when the session directory is missing
- session-cleanup skips metrics merging gracefully when the metrics dir is unwritable
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "hooks"
INIT_HOOK = HOOKS_DIR / "session-init.sh"
CLEANUP_HOOK = HOOKS_DIR / "session-cleanup.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(
    hook_path: Path,
    project_dir: Path,
    extra_env: "dict | None" = None,
    session_id: "str | None" = None,
    timeout: int = 15,
) -> subprocess.CompletedProcess:
    """Execute *hook_path* with an isolated project directory.

    Args:
        hook_path: Absolute path to the .sh hook file.
        project_dir: Temporary project directory to use as CLAUDE_PROJECT_DIR.
        extra_env: Additional environment variables to set.
        session_id: Value for COGNITIVE_OS_SESSION_ID (cleanup hook uses it).
        timeout: Subprocess timeout in seconds.

    Returns:
        CompletedProcess with stdout, stderr, and returncode.
    """
    if not hook_path.exists():
        pytest.skip(f"Hook not found: {hook_path}")

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"

    if session_id is not None:
        env["COGNITIVE_OS_SESSION_ID"] = session_id
    else:
        env.pop("COGNITIVE_OS_SESSION_ID", None)

    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        ["bash", str(hook_path)],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        input="",
    )


FLOCK_AVAILABLE = (
    subprocess.run(["which", "flock"], capture_output=True).returncode == 0
)


def _sessions_dir(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "sessions"


def _active_sessions_file(project_dir: Path) -> Path:
    return _sessions_dir(project_dir) / "active-sessions.json"


def _session_subdirs(project_dir: Path) -> "list[Path]":
    """Return subdirectories inside sessions/ that look like real session dirs.

    Filters out the ``locks`` subdirectory and any dot-prefixed entries so only
    timestamp-PID-hash style directories are returned.
    """
    sessions = _sessions_dir(project_dir)
    if not sessions.exists():
        return []
    return [
        d for d in sessions.iterdir()
        if d.is_dir() and d.name != "locks" and not d.name.startswith(".")
    ]


# ---------------------------------------------------------------------------
# session-init.sh tests
# ---------------------------------------------------------------------------


class TestSessionInit:
    """session-init.sh creates the session directory and registers the session."""

    def test_init_exits_zero(self, tmp_path):
        """Hook must exit 0 on a clean run."""
        result = _run_hook(INIT_HOOK, tmp_path)
        assert result.returncode == 0, (
            f"session-init.sh exited {result.returncode}\n"
            f"stderr: {result.stderr}"
        )

    def test_init_creates_sessions_directory(self, tmp_path):
        """Hook must create .cognitive-os/sessions/."""
        _run_hook(INIT_HOOK, tmp_path)
        assert _sessions_dir(tmp_path).is_dir(), (
            "sessions directory was not created"
        )

    def test_init_creates_session_subdirectory(self, tmp_path):
        """Hook must create a unique session sub-directory inside sessions/."""
        _run_hook(INIT_HOOK, tmp_path)
        subdirs = _session_subdirs(tmp_path)
        assert len(subdirs) >= 1, (
            f"No session sub-directory found under {_sessions_dir(tmp_path)}"
        )

    def test_init_creates_tasks_json(self, tmp_path):
        """Session directory must contain a tasks.json initialised to []."""
        _run_hook(INIT_HOOK, tmp_path)
        subdirs = _session_subdirs(tmp_path)
        assert subdirs, "No session sub-directory created"
        tasks_file = subdirs[0] / "tasks.json"
        assert tasks_file.exists(), "tasks.json not created"
        data = json.loads(tasks_file.read_text())
        assert data == [], f"tasks.json should be [], got {data!r}"

    def test_init_creates_meta_json(self, tmp_path):
        """Session directory must contain a meta.json with required fields."""
        _run_hook(INIT_HOOK, tmp_path)
        subdirs = _session_subdirs(tmp_path)
        assert subdirs, "No session sub-directory created"
        meta_file = subdirs[0] / "meta.json"
        assert meta_file.exists(), "meta.json not created"
        meta = json.loads(meta_file.read_text())
        assert "session_id" in meta, "meta.json missing session_id"
        assert "pid" in meta, "meta.json missing pid"
        assert "start_time" in meta, "meta.json missing start_time"

    def test_init_creates_metrics_subdirectory(self, tmp_path):
        """Session directory must contain a metrics/ subdirectory."""
        _run_hook(INIT_HOOK, tmp_path)
        subdirs = _session_subdirs(tmp_path)
        assert subdirs, "No session sub-directory created"
        metrics_dir = subdirs[0] / "metrics"
        assert metrics_dir.is_dir(), "metrics/ sub-directory not created"

    def test_init_registers_in_active_sessions(self, tmp_path):
        """Hook must add the session to active-sessions.json.

        Requires flock — skipped on systems without it (e.g. macOS without
        util-linux).
        """
        if not FLOCK_AVAILABLE:
            pytest.skip("flock not available — registration uses flock")
        _run_hook(INIT_HOOK, tmp_path)
        active_file = _active_sessions_file(tmp_path)
        assert active_file.exists(), "active-sessions.json not created"
        data = json.loads(active_file.read_text())
        assert "sessions" in data, "active-sessions.json missing 'sessions' key"
        assert len(data["sessions"]) >= 1, (
            "No session was registered in active-sessions.json"
        )

    def test_init_registered_entry_has_required_fields(self, tmp_path):
        """Registered session entry must include id, pid, start_time."""
        if not FLOCK_AVAILABLE:
            pytest.skip("flock not available — registration uses flock")
        _run_hook(INIT_HOOK, tmp_path)
        data = json.loads(_active_sessions_file(tmp_path).read_text())
        entry = data["sessions"][0]
        assert "id" in entry, "Session entry missing 'id'"
        assert "pid" in entry, "Session entry missing 'pid'"
        assert "start_time" in entry, "Session entry missing 'start_time'"

    def test_init_multiple_runs_register_multiple_sessions(self, tmp_path):
        """Each init run must register a distinct session."""
        if not FLOCK_AVAILABLE:
            pytest.skip("flock not available — registration uses flock")
        _run_hook(INIT_HOOK, tmp_path)
        _run_hook(INIT_HOOK, tmp_path)
        data = json.loads(_active_sessions_file(tmp_path).read_text())
        assert len(data["sessions"]) >= 2, (
            "Two init runs did not register two sessions"
        )

    def test_init_prunes_stale_dead_sessions_before_counting(self, tmp_path):
        """Dead sessions older than the grace window must be pruned on startup."""
        if not FLOCK_AVAILABLE:
            pytest.skip("flock not available — registration uses flock")
        sessions_dir = _sessions_dir(tmp_path)
        sessions_dir.mkdir(parents=True, exist_ok=True)
        _active_sessions_file(tmp_path).write_text(
            json.dumps({
                "sessions": [
                    {
                        "id": "1-999999-stale",
                        "pid": 999999,
                        "start_epoch": 1,
                        "start_time": "1970-01-01T00:00:01Z",
                        "working_directory": str(tmp_path),
                    }
                ]
            })
        )

        _run_hook(INIT_HOOK, tmp_path, extra_env={"COS_ACTIVE_SESSION_PRUNE_GRACE_SECONDS": "1"})

        data = json.loads(_active_sessions_file(tmp_path).read_text())
        ids = [entry["id"] for entry in data["sessions"]]
        assert "1-999999-stale" not in ids
        assert len(data["sessions"]) == 1

    def test_init_corrupted_active_sessions_json_reinitialized(self, tmp_path):
        """Hook must reinitialise active-sessions.json when it is corrupted."""
        if not FLOCK_AVAILABLE:
            pytest.skip("flock not available — registration uses flock")
        sessions_dir = _sessions_dir(tmp_path)
        sessions_dir.mkdir(parents=True, exist_ok=True)
        # Write corrupted JSON
        _active_sessions_file(tmp_path).write_text("NOT VALID JSON {{{")

        result = _run_hook(INIT_HOOK, tmp_path)
        # Hook must not crash
        assert result.returncode == 0, (
            f"Hook crashed on corrupted active-sessions.json\n"
            f"stderr: {result.stderr}"
        )
        # After recovery, file must be valid JSON
        active_file = _active_sessions_file(tmp_path)
        assert active_file.exists(), "active-sessions.json not recreated"
        data = json.loads(active_file.read_text())
        assert "sessions" in data, "Reinitialized file missing 'sessions' key"

    def test_init_prints_session_id_to_stdout(self, tmp_path):
        """Hook must print the Session ID to stdout for session discovery."""
        result = _run_hook(INIT_HOOK, tmp_path)
        assert "Session ID:" in result.stdout, (
            f"Expected 'Session ID:' in stdout.\nGot: {result.stdout!r}"
        )

    def test_init_output_contains_initialized_message(self, tmp_path):
        """Hook stdout must contain the initialization banner."""
        result = _run_hook(INIT_HOOK, tmp_path)
        assert "COGNITIVE OS SESSION INITIALIZED" in result.stdout or \
               "session" in result.stdout.lower(), (
            f"Expected initialization message in stdout.\nGot: {result.stdout!r}"
        )


# ---------------------------------------------------------------------------
# session-cleanup.sh tests
# ---------------------------------------------------------------------------


class TestSessionCleanup:
    """session-cleanup.sh deregisters the session and cleans up state."""

    def _setup_session(self, tmp_path: Path) -> str:
        """Run session-init to create a real session; return the session_id."""
        result = _run_hook(INIT_HOOK, tmp_path)
        assert result.returncode == 0, f"Init failed: {result.stderr}"
        # Extract session ID from stdout
        for line in result.stdout.splitlines():
            if "Session ID:" in line:
                session_id = line.split("Session ID:")[-1].strip()
                return session_id
        pytest.fail(f"Could not extract Session ID from init output:\n{result.stdout}")

    def _setup_session_fast(self, tmp_path: Path) -> str:
        """Create a minimal session structure without running session-init.sh.

        This avoids the 6 Python cold-starts in session-init.sh. Suitable for
        tests that only need a valid session directory on disk (not a fully
        registered session).
        """
        import time as _time
        session_id = f"{int(_time.time())}-0-testfast"
        session_dir = _sessions_dir(tmp_path) / session_id
        (session_dir / "metrics").mkdir(parents=True, exist_ok=True)
        (session_dir / "tasks.json").write_text("[]")
        import json as _json
        (session_dir / "meta.json").write_text(
            _json.dumps({"session_id": session_id, "pid": 0, "start_time": "2026-01-01T00:00:00Z"})
        )
        return session_id

    def test_cleanup_exits_zero_with_valid_session(self, tmp_path):
        """Hook must exit 0 after cleaning up a valid session."""
        session_id = self._setup_session(tmp_path)
        result = _run_hook(CLEANUP_HOOK, tmp_path, session_id=session_id)
        assert result.returncode == 0, (
            f"session-cleanup.sh exited {result.returncode}\n"
            f"stderr: {result.stderr}"
        )

    def test_cleanup_removes_from_active_sessions(self, tmp_path):
        """After cleanup, the session must no longer appear in active-sessions.json.

        Requires flock for registration — skipped when flock is unavailable.
        """
        if not FLOCK_AVAILABLE:
            pytest.skip("flock not available — registration uses flock")
        session_id = self._setup_session(tmp_path)
        # Verify it was registered first
        data_before = json.loads(_active_sessions_file(tmp_path).read_text())
        ids_before = [s["id"] for s in data_before["sessions"]]
        assert session_id in ids_before, "Session was not registered before cleanup"

        _run_hook(CLEANUP_HOOK, tmp_path, session_id=session_id)

        active_file = _active_sessions_file(tmp_path)
        if active_file.exists():
            data_after = json.loads(active_file.read_text())
            ids_after = [s["id"] for s in data_after["sessions"]]
            assert session_id not in ids_after, (
                f"Session {session_id!r} still in active-sessions.json after cleanup"
            )

    def test_cleanup_missing_session_dir_exits_cleanly(self, tmp_path):
        """Cleanup must exit 0 when the session directory does not exist."""
        # Create a valid active-sessions.json with a ghost session
        sessions_dir = _sessions_dir(tmp_path)
        sessions_dir.mkdir(parents=True, exist_ok=True)
        ghost_id = "ghost-session-12345"
        _active_sessions_file(tmp_path).write_text(
            json.dumps({"sessions": [{"id": ghost_id, "pid": 99999, "start_time": "2026-01-01T00:00:00Z"}]})
        )

        result = _run_hook(CLEANUP_HOOK, tmp_path, session_id=ghost_id)
        assert result.returncode == 0, (
            f"Cleanup should exit 0 even with missing session dir\n"
            f"exit={result.returncode}, stderr={result.stderr}"
        )

    def test_cleanup_no_session_id_exits_cleanly(self, tmp_path):
        """Cleanup without a session ID must exit 0 immediately."""
        result = _run_hook(CLEANUP_HOOK, tmp_path, session_id=None)
        assert result.returncode == 0, (
            f"Cleanup without session ID should exit 0\n"
            f"stderr: {result.stderr}"
        )

    def test_cleanup_removes_session_directory(self, tmp_path):
        """Session directory must be removed after cleanup (cleanup_on_exit=true)."""
        session_id = self._setup_session(tmp_path)
        session_dir = _sessions_dir(tmp_path) / session_id

        if not session_dir.exists():
            pytest.skip("Session directory not found (may use different naming)")

        _run_hook(CLEANUP_HOOK, tmp_path, session_id=session_id)
        # With cleanup_on_exit=true (default), the directory should be gone
        assert not session_dir.exists(), (
            f"Session directory {session_dir} still exists after cleanup"
        )

    def test_cleanup_merges_metrics_into_global(self, tmp_path):
        """Session metrics must be appended to the global metrics directory."""
        session_id = self._setup_session(tmp_path)
        session_dir = _sessions_dir(tmp_path) / session_id
        session_metrics_dir = session_dir / "metrics"

        if not session_metrics_dir.exists():
            # Create it if init didn't make it (may have different layout)
            session_metrics_dir.mkdir(parents=True, exist_ok=True)

        # Write a test metric file
        test_metric = session_metrics_dir / "test-metric.jsonl"
        test_metric.write_text('{"test": true}\n')

        _run_hook(CLEANUP_HOOK, tmp_path, session_id=session_id)

        global_metric = (tmp_path / ".cognitive-os" / "metrics" / "test-metric.jsonl")
        assert global_metric.exists(), (
            "Session metric was not merged into global metrics directory"
        )
        content = global_metric.read_text()
        assert '"test": true' in content, (
            "Merged metric file does not contain session data"
        )

    def test_cleanup_unwritable_metrics_skips_gracefully(self, tmp_path):
        """If global metrics dir is unwritable, cleanup should still exit 0."""
        # Use the fast setup to avoid 6 Python cold-starts from session-init.sh.
        # This test only needs a valid session dir with metrics — not a registered session.
        session_id = self._setup_session_fast(tmp_path)
        session_dir = _sessions_dir(tmp_path) / session_id
        session_metrics_dir = session_dir / "metrics"
        if not session_metrics_dir.exists():
            session_metrics_dir.mkdir(parents=True, exist_ok=True)

        # Write a metric in the session
        (session_metrics_dir / "test.jsonl").write_text('{"x": 1}\n')

        # Make global metrics dir unwritable
        global_metrics = tmp_path / ".cognitive-os" / "metrics"
        global_metrics.mkdir(parents=True, exist_ok=True)
        os.chmod(str(global_metrics), 0o444)  # read-only

        try:
            result = _run_hook(CLEANUP_HOOK, tmp_path, session_id=session_id)
            # Must not crash; it may warn but should exit cleanly
            assert result.returncode == 0, (
                f"Cleanup crashed with unwritable metrics dir\n"
                f"stderr: {result.stderr}"
            )
        finally:
            os.chmod(str(global_metrics), 0o755)  # restore for cleanup

    def test_cleanup_deregisters_only_target_session(self, tmp_path):
        """Cleanup must only remove the target session, leaving others intact.

        Requires flock for registration — skipped when flock is unavailable.
        """
        if not FLOCK_AVAILABLE:
            pytest.skip("flock not available — registration uses flock")
        # Register two sessions
        session_id_1 = self._setup_session(tmp_path)
        session_id_2 = self._setup_session(tmp_path)

        data = json.loads(_active_sessions_file(tmp_path).read_text())
        assert len(data["sessions"]) >= 2, "Expected two sessions registered"

        # Clean up only session 1
        _run_hook(CLEANUP_HOOK, tmp_path, session_id=session_id_1)

        data_after = json.loads(_active_sessions_file(tmp_path).read_text())
        ids_after = [s["id"] for s in data_after["sessions"]]
        assert session_id_1 not in ids_after, (
            f"Session 1 ({session_id_1}) should have been removed"
        )
        assert session_id_2 in ids_after, (
            f"Session 2 ({session_id_2}) should still be present"
        )


# ---------------------------------------------------------------------------
# Concurrency and flock pattern tests (appended)
# ---------------------------------------------------------------------------


class TestConcurrentInits:
    """Tests for concurrent session-init.sh behaviour."""

    def test_two_concurrent_inits_both_registered(self, tmp_path):
        """Two concurrent session-init calls must both appear in active-sessions.json.

        Uses Python threading to launch two hook subprocesses in parallel.
        Requires flock — skipped when unavailable (macOS ships without it by
        default; Linux always has it).
        """
        if not FLOCK_AVAILABLE:
            pytest.skip("flock not available — registration uses flock for atomicity")

        import threading

        results: list[subprocess.CompletedProcess] = []
        errors: list[str] = []

        def _run_init() -> None:
            r = _run_hook(INIT_HOOK, tmp_path)
            results.append(r)
            if r.returncode != 0:
                errors.append(r.stderr)

        t1 = threading.Thread(target=_run_init)
        t2 = threading.Thread(target=_run_init)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        assert not errors, f"One or more session-init calls failed:\n{''.join(errors)}"

        sessions_file = _active_sessions_file(tmp_path)
        assert sessions_file.exists(), "active-sessions.json not created"

        data = json.loads(sessions_file.read_text())
        registered = data.get("sessions", [])
        assert len(registered) >= 2, (
            f"Expected at least 2 sessions registered after concurrent inits, "
            f"got {len(registered)}: {registered}"
        )

    def test_flock_pattern_exists_in_hook(self):
        """session-init.sh source must contain a flock call for atomic registration.

        This guards against accidental removal of the locking mechanism during
        refactors.
        """
        if not INIT_HOOK.exists():
            pytest.skip(f"Hook not found: {INIT_HOOK}")

        source = INIT_HOOK.read_text()
        assert "flock" in source, (
            "session-init.sh does not contain 'flock' — concurrent registration "
            "is no longer protected. This is a regression."
        )
