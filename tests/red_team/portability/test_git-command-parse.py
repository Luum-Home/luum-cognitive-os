# SCOPE: os-only
"""Portability proof for hooks/_lib/git-command-parse.sh."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / 'hooks/_lib/git-command-parse.sh'


def test_git_command_parse_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: must not depend on OS repo cwd."""
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo portability-probe"}}
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "COS_METRICS_DIR": str(tmp_path / ".cognitive-os" / "metrics"),
    })
    result = subprocess.run(
        ["bash", str(ARTIFACT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
