# SCOPE: both
"""Contract tests for ADR-311 subagent budget enforcement."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "subagent-budget-enforcer.sh"


def _run_hook(tmp_path: Path, payload: dict, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
            "COGNITIVE_OS_SESSION_ID": "session-a",
            "COGNITIVE_OS_SESSION_KIND": "subagent",
            "COGNITIVE_OS_HOOK_AGENT_ID": "agent-a",
            "COS_SUBAGENT_TOOL_CALL_BUDGET": "2",
        }
    )
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )


def test_subagent_budget_blocks_after_configured_budget(tmp_path: Path) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo ok"}}

    first = _run_hook(tmp_path, payload)
    second = _run_hook(tmp_path, payload)
    third = _run_hook(tmp_path, payload)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert "WARN" in second.stderr
    assert third.returncode == 2
    assert "BLOCK" in third.stderr
    assert "ESCALATION:" in third.stderr

    metrics = tmp_path / ".cognitive-os" / "metrics" / "subagent-budget-enforcer.jsonl"
    assert metrics.exists()
    assert '"action": "block"' in metrics.read_text()

    resource_ledger = tmp_path / ".cognitive-os" / "metrics" / "ai-resource-ledger.jsonl"
    rows = [json.loads(line) for line in resource_ledger.read_text().splitlines()]
    assert [row["kind"] for row in rows] == [
        "subagent_budget_warn",
        "subagent_budget_block",
    ]
    assert rows[-1]["source"] == "subagent-budget-enforcer"
    assert rows[-1]["tool_calls"] == 3


def test_subagent_budget_allows_structured_escalation_after_budget(tmp_path: Path) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo ok"}}
    escalation_payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "printf 'ESCALATION: handing off with diagnosis'"},
    }

    assert _run_hook(tmp_path, payload).returncode == 0
    assert _run_hook(tmp_path, payload).returncode == 0
    escalation = _run_hook(tmp_path, escalation_payload)

    assert escalation.returncode == 0, escalation.stderr


def test_subagent_budget_ignores_orchestrator_sessions(tmp_path: Path) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "echo ok"}}
    result = _run_hook(
        tmp_path,
        payload,
        {
            "COGNITIVE_OS_SESSION_KIND": "orchestrator",
            "COGNITIVE_OS_HOOK_AGENT_ID": "",
            "CLAUDE_AGENT_ID": "",
            "CODEX_AGENT_ID": "",
            "COGNITIVE_OS_AGENT_ID": "",
        },
    )

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / ".cognitive-os" / "sessions" / "session-a" / "subagent-tool-calls-agent-a").exists()
