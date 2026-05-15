# SCOPE: os-only
"""Portability proof for scripts/ai-resource-economy-audit wrapper."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER = REPO_ROOT / "scripts/ai-resource-economy-audit"


def test_ai_resource_economy_audit_wrapper_safe_from_arbitrary_project_root(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update({"PYTHONPATH": str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")})
    result = subprocess.run([str(WRAPPER), "--json"], text=True, capture_output=True, cwd=tmp_path, env=env, timeout=20, check=False)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "ai-resource-economy-audit/v1" in output
    assert "Traceback" not in output
