from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from lib import engram_claims, engram_locks

pytestmark = pytest.mark.unit


class FakeEngram:
    def __init__(self) -> None:
        self.records: dict[str, dict] = {}

    def save(self, title: str, content: str, *, type_: str = "architecture", topic_key: str = "", project: str = "") -> dict:
        self.records[topic_key] = {
            "title": title,
            "content": content,
            "type": type_,
            "topic_key": topic_key,
            "project": project,
        }
        return self.records[topic_key]

    def search(self, query: str, *, limit: int = 5, project: str = "") -> list[dict]:
        record = self.records.get(query)
        return [record] if record else []


@pytest.fixture
def fake_engram(monkeypatch: pytest.MonkeyPatch) -> FakeEngram:
    fake = FakeEngram()
    monkeypatch.setattr(engram_claims, "_save_fn", fake.save)
    monkeypatch.setattr(engram_claims, "_search_fn", fake.search)
    monkeypatch.setattr(engram_locks, "_save_fn", fake.save)
    monkeypatch.setattr(engram_locks, "_search_fn", fake.search)
    return fake


def test_claim_task_blocks_different_live_session(fake_engram: FakeEngram) -> None:
    first = engram_claims.claim_task("TASK-1", "session-a", expected_files=["a.py"])
    second = engram_claims.claim_task("TASK-1", "session-b")

    assert first["session_id"] == "session-a"
    assert second["session_id"] == "session-a"
    assert engram_claims.find_claim("TASK-1")["expected_files"] == ["a.py"]


def test_complete_task_updates_same_claim_topic(fake_engram: FakeEngram) -> None:
    engram_claims.claim_task("TASK-2", "session-a")
    completed = engram_claims.complete_task("TASK-2", "session-a", {"commit": "abc"})

    assert completed["status"] == "completed"
    assert completed["completion_evidence"] == {"commit": "abc"}
    assert engram_claims.find_claim("TASK-2")["status"] == "completed"


def test_lock_blocks_other_session_until_stale(fake_engram: FakeEngram) -> None:
    first = engram_locks.acquire_lock("resource-x", "session-a", ttl_seconds=60)
    second = engram_locks.acquire_lock("resource-x", "session-b", ttl_seconds=60)

    assert first and first["session_id"] == "session-a"
    assert second is None

    stale = {
        **first,
        "heartbeat_at": (datetime.now(timezone.utc) - timedelta(seconds=200)).isoformat(),
    }
    fake_engram.records["lock/resource-x"]["content"] = json.dumps(stale)

    third = engram_locks.acquire_lock("resource-x", "session-b", ttl_seconds=60)
    assert third and third["session_id"] == "session-b"


def test_release_and_heartbeat_require_owner(fake_engram: FakeEngram) -> None:
    engram_locks.acquire_lock("resource-y", "session-a", ttl_seconds=60)

    assert engram_locks.heartbeat_lock("resource-y", "session-b") is False
    assert engram_locks.release_lock("resource-y", "session-b") is False
    assert engram_locks.heartbeat_lock("resource-y", "session-a") is True
    assert engram_locks.release_lock("resource-y", "session-a") is True
    assert engram_locks.find_lock("resource-y") is None
