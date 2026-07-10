"""Shared helpers for primitive readiness ledgers."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml


def load_lifecycle(root: Path) -> dict[str, dict[str, Any]]:
    """Load primitive lifecycle rows by primitive id."""
    manifest = root / "manifests" / "primitive-lifecycle.yaml"
    if not manifest.exists():
        return {}
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    rows: dict[str, dict[str, Any]] = {}
    for primitive in data.get("primitives", []):
        pid = primitive.get("id")
        if isinstance(pid, str):
            rows[pid] = primitive
    return rows


def family_counts(consumers: list[Any]) -> dict[str, int]:
    """Count consumers by family with stable key ordering."""
    counts: dict[str, int] = {}
    for consumer in consumers:
        counts[consumer.family] = counts.get(consumer.family, 0) + 1
    return dict(sorted(counts.items()))


def row_to_dict(row: Any) -> dict[str, Any]:
    """Convert readiness row dataclass and nested consumers to dictionaries."""
    data = asdict(row)
    data["consumers"] = [asdict(consumer) for consumer in row.consumers]
    return data
