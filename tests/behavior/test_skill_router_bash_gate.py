"""Behavior tests for hooks/skill-router-bash-gate.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = PROJECT_ROOT / "hooks" / "skill-router-bash-gate.sh"


def _run_hook(command: str) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT),
            "COGNITIVE_OS_PROJECT_DIR": str(PROJECT_ROOT),
        },
        check=False,
    )


def test_blocks_direct_dependency_upgrade_bypass() -> None:
    result = _run_hook("brew upgrade gentleman-programming/tap/engram")
    assert result.returncode == 2
    assert "SKILL ROUTER BASH GATE: BLOCK" in result.stderr
    assert "/deps-update --audit" in result.stderr


def test_allows_explicit_operator_override() -> None:
    result = _run_hook("COS_ALLOW_SKILL_BYPASS=1 brew upgrade gentleman-programming/tap/engram")
    assert result.returncode == 0
    assert "BLOCK" not in result.stderr


def test_allows_non_dependency_commands() -> None:
    result = _run_hook("python3 -m pytest tests/audit/test_hook_enforced_exclusions.py -q")
    assert result.returncode == 0
    assert "BLOCK" not in result.stderr
