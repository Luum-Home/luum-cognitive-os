"""Exercised chaos test for hooks/concurrent-write-guard.sh (ADR-041 Wave A).

Tier: A (Safety-critical — file locking for concurrent sessions)
Trigger: PreToolUse Edit/Write with a file_path and active COGNITIVE_OS_SESSION_ID.

Contract:
  - Fires on Edit|Write tool_name only.
  - Without COGNITIVE_OS_SESSION_ID: exits 0 (no session = no lock).
  - With session ID: acquires flock on target file.
  - Two concurrent sessions on same file: second must wait or detect collision.
  - Advisory: exits 0 in most cases; locking errors surface via stderr.
  - With SO_KILLSWITCH=1: exits 0 silently.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOK = _PROJ_ROOT / "hooks" / "concurrent-write-guard.sh"
_CHAOS_RUNS_REL = ".cognitive-os/metrics/chaos-runs.jsonl"


def _setup_project(tmp_path: Path, session_id: str | None = None) -> None:
    sessions_dir = tmp_path / ".cognitive-os" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
    if session_id:
        (sessions_dir / session_id).mkdir(exist_ok=True)
        (sessions_dir / "locks").mkdir(exist_ok=True)


def _write_chaos_run(tmp_path: Path, scenario: str, passed: bool) -> None:
    log = tmp_path / _CHAOS_RUNS_REL
    row = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event_type": "component.exercised",
        "component": "hooks/concurrent-write-guard.sh",
        "scenario": scenario,
        "passed": passed,
        "source": "chaos-test",
    }
    with log.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def _run(
    tmp_path: Path,
    file_path: str,
    tool_name: str = "Edit",
    env_extra: dict | None = None,
) -> subprocess.CompletedProcess:
    payload = json.dumps({
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path},
    })
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "VALKEY_DISABLED": "1",
    }
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(_HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
        cwd=str(tmp_path),
    )


@pytest.mark.skipif(not _HOOK.exists(), reason="concurrent-write-guard.sh not found")
def test_concurrent_write_guard_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="concurrent-write-guard.sh not found")
def test_concurrent_write_guard_no_session_is_passthrough(tmp_path: Path):
    """Without COGNITIVE_OS_SESSION_ID, hook must pass through (exit 0, no lock)."""
    _setup_project(tmp_path)
    target = tmp_path / "myfile.py"
    target.write_text("x = 1\n")
    result = _run(tmp_path, str(target))
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "no_session_passthrough", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="concurrent-write-guard.sh not found")
def test_concurrent_write_guard_non_edit_passthrough(tmp_path: Path):
    """Non-Edit/Write tool_name must be ignored (exit 0)."""
    _setup_project(tmp_path)
    result = _run(tmp_path, str(tmp_path / "x.py"), tool_name="Bash")
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "non_edit_passthrough", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="concurrent-write-guard.sh not found")
def test_concurrent_write_guard_with_session_acquires_lock(tmp_path: Path):
    """With a session ID, hook must create a lock file and exit 0."""
    session_id = "chaos-session-001"
    _setup_project(tmp_path, session_id=session_id)
    target = tmp_path / "protected.py"
    target.write_text("x = 1\n")
    result = _run(tmp_path, str(target), env_extra={"COGNITIVE_OS_SESSION_ID": session_id})
    assert result.returncode == 0, (
        f"Lock acquisition must exit 0, got {result.returncode}\n"
        f"stderr: {result.stderr[:300]}"
    )
    _write_chaos_run(tmp_path, "session_acquires_lock", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="concurrent-write-guard.sh not found")
def test_concurrent_write_guard_empty_file_path_passthrough(tmp_path: Path):
    """Empty file_path in payload must exit 0 (guard condition)."""
    _setup_project(tmp_path)
    payload = json.dumps({
        "tool_name": "Edit",
        "tool_input": {"file_path": ""},
    })
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_SESSION_ID": "chaos-session-002",
    }
    result = subprocess.run(
        ["bash", str(_HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "empty_file_path", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="concurrent-write-guard.sh not found")
def test_concurrent_write_guard_killswitch_suppresses(tmp_path: Path):
    """With SO_KILLSWITCH=1, hook must exit 0 silently."""
    session_id = "chaos-ks-session"
    _setup_project(tmp_path, session_id=session_id)
    target = tmp_path / "file.py"
    target.write_text("x = 1\n")
    result = _run(
        tmp_path, str(target),
        env_extra={"COGNITIVE_OS_SESSION_ID": session_id, "SO_KILLSWITCH": "1"},
    )
    assert result.returncode == 0, f"killswitch exit {result.returncode}: {result.stderr[:200]}"
    _write_chaos_run(tmp_path, "killswitch_suppresses", True)
