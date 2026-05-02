from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.session_lifecycle import inspect_pending, reap_decision, reap_sessions

pytestmark = pytest.mark.behavior


def make_session(project: Path, sid: str, *, age_seconds: int = 7200, pid: int | None = None) -> Path:
    session = project / ".cognitive-os" / "sessions" / sid
    session.mkdir(parents=True)
    now = int(time.time())
    (session / "meta.json").write_text(json.dumps({"session_id": sid, "pid": pid, "start_epoch": now - age_seconds}))
    return session


def test_pending_request_keeps_session(tmp_path: Path) -> None:
    session = make_session(tmp_path, "sess-pending")
    (session / "user-requests.jsonl").write_text(json.dumps({"status": "pending", "text": "do work"}) + "\n")

    inspection = inspect_pending(session)
    decision = reap_decision(session, grace_seconds=0)

    assert inspection.has_pending is True
    assert decision.decision == "KEEP_PENDING_CONTENT"


def test_unresolved_task_keeps_session(tmp_path: Path) -> None:
    session = make_session(tmp_path, "sess-task")
    (session / "tasks.json").write_text(json.dumps({"tasks": [{"status": "in_progress", "description": "work"}]}))

    decision = reap_decision(session, grace_seconds=0)

    assert decision.decision == "KEEP_PENDING_CONTENT"
    assert any("tasks.json" in reason for reason in decision.pending_reasons)


def test_pid_alive_keeps_any_age(tmp_path: Path) -> None:
    session = make_session(tmp_path, "sess-live", age_seconds=999999, pid=12345)

    with patch("lib.session_lifecycle.pid_alive", return_value=True):
        decision = reap_decision(session, grace_seconds=0)

    assert decision.decision == "KEEP_ACTIVE"


def test_dead_clean_old_session_archives(tmp_path: Path) -> None:
    session = make_session(tmp_path, "sess-old-clean", age_seconds=7200, pid=999999999)

    result = reap_sessions(tmp_path, grace_seconds=1)

    assert result.archived
    assert not session.exists()
    archived_path = Path(result.archived[0])
    assert archived_path.exists()
    assert (archived_path / "archived.json").exists()


def test_archive_older_than_retention_is_removed(tmp_path: Path) -> None:
    archived = tmp_path / ".cognitive-os" / "archive" / "sessions" / "sess-archived-old"
    archived.mkdir(parents=True)
    old = time.time() - (91 * 24 * 3600)
    (archived / "meta.json").write_text(json.dumps({"session_id": "sess-archived-old"}))
    # Force directory mtime older than retention.
    import os
    os.utime(archived, (old, old))

    result = reap_sessions(tmp_path, archive_retention_days=90)

    assert any(decision.decision == "RM_ARCHIVED" for decision in result.decisions)
    assert not archived.exists()
