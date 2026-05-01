"""Integration tests for SessionStart subagent fan-out hardening.

Incident 2026-05-01-session-multi-spawn-hang: Claude Code can create
subagent-shaped sessions that fire the full SessionStart hook surface. COS
SessionStart hooks are orchestrator-scope (self-install, daemon launch,
settings projection, recovery), while SubagentStart is the correct place for
subagent context injection. The timing wrapper therefore detects subagent
SessionStart input and skips the heavy hook body centrally.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WRAPPER = REPO_ROOT / "scripts" / "hook-timing-wrapper.sh"


def _write_hook(path: Path, marker: Path) -> None:
    path.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"cat > {marker}\n"
        "printf 'hook-ran'\n"
    )
    path.chmod(0o755)


def _run_wrapper(project: Path, hook: Path, payload: dict[str, object]) -> subprocess.CompletedProcess:
    env = {**os.environ, "COGNITIVE_OS_PROJECT_DIR": str(project)}
    return subprocess.run(
        ["bash", str(WRAPPER), "SessionStart", str(hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        timeout=10,
    )


def _last_timing(project: Path) -> dict[str, object]:
    timing = project / ".cognitive-os" / "metrics" / "hook-timing.jsonl"
    lines = timing.read_text().strip().splitlines()
    assert lines, "wrapper did not write hook timing"
    return json.loads(lines[-1])


def test_subagent_sessionstart_is_skipped_centrally(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    hook = tmp_path / "fake-hook.sh"
    marker = tmp_path / "hook-input.json"
    _write_hook(hook, marker)

    result = _run_wrapper(
        project,
        hook,
        {
            "hook_event_name": "SessionStart",
            "session_id": "s1",
            "transcript_path": str(project / ".claude" / "projects" / "subagents" / "a.jsonl"),
            "source": "startup",
            "agent_type": "Explore",
        },
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert not marker.exists(), "subagent SessionStart must not run the heavy hook body"
    timing = _last_timing(project)
    assert timing["event"] == "SessionStart"
    assert timing["session_kind"] == "subagent"
    assert timing["skipped"] == 1


def test_orchestrator_sessionstart_still_runs_and_receives_stdin(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    hook = tmp_path / "fake-hook.sh"
    marker = tmp_path / "hook-input.json"
    _write_hook(hook, marker)

    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "s1",
        "transcript_path": str(project / ".claude" / "projects" / "main.jsonl"),
        "source": "startup",
        "model": "claude-sonnet-4-6",
    }
    result = _run_wrapper(project, hook, payload)

    assert result.returncode == 0
    assert result.stdout == ""
    assert "hook-ran" in result.stderr
    assert json.loads(marker.read_text()) == payload
    timing = _last_timing(project)
    assert timing["session_kind"] == "orchestrator"
    assert timing["skipped"] == 0



def test_all_registered_sessionstart_hooks_skip_for_subagent_payload(tmp_path: Path) -> None:
    """Every registered SessionStart hook must be covered by the central gate.

    This is the automated version of the manual startup regression: parse the
    committed Claude settings, extract the real 17 SessionStart hook targets,
    invoke each through hook-timing-wrapper with a subagent-shaped payload, and
    assert every invocation is skipped before the hook body can mutate state.
    """
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    groups = settings["hooks"]["SessionStart"]
    commands: list[str] = []
    for group in groups:
        for hook in group.get("hooks", []):
            commands.append(hook["command"])

    assert len(commands) >= 10, "expected the full SessionStart hook chain"
    assert all("hook-timing-wrapper.sh" in c for c in commands)

    project = tmp_path / "project"
    project.mkdir()
    payload = {
        "hook_event_name": "SessionStart",
        "session_id": "subagent-session",
        "transcript_path": str(project / ".claude" / "projects" / "subagents" / "agent.jsonl"),
        "source": "startup",
        "agent_type": "Explore",
    }
    env = {**os.environ, "COGNITIVE_OS_PROJECT_DIR": str(project)}

    for command in commands:
        match = re.search(r'"\$CLAUDE_PROJECT_DIR/([^"]+\.sh)"', command)
        assert match, f"could not resolve hook path from command: {command}"
        hook_path = REPO_ROOT / match.group(1)
        result = subprocess.run(
            ["bash", str(WRAPPER), "SessionStart", str(hook_path)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=env,
            timeout=10,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == "", f"skipped subagent hook leaked stdout: {hook_path.name}"

    timing = project / ".cognitive-os" / "metrics" / "hook-timing.jsonl"
    records = [json.loads(line) for line in timing.read_text().splitlines()]
    assert len(records) == len(commands)
    assert {r["session_kind"] for r in records} == {"subagent"}
    assert {r["skipped"] for r in records} == {1}
