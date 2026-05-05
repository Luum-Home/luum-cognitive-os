from __future__ import annotations

import json
import os
import subprocess
import sys
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.chaos

ROOT = Path(__file__).resolve().parents[2]
CLAIM_TASK = ROOT / "scripts" / "claim_task.py"
RESOURCE_LEASE = ROOT / "scripts" / "resource_lease.py"
DESTRUCTIVE_GIT_BLOCKER = ROOT / "hooks" / "destructive-git-blocker.sh"
EDIT_COOP = ROOT / "scripts" / "edit-coop.sh"
REAPER = ROOT / "scripts" / "so-reaper.sh"
GOVERNED_AGENT = ROOT / "scripts" / "cos-governed-agent.sh"
GOVERNED_EDIT = ROOT / "scripts" / "cos-governed-edit.sh"


def run_python(script: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--project-dir", str(cwd), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
    )


def payload(proc: subprocess.CompletedProcess[str]) -> dict:
    assert proc.stdout, proc.stderr
    return json.loads(proc.stdout)


def load_derived_gate():
    spec = importlib.util.spec_from_file_location("derived_artifact_gate", ROOT / "scripts" / "derived_artifact_gate.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        check=False,
    )


@pytest.fixture
def scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".cognitive-os" / "tasks").mkdir(parents=True)
    (project / ".cognitive-os" / "metrics").mkdir(parents=True)
    (project / ".claude").mkdir()
    (project / ".codex").mkdir()
    git(project, "init")
    git(project, "config", "user.email", "swarm@example.invalid")
    git(project, "config", "user.name", "Swarm Test")
    (project / "target.txt").write_text("initial\n", encoding="utf-8")
    git(project, "add", "target.txt")
    baseline = git(project, "commit", "-m", "baseline")
    assert baseline.returncode == 0, baseline.stderr
    return project


def test_same_task_race_blocks_second_live_claim(scratch_project: Path) -> None:
    first = run_python(
        CLAIM_TASK,
        "acquire",
        "TASK-123",
        "--session-id",
        "claude-session-a",
        "--agent-id",
        "agent-a",
        "--expected-file",
        "target.txt",
        "--scope",
        "swarm-test",
        "--ttl-seconds",
        "60",
        cwd=scratch_project,
    )
    assert first.returncode == 0, first.stderr
    assert payload(first)["status"] == "acquired"

    second = run_python(
        CLAIM_TASK,
        "acquire",
        "TASK-123",
        "--session-id",
        "codex-session-b",
        "--agent-id",
        "agent-b",
        "--expected-file",
        "target.txt",
        "--scope",
        "swarm-test",
        "--ttl-seconds",
        "60",
        cwd=scratch_project,
    )
    second_payload = payload(second)
    assert second.returncode == 2
    assert second_payload["status"] == "blocked"
    assert second_payload["held_by"]["session_id"] == "claude-session-a"
    assert second_payload["held_by"]["task_id"] == "TASK-123"


def test_codex_governed_agent_blocks_duplicate_task_claim(scratch_project: Path) -> None:
    held = run_python(
        CLAIM_TASK,
        "acquire",
        "TASK-CODEX",
        "--session-id",
        "claude-session",
        "--agent-id",
        "claude-agent",
        "--scope",
        "shared task",
        "--ttl-seconds",
        "60",
        cwd=scratch_project,
    )
    assert held.returncode == 0, held.stderr

    env = os.environ.copy()
    env.update({"CODEX_PROJECT_DIR": str(scratch_project), "CODEX_SESSION_ID": "codex-session"})
    blocked = subprocess.run(
        [
            "bash",
            str(GOVERNED_AGENT),
            "--task-id",
            "TASK-CODEX",
            "--agent-id",
            "codex-agent",
            "--scope",
            "shared task",
            "--",
            "true",
        ],
        cwd=scratch_project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=10,
        check=False,
    )
    assert blocked.returncode == 2
    assert "TASK CLAIM BLOCK" in blocked.stderr
    assert "claude-session" in blocked.stderr


