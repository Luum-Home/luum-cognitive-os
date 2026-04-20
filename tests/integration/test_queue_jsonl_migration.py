"""Integration tests: RateLimitQueue JSONL migration and compaction.

Test matrix (4 required by spec):
  1. migrate_fixture_state_preserved   — legacy JSON with 3 entries → JSONL has
                                         3 ``queued`` events + replay gives same items.
  2. compaction_shrinks_file           — after JSONL_COMPACTION_THRESHOLD events the
                                         JSONL is compacted and line count drops.
  3. append_during_replay_safe         — concurrent enqueue while replay is in progress
                                         does not lose data.
  4. old_format_deprecated_banner      — after migration the old ``.json`` is renamed
                                         to ``.json.deprecated`` and a ``migration``
                                         audit event is present in the JSONL.

Additional tests cover edge cases introduced by the migration path.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJ_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJ_ROOT))

from lib.rate_limiter import (  # noqa: E402
    JSONL_COMPACTION_THRESHOLD,
    PRIORITY_NORMAL,
    RateLimitQueue,
    _derive_jsonl_path,
    _replay_jsonl,
)
from lib.rate_limit_queue_migration import migrate_queue_on_boot, migration_status

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_legacy_json(path: str, items: List[Dict[str, Any]]) -> None:
    """Write a list of queue items as a legacy monolithic JSON array."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(items, fh)


def _make_legacy_item(
    queue_id: str,
    action_type: str = "agent_launch",
    description: str = "test task",
    retry_count: int = 0,
    offset_seconds: float = -30.0,
) -> Dict[str, Any]:
    now = time.time()
    return {
        "queue_id": queue_id,
        "action_type": action_type,
        "context": {"description": description},
        "priority": PRIORITY_NORMAL,
        "enqueued_at": now + offset_seconds,
        "eligible_at": now + 3600,
        "retry_count": retry_count,
    }


def _count_lines(path: str) -> int:
    if not os.path.exists(path):
        return 0
    with open(path) as fh:
        return sum(1 for line in fh if line.strip())


# ---------------------------------------------------------------------------
# Test 1: legacy fixture → JSONL has 3 queued events + state preserved
# ---------------------------------------------------------------------------


