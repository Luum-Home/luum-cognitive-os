"""Unit tests for self-tuning proposer (ADR-304 Slice 3)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.telemetry_aggregator import aggregate_streams  # noqa: E402


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


def _write_manifest(repo: Path, slos: list[dict]) -> Path:
    path = repo / "manifests/observability-slo.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"schema_version": "observability-slo/v1", "slos": slos})
    )
    return path


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    (tmp_path / ".cognitive-os/metrics").mkdir(parents=True)
    (tmp_path / ".cognitive-os/tasks").mkdir(parents=True)
    return tmp_path


def _seed_breach_records(repo: Path, with_stdout: bool, stdout_bytes: int = 0):
    records = []
    for i in range(1, 101):
        rec = {
            "hook": "subagent-context-injector",
            "duration_ms": 60000,  # blow past 5s SLO
            "event": "PreToolUse",
        }
        if with_stdout:
            rec["stdout_bytes"] = stdout_bytes
        records.append(rec)
    _write_jsonl(repo / ".cognitive-os/metrics/hook-timing.jsonl", records)


SLO_DEF = {
    "id": "subagent-spawn-p95",
    "source_stream": ".cognitive-os/metrics/hook-timing.jsonl",
    "filter": 'hook == "subagent-context-injector"',
    "metric": "percentile(duration_ms, 0.95)",
    "window": "last_200_records",
    "target_lt": 5000,
    "severity_on_breach": "warn",
    "rationale": "ADR-303",
}


def _seed_history(queue: Path, slo_id: str, n_windows: int):
    """Seed queue with prior breach records across distinct hourly buckets."""
    queue.parent.mkdir(parents=True, exist_ok=True)
    with queue.open("w") as fh:
        for hr in range(n_windows):
            rec = {
                "adr": "ADR-304",
                "audit_id": "telemetry-aggregator",
                "code": "telemetry-slo-breach",
                "created_at": f"2026-05-13T{hr:02d}:00:00Z",
                "slo_id": slo_id,
                "stable_id": f"prior-{hr}",
                "schema_version": "control-plane-remediation/v1",
                "severity": "warn",
                "status": "queued",
            }
            fh.write(json.dumps(rec) + "\n")


def test_proposal_emitted_after_3_consecutive_breaches(tmp_repo: Path):
    _seed_breach_records(tmp_repo, with_stdout=True, stdout_bytes=0)
    manifest = _write_manifest(tmp_repo, [SLO_DEF])
    queue = tmp_repo / ".cognitive-os/tasks/control-plane-remediation.jsonl"
    _seed_history(queue, "subagent-spawn-p95", n_windows=2)
    now = datetime(2026, 5, 13, 23, 0, 0, tzinfo=timezone.utc)
    report = aggregate_streams(
        tmp_repo, manifest, now=now, remediation_queue=queue
    )
    proposals = [
        f for f in report.findings if f.code == "telemetry-self-tuning-proposal"
    ]
    assert len(proposals) == 1
    p = proposals[0]
    assert "subagent-context-injector" in p.message
    assert "scripts/_lib/settings-driver-claude-code.sh" in p.message


def test_no_proposal_when_hook_emits_stdout(tmp_repo: Path):
    _seed_breach_records(tmp_repo, with_stdout=True, stdout_bytes=128)
    manifest = _write_manifest(tmp_repo, [SLO_DEF])
    queue = tmp_repo / ".cognitive-os/tasks/control-plane-remediation.jsonl"
    _seed_history(queue, "subagent-spawn-p95", n_windows=2)
    now = datetime(2026, 5, 13, 23, 0, 0, tzinfo=timezone.utc)
    report = aggregate_streams(
        tmp_repo, manifest, now=now, remediation_queue=queue
    )
    proposals = [
        f for f in report.findings if f.code == "telemetry-self-tuning-proposal"
    ]
    assert proposals == []


def test_no_proposal_when_stdout_bytes_field_missing(tmp_repo: Path):
    _seed_breach_records(tmp_repo, with_stdout=False)
    manifest = _write_manifest(tmp_repo, [SLO_DEF])
    queue = tmp_repo / ".cognitive-os/tasks/control-plane-remediation.jsonl"
    _seed_history(queue, "subagent-spawn-p95", n_windows=2)
    now = datetime(2026, 5, 13, 23, 0, 0, tzinfo=timezone.utc)
    report = aggregate_streams(
        tmp_repo, manifest, now=now, remediation_queue=queue
    )
    proposals = [
        f for f in report.findings if f.code == "telemetry-self-tuning-proposal"
    ]
    assert proposals == []


def test_proposal_includes_concrete_change_block(tmp_repo: Path):
    _seed_breach_records(tmp_repo, with_stdout=True, stdout_bytes=0)
    manifest = _write_manifest(tmp_repo, [SLO_DEF])
    queue = tmp_repo / ".cognitive-os/tasks/control-plane-remediation.jsonl"
    _seed_history(queue, "subagent-spawn-p95", n_windows=2)
    now = datetime(2026, 5, 13, 23, 0, 0, tzinfo=timezone.utc)
    report = aggregate_streams(
        tmp_repo, manifest, now=now, remediation_queue=queue
    )
    proposals = [
        f for f in report.findings if f.code == "telemetry-self-tuning-proposal"
    ]
    assert len(proposals) == 1
    ws = proposals[0].window_summary
    assert ws["proposed_change"]["file"] == "scripts/_lib/settings-driver-claude-code.sh"
    assert ws["proposed_change"]["hook"] == "subagent-context-injector.sh"
    assert ws["proposed_change"]["from"] == "false"
    assert ws["proposed_change"]["to"] == "true"
    assert "apply-efficiency-profile.sh" in ws["manual_application_command"]


def test_proposal_dedup_via_stable_id(tmp_repo: Path):
    _seed_breach_records(tmp_repo, with_stdout=True, stdout_bytes=0)
    manifest = _write_manifest(tmp_repo, [SLO_DEF])
    queue = tmp_repo / ".cognitive-os/tasks/control-plane-remediation.jsonl"
    _seed_history(queue, "subagent-spawn-p95", n_windows=2)
    now = datetime(2026, 5, 13, 23, 0, 0, tzinfo=timezone.utc)
    r1 = aggregate_streams(
        tmp_repo, manifest, now=now, remediation_queue=queue
    )
    r2 = aggregate_streams(
        tmp_repo, manifest, now=now, remediation_queue=queue
    )
    p1 = [f for f in r1.findings if f.code == "telemetry-self-tuning-proposal"][0]
    p2 = [f for f in r2.findings if f.code == "telemetry-self-tuning-proposal"][0]
    assert p1.stable_id == p2.stable_id
    assert p1.stable_id.startswith("telemetry-self-tune/")


def test_no_proposal_when_fewer_than_3_windows(tmp_repo: Path):
    _seed_breach_records(tmp_repo, with_stdout=True, stdout_bytes=0)
    manifest = _write_manifest(tmp_repo, [SLO_DEF])
    queue = tmp_repo / ".cognitive-os/tasks/control-plane-remediation.jsonl"
    _seed_history(queue, "subagent-spawn-p95", n_windows=1)  # only 1 prior + current = 2
    now = datetime(2026, 5, 13, 23, 0, 0, tzinfo=timezone.utc)
    report = aggregate_streams(
        tmp_repo, manifest, now=now, remediation_queue=queue
    )
    proposals = [
        f for f in report.findings if f.code == "telemetry-self-tuning-proposal"
    ]
    assert proposals == []
