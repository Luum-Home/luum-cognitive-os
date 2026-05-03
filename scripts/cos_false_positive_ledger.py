#!/usr/bin/env python3
# SCOPE: both
"""Summarize hook false-positive signals from metrics."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
METRICS = REPO_ROOT / ".cognitive-os" / "metrics"
FALSE_POSITIVE_KEYS = ("false_positive", "bypass", "overrode", "operator_bypass")


def iter_jsonl(path: Path):
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
    except OSError:
        return


def hook_name(event: dict[str, Any], fallback: str) -> str:
    for key in ("hook", "hook_name", "component", "gate"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    return fallback.removesuffix(".jsonl")


def build_report(metrics_dir: Path = METRICS) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    events = 0
    files = sorted(metrics_dir.glob("*.jsonl")) if metrics_dir.exists() else []
    for path in files:
        for event in iter_jsonl(path):
            events += 1
            text = json.dumps(event, sort_keys=True).lower()
            if any(key in text for key in FALSE_POSITIVE_KEYS):
                counter[hook_name(event, path.name)] += 1
    total = sum(counter.values())
    return {
        "status": "pass" if total == 0 else "warn",
        "metrics_files": len(files),
        "events_scanned": events,
        "false_positive_events": total,
        "top_hooks": [{"hook": hook, "count": count} for hook, count in counter.most_common(10)],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-dir", type=Path, default=METRICS)
    args = parser.parse_args(argv)
    print(json.dumps(build_report(args.metrics_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
