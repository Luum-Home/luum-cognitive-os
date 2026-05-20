"""Maintainer telemetry impact measurement for ADR-201 Phase 5.

Phase 2 proved that rollups exist. Phase 5 asks the harder question: did those
rollups change an operator or maintainer decision?
"""
from __future__ import annotations

import json
from collections import Counter
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
    }
