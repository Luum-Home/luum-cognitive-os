"""Maintainer telemetry impact measurement for ADR-201 Phase 5.

Phase 2 proved that rollups exist. Phase 5 asks the harder question: did those
rollups change an operator or maintainer decision, and did accepted changes
improve or regress after landing?
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "maintainer-impact/v1"
POST_CHANGE_SCHEMA_VERSION = "maintainer-post-change-impact/v1"
DECISION_LEDGER = Path(".cognitive-os") / "metrics" / "maintainer-decision-impact.jsonl"
POST_CHANGE_LEDGER = Path(".cognitive-os") / "metrics" / "maintainer-post-change-impact.jsonl"

DECISIONS_THAT_COUNT_AS_CHANGE = {
    "accepted",
    "applied",
    "deferred",
    "rejected",
    "promoted",
    "demoted",
    "rerouted",
    "threshold_changed",
    "guard_tuned",
}

OUTCOMES_REQUIRING_FAILURE_PROTOCOL = {"regressed", "inconclusive"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_ledger_path(project_dir: Path) -> Path:
    return project_dir / DECISION_LEDGER


def default_post_change_ledger_path(project_dir: Path) -> Path:
    return project_dir / POST_CHANGE_LEDGER


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                yield row


def normalize_decision(value: Any) -> str:
    return str(value or "unknown").strip().lower().replace(" ", "_").replace("-", "_")


def day_bucket(value: Any) -> str:
    """Return YYYY-MM-DD for an impact row timestamp, or unknown."""
    raw = str(value or "").strip()
    if not raw:
        return "unknown"
    try:
        normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        return datetime.fromisoformat(normalized).date().isoformat()
    except ValueError:
        return "unknown"


def build_daily_trend(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate impact rows by UTC day for adoption trend checks."""
    by_day: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "total_decisions": 0,
            "rollup_influenced_decisions": 0,
            "changed_decisions": 0,
            "surfaces": Counter(),
        }
    )
    for row in rows:
        bucket = by_day[day_bucket(row.get("timestamp"))]
        bucket["total_decisions"] += 1
        surface = str(row.get("surface") or "unknown")
        bucket["surfaces"][surface] += 1
        if is_rollup_influenced(row):
            bucket["rollup_influenced_decisions"] += 1
            if normalize_decision(row.get("decision")) in DECISIONS_THAT_COUNT_AS_CHANGE:
                bucket["changed_decisions"] += 1

    trend = []
    for day in sorted(by_day):
        item = by_day[day]
        total = int(item["total_decisions"])
        changed = int(item["changed_decisions"])
        influenced = int(item["rollup_influenced_decisions"])
        trend.append(
            {
                "day": day,
                "total_decisions": total,
                "rollup_influenced_decisions": influenced,
                "changed_decisions": changed,
                "influence_rate": round(influenced / total, 6) if total else 0.0,
                "changed_rate": round(changed / total, 6) if total else 0.0,
                "surfaces": dict(sorted(item["surfaces"].items())),
            }
        )
    return trend


def is_rollup_influenced(row: dict[str, Any]) -> bool:
    """Return true when a decision row cites ledger/proposal evidence."""
    return bool(
        row.get("source_rollup_run_id")
        or row.get("source_rollup_ref")
        or row.get("proposal_id")
        or row.get("source_proposal_id")
    )


