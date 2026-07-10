# SCOPE: both
"""Plan/run shardable laptop integration validation.

This is the F1 sizing primitive for the historically slow
`make test-laptop-integration` lane. It splits tests/integration files into
stable size-balanced shards so broad-release attestations can run under bounded
wall-clock time instead of one 900s-prone serial sweep.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

def _files(root: Path) -> list[Path]:
    return sorted((root / "tests" / "integration").glob("test_*.py"))


def _weight(path: Path) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 1
    tests = text.count("def test_") + text.count("async def test_")
    return max(1, tests) + max(0, len(text) // 12_000)


def plan_shards(root: str | Path, shard_count: int) -> list[dict[str, Any]]:
    root_path = Path(root).resolve()
    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    shards = [{"index": i, "weight": 0, "files": []} for i in range(shard_count)]
    for path in sorted(_files(root_path), key=lambda item: (-_weight(item), item.name)):
        target = min(shards, key=lambda row: (row["weight"], row["index"]))
        target["files"].append(str(path.relative_to(root_path)))
        target["weight"] += _weight(path)
    for shard in shards:
        shard["file_count"] = len(shard["files"])
    return shards
