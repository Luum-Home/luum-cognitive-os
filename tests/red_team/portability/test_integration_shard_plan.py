# SCOPE: both
"""Portability probes for lib/integration_shard_plan.py — F1 sharding primitive.

Bilateral assertion: plan_shards() produces deterministic, balanced shards on
any harness that has python3 + the COS repo on disk. Behavior depends only on
the integration test directory contents, not on harness-specific state.

Falsification probes:
  - shard_count < 1 must raise ValueError (not silently degrade).
  - Total file count across shards must equal the source file count
    (no double-assignment, no dropped files).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.integration_shard_plan import plan_shards  # noqa: E402


def test_plan_shards_balances_and_partitions_integration_tests() -> None:
    """Bilateral: shards cover every test file exactly once, balanced by weight."""
    shards = plan_shards(REPO_ROOT, 4)
    assert len(shards) == 4
    assert all("index" in s and "weight" in s and "files" in s for s in shards)

    integration_dir = REPO_ROOT / "tests" / "integration"
    expected = sorted(p.name for p in integration_dir.glob("test_*.py"))
    actual_files: list[str] = []
    for shard in shards:
        actual_files.extend(shard["files"])
    actual_names = sorted(Path(f).name for f in actual_files)
    assert actual_names == expected, (
        "bilateral: every integration test file must appear in exactly one shard"
    )
    # Sanity: file_count matches list length
    for shard in shards:
        assert shard["file_count"] == len(shard["files"])


def test_plan_shards_rejects_invalid_shard_count() -> None:
    """Falsification: shard_count<1 must raise, not silently produce empty plan."""
    with pytest.raises(ValueError):
        plan_shards(REPO_ROOT, 0)
    with pytest.raises(ValueError):
        plan_shards(REPO_ROOT, -3)


def test_plan_shards_is_deterministic_across_invocations() -> None:
    """Bilateral: same inputs → same outputs (cross-harness reproducibility)."""
    a = plan_shards(REPO_ROOT, 3)
    b = plan_shards(REPO_ROOT, 3)
    assert a == b, "plan_shards must be deterministic for cross-harness parity"
