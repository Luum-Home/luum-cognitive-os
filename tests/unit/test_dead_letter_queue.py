"""Unit tests for lib/dead_letter_queue.py

Validates:
  enqueue_dead_letter writes to JSONL with correct fields
  list_dead_letters returns entries (newest first)
  requeue_dead_letter marks entry as requeued
  format_dlq_report produces a human-readable summary
  Edge cases: empty queue, unknown entry_id, multiple entries
"""
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dlq(tmp_path: Path):
    from lib.dead_letter_queue import DeadLetterQueue

    dlq_file = tmp_path / "dead-letter-queue.jsonl"
    return DeadLetterQueue(dlq_file=dlq_file), dlq_file


def _sample_entry(dlq, suffix: str = ""):
    return dlq.enqueue_dead_letter(
        task_id=f"sdd-apply-auth{suffix}",
        description=f"Implement JWT auth middleware{suffix}",
        failure_type="BUILD_ERROR",
        retry_history=[
            {"attempt": 1, "error": "cannot find module"},
            {"attempt": 2, "error": "cannot find module"},
            {"attempt": 3, "error": "cannot find module"},
        ],
        diagnosis="Missing dependency in go.mod",
    )


# ---------------------------------------------------------------------------
# Tests: enqueue
# ---------------------------------------------------------------------------


