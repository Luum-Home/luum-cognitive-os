"""Unit tests for lib/notification_digest.py"""
import pytest
from lib.notification_digest import NotificationDigest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(n: int = 1, status: str = "completed") -> NotificationDigest:
    d = NotificationDigest()
    for i in range(n):
        d.add(
            f"task-{i}",
            f"Task number {i} with a longer description text",
            status,
            f"Did something useful number {i}",
            duration_ms=60_000 + i * 1_000,
            tool_uses=10 + i,
            tests={"passed": 5, "failed": 0, "xfail": 1},
        )
    return d


# ---------------------------------------------------------------------------
# count / add
# ---------------------------------------------------------------------------

def test_add_single():
    d = NotificationDigest()
    d.add("t1", "Task 1", "completed")
    assert d.count() == 1


def test_add_multiple():
    d = _make(5)
    assert d.count() == 5


# ---------------------------------------------------------------------------
# has_failures
# ---------------------------------------------------------------------------

def test_has_failures_false():
    d = _make(3, status="completed")
    assert not d.has_failures()


def test_has_failures_true():
    d = _make(2, status="completed")
    d.add("bad", "Broken task", "failed", "something went wrong")
    assert d.has_failures()


# ---------------------------------------------------------------------------
# format_digest
# ---------------------------------------------------------------------------

def test_format_digest_header():
    d = _make(3)
    assert "AGENT DIGEST" in d.format_digest()


def test_format_digest_success_icon():
    d = _make(2, status="completed")
    digest = d.format_digest()
    assert "✅" in digest


def test_format_digest_failure_icon():
    d = NotificationDigest()
    d.add("f1", "Failed task", "failed", "exploded")
    digest = d.format_digest()
    assert "❌" in digest


def test_format_digest_summary_truncation():
    d = NotificationDigest()
    long_summary = "x" * 200
    d.add("t1", "Short description", "completed", long_summary)
    digest = d.format_digest()
    # truncated summary must end with "..."
    assert "..." in digest


def test_format_digest_under_1000_tokens():
    """10 notifications must produce a digest under ~4000 chars."""
    d = NotificationDigest()
    for i in range(10):
        d.add(
            f"task-{i}",
            f"Task number {i} with long description that goes on and on",
            "completed",
            f"Did something very useful for task number {i} and it was great",
            duration_ms=60_000 + i * 1_000,
            tool_uses=10 + i,
        )
    assert len(d.format_digest()) < 4_000


def test_format_digest_totals():
    d = _make(3)
    digest = d.format_digest()
    assert "Total duration" in digest
    assert "Total tool calls" in digest


def test_format_digest_tests():
    d = _make(2)
    digest = d.format_digest()
    assert "Tests:" in digest
    assert "passed" in digest


def test_format_digest_no_tests_section_when_empty():
    d = NotificationDigest()
    d.add("t1", "Task", "completed", "ok", 1000, 5)  # no tests kwarg
    digest = d.format_digest()
    assert "Tests:" not in digest


# ---------------------------------------------------------------------------
# format_single
# ---------------------------------------------------------------------------

def test_format_single():
    d = _make(3)
    single = d.format_single()
    # Last entry (index -1) should be task-2
    assert "task-2" not in single  # task_id not shown, description is
    assert "✅" in single or "❌" in single


def test_format_single_explicit_index():
    d = _make(3)
    first = d.format_single(0)
    assert "Task number 0" in first


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

def test_clear():
    d = _make(5)
    d.clear()
    assert d.count() == 0


# ---------------------------------------------------------------------------
# serialization roundtrip
# ---------------------------------------------------------------------------

def test_serialization_roundtrip():
    original = _make(4)
    data = original.to_dict()
    restored = NotificationDigest.from_dict(data)

    assert restored.count() == original.count()
    assert restored.has_failures() == original.has_failures()
    assert restored.format_digest() == original.format_digest()


# ---------------------------------------------------------------------------
# empty digest
# ---------------------------------------------------------------------------

def test_empty_digest():
    d = NotificationDigest()
    result = d.format_digest()
    assert "AGENT DIGEST" in result
    assert "0" in result
