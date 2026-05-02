# SCOPE: os-only
"""Runtime comparison benchmark schema and reporting helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_RESULT_FIELDS = {
    "benchmark_id",
    "system",
    "profile",
    "task_id",
    "result",
    "duration_seconds",
    "tests_passed",
    "cost_usd",
    "tool_calls",
    "files_touched",
    "security_events",
}


@dataclass(frozen=True)
class RuntimeBenchmarkResult:
    benchmark_id: str
    system: str
    profile: str
    task_id: str
    result: str
    duration_seconds: float = 0.0
    tests_passed: bool = False
    cost_usd: float | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: int = 0
    files_touched: int = 0
    repair_count: int = 0
    security_events: int = 0
    notes: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["timestamp"] = self.timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds")
        return row


def validate_result(row: dict[str, Any]) -> list[str]:
    """Return schema errors for a benchmark result row."""
    errors = [f"missing:{field}" for field in sorted(REQUIRED_RESULT_FIELDS) if field not in row]
    if row.get("result") not in {"pass", "fail", "inconclusive"}:
        errors.append("invalid:result")
    if row.get("duration_seconds", 0) < 0:
        errors.append("invalid:duration_seconds")
    if row.get("tool_calls", 0) < 0:
        errors.append("invalid:tool_calls")
    return errors


def append_result(path: str | Path, result: RuntimeBenchmarkResult) -> None:
    """Append a result row to JSONL after validation."""
    row = result.to_dict()
    errors = validate_result(row)
    if errors:
        raise ValueError(",".join(errors))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def load_results(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def format_leaderboard(rows: list[dict[str, Any]]) -> str:
    """Format runtime benchmark rows as a markdown leaderboard."""
    lines = ["# Runtime Benchmark Leaderboard", "", "| System | Profile | Runs | Pass rate | Avg cost | Security events |", "|---|---|---:|---:|---:|---:|"]
    if not rows:
        lines.append("| _none_ | _none_ | 0 | 0% |  | 0 |")
        return "\n".join(lines) + "\n"
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["system"]), str(row["profile"])), []).append(row)
    for (system, profile), group in sorted(grouped.items()):
        pass_rate = sum(1 for r in group if r.get("result") == "pass") / len(group)
        costs = [float(r["cost_usd"]) for r in group if r.get("cost_usd") is not None]
        avg_cost = sum(costs) / len(costs) if costs else 0.0
        security_events = sum(int(r.get("security_events", 0) or 0) for r in group)
        lines.append(f"| {system} | {profile} | {len(group)} | {pass_rate:.0%} | {avg_cost:.4f} | {security_events} |")
    return "\n".join(lines) + "\n"
