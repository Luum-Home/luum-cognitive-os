# SCOPE: os-only
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/cos_lean_skillopt.py"


def test_cos_lean_skillopt_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_cos_lean_skillopt_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    result = subprocess.run([sys.executable, str(ARTIFACT), "--help"], cwd=tmp_path, text=True, capture_output=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr or result.stdout
