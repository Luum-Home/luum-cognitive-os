#!/usr/bin/env python3
# SCOPE: both
"""Estimate AI resource budget before expensive agentic work."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CHARS_PER_TOKEN = 4
DEFAULT_TOKEN_BUDGET = 8000
DEFAULT_AGENT_COST_USD = 0.15


def estimate_path_tokens(paths: Iterable[str], root: Path = ROOT) -> tuple[int, int]:
    total_chars = 0
    file_count = 0
    for raw in paths:
        path = (root / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
        if not path.exists() or path.is_dir():
            continue
        try:
            total_chars += len(path.read_text(encoding="utf-8", errors="replace"))
            file_count += 1
        except OSError:
            continue
    return max(1, total_chars // CHARS_PER_TOKEN), file_count


def loop_risk(expected_tests: int, expected_agents: int, context_tokens: int) -> str:
    score = 0
    if expected_tests > 20:
        score += 1
    if expected_agents > 3:
        score += 1
    if context_tokens > DEFAULT_TOKEN_BUDGET * 2:
        score += 1
    return "high" if score >= 2 else "medium" if score == 1 else "low"


def build_preflight(task: str, paths: list[str], expected_agents: int, expected_tests: int, token_budget: int) -> dict[str, object]:
    path_tokens, file_count = estimate_path_tokens(paths)
    task_tokens = max(1, len(task) // CHARS_PER_TOKEN)
    context_tokens = path_tokens + task_tokens
    estimated_cost = round((context_tokens / max(1, DEFAULT_TOKEN_BUDGET)) * DEFAULT_AGENT_COST_USD * max(1, expected_agents), 4)
    risk = loop_risk(expected_tests, expected_agents, context_tokens)
    pct = int(context_tokens * 100 / max(1, token_budget))
    if pct >= 95 or risk == "high":
        status = "block"
        actions = ["split_task", "local_search_first", "plan_without_execution"]
    elif pct >= 80 or risk == "medium":
        status = "warn"
        actions = ["use_cheaper_model", "local_search_first", "ask_for_confirmation"]
    else:
        status = "pass"
        actions = ["proceed_with_budget_metering"]
    return {
        "schema_version": "ai-budget-preflight/v1",
        "status": status,
        "estimates": {
            "context_tokens": context_tokens,
            "file_count": file_count,
            "expected_agents": expected_agents,
            "expected_tests": expected_tests,
            "estimated_cost_usd": estimated_cost,
            "loop_risk": risk,
            "budget_percent": pct,
        },
        "recommended_actions": actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="")
    parser.add_argument("--paths", nargs="*", default=[])
    parser.add_argument("--expected-agents", type=int, default=1)
    parser.add_argument("--expected-tests", type=int, default=0)
    parser.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-block", action="store_true")
    args = parser.parse_args()
    report = build_preflight(args.task, args.paths, args.expected_agents, args.expected_tests, args.token_budget)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"ai-budget-preflight: {report['status']} {report['estimates']}")
        print("actions: " + ", ".join(report["recommended_actions"]))
    return 2 if args.fail_block and report["status"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