def test_same_file_race_blocks_second_writer(scratch_project: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(scratch_project),
            "COS_EDIT_LOCK_NO_PID_CHECK": "1",
        }
    )
    first_env = {**env, "COGNITIVE_OS_SESSION_ID": "session-a"}
    first = subprocess.run(
        ["bash", str(EDIT_COOP), "acquire", "target.txt", "swarm", "exclusive-edit"],
        cwd=scratch_project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=first_env,
        timeout=10,
    )
    assert first.returncode == 0, first.stderr
    (scratch_project / "target.txt").write_text("session-a fix\n", encoding="utf-8")

    second_env = {**env, "COGNITIVE_OS_SESSION_ID": "session-b"}
    second = subprocess.run(
        ["bash", str(EDIT_COOP), "acquire", "target.txt", "swarm", "exclusive-edit"],
        cwd=scratch_project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=second_env,
        timeout=10,
    )
    assert second.returncode == 2
    assert "BLOCKED" in second.stderr
    assert "session=session-a" in second.stderr
    assert (scratch_project / "target.txt").read_text(encoding="utf-8") == "session-a fix\n"


def test_projection_drift_requires_derived_artifact_closure(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = load_derived_gate()
    monkeypatch.setattr(gate, "changed_staged", lambda: {"cognitive-os.yaml"})
    failures: list[str] = []

    gate.check_staged_closure(failures)

    assert failures
    assert "Stage regenerated artifacts too" in failures[0]
    assert "manifests/hook-quality.yaml" in failures[0]
    assert ".claude/settings.json" in failures[0]
    assert ".codex/hooks.json" in failures[0]


def test_codex_governed_edit_blocks_when_file_is_locked(scratch_project: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(scratch_project),
            "COGNITIVE_OS_SESSION_ID": "session-a",
            "COS_EDIT_LOCK_NO_PID_CHECK": "1",
        }
    )
    first = subprocess.run(
        ["bash", str(EDIT_COOP), "acquire", "target.txt", "swarm", "exclusive-edit"],
        cwd=scratch_project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=10,
    )
    assert first.returncode == 0, first.stderr

    codex_env = os.environ.copy()
    codex_env.update(
        {
            "CODEX_PROJECT_DIR": str(scratch_project),
            "CODEX_SESSION_ID": "codex-session",
            "COS_EDIT_LOCK_NO_PID_CHECK": "1",
        }
    )
    blocked = subprocess.run(
        [
            "bash",
            str(GOVERNED_EDIT),
            "--task-id",
            "codex-lock-test",
            "--file",
            "target.txt",
            "--reason",
            "codex edit",
            "--",
            "bash",
            "-c",
            "printf codex > target.txt",
        ],
        cwd=scratch_project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=codex_env,
        timeout=10,
        check=False,
    )
    assert blocked.returncode == 2
    assert "BLOCKED" in blocked.stderr


def test_same_domain_lease_blocks_competing_agent(scratch_project: Path) -> None:
    first = run_python(
        RESOURCE_LEASE,
        "acquire",
        "hooks",
        "--session-id",
        "session-a",
        "--agent-id",
        "agent-a",
        "--reason",
        "wire hook projection",
        "--ttl-seconds",
        "60",
        cwd=scratch_project,
    )
    assert first.returncode == 0, first.stderr

    second = run_python(
        RESOURCE_LEASE,
        "acquire",
        "hooks",
        "--session-id",
        "session-b",
        "--agent-id",
        "agent-b",
        "--reason",
        "parallel hook edit",
        "--ttl-seconds",
        "60",
        cwd=scratch_project,
    )
    assert second.returncode == 2
    assert payload(second)["held_by"]["session_id"] == "session-a"


