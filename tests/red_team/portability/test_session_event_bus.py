# SCOPE: os-only
"""Portability proof for scripts/session_event_bus.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/session_event_bus.py"


def test_session_event_bus_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: script must not depend on OS repo cwd for safe invocation."""
    result = subprocess.run(
        [sys.executable, str(ARTIFACT), "--project-dir", str(tmp_path), "tail", "--limit", "1"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
