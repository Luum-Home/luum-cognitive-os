"""
Unit tests for lib.feedback_consumer — read_recent_feedback, group_by_classification,
surface_actionable, and summarise_for_skill_improvement.

Tests execute actual behaviour (grouping logic, filtering, ranking) against synthetic
JSONL data written to a tmp_path fixture. No mocking of filesystem — real I/O is tested.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from lib.feedback_consumer import (
    ACTIONABLE_CATEGORIES,
    group_by_classification,
    read_recent_feedback,
    summarise_for_skill_improvement,
    surface_actionable,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, entries: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _make_entry(
    category: str,
    confidence: float = 0.7,
    timestamp: str = "2026-04-30T10:00:00+00:00",
    prompt_length: int = 50,
) -> Dict[str, Any]:
    return {
        "timestamp": timestamp,
        "category": category,
        "confidence": confidence,
        "prompt_length": prompt_length,
    }


# ---------------------------------------------------------------------------
# read_recent_feedback
# ---------------------------------------------------------------------------


class TestReadRecentFeedback:
    def test_returns_empty_list_when_file_missing(self, tmp_path: Path) -> None:
        result = read_recent_feedback(limit=10, metrics_dir=str(tmp_path))
        assert result == []

    def test_reads_all_entries_when_fewer_than_limit(self, tmp_path: Path) -> None:
        entries = [_make_entry("feedback"), _make_entry("task_request")]
        _write_jsonl(tmp_path / "prompt-captures.jsonl", entries)
        result = read_recent_feedback(limit=50, metrics_dir=str(tmp_path))
        assert len(result) == 2

    def test_respects_limit_returns_last_n(self, tmp_path: Path) -> None:
        entries = [_make_entry("feedback", timestamp=f"2026-04-{10+i:02d}T00:00:00+00:00") for i in range(20)]
        _write_jsonl(tmp_path / "prompt-captures.jsonl", entries)
        result = read_recent_feedback(limit=5, metrics_dir=str(tmp_path))
        assert len(result) == 5
        # Should be the last 5 entries (newest 5)
        assert result[0]["timestamp"] == "2026-04-25T00:00:00+00:00"

    def test_ignores_malformed_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "prompt-captures.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"ok": 1}\nnot json\n{"ok": 2}\n', encoding="utf-8")
        result = read_recent_feedback(limit=10, metrics_dir=str(tmp_path))
        assert len(result) == 2
        assert all(e.get("ok") in (1, 2) for e in result)

    def test_returns_entries_in_chronological_order(self, tmp_path: Path) -> None:
        entries = [
            _make_entry("feedback", timestamp="2026-04-01T00:00:00+00:00"),
            _make_entry("task_request", timestamp="2026-04-30T00:00:00+00:00"),
        ]
        _write_jsonl(tmp_path / "prompt-captures.jsonl", entries)
        result = read_recent_feedback(limit=50, metrics_dir=str(tmp_path))
        assert result[0]["timestamp"] < result[1]["timestamp"]


# ---------------------------------------------------------------------------
# group_by_classification
# ---------------------------------------------------------------------------


class TestGroupByClassification:
    def test_groups_by_category_field(self) -> None:
        entries = [
            _make_entry("feedback"),
            _make_entry("feedback"),
            _make_entry("task_request"),
        ]
        groups = group_by_classification(entries)
        assert len(groups["feedback"]) == 2
        assert len(groups["task_request"]) == 1

    def test_unknown_category_placed_under_itself(self) -> None:
        entries = [_make_entry("novel_category")]
        groups = group_by_classification(entries)
        assert "novel_category" in groups

    def test_empty_input_returns_empty_dict(self) -> None:
        assert group_by_classification([]) == {}

    def test_missing_category_field_defaults_to_other(self) -> None:
        entries = [{"timestamp": "2026-04-30T00:00:00+00:00", "confidence": 0.5}]
        groups = group_by_classification(entries)
        assert "other" in groups

    def test_preserves_all_entries(self) -> None:
        entries = [_make_entry("feedback"), _make_entry("correction"), _make_entry("escalation")]
        groups = group_by_classification(entries)
        total = sum(len(v) for v in groups.values())
        assert total == 3


# ---------------------------------------------------------------------------
# surface_actionable
# ---------------------------------------------------------------------------


class TestSurfaceActionable:
    def test_returns_only_actionable_categories(self) -> None:
        entries = [
            _make_entry("feedback"),
            _make_entry("correction"),
            _make_entry("escalation"),
            _make_entry("task_request"),  # not actionable
            _make_entry("context"),       # not actionable
        ]
        grouped = group_by_classification(entries)
        actionable = surface_actionable(grouped)
        assert len(actionable) == 3
        for entry in actionable:
            assert entry["is_actionable"] is True

    def test_filters_out_low_confidence_entries(self) -> None:
        entries = [
            _make_entry("feedback", confidence=0.9),
            _make_entry("feedback", confidence=0.1),  # below threshold
        ]
        grouped = group_by_classification(entries)
        actionable = surface_actionable(grouped, min_confidence=0.5)
        assert len(actionable) == 1
        assert actionable[0]["confidence"] == 0.9

    def test_sorted_newest_first(self) -> None:
        entries = [
            _make_entry("feedback", timestamp="2026-04-01T00:00:00+00:00"),
            _make_entry("feedback", timestamp="2026-04-30T00:00:00+00:00"),
        ]
        grouped = group_by_classification(entries)
        actionable = surface_actionable(grouped)
        assert actionable[0]["timestamp"] == "2026-04-30T00:00:00+00:00"

    def test_assigns_recency_rank_starting_at_1(self) -> None:
        entries = [_make_entry("feedback"), _make_entry("correction")]
        grouped = group_by_classification(entries)
        actionable = surface_actionable(grouped)
        ranks = {e["recency_rank"] for e in actionable}
        assert 1 in ranks
        assert len(ranks) == len(actionable)

    def test_augments_with_signal_category_label(self) -> None:
        entries = [_make_entry("feedback")]
        grouped = group_by_classification(entries)
        actionable = surface_actionable(grouped)
        assert "signal_category" in actionable[0]
        assert isinstance(actionable[0]["signal_category"], str)

    def test_empty_grouped_returns_empty_list(self) -> None:
        assert surface_actionable({}) == []

    def test_non_actionable_only_returns_empty(self) -> None:
        entries = [_make_entry("task_request"), _make_entry("context")]
        grouped = group_by_classification(entries)
        assert surface_actionable(grouped) == []

    def test_all_actionable_categories_covered(self) -> None:
        """Each member of ACTIONABLE_CATEGORIES must produce an actionable entry."""
        entries = [_make_entry(cat) for cat in ACTIONABLE_CATEGORIES]
        grouped = group_by_classification(entries)
        actionable = surface_actionable(grouped)
        returned_cats = {e["category"] for e in actionable}
        assert ACTIONABLE_CATEGORIES.issubset(returned_cats)


# ---------------------------------------------------------------------------
# summarise_for_skill_improvement (integration of the three helpers)
# ---------------------------------------------------------------------------


class TestSummariseForSkillImprovement:
    def test_returns_expected_keys(self, tmp_path: Path) -> None:
        entries = [_make_entry("feedback"), _make_entry("task_request")]
        _write_jsonl(tmp_path / "prompt-captures.jsonl", entries)
        summary = summarise_for_skill_improvement(limit=50, metrics_dir=str(tmp_path))
        for key in ("total_entries", "actionable_count", "by_category", "actionable_signals", "period", "data_source"):
            assert key in summary, f"missing key: {key}"

    def test_actionable_count_matches_actionable_signals(self, tmp_path: Path) -> None:
        entries = [_make_entry("feedback"), _make_entry("escalation"), _make_entry("context")]
        _write_jsonl(tmp_path / "prompt-captures.jsonl", entries)
        summary = summarise_for_skill_improvement(limit=50, metrics_dir=str(tmp_path))
        assert summary["actionable_count"] == len(summary["actionable_signals"])

    def test_period_populated_from_entry_timestamps(self, tmp_path: Path) -> None:
        entries = [
            _make_entry("feedback", timestamp="2026-04-01T00:00:00+00:00"),
            _make_entry("task_request", timestamp="2026-04-30T00:00:00+00:00"),
        ]
        _write_jsonl(tmp_path / "prompt-captures.jsonl", entries)
        summary = summarise_for_skill_improvement(limit=50, metrics_dir=str(tmp_path))
        assert summary["period"]["from"] == "2026-04-01T00:00:00+00:00"
        assert summary["period"]["to"] == "2026-04-30T00:00:00+00:00"

    def test_handles_missing_file_gracefully(self, tmp_path: Path) -> None:
        summary = summarise_for_skill_improvement(limit=10, metrics_dir=str(tmp_path))
        assert summary["total_entries"] == 0
        assert summary["actionable_count"] == 0
        assert summary["actionable_signals"] == []
