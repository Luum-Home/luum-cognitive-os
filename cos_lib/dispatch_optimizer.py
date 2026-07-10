"""ADR-053 dispatch auto-optimizer.

Analyzes historical dispatch/benchmark metrics and writes human-reviewed routing
proposals. It never mutates active routing directly.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RoutingProposal:
    skill_name: str
    task_type: str
    provider: str
    samples: int
    success_rate: float
    avg_cost_usd: float
    avg_latency_ms: float
    rationale: str


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def normalize_dispatch_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill_name": str(row.get("skill_name") or "unknown"),
        "task_type": str(row.get("task_type") or "general"),
        "provider": str(row.get("provider_used") or row.get("provider") or "unknown"),
        "success": bool(row.get("success", row.get("passed", False))),
        "cost_usd": float(row.get("cost_usd") or 0.0),
        "latency_ms": float(row.get("latency_ms") or 0.0),
    }


def analyze(metrics_path: Path, min_samples_per_tuple: int = 10) -> list[RoutingProposal]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(metrics_path):
        norm = normalize_dispatch_row(row)
        grouped[(norm["skill_name"], norm["task_type"], norm["provider"])].append(norm)

    proposals: list[RoutingProposal] = []
    for (skill_name, task_type, provider), rows in sorted(grouped.items()):
        if len(rows) < min_samples_per_tuple:
            continue
        success_rate = sum(1 for row in rows if row["success"]) / len(rows)
        avg_cost = sum(row["cost_usd"] for row in rows) / len(rows)
        avg_latency = sum(row["latency_ms"] for row in rows) / len(rows)
        proposals.append(
            RoutingProposal(
                skill_name=skill_name,
                task_type=task_type,
                provider=provider,
                samples=len(rows),
                success_rate=round(success_rate, 4),
                avg_cost_usd=round(avg_cost, 6),
                avg_latency_ms=round(avg_latency, 2),
                rationale="highest observed sample bucket; operator must review before applying",
            )
        )
    return proposals


def propose_routing(proposals: list[RoutingProposal]) -> dict[str, Any]:
    best: dict[tuple[str, str], RoutingProposal] = {}
    for proposal in proposals:
        key = (proposal.skill_name, proposal.task_type)
        current = best.get(key)
        if current is None or (proposal.success_rate, -proposal.avg_cost_usd, -proposal.avg_latency_ms) > (
            current.success_rate,
            -current.avg_cost_usd,
            -current.avg_latency_ms,
        ):
            best[key] = proposal
    return {
        "schema_version": "dispatch-auto-tuned.v1",
        "human_review_required": True,
        "proposals": [asdict(value) for value in sorted(best.values(), key=lambda item: (item.skill_name, item.task_type))],
    }


def write_proposal(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
