from __future__ import annotations

import json
import multiprocessing
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from lib.session_bus import (  # noqa: E402
    EVENT_STORE_SCHEMA_VERSION,
    EventStreamGapDetected,
    UnsupportedEventBusPlatform,
    append_event,
    append_session_event,
    read_session_events,
    recover_session_counter,
    session_counter_path,
    session_stream_path,
)


def test_append_session_event_allocates_monotonic_seq(tmp_path: Path) -> None:
    first = append_session_event("session-start", {"n": 1}, project_dir=tmp_path, session_id="s1")
    second = append_session_event("file_write_intent", {"path": "a.py"}, project_dir=tmp_path, session_id="s1")

    assert first["schema_version"] == EVENT_STORE_SCHEMA_VERSION
    assert first["seq"] == 1
    assert second["seq"] == 2
    assert second["event_type"] == "file-write-intent"
    assert session_counter_path(tmp_path, "s1").read_text(encoding="utf-8").strip() == "2"


def test_append_event_can_opt_into_event_store_without_breaking_v1_default(tmp_path: Path) -> None:
    v1 = append_event("session-start", {}, project_dir=tmp_path, session_id="s1")
    v2 = append_event("session-start", {}, project_dir=tmp_path, session_id="s1", event_store=True)

    assert v1["schema_version"] == 1
    assert v2["schema_version"] == EVENT_STORE_SCHEMA_VERSION
    assert (tmp_path / ".cognitive-os" / "sessions" / "events.jsonl").is_file()
    assert session_stream_path(tmp_path, "s1").is_file()


def test_read_session_events_detects_seq_gap(tmp_path: Path) -> None:
    path = session_stream_path(tmp_path, "s1")
    path.parent.mkdir(parents=True)
    rows = [
        {"schema_version": EVENT_STORE_SCHEMA_VERSION, "seq": 1, "session_id": "s1", "event_type": "session-start", "ts": "2026-05-06T00:00:00Z", "producer": "test"},
        {"schema_version": EVENT_STORE_SCHEMA_VERSION, "seq": 3, "session_id": "s1", "event_type": "session-end", "ts": "2026-05-06T00:00:01Z", "producer": "test"},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    with pytest.raises(EventStreamGapDetected):
        read_session_events("s1", project_dir=tmp_path)


def test_recover_session_counter_rebuilds_from_stream(tmp_path: Path) -> None:
    for n in range(3):
        append_session_event("coordination-claim", {"n": n}, project_dir=tmp_path, session_id="s1")
    session_counter_path(tmp_path, "s1").unlink()

    assert recover_session_counter("s1", project_dir=tmp_path) == 3
    assert session_counter_path(tmp_path, "s1").read_text(encoding="utf-8").strip() == "3"


def test_unsafe_session_id_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsafe session_id"):
        append_session_event("session-start", {}, project_dir=tmp_path, session_id="../escape")


def test_unsupported_filesystem_refusal_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COS_EVENT_BUS_FORCE_UNSUPPORTED_FS", "1")
    with pytest.raises(UnsupportedEventBusPlatform):
        append_session_event("session-start", {}, project_dir=tmp_path, session_id="s1")

    event = append_session_event("session-start", {}, project_dir=tmp_path, session_id="s1", single_writer=True)
    assert event["seq"] == 1


def _append_worker(project_dir: str, session_id: str, count: int) -> None:
    from lib.session_bus import append_session_event as _append_session_event

    for i in range(count):
        _append_session_event("agent-message-sent", {"i": i}, project_dir=project_dir, session_id=session_id)


def test_concurrent_writers_allocate_gap_free_sequence(tmp_path: Path) -> None:
    count = 20
    procs = [multiprocessing.Process(target=_append_worker, args=(str(tmp_path), "s1", count)) for _ in range(2)]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join(timeout=20)
        assert proc.exitcode == 0

    events = read_session_events("s1", project_dir=tmp_path)
    assert len(events) == count * 2
    assert [event["seq"] for event in events] == list(range(1, count * 2 + 1))

from lib.session_bus import assert_index_consistent, read_event_index  # noqa: E402


def test_append_session_event_fans_out_minimal_index(tmp_path: Path) -> None:
    first = append_session_event("session-start", {}, project_dir=tmp_path, session_id="s1")
    second = append_session_event("session-end", {}, project_dir=tmp_path, session_id="s1")

    index = read_event_index(project_dir=tmp_path)
    assert [row["seq"] for row in index] == [first["seq"], second["seq"]]
    assert [row["session_id"] for row in index] == ["s1", "s1"]
    assert set(index[0]) == {"schema_version", "seq", "session_id", "event_type", "ts"}
    assert_index_consistent(tmp_path, "s1")


def test_assert_index_consistent_detects_missing_index_record(tmp_path: Path) -> None:
    append_session_event("session-start", {}, project_dir=tmp_path, session_id="s1", fan_out_index=False)

    with pytest.raises(EventStreamGapDetected, match="missing event-index record"):
        assert_index_consistent(tmp_path, "s1")
