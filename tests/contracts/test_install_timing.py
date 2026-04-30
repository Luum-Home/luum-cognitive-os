# SCOPE: os-only
"""tests/contracts/test_install_timing.py — Contract tests for install-timing tooling.

ADR-059 §Phase 2 exit criteria:
  - install-timing.jsonl accumulates records with required fields.
  - Records within budget (elapsed_s < 300, manual_steps <= 3, errors == 0).
  - lib/install_timing.py writes and reads back correct schema.

These tests run against the logger library itself (real writes to tmp_path).
They do NOT run the full end-to-end install (that is the job of make install-test).
"""

from __future__ import annotations

import json
from pathlib import Path


# Project root so we can import lib directly without install
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lib.install_timing import (
    BUDGET_ELAPSED_S,
    BUDGET_ERRORS,
    BUDGET_MANUAL_STEPS,
    append_install_record,
    read_records,
    within_budget,
)


# ── Schema tests ─────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {
    "timestamp",
    "profile",
    "elapsed_s",
    "manual_steps",
    "errors",
    "docker_required",
    "final_hook_count",
    "exit_code",
}


def test_append_creates_jsonl_and_returns_record(tmp_path: Path) -> None:
    """append_install_record must create the file and return the written record."""
    jsonl = tmp_path / "install-timing.jsonl"
    record = append_install_record(elapsed_s=42, jsonl_path=str(jsonl))

    assert jsonl.exists(), "JSONL file must be created"
    assert isinstance(record, dict), "Must return a dict"
    assert REQUIRED_FIELDS.issubset(record.keys()), (
        f"Missing fields: {REQUIRED_FIELDS - record.keys()}"
    )


def test_record_schema_types(tmp_path: Path) -> None:
    """All fields must have the correct types."""
    jsonl = tmp_path / "install-timing.jsonl"
    record = append_install_record(
        elapsed_s=120,
        profile="--minimal",
        manual_steps=1,
        errors=0,
        docker_required=0,
        final_hook_count=55,
        exit_code=0,
        jsonl_path=str(jsonl),
    )

    assert isinstance(record["timestamp"], str) and len(record["timestamp"]) > 0
    assert isinstance(record["profile"], str)
    assert isinstance(record["elapsed_s"], int)
    assert isinstance(record["manual_steps"], int)
    assert isinstance(record["errors"], int)
    assert isinstance(record["docker_required"], int)
    assert isinstance(record["final_hook_count"], int)
    assert isinstance(record["exit_code"], int)


def test_append_is_append_only(tmp_path: Path) -> None:
    """Multiple calls must accumulate records (append, not overwrite)."""
    jsonl = tmp_path / "install-timing.jsonl"

    for elapsed in [10, 20, 30]:
        append_install_record(elapsed_s=elapsed, jsonl_path=str(jsonl))

    records = read_records(jsonl_path=str(jsonl))
    assert len(records) == 3, f"Expected 3 records, got {len(records)}"
    assert [r["elapsed_s"] for r in records] == [10, 20, 30]


def test_read_records_parses_valid_json(tmp_path: Path) -> None:
    """read_records must parse every line as a valid JSON object."""
    jsonl = tmp_path / "install-timing.jsonl"
    append_install_record(elapsed_s=99, jsonl_path=str(jsonl))

    records = read_records(jsonl_path=str(jsonl))
    assert len(records) == 1
    assert records[0]["elapsed_s"] == 99


def test_read_records_empty_when_file_missing(tmp_path: Path) -> None:
    """read_records must return [] when the file does not exist."""
    missing = tmp_path / "nonexistent.jsonl"
    assert read_records(jsonl_path=str(missing)) == []


def test_jsonl_is_valid_json_lines(tmp_path: Path) -> None:
    """Each line in the JSONL file must be parseable JSON."""
    jsonl = tmp_path / "install-timing.jsonl"
    for i in range(5):
        append_install_record(elapsed_s=i * 10, jsonl_path=str(jsonl))

    lines = jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    for line in lines:
        obj = json.loads(line)
        assert REQUIRED_FIELDS.issubset(obj.keys())


# ── Budget / regression guard tests ──────────────────────────────────────────

def test_within_budget_passes_for_fast_clean_run() -> None:
    """A fast, clean install must pass the budget gate."""
    record = {
        "elapsed_s": 120,
        "manual_steps": 0,
        "errors": 0,
    }
    assert within_budget(record) is True


def test_within_budget_fails_when_elapsed_exceeds_limit() -> None:
    """elapsed_s >= 300 must fail the budget gate."""
    record = {"elapsed_s": BUDGET_ELAPSED_S, "manual_steps": 0, "errors": 0}
    assert within_budget(record) is False


def test_within_budget_fails_when_errors_nonzero() -> None:
    """Any error must fail the budget gate."""
    record = {"elapsed_s": 60, "manual_steps": 0, "errors": 1}
    assert within_budget(record) is False


def test_within_budget_fails_when_manual_steps_exceed_limit() -> None:
    """manual_steps > 3 must fail the budget gate."""
    record = {
        "elapsed_s": 60,
        "manual_steps": BUDGET_MANUAL_STEPS + 1,
        "errors": 0,
    }
    assert within_budget(record) is False


def test_budget_constants_match_adr059() -> None:
    """ADR-059 §Phase 2 specifies exact budget numbers — pin them."""
    assert BUDGET_ELAPSED_S == 300, "ADR-059: elapsed_s < 300"
    assert BUDGET_MANUAL_STEPS == 3, "ADR-059: manual_steps <= 3"
    assert BUDGET_ERRORS == 0, "ADR-059: errors == 0"


# ── Parent directory creation ─────────────────────────────────────────────────

def test_append_creates_parent_dirs(tmp_path: Path) -> None:
    """append_install_record must create intermediate directories."""
    nested = tmp_path / "a" / "b" / "c" / "install-timing.jsonl"
    record = append_install_record(elapsed_s=5, jsonl_path=str(nested))
    assert nested.exists()
    assert record["elapsed_s"] == 5
