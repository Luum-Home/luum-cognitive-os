from __future__ import annotations

import pytest

from lib.agent_team import AgentTeam


@pytest.mark.behavior
def test_task_created_hook_mirrors_task_into_agent_team(run_hook, mock_project) -> None:
    result = run_hook(
        "task-created.sh",
        stdin_json={
            "hook_event_name": "TaskCreated",
            "team_name": "release",
            "task_id": "docs-audit",
            "description": "Audit release documentation with acceptance criteria",
        },
        env=mock_project["env"],
    )
    assert result.returncode == 0

    team = AgentTeam("release", project_dir=mock_project["project_dir"])
    tasks = team.tasks()
    assert [(task.task_id, task.title) for task in tasks] == [
        ("docs-audit", "Audit release documentation with acceptance criteria")
    ]


@pytest.mark.behavior
def test_teammate_idle_hook_claims_agent_team_task_before_legacy_queue(run_hook, mock_project) -> None:
    project_dir = mock_project["project_dir"]
    team = AgentTeam("release", project_dir=project_dir)
    team.create_task("Fix policy docs", task_id="policy-docs")

    result = run_hook(
        "teammate-idle.sh",
        stdin_json={"hook_event_name": "TeammateIdle", "team_name": "release", "session_id": "worker-1"},
        env=mock_project["env"],
    )

    assert result.returncode == 2
    assert "claimed ADR-233 team task policy-docs" in result.stdout
    claimed = {task.task_id: task for task in team.tasks()}["policy-docs"]
    assert claimed.status == "in_progress"
    assert claimed.claimed_by == "worker-1"
