# SCOPE: os-only
"""Compare memory retrieval benchmark reports side by side."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "memory-retrieval-comparison/v1"


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


def load_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_path"] = path
    return data


def strategy_name(report: dict[str, Any]) -> str:
    return str(report.get("strategy") or Path(str(report.get("_path", "unknown"))).stem.rsplit("-2026", 1)[0])


def fixture_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["fixture_id"]): row for row in report.get("results", [])}


def compare_reports(paths: list[Path], *, baseline: str = "current-local") -> dict[str, Any]:
    reports = [load_report(path) for path in paths]
    by_strategy = {strategy_name(report): report for report in reports}
    if baseline not in by_strategy:
        raise ValueError(f"baseline report not found: {baseline}")
    base = by_strategy[baseline]
    base_summary = base.get("summary", {})
    base_fixtures = fixture_map(base)
    rows = []
    for strategy, report in sorted(by_strategy.items()):
        summary = report.get("summary", {})
        fmap = fixture_map(report)
        fixed_fixtures = []
        regressed_fixtures = []
        for fixture_id, base_row in base_fixtures.items():
            row = fmap.get(fixture_id, {})
            if not base_row.get("passed") and row.get("passed"):
                fixed_fixtures.append(fixture_id)
            if base_row.get("passed") and not row.get("passed"):
                regressed_fixtures.append(fixture_id)
        delta_passed = int(summary.get("passed", 0)) - int(base_summary.get("passed", 0))
        delta_temporal = int(summary.get("temporal_correct", 0)) - int(base_summary.get("temporal_correct", 0))
        delta_source = int(summary.get("source_supported", 0)) - int(base_summary.get("source_supported", 0))
        score = (delta_passed * 10) + (delta_temporal * 3) + (delta_source * 3) - (len(regressed_fixtures) * 20)
        rows.append(
            {
                "strategy": strategy,
                "status": report.get("status"),
                "passed": summary.get("passed", 0),
                "block": summary.get("block", 0),
                "temporal_correct": summary.get("temporal_correct", 0),
                "source_supported": summary.get("source_supported", 0),
                "delta_passed": delta_passed,
                "delta_temporal_correct": delta_temporal,
                "delta_source_supported": delta_source,
                "fixed_fixtures": fixed_fixtures,
                "regressed_fixtures": regressed_fixtures,
                "score": score,
                "path": display_path(Path(report.get("_path"))),
            }
        )
    candidates = [row for row in rows if row["strategy"] != baseline]
    complexity = {
        "temporal-local": 1,
        "graph-path-local": 2,
        "dual-level-local": 3,
        "memory-class-local": 4,
    }
    winner = sorted(
        candidates,
        key=lambda row: (-row["score"], -row["delta_passed"], complexity.get(row["strategy"], 99), row["strategy"]),
    )[0] if candidates else None
    return {
        "schema_version": SCHEMA_VERSION,
        "baseline": baseline,
        "winner": winner,
        "rows": rows,
        "decision": decision_from_winner(winner),
    }


def decision_from_winner(winner: dict[str, Any] | None) -> dict[str, Any]:
    if not winner:
        return {"next_port": None, "reason": "no candidate reports"}
    strategy = winner["strategy"]
    if strategy == "graph-path-local":
        return {
            "next_port": "M1+M3",
            "reason": "graph-path-local is the smallest passing mode: it fixes temporal freshness and multi-hop support chains without requiring dual-level ranking or memory_class overlay.",
        }
    if strategy == "temporal-local":
        return {"next_port": "M1", "reason": "temporal-local has the best non-passing delta and should land before ranking changes."}
    if strategy == "dual-level-local":
        return {"next_port": "M1+M3+M2", "reason": "dual-level-local wins only if graph path also required; port after schema/path support."}
    if strategy == "memory-class-local":
        return {"next_port": "M1+M3+M2+M4", "reason": "memory-class overlay should remain last unless it is the sole winning delta."}
    return {"next_port": strategy, "reason": "highest score vs baseline"}


def markdown_table(comparison: dict[str, Any]) -> str:
    lines = [
        "| Strategy | Status | Passed | Blocks | ΔPassed | ΔTemporal | ΔSource | Score | Fixed fixtures |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in comparison["rows"]:
        lines.append(
            f"| `{row['strategy']}` | {row['status']} | {row['passed']} | {row['block']} | {row['delta_passed']} | {row['delta_temporal_correct']} | {row['delta_source_supported']} | {row['score']} | {', '.join(row['fixed_fixtures']) or '-'} |"
        )
    return "\n".join(lines) + "\n"
