# SCOPE: os-only
"""Portability probes for scripts/cos-integration-shard-plan.

Bilateral assertion: invoking the script via python3 on any harness with
--shards N --json produces the integration-shard-plan/v1 envelope and
N shards covering every tests/integration/test_*.py file exactly once.

Falsification probes:
  - --run without --shard-index must error (argparse parser.error path).
  - --shard-index out of range must error (range guard is real, not a stub).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "cos-integration-shard-plan"


def test_cos_integration_shard_plan_emits_versioned_plan() -> None:
    """Bilateral: --json emits integration-shard-plan/v1 covering all files."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--shards", "3", "--json"],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "integration-shard-plan/v1"
    assert payload["shard_count"] == 3
    assert len(payload["shards"]) == 3

    integration_dir = REPO_ROOT / "tests" / "integration"
    expected = sorted(p.name for p in integration_dir.glob("test_*.py"))
    actual: list[str] = []
    for shard in payload["shards"]:
        actual.extend(shard["files"])
    actual_names = sorted(Path(f).name for f in actual)
    assert actual_names == expected, (
        "bilateral: every integration file must appear once across the shards"
    )


def test_cos_integration_shard_plan_selected_shard_in_payload() -> None:
    """Bilateral: --shard-index attaches a 'selected' shard to the payload."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--shards", "4", "--shard-index", "2", "--json"],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    assert payload["selected"]["index"] == 2


def test_cos_integration_shard_plan_rejects_run_without_index() -> None:
    """Falsification: --run requires --shard-index; bare --run must error."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--shards", "2", "--run"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode != 0, "falsification: --run without --shard-index must fail"


def test_cos_integration_shard_plan_rejects_out_of_range_index() -> None:
    """Falsification: --shard-index >= --shards must error."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--shards", "2", "--shard-index", "9", "--json"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode != 0, "falsification: out-of-range shard index must fail"
