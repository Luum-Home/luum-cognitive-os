# SCOPE: os-only
"""Portability proof for hooks/_lib/remediation.sh."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "hooks/_lib/remediation.sh"


def test_remediation_sources_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: shell helper must source without requiring OS repo cwd."""
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COS_METRICS_DIR": str(tmp_path / ".cognitive-os" / "metrics"),
    })
    result = subprocess.run(
        ["bash", "-c", f"source {ARTIFACT!s}"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
