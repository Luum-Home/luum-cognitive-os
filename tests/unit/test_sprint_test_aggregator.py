"""Unit tests for lib.sprint_test_aggregator (ADR-036 Wave 1)."""

from __future__ import annotations

import json
from pathlib import Path


from lib.sprint_test_aggregator import (
    aggregate,
    detect_recent_sessions,
    detect_regressions,
    detect_runner,
    parse_log,
    read_session_records,
    render_text,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_session(root: Path, sid: str, records: list[dict]) -> None:
    sdir = root / sid
    sdir.mkdir(parents=True, exist_ok=True)
    jsonl = sdir / "test-results.jsonl"
    with jsonl.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_aggregate_empty_returns_zero_totals(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    out = aggregate([], sessions_root=root)
    assert out["totals"] == {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    assert out["status"] == "pass"
    assert out["records"] == []


def test_aggregate_jsonl_records_sums_counts(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    _mk_session(
        root,
        "s1",
        [
            {"suite": "tests/unit/a", "runner": "pytest", "passed": 5, "failed": 1},
            {"suite": "tests/unit/b", "runner": "pytest", "passed": 3, "skipped": 2},
        ],
    )
    _mk_session(
        root,
        "s2",
        [{"suite": "tests/unit/a", "runner": "pytest", "passed": 6, "failed": 0}],
    )

    out = aggregate(["s1", "s2"], sessions_root=root)
    assert out["totals"]["passed"] == 14
    assert out["totals"]["failed"] == 1
    assert out["totals"]["skipped"] == 2
    assert out["status"] == "fail"  # one failure present
    # per-suite rollup
    assert out["per_suite"]["tests/unit/a"]["passed"] == 11
    assert out["per_suite"]["tests/unit/a"]["failed"] == 1


def test_detect_regressions_flags_pass_to_fail(tmp_path: Path) -> None:
    # s1: suite-a passes. s2: suite-a fails. -> regression from s1 to s2.
    records = [
        ("s1", [{"suite": "suite-a", "runner": "pytest", "passed": 3, "failed": 0}]),
        (
            "s2",
            [
                {
                    "suite": "suite-a",
                    "runner": "pytest",
                    "passed": 2,
                    "failed": 1,
                    "failures": ["suite-a::test_x"],
                }
            ],
        ),
    ]
    # detect_regressions works on normalized records (with failures key).
    # Hand-normalize by stuffing defaults.
    def _norm(session_id, raws):
        out = []
        for r in raws:
            out.append(
                {
                    "suite": r["suite"],
                    "runner": r.get("runner", "unknown"),
                    "passed": r.get("passed", 0),
                    "failed": r.get("failed", 0),
                    "skipped": r.get("skipped", 0),
                    "errors": r.get("errors", 0),
                    "failures": r.get("failures", []),
                    "session_id": session_id,
                }
            )
        return out

    normalized = [(sid, _norm(sid, recs)) for sid, recs in records]
    regressions = detect_regressions(normalized)
    assert len(regressions) == 1
    assert regressions[0]["suite"] == "suite-a"
    assert regressions[0]["from_session"] == "s1"
    assert regressions[0]["to_session"] == "s2"
    assert regressions[0]["failures_added"] == ["suite-a::test_x"]


def test_parse_log_pytest_summary_line() -> None:
    log = (
        "collected 8 items\n"
        "=========================== short test summary info ============================\n"
        "5 passed, 2 failed, 1 skipped in 0.42s\n"
    )
    rec = parse_log(log, suite_hint="task-abc")
    assert rec is not None
    assert rec["runner"] == "pytest"
    assert rec["passed"] == 5
    assert rec["failed"] == 2
    assert rec["skipped"] == 1
    assert rec["suite"] == "task-abc"


def test_parse_log_go_test_pass_fail_lines() -> None:
    log = (
        "=== RUN   TestAlpha\n"
        "--- PASS: TestAlpha (0.01s)\n"
        "=== RUN   TestBeta\n"
        "--- FAIL: TestBeta (0.02s)\n"
        "FAIL\n"
        "FAIL    example.com/pkg    0.12s\n"
    )
    rec = parse_log(log)
    assert rec is not None
    assert rec["runner"] == "go"
    assert rec["passed"] == 1
    assert rec["failed"] == 1
    assert "TestBeta" in rec["failures"]


def test_parse_log_jest_summary_line() -> None:
    log = "Test Suites: 1 passed, 1 total\nTests: 2 failed, 5 passed, 7 total\n"
    rec = parse_log(log, suite_hint="jest-run")
    assert rec is not None
    assert rec["runner"] == "jest"
    assert rec["failed"] == 2
    assert rec["passed"] == 5


def test_parse_log_unknown_returns_none() -> None:
    assert parse_log("just some random output with no test summary\n") is None


def test_detect_runner_variants() -> None:
    assert detect_runner("--- PASS: TestX (0.01s)\n") == "go"
    assert detect_runner("Tests: 3 passed, 3 total\n") == "jest"
    assert detect_runner("Test Files  2 passed (2)\n") == "vitest"
    assert detect_runner("random gibberish") == "unknown"


def test_read_session_records_fallback_to_task_logs(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    sdir = root / "s-fallback"
    (sdir / "metrics").mkdir(parents=True)
    (sdir / "metrics" / "task-agent1.log").write_text(
        "======== 4 passed, 1 failed in 0.1s ========\n",
        encoding="utf-8",
    )
    records = read_session_records("s-fallback", sessions_root=root)
    assert len(records) == 1
    assert records[0]["runner"] == "pytest"
    assert records[0]["passed"] == 4
    assert records[0]["failed"] == 1
    assert records[0]["suite"] == "task-agent1"
    assert records[0]["session_id"] == "s-fallback"


def test_detect_recent_sessions_sorts_by_epoch_prefix(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    for name in ["100-1-aaa", "300-3-ccc", "200-2-bbb"]:
        (root / name).mkdir()
    # hidden/dotfiles must be ignored
    (root / ".current-session-1").write_text("x")
    found = detect_recent_sessions(limit=5, sessions_root=root)
    assert found == ["300-3-ccc", "200-2-bbb", "100-1-aaa"]


def test_render_text_includes_totals_and_status(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    root.mkdir()
    _mk_session(
        root,
        "s1",
        [{"suite": "x", "runner": "pytest", "passed": 2, "failed": 0}],
    )
    out = aggregate(["s1"], sessions_root=root)
    text = render_text(out)
    assert "status=PASS" in text
    assert "passed=2" in text
    assert "regressions: none" in text


def test_aggregate_jsonl_takes_priority_over_fallback(tmp_path: Path) -> None:
    """If test-results.jsonl exists and has records, the task-*.log fallback
    MUST NOT be consulted (primary source wins)."""
    root = tmp_path / "sessions"
    sdir = root / "s-dual"
    (sdir / "metrics").mkdir(parents=True)
    # Fallback log would contribute 10 passed, but JSONL says 1 passed.
    (sdir / "metrics" / "task-x.log").write_text(
        "==== 10 passed in 0.1s ====\n", encoding="utf-8"
    )
    with (sdir / "test-results.jsonl").open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"suite": "primary", "runner": "pytest", "passed": 1}) + "\n")
    out = aggregate(["s-dual"], sessions_root=root)
    assert out["totals"]["passed"] == 1
    assert "primary" in out["per_suite"]
    assert "task-x" not in out["per_suite"]


def test_malformed_jsonl_lines_are_skipped(tmp_path: Path) -> None:
    root = tmp_path / "sessions"
    sdir = root / "s-bad"
    sdir.mkdir(parents=True)
    with (sdir / "test-results.jsonl").open("w", encoding="utf-8") as fh:
        fh.write("{not json}\n")
        fh.write(json.dumps({"suite": "ok", "runner": "pytest", "passed": 3}) + "\n")
        fh.write("\n")  # empty line
    out = aggregate(["s-bad"], sessions_root=root)
    assert out["totals"]["passed"] == 3
    assert "ok" in out["per_suite"]
