"""Behavior tests for ADR-214 Bash gate integration."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior
PROJECT_ROOT = Path(__file__).resolve().parents[2]
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


def test_bash_gate_blocks_ad_hoc_license_audit_toolchain() -> None:
    result = _run_hook("pip-licenses --format=json && go-licenses report ./...")

    assert result.returncode == 2
    assert "TOOL DISCOVERY PRE-USE GATE: BLOCK" in result.stderr
    assert "scripts/agentic-tool-license-matrix.sh" in result.stderr


def test_bash_gate_allows_canonical_cos_license_primitive() -> None:
    result = _run_hook("bash scripts/agentic-tool-license-matrix.sh --json")

    assert result.returncode == 0
    assert "TOOL DISCOVERY PRE-USE GATE: BLOCK" not in result.stderr


def test_bash_gate_allows_explicit_tool_discovery_bypass() -> None:
    result = _run_hook("COS_ALLOW_TOOL_DISCOVERY_BYPASS=1 pip-licenses --format=json")

    assert result.returncode == 0
    assert "TOOL DISCOVERY PRE-USE GATE: BLOCK" not in result.stderr
