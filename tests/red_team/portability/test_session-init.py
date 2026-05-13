# SCOPE: os-only
"""Portability proof for hooks/session-init.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / "hooks" / "session-init.sh"


def test_session_init_creates_state_inside_consumer_project(tmp_path: Path) -> None:
    """Falsification probe: session state must be rooted in consumer project dir."""
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    result = subprocess.run(["bash", str(HOOK)], cwd=tmp_path, env=env, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    sessions = tmp_path / ".cognitive-os" / "sessions"
    assert sessions.exists()
    current_files = sorted(sessions.glob(".current-session-*"))
    assert current_files
    current = current_files[-1].read_text(encoding="utf-8").strip()
    meta = json.loads((sessions / current / "meta.json").read_text(encoding="utf-8"))
    assert meta["working_directory"] == str(tmp_path)
    assert (sessions / current / "tasks.json").exists()
