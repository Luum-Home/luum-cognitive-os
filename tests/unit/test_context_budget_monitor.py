from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from lib.context_budget_monitor import build_report

pytestmark = pytest.mark.unit


def write_rows(project: Path, rows: list[dict]) -> None:
    path = project / ".cognitive-os" / "metrics" / "context-budget.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def row(verdict: str, *, source: str = "context-budget-meter", ts: float = 1000.0, latency_ms: float = 1.0, reason: str = "", allowed: bool = True) -> dict:
    return {
        "timestamp_epoch": ts,
        "source": source,
        "verdict": verdict,
        "ratio_used": 0.5,
        "latency_ms": latency_ms,
        "reason": reason,
        "allowed": allowed,
    }


def test_empty_report_warns(tmp_path: Path) -> None:
    report = build_report(tmp_path, now_epoch=1000.0)
    assert report.status == "warn"
    assert report.total_entries == 0
    assert report.findings


def test_green_report_passes(tmp_path: Path) -> None:
    rows = [row("PASS", ts=1000.0 + i, latency_ms=2.0) for i in range(95)]
    rows += [row("WARN", ts=1100.0 + i, source="skill-router-prompt-suggest") for i in range(5)]
    write_rows(tmp_path, rows)
    report = build_report(tmp_path, now_epoch=1200.0)
    assert report.status == "pass"
    assert report.pass_rate == 0.95
    assert report.warn_rate == 0.05
    assert report.block_rate == 0.0
    assert report.meter_p99_ms == 2.0


def test_slo_violations_are_findings(tmp_path: Path) -> None:
    rows = [row("PASS", ts=1000.0 + i) for i in range(80)]
    rows += [row("WARN", ts=1100.0 + i) for i in range(10)]
    rows += [row("BLOCK", ts=1200.0 + i, reason="override", allowed=True, latency_ms=50.0) for i in range(10)]
    write_rows(tmp_path, rows)
    report = build_report(tmp_path, now_epoch=1300.0)
    assert report.status == "warn"
    assert any("PASS rate" in finding for finding in report.findings)
    assert any("WARN rate" in finding for finding in report.findings)
    assert any("BLOCK rate" in finding for finding in report.findings)
    assert any("override rate" in finding for finding in report.findings)
    assert any("p99" in finding for finding in report.findings)


def test_window_filters_old_rows(tmp_path: Path) -> None:
    now = time.time()
    write_rows(tmp_path, [row("BLOCK", ts=now - 40 * 86400), row("PASS", ts=now)])
    report = build_report(tmp_path, window_days=30, now_epoch=now)
    assert report.total_entries == 1
    assert report.verdict_counts == {"PASS": 1}
