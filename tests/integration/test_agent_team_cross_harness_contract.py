from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COS = PROJECT_ROOT / "scripts" / "cos"


@pytest.mark.integration
def test_codex_and_claude_envs_share_same_agent_team_inbox(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    codex_env = {"COGNITIVE_OS_PROJECT_DIR": str(project), "CODEX_SESSION_ID": "codex-s1"}
    claude_env = {"COGNITIVE_OS_PROJECT_DIR": str(project), "CLAUDE_SESSION_ID": "claude-s1"}

    join_codex = subprocess.run(
        [str(COS), "team", "--json", "join", "--team", "release", "--session-id", "codex-s1", "--role", "codex", "--worktree-path", str(project)],
        cwd=PROJECT_ROOT,
        env=codex_env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert join_codex.returncode == 0, join_codex.stderr

    send = subprocess.run(
        [str(COS), "team", "--json", "handoff", "send", "--team", "release", "--from-agent", "codex-s1", "--to-agent", "claude-s1", "--text", "review handoff", "--handoff-id", "cross-1"],
        cwd=PROJECT_ROOT,
        env=codex_env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert send.returncode == 0, send.stderr

    inbox = subprocess.run(
        [str(COS), "team", "--json", "inbox", "--team", "release", "--session-id", "claude-s1"],
        cwd=PROJECT_ROOT,
        env=claude_env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert inbox.returncode == 0, inbox.stderr
    payload = json.loads(inbox.stdout)
    handoff = json.loads(payload["messages"][0]["text"])
    assert handoff["handoff"]["handoff_id"] == "cross-1"
    assert handoff["handoff"]["from_agent"] == "codex-s1"
    assert handoff["handoff"]["to_agent"] == "claude-s1"
