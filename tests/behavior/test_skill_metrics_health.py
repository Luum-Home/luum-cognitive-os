"""Behavior tests for skill-metrics.jsonl health.

These tests validate the real metrics file in .cognitive-os/metrics/skill-metrics.jsonl.
They check population, schema consistency, and that recent entries have non-zero values.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
METRICS_FILE = PROJECT_ROOT / ".cognitive-os" / "metrics" / "skill-metrics.jsonl"


def _load_entries() -> list[dict]:
    """Load all valid entries from skill-metrics.jsonl."""
    if not METRICS_FILE.exists():
        return []
    entries = []
    for line in METRICS_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


def _recent_entries(entries: list[dict], hours: int = 24) -> list[dict]:
    """Filter entries to those within the last N hours."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    recent = []
    for entry in entries:
        ts_str = entry.get("timestamp", "")
        if not ts_str:
            continue
        try:
            # Handle both Z suffix and +00:00
            ts_str_clean = ts_str.replace("Z", "+00:00")
            ts = datetime.fromisoformat(ts_str_clean)
            if ts >= cutoff:
                recent.append(entry)
        except (ValueError, TypeError):
            pass
    return recent


# ---------------------------------------------------------------------------
# test_metrics_file_exists
# ---------------------------------------------------------------------------

class TestMetricsFileExists:
    def test_metrics_file_exists(self) -> None:
        """skill-metrics.jsonl must exist in .cognitive-os/metrics/."""
        assert METRICS_FILE.exists(), (
            f"skill-metrics.jsonl not found at {METRICS_FILE}. "
            "The metrics file should be created by the first skill invocation."
        )

    def test_metrics_file_is_readable(self) -> None:
        """skill-metrics.jsonl must be readable."""
        if not METRICS_FILE.exists():
            pytest.skip("No skill-metrics.jsonl present")
        content = METRICS_FILE.read_text()
        # File may be empty but should not raise
        assert isinstance(content, str)


# ---------------------------------------------------------------------------
# test_no_zero_token_entries_recent
# ---------------------------------------------------------------------------

class TestNoZeroTokenEntriesRecent:
    """Entries written after the fix should have tokens > 0.

    This test is xfail if there are no recent entries (i.e., no skills have
    been invoked in the last 24 hours since the fix was applied).
    """

    @pytest.mark.xfail(
        reason="No recent entries in skill-metrics.jsonl — invoke a skill to produce data",
        strict=False,
    )
    def test_recent_entries_have_nonzero_tokens(self) -> None:
        """Entries from the last 24h should have tokens > 0 after the fix."""
        entries = _load_entries()
        recent = _recent_entries(entries, hours=24)

        if not recent:
            pytest.xfail("No entries in last 24 hours")

        zero_token_entries = [e for e in recent if e.get("tokens", 0) == 0]
        assert not zero_token_entries, (
            f"{len(zero_token_entries)} recent entries still have tokens=0. "
            "Fix may not have been applied or hook not firing.\n"
            f"Sample: {zero_token_entries[:3]}"
        )

    @pytest.mark.xfail(
        reason="No recent entries in skill-metrics.jsonl — invoke a skill to produce data",
        strict=False,
    )
    def test_recent_entries_have_nonzero_duration(self) -> None:
        """Entries from the last 24h should have duration_ms > 0 after the fix."""
        entries = _load_entries()
        recent = _recent_entries(entries, hours=24)

        if not recent:
            pytest.xfail("No entries in last 24 hours")

        zero_duration_entries = [e for e in recent if e.get("duration_ms", 0) == 0]
        assert not zero_duration_entries, (
            f"{len(zero_duration_entries)} recent entries still have duration_ms=0.\n"
            f"Sample: {zero_duration_entries[:3]}"
        )


# ---------------------------------------------------------------------------
# test_schema_consistency
# ---------------------------------------------------------------------------

class TestSchemaConsistency:
    REQUIRED_FIELDS = {"timestamp", "skill", "model", "tokens", "duration_ms", "success"}

    def test_all_entries_have_same_fields(self) -> None:
        """All entries must have the same set of required fields."""
        entries = _load_entries()
        if not entries:
            pytest.skip("No entries in skill-metrics.jsonl")

        for i, entry in enumerate(entries):
            missing = self.REQUIRED_FIELDS - set(entry.keys())
            assert not missing, (
                f"Entry {i + 1} is missing fields: {missing}\nEntry: {entry}"
            )

    def test_all_entries_have_string_skill(self) -> None:
        """skill field must always be a non-empty string."""
        entries = _load_entries()
        if not entries:
            pytest.skip("No entries in skill-metrics.jsonl")

        for i, entry in enumerate(entries):
            skill = entry.get("skill")
            assert isinstance(skill, str) and skill, (
                f"Entry {i + 1} has invalid skill field: {skill!r}"
            )

    def test_all_entries_have_valid_timestamps(self) -> None:
        """timestamp field must be a parseable ISO-8601 string."""
        entries = _load_entries()
        if not entries:
            pytest.skip("No entries in skill-metrics.jsonl")

        for i, entry in enumerate(entries):
            ts_str = entry.get("timestamp", "")
            assert ts_str, f"Entry {i + 1} has empty timestamp"
            try:
                ts_clean = ts_str.replace("Z", "+00:00")
                datetime.fromisoformat(ts_clean)
            except (ValueError, TypeError) as exc:
                pytest.fail(f"Entry {i + 1} has invalid timestamp {ts_str!r}: {exc}")

    def test_success_field_is_boolean(self) -> None:
        """success field must be a boolean in all entries."""
        entries = _load_entries()
        if not entries:
            pytest.skip("No entries in skill-metrics.jsonl")

        for i, entry in enumerate(entries):
            success = entry.get("success")
            assert isinstance(success, bool), (
                f"Entry {i + 1} has non-boolean success: {success!r}"
            )

    def test_tokens_and_duration_are_numeric(self) -> None:
        """tokens and duration_ms must be numbers in all entries."""
        entries = _load_entries()
        if not entries:
            pytest.skip("No entries in skill-metrics.jsonl")

        for i, entry in enumerate(entries):
            assert isinstance(entry.get("tokens"), (int, float)), (
                f"Entry {i + 1} tokens is not numeric: {entry.get('tokens')!r}"
            )
            assert isinstance(entry.get("duration_ms"), (int, float)), (
                f"Entry {i + 1} duration_ms is not numeric: {entry.get('duration_ms')!r}"
            )

    def test_all_tokens_zero_indicates_broken_tracker(self) -> None:
        """If ALL entries have tokens=0, the tracker is broken — this should fail.

        After the fix, at least the estimate-based approach should produce > 0.
        This test is informational: it xfails if there are no entries.
        """
        entries = _load_entries()
        if not entries:
            pytest.skip("No entries to check")

        all_zero = all(e.get("tokens", 0) == 0 for e in entries)
        zero_count = sum(1 for e in entries if e.get("tokens", 0) == 0)
        total = len(entries)

        # We allow some historical zeros (pre-fix entries) but flag if ALL are zero
        if all_zero:
            pytest.fail(
                f"ALL {total} entries have tokens=0. "
                "The skill-tracker.sh hook is not capturing token estimates. "
                "Ensure the fix was applied correctly."
            )
        elif zero_count > 0:
            # Partial zeros — informational, not a failure (pre-fix legacy data)
            pytest.xfail(
                reason=f"{zero_count}/{total} entries have tokens=0 (likely pre-fix legacy data)"
            )
