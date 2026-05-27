# SCOPE: os-only
"""Portability proof for hooks/research-compliance-guard.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "hooks" / "research-compliance-guard.sh"


def test_research_compliance_guard_safe_from_arbitrary_project_root(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "CODEX_PROJECT_DIR": str(tmp_path),
            "CLAUDE_PROJECT_DIR": str(tmp_path),
        }
    )
    payload = json.dumps({"tool_input": {"command": "git commit -m portability"}})
    result = subprocess.run(
        ["bash", str(ARTIFACT)],
        input=payload,
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
