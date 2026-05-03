#!/usr/bin/env python3
# SCOPE: both
"""Exercise the LLM dispatch and task-history metrics paths offline.

This does not call external providers. It invokes the real dispatch() control
flow with a deterministic local provider shim, then appends one historical task
record so cost prediction has a real JSONL data point to read.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.dispatch import dispatch


def _local_success(prompt: str, **_: Any) -> dict[str, Any]:
    tokens_in = max(1, len(prompt.split()))
    return {
        "success": True,
        "text": "offline dispatch smoke ok",
        "tokens_in": tokens_in,
        "tokens_out": 5,
        "cost_usd": 0.0,
        "error": "",
        "model": "offline-smoke",
        "provider_label": "offline_dispatch_smoke",
    }


def append_task_history(root: Path, prompt: str) -> Path:
    metrics = root / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    path = metrics / "task-history.jsonl"
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "description": prompt,
        "task_type": "governance-smoke",
        "phases_executed": ["dispatch-smoke"],
        "total_cost_usd": 0.0,
        "tokens_in": max(1, len(prompt.split())),
        "tokens_out": 5,
        "models_used": {"offline-smoke": 1},
        "duration_minutes": 0.01,
        "files_changed": 0,
        "source": "scripts/cos-dispatch-smoke",
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def build_report(root: Path = REPO_ROOT, prompt: str = "COS dispatch smoke exercises cost metrics") -> dict[str, Any]:
    result = dispatch(
        prompt,
        providers=["qwen"],
        task_type="governance-smoke",
        skill_name="cos-dispatch-smoke",
        _qwen_fn=_local_success,
    )
    history_path = append_task_history(root, prompt)
    dispatch_path = root / ".cognitive-os" / "metrics" / "llm-dispatch.jsonl"
    return {
        "status": "pass" if result.success and dispatch_path.exists() and history_path.exists() else "fail",
        "provider_used": result.provider_used,
        "model": result.model,
        "dispatch_metrics": str(dispatch_path),
        "task_history": str(history_path),
        "tokens_in": result.input_tokens,
        "tokens_out": result.output_tokens,
        "cost_usd": result.cost_usd,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--prompt", default="COS dispatch smoke exercises cost metrics")
    args = parser.parse_args(argv)
    report = build_report(REPO_ROOT, args.prompt)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"dispatch smoke: {report['status']} provider={report['provider_used']} model={report['model']}")
        print(f"- {report['dispatch_metrics']}")
        print(f"- {report['task_history']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