class TestEnqueue:
    def test_enqueue_creates_file(self, tmp_path):
        dlq, dlq_file = _make_dlq(tmp_path)
        _sample_entry(dlq)
        assert dlq_file.exists()

    def test_enqueue_writes_valid_jsonl(self, tmp_path):
        dlq, dlq_file = _make_dlq(tmp_path)
        _sample_entry(dlq)
        lines = dlq_file.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["task_id"] == "sdd-apply-auth"

    def test_enqueue_sets_status_dead(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        entry = _sample_entry(dlq)
        assert entry["status"] == "dead"

    def test_enqueue_sets_entry_id(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        entry = _sample_entry(dlq)
        assert entry["entry_id"] != ""
        assert len(entry["entry_id"]) == 36  # UUID4

    def test_enqueue_sets_enqueued_at(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        entry = _sample_entry(dlq)
        assert entry["enqueued_at"] is not None
        assert "T" in entry["enqueued_at"]  # ISO-8601

    def test_enqueue_sets_requeued_at_none(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        entry = _sample_entry(dlq)
        assert entry["requeued_at"] is None

    def test_enqueue_stores_retry_history(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        entry = _sample_entry(dlq)
        assert len(entry["retry_history"]) == 3

    def test_enqueue_stores_diagnosis(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        entry = _sample_entry(dlq)
        assert "go.mod" in entry["diagnosis"]

    def test_multiple_enqueues_produce_multiple_lines(self, tmp_path):
        dlq, dlq_file = _make_dlq(tmp_path)
        _sample_entry(dlq, "-a")
        _sample_entry(dlq, "-b")
        _sample_entry(dlq, "-c")
        lines = dlq_file.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_each_entry_has_unique_entry_id(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        e1 = _sample_entry(dlq, "-a")
        e2 = _sample_entry(dlq, "-b")
        assert e1["entry_id"] != e2["entry_id"]


# ---------------------------------------------------------------------------
# Tests: list_dead_letters
# ---------------------------------------------------------------------------


class TestList:
    def test_list_empty_queue_returns_empty(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        assert dlq.list_dead_letters() == []

    def test_list_returns_entries(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        _sample_entry(dlq)
        entries = dlq.list_dead_letters()
        assert len(entries) == 1

    def test_list_returns_newest_first(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        _sample_entry(dlq, "-first")
        _sample_entry(dlq, "-second")
        _sample_entry(dlq, "-third")
        entries = dlq.list_dead_letters()
        assert entries[0]["task_id"] == "sdd-apply-auth-third"
        assert entries[-1]["task_id"] == "sdd-apply-auth-first"

    def test_list_respects_limit(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        for i in range(5):
            _sample_entry(dlq, f"-{i}")
        entries = dlq.list_dead_letters(limit=3)
        assert len(entries) == 3

    def test_list_default_limit_is_20(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        for i in range(25):
            _sample_entry(dlq, f"-{i}")
        entries = dlq.list_dead_letters()
        assert len(entries) == 20

    def test_list_returns_all_fields(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        _sample_entry(dlq)
        entry = dlq.list_dead_letters()[0]
        for field in ("entry_id", "task_id", "description", "failure_type",
                      "retry_history", "diagnosis", "status", "enqueued_at"):
            assert field in entry


# ---------------------------------------------------------------------------
# Tests: requeue_dead_letter
# ---------------------------------------------------------------------------


class TestRequeue:
    def test_requeue_marks_status_as_requeued(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        original = _sample_entry(dlq)
        updated = dlq.requeue_dead_letter(original["entry_id"])
        assert updated["status"] == "requeued"

    def test_requeue_sets_requeued_at(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        original = _sample_entry(dlq)
        updated = dlq.requeue_dead_letter(original["entry_id"])
        assert updated["requeued_at"] is not None
        assert "T" in updated["requeued_at"]

    def test_requeue_writes_new_line_to_jsonl(self, tmp_path):
        dlq, dlq_file = _make_dlq(tmp_path)
        original = _sample_entry(dlq)
        dlq.requeue_dead_letter(original["entry_id"])
        lines = dlq_file.read_text().strip().splitlines()
        assert len(lines) == 2  # original + requeue record

    def test_requeue_preserves_original_fields(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        original = _sample_entry(dlq)
        updated = dlq.requeue_dead_letter(original["entry_id"])
        assert updated["task_id"] == original["task_id"]
        assert updated["diagnosis"] == original["diagnosis"]
        assert updated["failure_type"] == original["failure_type"]

    def test_requeue_unknown_entry_id_raises_key_error(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        with pytest.raises(KeyError, match="not-a-real-id"):
            dlq.requeue_dead_letter("not-a-real-id")

    def test_requeue_entry_appears_in_list(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        original = _sample_entry(dlq)
        dlq.requeue_dead_letter(original["entry_id"])
        all_entries = dlq.list_dead_letters(limit=100)
        statuses = {e["status"] for e in all_entries}
        assert "requeued" in statuses


# ---------------------------------------------------------------------------
# Tests: format_dlq_report
# ---------------------------------------------------------------------------


class TestFormatReport:
    def test_empty_report_message(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        report = dlq.format_dlq_report()
        assert "empty" in report.lower()

    def test_report_contains_header(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        _sample_entry(dlq)
        report = dlq.format_dlq_report()
        assert "Dead Letter Queue" in report

    def test_report_shows_task_id(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        _sample_entry(dlq)
        report = dlq.format_dlq_report()
        assert "sdd-apply-auth" in report

    def test_report_shows_failure_type(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        _sample_entry(dlq)
        report = dlq.format_dlq_report()
        assert "BUILD_ERROR" in report

    def test_report_shows_counts(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        _sample_entry(dlq, "-a")
        _sample_entry(dlq, "-b")
        original = _sample_entry(dlq, "-c")
        dlq.requeue_dead_letter(original["entry_id"])
        report = dlq.format_dlq_report()
        # 3 dead + 1 requeued record = 4 total lines written
        assert "dead" in report.lower()
        assert "requeued" in report.lower()

    def test_report_diagnosis_shown(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        _sample_entry(dlq)
        report = dlq.format_dlq_report()
        assert "go.mod" in report


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_non_existent_dlq_file_list_returns_empty(self, tmp_path):
        from lib.dead_letter_queue import DeadLetterQueue

        dlq = DeadLetterQueue(dlq_file=tmp_path / "nonexistent.jsonl")
        assert dlq.list_dead_letters() == []

    def test_empty_retry_history_accepted(self, tmp_path):
        dlq, _ = _make_dlq(tmp_path)
        entry = dlq.enqueue_dead_letter(
            task_id="minimal",
            description="desc",
            failure_type="UNKNOWN",
            retry_history=[],
            diagnosis="none",
        )
        assert entry["retry_history"] == []

    def test_dlq_creates_parent_directories(self, tmp_path):
        from lib.dead_letter_queue import DeadLetterQueue

        deep_file = tmp_path / "a" / "b" / "c" / "dlq.jsonl"
        dlq = DeadLetterQueue(dlq_file=deep_file)
        _sample_entry(dlq)
        assert deep_file.exists()
