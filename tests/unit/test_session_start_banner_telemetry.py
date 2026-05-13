"""Unit tests for lib.telemetry_banner (ADR-304 Slice 2)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.telemetry_banner import render_banner  # noqa: E402


def _write_snapshot(path: Path, generated_at: str, findings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "telemetry-aggregator/v1",
                "generated_at": generated_at,
                "findings": findings,
            }
        )
    )


def test_banner_shows_top_3_findings(tmp_path: Path):
    now = datetime(2026, 5, 13, 22, 0, 0, tzinfo=timezone.utc)
    snap = tmp_path / "snap.yaml"
    findings = [
        {
            "slo_id": "session-start-blocking-total",
            "metric_value": 2496,
            "target": 2000,
            "target_comparator": "<",
            "severity": "warn",
            "code": "telemetry-slo-breach",
            "stable_id": "abc",
            "timestamp": "2026-05-13T22:00:00Z",
            "rationale": "r",
            "window_summary": {},
            "message": "",
        },
        {
            "slo_id": "subagent-spawn-p95",
            "metric_value": 55620,
            "target": 5000,
            "target_comparator": "<",
            "severity": "warn",
            "code": "telemetry-slo-breach",
            "stable_id": "def",
            "timestamp": "2026-05-13T22:00:00Z",
            "rationale": "r",
            "window_summary": {},
            "message": "",
        },
        {
            "slo_id": "llm-dispatch-success-ratio",
            "metric_value": 0.5,
            "target": 0.85,
            "target_comparator": ">=",
            "severity": "warn",
            "code": "telemetry-slo-breach",
            "stable_id": "ghi",
            "timestamp": "2026-05-13T22:00:00Z",
            "rationale": "r",
            "window_summary": {},
            "message": "",
        },
        {
            "slo_id": "extra",
            "metric_value": 1,
            "target": 0,
            "target_comparator": "<",
            "severity": "info",
            "code": "telemetry-slo-breach",
            "stable_id": "jkl",
            "timestamp": "2026-05-13T22:00:00Z",
            "rationale": "r",
            "window_summary": {},
            "message": "",
        },
    ]
    _write_snapshot(snap, "2026-05-13T21:30:00Z", findings)
    banner = render_banner(snap, top_n=3, now=now)
    assert "Performance findings" in banner
    assert "session-start-blocking-total" in banner
    assert "subagent-spawn-p95" in banner
    assert "llm-dispatch-success-ratio" in banner
    assert "extra" not in banner
    assert "cos-telemetry-aggregate" in banner


def test_banner_silent_when_snapshot_missing(tmp_path: Path):
    banner = render_banner(tmp_path / "nope.yaml")
    assert banner == ""


def test_banner_silent_when_snapshot_stale(tmp_path: Path):
    now = datetime(2026, 5, 13, 22, 0, 0, tzinfo=timezone.utc)
    stale = (now - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = tmp_path / "snap.yaml"
    _write_snapshot(
        snap,
        stale,
        [
            {
                "slo_id": "x",
                "metric_value": 1,
                "target": 0,
                "target_comparator": "<",
                "severity": "warn",
                "code": "telemetry-slo-breach",
                "stable_id": "a",
                "timestamp": stale,
                "rationale": "r",
                "window_summary": {},
                "message": "",
            }
        ],
    )
    assert render_banner(snap, max_age_hours=2.0, now=now) == ""


def test_banner_renders_correctly_with_zero_findings(tmp_path: Path):
    now = datetime(2026, 5, 13, 22, 0, 0, tzinfo=timezone.utc)
    snap = tmp_path / "snap.yaml"
    _write_snapshot(snap, "2026-05-13T21:30:00Z", [])
    assert render_banner(snap, now=now) == ""


def test_banner_suppresses_info_only_findings(tmp_path: Path):
    now = datetime(2026, 5, 13, 22, 0, 0, tzinfo=timezone.utc)
    snap = tmp_path / "snap.yaml"
    _write_snapshot(
        snap,
        "2026-05-13T21:30:00Z",
        [
            {
                "slo_id": "missing",
                "metric_value": None,
                "target": None,
                "target_comparator": "info",
                "severity": "info",
                "code": "telemetry-stream-missing",
                "stable_id": "a",
                "timestamp": "2026-05-13T21:30:00Z",
                "rationale": "r",
                "window_summary": {},
                "message": "",
            }
        ],
    )
    assert render_banner(snap, now=now) == ""
