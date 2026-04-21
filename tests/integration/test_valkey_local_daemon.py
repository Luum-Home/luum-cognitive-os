"""Integration tests for the Valkey local daemon (ADR-042).

Tests:
  1. Start daemon — PID file created, port is listening
  2. Client can connect and SET/GET works
  3. Stop daemon — process exits cleanly, PID file removed
  4. Idempotent start — second start call is a no-op
  5. agent_bus._resolve_valkey_url discovers running daemon
  6. valkey-health.jsonl updated on start and stop

Requires redis-server or valkey-server to be installed locally.
Skips gracefully when neither binary is available.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos-valkey-local.sh"
BASH_BIN = shutil.which("bash") or "/bin/bash"


def _server_available() -> bool:
    return shutil.which("valkey-server") is not None or shutil.which("redis-server") is not None


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


def _wait_port(port: int, up: bool = True, secs: float = 8.0) -> bool:
    deadline = time.monotonic() + secs
    while time.monotonic() < deadline:
        if _port_listening(port) == up:
            return True
        time.sleep(0.1)
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
    )


# ---------------------------------------------------------------------------
# Skip if binary not found
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    not _server_available(),
    reason="Neither valkey-server nor redis-server is installed; skipping local daemon tests",
)


# ---------------------------------------------------------------------------
# Fixture: isolated project dir with runtime/metrics dirs + free port
# ---------------------------------------------------------------------------

@pytest.fixture()
def project_dir(tmp_path: Path):
    runtime = tmp_path / ".cognitive-os" / "runtime"
    metrics = tmp_path / ".cognitive-os" / "metrics"
    runtime.mkdir(parents=True)
    metrics.mkdir(parents=True)
    yield str(tmp_path)


@pytest.fixture()
def free_port() -> int:
    return _free_port()


@pytest.fixture()
def running_daemon(project_dir: str, free_port: int):
    """Start the daemon on a free port, yield (project_dir, port), then stop."""
    result = _run_script(
        project_dir=project_dir,
        extra_env={"VALKEY_LOCAL_PORT": str(free_port)},
    )
    assert result.returncode == 0, f"Daemon start failed:\n{result.stderr}"
    port_file = Path(project_dir) / ".cognitive-os" / "runtime" / "valkey.port"
    # Wait for port file
    deadline = time.monotonic() + 8
    while not port_file.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    assert port_file.exists(), "Port file not created"
    port = int(port_file.read_text().strip())
    assert _wait_port(port, up=True), f"Port {port} not listening after daemon start"
    yield project_dir, port
    _run_script("--stop", project_dir=project_dir, extra_env={"VALKEY_LOCAL_PORT": str(free_port)})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDaemonLifecycle:
    def test_start_creates_pid_file(self, running_daemon):
        project_dir, port = running_daemon
        pid_file = Path(project_dir) / ".cognitive-os" / "runtime" / "valkey.pid"
        assert pid_file.exists(), "PID file not created"
        pid = int(pid_file.read_text().strip())
        assert pid > 0, "PID must be positive integer"

    def test_start_port_is_listening(self, running_daemon):
        project_dir, port = running_daemon
        assert _port_listening(port), f"Port {port} not listening"

    def test_client_set_get(self, running_daemon):
        project_dir, port = running_daemon
        try:
            import redis
        except ImportError:
            pytest.skip("redis package not installed")
        client = redis.Redis(host="127.0.0.1", port=port, decode_responses=True)
        client.set("adr042:test:key", "hello_daemon")
        val = client.get("adr042:test:key")
        assert val == "hello_daemon", f"Expected 'hello_daemon', got {val!r}"
        client.delete("adr042:test:key")

    def test_stop_kills_process(self, project_dir, free_port):
        # Start
        r = _run_script(
            project_dir=project_dir,
            extra_env={"VALKEY_LOCAL_PORT": str(free_port)},
        )
        assert r.returncode == 0, r.stderr
        port_file = Path(project_dir) / ".cognitive-os" / "runtime" / "valkey.port"
        deadline = time.monotonic() + 8
        while not port_file.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        port = int(port_file.read_text().strip())
        assert _wait_port(port, up=True)

        # Stop
        r2 = _run_script(
            "--stop",
            project_dir=project_dir,
            extra_env={"VALKEY_LOCAL_PORT": str(free_port)},
        )
        assert r2.returncode == 0, r2.stderr

        # Verify port closed
        assert _wait_port(port, up=False, secs=6), f"Port {port} still listening after stop"

        # PID and port files removed
        pid_file = Path(project_dir) / ".cognitive-os" / "runtime" / "valkey.pid"
        assert not pid_file.exists(), "PID file not cleaned up"
        assert not port_file.exists(), "Port file not cleaned up"

    def test_idempotent_start(self, running_daemon, free_port):
        project_dir, port = running_daemon
        pid_file = Path(project_dir) / ".cognitive-os" / "runtime" / "valkey.pid"
        first_pid = int(pid_file.read_text().strip())

        # Second start — should be no-op
        r = _run_script(
            project_dir=project_dir,
            extra_env={"VALKEY_LOCAL_PORT": str(free_port)},
        )
        assert r.returncode == 0, r.stderr
        second_pid = int(pid_file.read_text().strip())
        assert first_pid == second_pid, "Second start must not spawn a new process"


class TestMetrics:
    def test_start_emits_metric(self, running_daemon):
        project_dir, port = running_daemon
        health_file = Path(project_dir) / ".cognitive-os" / "metrics" / "valkey-health.jsonl"
        assert health_file.exists(), "valkey-health.jsonl not created"
        records = [json.loads(line) for line in health_file.read_text().splitlines() if line.strip()]
        event_types = [r.get("event_type") for r in records]
        assert "started" in event_types, f"No 'started' event found. Events: {event_types}"
        # Verify port is logged
        started_records = [r for r in records if r.get("event_type") == "started"]
        assert started_records[0].get("port") == port

    def test_stop_emits_metric(self, project_dir, free_port):
        r = _run_script(
            project_dir=project_dir,
            extra_env={"VALKEY_LOCAL_PORT": str(free_port)},
        )
        assert r.returncode == 0, r.stderr
        port_file = Path(project_dir) / ".cognitive-os" / "runtime" / "valkey.port"
        deadline = time.monotonic() + 8
        while not port_file.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        port = int(port_file.read_text().strip())
        _wait_port(port, up=True)

        _run_script(
            "--stop",
            project_dir=project_dir,
            extra_env={"VALKEY_LOCAL_PORT": str(free_port)},
        )

        health_file = Path(project_dir) / ".cognitive-os" / "metrics" / "valkey-health.jsonl"
        records = [json.loads(line) for line in health_file.read_text().splitlines() if line.strip()]
        event_types = [r.get("event_type") for r in records]
        assert "stopped" in event_types, f"No 'stopped' event found. Events: {event_types}"


class TestAgentBusIntegration:
    def test_resolve_valkey_url_finds_local_daemon(self, running_daemon):
        """_resolve_valkey_url should return a URL when local daemon is running."""
        project_dir, port = running_daemon
        sys.path.insert(0, str(REPO_ROOT))
        try:
            import importlib
            import lib.agent_bus as ab
            importlib.reload(ab)

            # Point primary URL directly at the daemon's port
            url = f"redis://localhost:{port}"
            resolved = ab._resolve_valkey_url(url)
            assert resolved is not None, "_resolve_valkey_url returned None for running daemon"
            assert str(port) in resolved, f"Resolved URL {resolved!r} does not contain port {port}"
        finally:
            if str(REPO_ROOT) in sys.path:
                sys.path.remove(str(REPO_ROOT))

    def test_resolve_valkey_url_unreachable_returns_none(self):
        """_resolve_valkey_url returns None when no server is available on the given URL."""
        sys.path.insert(0, str(REPO_ROOT))
        try:
            import importlib
            import lib.agent_bus as ab
            importlib.reload(ab)
            # Use a port that should definitely not be listening
            dead_url = "redis://localhost:19379"
            # Temporarily patch the fallback list to avoid hitting real local servers
            orig = ab._LOCAL_FALLBACK_URLS
            ab._LOCAL_FALLBACK_URLS = []
            try:
                resolved = ab._resolve_valkey_url(dead_url)
                assert resolved is None, f"Expected None for unreachable URL, got {resolved!r}"
            finally:
                ab._LOCAL_FALLBACK_URLS = orig
        finally:
            if str(REPO_ROOT) in sys.path:
                sys.path.remove(str(REPO_ROOT))


class TestBinaryDetection:
    def test_missing_binary_exits_2(self, project_dir):
        """When neither binary exists, script exits 2 with helpful message."""
        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = project_dir
        env["ORCHESTRATOR_MODE"] = "executor"
        # Override PATH to hide redis/valkey binaries but keep bash itself
        # Use a dir that exists but has no redis/valkey
        env["PATH"] = "/usr/bin:/bin"
        result = subprocess.run(
            [BASH_BIN, str(SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )
        if shutil.which("valkey-server", path="/usr/bin:/bin") or shutil.which("redis-server", path="/usr/bin:/bin"):
            pytest.skip("valkey-server/redis-server found in /usr/bin — cannot test missing binary on this machine")
        assert result.returncode == 2, f"Expected exit 2, got {result.returncode}\nstderr: {result.stderr}"
        assert any(
            keyword in result.stderr.lower()
            for keyword in ("install", "not found", "brew")
        ), f"Expected install hint in stderr: {result.stderr}"
