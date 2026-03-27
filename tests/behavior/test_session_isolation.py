"""Behavior tests for session isolation.

Simulates two sessions and verifies they get separate task files
and metrics directories.
Migrated from test-session-isolation.sh.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def session_init_hook(project_root):
    hook = project_root / ".cognitive-os" / "hooks" / "session-init.sh"
    if not hook.exists() or not os.access(hook, os.X_OK):
        pytest.skip("session-init.sh not found or not executable")
    return hook


@pytest.fixture
def sessions_dir(project_root):
    return project_root / ".cognitive-os" / "sessions"


def _init_session(session_init_hook, project_root):
    """Run session-init.sh and return (exit_code, session_id, stdout)."""
    result = subprocess.run(
        ["bash", str(session_init_hook)],
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(project_root)},
        timeout=10,
    )
    # Extract session ID from output
    sid = None
    for line in result.stdout.splitlines():
        if "Session ID:" in line:
            sid = line.split("Session ID:")[-1].strip()
            break
    return result.returncode, sid, result.stdout


@pytest.mark.behavior
class TestSessionIsolation:
    """Tests for session isolation -- separate directories, unique IDs, task independence."""

    def test_session_init_creates_directory(self, session_init_hook, sessions_dir, project_root):
        rc, sid, _ = _init_session(session_init_hook, project_root)
        try:
            assert rc == 0, f"session-init.sh should exit 0, got {rc}"
            assert sid is not None, "should output a session ID"
            assert (sessions_dir / sid).is_dir(), "session directory should exist"
        finally:
            if sid:
                shutil.rmtree(sessions_dir / sid, ignore_errors=True)
                self._remove_from_active(sessions_dir, sid)

    def test_session_creates_tasks_json(self, session_init_hook, sessions_dir, project_root):
        _, sid, _ = _init_session(session_init_hook, project_root)
        try:
            assert sid is not None
            assert (sessions_dir / sid / "tasks.json").exists(), "tasks.json should be created"
        finally:
            if sid:
                shutil.rmtree(sessions_dir / sid, ignore_errors=True)
                self._remove_from_active(sessions_dir, sid)

    def test_session_creates_metrics_dir(self, session_init_hook, sessions_dir, project_root):
        _, sid, _ = _init_session(session_init_hook, project_root)
        try:
            assert sid is not None
            assert (sessions_dir / sid / "metrics").is_dir(), "metrics/ should be created"
        finally:
            if sid:
                shutil.rmtree(sessions_dir / sid, ignore_errors=True)
                self._remove_from_active(sessions_dir, sid)

    def test_session_creates_valid_meta_json(self, session_init_hook, sessions_dir, project_root):
        _, sid, _ = _init_session(session_init_hook, project_root)
        try:
            assert sid is not None
            meta = sessions_dir / sid / "meta.json"
            if meta.exists():
                json.loads(meta.read_text())  # Should not raise
        finally:
            if sid:
                shutil.rmtree(sessions_dir / sid, ignore_errors=True)
                self._remove_from_active(sessions_dir, sid)

    def test_two_sessions_have_unique_ids(self, session_init_hook, sessions_dir, project_root):
        _, sid1, _ = _init_session(session_init_hook, project_root)
        _, sid2, _ = _init_session(session_init_hook, project_root)
        try:
            assert sid1 is not None and sid2 is not None
            assert sid1 != sid2, f"session IDs should be unique: {sid1} vs {sid2}"
        finally:
            for s in [sid1, sid2]:
                if s:
                    shutil.rmtree(sessions_dir / s, ignore_errors=True)
                    self._remove_from_active(sessions_dir, s)

    def test_task_files_are_independent(self, session_init_hook, sessions_dir, project_root):
        _, sid1, _ = _init_session(session_init_hook, project_root)
        _, sid2, _ = _init_session(session_init_hook, project_root)
        try:
            assert sid1 and sid2
            t1 = sessions_dir / sid1 / "tasks.json"
            t2 = sessions_dir / sid2 / "tasks.json"
            t1.write_text('[{"task":"from-session-1"}]')
            t2.write_text('[{"task":"from-session-2"}]')

            data1 = json.loads(t1.read_text())
            data2 = json.loads(t2.read_text())
            assert data1[0]["task"] == "from-session-1"
            assert data2[0]["task"] == "from-session-2"
        finally:
            for s in [sid1, sid2]:
                if s:
                    shutil.rmtree(sessions_dir / s, ignore_errors=True)
                    self._remove_from_active(sessions_dir, s)

    def test_metrics_dirs_are_independent(self, session_init_hook, sessions_dir, project_root):
        _, sid1, _ = _init_session(session_init_hook, project_root)
        _, sid2, _ = _init_session(session_init_hook, project_root)
        try:
            assert sid1 and sid2
            m1 = sessions_dir / sid1 / "metrics" / "test.jsonl"
            m2 = sessions_dir / sid2 / "metrics" / "test.jsonl"
            m1.write_text('{"test":"session1"}\n')
            m2.write_text('{"test":"session2"}\n')

            assert json.loads(m1.read_text().strip())["test"] == "session1"
            assert json.loads(m2.read_text().strip())["test"] == "session2"
        finally:
            for s in [sid1, sid2]:
                if s:
                    shutil.rmtree(sessions_dir / s, ignore_errors=True)
                    self._remove_from_active(sessions_dir, s)

    def test_active_sessions_registry(self, session_init_hook, sessions_dir, project_root):
        _, sid1, _ = _init_session(session_init_hook, project_root)
        _, sid2, _ = _init_session(session_init_hook, project_root)
        try:
            active = sessions_dir / "active-sessions.json"
            if not active.exists():
                pytest.skip("active-sessions.json not found")
            data = json.loads(active.read_text())
            ids = [s["id"] for s in data.get("sessions", [])]
            assert sid1 in ids and sid2 in ids, (
                f"both sessions should be in the registry, got {ids}"
            )
        finally:
            for s in [sid1, sid2]:
                if s:
                    shutil.rmtree(sessions_dir / s, ignore_errors=True)
                    self._remove_from_active(sessions_dir, s)

    @staticmethod
    def _remove_from_active(sessions_dir: Path, sid: str):
        active = sessions_dir / "active-sessions.json"
        if not active.exists():
            return
        try:
            data = json.loads(active.read_text())
            data["sessions"] = [s for s in data.get("sessions", []) if s.get("id") != sid]
            active.write_text(json.dumps(data))
        except Exception:
            pass
