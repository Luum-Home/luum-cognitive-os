# SCOPE: both
"""Portability probes for hooks/post-agent-verify.sh."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "post-agent-verify.sh"
PRE_HOOK = REPO_ROOT / "hooks" / "pre-agent-snapshot.sh"


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, timeout=10)


def init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    (repo / "allowed.txt").write_text("base allowed\n")
    (repo / "blocked.txt").write_text("base blocked\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "seed")


def env(repo: Path, session: str = "s1", agent: str = "a1") -> dict[str, str]:
    data = os.environ.copy()
    data.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(repo),
            "CLAUDE_PROJECT_DIR": str(repo),
            "COGNITIVE_OS_SESSION_ID": session,
            "CLAUDE_AGENT_ID": agent,
        }
    )
    return data


def run_hook(repo: Path, payload: dict, *, session: str = "s1", agent: str = "a1") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(repo),
        env=env(repo, session, agent),
        timeout=15,
    )


def test_non_agent_payload_skips(tmp_path: Path) -> None:
    init_repo(tmp_path)
    result = run_hook(tmp_path, {"tool_name": "Bash", "tool_input": {"command": "echo ok"}})
    assert result.returncode == 0
    assert result.stderr == ""


def test_no_scope_warns_without_restoring(tmp_path: Path) -> None:
    init_repo(tmp_path)
    (tmp_path / "allowed.txt").write_text("agent wrote\n")
    result = run_hook(tmp_path, {"tool_name": "Agent", "tool_input": {"prompt": "work"}})
    assert result.returncode == 0
    assert "No TOUCH scope" in result.stderr
    assert (tmp_path / "allowed.txt").read_text() == "agent wrote\n"


def test_in_scope_write_is_preserved(tmp_path: Path) -> None:
    init_repo(tmp_path)
    session = "scope"
    agent = "agent"
    session_dir = tmp_path / ".cognitive-os" / "sessions" / session
    session_dir.mkdir(parents=True)
    (session_dir / f"agent-{agent}-prompt.txt").write_text("TOUCH only:\n  - allowed.txt\n")
    (tmp_path / "allowed.txt").write_text("agent allowed\n")
    result = run_hook(tmp_path, {"tool_name": "Agent"}, session=session, agent=agent)
    assert result.returncode == 0
    assert (tmp_path / "allowed.txt").read_text() == "agent allowed\n"


def test_falsification_out_of_scope_write_restores_from_snapshot(tmp_path: Path) -> None:
    init_repo(tmp_path)
    session = "restore"
    agent = "agent"
    (tmp_path / "blocked.txt").write_text("baseline blocked\n")
    pre = subprocess.run(
        ["bash", str(PRE_HOOK)],
        input=json.dumps({"tool_name": "Agent", "tool_input": {"prompt": "work"}}),
        text=True,
        capture_output=True,
        cwd=str(tmp_path),
        env=env(tmp_path, session, agent),
        timeout=15,
    )
    assert pre.returncode == 0, pre.stderr
    prompt = tmp_path / ".cognitive-os" / "sessions" / session / f"agent-{agent}-prompt.txt"
    prompt.write_text("TOUCH only:\n  - allowed.txt\n")
    (tmp_path / "blocked.txt").write_text("agent clobbered\n")
    result = run_hook(tmp_path, {"tool_name": "Agent"}, session=session, agent=agent)
    assert result.returncode == 0
    assert (tmp_path / "blocked.txt").read_text() == "baseline blocked\n"
