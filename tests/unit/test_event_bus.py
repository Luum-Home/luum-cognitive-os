"""
Unit tests for lib/event_bus.py — P1.3 inter-session pub/sub event bus.

Run with:
    python3 -m pytest tests/unit/test_event_bus.py -v

Covers:
1. emit + tail roundtrip
2. emit concurrent from 2 processes — no line interleaving
3. tail with --since filter
4. tail --follow generator yields new events
5. schema validation rejects unknown event_type
6. rotation triggered at configured threshold
7. corrupt line tolerated (skipped)
8. stats counts last hour correctly
"""

from __future__ import annotations

import json
import multiprocessing
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure project root is importable regardless of how pytest is invoked.
_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from lib.event_bus import (  # noqa: E402
    emit,
    tail,
    stats,
    EVENT_TYPES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_events(bus_path: Path) -> list[dict]:
    return list(tail(bus_path=bus_path))


def _make_bus(tmp_path: Path) -> Path:
    return tmp_path / "events.jsonl"


# ---------------------------------------------------------------------------
# Test 1: emit + tail roundtrip
# ---------------------------------------------------------------------------

def test_emit_tail_roundtrip(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)
    emit("task_completed", {"task_id": "t1"}, session_id="s1", bus_path=bus)
    emit("session_started", {"info": "boot"}, session_id="s2", bus_path=bus)

    events = _all_events(bus)
    assert len(events) == 2

    first = events[0]
    assert first["event_type"] == "task_completed"
    assert first["session_id"] == "s1"
    assert first["payload"] == {"task_id": "t1"}
    assert "ts" in first

    second = events[1]
    assert second["event_type"] == "session_started"
    assert second["session_id"] == "s2"


# ---------------------------------------------------------------------------
# Test 2: concurrent emit from 2 processes — no line interleaving
# ---------------------------------------------------------------------------

def _worker_emit(bus_path_str: str, event_type: str, n: int, session_id: str) -> None:
    """Subprocess worker: emit n events."""
    from lib.event_bus import emit as _emit  # noqa: PLC0415
    for i in range(n):
        _emit(event_type, {"idx": i}, session_id=session_id, bus_path=bus_path_str)


def test_concurrent_emit_no_interleaving(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)
    n = 50

    # Use multiprocessing to guarantee separate OS processes.
    p1 = multiprocessing.Process(
        target=_worker_emit,
        args=(str(bus), "claim_acquired", n, "proc-1"),
    )
    p2 = multiprocessing.Process(
        target=_worker_emit,
        args=(str(bus), "claim_released", n, "proc-2"),
    )
    p1.start()
    p2.start()
    p1.join(timeout=15)
    p2.join(timeout=15)

    assert p1.exitcode == 0, f"proc-1 exited with {p1.exitcode}"
    assert p2.exitcode == 0, f"proc-2 exited with {p2.exitcode}"

    # Every line must be a valid JSON object.
    raw_lines = [l for l in bus.read_text("utf-8").splitlines() if l.strip()]
    assert len(raw_lines) == n * 2, f"Expected {n * 2} lines, got {len(raw_lines)}"

    for i, line in enumerate(raw_lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            pytest.fail(f"Line {i} is corrupt (interleaved?): {line!r}\n{exc}")
        assert "event_type" in obj
        assert "ts" in obj


# ---------------------------------------------------------------------------
# Test 3: tail with --since filter
# ---------------------------------------------------------------------------

def test_tail_since_filter(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)

    # Emit an "old" event by backdating the ts directly.
    old_ts = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
    old_record = json.dumps(
        {"ts": old_ts, "session_id": "s", "event_type": "task_completed", "payload": {"old": True}}
    )
    bus.write_text(old_record + "\n", encoding="utf-8")

    # Emit a new event via the normal API (current time).
    emit("session_started", {"new": True}, session_id="s", bus_path=bus)

    cutoff = datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()
    filtered = list(tail(since_ts=cutoff, bus_path=bus))

    assert len(filtered) == 1
    assert filtered[0]["payload"]["new"] is True


# ---------------------------------------------------------------------------
# Test 4: tail --follow yields new events
# ---------------------------------------------------------------------------

def test_tail_follow_yields_new_events(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)

    # Prime with one event.
    emit("task_completed", {"init": True}, session_id="s", bus_path=bus)

    collected: list[dict] = []
    stop_event = threading.Event()

    def _follower() -> None:
        for ev in tail(follow=True, bus_path=bus, poll_interval=0.02):
            collected.append(ev)
            if stop_event.is_set() and len(collected) >= 3:
                break

    t = threading.Thread(target=_follower, daemon=True)
    t.start()

    # Wait for the initial event to be consumed.
    deadline = time.time() + 5
    while len(collected) < 1 and time.time() < deadline:
        time.sleep(0.05)

    # Emit two more events.
    emit("commit_landed", {"sha": "abc"}, session_id="s", bus_path=bus)
    emit("session_ended", {}, session_id="s", bus_path=bus)

    # Signal the follower to stop after it sees >= 3 events.
    stop_event.set()
    t.join(timeout=10)

    assert len(collected) >= 3, f"Expected >=3 events, got {len(collected)}: {collected}"
    event_types = [e["event_type"] for e in collected]
    assert "task_completed" in event_types
    assert "commit_landed" in event_types
    assert "session_ended" in event_types


# ---------------------------------------------------------------------------
# Test 5: schema validation rejects unknown event_type
# ---------------------------------------------------------------------------

def test_emit_rejects_unknown_event_type(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)
    with pytest.raises(ValueError, match="Unknown event_type"):
        emit("this_is_not_valid", {}, bus_path=bus)

    # File must not have been created or must be empty.
    if bus.exists():
        assert bus.stat().st_size == 0


def test_emit_all_valid_event_types(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)
    for et in EVENT_TYPES:
        emit(et, {}, bus_path=bus)
    events = _all_events(bus)
    assert len(events) == len(EVENT_TYPES)


# ---------------------------------------------------------------------------
# Test 6: rotation triggered at configured threshold
# ---------------------------------------------------------------------------

def test_rotation_triggered(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)
    # Write content just over the threshold.
    threshold = 100  # bytes — tiny, for test speed
    bus.parent.mkdir(parents=True, exist_ok=True)
    bus.write_bytes(b"x" * (threshold + 1))

    # One more emit should trigger rotation.
    emit(
        "task_completed",
        {"after_rotation": True},
        session_id="s",
        bus_path=bus,
        rotation_bytes=threshold,
    )

    # The bus file should now contain only the new event.
    content = bus.read_text("utf-8")
    lines = [l for l in content.splitlines() if l.strip()]
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["payload"]["after_rotation"] is True

    # An archive file must exist.
    archives = list(tmp_path.glob("events-*.jsonl.gz"))
    assert len(archives) >= 1, "No archive file created after rotation"


# ---------------------------------------------------------------------------
# Test 7: corrupt line tolerated (skipped)
# ---------------------------------------------------------------------------

def test_corrupt_line_tolerated(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)
    bus.parent.mkdir(parents=True, exist_ok=True)

    good_before = json.dumps(
        {"ts": "2025-01-01T00:00:00+00:00", "session_id": "s",
         "event_type": "task_completed", "payload": {"n": 1}}
    )
    corrupt = "THIS IS NOT JSON{{{ broken !!!"
    good_after = json.dumps(
        {"ts": "2025-01-02T00:00:00+00:00", "session_id": "s",
         "event_type": "session_ended", "payload": {"n": 2}}
    )
    bus.write_text("\n".join([good_before, corrupt, good_after]) + "\n", encoding="utf-8")

    events = _all_events(bus)
    # Only the two valid lines should be returned.
    assert len(events) == 2
    assert events[0]["event_type"] == "task_completed"
    assert events[1]["event_type"] == "session_ended"


# ---------------------------------------------------------------------------
# Test 8: stats counts last hour correctly
# ---------------------------------------------------------------------------

def test_stats_counts_last_hour(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)

    # Emit events that are inside the window.
    emit("task_completed", {"i": 1}, session_id="s", bus_path=bus)
    emit("task_completed", {"i": 2}, session_id="s", bus_path=bus)
    emit("commit_landed", {"sha": "abc"}, session_id="s", bus_path=bus)

    # Inject a very old event directly (outside the 1-hour window).
    old_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=2)).isoformat()
    old_record = json.dumps(
        {"ts": old_ts, "session_id": "s", "event_type": "session_started", "payload": {}}
    )
    with bus.open("a", encoding="utf-8") as fh:
        fh.write(old_record + "\n")

    counts = stats(window_seconds=3600, bus_path=bus)

    assert counts["task_completed"] == 2
    assert counts["commit_landed"] == 1
    # session_started was injected outside the window — must NOT appear.
    assert "session_started" not in counts


# ---------------------------------------------------------------------------
# Bonus: emit rejects non-dict payload
# ---------------------------------------------------------------------------

def test_emit_rejects_non_dict_payload(tmp_path: Path) -> None:
    bus = _make_bus(tmp_path)
    with pytest.raises(TypeError, match="payload must be a dict"):
        emit("task_completed", ["not", "a", "dict"], bus_path=bus)  # type: ignore[arg-type]
