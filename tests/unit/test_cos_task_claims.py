from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.cos_task_claims import claim_task, claims_path, task_fingerprint


def write_active_session(project: Path, session_id: str, pid: int) -> None:
    sessions = project / ".cognitive-os" / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "active-sessions.json").write_text(json.dumps({"sessions": [{"id": session_id, "pid": pid, "start_time": "2026-05-02T00:00:00Z"}]}))


def test_task_claim_blocks_same_work_from_live_other_session(tmp_path: Path) -> None:
    write_active_session(tmp_path, "s1", os.getpid())
    task = {"id": "T1", "title": "Implement ledger", "deliverable": "scripts/cos_task_claims.py"}

    ok, first = claim_task(tmp_path, task, session="s1")
    assert ok is True
    assert first["fingerprint"] == task_fingerprint(task)

    ok, second = claim_task(tmp_path, {**task, "id": "T2"}, session="s2")
    assert ok is False
    assert second["status"] == "conflict"
    assert second["held_by"] == "s1"


def test_task_claim_prunes_dead_session_and_allows_takeover(tmp_path: Path) -> None:
    write_active_session(tmp_path, "dead", 99999999)
    task = {"id": "T1", "description": "same", "deliverable": "docs/out.md"}

    ok, _ = claim_task(tmp_path, task, session="dead")
    assert ok is True
    ok, takeover = claim_task(tmp_path, {**task, "id": "T2"}, session="live")
    assert ok is True
    assert takeover["session_id"] == "live"

    data = json.loads(claims_path(tmp_path).read_text())
    statuses = {claim["session_id"]: claim["status"] for claim in data["claims"]}
    assert statuses["dead"] == "stale"
    assert statuses["live"] == "active"


def test_unknown_session_claim_survives_without_registry(tmp_path: Path) -> None:
    task = {"id": "T1", "description": "human terminal work", "deliverable": "docs/out.md"}

    ok, _ = claim_task(tmp_path, task, session="human-terminal")
    assert ok is True
    ok, second = claim_task(tmp_path, {**task, "id": "T2"}, session="other-terminal")

    assert ok is False
    assert second["held_by"] == "human-terminal"
    data = json.loads(claims_path(tmp_path).read_text())
    assert data["claims"][0]["status"] == "active"


def test_unknown_session_claim_expires_after_ttl(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("COS_TASK_CLAIM_TTL_SECONDS", "60")
    stale = {
        "task_id": "T1",
        "session_id": "unknown-session",
        "claimed_at": "2026-05-02T00:00:00Z",
        "expected_files": ["docs/out.md"],
        "fingerprint": task_fingerprint({"id": "T1", "description": "same", "deliverable": "docs/out.md"}),
        "status": "active",
    }
    path = claims_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"claims": [stale]}))

    ok, takeover = claim_task(tmp_path, {"id": "T2", "description": "same", "deliverable": "docs/out.md"}, session="new-session")

    assert ok is True
    assert takeover["session_id"] == "new-session"
    data = json.loads(path.read_text())
    statuses = {claim["session_id"]: claim["status"] for claim in data["claims"]}
    assert statuses["unknown-session"] == "stale"
    assert statuses["new-session"] == "active"
