"""Tests for hooks/session-watchdog-launcher.sh — ADR-047 Phase A auto-start.

The launcher is a bash SessionStart hook that ensures a singleton daemon for
scripts/so_session_watchdog.py is running. It MUST:

  * be idempotent — re-running with a live pidfile does NOT spawn a new daemon
  * clean up stale pidfiles (process dead) and spawn a fresh daemon
  * respect COS_SESSION_WATCHDOG_DISABLE=1 (exit 0, no spawn)
  * respect runtime.session_watchdog.enabled: false in cognitive-os.yaml
  * always exit 0 (MUST NOT block session start)

These tests run the real bash script against a temporary PROJECT_DIR with a
stub watchdog that would-spawn-but-doesn't-loop (simulated via flag files).
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import textwrap
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LAUNCHER = REPO_ROOT / "hooks" / "session-watchdog-launcher.sh"


def _make_project(tmp_path: Path, *, yaml_enabled: bool | None = True,
                  include_watchdog_script: bool = True) -> Path:
    """Create a minimal fake project dir that the launcher can operate on.

    - Writes a stub scripts/so_session_watchdog.py that exits immediately
      (so no real daemon lingers during tests).
    - Writes cognitive-os.yaml with the requested session_watchdog.enabled.
    - Creates hooks/_lib/killswitch_check.sh as a no-op source file.
    - Symlinks the real launcher under hooks/.
    """
    (tmp_path / "scripts").mkdir()
    (tmp_path / "hooks" / "_lib").mkdir(parents=True)
    (tmp_path / ".cognitive-os" / "runtime").mkdir(parents=True)

    # No-op killswitch stub (the real launcher sources it).
    (tmp_path / "hooks" / "_lib" / "killswitch_check.sh").write_text(
        "#!/usr/bin/env bash\n# no-op stub for tests\nreturn 0 2>/dev/null || true\n"
    )

    if include_watchdog_script:
        # A tiny stub: accept args, write a marker, exit. Not a real daemon.
        stub = textwrap.dedent("""\
            #!/usr/bin/env python3
            import os, sys, time, pathlib
            marker = pathlib.Path(os.environ.get("COGNITIVE_OS_PROJECT_DIR", ".")) / ".cognitive-os" / "runtime" / "spawned.flag"
            marker.write_text(" ".join(sys.argv))
            # Sleep briefly so the parent can observe the PID alive, then exit.
            time.sleep(0.5)
            sys.exit(0)
        """)
        script_path = tmp_path / "scripts" / "so_session_watchdog.py"
        script_path.write_text(stub)
        script_path.chmod(0o755)

    if yaml_enabled is not None:
        enabled_str = "true" if yaml_enabled else "false"
        (tmp_path / "cognitive-os.yaml").write_text(
            "runtime:\n"
            "  session_watchdog:\n"
            f"    enabled: {enabled_str}\n"
            '    mode: "log-only"\n'
            "    ttl_hours: 6\n"
        )
    # Copy launcher into the temp project so CLAUDE_PROJECT_DIR resolution works.
    dest = tmp_path / "hooks" / "session-watchdog-launcher.sh"
    shutil.copy(LAUNCHER, dest)
    dest.chmod(0o755)
    return tmp_path


def _run_launcher(project: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    env["CLAUDE_PROJECT_DIR"] = str(project)
    # Unset opt-out unless overridden
    env.pop("COS_SESSION_WATCHDOG_DISABLE", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(project / "hooks" / "session-watchdog-launcher.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _cleanup_spawned(project: Path) -> None:
    """Kill any daemon spawned during a test to prevent orphans."""
    pid_file = project / ".cognitive-os" / "runtime" / "session-watchdog.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        except (ValueError, OSError):
            pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_exit_code_always_zero(tmp_path):
    """Launcher MUST exit 0 even when the watchdog script is missing."""
    project = _make_project(tmp_path, include_watchdog_script=False)
    result = _run_launcher(project)
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_respects_opt_out_env_var(tmp_path):
    """COS_SESSION_WATCHDOG_DISABLE=1 must short-circuit to exit 0 with no spawn."""
    project = _make_project(tmp_path, yaml_enabled=True)
    result = _run_launcher(project, extra_env={"COS_SESSION_WATCHDOG_DISABLE": "1"})
    assert result.returncode == 0
    # No pidfile, no marker should be created
    assert not (project / ".cognitive-os" / "runtime" / "session-watchdog.pid").exists()
    assert not (project / ".cognitive-os" / "runtime" / "spawned.flag").exists()


def test_respects_feature_flag_disabled(tmp_path):
    """runtime.session_watchdog.enabled: false in cognitive-os.yaml → no spawn."""
    project = _make_project(tmp_path, yaml_enabled=False)
    result = _run_launcher(project)
    assert result.returncode == 0
    assert not (project / ".cognitive-os" / "runtime" / "session-watchdog.pid").exists()
    assert not (project / ".cognitive-os" / "runtime" / "spawned.flag").exists()


def test_spawns_if_no_pidfile(tmp_path):
    """No pidfile present → launcher spawns the daemon."""
    project = _make_project(tmp_path, yaml_enabled=True)
    try:
        result = _run_launcher(project)
        assert result.returncode == 0
        pid_file = project / ".cognitive-os" / "runtime" / "session-watchdog.pid"
        assert pid_file.exists(), f"pidfile not created; stderr={result.stderr}"
        pid = int(pid_file.read_text().strip())
        assert pid > 0
        # Stderr should confirm the PID
        assert "daemon ensured" in result.stderr
        # Give the stub time to write its marker
        time.sleep(0.2)
        marker = project / ".cognitive-os" / "runtime" / "spawned.flag"
        assert marker.exists(), "Stub watchdog did not run"
        assert "--daemon" in marker.read_text()
        assert "--interval" in marker.read_text()
    finally:
        _cleanup_spawned(project)


def test_skips_if_daemon_already_running(tmp_path):
    """Existing pidfile + live process matching watchdog cmdline → no re-spawn."""
    project = _make_project(tmp_path, yaml_enabled=True)
    runtime = project / ".cognitive-os" / "runtime"

    # Spawn a fake long-running process whose cmdline contains the watchdog signature.
    # Use python so the cmdline reliably includes 'so_session_watchdog.py'.
    fake = subprocess.Popen(
        ["python3", "-c",
         "import sys, time; sys.argv.append('so_session_watchdog.py'); time.sleep(30)"],
    )
    try:
        # Write pidfile pointing at the fake process
        (runtime / "session-watchdog.pid").write_text(str(fake.pid))

        result = _run_launcher(project)
        assert result.returncode == 0
        # Pidfile should still point at the live fake (not replaced)
        assert (runtime / "session-watchdog.pid").read_text().strip() == str(fake.pid)
        # The stub should NOT have been executed (no marker)
        assert not (runtime / "spawned.flag").exists(), \
            "Launcher spawned a new daemon despite one being alive"
    finally:
        fake.terminate()
        try:
            fake.wait(timeout=3)
        except subprocess.TimeoutExpired:
            fake.kill()


def test_spawns_if_pid_stale(tmp_path):
    """Pidfile points at a dead PID → stale, cleaned up, fresh daemon spawned."""
    project = _make_project(tmp_path, yaml_enabled=True)
    runtime = project / ".cognitive-os" / "runtime"

    # Find a PID that definitely does not exist. Spawn+reap a short-lived process.
    dead = subprocess.Popen(["true"])
    dead.wait()
    dead_pid = dead.pid
    # Guard: ensure it's really gone
    try:
        os.kill(dead_pid, 0)
        pytest.skip(f"PID {dead_pid} unexpectedly still alive; cannot test stale path")
    except ProcessLookupError:
        pass

    (runtime / "session-watchdog.pid").write_text(str(dead_pid))

    try:
        result = _run_launcher(project)
        assert result.returncode == 0
        # Pidfile should now point at a NEW (live or recently-live) PID, not the dead one
        new_pid_str = (runtime / "session-watchdog.pid").read_text().strip()
        assert new_pid_str, "Pidfile empty after stale cleanup"
        assert int(new_pid_str) != dead_pid, "Stale PID not replaced"
        # Marker proves the stub was executed
        time.sleep(0.2)
        assert (runtime / "spawned.flag").exists()
    finally:
        _cleanup_spawned(project)
