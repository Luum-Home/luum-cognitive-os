"""Unit tests for CorrelationStore (ADR-033b).

Tests:
1. store + lookup (basic round-trip)
2. TTL pruning removes old entries
3. crash recovery from JSONL
4. missing tool_use_id returns None
5. persistence across process (JSONL replay)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lib.harness_adapter.tool_use_correlation import CorrelationStore


class TestCorrelationStoreBasic:
    def test_record_and_pop_returns_stored_value(self, tmp_path):
        """record() then pop() returns the stored monotonic value."""
        store = CorrelationStore(persistence_path=tmp_path / "corr.jsonl")
        t = time.monotonic()
        store.record("abc", t)
        result = store.pop("abc")
        assert result is not None
        assert abs(result - t) < 0.001, "pop should return exactly what was stored"

    def test_pop_removes_entry(self, tmp_path):
        """pop() removes the entry; subsequent pop returns None."""
        store = CorrelationStore(persistence_path=tmp_path / "corr.jsonl")
        store.record("xyz", time.monotonic())
        assert store.pop("xyz") is not None
        assert store.pop("xyz") is None

    def test_missing_tool_use_id_returns_none(self, tmp_path):
        """pop() on an unknown ID returns None without raising."""
        store = CorrelationStore(persistence_path=tmp_path / "corr.jsonl")
        assert store.pop("does-not-exist") is None

    def test_empty_tool_use_id_is_ignored(self, tmp_path):
        """record('', ...) is silently dropped; pop('') returns None."""
        store = CorrelationStore(persistence_path=tmp_path / "corr.jsonl")
        store.record("", time.monotonic())
        assert store.pop("") is None
        assert len(store) == 0

    def test_get_does_not_remove_entry(self, tmp_path):
        """get() peeks without consuming the entry."""
        store = CorrelationStore(persistence_path=tmp_path / "corr.jsonl")
        t = time.monotonic()
        store.record("peek", t)
        assert store.get("peek") == t
        assert store.get("peek") == t  # still there


class TestCorrelationStoreTTL:
    def test_ttl_prune_removes_old_entries(self, tmp_path):
        """Entries older than ttl_seconds are pruned on the next record() call."""
        store = CorrelationStore(
            persistence_path=tmp_path / "corr.jsonl",
            ttl_seconds=0.1,  # 100 ms TTL for testing
        )
        # Use a timestamp far in the past (relative to monotonic)
        old_ts = time.monotonic() - 10.0  # 10 s ago, well past 100 ms TTL
        store._store["stale-id"] = old_ts  # inject directly to bypass record()
        # record() triggers pruning
        store.record("fresh-id", time.monotonic())
        assert store.get("stale-id") is None, "Stale entry should have been pruned"
        assert store.get("fresh-id") is not None, "Fresh entry must survive"


class TestCorrelationStoreCrashRecovery:
    def test_load_replays_jsonl_on_construction(self, tmp_path):
        """Constructing a CorrelationStore with an existing JSONL file restores state."""
        jsonl_path = tmp_path / "corr.jsonl"
        # Simulate a prior process writing the file
        t = time.monotonic()
        with open(jsonl_path, "w") as fh:
            fh.write(json.dumps({"tool_use_id": "restored-id", "started_at": t}) + "\n")

        store = CorrelationStore(persistence_path=jsonl_path)
        result = store.get("restored-id")
        assert result is not None
        assert abs(result - t) < 0.001

    def test_load_skips_stale_jsonl_entries(self, tmp_path):
        """JSONL entries older than TTL are not restored into memory."""
        jsonl_path = tmp_path / "corr.jsonl"
        stale_ts = time.monotonic() - 7200.0  # 2 hours ago
        with open(jsonl_path, "w") as fh:
            fh.write(
                json.dumps({"tool_use_id": "old-id", "started_at": stale_ts}) + "\n"
            )

        store = CorrelationStore(persistence_path=jsonl_path, ttl_seconds=3600)
        assert store.get("old-id") is None, "Stale JSONL entry should not be replayed"

    def test_persistence_across_process_boundary(self, tmp_path):
        """A value written by one CorrelationStore instance is readable by a second."""
        jsonl_path = tmp_path / "corr.jsonl"
        t = time.monotonic()

        # Process 1: write
        store1 = CorrelationStore(persistence_path=jsonl_path)
        store1.record("cross-process-id", t)

        # Process 2: new instance reads the same file
        store2 = CorrelationStore(persistence_path=jsonl_path)
        result = store2.get("cross-process-id")
        assert result is not None
        assert abs(result - t) < 0.001

    def test_malformed_jsonl_lines_are_skipped(self, tmp_path):
        """Corrupted lines in the JSONL file do not prevent loading valid lines."""
        jsonl_path = tmp_path / "corr.jsonl"
        t = time.monotonic()
        with open(jsonl_path, "w") as fh:
            fh.write("CORRUPTED LINE NOT JSON\n")
            fh.write(json.dumps({"tool_use_id": "good-id", "started_at": t}) + "\n")

        store = CorrelationStore(persistence_path=jsonl_path)
        assert store.get("good-id") is not None
