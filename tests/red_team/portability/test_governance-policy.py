# SCOPE: os-only
"""Portability proof for hooks/_lib/governance-policy.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "hooks/_lib/governance-policy.sh"


def test_governance_policy_sources_and_fails_open_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: shared helper must source and not require the OS repo cwd."""
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
    })
    result = subprocess.run(
        ["bash", "-c", f"source {ARTIFACT!s}; cos_governance_policy_allows_block destructive-git"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
