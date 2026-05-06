"""Smoke tests for ADR-213: blocked Agent preflight must not hide WIP in stash."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str], cwd: Path, *, env: dict[str, str] | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(args, cwd=cwd, env=merged, input=input_text, text=True, capture_output=True, timeout=30)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = _run(["git", *args], repo)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def _active_agent_commands() -> list[str]:
    payload = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    for group in payload["hooks"]["PreToolUse"]:
        if group.get("matcher") == "Agent":
            return [hook["command"] for hook in group["hooks"]]
    raise AssertionError("Agent PreToolUse group not found")


def _window_commands() -> list[str]:
    commands = [cmd for cmd in _active_agent_commands() if "agent-prelaunch.sh" in cmd or "pre-agent-snapshot.sh" in cmd]
    assert len(commands) == 2
    return commands


def _project_with_manual_stash_and_visible_wip(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    # Hook commands execute from ROOT via CLAUDE_PROJECT_DIR, but agent-prelaunch
    # looks for project-local scripts/manifests through COGNITIVE_OS_PROJECT_DIR.
    (project / "hooks").symlink_to(ROOT / "hooks", target_is_directory=True)
    (project / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
    (project / "lib").symlink_to(ROOT / "lib", target_is_directory=True)
    (project / "manifests").symlink_to(ROOT / "manifests", target_is_directory=True)
    (project / ".gitignore").write_text(".cognitive-os/\nhooks\nscripts\nlib\nmanifests\n", encoding="utf-8")

    _git(project, "init")
    _git(project, "config", "user.email", "test@example.com")
    _git(project, "config", "user.name", "Test User")
    (project / "README.md").write_text("base\n", encoding="utf-8")
    (project / "stash.txt").write_text("base stash\n", encoding="utf-8")
    _git(project, "add", "README.md", "stash.txt", ".gitignore")
    _git(project, "commit", "-m", "initial")

    # Existing non-auto stash is what makes agent-prelaunch block. This mirrors
    # the incident class: launch should block before any new auto-pre-agent stash
    # is allowed to hide currently visible WIP.
    (project / "stash.txt").write_text("manual preserved stash\n", encoding="utf-8")
    _git(project, "stash", "push", "-m", "manual-preserve-important", "--", "stash.txt")

    # Operator WIP that must stay visible if launch is blocked.
    (project / "README.md").write_text("base\noperator visible WIP\n", encoding="utf-8")
    assert "operator visible WIP" in _git(project, "diff", "--", "README.md").stdout
    return project


def _hook_env(project: Path) -> dict[str, str]:
    return {
        "CLAUDE_PROJECT_DIR": str(project),
        "COGNITIVE_OS_PROJECT_DIR": str(project),
        "CLAUDE_AGENT_ID": "adr213-smoke-agent",
        "COGNITIVE_OS_SESSION_ID": "adr213-smoke-session",
        "COS_STATE_RETENTION_PREFLIGHT_COOLDOWN_SECONDS": "0",
        "COS_STASH_LEAK_TTL": "0",
        "COS_STASH_LEAK_BLOCK_TTL": "0",
    }


def _run_hook_command(command: str, project: Path, payload: str) -> subprocess.CompletedProcess[str]:
    return _run(["bash", "-lc", command], project, env=_hook_env(project), input_text=payload)


def _agent_payload() -> str:
    return json.dumps(
        {
            "tool_name": "Agent",
            "tool_use_id": "toolu_adr213_smoke",
            "tool_input": {
                "subagent_type": "Explore",
                "description": "READ_ONLY: true smoke should block on manual stash before snapshot",
            },
        }
    )


def test_active_agent_chain_block_does_not_create_auto_stash_or_hide_wip(tmp_path: Path) -> None:
    project = _project_with_manual_stash_and_visible_wip(tmp_path)
    payload = _agent_payload()
    commands = _window_commands()

    seen_block = None
    for command in commands:
        result = _run_hook_command(command, project, payload)
        if result.returncode != 0:
            seen_block = result
            break

    assert seen_block is not None, "agent-prelaunch should block on manual stash"
    assert seen_block.returncode == 2
    assert "ADR-116 GOVERNED PREFLIGHT BLOCK" in seen_block.stderr

    stash_list = _git(project, "stash", "list").stdout
    assert "manual-preserve-important" in stash_list
    assert "auto-pre-agent" not in stash_list
    assert "operator visible WIP" in _git(project, "diff", "--", "README.md").stdout
    assert not list((project / ".cognitive-os" / "runtime").glob("pre-agent-snapshot-*.json"))


def test_old_bad_order_would_have_hidden_wip_in_auto_stash(tmp_path: Path) -> None:
    project = _project_with_manual_stash_and_visible_wip(tmp_path)
    payload = _agent_payload()
    commands = _window_commands()
    snapshot_command = next(cmd for cmd in commands if "pre-agent-snapshot.sh" in cmd)
    prelaunch_command = next(cmd for cmd in commands if "agent-prelaunch.sh" in cmd)

    snapshot = _run_hook_command(snapshot_command, project, payload)
    assert snapshot.returncode == 0, snapshot.stderr

    # This is the old failure mode: visible operator WIP moved out of git diff
    # and into an auto-pre-agent stash before launch admission completed.
    stash_list = _git(project, "stash", "list").stdout
    assert "auto-pre-agent" in stash_list
    assert "operator visible WIP" not in _git(project, "diff", "--", "README.md").stdout

    blocked = _run_hook_command(prelaunch_command, project, payload)
    assert blocked.returncode == 2
    assert "ADR-116 GOVERNED PREFLIGHT BLOCK" in blocked.stderr
