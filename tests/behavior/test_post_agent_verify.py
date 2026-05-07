"""Behavior tests for hooks/post-agent-verify.sh (ADR-003 Mechanism B).

Validates:
- No action when every changed file is inside TOUCH scope.
- Forbidden writes (files outside TOUCH scope) are auto-restored from the
  snapshot stash and an alert is emitted on stderr.
- Violations are logged to `.cognitive-os/metrics/agent-violations.jsonl`.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRE_HOOK = PROJECT_ROOT / "hooks" / "pre-agent-snapshot.sh"
POST_HOOK = PROJECT_ROOT / "hooks" / "post-agent-verify.sh"
CONFIRM_HOOK = PROJECT_ROOT / "hooks" / "agent-launch-confirmed.sh"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def _init_repo_with_files(repo: Path, files: dict[str, str]) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    for path, content in files.items():
        full = repo / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "seed")


def _common_env(repo: Path, agent_id: str, session_id: str) -> dict:
    env = os.environ.copy()
    env.update(
        {
            "CLAUDE_PROJECT_DIR": str(repo),
            "COGNITIVE_OS_PROJECT_DIR": str(repo),
            "COGNITIVE_OS_SESSION_ID": session_id,
            "CLAUDE_AGENT_ID": agent_id,
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    return env


def _run_pre(repo: Path, agent_id: str, session_id: str, prompt: str = "work") -> subprocess.CompletedProcess:
    payload = {"tool_name": "Agent", "tool_input": {"prompt": prompt, "description": prompt}}
    return subprocess.run(
        ["bash", str(PRE_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=_common_env(repo, agent_id, session_id),
        cwd=str(repo),
        timeout=15,
    )


def _run_confirmed(repo: Path, agent_id: str, session_id: str, prompt: str = "work") -> subprocess.CompletedProcess:
    payload = {"tool_name": "Agent", "tool_input": {"prompt": prompt, "description": prompt}}
    return subprocess.run(
        ["bash", str(CONFIRM_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=_common_env(repo, agent_id, session_id),
        cwd=str(repo),
        timeout=15,
    )


def _run_post(repo: Path, agent_id: str, session_id: str) -> subprocess.CompletedProcess:
    payload = {"tool_name": "Agent", "tool_input": {"prompt": "work"}, "tool_response": {"result": "done"}}
    return subprocess.run(
        ["bash", str(POST_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=_common_env(repo, agent_id, session_id),
        cwd=str(repo),
        timeout=15,
    )


def _write_touch_scope(repo: Path, session_id: str, agent_id: str, allowed: list[str]) -> None:
    session_dir = repo / ".cognitive-os" / "sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = session_dir / f"agent-{agent_id}-prompt.txt"
    body = "TOUCH only:\n"
    for p in allowed:
        body += f"  - {p}\n"
    body += "\nDO NOT TOUCH:\n  - everything else\n"
    prompt_file.write_text(body)


class TestHookExists:

    def test_hook_is_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(POST_HOOK)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr


class TestPostVerifyBehavior:

    def test_verify_no_action_when_in_scope(self, tmp_path: Path):
        repo = tmp_path / "repo"
        _init_repo_with_files(
            repo,
            {"src/allowed.txt": "v1\n", "src/forbidden.txt": "v1\n"},
        )
        agent_id = "agent-inscope"
        session_id = "sess-inscope"

        # Start with dirty tree (pre-existing modification) so snapshot is real
        (repo / "src" / "allowed.txt").write_text("v1\nstarting\n")

        pre = _run_pre(repo, agent_id, session_id)
        assert pre.returncode == 0, pre.stderr
        confirmed = _run_confirmed(repo, agent_id, session_id)
        assert confirmed.returncode == 0, confirmed.stderr

        # Declare scope BEFORE the agent writes
        _write_touch_scope(repo, session_id, agent_id, ["src/allowed.txt"])

        # Agent edits only in-scope file
        (repo / "src" / "allowed.txt").write_text("v1\nstarting\nagent wrote\n")

        post = _run_post(repo, agent_id, session_id)
        assert post.returncode == 0, post.stderr

        # File should NOT have been restored — agent's write stays
        final = (repo / "src" / "allowed.txt").read_text()
        assert "agent wrote" in final

        # No violation should be logged
        vlog = repo / ".cognitive-os" / "metrics" / "agent-violations.jsonl"
        if vlog.exists():
            lines = [l for l in vlog.read_text().splitlines() if l.strip()]
            for l in lines:
                entry = json.loads(l)
                assert entry["event"] != "out_of_scope_write", (
                    f"unexpected violation logged: {entry}"
                )

    def test_verify_restores_out_of_scope_writes(self, tmp_path: Path):
        repo = tmp_path / "repo"
        _init_repo_with_files(
            repo,
            {
                "src/allowed.txt": "original-allowed\n",
                "src/forbidden.txt": "original-forbidden\n",
            },
        )
        agent_id = "agent-oos"
        session_id = "sess-oos"

        # Dirty both files with pre-agent baseline values so snapshot captures them
        (repo / "src" / "allowed.txt").write_text("baseline-allowed\n")
        (repo / "src" / "forbidden.txt").write_text("baseline-forbidden\n")

        pre = _run_pre(repo, agent_id, session_id)
        assert pre.returncode == 0, pre.stderr
        confirmed = _run_confirmed(repo, agent_id, session_id)
        assert confirmed.returncode == 0, confirmed.stderr

        _write_touch_scope(repo, session_id, agent_id, ["src/allowed.txt"])

        # Agent writes to BOTH files (the forbidden write is the violation)
        (repo / "src" / "allowed.txt").write_text("baseline-allowed\nagent-edit\n")
        (repo / "src" / "forbidden.txt").write_text("agent-clobbered\n")

        post = _run_post(repo, agent_id, session_id)
        assert post.returncode == 0, post.stderr

        # Allowed file should still have the agent's edit
        allowed_final = (repo / "src" / "allowed.txt").read_text()
        assert "agent-edit" in allowed_final

        # Forbidden file should be restored from snapshot (baseline value)
        forbidden_final = (repo / "src" / "forbidden.txt").read_text()
        assert forbidden_final == "baseline-forbidden\n", (
            f"forbidden file not restored, got: {forbidden_final!r}"
        )

        # Alert on stderr
        assert "OUT-OF-SCOPE" in post.stderr or "AGENT WROTE OUTSIDE SCOPE" in post.stderr

    def test_verify_logs_violation(self, tmp_path: Path):
        repo = tmp_path / "repo"
        _init_repo_with_files(
            repo,
            {"a.txt": "orig-a\n", "b.txt": "orig-b\n"},
        )
        agent_id = "agent-log"
        session_id = "sess-log"

        # Make tree dirty so pre-hook creates a stash
        (repo / "a.txt").write_text("baseline-a\n")
        (repo / "b.txt").write_text("baseline-b\n")

        pre = _run_pre(repo, agent_id, session_id)
        assert pre.returncode == 0
        confirmed = _run_confirmed(repo, agent_id, session_id)
        assert confirmed.returncode == 0, confirmed.stderr

        _write_touch_scope(repo, session_id, agent_id, ["a.txt"])

        # Agent writes to forbidden file only
        (repo / "b.txt").write_text("agent-clobbered-b\n")

        post = _run_post(repo, agent_id, session_id)
        assert post.returncode == 0

        vlog = repo / ".cognitive-os" / "metrics" / "agent-violations.jsonl"
        assert vlog.exists(), f"violations log missing: {vlog}"
        lines = [l for l in vlog.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1

        matched = False
        for l in lines:
            entry = json.loads(l)
            if entry.get("event") == "out_of_scope_write" and entry.get("file") == "b.txt":
                matched = True
                assert entry["agent_id"] == agent_id
                assert entry["restored"] is True
        assert matched, f"no out_of_scope_write violation for b.txt, log:\n{lines}"

    def test_verify_skips_with_warning_when_no_scope(self, tmp_path: Path):
        """When no prompt/scope file exists, the hook must NOT auto-restore."""
        repo = tmp_path / "repo"
        _init_repo_with_files(repo, {"a.txt": "orig\n"})
        agent_id = "agent-noscope"
        session_id = "sess-noscope"

        (repo / "a.txt").write_text("baseline\n")
        pre = _run_pre(repo, agent_id, session_id)
        assert pre.returncode == 0
        confirmed = _run_confirmed(repo, agent_id, session_id)
        assert confirmed.returncode == 0, confirmed.stderr

        # No prompt file written → no TOUCH scope available

        (repo / "a.txt").write_text("agent-wrote\n")

        post = _run_post(repo, agent_id, session_id)
        assert post.returncode == 0
        # File not restored
        assert (repo / "a.txt").read_text() == "agent-wrote\n"
        # Warning emitted
        assert "No TOUCH scope" in post.stderr or "Skipping auto-restore" in post.stderr
