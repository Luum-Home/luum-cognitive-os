"""Unit coverage for reserved empty pytest lanes in pytest-with-summary.sh."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1].parent
WRAPPER = PROJECT_ROOT / "scripts" / "pytest-with-summary.sh"


def test_reserved_empty_cost_lane_is_reported_as_ok(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty-arena"
    empty_dir.mkdir()
    report_dir = tmp_path / "reports"
    env = {
        **os.environ,
        "COS_TEST_REPORT_DIR": str(report_dir),
        "PYTEST_BIN": f"{sys.executable} -m pytest",
    }

    result = subprocess.run(
        [
            "bash",
            str(WRAPPER),
            "--workers",
            "0",
            "--lane",
            "arena",
            "--",
            str(empty_dir),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    latest = report_dir / "latest"
    run_dir = latest.resolve()
    summary = (run_dir / "summary.txt").read_text()
    policy = json.loads((run_dir / "resource-policy.json").read_text())

    assert "Empty reserved lane: true" in summary
    assert policy["outcome"] == "empty_reserved_lane"
