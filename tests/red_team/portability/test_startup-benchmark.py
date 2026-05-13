# SCOPE: os-only
"""Portability proof for scripts/startup-benchmark.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "startup-benchmark.sh"


def test_startup_benchmark_writes_metrics_under_supplied_project_dir(tmp_path: Path) -> None:
    """Falsification probe: benchmark output must follow --project-dir, not repo root."""
    (tmp_path / ".claude").mkdir(parents=True)
    (tmp_path / ".claude" / "settings.json").write_text('{"hooks":{"SessionStart":[]}}', encoding="utf-8")
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--project-dir", str(tmp_path)],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    metric = tmp_path / ".cognitive-os" / "metrics" / "startup-benchmark.jsonl"
    assert metric.exists()
    row = json.loads(metric.read_text(encoding="utf-8").splitlines()[-1])
    assert row["project_dir"] == str(tmp_path)
