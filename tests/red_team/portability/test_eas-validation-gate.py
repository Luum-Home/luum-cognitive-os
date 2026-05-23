# SCOPE: os-only
"""Portability proof for hooks/eas-validation-gate.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "hooks/eas-validation-gate.sh"


def test_eas_validation_gate_runs_noop_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: no-surface fast path must not depend on repo cwd."""
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
    })
    result = subprocess.run(
        ["bash", str(ARTIFACT)],
        input=json.dumps({"hook_event_name": "Stop"}),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert str(REPO_ROOT) not in result.stdout
    assert str(REPO_ROOT) not in result.stderr
