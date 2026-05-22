# SCOPE: os-only
"""Portability proof for scripts/context_budget_meter_fast.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/context_budget_meter_fast.py"


def test_context_budget_meter_fast_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: fast meter must not depend on OS repo cwd."""
    (tmp_path / "cognitive-os.yaml").write_text("context_budget:\n  user_max_tokens: 1000\n", encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "PYTHONPATH": str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
    })
    result = subprocess.run(
        [sys.executable, str(ARTIFACT), str(tmp_path), "portable-smoke"],
        input=json.dumps({"prompt": "hello", "tool_use_id": "tu1"}),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "No such file or directory" not in output
    assert "Traceback" not in output
    assert (tmp_path / ".cognitive-os" / "metrics" / "context-budget.jsonl").exists()
