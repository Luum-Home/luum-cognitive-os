# SCOPE: os-only
"""Portability proof for hooks/skill-router-bash-gate.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "skill-router-bash-gate.sh"


def _run(project: Path, command: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update({"CLAUDE_PROJECT_DIR": str(project), "COGNITIVE_OS_PROJECT_DIR": str(project)})
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(project),
        timeout=10,
    )


def test_safe_bash_command_allows_without_repo_skill_catalog(tmp_path: Path) -> None:
    """Falsification probe: generic suggestion path must not require COS skill catalog."""
    result = _run(tmp_path, "printf hello")
    assert result.returncode == 0, result.stderr
    assert "SKILL ROUTER" not in result.stderr


def test_dependency_upgrade_still_blocks_in_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: disabling generic suggestions must not disable hard gates."""
    result = _run(tmp_path, "pip install --upgrade requests")
    assert result.returncode == 2
    assert "Direct dependency/toolchain upgrade command detected" in result.stderr
