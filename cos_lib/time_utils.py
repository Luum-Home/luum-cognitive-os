"""Shared timestamp helpers for Cognitive OS scripts."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    """Return UTC timestamp in COS JSONL format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(value: Any) -> float | None:
    """Parse numeric or ISO-ish timestamps into epoch seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None
