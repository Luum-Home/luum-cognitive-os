"""Tests for lib/request_queue.py — user request persistence queue."""

import json
from pathlib import Path

import pytest

from lib.request_queue import (
    enqueue_request,
    get_all_requests,
    get_pending_requests,
    mark_done,
    format_pending_summary,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def queue_dir(tmp_path):
    """Provide a temp session directory for queue tests."""
    session_dir = tmp_path / "sessions" / "test-session"
    session_dir.mkdir(parents=True)
    return str(session_dir)


class TestEnqueue:
    def test_creates_file(self, queue_dir):
        enqueue_request("test message", session_dir=queue_dir)
        path = Path(queue_dir) / "user-requests.jsonl"
        assert path.exists()

    def test_appends_entry(self, queue_dir):
        enqueue_request("first", session_dir=queue_dir)
        enqueue_request("second", session_dir=queue_dir)
        path = Path(queue_dir) / "user-requests.jsonl"
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_entry_has_required_fields(self, queue_dir):
        entry = enqueue_request("test msg", session_dir=queue_dir)
        assert "timestamp" in entry
        assert entry["message"] == "test msg"
        assert entry["status"] == "pending"

    def test_caps_long_messages(self, queue_dir):
        long_msg = "x" * 5000
        entry = enqueue_request(long_msg, session_dir=queue_dir)
        assert len(entry["message"]) == 2000

    def test_valid_jsonl(self, queue_dir):
        enqueue_request("test", session_dir=queue_dir)
        path = Path(queue_dir) / "user-requests.jsonl"
        lines = path.read_text().splitlines()
        assert len(lines) >= 1, "enqueue_request must write at least one JSONL line"
        for line in lines:
            entry = json.loads(line)  # must parse without raising
            assert isinstance(entry, dict), f"each JSONL line must be a JSON object, got: {type(entry)}"
            assert "message" in entry, f"each entry must have a 'message' key, keys={list(entry)}"


class TestGetPending:
    def test_empty_queue(self, queue_dir):
        assert get_pending_requests(session_dir=queue_dir) == []

    def test_returns_only_pending(self, queue_dir):
        enqueue_request("pending one", session_dir=queue_dir)
        enqueue_request("pending two", session_dir=queue_dir)
        enqueue_request("done one", session_dir=queue_dir, status="done")
        pending = get_pending_requests(session_dir=queue_dir)
        assert len(pending) == 2
        assert all(p["status"] == "pending" for p in pending)

    def test_missing_file_returns_empty(self, queue_dir):
        assert get_pending_requests(session_dir=queue_dir + "/nonexistent") == []

    def test_handles_malformed_lines(self, queue_dir):
        path = Path(queue_dir) / "user-requests.jsonl"
        path.write_text('not json\n{"message":"valid","status":"pending","timestamp":"t"}\n')
        pending = get_pending_requests(session_dir=queue_dir)
        assert len(pending) == 1


class TestMarkDone:
    def test_marks_matching_request(self, queue_dir):
        enqueue_request("fix the bug in auth", session_dir=queue_dir)
        result = mark_done("fix the bug", session_dir=queue_dir)
        assert result is True
        pending = get_pending_requests(session_dir=queue_dir)
        assert len(pending) == 0

    def test_returns_false_if_no_match(self, queue_dir):
        enqueue_request("something else", session_dir=queue_dir)
        result = mark_done("nonexistent", session_dir=queue_dir)
        assert result is False

    def test_marks_only_first_match(self, queue_dir):
        enqueue_request("fix auth", session_dir=queue_dir)
        enqueue_request("fix auth again", session_dir=queue_dir)
        mark_done("fix auth", session_dir=queue_dir)
        pending = get_pending_requests(session_dir=queue_dir)
        assert len(pending) == 1
        assert pending[0]["message"] == "fix auth again"

    def test_missing_file_returns_false(self, queue_dir):
        assert mark_done("anything", session_dir=queue_dir + "/nope") is False


class TestGetAll:
    def test_returns_all_statuses(self, queue_dir):
        enqueue_request("pending", session_dir=queue_dir)
        enqueue_request("done", session_dir=queue_dir, status="done")
        enqueue_request("deferred", session_dir=queue_dir, status="deferred")
        all_reqs = get_all_requests(session_dir=queue_dir)
        assert len(all_reqs) == 3


class TestFormatSummary:
    def test_no_pending(self, queue_dir):
        result = format_pending_summary(session_dir=queue_dir)
        assert "No pending" in result

    def test_formats_pending(self, queue_dir):
        enqueue_request("fix the auth bug", session_dir=queue_dir)
        enqueue_request("add tests for login", session_dir=queue_dir)
        result = format_pending_summary(session_dir=queue_dir)
        assert "2 pending" in result
        assert "fix the auth" in result
        assert "add tests" in result

    def test_truncates_long_messages(self, queue_dir):
        enqueue_request("x" * 200, session_dir=queue_dir)
        result = format_pending_summary(session_dir=queue_dir)
        assert "..." in result
