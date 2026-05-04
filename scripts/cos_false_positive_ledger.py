#!/usr/bin/env python3
# SCOPE: both
"""Summarize hook false-positive signals from metrics."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
METRICS = REPO_ROOT / ".cognitive-os" / "metrics"
FALSE_POSITIVE_FLAG_FIELDS = ("false_positive", "operator_bypass", "overrode", "bypassed")
FALSE_POSITIVE_REASON_FIELDS = (
    "bypass_reason",
    "override_reason",
    "false_positive_reason",
    "operator_bypass_reason",
)
FALSE_POSITIVE_ENUM_FIELDS = (
    "event",
    "event_type",
    "type",
    "kind",
    "action",
    "status",
    "decision",
    "outcome",
    "classification",
)
FALSE_POSITIVE_ENUM_VALUES = (
    "false_positive",
    "false-positive",
    "operator_bypass",
    "operator-bypass",
    "bypass",
    "bypassed",
    "override",
    "overrode",
)
FALSE_POSITIVE_REASON_TOKENS = ("false positive", "false-positive", "operator bypass", "operator-bypass")
DEFAULT_WINDOW_HOURS = 24


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


def parse_ts(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def hook_name(event: dict[str, Any], fallback: str) -> str:
    for key in ("hook", "hook_name", "component", "gate"):
        value = event.get(key)
        if isinstance(value, str) and value:
            return value
    return fallback.removesuffix(".jsonl")


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _normalized(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def is_false_positive_event(event: dict[str, Any]) -> bool:
    """Return true only for scoped false-positive/bypass signals.

    Do not scan the entire payload: runtime reports can legitimately contain
    filenames such as ``adaptive-bypass.jsonl`` or documentation snippets.
    Counting those strings as operator bypasses inflates the ledger with
    false-positives about false-positives.
    """

    for key in FALSE_POSITIVE_FLAG_FIELDS:
        if key in event and _truthy(event[key]):
            return True

    for key in FALSE_POSITIVE_REASON_FIELDS:
        value = _normalized(event.get(key))
        if value:
            return True

    for key in FALSE_POSITIVE_ENUM_FIELDS:
        value = _normalized(event.get(key))
        if value in FALSE_POSITIVE_ENUM_VALUES:
            return True
        if any(token in value for token in FALSE_POSITIVE_REASON_TOKENS):
            return True

    return False


def build_report(metrics_dir: Path = METRICS, *, window_hours: int = DEFAULT_WINDOW_HOURS) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    events = 0
    now = datetime.now(timezone.utc).timestamp()
    since = now - (window_hours * 3600) if window_hours > 0 else None
    files = sorted(metrics_dir.glob("*.jsonl")) if metrics_dir.exists() else []
    for path in files:
        for event in iter_jsonl(path):
            if since is not None:
                ts = parse_ts(event.get("timestamp") or event.get("ts") or event.get("created_at"))
                if ts is not None and ts < since:
                    continue
            events += 1
            if is_false_positive_event(event):
                counter[hook_name(event, path.name)] += 1
    total = sum(counter.values())
    return {
        "status": "pass" if total == 0 else "warn",
        "window_hours": window_hours,
        "metrics_files": len(files),
        "events_scanned": events,
        "false_positive_events": total,
        "top_hooks": [{"hook": hook, "count": count} for hook, count in counter.most_common(10)],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-dir", type=Path, default=METRICS)
    parser.add_argument("--window-hours", type=int, default=DEFAULT_WINDOW_HOURS)
    args = parser.parse_args(argv)
    print(json.dumps(build_report(args.metrics_dir, window_hours=args.window_hours), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
