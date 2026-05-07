from __future__ import annotations

import pytest

from lib.agent_team import AgentTeam


@pytest.mark.behavior
def test_two_session_file_ipc_flow(tmp_path) -> None:
    lead = AgentTeam("release", project_dir=tmp_path)
    worker = AgentTeam("release", project_dir=tmp_path)

    lead.join(session_id="lead", role="lead", worktree_path="/wt/lead")
    worker.join(session_id="worker", role="worker", worktree_path="/wt/worker")
    lead.create_task("Audit", task_id="audit")
    lead.create_task("Fix", task_id="fix", depends_on=["audit"])

    audit = worker.claim_next(session_id="worker")
    assert audit is not None and audit.task_id == "audit"
    assert lead.claim_next(session_id="lead") is None

    worker.complete_task("audit", session_id="worker", output_summary="clean")
    fix = lead.claim_next(session_id="lead")
    assert fix is not None and fix.task_id == "fix"

    lead.send_message(sender="lead", recipient="worker", text="continue")
    assert worker.inbox("worker")[0].text == "continue"

    events = [event["event"] for event in lead.events()]
    assert "member_joined" in events
    assert "task_created" in events
    assert "task_claimed" in events
    assert "task_completed" in events
    assert "message_sent" in events
