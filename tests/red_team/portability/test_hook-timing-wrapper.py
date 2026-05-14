# SCOPE: os-only
"""Portability proof for scripts/hook-timing-wrapper.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/hook-timing-wrapper.sh"


def test_hook_timing_wrapper_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: wrapper must not depend on OS repo cwd."""
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COS_HOOK_TIMING_DISABLE": "1",
    })
    result = subprocess.run(
        ["bash", str(ARTIFACT), "PreToolUse", "/bin/echo", "portability-ok"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "portability-ok" in result.stdout
