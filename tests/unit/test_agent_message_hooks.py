from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from lib.agent_message_bus import send_message

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "hooks" / "agent-message-inbox-guard.sh"
CONTEXT = REPO / "hooks" / "agent-message-inbox-context.sh"


def test_guard_warn_mode_does_not_block_non_risky_bash(tmp_path: Path) -> None:
    send_message(tmp_path, from_session="auditor", to_session="operator", message_type="audit_finding", severity="block", body="Fix before commit")
    payload = {"tool_name": "Bash", "tool_input": {"command": "git status"}}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "operator", "COS_AGENT_MESSAGE_GUARD_MODE": "block"}

    res = subprocess.run(["bash", str(GUARD)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)

    assert res.returncode == 0


def test_guard_blocks_risky_git_when_blocker_exists(tmp_path: Path) -> None:
    send_message(tmp_path, from_session="auditor", to_session="operator", message_type="audit_finding", severity="block", body="Fix before commit")
    payload = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}}
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "operator", "COS_AGENT_MESSAGE_GUARD_MODE": "block"}

    res = subprocess.run(["bash", str(GUARD)], input=json.dumps(payload), text=True, capture_output=True, env=env, timeout=10)

    assert res.returncode == 2
    assert "blocking risky operation" in res.stderr


def test_context_hook_emits_pending_messages(tmp_path: Path) -> None:
    send_message(tmp_path, from_session="auditor", to_session="operator", message_type="audit_finding", severity="warn", target="lib/x.py", body="Check edge case")
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "operator"}

    res = subprocess.run(["bash", str(CONTEXT)], text=True, capture_output=True, env=env, timeout=10)

    assert res.returncode == 0
    out = json.loads(res.stdout)
    assert "Pending directed agent messages" in out["additionalContext"]
    assert "Check edge case" in out["additionalContext"]
