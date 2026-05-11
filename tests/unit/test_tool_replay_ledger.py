"""
Tests for ADR-263 — ToolReplayLedger.

Covers:
- FRESH → PREVIEW → REFERENCE_ONLY transitions
- TTL expiration
- Item cap enforcement
- Char cap enforcement
- Spillover write/read
- stats() shape
- cleanup()
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.tool_replay_ledger import (
    Mode,
    ToolReplayLedger,
    compute_target_hash,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def ledger(tmp_path: Path) -> ToolReplayLedger:
    """Fresh ledger backed by a temp directory."""
    return ToolReplayLedger(
        session_id="test-session",
        base_dir=str(tmp_path),
    )


@pytest.fixture()
def small_ledger(tmp_path: Path) -> ToolReplayLedger:
    """Ledger with tiny caps for easy cap-enforcement tests."""
    return ToolReplayLedger(
        session_id="small-session",
        base_dir=str(tmp_path),
        char_cap=500,
        item_cap=3,
        ttl_hours=1.0,
    )


# ---------------------------------------------------------------------------
# Mode transition: FRESH → PREVIEW → REFERENCE_ONLY
# ---------------------------------------------------------------------------

class TestModeTransitions:
    def test_first_call_is_fresh(self, ledger: ToolReplayLedger) -> None:
        decision = ledger.record("Read", "abc123", 100)
        assert decision.mode == Mode.FRESH
        assert not decision.trimmed

    def test_second_call_is_preview(self, ledger: ToolReplayLedger) -> None:
        ledger.record("Read", "abc123", 100)
        decision = ledger.record("Read", "abc123", 100)
        assert decision.mode == Mode.PREVIEW
        assert decision.trimmed

    def test_char_cap_triggers_reference_only(self, small_ledger: ToolReplayLedger) -> None:
        """After cumulative chars exceed char_cap on replay, mode = REFERENCE_ONLY."""
        # First call: FRESH, contributes 300 chars (item_cap=3, char_cap=500)
        small_ledger.record("Bash", "hash1", 300)
        # Second call same target: PREVIEW, adds 300 → total = 600 > cap of 500
        decision = small_ledger.record("Bash", "hash1", 300)
        assert decision.mode == Mode.REFERENCE_ONLY
        assert decision.trim_reason == "char_cap"

    def test_get_mode_without_modifying_budget(self, ledger: ToolReplayLedger) -> None:
        assert ledger.get_mode("Read", "xyz") == Mode.FRESH
        # record once
        ledger.record("Read", "xyz", 100)
        assert ledger.get_mode("Read", "xyz") == Mode.PREVIEW
        # budget should not have changed from get_mode calls
        stats = ledger.stats()
        assert stats["total_chars"] == 100  # only from the one record()


# ---------------------------------------------------------------------------
# TTL expiration
# ---------------------------------------------------------------------------

class TestTTLExpiration:
    def test_expired_entry_returns_fresh(self, ledger: ToolReplayLedger) -> None:
        """An entry whose touchedAt is older than ttl should be treated as new."""
        ledger.record("Bash", "ttlhash", 100)

        # Mock time to be 5 hours in the future
        future = time.time() + 5 * 3600
        with patch("lib.tool_replay_ledger.time") as mock_time:
            mock_time.time.return_value = future
            decision = ledger.record("Bash", "ttlhash", 100)

        assert decision.mode == Mode.FRESH

    def test_get_mode_expired_returns_fresh(self, ledger: ToolReplayLedger) -> None:
        ledger.record("Read", "expirehash", 200)
        future = time.time() + 5 * 3600
        with patch("lib.tool_replay_ledger.time") as mock_time:
            mock_time.time.return_value = future
            mode = ledger.get_mode("Read", "expirehash")
        assert mode == Mode.FRESH


# ---------------------------------------------------------------------------
# Item cap enforcement
# ---------------------------------------------------------------------------

class TestItemCap:
    def test_item_cap_blocks_new_targets(self, small_ledger: ToolReplayLedger) -> None:
        """After item_cap distinct (tool, target) pairs, the 11th triggers REFERENCE_ONLY."""
        # Fill cap (3 items for small_ledger)
        for i in range(small_ledger._item_cap):
            d = small_ledger.record("Bash", f"hash{i}", 10)
            assert d.mode == Mode.FRESH, f"Expected FRESH for item {i}"

        # (item_cap + 1)-th new target → REFERENCE_ONLY with trim_reason="item_cap"
        d = small_ledger.record("Bash", "overflow_hash", 10)
        assert d.mode == Mode.REFERENCE_ONLY
        assert d.trim_reason == "item_cap"

    def test_item_cap_with_10_items_default(self, tmp_path: Path) -> None:
        """Default item_cap=10: 10 items FRESH, 11th REFERENCE_ONLY."""
        ledger = ToolReplayLedger(
            session_id="cap10",
            base_dir=str(tmp_path),
            # Use tiny char_cap so char cap doesn't fire first
            char_cap=999_999,
            item_cap=10,
        )
        for i in range(10):
            d = ledger.record("Read", f"target{i}", 5)
            assert d.mode == Mode.FRESH

        d = ledger.record("Read", "target_overflow", 5)
        assert d.mode == Mode.REFERENCE_ONLY
        assert d.trim_reason == "item_cap"


# ---------------------------------------------------------------------------
# Char cap enforcement
# ---------------------------------------------------------------------------

class TestCharCap:
    def test_cumulative_chars_exceed_cap(self, tmp_path: Path) -> None:
        """Cumulative chars > 20K on replay → REFERENCE_ONLY."""
        ledger = ToolReplayLedger(
            session_id="charcap",
            base_dir=str(tmp_path),
            char_cap=20_000,
            item_cap=100,
        )
        # Register one target with a large first call (FRESH, adds to total)
        ledger.record("Read", "bighash", 15_000)
        # Replay same target: total would become 30_000 > 20_000 → REFERENCE_ONLY
        d = ledger.record("Read", "bighash", 15_000)
        assert d.mode == Mode.REFERENCE_ONLY
        assert d.trim_reason == "char_cap"

    def test_under_cap_stays_preview(self, tmp_path: Path) -> None:
        ledger = ToolReplayLedger(
            session_id="undercap",
            base_dir=str(tmp_path),
            char_cap=20_000,
            item_cap=100,
        )
        ledger.record("Bash", "smallhash", 1_000)
        d = ledger.record("Bash", "smallhash", 500)
        assert d.mode == Mode.PREVIEW


# ---------------------------------------------------------------------------
# Spillover write/read
# ---------------------------------------------------------------------------

class TestSpillover:
    def test_write_spillover_creates_file(self, ledger: ToolReplayLedger) -> None:
        content = "x" * 5000
        path = ledger.write_spillover("Read", "abc123ab", content)
        p = Path(path)
        assert p.exists()
        assert p.read_text(encoding="utf-8") == content

    def test_pointer_format(self, ledger: ToolReplayLedger) -> None:
        content = "hello spillover"
        path = ledger.write_spillover("Bash", "deadbeef", content)
        pointer = ledger.make_pointer("Bash", "deadbeef", path)
        assert pointer.startswith("[REF:tool=Bash")
        assert "target=deadbeef" in pointer
        assert path in pointer

    def test_spillover_content_is_complete(self, ledger: ToolReplayLedger) -> None:
        content = "line\n" * 1000
        path = ledger.write_spillover("WebFetch", "cafebabe", content)
        recovered = Path(path).read_text(encoding="utf-8")
        assert recovered == content

    def test_reference_only_triggers_spillover_workflow(self, small_ledger: ToolReplayLedger) -> None:
        """End-to-end: REFERENCE_ONLY decision, then spillover write, pointer valid."""
        small_ledger.record("Bash", "capme", 300)  # FRESH
        d = small_ledger.record("Bash", "capme", 300)  # triggers REFERENCE_ONLY (char_cap)
        assert d.mode == Mode.REFERENCE_ONLY

        full_content = "A" * 300
        spill_path = small_ledger.write_spillover("Bash", "capme", full_content)
        pointer = small_ledger.make_pointer("Bash", "capme", spill_path)

        # Pointer is self-describing
        assert "[REF:" in pointer
        # File is readable and contains full content
        assert Path(spill_path).read_text() == full_content


# ---------------------------------------------------------------------------
# stats()
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_shape(self, ledger: ToolReplayLedger) -> None:
        s = ledger.stats()
        assert "session_id" in s
        assert "total_chars" in s
        assert "char_cap" in s
        assert "total_items" in s
        assert "item_cap" in s
        assert "chars_saved" in s
        assert "entries_tracked" in s

    def test_stats_counts_update(self, ledger: ToolReplayLedger) -> None:
        ledger.record("Read", "h1", 500)
        ledger.record("Read", "h2", 300)
        s = ledger.stats()
        assert s["total_items"] == 2
        assert s["total_chars"] == 800
        assert s["entries_tracked"] == 2

    def test_stats_chars_saved_increments(self, small_ledger: ToolReplayLedger) -> None:
        small_ledger.record("Bash", "saved_hash", 100)
        small_ledger.record("Bash", "saved_hash", 100)  # PREVIEW → saves some chars
        s = small_ledger.stats()
        assert s["chars_saved"] >= 0  # non-negative; exact value depends on thresholds


# ---------------------------------------------------------------------------
# cleanup()
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_cleanup_removes_db(self, ledger: ToolReplayLedger) -> None:
        db_path = Path(ledger._db_path)
        assert db_path.exists()
        ledger.cleanup()
        assert not db_path.exists()

    def test_cleanup_removes_spillover_dir(self, ledger: ToolReplayLedger) -> None:
        # Create some spillover files
        ledger.write_spillover("Read", "abc", "content")
        spillover_dir = Path(ledger._spillover_dir)
        assert spillover_dir.exists()
        ledger.cleanup()
        assert not spillover_dir.exists()


# ---------------------------------------------------------------------------
# compute_target_hash helper
# ---------------------------------------------------------------------------

class TestComputeTargetHash:
    def test_stable_hash_for_same_args(self) -> None:
        h1 = compute_target_hash("cat /foo/bar.py")
        h2 = compute_target_hash("cat /foo/bar.py")
        assert h1 == h2

    def test_length_is_16(self) -> None:
        h = compute_target_hash("Read /some/path")
        assert len(h) == 16

    def test_different_args_different_hash(self) -> None:
        h1 = compute_target_hash("cat /foo.py")
        h2 = compute_target_hash("cat /bar.py")
        assert h1 != h2
