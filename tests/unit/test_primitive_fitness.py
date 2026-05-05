"""Tests for primitive fitness comparison."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.primitive_fitness import build_report, collect_fitness_snapshot, compare_primitive_fitness

pytestmark = pytest.mark.unit


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def _metrics(root: Path, *, trust: int, successes: int, failures: int, hallucinations: int = 0) -> Path:
    metrics = root / ".cognitive-os" / "metrics"
    _write_jsonl(metrics / "trust-scores.jsonl", [{"score": trust, "uncertainties_count": 1}])
    _write_jsonl(
        metrics / "skill-metrics.jsonl",
        [{"skill": "candidate", "success": True} for _ in range(successes)]
        + [{"skill": "candidate", "success": False} for _ in range(failures)],
    )
    _write_jsonl(
        metrics / "hallucinations.jsonl",
        [{"hallucinations": hallucinations, "verified": 10}],
    )
    _write_jsonl(
        metrics / "llm-dispatch.jsonl",
        [
            {"success": True, "latency_ms": 1000, "cost_usd": 0.01},
            {"success": True, "latency_ms": 1200, "cost_usd": 0.01},
        ],
    )
    _write_jsonl(metrics / "hook-events.jsonl", [{"outcome": "observe", "hook": "unit"}])
    return metrics


def test_candidate_with_better_kpis_promotes(tmp_path: Path) -> None:
    baseline = _metrics(tmp_path / "baseline", trust=80, successes=3, failures=1)
    candidate = _metrics(tmp_path / "candidate", trust=92, successes=5, failures=0)

    report = build_report(
        primitive_id="skills/example",
        baseline_metrics=baseline,
        candidate_metrics=candidate,
        required_delta=1.0,
    )

    assert report.verdict == "promote"
    assert report.delta is not None and report.delta > 1.0
    assert report.safety_regressions == []
    assert report.baseline.scores["quality"] == 80
    assert report.candidate.scores["quality"] == 92


def test_safety_regression_blocks_even_when_quality_improves(tmp_path: Path) -> None:
    baseline = _metrics(tmp_path / "baseline", trust=80, successes=3, failures=1, hallucinations=0)
    candidate = _metrics(tmp_path / "candidate", trust=95, successes=5, failures=0, hallucinations=2)

    report = build_report(
        primitive_id="hooks/example",
        baseline_metrics=baseline,
        candidate_metrics=candidate,
        required_delta=1.0,
    )

    assert report.verdict == "reject"
    assert any("hallucination rate increased" in item for item in report.safety_regressions)


def test_missing_samples_needs_evidence(tmp_path: Path) -> None:
    baseline = collect_fitness_snapshot(label="baseline", metrics_dir=tmp_path / "empty-a")
    candidate = collect_fitness_snapshot(label="candidate", metrics_dir=tmp_path / "empty-b")

    report = compare_primitive_fitness(
        primitive_id="scripts/example",
        baseline=baseline,
        candidate=candidate,
        min_sample_count=1,
    )

    assert report.verdict == "needs_evidence"
    assert report.delta is None
