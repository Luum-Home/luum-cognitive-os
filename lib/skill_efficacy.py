# SCOPE: os-only
"""Skill efficacy metrics for Cognitive OS.

This module estimates whether a skill earns its keep by comparing skill-enabled
runs against matched no-skill baselines when available and by computing a simple
net value score otherwise.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from lib.skill_archive import SkillSnapshot


@dataclass(frozen=True)
class SkillRun:
    skill_name: str
    task_fingerprint: str
    success: bool
    cost_usd: float = 0.0
    latency_seconds: float = 0.0
    tool_calls: int = 0
    regression: bool = False
    security_findings: int = 0
    skill_enabled: bool = True


@dataclass(frozen=True)
class SkillEfficacySummary:
    skill_name: str
    skill_invocations: int
    paired_baselines: int
    success_rate: float
    baseline_success_rate: float | None
    task_success_delta: float | None
    cost_delta_usd: float | None
    latency_delta_seconds: float | None
    tool_call_delta: float | None
    regression_rate: float
    security_findings: int
    net_value_score: float
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def task_fingerprint(task: str) -> str:
    """Return a stable fingerprint for a task description."""
    normalized = " ".join((task or "").lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def run_from_snapshot(snapshot: SkillSnapshot) -> SkillRun:
    """Convert an archive snapshot into a SkillRun."""
    metadata = snapshot.metadata or {}
    return SkillRun(
        skill_name=snapshot.skill_name,
        task_fingerprint=str(metadata.get("task_fingerprint") or task_fingerprint(snapshot.task_description)),
        success=bool(snapshot.success),
        cost_usd=float(snapshot.cost_usd),
        latency_seconds=float(metadata.get("latency_seconds", 0.0) or 0.0),
        tool_calls=int(metadata.get("tool_calls", 0) or 0),
        regression=bool(metadata.get("regression", False)),
        security_findings=int(metadata.get("security_findings", 0) or 0),
        skill_enabled=bool(metadata.get("skill_enabled", True)),
    )


def _mean(values: Iterable[float]) -> float:
    vals = list(values)
    return statistics.mean(vals) if vals else 0.0


def summarize_skill(skill_name: str, runs: list[SkillRun]) -> SkillEfficacySummary:
    """Compute efficacy summary for one skill."""
    skill_runs = [r for r in runs if r.skill_name == skill_name and r.skill_enabled]
    baseline_runs = [r for r in runs if r.skill_name == skill_name and not r.skill_enabled]
    by_task_baseline = {r.task_fingerprint: r for r in baseline_runs}
    paired = [(r, by_task_baseline[r.task_fingerprint]) for r in skill_runs if r.task_fingerprint in by_task_baseline]

    success_rate = _mean(1.0 if r.success else 0.0 for r in skill_runs)
    baseline_success_rate = _mean(1.0 if b.success else 0.0 for _, b in paired) if paired else None
    task_success_delta = _mean((1.0 if r.success else 0.0) - (1.0 if b.success else 0.0) for r, b in paired) if paired else None
    cost_delta = _mean(r.cost_usd - b.cost_usd for r, b in paired) if paired else None
    latency_delta = _mean(r.latency_seconds - b.latency_seconds for r, b in paired) if paired else None
    tool_delta = _mean(float(r.tool_calls - b.tool_calls) for r, b in paired) if paired else None
    regression_rate = _mean(1.0 if r.regression else 0.0 for r in skill_runs)
    security_findings = sum(r.security_findings for r in skill_runs)

    # Net value: success dominates, cost/latency/tool/regression/security penalize.
    success_component = (task_success_delta if task_success_delta is not None else success_rate - 0.5) * 100
    cost_penalty = max(cost_delta or 0.0, 0.0) * 10
    latency_penalty = max(latency_delta or 0.0, 0.0) * 0.1
    tool_penalty = max(tool_delta or 0.0, 0.0) * 1.0
    regression_penalty = regression_rate * 40
    security_penalty = security_findings * 5
    score = round(success_component - cost_penalty - latency_penalty - tool_penalty - regression_penalty - security_penalty, 2)
    verdict = "high-value" if score >= 15 else "watch" if score >= 0 else "negative-value"

    return SkillEfficacySummary(
        skill_name=skill_name,
        skill_invocations=len(skill_runs),
        paired_baselines=len(paired),
        success_rate=round(success_rate, 4),
        baseline_success_rate=round(baseline_success_rate, 4) if baseline_success_rate is not None else None,
        task_success_delta=round(task_success_delta, 4) if task_success_delta is not None else None,
        cost_delta_usd=round(cost_delta, 4) if cost_delta is not None else None,
        latency_delta_seconds=round(latency_delta, 4) if latency_delta is not None else None,
        tool_call_delta=round(tool_delta, 4) if tool_delta is not None else None,
        regression_rate=round(regression_rate, 4),
        security_findings=security_findings,
        net_value_score=score,
        verdict=verdict,
    )


def summarize_runs(runs: list[SkillRun]) -> list[SkillEfficacySummary]:
    names = sorted({r.skill_name for r in runs if r.skill_enabled})
    return [summarize_skill(name, runs) for name in names]


def load_runs_from_archive(path: str | Path) -> list[SkillRun]:
    """Load SkillRun records from skill-archive JSONL, tolerating MetricEvent rows."""
    p = Path(path)
    if not p.exists():
        return []
    runs: list[SkillRun] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "payload" in row and isinstance(row.get("payload"), dict):
            payload = dict(row["payload"])
            payload.setdefault("timestamp", row.get("timestamp", ""))
        else:
            payload = row
        required = {"skill_name", "success", "task_description"}
        if not required.issubset(payload):
            continue
        snap = SkillSnapshot(
            skill_name=str(payload["skill_name"]),
            version=str(payload.get("version", "unknown")),
            timestamp=str(payload.get("timestamp", "")),
            trust_score=float(payload.get("trust_score", 0.0) or 0.0),
            success=bool(payload.get("success")),
            task_description=str(payload.get("task_description", "")),
            tokens_used=int(payload.get("tokens_used", 0) or 0),
            cost_usd=float(payload.get("cost_usd", 0.0) or 0.0),
            metadata=dict(payload.get("metadata", {}) or {}),
        )
        runs.append(run_from_snapshot(snap))
    return runs


def format_markdown(summaries: list[SkillEfficacySummary]) -> str:
    """Format summaries as a simple operator report."""
    lines = ["# Skill Efficacy Report", "", "| Skill | Uses | Paired | Success Δ | Cost Δ | Regression | Security | Net | Verdict |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    if not summaries:
        lines.append("| _none_ | 0 | 0 |  |  |  |  | 0 | no-data |")
        return "\n".join(lines) + "\n"
    for s in sorted(summaries, key=lambda item: item.net_value_score, reverse=True):
        lines.append(
            f"| {s.skill_name} | {s.skill_invocations} | {s.paired_baselines} | "
            f"{'' if s.task_success_delta is None else s.task_success_delta:.4} | "
            f"{'' if s.cost_delta_usd is None else s.cost_delta_usd:.4} | "
            f"{s.regression_rate:.2%} | {s.security_findings} | {s.net_value_score:.2f} | {s.verdict} |"
        )
    return "\n".join(lines) + "\n"
