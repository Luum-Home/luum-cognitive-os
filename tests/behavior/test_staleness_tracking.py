"""Behavior tests for SDD exploration staleness tracking.

Tests the staleness detection logic used by sdd-explore to decide whether
to run a full exploration, an incremental refresh, or skip entirely.

Related skill: sdd-explore
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Staleness logic
# ---------------------------------------------------------------------------


def check_staleness(
    exploration_date: Optional[str],
    threshold_days: int = 30,
    force_full: bool = False,
) -> str:
    """Determine exploration mode based on staleness.

    Args:
        exploration_date: ISO-format date of last exploration, or None.
        threshold_days: Number of days before exploration is considered stale.
        force_full: If True, always return 'full' regardless of staleness.

    Returns:
        'full' | 'incremental-refresh' | 'skip'
    """
    if force_full:
        return "full"

    if exploration_date is None:
        return "full"

    last = datetime.fromisoformat(exploration_date)
    age = (datetime.now() - last).days

    if age >= threshold_days:
        return "incremental-refresh"

    return "skip"


def incremental_refresh(
    previous_files: Dict[str, str],
    current_files: Dict[str, str],
) -> Dict[str, str]:
    """Re-analyze only changed files, preserving unchanged entries.

    Args:
        previous_files: Mapping of filepath -> analysis from prior exploration.
        current_files: Mapping of filepath -> hash for current state.

    Returns:
        Updated analysis dict (unchanged entries kept, changed entries
        replaced with placeholder indicating re-analysis needed).
    """
    result: Dict[str, str] = {}
    for path, current_hash in current_files.items():
        prev = previous_files.get(path)
        if prev is not None and prev == current_hash:
            # File unchanged — preserve previous analysis
            result[path] = prev
        else:
            # File changed or new — mark for re-analysis
            result[path] = f"re-analyzed:{current_hash}"
    return result


def format_freshness_metadata(
    exploration_date: str,
    mode: str,
    files_analyzed: int,
    files_total: int,
) -> str:
    """Format the Freshness section for exploration output.

    Returns a multiline string with required fields.
    """
    return (
        "## Freshness\n"
        f"- Last exploration: {exploration_date}\n"
        f"- Mode: {mode}\n"
        f"- Files analyzed: {files_analyzed}/{files_total}\n"
    )


# ---------------------------------------------------------------------------
# Tests: Staleness detection
# ---------------------------------------------------------------------------


class TestStalenessDetection:
    """Tests for the check_staleness function."""

    def test_fresh_exploration_skipped(self):
        """Exploration <30 days old returns 'skip' (still fresh)."""
        recent = (datetime.now() - timedelta(days=10)).isoformat()
        assert check_staleness(recent) == "skip"

    def test_stale_exploration_triggers_refresh(self):
        """Exploration >=30 days old triggers incremental refresh."""
        old = (datetime.now() - timedelta(days=45)).isoformat()
        assert check_staleness(old) == "incremental-refresh"

    def test_no_prior_exploration_triggers_full(self):
        """No existing exploration means full mode."""
        assert check_staleness(None) == "full"

    def test_staleness_threshold_boundary(self):
        """Exactly 30 days is considered stale (>=30)."""
        boundary = (datetime.now() - timedelta(days=30)).isoformat()
        assert check_staleness(boundary) == "incremental-refresh"

    def test_force_full_ignores_staleness(self):
        """Explicit force_full overrides staleness check."""
        recent = (datetime.now() - timedelta(days=5)).isoformat()
        assert check_staleness(recent, force_full=True) == "full"

    def test_force_full_with_no_prior(self):
        """force_full with no prior exploration still returns full."""
        assert check_staleness(None, force_full=True) == "full"

    @pytest.mark.parametrize(
        "days_ago,expected",
        [
            (0, "skip"),
            (1, "skip"),
            (29, "skip"),
            (30, "incremental-refresh"),
            (31, "incremental-refresh"),
            (365, "incremental-refresh"),
        ],
    )
    def test_staleness_parametrized(self, days_ago: int, expected: str):
        """Staleness detection across various ages."""
        date = (datetime.now() - timedelta(days=days_ago)).isoformat()
        assert check_staleness(date) == expected


# ---------------------------------------------------------------------------
# Tests: Incremental refresh
# ---------------------------------------------------------------------------


class TestIncrementalRefresh:

    def test_incremental_refresh_preserves_unchanged(self):
        """Only changed files are re-analyzed; unchanged entries preserved."""
        previous = {"a.py": "hash1", "b.py": "hash2", "c.py": "hash3"}
        current = {"a.py": "hash1", "b.py": "hash_new", "c.py": "hash3"}

        result = incremental_refresh(previous, current)

        assert result["a.py"] == "hash1"  # preserved
        assert result["b.py"] == "re-analyzed:hash_new"  # changed
        assert result["c.py"] == "hash3"  # preserved

    def test_new_file_is_analyzed(self):
        """A file not in previous exploration is marked for analysis."""
        previous = {"a.py": "hash1"}
        current = {"a.py": "hash1", "new.py": "hash_new"}

        result = incremental_refresh(previous, current)

        assert result["a.py"] == "hash1"
        assert result["new.py"] == "re-analyzed:hash_new"

    def test_removed_file_not_in_result(self):
        """Files removed from codebase don't appear in result."""
        previous = {"a.py": "hash1", "removed.py": "hash2"}
        current = {"a.py": "hash1"}

        result = incremental_refresh(previous, current)

        assert "removed.py" not in result
        assert result["a.py"] == "hash1"


# ---------------------------------------------------------------------------
# Tests: Freshness metadata format
# ---------------------------------------------------------------------------


class TestFreshnessMetadata:

    def test_freshness_metadata_format(self):
        """Output contains Freshness section with all required fields."""
        output = format_freshness_metadata(
            exploration_date="2025-12-01",
            mode="incremental-refresh",
            files_analyzed=12,
            files_total=50,
        )

        assert "## Freshness" in output
        assert "Last exploration:" in output
        assert "Mode:" in output
        assert "Files analyzed:" in output
        assert "12/50" in output

    def test_freshness_metadata_full_mode(self):
        """Full mode metadata shows all files analyzed."""
        output = format_freshness_metadata(
            exploration_date="2025-12-01",
            mode="full",
            files_analyzed=50,
            files_total=50,
        )

        assert "Mode: full" in output
        assert "50/50" in output