class TestMigrateFixtureStatePreserved:
    """Migrating a 3-entry JSON fixture produces a valid JSONL and identical state."""

    def test_migrate_fixture_state_preserved(self, tmp_path: Path) -> None:
        """Core requirement: 3 legacy items → 3 queued events, identical item fields."""
        json_path = str(tmp_path / "rate-limit-queue.json")
        jsonl_path = _derive_jsonl_path(json_path)

        legacy_items = [
            _make_legacy_item("aaa00001", description="task alpha"),
            _make_legacy_item("bbb00002", description="task beta"),
            _make_legacy_item("ccc00003", description="task gamma", retry_count=1),
        ]
        _write_legacy_json(json_path, legacy_items)

        # Run migration
        migrated = migrate_queue_on_boot(json_path=json_path, jsonl_path=jsonl_path)
        assert migrated == 3, f"Expected 3 migrated, got {migrated}"

        # JSONL must exist
        assert os.path.exists(jsonl_path), "JSONL file should be created by migration"

        # Replay the JSONL and verify item fields match the originals
        replayed = _replay_jsonl(jsonl_path)
        replayed_by_id = {item["queue_id"]: item for item in replayed}

        assert set(replayed_by_id.keys()) == {"aaa00001", "bbb00002", "ccc00003"}, (
            f"Unexpected queue IDs after replay: {set(replayed_by_id.keys())}"
        )

        for orig in legacy_items:
            qid = orig["queue_id"]
            replayed_item = replayed_by_id[qid]
            assert replayed_item["action_type"] == orig["action_type"], (
                f"action_type mismatch for {qid}"
            )
            assert replayed_item["context"]["description"] == orig["context"]["description"], (
                f"context mismatch for {qid}"
            )
            assert replayed_item["retry_count"] == orig["retry_count"], (
                f"retry_count mismatch for {qid}"
            )
            assert replayed_item["priority"] == orig["priority"], (
                f"priority mismatch for {qid}"
            )

    def test_migrate_idempotent(self, tmp_path: Path) -> None:
        """Calling migrate twice must not duplicate events."""
        json_path = str(tmp_path / "rate-limit-queue.json")
        jsonl_path = _derive_jsonl_path(json_path)

        legacy_items = [_make_legacy_item("dup00001")]
        _write_legacy_json(json_path, legacy_items)

        first = migrate_queue_on_boot(json_path=json_path, jsonl_path=jsonl_path)
        assert first == 1

        # Second call: JSONL now exists — must be no-op
        second = migrate_queue_on_boot(json_path=json_path, jsonl_path=jsonl_path)
        assert second == 0, "Second migration call should be a no-op"

        replayed = _replay_jsonl(jsonl_path)
        assert len(replayed) == 1, "Idempotent migration must not create duplicate items"

    def test_migrate_empty_json(self, tmp_path: Path) -> None:
        """Migrating an empty JSON array creates an empty JSONL (just the migration audit event)."""
        json_path = str(tmp_path / "rate-limit-queue.json")
        jsonl_path = _derive_jsonl_path(json_path)
        _write_legacy_json(json_path, [])

        migrated = migrate_queue_on_boot(json_path=json_path, jsonl_path=jsonl_path)
        assert migrated == 0

        # JSONL should exist (migration audit event)
        assert os.path.exists(jsonl_path)
        replayed = _replay_jsonl(jsonl_path)
        assert replayed == []

    def test_migrate_no_json_is_noop(self, tmp_path: Path) -> None:
        """If the old JSON file does not exist, migration returns 0 and no JSONL is created."""
        json_path = str(tmp_path / "nonexistent.json")
        jsonl_path = _derive_jsonl_path(json_path)

        migrated = migrate_queue_on_boot(json_path=json_path, jsonl_path=jsonl_path)
        assert migrated == 0
        assert not os.path.exists(jsonl_path), "No JSONL should be created if source is absent"


# ---------------------------------------------------------------------------
# Test 2: compaction shrinks the JSONL file
# ---------------------------------------------------------------------------


class TestCompactionShrinksFile:
    """After JSONL_COMPACTION_THRESHOLD events the file is compacted."""

    def test_compaction_shrinks_file(self, tmp_path: Path) -> None:
        """Core requirement: N=50 live items survive; compacted JSONL has ~50-60 lines."""
        queue_path = str(tmp_path / "rate-limit-queue.json")
        queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=3600)

        # Enqueue 50 items (these will be kept)
        for i in range(50):
            queue.enqueue("agent_launch", {"description": f"live-{i}"})

        jsonl_path = queue._jsonl_path

        # Pump enough dequeue+enqueue cycles to exceed the compaction threshold.
        # Each cycle: make items eligible → dequeue → re-enqueue.
        # We track events: each enqueue = 1 event, each dequeue = N events,
        # each _save during dequeue/enqueue = 1+N events.
        # Easier: just directly append dummy events until threshold.
        from lib.rate_limiter import _append_event

        filler_count = JSONL_COMPACTION_THRESHOLD + 10
        now = time.time()
        for _ in range(filler_count):
            _append_event(
                jsonl_path,
                {"action": "updated", "action_id": "filler", "timestamp": now, "item": {}},
            )

        # Trigger compaction via one more enqueue
        queue.enqueue("agent_launch", {"description": "trigger-compact"})

        line_count = _count_lines(jsonl_path)
        # After compaction: one compacted event (1 line) + the new enqueue event (1 line)
        # = 2 lines at minimum.  The compacted snapshot has all 51 live items embedded
        # in a single line, so total lines should be << filler_count.
        assert line_count <= 60, (
            f"Compacted JSONL should have <=60 lines (have {line_count} after "
            f"compaction from {filler_count} filler events)"
        )

        # Verify all 51 live items survive compaction
        reloaded = RateLimitQueue(state_path=queue_path, cooldown_seconds=3600)
        items = reloaded.peek()
        assert len(items) == 51, (
            f"Expected 51 live items after compaction, got {len(items)}"
        )

    def test_no_compaction_below_threshold(self, tmp_path: Path) -> None:
        """JSONL must NOT be compacted when event count is below threshold."""
        queue_path = str(tmp_path / "rate-limit-queue.json")
        queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=3600)

        for i in range(5):
            queue.enqueue("agent_launch", {"description": f"item-{i}"})

        line_count = _count_lines(queue._jsonl_path)
        # 5 queued events — should not have been compacted
        assert line_count == 5, (
            f"Expected 5 JSONL lines (no compaction), got {line_count}"
        )


