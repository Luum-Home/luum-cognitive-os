from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COS = PROJECT_ROOT / "scripts" / "cos"


def run_agent_daemon(project: Path, *args: str) -> dict:
    result = subprocess.run(
        [str(COS), "agent", "daemon", "--json", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


@pytest.mark.behavior
def test_cos_agent_daemon_enqueue_list_and_dry_run(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    queued = run_agent_daemon(project, "--project-dir", str(project), "enqueue", "--task-id", "docs", "--command", "echo hi")
    assert queued["status"] == "queued"

    listed = run_agent_daemon(project, "--project-dir", str(project), "list")
    assert [task["task_id"] for task in listed["tasks"]] == ["docs"]

    launched = run_agent_daemon(project, "--project-dir", str(project), "run-once", "--dry-run")
    assert launched["status"] == "launched"
    assert launched["task"]["status"] == "running"


@pytest.mark.behavior
def test_cos_agent_daemon_uses_fake_tmux_runtime(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    fake_tmux = tmp_path / "tmux"
    fake_log = tmp_path / "tmux.log"
    fake_tmux.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> {fake_log}\n"
        "exit 0\n"
    )
    fake_tmux.chmod(0o755)

    run_agent_daemon(project, "--project-dir", str(project), "enqueue", "--task-id", "docs", "--command", "echo hi")
    launched = run_agent_daemon(
        project,
        "--project-dir",
        str(project),
        "run-once",
        "--tmux-bin",
        str(fake_tmux),
    )

    assert launched["status"] == "launched"
    assert "new-session -d -s cos-agent-docs" in fake_log.read_text()

@pytest.mark.behavior
def test_cos_agent_daemon_reap_stale_and_service_plan(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    run_agent_daemon(project, "--project-dir", str(project), "enqueue", "--task-id", "stale", "--command", "sleep 99", "--max-runtime-seconds", "1")
    run_agent_daemon(project, "--project-dir", str(project), "run-once", "--dry-run")
    reaped = run_agent_daemon(project, "--project-dir", str(project), "reap", "--stale-heartbeat-seconds", "0")
    assert reaped["stale_failed"][0]["task_id"] == "stale"

    plan = run_agent_daemon(project, "--project-dir", str(project), "service-plan", "--kind", "systemd")
    assert "ExecStart" in plan["content"]


@pytest.mark.behavior
def test_cos_agent_daemon_enqueue_team_next(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(
        [str(COS), "team", "--json", "--project-dir", str(project), "task", "create", "--team", "release", "--task-id", "docs", "--title", "Write docs"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    queued = run_agent_daemon(
        project,
        "--project-dir", str(project),
        "enqueue-team-next",
        "--team", "release",
        "--session-id", "worker",
        "--command-template", "echo {task_id}:{title}",
    )
    assert queued["status"] == "queued_team_task"
    assert queued["task"]["command"] == "echo docs:Write docs"

@pytest.mark.behavior
def test_cos_agent_daemon_install_service_and_kill_cli(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    target = tmp_path / "systemd"
    installed = run_agent_daemon(
        project,
        "--project-dir", str(project),
        "install-service",
        "--kind", "systemd",
        "--target-dir", str(target),
    )
    assert installed["status"] == "installed"
    assert Path(installed["path"]).is_file()

    queued = run_agent_daemon(
        project,
        "--project-dir", str(project),
        "enqueue",
        "--task-id", "kill-cli",
        "--session-id", "s1",
        "--command", "sleep 999",
    )
    assert queued["task"]["task_id"] == "kill-cli"
    run_agent_daemon(project, "--project-dir", str(project), "run-once", "--dry-run")
    killed = run_agent_daemon(
        project,
        "--project-dir", str(project),
        "kill",
        "--task-id", "kill-cli",
        "--tmux-bin", "/missing/tmux",
        "--reason", "test_cli_kill",
    )
    assert killed["status"] == "killed"
    assert killed["task"]["status"] == "failed"

@pytest.mark.behavior
def test_cos_agent_daemon_prepare_worktree_uses_branch_per_task_prefix(tmp_path: Path) -> None:
    project = tmp_path / "project-git"
    project.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project, check=True)
    (project / "README.md").write_text("hello\n")
    subprocess.run(["git", "add", "README.md"], cwd=project, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=project, check=True)
    queued = run_agent_daemon(
        project,
        "--project-dir", str(project),
        "enqueue",
        "--task-id", "branch-task",
        "--session-id", "s1",
        "--command", "true",
        "--prepare-worktree",
        "--worktree-root", str(tmp_path / "worktrees"),
    )
    assert queued["task"]["worktree_path"].endswith("branch-task")
    branch = subprocess.run(["git", "-C", queued["task"]["worktree_path"], "branch", "--show-current"], capture_output=True, text=True, check=True).stdout.strip()
    assert branch == "codex/task/branch-task"
