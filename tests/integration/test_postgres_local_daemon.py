"""Integration tests for the PostgreSQL local daemon (ADR-045).

Tests:
  1. Script exits 2 with helpful message when pg_ctl is absent
  2. Status command reports STOPPED when daemon is not running
  3. --init creates a valid data directory (skipped if pg_ctl absent)
  4. Start creates PID file and port file and cluster is reachable (skipped if absent)
  5. Stop cleans up PID and port files and closes port (skipped if absent)

initdb can take 2-5 seconds; lifecycle tests use @pytest.mark.timeout(120).
Skips gracefully when pg_ctl / initdb is not installed.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos-postgres-local.sh"
BASH_BIN = shutil.which("bash") or "/bin/bash"


def _pgctl_available() -> bool:
    """Return True if pg_ctl is discoverable in PATH or common Homebrew paths."""
    if shutil.which("pg_ctl") is not None:
        return True
    for ver in (17, 16, 15, 14):
        for prefix in ("/opt/homebrew/opt", "/usr/local/opt"):
            candidate = Path(f"{prefix}/postgresql@{ver}/bin/pg_ctl")
            if candidate.exists():
                return True
    return False


def _free_port() -> int:
    """Return an ephemeral port that is not currently bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _port_listening(port: int, timeout: float = 0.5) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except OSError:
        return False


def _wait_port(port: int, up: bool = True, secs: float = 15.0) -> bool:
    """Wait for a port to become reachable (or unreachable)."""
    deadline = time.monotonic() + secs
    while time.monotonic() < deadline:
        if _port_listening(port) == up:
            return True
        time.sleep(0.2)
    return False