# ---------------------------------------------------------------------------
# Test 3: append during replay is safe
# ---------------------------------------------------------------------------


class TestAppendDuringReplaySafe:
    """Concurrent enqueue while replay is in progress does not lose data."""

    def test_concurrent_enqueue_and_reload(self, tmp_path: Path) -> None:
        """Two threads enqueue concurrently; all items visible after reload."""
        queue_path = str(tmp_path / "rate-limit-queue.json")
        errors: list[Exception] = []
        ids: list[str] = []
        lock = threading.Lock()

        def worker(index: int) -> None:
            q = RateLimitQueue(state_path=queue_path, cooldown_seconds=3600)
            try:
                qid = q.enqueue("agent_launch", {"description": f"concurrent-{index}"})
                with lock:
                    ids.append(qid)
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, f"Unexpected errors during concurrent enqueue: {errors}"
        assert len(ids) == 10, f"Expected 10 queue IDs, got {len(ids)}"
        assert len(set(ids)) == 10, "Duplicate queue IDs detected"

        # Reload and verify all 10 items are present
        reloaded = RateLimitQueue(state_path=queue_path, cooldown_seconds=3600)
        items = reloaded.peek()
        assert len(items) == 10, (
            f"Expected 10 items after reload, got {len(items)}"
        )

    def test_reload_after_interleaved_enqueue_dequeue(self, tmp_path: Path) -> None:
        """Replay is consistent after a mix of enqueue and dequeue events."""
        queue_path = str(tmp_path / "rate-limit-queue.json")
        queue = RateLimitQueue(state_path=queue_path, cooldown_seconds=3600)

        # Enqueue 5, make 3 eligible, dequeue them
        ids = []
        for i in range(5):
            ids.append(queue.enqueue("bash_command", {"description": f"cmd-{i}"}))

        # Make first 3 eligible
        for item in queue._items[:3]:
            item["eligible_at"] = time.time() - 1
        queue._save()

        dequeued = queue.dequeue_ready()
        assert len(dequeued) == 3

        # Reload from disk — should have exactly 2 remaining
        reloaded = RateLimitQueue(state_path=queue_path, cooldown_seconds=3600)
        remaining = reloaded.peek()
        assert len(remaining) == 2, (
            f"Expected 2 remaining items after reload, got {len(remaining)}"
        )


# ---------------------------------------------------------------------------
# Test 4: old format deprecated banner
# ---------------------------------------------------------------------------


