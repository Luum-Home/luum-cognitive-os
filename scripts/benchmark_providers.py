#!/usr/bin/env python3
# SCOPE: os-only
"""No-cost provider benchmark harness for ADR-052.

The harness is intentionally safe by default: built-in `fixture-*` providers
exercise task-set parsing, scoring, JSONL output, and report generation without
calling external models. Real provider execution can be added behind explicit
provider adapters later without changing the metrics schema.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class BenchmarkResult:
    benchmark_id: str
    task_set: str
    task_id: str
    provider: str
    model: str
    passed: bool
    score: float
    cost_usd: float
    latency_ms: int
    evaluator: str


def load_tasks(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tasks = data.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        raise ValueError(f"{path}: expected non-empty tasks list")
    for task in tasks:
        if not isinstance(task, dict) or not task.get("id") or not task.get("prompt"):
            raise ValueError(f"{path}: every task needs id and prompt")
    return tasks


def fixture_response(provider: str, task: dict[str, Any]) -> str:
    keywords = " ".join(str(item) for item in task.get("expected_keywords", []))
    if provider.endswith("weak"):
        return f"generic response for {task['id']}"
    return f"{task['id']} response includes {keywords}".strip()


def score_response(response: str, task: dict[str, Any]) -> tuple[bool, float]:
    keywords = [str(item).lower() for item in task.get("expected_keywords", [])]
    if not keywords:
        return True, 1.0
    hits = sum(1 for keyword in keywords if keyword in response.lower())
    score = hits / len(keywords)
    return hits == len(keywords), score


def run_benchmark(task_set: Path, providers: list[str], benchmark_id: str | None = None) -> list[BenchmarkResult]:
    tasks = load_tasks(task_set)
    run_id = benchmark_id or datetime.now(timezone.utc).strftime("provider-benchmark-%Y%m%dT%H%M%SZ")
    results: list[BenchmarkResult] = []
    for provider in providers:
        for task in tasks:
            if not provider.startswith("fixture-"):
                response = ""
                passed = False
                score = 0.0
                evaluator = "adapter-unavailable"
            else:
                response = fixture_response(provider, task)
                passed, score = score_response(response, task)
                evaluator = "keyword-fixture"
            results.append(
                BenchmarkResult(
                    benchmark_id=run_id,
                    task_set=task_set.name,
                    task_id=str(task["id"]),
                    provider=provider,
                    model=provider,
                    passed=passed,
                    score=score,
                    cost_usd=0.0,
                    latency_ms=0,
                    evaluator=evaluator,
                )
            )
    return results


def summarize(results: list[BenchmarkResult]) -> dict[str, Any]:
    by_provider: dict[str, list[BenchmarkResult]] = {}
    for result in results:
        by_provider.setdefault(result.provider, []).append(result)
    return {
        provider: {
            "tasks_total": len(rows),
            "tasks_passed": sum(1 for row in rows if row.passed),
            "avg_score": round(sum(row.score for row in rows) / len(rows), 4) if rows else 0.0,
            "avg_cost_usd": round(sum(row.cost_usd for row in rows) / len(rows), 6) if rows else 0.0,
        }
        for provider, rows in sorted(by_provider.items())
    }


def write_jsonl(path: Path, results: list[BenchmarkResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(asdict(result), sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-set", required=True)
    parser.add_argument("--providers", required=True, help="Comma-separated providers; fixture-* providers are no-cost.")
    parser.add_argument("--output-jsonl", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    providers = [item.strip() for item in args.providers.split(",") if item.strip()]
    results = run_benchmark(Path(args.task_set), providers)
    if args.output_jsonl:
        write_jsonl(Path(args.output_jsonl), results)
    payload = {"summary": summarize(results), "results": [asdict(result) for result in results]}
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