def run_git_blocker(project: Path, command: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for key in ("CI", "COS_GIT_BYPASS", "COS_ALLOW_DESTRUCTIVE_GIT"):
        env.pop(key, None)
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "CLAUDE_PROJECT_DIR": str(project),
            "COGNITIVE_OS_SESSION_ID": "agent-session",
            "CLAUDE_AGENT_ID": "agent-b",
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(
        ["bash", str(DESTRUCTIVE_GIT_BLOCKER)],
        cwd=project,
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=10,
        check=False,
    )


def test_dirty_worktree_pull_rebase_is_blocked_before_mutation(scratch_project: Path) -> None:
    (scratch_project / "target.txt").write_text("agent-b uncommitted fix\n", encoding="utf-8")
    result = run_git_blocker(scratch_project, "git pull --rebase origin main")
    assert result.returncode == 1
    assert "BLOCKED" in result.stderr
    assert "git pull --rebase" in result.stderr
    assert (scratch_project / "target.txt").read_text(encoding="utf-8") == "agent-b uncommitted fix\n"


def test_agent_b_fix_overwrite_incident_reset_is_blocked(scratch_project: Path) -> None:
    (scratch_project / "target.txt").write_text("agent-b regex fix\n", encoding="utf-8")
    result = run_git_blocker(scratch_project, "git fetch origin main && git reset --hard origin/main")
    assert result.returncode == 1
    assert "BLOCKED" in result.stderr
    assert "git reset" in result.stderr or "git fetch origin main" in result.stderr
    assert (scratch_project / "target.txt").read_text(encoding="utf-8") == "agent-b regex fix\n"


def test_cross_ide_parity_marks_shared_gates_and_known_matcher_gaps() -> None:
    claude = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    codex = json.loads((ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    claude_text = json.dumps(claude)
    codex_text = json.dumps(codex)

    for shared_hook in ("orchestrator-claim-gate.sh", "destructive-git-blocker.sh"):
        assert shared_hook in claude_text
        assert shared_hook in codex_text

    assert "concurrent-write-guard.sh" in claude_text
    assert "concurrent-write-guard.sh" not in codex_text


@pytest.mark.parametrize("harness", ["claude", "codex"])
def test_memory_sharing_doctor_runs_for_supported_harnesses(harness: str) -> None:
    result = subprocess.run(
        [
            "bash",
            str(ROOT / "scripts" / "cos-doctor-memory-lifecycle.sh"),
            "--harness",
            harness,
            "--skip-engram-start",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert f"memory lifecycle hooks are projected for {harness}" in combined


def test_task_completed_by_other_agent_is_marked_by_watermark(scratch_project: Path) -> None:
    tasks_path = scratch_project / ".cognitive-os" / "tasks" / "active-tasks.json"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tasks_path.write_text(
        json.dumps(
            {
                "version": 1,
                "tasks": [
                    {
                        "id": "TASK-WATERMARK",
                        "description": "generate swarm output artifact",
                        "status": "pending",
                        "requested_at": now,
                        "pid": None,
                        "expectedOutputs": ["outputs/swarm-result.txt"],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = scratch_project / "outputs" / "swarm-result.txt"
    output.parent.mkdir()
    output.write_text("created by another session\n", encoding="utf-8")

    env = os.environ.copy()
    env.update({"COGNITIVE_OS_PROJECT_DIR": str(scratch_project), "COS_GIT_BYPASS": "1"})
    result = subprocess.run(
        ["bash", str(REAPER)],
        cwd=scratch_project,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(tasks_path.read_text(encoding="utf-8"))
    task = data["tasks"][0]
    assert task["status"] == "completed-by-watermark"
    assert task["watermark_evidence"]["mode"] == "A"


def test_completed_by_other_agent_reconciliation_fixture(scratch_project: Path) -> None:
    from lib.task_reconciliation import reconcile_completed_by_other_session

    sessions = scratch_project / ".cognitive-os" / "sessions"
    (sessions / "codex-session").mkdir(parents=True)
    (sessions / "claude-session").mkdir(parents=True)
    (sessions / "codex-session" / "tasks.json").write_text(
        json.dumps({"tasks": [{"task_id": "TASK-DONE-ELSEWHERE", "status": "pending"}]}) + "\n",
        encoding="utf-8",
    )
    watermark = scratch_project / ".cognitive-os" / "tasks" / "completion-watermark.jsonl"
    watermark.parent.mkdir(parents=True, exist_ok=True)
    watermark.write_text(
        json.dumps({"task_id": "TASK-DONE-ELSEWHERE", "status": "done-by-other-session", "session_id": "claude-session"}) + "\n",
        encoding="utf-8",
    )

    report = [item.to_dict() for item in reconcile_completed_by_other_session(scratch_project)]

    assert report[0]["status"] == "done-by-other-session"
    assert report[0]["completing_session"] == "claude-session"
    assert report[0]["pending_session"] == "codex-session"
