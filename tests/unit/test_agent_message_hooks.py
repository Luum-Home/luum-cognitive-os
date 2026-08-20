from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from cos_lib.agent_message_bus import send_message

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
    send_message(tmp_path, from_session="auditor", to_session="operator", message_type="audit_finding", severity="warn", target="cos_lib/x.py", body="Check edge case")
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path), "COGNITIVE_OS_SESSION_ID": "operator"}

    res = subprocess.run(["bash", str(CONTEXT)], text=True, capture_output=True, env=env, timeout=10)

    assert res.returncode == 0
    out = json.loads(res.stdout)
    # Claude Code reads additionalContext ONLY from inside hookSpecificOutput
    # (contract: manifests/claude-code-hooks-schema.yaml). The root-level form
    # is valid JSON, so the host parses it, recognises no field, and drops the
    # context without a word. Asserting the root-level key -- as this test did
    # until 5d9c1ee1b fixed the hook -- certifies exactly the defect that made
    # the inbox invisible. Assert the delivered shape, and assert the discarded
    # one is absent so this cannot silently regress back to it.
    assert "additionalContext" not in out, (
        "root-level additionalContext is dropped by the host; emitting it is the bug"
    )
    specific = out["hookSpecificOutput"]
    assert specific["hookEventName"] == "UserPromptSubmit"
    assert "Pending directed agent messages" in specific["additionalContext"]
    assert "Check edge case" in specific["additionalContext"]
