# SCOPE: os-only
"""Portability proof for hooks/bash-hot-path-dispatcher.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "bash-hot-path-dispatcher.sh"


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


def test_safe_bash_command_allows_in_arbitrary_project(tmp_path: Path) -> None:
    result = _run(tmp_path, "printf hello")
    assert result.returncode == 0, result.stderr


def test_dependency_mutation_routes_to_hard_gate(tmp_path: Path) -> None:
    result = _run(tmp_path, "pip install --upgrade requests")
    assert result.returncode == 2
    assert "Direct dependency/toolchain upgrade command detected" in result.stderr
