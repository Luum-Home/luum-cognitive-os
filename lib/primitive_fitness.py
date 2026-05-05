# SCOPE: both
"""Primitive fitness evaluation for governed self-improvement.

This module compares a candidate primitive against a baseline using the KPI/OKR
signals already produced by Cognitive OS. It is intentionally evidence-first:
missing metric families are excluded from the weighted score and reported as
missing signals rather than treated as zero.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from lib.dogfood_scorer import DogfoodScorer
from lib.friction_telemetry import summarize as summarize_friction
from lib.kpi_collector import collect_session_kpis
from lib.outcome_metrics import compute_dispatch_outcomes


DOMAIN_WEIGHTS: dict[str, int] = {
    "quality": 25,
    "effectiveness": 20,
    "safety": 25,
    "friction": 15,
    "cost_latency": 10,
    "dogfood": 5,
}


@dataclass(frozen=True)
class FitnessSnapshot:
    """Point-in-time metric snapshot for one primitive variant."""

    label: str
    metrics_dir: str
    scores: dict[str, float | None]
    raw: dict[str, Any]
    missing_signals: list[str]
    overall_score: float | None
    sample_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PrimitiveFitnessReport:
    """Baseline-vs-candidate comparison used by promotion gates."""

    schema_version: str
    primitive_id: str
    status: str
    verdict: str
    baseline: FitnessSnapshot
    candidate: FitnessSnapshot
    delta: float | None
    required_delta: float
    safety_regressions: list[str] = field(default_factory=list)
    missing_signals: list[str] = field(default_factory=list)
    evidence_commands: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["baseline"] = self.baseline.to_dict()
        payload["candidate"] = self.candidate.to_dict()
        return payload


# ---------------------------------------------------------------------------
# JSONL helpers
# ---------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            if "schema_version" in data and isinstance(data.get("payload"), dict):
                flat = dict(data["payload"])
                flat.setdefault("event_type", data.get("event_type"))
                flat.setdefault("timestamp", data.get("timestamp"))
                rows.append(flat)
            else:
                rows.append(data)
    return rows


def _bounded(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _weighted_score(scores: dict[str, float | None]) -> float | None:
    numerator = 0.0
    denominator = 0
    for domain, weight in DOMAIN_WEIGHTS.items():
        score = scores.get(domain)
        if score is None:
            continue
        numerator += score * weight
        denominator += weight
    if denominator == 0:
        return None
    return round(numerator / denominator, 2)


# ---------------------------------------------------------------------------
# Snapshot extraction
# ---------------------------------------------------------------------------


def _quality_score(kpis: dict[str, Any]) -> float | None:
    quality = kpis.get("quality", {})
    count = int(kpis.get("trust", {}).get("trust_score_count", 0) or 0)
    if count == 0 and int(kpis.get("skills", {}).get("total_executions", 0) or 0) == 0:
        return None
    return _bounded(float(quality.get("composite_score", 0) or 0))


def _effectiveness_score(kpis: dict[str, Any], dispatch_rows: list[dict[str, Any]]) -> float | None:
    parts: list[float] = []
    skills = kpis.get("skills", {})
    if int(skills.get("total_executions", 0) or 0) > 0:
        parts.append(_bounded(float(skills.get("first_attempt_success_rate", 0) or 0)))
    outcomes = compute_dispatch_outcomes(dispatch_rows)
    if outcomes.total_dispatches > 0:
        parts.append(_bounded(outcomes.success_rate * 100.0))
    errors = kpis.get("errors", {})
    total_errors = int(errors.get("total_errors", 0) or 0)
    if total_errors > 0:
        recurrence = int(errors.get("recurrence_count", 0) or 0)
        parts.append(_bounded(100.0 - recurrence * 15.0 - min(total_errors, 20)))
    return _mean(parts)


def _safety_score(kpis: dict[str, Any], metrics_dir: Path) -> tuple[float | None, dict[str, Any]]:
    hallucinations = kpis.get("hallucinations", {})
    parts: list[float] = []
    raw: dict[str, Any] = {}
    if int(hallucinations.get("total_checks", 0) or 0) > 0:
        rate = float(hallucinations.get("hallucination_rate", 0) or 0)
        raw["hallucination_rate"] = rate
        parts.append(_bounded(100.0 - rate * 2.0))

    safety_files = [
        "git-op-blocks.jsonl",
        "rm-op-blocks.jsonl",
        "lethal-trifecta.jsonl",
        "missing-secrets.jsonl",
        "confidence-gates.jsonl",
        "network-egress.jsonl",
        "protected-config-write.jsonl",
    ]
    safety_rows = [row for name in safety_files for row in read_jsonl(metrics_dir / name)]
    if safety_rows:
        bypasses = sum(1 for row in safety_rows if row.get("bypass") is True or "bypass" in str(row.get("event_type", "")).lower())
        failures = sum(1 for row in safety_rows if str(row.get("status", row.get("execution_status", ""))).lower() in {"failed", "error"})
        raw["safety_rows"] = len(safety_rows)
        raw["safety_bypasses"] = bypasses
        raw["safety_failures"] = failures
        parts.append(_bounded(100.0 - bypasses * 25.0 - failures * 20.0))
    return _mean(parts), raw


def _friction_score(metrics_dir: Path) -> tuple[float | None, dict[str, Any]]:
    hook_rows: list[dict[str, Any]] = []
    for path in metrics_dir.glob("*.jsonl"):
        if path.name in {"key-learnings.jsonl", "primitive-promotion-evaluations.jsonl"}:
            continue
        hook_rows.extend(read_jsonl(path))
    summary = summarize_friction(hook_rows)
    total = int(summary.get("total_events", 0) or 0)
    if total == 0:
        return None, summary
    counts = summary.get("outcome_counts", {})
    blocks = int(counts.get("block", 0) or 0)
    warns = int(counts.get("warn", 0) or 0)
    bypasses = int(counts.get("bypass", 0) or 0)
    false_positive_candidates = len(summary.get("false_positive_candidates", []) or [])
    score = 100.0 - (blocks / total * 45.0) - (warns / total * 20.0) - (bypasses / total * 35.0) - false_positive_candidates * 5.0
    return _bounded(score), summary


def _cost_latency_score(kpis: dict[str, Any], dispatch_rows: list[dict[str, Any]], friction: dict[str, Any]) -> float | None:
    parts: list[float] = []
    total_cost = float(kpis.get("cost", {}).get("total_usd", 0) or 0)
    if total_cost > 0:
        parts.append(_bounded(100.0 - min(total_cost, 50.0) * 2.0))
    outcomes = compute_dispatch_outcomes(dispatch_rows)
    if outcomes.total_dispatches > 0:
        parts.append(_bounded(100.0 - min(outcomes.p95_latency_ms / 1000.0, 60.0)))
    latency_hooks = friction.get("top_latency_hooks", []) if isinstance(friction, dict) else []
    if latency_hooks:
        p95 = max(float(item.get("p95_latency_ms", 0) or 0) for item in latency_hooks)
        parts.append(_bounded(100.0 - min(p95 / 100.0, 60.0)))
    return _mean(parts)


def _dogfood_score(repo_dir: Path | None, dogfood_json: Path | None) -> tuple[float | None, dict[str, Any]]:
    if dogfood_json and dogfood_json.exists():
        try:
            payload = json.loads(dogfood_json.read_text(encoding="utf-8"))
            score = payload.get("overall")
            return (float(score) if score is not None else None), payload
        except Exception:
            return None, {"error": f"could not read {dogfood_json}"}
    if repo_dir is None:
        return None, {"reason": "no repo_dir"}
    try:
        score = DogfoodScorer(repo_dir).compute_score()
        return score.overall, score.to_dict()
    except Exception as exc:  # noqa: BLE001
        return None, {"error": str(exc)}


def collect_fitness_snapshot(
    *,
    label: str,
    metrics_dir: str | Path,
    repo_dir: str | Path | None = None,
    dogfood_json: str | Path | None = None,
) -> FitnessSnapshot:
    metrics = Path(metrics_dir)
    repo = Path(repo_dir) if repo_dir else None
    dogfood_path = Path(dogfood_json) if dogfood_json else None
    kpis = collect_session_kpis(str(metrics))
    dispatch_rows = read_jsonl(metrics / "llm-dispatch.jsonl") + read_jsonl(metrics / "dispatch-outcomes.jsonl")
    friction_score, friction_raw = _friction_score(metrics)
    safety_score, safety_raw = _safety_score(kpis, metrics)
    dogfood_score, dogfood_raw = _dogfood_score(repo, dogfood_path)
    scores: dict[str, float | None] = {
        "quality": _quality_score(kpis),
        "effectiveness": _effectiveness_score(kpis, dispatch_rows),
        "safety": safety_score,
        "friction": friction_score,
        "cost_latency": _cost_latency_score(kpis, dispatch_rows, friction_raw),
        "dogfood": dogfood_score,
    }
    missing = [name for name, value in scores.items() if value is None]
    sample_count = sum(
        int(value or 0)
        for value in (
            kpis.get("trust", {}).get("trust_score_count"),
            kpis.get("skills", {}).get("total_executions"),
            kpis.get("errors", {}).get("total_errors"),
            friction_raw.get("total_events") if isinstance(friction_raw, dict) else 0,
            len(dispatch_rows),
        )
    )
    return FitnessSnapshot(
        label=label,
        metrics_dir=str(metrics),
        scores=scores,
        raw={
            "kpis": kpis,
            "friction": friction_raw,
            "safety": safety_raw,
            "dispatch_outcomes": compute_dispatch_outcomes(dispatch_rows).__dict__,
            "dogfood": dogfood_raw,
        },
        missing_signals=missing,
        overall_score=_weighted_score(scores),
        sample_count=sample_count,
    )


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def detect_safety_regressions(baseline: FitnessSnapshot, candidate: FitnessSnapshot) -> list[str]:
    regressions: list[str] = []
    b_safety = baseline.raw.get("safety", {}) if isinstance(baseline.raw, dict) else {}
    c_safety = candidate.raw.get("safety", {}) if isinstance(candidate.raw, dict) else {}
    for key, label in (
        ("hallucination_rate", "hallucination rate increased"),
        ("safety_bypasses", "safety bypass count increased"),
        ("safety_failures", "safety failure count increased"),
    ):
        if float(c_safety.get(key, 0) or 0) > float(b_safety.get(key, 0) or 0):
            regressions.append(f"{label}: {b_safety.get(key, 0)} -> {c_safety.get(key, 0)}")

    b_test_health = baseline.raw.get("dogfood", {}).get("dimensions", {}).get("test_health") if isinstance(baseline.raw.get("dogfood"), dict) else None
    c_test_health = candidate.raw.get("dogfood", {}).get("dimensions", {}).get("test_health") if isinstance(candidate.raw.get("dogfood"), dict) else None
    if b_test_health is not None and c_test_health is not None and float(c_test_health) < float(b_test_health):
        regressions.append(f"test health regressed: {b_test_health} -> {c_test_health}")
    return regressions


def compare_primitive_fitness(
    *,
    primitive_id: str,
    baseline: FitnessSnapshot,
    candidate: FitnessSnapshot,
    required_delta: float = 1.0,
    min_sample_count: int = 1,
    evidence_commands: list[str] | None = None,
) -> PrimitiveFitnessReport:
    missing = sorted(set(baseline.missing_signals + candidate.missing_signals))
    safety_regressions = detect_safety_regressions(baseline, candidate)
    delta = None
    if baseline.overall_score is not None and candidate.overall_score is not None:
        delta = round(candidate.overall_score - baseline.overall_score, 2)

    if baseline.sample_count < min_sample_count or candidate.sample_count < min_sample_count:
        verdict = "needs_evidence"
    elif delta is None:
        verdict = "needs_evidence"
    elif safety_regressions:
        verdict = "reject"
    elif delta >= required_delta:
        verdict = "promote"
    elif delta < 0:
        verdict = "reject"
    else:
        verdict = "keep_draft"

    return PrimitiveFitnessReport(
        schema_version="primitive-fitness.v1",
        primitive_id=primitive_id,
        status="pass" if verdict == "promote" else "fail" if verdict == "reject" else "needs_evidence",
        verdict=verdict,
        baseline=baseline,
        candidate=candidate,
        delta=delta,
        required_delta=float(required_delta),
        safety_regressions=safety_regressions,
        missing_signals=missing,
        evidence_commands=evidence_commands or [],
    )


def build_report(
    *,
    primitive_id: str,
    baseline_metrics: str | Path,
    candidate_metrics: str | Path,
    baseline_repo: str | Path | None = None,
    candidate_repo: str | Path | None = None,
    baseline_dogfood_json: str | Path | None = None,
    candidate_dogfood_json: str | Path | None = None,
    required_delta: float = 1.0,
    min_sample_count: int = 1,
    evidence_commands: list[str] | None = None,
) -> PrimitiveFitnessReport:
    baseline = collect_fitness_snapshot(
        label="baseline",
        metrics_dir=baseline_metrics,
        repo_dir=baseline_repo,
        dogfood_json=baseline_dogfood_json,
    )
    candidate = collect_fitness_snapshot(
        label="candidate",
        metrics_dir=candidate_metrics,
        repo_dir=candidate_repo,
        dogfood_json=candidate_dogfood_json,
    )
    return compare_primitive_fitness(
        primitive_id=primitive_id,
        baseline=baseline,
        candidate=candidate,
        required_delta=required_delta,
        min_sample_count=min_sample_count,
        evidence_commands=evidence_commands,
    )
