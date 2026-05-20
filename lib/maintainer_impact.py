"""Maintainer telemetry impact measurement for ADR-201 Phase 5.

Phase 2 proved that rollups exist. Phase 5 asks the harder question: did those
rollups change an operator or maintainer decision?
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "maintainer-impact/v1"
DECISION_LEDGER = Path(".cognitive-os") / "metrics" / "maintainer-decision-impact.jsonl"

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


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_ledger_path(project_dir: Path) -> Path:
    return project_dir / DECISION_LEDGER


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
