"""Behavior tests for ADR-123-S1 friction telemetry report."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from lib.friction_telemetry import summarize

pytestmark = pytest.mark.behavior

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-friction-report"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def sample_rows() -> list[dict]:
    return [
        {"hook": "direct-main-guard", "exit_code": 2, "duration_ms": 100, "body_duration_ms": 80, "reason": "main push"},
        {"hook": "direct-main-guard", "exit_code": 2, "duration_ms": 120, "body_duration_ms": 90, "reason": "main push"},
        {"hook": "doc-sync-detector", "exit_code": 1, "execution_status": "error", "latency_ms": 50, "reason": "projection drift"},
        {"hook": "session-heartbeat", "exit_code": 0, "duration_ms": 10},
        {"hook": "adaptive-bypass", "outcome": "bypass", "duration_ms": 30},
        {"hook": "repair-helper", "outcome": "auto_repair", "duration_ms": 40},
    ]


def test_friction_summary_normalizes_block_warn_bypass_and_repair() -> None:
    report = summarize(sample_rows(), limit=5, false_positive_threshold=2)

    assert report["outcome_counts"] == {
        "auto_repair": 1,
        "block": 2,
        "bypass": 1,
        "observe": 1,
        "warn": 1,
    }
    assert report["top_blocking_hooks"] == [{"hook": "direct-main-guard", "count": 2}]
    assert report["top_warning_hooks"] == [{"hook": "doc-sync-detector", "count": 1}]
    assert report["top_bypass_hooks"] == [{"hook": "adaptive-bypass", "count": 1}]
    assert report["false_positive_candidates"] == [
        {"hook": "direct-main-guard", "outcome": "block", "reason": "main push", "count": 2}
    ]


def test_cos_friction_report_json_cli(tmp_path: Path) -> None:
    metrics = tmp_path / "hook-timing.jsonl"
    write_jsonl(metrics, sample_rows())

    result = subprocess.run(
        [str(SCRIPT), "--metrics", str(metrics), "--json", "--limit", "3"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "friction-telemetry.v1"
    assert payload["total_events"] == 6
    assert payload["top_blocking_hooks"][0]["hook"] == "direct-main-guard"


def test_cos_friction_report_text_cli(tmp_path: Path) -> None:
    metrics = tmp_path / "hook-timing.jsonl"
    write_jsonl(metrics, sample_rows())

    result = subprocess.run(
        [str(SCRIPT), "--metrics", str(metrics)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "COS Friction Report" in result.stdout
    assert "direct-main-guard" in result.stdout
    assert "False-positive candidates" in result.stdout
