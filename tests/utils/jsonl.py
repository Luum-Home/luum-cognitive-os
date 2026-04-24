"""JSONL helpers for tests that read legacy or MetricEvent-wrapped rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def flatten_metric_event(row: dict[str, Any]) -> dict[str, Any]:
    """Return a legacy-flat row from either a raw dict or MetricEvent row."""
    if "schema_version" not in row or "event_type" not in row or "payload" not in row:
        return row
    payload = row.get("payload")
    if not isinstance(payload, dict):
        payload = {"legacy_payload": payload}
    flat = dict(payload)
    event_type = row.get("event_type", "")
    if isinstance(event_type, str) and event_type.startswith("consequence."):
        flat.setdefault("record_type", event_type.removeprefix("consequence."))
    flat.setdefault("timestamp", row.get("timestamp", ""))
    return flat


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read valid JSONL rows, flattening MetricEvent wrappers for legacy assertions."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(flatten_metric_event(json.loads(line)))
        except json.JSONDecodeError:
            continue
    return rows


def read_first_jsonl(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    if not rows:
        raise AssertionError(f"No JSONL rows found in {path}")
    return rows[0]
