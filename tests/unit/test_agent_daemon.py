from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.agent_daemon import AgentDaemon, AgentDaemonError


@pytest.mark.unit
def test_enqueue_writes_queue_and_state(tmp_path: Path) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    task = daemon.enqueue(command="echo hello", task_id="docs", session_id="s1")

    assert task.status == "queued"
    assert task.tmux_session == "cos-agent-docs"
    assert daemon.queue_path.is_file()
    assert json.loads(daemon.queue_path.read_text().splitlines()[0])["task_id"] == "docs"
    assert json.loads(daemon.state_path("docs").read_text())["status"] == "queued"


@pytest.mark.unit
def test_launch_dry_run_generates_run_script_and_running_state(tmp_path: Path) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    daemon.enqueue(command="printf ok", task_id="docs")

    running = daemon.launch("docs", dry_run=True)

    assert running.status == "running"
    script = daemon.task_dir("docs") / "run.sh"
    content = script.read_text()
    assert "printf ok" in content
    assert "heartbeat.json" in content
    assert "done.json" in content
    assert json.loads(daemon.state_path("docs").read_text())["status"] == "running"


@pytest.mark.unit
def test_launch_requires_tmux_when_not_dry_run(tmp_path: Path) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    daemon.enqueue(command="echo hi", task_id="docs")

    with pytest.raises(AgentDaemonError):
        daemon.launch("docs", tmux_bin="/definitely/missing/tmux", dry_run=False)


@pytest.mark.unit
def test_reap_completed_moves_running_task_to_completed(tmp_path: Path) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    daemon.enqueue(command="echo hi", task_id="docs")
    daemon.launch("docs", dry_run=True)
    daemon.done_path("docs").write_text('{"exit_code":0,"task_id":"docs"}\n')

    completed = daemon.reap_completed()

    assert [task.task_id for task in completed] == ["docs"]
    assert json.loads(daemon.state_path("docs").read_text())["status"] == "completed"
    assert daemon.results_path.is_file()