def _run_script(*args: str, project_dir: str, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = project_dir
    env["ORCHESTRATOR_MODE"] = "executor"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [BASH_BIN, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def project_dir(tmp_path: Path):
    runtime = tmp_path / ".cognitive-os" / "runtime"
    metrics = tmp_path / ".cognitive-os" / "metrics"
    runtime.mkdir(parents=True)
    metrics.mkdir(parents=True)
    yield str(tmp_path)


# ---------------------------------------------------------------------------
# Tests that do NOT require pg_ctl
# ---------------------------------------------------------------------------

class TestBinaryAbsence:
    def test_missing_binary_exits_2(self, project_dir):
        """When pg_ctl is absent, script exits 2 with helpful message."""
        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = project_dir
        env["ORCHESTRATOR_MODE"] = "executor"
        # Restrict PATH to hide pg_ctl and Homebrew paths
        env["PATH"] = "/usr/bin:/bin"
        result = subprocess.run(
            [BASH_BIN, str(SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        if shutil.which("pg_ctl", path="/usr/bin:/bin") is not None:
            pytest.skip("pg_ctl found in /usr/bin — cannot test missing binary")
        # Also check Homebrew paths are really gone with the restricted PATH
        # If the script can find pg_ctl via hardcoded Homebrew paths, skip
        for ver in (17, 16, 15, 14):
            for prefix in ("/opt/homebrew/opt", "/usr/local/opt"):
                if Path(f"{prefix}/postgresql@{ver}/bin/pg_ctl").exists():
                    pytest.skip(f"pg_ctl found at Homebrew path — restricted PATH test not applicable")
        assert result.returncode == 2, (
            f"Expected exit 2 for missing binary, got {result.returncode}\n"
            f"stderr: {result.stderr}"
        )
        assert any(
            keyword in result.stderr.lower()
            for keyword in ("install", "not found", "brew", "pg_ctl")
        ), f"Expected install hint in stderr: {result.stderr}"

    def test_status_stopped_without_pid_file(self, project_dir):
        """--status should report STOPPED when no PID file exists."""
        result = _run_script("--status", project_dir=project_dir)
        combined = result.stdout + result.stderr
        assert "STOPPED" in combined, (
            f"Expected STOPPED in output.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Tests that require pg_ctl / initdb (skipped if absent)
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not _pgctl_available(),
    reason="pg_ctl not installed; skipping PostgreSQL local daemon lifecycle tests",
)


@pytest.mark.timeout(120)
class TestDaemonInit:
    def test_init_creates_data_directory(self, project_dir):
        """--init should create a valid PostgreSQL data directory."""
        result = _run_script("--init", project_dir=project_dir)
        assert result.returncode == 0, (
            f"--init failed (exit {result.returncode}):\n{result.stderr}"
        )
        data_dir = Path(project_dir) / ".cognitive-os" / "runtime" / "postgres-data"
        assert data_dir.exists(), "Data directory not created by --init"
        # A valid initdb output always contains a 'global' subdirectory
        assert (data_dir / "global").exists(), "'global' subdir missing — initdb may have failed"

    def test_init_idempotent(self, project_dir):
        """Calling --init twice should not fail or overwrite."""
        r1 = _run_script("--init", project_dir=project_dir)
        assert r1.returncode == 0, r1.stderr
        data_dir = Path(project_dir) / ".cognitive-os" / "runtime" / "postgres-data"
        mtime_before = (data_dir / "global").stat().st_mtime

        r2 = _run_script("--init", project_dir=project_dir)
        assert r2.returncode == 0, r2.stderr
        mtime_after = (data_dir / "global").stat().st_mtime
        # Second call should skip (no reinit) — mtime unchanged
        assert mtime_before == mtime_after, "Second --init overwrote existing cluster"


@pytest.mark.timeout(120)
class TestDaemonLifecycle:
    def test_start_creates_pid_and_port_files(self, project_dir):
        """Start creates PID and port files in the runtime dir."""
        free = _free_port()
        result = _run_script(
            project_dir=project_dir,
            extra_env={"POSTGRES_LOCAL_PORT": str(free)},
        )
        try:
            assert result.returncode == 0, (
                f"Start failed (exit {result.returncode}):\n{result.stderr}"
            )
            pid_file = Path(project_dir) / ".cognitive-os" / "runtime" / "postgres.pid"
            port_file = Path(project_dir) / ".cognitive-os" / "runtime" / "postgres.port"
            assert pid_file.exists(), "PID file not created"
            assert port_file.exists(), "Port file not created"
            port = int(port_file.read_text().strip())
            assert port > 0, "Port must be a positive integer"
        finally:
            _run_script("--stop", project_dir=project_dir, extra_env={"POSTGRES_LOCAL_PORT": str(free)})

    def test_start_port_is_listening(self, project_dir):
        """Port should accept connections after start."""
        free = _free_port()
        result = _run_script(
            project_dir=project_dir,
            extra_env={"POSTGRES_LOCAL_PORT": str(free)},
        )
        try:
            assert result.returncode == 0, (
                f"Start failed:\n{result.stderr}"
            )
            port_file = Path(project_dir) / ".cognitive-os" / "runtime" / "postgres.port"
            port = int(port_file.read_text().strip())
            assert _wait_port(port, up=True, secs=15), f"Port {port} not listening after start"
        finally:
            _run_script("--stop", project_dir=project_dir, extra_env={"POSTGRES_LOCAL_PORT": str(free)})

    def test_stop_cleans_up_files(self, project_dir):
        """Stop removes PID and port files and closes the port."""
        free = _free_port()
        r = _run_script(
            project_dir=project_dir,
            extra_env={"POSTGRES_LOCAL_PORT": str(free)},
        )
        assert r.returncode == 0, r.stderr
        port_file = Path(project_dir) / ".cognitive-os" / "runtime" / "postgres.port"
        pid_file = Path(project_dir) / ".cognitive-os" / "runtime" / "postgres.pid"
        port = int(port_file.read_text().strip())
        _wait_port(port, up=True, secs=15)

        r2 = _run_script("--stop", project_dir=project_dir, extra_env={"POSTGRES_LOCAL_PORT": str(free)})
        assert r2.returncode == 0, r2.stderr

        assert _wait_port(port, up=False, secs=10), f"Port {port} still listening after stop"
        assert not pid_file.exists(), "PID file not removed after stop"
        assert not port_file.exists(), "Port file not removed after stop"

    def test_start_emits_started_metric(self, project_dir):
        """Start should append a 'started' event to postgres-health.jsonl."""
        free = _free_port()
        r = _run_script(
            project_dir=project_dir,
            extra_env={"POSTGRES_LOCAL_PORT": str(free)},
        )
        try:
            assert r.returncode == 0, r.stderr
            health_file = Path(project_dir) / ".cognitive-os" / "metrics" / "postgres-health.jsonl"
            assert health_file.exists(), "postgres-health.jsonl not created"
            records = [json.loads(line) for line in health_file.read_text().splitlines() if line.strip()]
            event_types = [rec.get("event_type") for rec in records]
            assert "started" in event_types, f"No 'started' event found. Events: {event_types}"
        finally:
            _run_script("--stop", project_dir=project_dir, extra_env={"POSTGRES_LOCAL_PORT": str(free)})
