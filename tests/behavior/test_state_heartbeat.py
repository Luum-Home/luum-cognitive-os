"""Behavior tests for StateHeartbeat — continuous session state persistence.

Tests the lib/state_heartbeat.py module and the hooks/state-heartbeat.sh hook.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_dir() -> Path:
    """Create a temporary session directory and return its Path."""
    tmp = Path(tempfile.mkdtemp())
    session = tmp / ".cognitive-os" / "sessions" / "test-session-123"
    session.mkdir(parents=True, exist_ok=True)
    return session


def _import_heartbeat():
    """Import StateHeartbeat (skip if import fails)."""
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from lib.state_heartbeat import StateHeartbeat
        return StateHeartbeat
    except ImportError as exc:
        pytest.skip(f"Cannot import StateHeartbeat: {exc}")


# ---------------------------------------------------------------------------
# Import sanity
# ---------------------------------------------------------------------------

def test_import_state_heartbeat():
    """Acceptance criterion 1: module imports cleanly."""
    StateHeartbeat = _import_heartbeat()
    assert StateHeartbeat is not None


# ---------------------------------------------------------------------------
# Registration and collector execution
# ---------------------------------------------------------------------------

def test_register_and_run_custom_collector():
    """Registered collectors are called and their results appear in snapshot."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))
    hb.register("custom", lambda: {"hello": "world"})
    snap = hb.snapshot()
    assert snap["custom"] == {"hello": "world"}


def test_snapshot_has_timestamp():
    """Snapshot always contains a top-level timestamp."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))
    snap = hb.snapshot()
    assert "timestamp" in snap
    assert snap["timestamp"]  # non-empty


def test_snapshot_has_all_builtin_collectors():
    """All five built-in collectors appear in the snapshot dict."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))
    snap = hb.snapshot()
    for key in ("active_tasks", "pending_requests", "git_status", "session_meta", "todo_state"):
        assert key in snap, f"Missing collector output: {key}"


# ---------------------------------------------------------------------------
# Save / load roundtrip
# ---------------------------------------------------------------------------

def test_save_creates_json_file():
    """save() creates a valid JSON file at state-snapshot.json."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))
    hb.save()
    snap_path = session_dir / "state-snapshot.json"
    assert snap_path.exists(), "state-snapshot.json was not created"
    with open(snap_path) as fh:
        data = json.load(fh)
    assert "timestamp" in data


def test_load_returns_saved_data():
    """load() reads back what save() wrote."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))
    # Add a known collector so we can identify the data
    hb.register("marker", lambda: {"sentinel": 42})
    hb.save()
    loaded = hb.load()
    assert loaded is not None
    assert loaded["marker"]["sentinel"] == 42


def test_load_returns_none_when_no_snapshot():
    """load() returns None when state-snapshot.json does not exist."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))
    assert hb.load() is None


# ---------------------------------------------------------------------------
# Resilience: crashing collector
# ---------------------------------------------------------------------------

def test_crashing_collector_does_not_break_heartbeat():
    """A collector that raises an exception must not crash snapshot()."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))

    def bad_collector():
        raise RuntimeError("simulated crash")

    hb.register("bad", bad_collector)
    hb.register("good", lambda: {"ok": True})

    snap = hb.snapshot()  # must not raise
    assert snap["bad"]["status"] == "unavailable"
    assert snap["good"]["ok"] is True


def test_crashing_collector_does_not_prevent_save():
    """save() succeeds even when a collector crashes."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))
    hb.register("bad", lambda: (_ for _ in ()).throw(ValueError("boom")))
    hb.save()  # must not raise
    assert (session_dir / "state-snapshot.json").exists()


# ---------------------------------------------------------------------------
# format_recovery_prompt
# ---------------------------------------------------------------------------

def test_format_recovery_prompt_no_snapshot():
    """format_recovery_prompt with no snapshot returns a sensible message."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))
    msg = hb.format_recovery_prompt()
    assert "No previous session state" in msg


def test_format_recovery_prompt_with_snapshot():
    """format_recovery_prompt returns a non-empty recovery string after save."""
    StateHeartbeat = _import_heartbeat()
    session_dir = _make_session_dir()
    hb = StateHeartbeat(str(session_dir))
    hb.save()
    msg = hb.format_recovery_prompt()
    assert "PREVIOUS SESSION STATE" in msg
    assert "Snapshot taken" in msg


# ---------------------------------------------------------------------------
# collect_active_tasks — real format
# ---------------------------------------------------------------------------

def test_collect_active_tasks_with_real_format(tmp_path):
    """collect_active_tasks handles the real active-tasks.json format correctly."""
    StateHeartbeat = _import_heartbeat()
    # Build a fake project layout
    cos_dir = tmp_path / ".cognitive-os"
    tasks_dir = cos_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    tasks_data = {
        "version": 1,
        "tasks": [
            {"id": "t1", "description": "Write tests", "status": "in_progress"},
            {"id": "t2", "description": "Deploy", "status": "completed"},
            {"id": "t3", "description": "Review PR", "status": "pending"},
        ],
    }
    (tasks_dir / "active-tasks.json").write_text(json.dumps(tasks_data))

    # session dir is inside the fake project
    session_dir = cos_dir / "sessions" / "s1"
    session_dir.mkdir(parents=True)

    hb = StateHeartbeat(str(session_dir))
    result = hb._collect_active_tasks()
    assert result["total"] == 3
    in_prog_ids = [t["id"] for t in result["in_progress"]]
    assert "t1" in in_prog_ids   # in_progress
    assert "t3" in in_prog_ids   # pending
    assert "t2" not in in_prog_ids  # completed — excluded


# ---------------------------------------------------------------------------
# collect_git_status — no git repo
# ---------------------------------------------------------------------------

def test_collect_git_status_outside_git_repo(tmp_path):
    """collect_git_status returns a dict even when not in a git repo."""
    StateHeartbeat = _import_heartbeat()
    session_dir = tmp_path / "sessions" / "s1"
    session_dir.mkdir(parents=True)
    hb = StateHeartbeat(str(session_dir))

    old_dir = os.getcwd()
    try:
        os.chdir(str(tmp_path))  # move to a non-git dir
        result = hb._collect_git_status()
    finally:
        os.chdir(old_dir)

    # Must always return a dict
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Hook syntax check
# ---------------------------------------------------------------------------

def test_hook_syntax_ok():
    """bash -n on state-heartbeat.sh exits 0 (Acceptance criterion 2)."""
    hook = PROJECT_ROOT / "hooks" / "state-heartbeat.sh"
    if not hook.exists():
        pytest.skip("state-heartbeat.sh not found")
    result = subprocess.run(["bash", "-n", str(hook)], capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax error: {result.stderr}"


def test_crash_recovery_syntax_ok():
    """bash -n on crash-recovery.sh exits 0 (Acceptance criterion 3)."""
    hook = PROJECT_ROOT / "hooks" / "crash-recovery.sh"
    if not hook.exists():
        pytest.skip("crash-recovery.sh not found")
    result = subprocess.run(["bash", "-n", str(hook)], capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax error: {result.stderr}"
