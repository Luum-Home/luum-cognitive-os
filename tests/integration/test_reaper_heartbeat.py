"""Integration tests for reaper-heartbeat.sh (D1).

Tests:
1. PID file is created under .cognitive-os/runtime/ on first invocation.
2. Single-instance guard: second invocation no-ops when the loop is already running.
3. Background loop invokes so-reaper.sh at least once (verified via a stub reaper
   that writes a marker file).
4. Process is cleaned up on teardown (signal.SIGTERM to the loop PID).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[2]
HOOK = PROJECT_DIR / "hooks" / "reaper-heartbeat.sh"


@pytest.fixture(autouse=True)
def _require_hook():
    if not HOOK.exists():
        pytest.skip(f"Hook not found: {HOOK}")


@pytest.fixture()
def tmp_project(tmp_path):
    """Minimal project directory with the required .cognitive-os structure."""
    runtime_dir = tmp_path / ".cognitive-os" / "runtime"
    runtime_dir.mkdir(parents=True)
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)
    # Create a stub so-reaper.sh that writes a marker and exits immediately.
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    stub_reaper = scripts_dir / "so-reaper.sh"
    stub_reaper.write_text(
        "#!/usr/bin/env bash\necho 'reaper-ran' >> \"$REAPER_MARKER_FILE\"\n"
    )
    stub_reaper.chmod(0o755)
    return tmp_path


def _run_hook(tmp_project: Path, env_overrides: dict | None = None) -> tuple[int, str, str]:
    """Invoke reaper-heartbeat.sh with PROJECT_DIR pointing at tmp_project.

    The hook launches a background subshell (`(sleep 10; while true; ...) &`).
    Using subprocess.PIPE blocks because the spawned subshell inherits the pipe
    fd and keeps it open indefinitely.  We work around this by redirecting
    stdout/stderr to temp files, so the pipe is never involved.

    Returns (returncode, stdout_text, stderr_text).
    """
    import tempfile

    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_project),
        "CLAUDE_PROJECT_DIR": str(tmp_project),
        "PROJECT_DIR": str(tmp_project),
    }
    if env_overrides:
        env.update(env_overrides)

    stdout_file = tmp_project / "_hook_stdout.txt"
    stderr_file = tmp_project / "_hook_stderr.txt"

    with open(stdout_file, "w") as fout, open(stderr_file, "w") as ferr:
        proc = subprocess.Popen(
            ["bash", str(HOOK)],
            stdout=fout,
            stderr=ferr,
            env=env,
        )
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    stdout = stdout_file.read_text() if stdout_file.exists() else ""
    stderr = stderr_file.read_text() if stderr_file.exists() else ""
    return proc.returncode, stdout, stderr


class TestReaperHeartbeat:
    """D1 — reaper-heartbeat.sh behaviour."""

    def test_pid_file_created(self, tmp_project):
        """First invocation must create a PID file."""
        pid_file = tmp_project / ".cognitive-os" / "runtime" / "reaper-heartbeat.pid"
        assert not pid_file.exists(), "PID file should not exist before hook runs"

        rc, _out, err = _run_hook(tmp_project)
        assert rc == 0, f"Hook exited non-zero: {err}"

        assert pid_file.exists(), "PID file must be created by hook"
        pid_content = pid_file.read_text().strip()
        assert pid_content.isdigit(), f"PID file must contain a number, got: {pid_content!r}"

        # Cleanup: kill the background loop
        loop_pid = int(pid_content)
        try:
            os.kill(loop_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass  # already dead — fine

    def test_single_instance_guard(self, tmp_project):
        """Second invocation must no-op if the first loop is still alive."""
        pid_file = tmp_project / ".cognitive-os" / "runtime" / "reaper-heartbeat.pid"

        # First invocation — starts the loop
        rc1, _out1, err1 = _run_hook(tmp_project)
        assert rc1 == 0, f"First invocation failed: {err1}"
        assert pid_file.exists(), "PID file must exist after first invocation"
        loop_pid = int(pid_file.read_text().strip())

        try:
            # Verify the process is alive
            os.kill(loop_pid, 0)  # signal 0 = probe only

            # Second invocation — must no-op (PID still alive)
            rc2, _out2, err2 = _run_hook(tmp_project)
            assert rc2 == 0, f"Second invocation failed: {err2}"

            # PID file must still point to the ORIGINAL loop (not a new one)
            new_pid = int(pid_file.read_text().strip())
            assert new_pid == loop_pid, (
                f"Second invocation should NOT replace the PID (got {new_pid}, expected {loop_pid})"
            )
        finally:
            try:
                os.kill(loop_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def test_stale_pid_replaced(self, tmp_project):
        """Stale PID file (dead process) must be replaced with a fresh loop."""
        pid_file = tmp_project / ".cognitive-os" / "runtime" / "reaper-heartbeat.pid"

        # Plant a stale PID that definitely doesn't exist
        pid_file.write_text("99999999\n")

        rc, _out, err = _run_hook(tmp_project)
        assert rc == 0, f"Hook failed on stale PID: {err}"

        new_pid_str = pid_file.read_text().strip()
        assert new_pid_str.isdigit(), "PID file must be rewritten after stale PID"
        new_pid = int(new_pid_str)
        assert new_pid != 99999999, "PID file must have a new (real) PID"

        # Cleanup
        try:
            os.kill(new_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def test_reaper_invoked_by_background_loop(self, tmp_project):
        """Background loop must invoke so-reaper.sh at least once.

        The stub reaper appends a line to REAPER_MARKER_FILE.  We set the
        initial sleep to 0 by creating a patched hook that sets sleep 0 in the
        loop body (difficult to override), so we instead:
        - Provide a stub so-reaper.sh that is fast (just writes a file)
        - Wait up to 15s for the first real invocation (the hook sleeps 10s
          before the first run — so we wait 12s max).
        """
        marker_file = tmp_project / "reaper-ran.marker"
        env = {
            "REAPER_MARKER_FILE": str(marker_file),
        }

        rc, _out, err = _run_hook(tmp_project, env_overrides=env)
        assert rc == 0, f"Hook failed: {err}"

        pid_file = tmp_project / ".cognitive-os" / "runtime" / "reaper-heartbeat.pid"
        loop_pid_str = pid_file.read_text().strip()
        loop_pid = int(loop_pid_str)

        try:
            # The loop sleeps 10s before first run, then runs the reaper.
            # Wait up to 14 seconds.
            deadline = time.monotonic() + 14
            while time.monotonic() < deadline:
                if marker_file.exists() and marker_file.read_text().strip():
                    break
                time.sleep(0.5)

            assert marker_file.exists(), (
                "so-reaper.sh was never invoked within 14s — background loop may not be running"
            )
            content = marker_file.read_text().strip()
            assert "reaper-ran" in content, (
                f"Marker file content unexpected: {content!r}"
            )
        finally:
            try:
                os.kill(loop_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
