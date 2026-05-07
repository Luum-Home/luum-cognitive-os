from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COS = PROJECT_ROOT / "scripts" / "cos"


def run_cos_team(tmp_path: Path, *args: str) -> dict:
    result = subprocess.run(
        [str(COS), "team", "--json", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


@pytest.mark.behavior
def test_cos_team_cli_task_message_and_handoff_flow(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    joined = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "join",
        "--team",
        "release",
        "--session-id",
        "lead",
        "--role",
        "lead",
        "--worktree-path",
        str(project),
    )
    assert joined["status"] == "joined"

    created = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "task",
        "create",
        "--team",
        "release",
        "--task-id",
        "audit",
        "--title",
        "Audit release notes",
    )
    assert created["task"]["task_id"] == "audit"

    claimed = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "task",
        "claim-next",
        "--team",
        "release",
        "--session-id",
        "worker",
    )
    assert claimed["status"] == "task_claimed"
    assert claimed["task"]["claimed_by"] == "worker"

    completed = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "task",
        "complete",
        "--team",
        "release",
        "--task-id",
        "audit",
        "--session-id",
        "worker",
        "--output-summary",
        "clean",
    )
    assert completed["task"]["status"] == "completed"

    sent = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "message",
        "send",
        "--team",
        "release",
        "--sender",
        "lead",
        "--recipient",
        "worker",
        "--text",
        "continue",
    )
    assert sent["status"] == "message_sent"

    handoff = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "handoff",
        "send",
        "--team",
        "release",
        "--from-agent",
        "lead",
        "--to-agent",
        "worker",
        "--text",
        "take over docs",
        "--handoff-id",
        "handoff-1",
    )
    assert handoff["status"] == "handoff_sent"
    assert handoff["handoff"]["handoff_id"] == "handoff-1"

    inbox = run_cos_team(
        project,
        "--project-dir",
        str(project),
        "inbox",
        "--team",
        "release",
        "--session-id",
        "worker",
    )
    texts = [message["text"] for message in inbox["messages"]]
    assert "continue" in texts
    handoff_payloads = [json.loads(text) for text in texts if text.startswith('{"handoff"') or '"type": "handoff"' in text]
    assert handoff_payloads[0]["type"] == "handoff"
    assert handoff_payloads[0]["handoff"]["to_agent"] == "worker"

@pytest.mark.behavior
def test_cos_team_handoff_receive_executes_once(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    output = project / "received.txt"
    run_cos_team(
        project,
        "--project-dir", str(project),
        "handoff", "send",
        "--team", "release",
        "--from-agent", "lead",
        "--to-agent", "worker",
        "--text", "hello receiver",
        "--handoff-id", "receive-1",
    )
    received = run_cos_team(
        project,
        "--project-dir", str(project),
        "handoff", "receive",
        "--team", "release",
        "--session-id", "worker",
        "--exec-command-template", f"printf '{{text}}' > {output}",
        "--once",
    )
    assert received["received"][0]["executed"] is True
    assert output.read_text() == "hello receiver"

    second = run_cos_team(
        project,
        "--project-dir", str(project),
        "handoff", "receive",
        "--team", "release",
        "--session-id", "worker",
        "--once",
    )
    assert second["received"] == []
