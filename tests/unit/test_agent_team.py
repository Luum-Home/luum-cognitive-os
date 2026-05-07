from __future__ import annotations

import pytest

from lib.agent_team import AgentTeam, AgentTeamError


@pytest.mark.unit
def test_members_join_and_latest_status(tmp_path) -> None:
    team = AgentTeam("alpha", project_dir=tmp_path)

    team.join(session_id="s1", role="lead", worktree_path="/tmp/w1")
    team.join(session_id="s2", role="worker", worktree_path="/tmp/w2")

    members = {member.session_id: member for member in team.members()}
    assert members["s1"].role == "lead"
    assert members["s2"].worktree_path == "/tmp/w2"


@pytest.mark.unit
def test_task_claim_is_locked_and_dependency_aware(tmp_path) -> None:
    team = AgentTeam("alpha", project_dir=tmp_path)
    first = team.create_task("First", task_id="t1")
    second = team.create_task("Second", task_id="t2", depends_on=["t1"])

    claim1 = team.claim_next(session_id="s1")
    claim2 = team.claim_next(session_id="s2")

    assert first.task_id == "t1"
    assert second.depends_on == ("t1",)
    assert claim1 is not None and claim1.task_id == "t1"
    assert claim2 is None

    team.complete_task("t1", session_id="s1", output_summary="done")
    claim3 = team.claim_next(session_id="s2")
    assert claim3 is not None and claim3.task_id == "t2"


@pytest.mark.unit
def test_complete_unknown_task_raises(tmp_path) -> None:
    team = AgentTeam("alpha", project_dir=tmp_path)
    with pytest.raises(AgentTeamError):
        team.complete_task("missing", session_id="s1")


@pytest.mark.unit
def test_inbox_delivery_is_per_recipient(tmp_path) -> None:
    team = AgentTeam("alpha", project_dir=tmp_path)

    team.send_message(sender="s1", recipient="s2", text="hello")
    team.send_message(sender="s1", recipient="s3", text="other")

    assert [message.text for message in team.inbox("s2")] == ["hello"]
    assert [message.text for message in team.inbox("s3")] == ["other"]
