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
    "quality": 23,
    "effectiveness": 18,
    "safety": 24,
    "friction": 14,
    "cost_latency": 9,
    "dogfood": 4,
    "consumer_evidence": 4,
    "portability_readiness": 4,
}

CORE_PROMOTION_DOMAINS = {"quality", "effectiveness", "safety", "friction", "cost_latency", "dogfood"}
SUPPORTING_EVIDENCE_DOMAINS = {"consumer_evidence", "portability_readiness"}


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


def _load_json_object(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"error": f"could not read {path}"}
    return payload if isinstance(payload, dict) else {"error": "payload is not an object"}


def _consumer_evidence_score(bundle_path: Path | None) -> tuple[float | None, dict[str, Any]]:
    bundle = _load_json_object(bundle_path)
    if bundle is None:
        return None, {"reason": "no consumer proposal bundle"}
    if "error" in bundle:
        return None, bundle

    proposals = bundle.get("proposals", [])
    if not isinstance(proposals, list):
        return None, {"error": "consumer proposals must be a list"}
    invalid_runtime = [item for item in proposals if isinstance(item, dict) and item.get("runtime_effect") != "none"]
    action_counts = bundle.get("action_counts") if isinstance(bundle.get("action_counts"), dict) else {}
    if not action_counts:
        action_counts = {}
        for proposal in proposals:
            if isinstance(proposal, dict):
                action = str(proposal.get("action") or "unknown")
                action_counts[action] = int(action_counts.get(action, 0) or 0) + 1

    proposal_count = len(proposals)
    upstream = int(action_counts.get("upstream-candidate", 0) or 0)
    project_local = int(action_counts.get("project-local", 0) or 0)
    harness_gap = int(action_counts.get("harness-gap", 0) or 0)
    reject = int(action_counts.get("reject", 0) or 0)
    docs_only = int(action_counts.get("docs-only", 0) or 0)
    policy = bundle.get("policy") if isinstance(bundle.get("policy"), dict) else {}
    propose_only = bundle.get("mode") == "propose_only" and bundle.get("runtime_effect") == "none" and policy.get("auto_merge") is False

    raw = {
        "source": str(bundle_path),
        "proposal_count": proposal_count,
        "action_counts": dict(sorted(action_counts.items())),
        "upstream_candidate_count": upstream,
        "project_local_count": project_local,
        "harness_gap_count": harness_gap,
        "docs_only_count": docs_only,
        "reject_count": reject,
        "invalid_runtime_effect_count": len(invalid_runtime),
        "propose_only": propose_only,
        "runtime_effect": bundle.get("runtime_effect", ""),
    }
    if proposal_count == 0:
        return None, raw
    if invalid_runtime or not propose_only:
        return 0.0, raw
    score = 70.0 + min(upstream * 4.0, 16.0) + min(docs_only * 2.0, 6.0) - project_local * 2.0 - harness_gap * 8.0 - reject * 10.0
    return _bounded(score), raw


def _portability_readiness_score(report_path: Path | None) -> tuple[float | None, dict[str, Any]]:
    report = _load_json_object(report_path)
    if report is None:
        return None, {"reason": "no dependency readiness report"}
    if "error" in report:
        return None, report
    buckets = ("already_present", "installable", "manual", "auth_bound", "unsupported_platform", "installed", "failed")
    counts = {bucket: len(report.get(bucket, []) or []) for bucket in buckets}
    dependency_count = sum(counts[bucket] for bucket in ("already_present", "installable", "manual", "auth_bound", "unsupported_platform"))
    if dependency_count == 0 and counts["installed"] == 0 and counts["failed"] == 0:
        return None, {"source": str(report_path), "dependency_count": 0, "bucket_counts": counts}
    credential_policy_ok = report.get("credential_policy") == "never-copy-or-read-credential-stores"
    score = 100.0
    score -= counts["unsupported_platform"] * 12.0
    score -= counts["failed"] * 25.0
    score -= counts["manual"] * 2.0
    score -= counts["installable"] * 1.0
    if not credential_policy_ok:
        score -= 30.0
    raw = {
        "source": str(report_path),
        "schema_version": report.get("schema_version", ""),
        "profile": report.get("profile", ""),
        "platform": report.get("platform", ""),
        "mode": report.get("mode", ""),
        "dependency_count": dependency_count,
        "bucket_counts": counts,
        "credential_policy_ok": credential_policy_ok,
    }
    return _bounded(score), raw


