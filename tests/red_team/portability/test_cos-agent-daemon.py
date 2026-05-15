# SCOPE: os-only
"""Portability proof for scripts/cos-agent-daemon."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/cos-agent-daemon"


def test_cos_agent_daemon_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: script must not depend on OS repo cwd for safe invocation."""
    result = subprocess.run(
        [sys.executable, str(ARTIFACT), "--help"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "usage:" in (result.stdout + result.stderr).lower()


def test_cos_agent_daemon_has_passing_scope_contract() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/primitive_scope_classifier.py",
            "--project-dir",
            ".",
            "--paths",
            "scripts/cos-agent-daemon",
            "--fail-contradictions",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert '"by_effective_scope": {"both": 1}' in result.stdout