def build_decision_event(
    *,
    decision: str,
    surface: str,
    source_rollup_run_id: str | None = None,
    source_rollup_ref: str | None = None,
    proposal_id: str | None = None,
    reason: str | None = None,
    operator: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Build one append-only impact ledger row."""
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": timestamp or utc_now(),
        "surface": surface,
        "decision": normalize_decision(decision),
        "source_rollup_run_id": source_rollup_run_id,
        "source_rollup_ref": source_rollup_ref,
        "proposal_id": proposal_id,
        "reason": reason,
        "operator": operator,
    }


def append_decision_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def _metric_delta(before_metrics: dict[str, Any], after_metrics: dict[str, Any]) -> dict[str, dict[str, float]]:
    deltas: dict[str, dict[str, float]] = {}
    for key in sorted(set(before_metrics) | set(after_metrics)):
        before = before_metrics.get(key)
        after = after_metrics.get(key)
        if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
            continue
        deltas[key] = {
            "before": float(before),
            "after": float(after),
            "delta": round(float(after) - float(before), 6),
        }
    return deltas


def normalize_outcome(value: Any) -> str:
    normalized = normalize_decision(value)
    if normalized in {"pass", "passed", "improved", "success"}:
        return "improved"
    if normalized in {"fail", "failed", "regression", "regressed"}:
        return "regressed"
    if normalized in {"inconclusive", "unknown", "insufficient_data"}:
        return "inconclusive"
    return normalized or "unknown"


def outcome_failure_protocol(
    *,
    proposal_id: str,
    degradation_pattern: str,
    outcome: str,
    work_id: str | None = None,
    source_rollup_ref: str | None = None,
) -> dict[str, Any]:
    """Build the mandatory protocol for regressed or inconclusive outcomes."""
    normalized = normalize_outcome(outcome)
    if normalized not in OUTCOMES_REQUIRING_FAILURE_PROTOCOL:
        return {
            "required": False,
            "outcome": normalized,
            "proposal_id": proposal_id,
            "degradation_pattern": degradation_pattern,
        }
    confidence_penalty = 0.20 if normalized == "regressed" else 0.10
    return {
        "required": True,
        "status": "manual_investigation_open",
        "outcome": normalized,
        "proposal_id": proposal_id,
        "work_id": work_id,
        "source_rollup_ref": source_rollup_ref,
        "quarantine": {
            "pattern": degradation_pattern,
            "reason": f"post-change outcome {normalized}",
            "future_promotion_state": "quarantined_until_manual_resolution",
        },
        "rollback": {
            "approval_required": True,
            "allowed_without_approval": False,
        },
        "confidence_penalty": {
            "similar_pattern_penalty": confidence_penalty,
            "applies_to": degradation_pattern,
        },
        "next_actions": [
            "open_manual_investigation",
            "attach_before_after_metrics_and_source_rollup",
            "require_human_approval_before_rollback",
            "penalize_future_maintainer_confidence_for_similar_patterns",
        ],
    }


def build_post_change_impact_event(
    *,
    proposal_id: str,
    work_id: str,
    surface: str,
    degradation_pattern: str,
    before_metrics: dict[str, Any],
    after_metrics: dict[str, Any],
    source_rollup_run_id: str | None = None,
    source_rollup_ref: str | None = None,
    operator_decision: str,
    outcome: str,
    operator: str | None = None,
    timestamp: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build one post-change impact row for an accepted/applied proposal.

    The row is append-only evidence tying an accepted proposal to before/after
    metrics, source rollup provenance, the operator decision, and work identity.
    Regressed or inconclusive rows embed the failure protocol so rollback cannot
    happen silently.
    """
    normalized_outcome = normalize_outcome(outcome)
    return {
        "schema_version": POST_CHANGE_SCHEMA_VERSION,
        "timestamp": timestamp or utc_now(),
        "proposal_id": proposal_id,
        "work_id": work_id,
        "surface": surface,
        "degradation_pattern": degradation_pattern,
        "source_rollup_run_id": source_rollup_run_id,
        "source_rollup_ref": source_rollup_ref,
        "operator_decision": normalize_decision(operator_decision),
        "operator": operator,
        "before_metrics": before_metrics,
        "after_metrics": after_metrics,
        "metric_delta": _metric_delta(before_metrics, after_metrics),
        "outcome": normalized_outcome,
        "notes": notes,
        "failure_protocol": outcome_failure_protocol(
            proposal_id=proposal_id,
            degradation_pattern=degradation_pattern,
            outcome=normalized_outcome,
            work_id=work_id,
            source_rollup_ref=source_rollup_ref,
        ),
    }


def append_post_change_impact_event(path: Path, event: dict[str, Any]) -> None:
    if not event.get("work_id"):
        raise ValueError("post-change impact event requires work_id")
    if not event.get("proposal_id"):
        raise ValueError("post-change impact event requires proposal_id")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def post_change_impact_report(project_dir: Path, *, ledger_path: Path | None = None) -> dict[str, Any]:
    path = ledger_path or default_post_change_ledger_path(project_dir)
    rows = list(read_jsonl(path) or [])
    outcomes = Counter(normalize_outcome(row.get("outcome")) for row in rows)
    failure_rows = [row for row in rows if normalize_outcome(row.get("outcome")) in OUTCOMES_REQUIRING_FAILURE_PROTOCOL]
    quarantined_patterns = sorted(
        {
            str((row.get("failure_protocol") or {}).get("quarantine", {}).get("pattern") or row.get("degradation_pattern"))
            for row in failure_rows
            if row.get("degradation_pattern") or (row.get("failure_protocol") or {}).get("quarantine")
        }
    )
    if not rows:
        status = "no_data"
    elif failure_rows:
        status = "outcome_failures_pending_investigation"
    else:
        status = "post_change_outcomes_recorded"
    return {
        "schema_version": POST_CHANGE_SCHEMA_VERSION,
        "project_dir": str(project_dir),
        "ledger_path": str(path),
        "status": status,
        "total_records": len(rows),
        "outcomes_by_type": dict(sorted(outcomes.items())),
        "failure_count": len(failure_rows),
        "quarantined_patterns": quarantined_patterns,
        "proposal_ids": sorted({str(row.get("proposal_id")) for row in rows if row.get("proposal_id")}),
        "work_ids": sorted({str(row.get("work_id")) for row in rows if row.get("work_id")}),
        "failure_protocols": [row.get("failure_protocol") for row in failure_rows],
    }


def impact_report(project_dir: Path, *, ledger_path: Path | None = None) -> dict[str, Any]:
    """Summarize whether telemetry rollups changed decisions."""
    path = ledger_path or default_ledger_path(project_dir)
    rows = list(read_jsonl(path) or [])
    decisions = Counter(normalize_decision(row.get("decision")) for row in rows)
    influenced = [row for row in rows if is_rollup_influenced(row)]
    changed = [
        row
        for row in influenced
        if normalize_decision(row.get("decision")) in DECISIONS_THAT_COUNT_AS_CHANGE
    ]
    rollup_ids = sorted(
        {
            str(row.get("source_rollup_run_id"))
            for row in influenced
            if row.get("source_rollup_run_id")
        }
    )
    proposal_ids = sorted(
        {
            str(row.get("proposal_id") or row.get("source_proposal_id"))
            for row in influenced
            if row.get("proposal_id") or row.get("source_proposal_id")
        }
    )
    total = len(rows)
    influence_rate = round(len(influenced) / total, 6) if total else 0.0
    changed_rate = round(len(changed) / total, 6) if total else 0.0
    if not rows:
        status = "no_data"
    elif not influenced:
        status = "no_rollup_influence"
    elif changed:
        status = "rollups_changed_decisions"
    else:
        status = "rollups_seen_no_change"

    daily_trend = build_daily_trend(rows)

    return {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(project_dir),
        "ledger_path": str(path),
        "status": status,
        "total_decisions": total,
        "rollup_influenced_decisions": len(influenced),
        "changed_decisions": len(changed),
        "influence_rate": influence_rate,
        "changed_rate": changed_rate,
        "decisions_by_type": dict(sorted(decisions.items())),
        "source_rollup_run_ids": rollup_ids,
        "proposal_ids": proposal_ids,
        "daily_trend": daily_trend,
        "latest_trend_day": daily_trend[-1] if daily_trend else None,
    }
