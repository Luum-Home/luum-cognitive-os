# SCOPE: os-only
"""Portability proof for scripts/cos-agent-flicker-report."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/cos-agent-flicker-report"


def test_cos_agent_flicker_report_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_wrapper_runs_json_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: wrapper must accept an arbitrary project root."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    result = subprocess.run(
        [str(ARTIFACT), "--project-dir", str(tmp_path), "--json"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode in {0, 2}, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "agent-flicker-control-report/v1"
    assert payload["summary"]["control_count"] == 10
