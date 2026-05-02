#!/usr/bin/env python3
# SCOPE: os-only
"""Run deterministic paired skill-efficacy smoke tasks.

This does not call models. It materializes paired baseline/with-skill records in
an isolated archive and renders the same report path used by live archives.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from lib.metric_event import MetricEvent, append_event
from lib.skill_efficacy import format_markdown, load_runs_from_archive, summarize_runs, task_fingerprint

DEFAULT_TASKS = PROJECT_ROOT / ".cognitive-os" / "tests" / "skill-efficacy" / "tasks.json"
DEFAULT_ARCHIVE = PROJECT_ROOT / ".cognitive-os" / "metrics" / "skill-efficacy-smoke.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / ".cognitive-os" / "reports" / "skill-efficacy-smoke-report.md"


def _append_record(path: Path, *, skill_name: str, task: str, payload: dict, enabled: bool) -> None:
    metadata = {
        "task_fingerprint": task_fingerprint(task),
        "skill_enabled": enabled,
        "latency_seconds": payload.get("latency_seconds", 0),
        "tool_calls": payload.get("tool_calls", 0),
        "regression": payload.get("regression", False),
        "security_findings": payload.get("security_findings", 0),
    }
    append_event(
        str(path),
        MetricEvent(
            source="skill-efficacy-smoke",
            event_type="skill.execution.recorded",
            payload={
                "skill_name": skill_name,
                "version": "smoke",
                "trust_score": 80 if payload.get("success") else 40,
                "success": bool(payload.get("success")),
                "task_description": task,
                "tokens_used": 0,
                "cost_usd": float(payload.get("cost_usd", 0.0)),
                "metadata": metadata,
            },
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", default=str(DEFAULT_TASKS))
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    tasks_path = Path(args.tasks)
    archive = Path(args.archive)
    report = Path(args.report)
    archive.parent.mkdir(parents=True, exist_ok=True)
    if args.reset and archive.exists():
        archive.unlink()
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    for task in data.get("tasks", []):
        _append_record(archive, skill_name=task["skill_name"], task=task["task"], payload=task["baseline"], enabled=False)
        _append_record(archive, skill_name=task["skill_name"], task=task["task"], payload=task["with_skill"], enabled=True)
    summaries = summarize_runs(load_runs_from_archive(archive))
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(format_markdown(summaries), encoding="utf-8")
    print(str(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
