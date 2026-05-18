"""Tests for lib/single_writer_metric.py (ADR-121 Phase 2 metric gap)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.single_writer_metric import record_push_attempt


@pytest.fixture()
def metric_path(tmp_path: Path) -> Path:
    return tmp_path / "metrics" / "single-writer-enforcement.jsonl"


def test_record_creates_file_and_appends(metric_path: Path) -> None:
    record_push_attempt("sess-1", "main", "allowed", metric_file=metric_path)
    assert metric_path.exists()
    lines = metric_path.read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["session_id"] == "sess-1"
    assert row["branch"] == "main"
    assert row["outcome"] == "allowed"
    assert "timestamp" in row
    assert row["actor"] == "agent"


def test_multiple_records_appended(metric_path: Path) -> None:
    for outcome in ("allowed", "blocked", "queued"):
        record_push_attempt("sess-2", "main", outcome, metric_file=metric_path)
    lines = metric_path.read_text().splitlines()
    assert len(lines) == 3
    outcomes = [json.loads(l)["outcome"] for l in lines]
    assert outcomes == ["allowed", "blocked", "queued"]


def test_reason_field_optional(metric_path: Path) -> None:
    record_push_attempt("sess-3", "main", "blocked", metric_file=metric_path)
    row = json.loads(metric_path.read_text())
    assert "reason" not in row


def test_reason_field_present_when_supplied(metric_path: Path) -> None:
    record_push_attempt(
        "sess-4", "main", "bypassed", reason="operator emergency", metric_file=metric_path
    )
    row = json.loads(metric_path.read_text())
    assert row["reason"] == "operator emergency"


def test_operator_actor(metric_path: Path) -> None:
    record_push_attempt("sess-5", "main", "bypassed", actor="operator", metric_file=metric_path)
    row = json.loads(metric_path.read_text())
    assert row["actor"] == "operator"


def test_returns_written_dict(metric_path: Path) -> None:
    result = record_push_attempt("sess-6", "main", "queued", metric_file=metric_path)
    assert isinstance(result, dict)
    assert result["outcome"] == "queued"
    assert result["session_id"] == "sess-6"


def test_parent_dirs_created(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c" / "metric.jsonl"
    record_push_attempt("sess-7", "main", "allowed", metric_file=deep)
    assert deep.exists()


def test_invalid_outcome_rejected(metric_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid single-writer outcome"):
        record_push_attempt("sess-8", "main", "unknown", metric_file=metric_path)  # type: ignore[arg-type]
    assert not metric_path.exists()