def collect_fitness_snapshot(
    *,
    label: str,
    metrics_dir: str | Path,
    repo_dir: str | Path | None = None,
    dogfood_json: str | Path | None = None,
    consumer_proposals_json: str | Path | None = None,
    dependency_report_json: str | Path | None = None,
) -> FitnessSnapshot:
    metrics = Path(metrics_dir)
    repo = Path(repo_dir) if repo_dir else None
    dogfood_path = Path(dogfood_json) if dogfood_json else None
    consumer_path = Path(consumer_proposals_json) if consumer_proposals_json else None
    dependency_path = Path(dependency_report_json) if dependency_report_json else None
    kpis = collect_session_kpis(str(metrics))
    dispatch_rows = read_jsonl(metrics / "llm-dispatch.jsonl") + read_jsonl(metrics / "dispatch-outcomes.jsonl")
    friction_score, friction_raw = _friction_score(metrics)
    safety_score, safety_raw = _safety_score(kpis, metrics)
    dogfood_score, dogfood_raw = _dogfood_score(repo, dogfood_path)
    consumer_score, consumer_raw = _consumer_evidence_score(consumer_path)
    portability_score, portability_raw = _portability_readiness_score(dependency_path)
    scores: dict[str, float | None] = {
        "quality": _quality_score(kpis),
        "effectiveness": _effectiveness_score(kpis, dispatch_rows),
        "safety": safety_score,
        "friction": friction_score,
        "cost_latency": _cost_latency_score(kpis, dispatch_rows, friction_raw),
        "dogfood": dogfood_score,
        "consumer_evidence": consumer_score,
        "portability_readiness": portability_score,
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
            consumer_raw.get("proposal_count") if isinstance(consumer_raw, dict) else 0,
            portability_raw.get("dependency_count") if isinstance(portability_raw, dict) else 0,
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
            "consumer_evidence": consumer_raw,
            "portability_readiness": portability_raw,
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

    baseline_core = any(baseline.scores.get(domain) is not None for domain in CORE_PROMOTION_DOMAINS)
    candidate_core = any(candidate.scores.get(domain) is not None for domain in CORE_PROMOTION_DOMAINS)
    supporting_only = not (baseline_core and candidate_core)

    if baseline.sample_count < min_sample_count or candidate.sample_count < min_sample_count:
        verdict = "needs_evidence"
    elif supporting_only:
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
        missing_signals=missing + (["core_promotion_domains"] if supporting_only else []),
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
    baseline_consumer_proposals_json: str | Path | None = None,
    candidate_consumer_proposals_json: str | Path | None = None,
    baseline_dependency_report_json: str | Path | None = None,
    candidate_dependency_report_json: str | Path | None = None,
    required_delta: float = 1.0,
    min_sample_count: int = 1,
    evidence_commands: list[str] | None = None,
) -> PrimitiveFitnessReport:
    baseline = collect_fitness_snapshot(
        label="baseline",
        metrics_dir=baseline_metrics,
        repo_dir=baseline_repo,
        dogfood_json=baseline_dogfood_json,
        consumer_proposals_json=baseline_consumer_proposals_json,
        dependency_report_json=baseline_dependency_report_json,
    )
    candidate = collect_fitness_snapshot(
        label="candidate",
        metrics_dir=candidate_metrics,
        repo_dir=candidate_repo,
        dogfood_json=candidate_dogfood_json,
        consumer_proposals_json=candidate_consumer_proposals_json,
        dependency_report_json=candidate_dependency_report_json,
    )
    return compare_primitive_fitness(
        primitive_id=primitive_id,
        baseline=baseline,
        candidate=candidate,
        required_delta=required_delta,
        min_sample_count=min_sample_count,
        evidence_commands=evidence_commands,
    )
