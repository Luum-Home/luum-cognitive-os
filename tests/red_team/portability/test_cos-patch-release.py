# SCOPE: os-only
"""Portability proof for scripts/cos-patch-release."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts" / "cos-patch-release"


def test_cos_patch_release_safe_invocation_from_arbitrary_project_root(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "CODEX_PROJECT_DIR": str(tmp_path),
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "PYTHONPATH": str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
        }
    )

    result = subprocess.run(
        [str(ARTIFACT), "--help"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "prepare" in output
    assert "publish" in output
    assert "Traceback" not in output
