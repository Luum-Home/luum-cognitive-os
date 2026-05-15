# SCOPE: os-only
"""Portability proof for scripts/ai_budget_preflight.py and wrapper."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE = REPO_ROOT / "scripts/ai_budget_preflight.py"
WRAPPER = REPO_ROOT / "scripts/ai-budget-preflight"


def test_ai_budget_preflight_safe_from_arbitrary_project_root(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "PYTHONPATH": str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
    })
    for command in ([sys.executable, str(MODULE), "--json"], [str(WRAPPER), "--json"]):
        result = subprocess.run(command, text=True, capture_output=True, cwd=tmp_path, env=env, timeout=20, check=False)
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        assert "ai-budget-preflight/v1" in output
        assert "Traceback" not in output
