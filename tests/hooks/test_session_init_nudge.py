"""Behavioral tests for the pending-task nudge in hooks/session-init.sh.

Tests cover:
1. With pending items in work-queue.json → "Pending tasks detected" + skill refs in stderr
2. With 0 pending items → no nudge in stderr
3. Missing work-queue.json → no error, no nudge, returncode 0
4. Malformed JSON → fail-silent, no nudge, returncode 0

All tests use tmp_path isolation. The real .cognitive-os/work-queue.json is never touched.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SESSION_INIT = PROJECT_ROOT / "hooks" / "session-init.sh"

pytestmark = [pytest.mark.behavior]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_session_init(project_dir: Path, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run session-init.sh against the given project dir."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    # Suppress any network/external calls that might be made
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    env["CI"] = "true"
    return subprocess.run(
        ["bash", str(SESSION_INIT)],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _write_work_queue(project_dir: Path, pending_count: int, parked_count: int = 0) -> Path:
    """Write a work-queue.json with the given number of pending tasks."""
    cos_dir = project_dir / ".cognitive-os"
    cos_dir.mkdir(parents=True, exist_ok=True)
    wq_path = cos_dir / "work-queue.json"

    pending_items = [
        {"id": f"task-{i}", "priority": "P1", "status": "pending", "title": f"Task {i}"}
        for i in range(pending_count)
    ]
    parked_items = [
        {"id": f"parked-{i}", "status": "parked", "title": f"Parked {i}"}
        for i in range(parked_count)
    ]

    wq_path.write_text(json.dumps({
        "priority_queue": pending_items,
        "parked": parked_items,
    }))
    return wq_path


def _make_minimal_cos_structure(project_dir: Path) -> None:
    """Create the minimum directory/file structure that session-init.sh expects."""
    cos_dir = project_dir / ".cognitive-os"
    for subdir in ["metrics", "sessions", "runtime"]:
        (cos_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Create a minimal cognitive-os.yaml so config reads don't fail
    (cos_dir / "cognitive-os.yaml").write_text(
        "project:\n  name: test\n  phase: reconstruction\n"
    )
    (project_dir / "cognitive-os.yaml").write_text(
        "project:\n  name: test\n  phase: reconstruction\n"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPendingTaskNudge:
    """session-init.sh emits nudge when pending tasks exist."""

    def test_pending_tasks_detected_message_in_stderr(self, tmp_path):
        """With ≥1 pending item, stderr must contain 'Pending tasks detected'."""
        _make_minimal_cos_structure(tmp_path)
        _write_work_queue(tmp_path, pending_count=1)
        result = _run_session_init(tmp_path)
        assert "Pending tasks detected" in result.stderr, (
            f"Expected 'Pending tasks detected' in stderr. stderr={result.stderr!r}"
        )

    def test_nudge_contains_session_backlog_skill_ref(self, tmp_path):
        """Nudge must reference /session-backlog."""
        _make_minimal_cos_structure(tmp_path)
        _write_work_queue(tmp_path, pending_count=2)
        result = _run_session_init(tmp_path)
        assert "/session-backlog" in result.stderr, (
            f"Expected '/session-backlog' in stderr. stderr={result.stderr!r}"
        )

    def test_nudge_contains_resume_tasks_skill_ref(self, tmp_path):
        """Nudge must reference /resume-tasks."""
        _make_minimal_cos_structure(tmp_path)
        _write_work_queue(tmp_path, pending_count=2)
        result = _run_session_init(tmp_path)
        assert "/resume-tasks" in result.stderr, (
            f"Expected '/resume-tasks' in stderr. stderr={result.stderr!r}"
        )

    def test_nudge_contains_session_report_skill_ref(self, tmp_path):
        """Nudge must reference /session-report-executive."""
        _make_minimal_cos_structure(tmp_path)
        _write_work_queue(tmp_path, pending_count=2)
        result = _run_session_init(tmp_path)
        assert "/session-report-executive" in result.stderr, (
            f"Expected '/session-report-executive' in stderr. stderr={result.stderr!r}"
        )


class TestNoPendingTasksNudge:
    """session-init.sh must NOT emit nudge when no pending tasks."""

    def test_zero_pending_no_nudge(self, tmp_path):
        """With 0 pending items, 'Pending tasks detected' must NOT appear in stderr."""
        _make_minimal_cos_structure(tmp_path)
        _write_work_queue(tmp_path, pending_count=0)
        result = _run_session_init(tmp_path)
        assert "Pending tasks detected" not in result.stderr, (
            f"Unexpected nudge with 0 pending tasks. stderr={result.stderr!r}"
        )

    def test_zero_pending_exits_zero(self, tmp_path):
        _make_minimal_cos_structure(tmp_path)
        _write_work_queue(tmp_path, pending_count=0)
        result = _run_session_init(tmp_path)
        assert result.returncode == 0, result.stderr


class TestMissingWorkQueue:
    """session-init.sh is fail-silent when work-queue.json is absent."""

    def test_missing_work_queue_exits_zero(self, tmp_path):
        _make_minimal_cos_structure(tmp_path)
        # Do NOT create work-queue.json
        result = _run_session_init(tmp_path)
        assert result.returncode == 0, result.stderr

    def test_missing_work_queue_no_nudge(self, tmp_path):
        _make_minimal_cos_structure(tmp_path)
        result = _run_session_init(tmp_path)
        assert "Pending tasks detected" not in result.stderr, (
            f"Unexpected nudge without work-queue.json. stderr={result.stderr!r}"
        )

    def test_missing_work_queue_no_error_output(self, tmp_path):
        """No 'error' or exception text from the missing-file code path."""
        _make_minimal_cos_structure(tmp_path)
        result = _run_session_init(tmp_path)
        # Script must not produce parse errors about work-queue
        lower = result.stderr.lower()
        assert "parse error" not in lower and "jq: error" not in lower, (
            f"Unexpected error in stderr. stderr={result.stderr!r}"
        )


class TestMalformedWorkQueue:
    """session-init.sh is fail-silent when work-queue.json contains invalid JSON."""

    def test_malformed_json_exits_zero(self, tmp_path):
        _make_minimal_cos_structure(tmp_path)
        wq = tmp_path / ".cognitive-os" / "work-queue.json"
        wq.write_text("{this is not valid json}")
        result = _run_session_init(tmp_path)
        assert result.returncode == 0, result.stderr

    def test_malformed_json_no_nudge(self, tmp_path):
        _make_minimal_cos_structure(tmp_path)
        wq = tmp_path / ".cognitive-os" / "work-queue.json"
        wq.write_text("{this is not valid json}")
        result = _run_session_init(tmp_path)
        assert "Pending tasks detected" not in result.stderr, (
            f"Nudge emitted despite malformed JSON. stderr={result.stderr!r}"
        )
