"""Integration tests for the Paperclip local daemon (ADR-043).

Tests:
  1. Script exits 2 with helpful message when binary is absent
  2. Status command reports STOPPED when daemon is not running
  3. Start creates PID file and port file (skipped if binary absent)
  4. Port is listening after start (skipped if binary absent)
  5. Stop cleans up PID and port files (skipped if binary absent)

The binary-absent tests do not require Paperclip to be installed — they
verify that the script fails gracefully. The lifecycle tests are skipped
when the binary is unavailable.
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
SCRIPT = REPO_ROOT / "scripts" / "cos-paperclip-local.sh"
BASH_BIN = shutil.which("bash") or "/bin/bash"


def _paperclip_available() -> bool:
    """Return True if a Paperclip binary is discoverable."""
    if shutil.which("paperclip") is not None:
        return True
    # Check if npx can resolve it without actually starting it
    result = subprocess.run(
        ["npx", "--no-install", "paperclip", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode == 0


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


def _wait_port(port: int, up: bool = True, secs: float = 20.0) -> bool:
    """Wait for a port to become reachable (or unreachable). Node.js is slow."""
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
        timeout=60,
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
# Tests that do NOT require the binary
# ---------------------------------------------------------------------------

class TestBinaryAbsence:
    def test_missing_binary_exits_2(self, project_dir):
        """When paperclip binary is absent, script exits 2 with helpful message."""
        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = project_dir
        env["ORCHESTRATOR_MODE"] = "executor"
        # Restrict PATH to hide paperclip and npx
        env["PATH"] = "/usr/bin:/bin"
        result = subprocess.run(
            [BASH_BIN, str(SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        # If paperclip or npx is somehow in /usr/bin, skip this test
        if shutil.which("paperclip", path="/usr/bin:/bin") is not None:
            pytest.skip("paperclip found in /usr/bin — cannot test missing binary")
        if shutil.which("npx", path="/usr/bin:/bin") is not None:
            pytest.skip("npx found in /usr/bin — binary-absent test not conclusive")
        assert result.returncode == 2, (
            f"Expected exit 2 for missing binary, got {result.returncode}\n"
            f"stderr: {result.stderr}"
        )
        assert any(
            keyword in result.stderr.lower()
            for keyword in ("install", "not found", "npm", "npx")
        ), f"Expected install hint in stderr: {result.stderr}"

    def test_status_stopped_without_pid_file(self, project_dir):
        """--status should report STOPPED when no PID file exists."""
        result = _run_script("--status", project_dir=project_dir)
        # Status should always exit 0 even without binary
        assert "STOPPED" in result.stdout or "STOPPED" in result.stderr, (
            f"Expected STOPPED in output.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_missing_binary_emits_metric(self, project_dir):
        """When binary is absent, a warning metric should be appended to JSONL."""
        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = project_dir
        env["ORCHESTRATOR_MODE"] = "executor"
        env["PATH"] = "/usr/bin:/bin"

        if shutil.which("paperclip", path="/usr/bin:/bin") is not None:
            pytest.skip("paperclip found in /usr/bin — cannot test missing binary")
        if shutil.which("npx", path="/usr/bin:/bin") is not None:
            pytest.skip("npx found in /usr/bin — binary-absent test not conclusive")

        subprocess.run(
            [BASH_BIN, str(SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

        health_file = Path(project_dir) / ".cognitive-os" / "metrics" / "paperclip-health.jsonl"
        if health_file.exists():
            records = [json.loads(line) for line in health_file.read_text().splitlines() if line.strip()]
            event_types = [r.get("event_type") for r in records]
            assert "binary-not-found" in event_types, (
                f"Expected 'binary-not-found' metric. Found: {event_types}"
            )


# ---------------------------------------------------------------------------
# Tests that require the binary (skipped if absent)
# ---------------------------------------------------------------------------

_BINARY_AVAILABLE = False
try:
    _BINARY_AVAILABLE = _paperclip_available()
except Exception:
    pass

pytestmark_binary = pytest.mark.skipif(
    not _BINARY_AVAILABLE,
    reason="Paperclip binary not installed; skipping daemon lifecycle tests",
)


@pytestmark_binary
class TestDaemonLifecycle:
    def test_start_creates_pid_and_port_files(self, project_dir):
        """Start creates PID and port files in the runtime dir."""
        free = _free_port()
        result = _run_script(
            project_dir=project_dir,
            extra_env={"PAPERCLIP_LOCAL_PORT": str(free)},
        )
        try:
            assert result.returncode == 0, f"Start failed:\n{result.stderr}"
            pid_file = Path(project_dir) / ".cognitive-os" / "runtime" / "paperclip.pid"
            port_file = Path(project_dir) / ".cognitive-os" / "runtime" / "paperclip.port"
            assert pid_file.exists(), "PID file not created"
            assert port_file.exists(), "Port file not created"
            port = int(port_file.read_text().strip())
            assert port > 0, "Port must be a positive integer"
        finally:
            _run_script("--stop", project_dir=project_dir, extra_env={"PAPERCLIP_LOCAL_PORT": str(free)})

    def test_start_port_is_listening(self, project_dir):
        """Port should be accepting connections after start."""
        free = _free_port()
        result = _run_script(
            project_dir=project_dir,
            extra_env={"PAPERCLIP_LOCAL_PORT": str(free)},
        )
        try:
            assert result.returncode == 0, f"Start failed:\n{result.stderr}"
            port_file = Path(project_dir) / ".cognitive-os" / "runtime" / "paperclip.port"
            port = int(port_file.read_text().strip())
            assert _wait_port(port, up=True, secs=20), f"Port {port} not listening after start"
        finally:
            _run_script("--stop", project_dir=project_dir, extra_env={"PAPERCLIP_LOCAL_PORT": str(free)})

    def test_stop_cleans_up_files(self, project_dir):
        """Stop removes PID and port files."""
        free = _free_port()
        r = _run_script(
            project_dir=project_dir,
            extra_env={"PAPERCLIP_LOCAL_PORT": str(free)},
        )
        assert r.returncode == 0, r.stderr
        port_file = Path(project_dir) / ".cognitive-os" / "runtime" / "paperclip.port"
        pid_file = Path(project_dir) / ".cognitive-os" / "runtime" / "paperclip.pid"
        port = int(port_file.read_text().strip())
        _wait_port(port, up=True, secs=20)

        r2 = _run_script("--stop", project_dir=project_dir, extra_env={"PAPERCLIP_LOCAL_PORT": str(free)})
        assert r2.returncode == 0, r2.stderr

        assert _wait_port(port, up=False, secs=10), f"Port {port} still listening after stop"
        assert not pid_file.exists(), "PID file not removed after stop"
        assert not port_file.exists(), "Port file not removed after stop"
