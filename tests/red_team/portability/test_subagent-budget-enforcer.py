# SCOPE: os-only
"""Portability proof for hooks/subagent-budget-enforcer.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "hooks/subagent-budget-enforcer.sh"


def test_subagent_budget_enforcer_passes_orchestrator_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: hook must not require COS repo cwd for non-subagent sessions."""
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo ok"}, "session_kind": "orchestrator"}
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "CODEX_PROJECT_DIR": str(tmp_path),
            "CLAUDE_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_SESSION_ID": "portable-session",
            "COGNITIVE_OS_SESSION_KIND": "orchestrator",
            "COS_PRIVATE_MODE": "0",
        }
    )
    for key in ("COGNITIVE_OS_HOOK_AGENT_ID", "CLAUDE_AGENT_ID", "CODEX_AGENT_ID", "COGNITIVE_OS_AGENT_ID", "COS_AGENT_ID"):
        env.pop(key, None)

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
