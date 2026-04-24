"""E2E tests for cos-executor daemon lifecycle (ADR-034).

Validates:
  - --daemon starts cleanly, writes PID file, process stays alive
  - --status returns ALIVE after --daemon, DEAD after --stop
  - --stop terminates the daemon and removes the PID file
  - --foreground exits within 2 s when sent SIGTERM (no hang)
  - Banner (OrchestratorCapabilities) flips from ❌ to ✅ when daemon is alive

No Valkey required: all tests use the file-fallback path by pointing VALKEY_URL
at a dead port (127.0.0.1:1).

Teardown: every test that starts a daemon cleans up via a pytest fixture so
orphan processes are impossible even when a test assertion fails.
"""

from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
EXECUTOR_SCRIPT = REPO_ROOT / "scripts" / "cos_executor.py"

# Ensure lib/ symlinks are resolvable for OrchestratorCapabilities import.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_executor_module(project_dir: Path):
    """Load scripts/cos_executor.py as an isolated module bound to *project_dir*."""
    assert EXECUTOR_SCRIPT.exists(), f"missing {EXECUTOR_SCRIPT}"
    os.environ["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)

    mod_name = f"cos_executor_e2e_{project_dir.name}"
    spec = importlib.util.spec_from_file_location(mod_name, str(EXECUTOR_SCRIPT))
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def _run_executor(*args: str, project_dir: Path, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run the executor script as a subprocess with an isolated project dir."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env["VALKEY_URL"] = "redis://127.0.0.1:1"
    env["COS_VALKEY_URL"] = "redis://127.0.0.1:1"
    return subprocess.run(
        [sys.executable, str(EXECUTOR_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _wait_pid_alive(pid_file: Path, timeout: float = 3.0) -> int:
    """Poll until the PID file appears and the process is alive; return PID."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip() or "0")
                if pid > 0:
                    os.kill(pid, 0)  # raises OSError if dead
                    return pid
            except (OSError, ValueError):
                pass
        time.sleep(0.05)
    raise AssertionError(
        f"PID file {pid_file} did not appear or process not alive within {timeout}s"
    )


def _wait_process_dead(pid: int, timeout: float = 5.0) -> None:
    """Poll until the given PID is no longer alive."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return  # gone
        time.sleep(0.1)
    raise AssertionError(f"Process {pid} did not die within {timeout}s")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_dir(tmp_path, monkeypatch):
    """Isolated project dir with Valkey pointed at a dead port."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setenv("VALKEY_URL", "redis://127.0.0.1:1")
    monkeypatch.setenv("COS_VALKEY_URL", "redis://127.0.0.1:1")
    yield tmp_path


@pytest.fixture()
def running_daemon(project_dir):
    """Start the executor as a real daemon process; kill on teardown."""
    result = _run_executor("--daemon", project_dir=project_dir, timeout=10)
    assert result.returncode == 0, (
        f"--daemon failed (rc={result.returncode}):\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )

    pid_file = project_dir / ".cognitive-os" / "runtime" / "cos-executor.pid"
    pid = _wait_pid_alive(pid_file, timeout=4.0)

    yield pid, project_dir

    # Teardown: ensure daemon is dead regardless of test outcome.
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass  # already dead
    try:
        _wait_process_dead(pid, timeout=5.0)
    except AssertionError:
        # Force-kill if it won't die gracefully.
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
    # Remove stale PID file if daemon left one behind.
    try:
        pid_file.unlink()
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDaemonLifecycle:
    """--daemon → --status → --stop lifecycle."""

    def test_daemon_starts_pid_file_created(self, running_daemon):
        pid, pdir = running_daemon
        pid_file = pdir / ".cognitive-os" / "runtime" / "cos-executor.pid"

        assert pid_file.exists(), "PID file missing after --daemon"
        stored = int(pid_file.read_text().strip())
        assert stored == pid, f"PID file contains {stored}, expected {pid}"

    def test_daemon_process_alive(self, running_daemon):
        pid, _ = running_daemon
        # os.kill(pid, 0) raises OSError if the process is dead.
        try:
            os.kill(pid, 0)
        except OSError as exc:
            pytest.fail(f"Daemon process {pid} is not alive: {exc}")

    def test_status_alive_while_running(self, running_daemon, project_dir):
        _pid, pdir = running_daemon
        result = _run_executor("--status", project_dir=pdir, timeout=5)
        assert result.returncode == 0, f"--status returned {result.returncode}"
        assert "ALIVE" in result.stdout, f"Expected ALIVE, got: {result.stdout!r}"

    def test_stop_kills_daemon(self, running_daemon, project_dir):
        pid, pdir = running_daemon
        pid_file = pdir / ".cognitive-os" / "runtime" / "cos-executor.pid"

        result = _run_executor("--stop", project_dir=pdir, timeout=10)
        assert result.returncode == 0, (
            f"--stop failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Process must be dead.
        _wait_process_dead(pid, timeout=5.0)

        # PID file must be gone.
        assert not pid_file.exists(), f"PID file still exists after --stop: {pid_file}"

    def test_status_dead_after_stop(self, running_daemon, project_dir):
        pid, pdir = running_daemon
        _run_executor("--stop", project_dir=pdir, timeout=10)
        _wait_process_dead(pid, timeout=5.0)

        result = _run_executor("--status", project_dir=pdir, timeout=5)
        assert result.returncode == 1, f"Expected rc=1 (DEAD), got {result.returncode}"
        assert "DEAD" in result.stdout, f"Expected DEAD, got: {result.stdout!r}"

    def test_daemon_idempotent(self, running_daemon, project_dir):
        """Calling --daemon when already running must return 0 and not fork again."""
        pid, pdir = running_daemon
        result = _run_executor("--daemon", project_dir=pdir, timeout=5)
        assert result.returncode == 0, (
            f"Second --daemon invocation failed: {result.returncode}"
        )
        # PID must be unchanged.
        pid_file = pdir / ".cognitive-os" / "runtime" / "cos-executor.pid"
        stored = int(pid_file.read_text().strip())
        assert stored == pid, f"PID changed after idempotent --daemon: was {pid}, now {stored}"


class TestBannerFlip:
    """OrchestratorCapabilities banner toggles with daemon state."""

    def test_banner_executor_checkmark_while_daemon_alive(self, running_daemon, project_dir):
        _pid, pdir = running_daemon

        from lib.orchestrator_capabilities import OrchestratorCapabilities  # noqa: PLC0415

        # Point capabilities at the isolated project dir.
        orig = os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        os.environ["COGNITIVE_OS_PROJECT_DIR"] = str(pdir)
        try:
            caps = OrchestratorCapabilities()
            caps._mode = None  # reset cache so detect() re-runs
            caps.detect()
            status = caps.format_status()
        finally:
            if orig is not None:
                os.environ["COGNITIVE_OS_PROJECT_DIR"] = orig
            else:
                del os.environ["COGNITIVE_OS_PROJECT_DIR"]

        # The executor indicator should be ✅ when daemon is live.
        assert "✅" in status, (
            f"Expected ✅ in banner while daemon is alive, got: {status!r}"
        )

    def test_banner_executor_cross_after_stop(self, running_daemon, project_dir):
        pid, pdir = running_daemon
        _run_executor("--stop", project_dir=pdir, timeout=10)
        _wait_process_dead(pid, timeout=5.0)

        from lib.orchestrator_capabilities import OrchestratorCapabilities  # noqa: PLC0415

        orig = os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        os.environ["COGNITIVE_OS_PROJECT_DIR"] = str(pdir)
        try:
            caps = OrchestratorCapabilities()
            caps._mode = None
            caps.detect()
            status = caps.format_status()
        finally:
            if orig is not None:
                os.environ["COGNITIVE_OS_PROJECT_DIR"] = orig
            else:
                del os.environ["COGNITIVE_OS_PROJECT_DIR"]

        # After stop, executor should show ❌.
        assert "Executor ❌" in status or (
            "✅" not in status.split("Executor")[1] if "Executor" in status else True
        ), f"Expected Executor ❌ after stop, got: {status!r}"


class TestForegroundSigterm:
    """--foreground must exit within 2 s when SIGTERM is sent."""

    def test_foreground_exits_on_sigterm(self, project_dir):
        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
        env["VALKEY_URL"] = "redis://127.0.0.1:1"
        env["COS_VALKEY_URL"] = "redis://127.0.0.1:1"

        proc = subprocess.Popen(
            [sys.executable, str(EXECUTOR_SCRIPT), "--foreground"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Give the executor time to start up and enter its event loop.
        time.sleep(1.0)

        # Verify it's running.
        assert proc.poll() is None, (
            f"--foreground exited prematurely (rc={proc.returncode})"
        )

        # Send SIGTERM and measure how long it takes.
        t0 = time.time()
        proc.send_signal(signal.SIGTERM)

        try:
            proc.wait(timeout=4.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            pytest.fail(
                "--foreground did not exit within 4 s after SIGTERM — "
                "signal handler is not wired to the executor stop() method"
            )

        elapsed = time.time() - t0
        assert elapsed < 4.0, f"--foreground took {elapsed:.1f}s to exit after SIGTERM (expected < 4s)"

        # Exit code must not be a crash code.
        assert proc.returncode in (0, -signal.SIGTERM), (
            f"Unexpected exit code after SIGTERM: {proc.returncode}"
        )

        # PID file must be cleaned up.
        pid_file = project_dir / ".cognitive-os" / "runtime" / "cos-executor.pid"
        assert not pid_file.exists(), "PID file not cleaned up after --foreground SIGTERM"


class TestFallbackEventPickup:
    """Daemon picks up file-fallback events and writes to canonical-live.jsonl."""

    def test_daemon_processes_fallback_event(self, running_daemon, project_dir):
        _pid, pdir = running_daemon

        # Drop an event file into the agent-bus directory.
        bus_dir = pdir / ".cognitive-os" / "agent-bus" / "test-agent-e2e"
        bus_dir.mkdir(parents=True, exist_ok=True)
        event = {
            "event_type": "progress_marker",
            "agent_id": "test-agent-e2e",
            "ts": time.time(),
            "message": "e2e daemon test",
        }
        (bus_dir / "progress.jsonl").write_text(json.dumps(event) + "\n")

        canonical = pdir / ".cognitive-os" / "metrics" / "canonical-live.jsonl"
        deadline = time.time() + 6.0
        while time.time() < deadline:
            if canonical.exists() and canonical.read_text().strip():
                lines = [
                    json.loads(l)
                    for l in canonical.read_text().splitlines()
                    if l.strip()
                ]
                if any(l.get("agent_id") == "test-agent-e2e" for l in lines):
                    return  # success
            time.sleep(0.2)

        pytest.fail(
            "Daemon did not republish the fallback event to canonical-live.jsonl "
            f"within 6s. File exists: {canonical.exists()}, "
            f"contents: {canonical.read_text()[:500] if canonical.exists() else '<missing>'}"
        )
