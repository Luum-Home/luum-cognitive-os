#!/usr/bin/env python3
# SCOPE: os-only
"""Render a workstation/container benchmark comparison report.

The script is deliberately report-only: it does not invoke agents, containers,
or provider APIs. Operators run the same fixture workload in workstation and
container environments, record compact JSON results, then use this script to
compare overhead, catch value, and artifact quality.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RunRow:
    fixture_id: str
    environment: str
    mode: str
    success: bool
    elapsed_ms: int
    cost_usd: float
    catch_value: str
    artifact_quality: str
    notes: str = ""


def load_rows(path: Path) -> list[RunRow]:
    """Load benchmark rows from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_rows = data.get("runs", data if isinstance(data, list) else [])
    if not isinstance(raw_rows, list):
        raise ValueError("input JSON must be a list or object with a 'runs' list")
    rows: list[RunRow] = []
    for raw in raw_rows:
        rows.append(
            RunRow(
                fixture_id=str(raw["fixture_id"]),
                environment=str(raw["environment"]),
                mode=str(raw["mode"]),
                success=bool(raw.get("success", False)),
                elapsed_ms=int(raw.get("elapsed_ms", 0)),
                cost_usd=float(raw.get("cost_usd", 0.0)),
                catch_value=str(raw.get("catch_value", "not-recorded")),
                artifact_quality=str(raw.get("artifact_quality", "not-recorded")),
                notes=str(raw.get("notes", "")),
            )
        )
    return rows


def render_report(rows: list[RunRow], out_path: Path) -> None:
    """Write a Markdown comparison report."""
    by_fixture: dict[str, list[RunRow]] = {}
    for row in rows:
        by_fixture.setdefault(row.fixture_id, []).append(row)

    lines = [
        f"# Workstation/container benchmark comparison — {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "Scope: workstation and container only. Kubernetes/cluster benchmarks remain deferred.",
        "",
        "## Summary table",
        "",
        "| Fixture | Environment | Mode | Success | Elapsed | Cost | Catch value | Artifact quality |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.fixture_id} | {row.environment} | {row.mode} | "
            f"{str(row.success).lower()} | {row.elapsed_ms}ms | "
            f"${row.cost_usd:.4f} | {row.catch_value} | {row.artifact_quality} |"
        )

    lines.extend(["", "## Fixture comparisons"])
    for fixture_id, fixture_rows in sorted(by_fixture.items()):
        lines.extend(["", f"### {fixture_id}"])
        workstation = [r for r in fixture_rows if r.environment == "workstation"]
        container = [r for r in fixture_rows if r.environment == "container"]
        if workstation and container:
            fastest_workstation = min(r.elapsed_ms for r in workstation if r.elapsed_ms >= 0)
            fastest_container = min(r.elapsed_ms for r in container if r.elapsed_ms >= 0)
            delta = fastest_container - fastest_workstation
            lines.append(f"- Fastest container minus workstation latency: **{delta}ms**")
        else:
            lines.append("- Latency delta: not available until both environments are recorded.")
        for row in fixture_rows:
            if row.notes:
                lines.append(f"- {row.environment}/{row.mode}: {row.notes}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON file with benchmark run rows")
    parser.add_argument("--output", required=True, help="Markdown report path")
    args = parser.parse_args(argv)

    rows = load_rows(Path(args.input))
    render_report(rows, Path(args.output))
    print(f"Report → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
