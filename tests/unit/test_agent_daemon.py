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

@pytest.mark.unit
def test_enqueue_respects_budget_gate(tmp_path: Path) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    with pytest.raises(AgentDaemonError):
        daemon.enqueue(command="echo expensive", task_id="expensive", estimated_cost_usd=2.0, budget_cap_usd=1.0)


@pytest.mark.unit
def test_reap_completed_records_estimated_cost(tmp_path: Path) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    daemon.enqueue(command="echo hi", task_id="docs", session_id="s1", estimated_cost_usd=0.25, budget_cap_usd=1.0)
    daemon.launch("docs", dry_run=True)
    daemon.done_path("docs").write_text('{"exit_code":0,"task_id":"docs"}\n')
    daemon.reap_completed()
    budget = json.loads((tmp_path / ".cognitive-os/metrics/session-budgets/s1.json").read_text())
    assert budget["spent_usd"] == 0.25


@pytest.mark.unit
def test_reap_stale_fails_running_task(tmp_path: Path) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    daemon.enqueue(command="sleep 99", task_id="stale", max_runtime_seconds=1)
    running = daemon.launch("stale", dry_run=True)
    stale = daemon.reap_stale(stale_heartbeat_seconds=1, now=running.updated_at + 10)
    assert [task.task_id for task in stale] == ["stale"]
    assert json.loads(daemon.state_path("stale").read_text())["status"] == "failed"
    assert "max_runtime_exceeded" in json.loads(daemon.done_path("stale").read_text())["reasons"]


@pytest.mark.unit
def test_service_plan_outputs_launchd_and_systemd(tmp_path: Path) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    assert "com.luum.cos-agent-daemon" in daemon.launchd_plist()
    assert "ExecStart=python3" in daemon.systemd_unit()


def test_install_service_writes_launchd_file_to_target_dir(tmp_path: Path) -> None:
    from lib.agent_daemon import AgentDaemon

    project = tmp_path / "project"
    project.mkdir()
    target = tmp_path / "LaunchAgents"
    path = AgentDaemon(project_dir=project).install_service(kind="launchd", target_dir=target, python_bin="python3")
    assert path.parent == target
    assert path.name == "com.luum.cos-agent-daemon.plist"
    assert "cos-agent-daemon" in path.read_text()


def test_kill_task_marks_failed_and_writes_done_without_tmux(tmp_path: Path) -> None:
    from lib.agent_daemon import AgentDaemon

    daemon = AgentDaemon(project_dir=tmp_path)
    task = daemon.enqueue(command="sleep 999", task_id="kill-me", session_id="s1")
    daemon.launch(task.task_id, dry_run=True)
    killed = daemon.kill_task(task.task_id, tmux_bin="/missing/tmux", reason="test_kill")
    assert killed.status == "failed"
    done = json.loads(daemon.done_path(task.task_id).read_text())
    assert done["exit_code"] == 137
    assert done["reasons"] == ["test_kill"]


def test_activation_command_and_plan_are_operator_visible(tmp_path: Path) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    service = tmp_path / "cos-agent-daemon.service"
    assert daemon.activation_command(kind="systemd", service_path=service) == ["systemctl", "--user", "enable", "--now", "cos-agent-daemon.service"]
    plan = daemon.activate_service(kind="launchd", service_path=tmp_path / "com.luum.cos-agent-daemon.plist", execute=False)
    assert plan["executed"] is False
    assert plan["command"][:3] == ["launchctl", "load", "-w"]


def test_kill_task_uses_heartbeat_pid_process_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    daemon = AgentDaemon(project_dir=tmp_path)
    task = daemon.enqueue(command="sleep 999", task_id="kill-tree", session_id="s1")
    daemon.launch(task.task_id, dry_run=True)
    daemon.heartbeat_path(task.task_id).write_text('{"pid":4242,"timestamp":1}\n', encoding="utf-8")
    calls = []
    monkeypatch.setattr(daemon, "_kill_process_tree", lambda pid: calls.append(pid) or ["SIGTERM", "SIGKILL"])

    daemon.kill_task(task.task_id, tmux_bin="/missing/tmux", reason="tree")

    assert calls == [4242]
    done = json.loads(daemon.done_path(task.task_id).read_text())
    assert done["pid"] == 4242
    assert done["kill_signals"][-2:] == ["SIGTERM", "SIGKILL"]
