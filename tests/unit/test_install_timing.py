# SCOPE: os-only
"""tests/unit/test_install_timing.py — Unit tests for lib/install_timing.py.

Fast, isolated tests that verify the JSONL logger's correctness:
real file writes to tmp_path, parse-back asserts, shape verification.

For the full contract / regression guard (ADR-059 exit criteria) see:
  tests/contracts/test_install_timing.py
"""

from __future__ import annotations

import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lib.install_timing import (
    append_install_record,
    read_records,
    within_budget,
)

# Inline the set in case the import above is syntactically awkward
_REQUIRED_FIELDS = {
    "timestamp",
    "profile",
    "elapsed_s",
    "manual_steps",
    "errors",
    "docker_required",
    "final_hook_count",
    "exit_code",
}


def test_logger_writes_valid_jsonl_and_parses_back(tmp_path: Path) -> None:
    """End-to-end: write a record, read it back, assert shape and values."""
    jsonl = tmp_path / "metrics" / "install-timing.jsonl"

    append_install_record(
        elapsed_s=75,
        profile="--standard",
        manual_steps=0,
        errors=0,
        docker_required=0,
        final_hook_count=67,
        exit_code=0,
        jsonl_path=str(jsonl),
    )

    # File must exist and be non-empty
    assert jsonl.exists()
    raw = jsonl.read_text(encoding="utf-8").strip()
    assert len(raw) > 0

    # Every line must be valid JSON
    obj = json.loads(raw)

    # Shape check
    assert _REQUIRED_FIELDS.issubset(obj.keys()), (
        f"Missing fields: {_REQUIRED_FIELDS - obj.keys()}"
    )

    # Value round-trip
    assert obj["elapsed_s"] == 75
    assert obj["profile"] == "--standard"
    assert obj["final_hook_count"] == 67
    assert obj["exit_code"] == 0

    # read_records must return same data
    records = read_records(jsonl_path=str(jsonl))
    assert len(records) == 1
    assert records[0]["elapsed_s"] == 75


def test_logger_appends_multiple_records(tmp_path: Path) -> None:
    """Multiple calls must produce multiple lines (append-only invariant)."""
    jsonl = tmp_path / "install-timing.jsonl"

    for elapsed in (10, 20, 30, 40, 50):
        append_install_record(elapsed_s=elapsed, jsonl_path=str(jsonl))

    lines = jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5

    for i, line in enumerate(lines):
        record = json.loads(line)
        assert record["elapsed_s"] == (i + 1) * 10


def test_within_budget_gate(tmp_path: Path) -> None:
    """within_budget must correctly apply ADR-059 §Phase 2 thresholds."""
    good = append_install_record(
        elapsed_s=120, manual_steps=0, errors=0,
        jsonl_path=str(tmp_path / "t.jsonl"),
    )
    assert within_budget(good) is True

    bad_time = {**good, "elapsed_s": 300}
    assert within_budget(bad_time) is False

    bad_errors = {**good, "errors": 1}
    assert within_budget(bad_errors) is False

    bad_steps = {**good, "manual_steps": 4}
    assert within_budget(bad_steps) is False


def test_missing_jsonl_returns_empty_list(tmp_path: Path) -> None:
    """read_records on a nonexistent file must return [] without raising."""
    records = read_records(jsonl_path=str(tmp_path / "ghost.jsonl"))
    assert records == []


def test_timestamp_format(tmp_path: Path) -> None:
    """Timestamps must be UTC ISO-8601 strings (Z suffix, T separator)."""
    import re
    jsonl = tmp_path / "ts-test.jsonl"
    record = append_install_record(elapsed_s=1, jsonl_path=str(jsonl))
    ts = record["timestamp"]
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    assert re.match(pattern, ts), f"Unexpected timestamp format: {ts!r}"
