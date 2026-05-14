# SCOPE: os-only
"""Portability proof for hooks/network-egress-guard.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "hooks/network-egress-guard.sh"


def test_network_egress_guard_passes_unrelated_tool_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: hook must not depend on OS repo cwd for passthrough input."""
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(tmp_path / "probe.txt")}}
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COS_METRICS_DIR": str(tmp_path / ".cognitive-os" / "metrics"),
        "COS_PRIVATE_MODE": "0",
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
