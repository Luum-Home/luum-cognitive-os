"""Unit tests for lib.telemetry_aggregator (ADR-304 Slice 1)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.telemetry_aggregator import (  # noqa: E402
    aggregate_streams,
    append_findings_idempotent,
    validate_slo_manifest,
    write_snapshot,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    (tmp_path / ".cognitive-os/metrics").mkdir(parents=True)
    (tmp_path / ".cognitive-os/tasks").mkdir(parents=True)
    (tmp_path / "manifests").mkdir(parents=True)
    return tmp_path


def _write_manifest(repo: Path, slos: list[dict]) -> Path:
    path = repo / "manifests/observability-slo.yaml"
    path.write_text(
        yaml.safe_dump({"schema_version": "observability-slo/v1", "slos": slos})
    )
    return path


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_slo_manifest_schema_strict():
    # Missing required field
    with pytest.raises(ValueError, match="missing fields"):
        validate_slo_manifest(
            {
                "schema_version": "observability-slo/v1",
                "slos": [{"id": "x", "source_stream": "foo"}],
            }
        )
    # Wrong schema version
    with pytest.raises(ValueError, match="schema_version"):
        validate_slo_manifest({"schema_version": "bad", "slos": []})
    # Both target_lt and target_gte
    with pytest.raises(ValueError, match="cannot declare both"):
        validate_slo_manifest(
            {
                "schema_version": "observability-slo/v1",
                "slos": [
                    {
                        "id": "x",
                        "source_stream": "foo",
                        "metric": "latest.x",
                        "severity_on_breach": "warn",
                        "rationale": "r",
                        "target_lt": 1,
                        "target_gte": 2,
                    }
                ],
            }
        )
    # Valid
    validate_slo_manifest(
        {
            "schema_version": "observability-slo/v1",
            "slos": [
                {
                    "id": "x",
                    "source_stream": "foo",
                    "metric": "latest.x",
                    "target_lt": 100,
                    "severity_on_breach": "warn",
                    "rationale": "r",
                }
            ],
        }
    )


def test_aggregator_skips_missing_streams_with_info_finding(tmp_repo: Path):
    manifest = _write_manifest(
        tmp_repo,
        [
            {
                "id": "missing-stream",
                "source_stream": ".cognitive-os/metrics/nope.jsonl",
                "metric": "latest.foo",
                "target_lt": 100,
                "severity_on_breach": "warn",
                "rationale": "r",
            }
        ],
    )
    report = aggregate_streams(tmp_repo, manifest, enable_self_tuning=False)
    assert len(report.findings) == 1
    f = report.findings[0]
    assert f.code == "telemetry-stream-missing"
    assert f.severity == "info"
    assert f.slo_id == "missing-stream"


def test_aggregator_emits_breach_finding_with_stable_id(tmp_repo: Path):
    _write_jsonl(
        tmp_repo / ".cognitive-os/metrics/startup-benchmark.jsonl",
        [{"session_start": {"blocking_total_ms": 9703, "total_duration_ms": 9703}}],
    )
    manifest = _write_manifest(
        tmp_repo,
        [
            {
                "id": "session-start-blocking-total",
                "source_stream": ".cognitive-os/metrics/startup-benchmark.jsonl",
                "metric": "latest.session_start.blocking_total_ms",
                "target_lt": 2000,
                "severity_on_breach": "warn",
                "rationale": "ADR-028",
            }
        ],
    )
    report = aggregate_streams(tmp_repo, manifest, enable_self_tuning=False)
    breaches = [f for f in report.findings if f.code == "telemetry-slo-breach"]
    assert len(breaches) == 1
    assert breaches[0].metric_value == 9703.0
    assert breaches[0].target == 2000.0
    assert breaches[0].target_comparator == "<"
    assert breaches[0].stable_id
    assert len(breaches[0].stable_id) == 16  # truncated sha256


def test_stable_id_dedupes_same_window(tmp_repo: Path):
    _write_jsonl(
        tmp_repo / ".cognitive-os/metrics/startup-benchmark.jsonl",
        [{"session_start": {"blocking_total_ms": 9703, "total_duration_ms": 9703}}],
    )
    manifest = _write_manifest(
        tmp_repo,
        [
            {
                "id": "session-start-blocking-total",
                "source_stream": ".cognitive-os/metrics/startup-benchmark.jsonl",
                "metric": "latest.session_start.blocking_total_ms",
                "target_lt": 2000,
                "severity_on_breach": "warn",
                "rationale": "r",
            }
        ],
    )
    fixed_now = datetime(2026, 5, 13, 22, 0, 0, tzinfo=timezone.utc)
    r1 = aggregate_streams(
        tmp_repo, manifest, now=fixed_now, enable_self_tuning=False
    )
    r2 = aggregate_streams(
        tmp_repo, manifest, now=fixed_now, enable_self_tuning=False
    )
    assert r1.findings[0].stable_id == r2.findings[0].stable_id


def test_percentile_filter_combination_for_subagent_p95(tmp_repo: Path):
    # 100 records of subagent-context-injector with growing durations.
    records = [
        {"hook": "subagent-context-injector", "duration_ms": i * 100, "event": "PreToolUse"}
        for i in range(1, 101)
    ]
    # Inject some noise from a different hook
    records += [
        {"hook": "other", "duration_ms": 99999, "event": "PreToolUse"} for _ in range(10)
    ]
    _write_jsonl(tmp_repo / ".cognitive-os/metrics/hook-timing.jsonl", records)
    manifest = _write_manifest(
        tmp_repo,
        [
            {
                "id": "subagent-spawn-p95",
                "source_stream": ".cognitive-os/metrics/hook-timing.jsonl",
                "filter": 'hook == "subagent-context-injector"',
                "metric": "percentile(duration_ms, 0.95)",
                "window": "last_200_records",
                "target_lt": 5000,
                "severity_on_breach": "warn",
                "rationale": "r",
            }
        ],
    )
    report = aggregate_streams(tmp_repo, manifest, enable_self_tuning=False)
    breaches = [f for f in report.findings if f.code == "telemetry-slo-breach"]
    assert len(breaches) == 1
    # p95 of [100..10000] step 100 = ~9500
    assert breaches[0].metric_value is not None
    assert 9000 <= breaches[0].metric_value <= 10000
    assert breaches[0].window_summary["n_samples"] >= 100
    assert "p95" in breaches[0].window_summary


def test_window_applies_after_filter_for_sparse_stream(tmp_repo: Path):
    records = [
        {"hook": "subagent-context-injector", "duration_ms": 1000, "event": "SubagentStart"},
        {"hook": "subagent-context-injector", "duration_ms": 6000, "event": "SubagentStart"},
        {"hook": "subagent-context-injector", "duration_ms": 10000, "event": "SubagentStart"},
    ]
    records += [
        {"hook": "other", "duration_ms": 1, "event": "PostToolUse"}
        for _ in range(100)
    ]
    _write_jsonl(tmp_repo / ".cognitive-os/metrics/hook-timing.jsonl", records)
    manifest = _write_manifest(
        tmp_repo,
        [
            {
                "id": "subagent-spawn-p95",
                "source_stream": ".cognitive-os/metrics/hook-timing.jsonl",
                "filter": 'event == "SubagentStart"',
                "metric": "percentile(duration_ms, 0.95)",
                "window": "last_3_records",
                "target_lt": 5000,
                "severity_on_breach": "warn",
                "rationale": "r",
            }
        ],
    )
    report = aggregate_streams(tmp_repo, manifest, enable_self_tuning=False)
    breaches = [f for f in report.findings if f.code == "telemetry-slo-breach"]
    assert len(breaches) == 1
    assert breaches[0].window_summary["n_samples"] == 3
    assert breaches[0].window_summary["n_matched_before_window"] == 3
    assert breaches[0].window_summary["n_records_read"] == 103


def test_remediation_queue_append_does_not_duplicate(tmp_repo: Path):
    _write_jsonl(
        tmp_repo / ".cognitive-os/metrics/startup-benchmark.jsonl",
        [{"session_start": {"blocking_total_ms": 9703, "total_duration_ms": 9703}}],
    )
    manifest = _write_manifest(
        tmp_repo,
        [
            {
                "id": "session-start-blocking-total",
                "source_stream": ".cognitive-os/metrics/startup-benchmark.jsonl",
                "metric": "latest.session_start.blocking_total_ms",
                "target_lt": 2000,
                "severity_on_breach": "warn",
                "rationale": "r",
            }
        ],
    )
    fixed_now = datetime(2026, 5, 13, 22, 0, 0, tzinfo=timezone.utc)
    queue = tmp_repo / ".cognitive-os/tasks/control-plane-remediation.jsonl"
    r1 = aggregate_streams(
        tmp_repo, manifest, now=fixed_now, enable_self_tuning=False
    )
    appended1, skipped1 = append_findings_idempotent(r1.findings, queue)
    appended2, skipped2 = append_findings_idempotent(r1.findings, queue)
    assert appended1 == 1
    assert skipped1 == 0
    assert appended2 == 0
    assert skipped2 == 1
    # Queue has exactly 1 line
    assert sum(1 for _ in queue.open()) == 1


def test_strict_mode_exits_2_on_any_breach(tmp_repo: Path):
    _write_jsonl(
        tmp_repo / ".cognitive-os/metrics/startup-benchmark.jsonl",
        [{"session_start": {"blocking_total_ms": 9703, "total_duration_ms": 9703}}],
    )
    _write_manifest(
        tmp_repo,
        [
            {
                "id": "session-start-blocking-total",
                "source_stream": ".cognitive-os/metrics/startup-benchmark.jsonl",
                "metric": "latest.session_start.blocking_total_ms",
                "target_lt": 2000,
                "severity_on_breach": "warn",
                "rationale": "r",
            }
        ],
    )
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/cos-telemetry-aggregate"),
            "--repo-root",
            str(tmp_repo),
            "--manifest",
            str(tmp_repo / "manifests/observability-slo.yaml"),
            "--snapshot",
            str(tmp_repo / "snap.yaml"),
            "--findings",
            str(tmp_repo / ".cognitive-os/tasks/control-plane-remediation.jsonl"),
            "--strict",
            "--no-self-tuning",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, result.stdout + result.stderr


def test_quiet_mode_silent_on_pass(tmp_repo: Path):
    _write_jsonl(
        tmp_repo / ".cognitive-os/metrics/startup-benchmark.jsonl",
        [{"session_start": {"blocking_total_ms": 100, "total_duration_ms": 100}}],
    )
    _write_manifest(
        tmp_repo,
        [
            {
                "id": "session-start-blocking-total",
                "source_stream": ".cognitive-os/metrics/startup-benchmark.jsonl",
                "metric": "latest.session_start.blocking_total_ms",
                "target_lt": 2000,
                "severity_on_breach": "warn",
                "rationale": "r",
            }
        ],
    )
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/cos-telemetry-aggregate"),
            "--repo-root",
            str(tmp_repo),
            "--manifest",
            str(tmp_repo / "manifests/observability-slo.yaml"),
            "--snapshot",
            str(tmp_repo / "snap.yaml"),
            "--findings",
            str(tmp_repo / ".cognitive-os/tasks/q.jsonl"),
            "--quiet",
            "--no-self-tuning",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_snapshot_yaml_is_well_formed(tmp_repo: Path):
    _write_jsonl(
        tmp_repo / ".cognitive-os/metrics/startup-benchmark.jsonl",
        [{"session_start": {"blocking_total_ms": 9703, "total_duration_ms": 9703}}],
    )
    manifest = _write_manifest(
        tmp_repo,
        [
            {
                "id": "session-start-blocking-total",
                "source_stream": ".cognitive-os/metrics/startup-benchmark.jsonl",
                "metric": "latest.session_start.blocking_total_ms",
                "target_lt": 2000,
                "severity_on_breach": "warn",
                "rationale": "r",
            }
        ],
    )
    report = aggregate_streams(tmp_repo, manifest, enable_self_tuning=False)
    snap = tmp_repo / "snap.yaml"
    write_snapshot(report, snap)
    parsed = yaml.safe_load(snap.read_text())
    assert parsed["schema_version"] == "telemetry-aggregator/v1"
    assert parsed["summary"]["n_breaches"] == 1