class TestOldFormatDeprecatedBanner:
    """After migration the old .json is renamed and a migration event exists in JSONL."""

    def test_old_json_renamed_to_deprecated(self, tmp_path: Path) -> None:
        """Core requirement: legacy .json → .json.deprecated after migration."""
        json_path = str(tmp_path / "rate-limit-queue.json")
        jsonl_path = _derive_jsonl_path(json_path)
        deprecated_path = json_path + ".deprecated"

        legacy_items = [
            _make_legacy_item("dep00001", description="item one"),
            _make_legacy_item("dep00002", description="item two"),
        ]
        _write_legacy_json(json_path, legacy_items)

        assert os.path.exists(json_path), "Precondition: JSON must exist before migration"
        assert not os.path.exists(deprecated_path), "Precondition: .deprecated should not exist"

        migrate_queue_on_boot(json_path=json_path, jsonl_path=jsonl_path)

        # Old file must have been renamed
        assert not os.path.exists(json_path), (
            "Legacy .json should be renamed to .deprecated after migration"
        )
        assert os.path.exists(deprecated_path), (
            "Legacy .json.deprecated backup must exist after migration"
        )

    def test_migration_audit_event_in_jsonl(self, tmp_path: Path) -> None:
        """JSONL must contain a ``migration`` action event after migration."""
        json_path = str(tmp_path / "rate-limit-queue.json")
        jsonl_path = _derive_jsonl_path(json_path)

        legacy_items = [_make_legacy_item("audit001")]
        _write_legacy_json(json_path, legacy_items)
        migrate_queue_on_boot(json_path=json_path, jsonl_path=jsonl_path)

        # Parse all events from JSONL
        events = []
        with open(jsonl_path) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(json.loads(line))

        migration_events = [e for e in events if e.get("action") == "migration"]
        assert len(migration_events) == 1, (
            f"Expected exactly 1 migration audit event, found {len(migration_events)}"
        )
        m = migration_events[0]
        assert m["migrated_count"] == 1, (
            f"Migration event should report 1 migrated item, got {m['migrated_count']}"
        )
        assert m["source"] == json_path, "Migration event should record source path"

    def test_migration_status_helper(self, tmp_path: Path) -> None:
        """migration_status() correctly reports state before and after migration."""
        json_path = str(tmp_path / "rate-limit-queue.json")
        jsonl_path = _derive_jsonl_path(json_path)

        # Before anything exists
        status = migration_status(json_path=json_path, jsonl_path=jsonl_path)
        assert not status["json_exists"]
        assert not status["jsonl_exists"]
        assert not status["needs_migration"]
        assert not status["already_migrated"]

        # After writing JSON (needs migration)
        _write_legacy_json(json_path, [_make_legacy_item("st0001")])
        status = migration_status(json_path=json_path, jsonl_path=jsonl_path)
        assert status["json_exists"]
        assert not status["jsonl_exists"]
        assert status["needs_migration"]

        # After migration (already migrated)
        migrate_queue_on_boot(json_path=json_path, jsonl_path=jsonl_path)
        status = migration_status(json_path=json_path, jsonl_path=jsonl_path)
        assert not status["json_exists"]
        assert status["jsonl_exists"]
        assert status["deprecated_exists"]
        assert status["already_migrated"]
        assert not status["needs_migration"]

    def test_ratelimitqueue_auto_migrates_on_init(self, tmp_path: Path) -> None:
        """RateLimitQueue.__init__ auto-migrates the legacy JSON without explicit call."""
        json_path = str(tmp_path / "rate-limit-queue.json")
        jsonl_path = _derive_jsonl_path(json_path)
        deprecated_path = json_path + ".deprecated"

        legacy_items = [
            _make_legacy_item("auto001", description="auto-migrated"),
            _make_legacy_item("auto002", description="also migrated"),
        ]
        _write_legacy_json(json_path, legacy_items)

        # Constructing a RateLimitQueue should trigger migration automatically
        queue = RateLimitQueue(state_path=json_path, cooldown_seconds=3600)

        assert os.path.exists(jsonl_path), "JSONL should be created by auto-migration"
        assert os.path.exists(deprecated_path), ".deprecated file should exist after auto-migration"

        items = queue.peek()
        assert len(items) == 2, f"Expected 2 items after auto-migration, got {len(items)}"
        descriptions = {i["context"]["description"] for i in items}
        assert descriptions == {"auto-migrated", "also migrated"}
