from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

ROOT = Path(__file__).resolve().parents[2]


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "scripts").symlink_to(ROOT / "scripts", target_is_directory=True)
    (project / "lib").symlink_to(ROOT / "lib", target_is_directory=True)
    (project / "cognitive-os.yaml").write_text(
        "project:\n  phase: reconstruction\n"
        "concurrency_safety:\n  resource_leases:\n"
        "    default_ttl_seconds: 60\n"
        "    critical_domains:\n      - auth\n      - billing\n      - migrations\n      - infrastructure\n",
        encoding="utf-8",
    )
    return project


def _run_hook(
    hook: str,
    payload: dict,
    project: Path,
    *,
    session_id: str = "session-test",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "CLAUDE_PROJECT_DIR": str(project),
            "COGNITIVE_OS_SESSION_ID": session_id,
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    return subprocess.run(
        ["bash", str(ROOT / "hooks" / hook)],
        input=json.dumps(payload),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=20,
    )


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_agent_hooks_write_work_ledger_and_resource_lease(tmp_path: Path) -> None:
    project = _project(tmp_path)
    payload = {
        "tool_name": "Agent",
        "tool_use_id": "agent-tool-1",
        "tool_input": {"description": "modify auth policy safely"},
    }

    pre = _run_hook("agent-prelaunch.sh", payload, project)
    assert pre.returncode == 0, pre.stderr

    events = _jsonl(project / ".cognitive-os/runtime/agent-work-ledger.jsonl")
    assert events[-1]["status"] == "started"
    assert events[-1]["agent_id"] == "agent-tool-1"
    assert (project / ".cognitive-os/runtime/resource-leases/auth.json").exists()
    claims = json.loads((project / ".cognitive-os/runtime/task-claims.json").read_text(encoding="utf-8"))
    assert len(claims["claims"]) == 1

    post_payload = {
        **payload,
        "tool_response": {"result": "Done. Acceptance Criteria: 1. `true` exits 0"},
    }
    post = _run_hook("completion-gate.sh", post_payload, project)
    assert post.returncode == 0, post.stderr

    events = _jsonl(project / ".cognitive-os/runtime/agent-work-ledger.jsonl")
    assert events[-1]["status"] == "completed"
    assert not (project / ".cognitive-os/runtime/resource-leases/auth.json").exists()
    claims = json.loads((project / ".cognitive-os/runtime/task-claims.json").read_text(encoding="utf-8"))
    assert claims["claims"] == {}


def test_agent_prelaunch_blocks_duplicate_canonical_task_claim(tmp_path: Path) -> None:
    project = _project(tmp_path)
    payload_a = {
        "tool_name": "Agent",
        "tool_use_id": "agent-tool-a",
        "tool_input": {"description": "implement TASK-123 cross IDE safety"},
    }
    payload_b = {
        "tool_name": "Agent",
        "tool_use_id": "agent-tool-b",
        "tool_input": {"description": "implement TASK-123 cross IDE safety"},
    }

    first = _run_hook("agent-prelaunch.sh", payload_a, project, session_id="session-a")
    assert first.returncode == 0, first.stderr

    blocked = _run_hook("agent-prelaunch.sh", payload_b, project, session_id="session-b")
    assert blocked.returncode == 2
    assert "ADR-116 TASK CLAIM BLOCK" in blocked.stderr
    assert "session-a" in blocked.stderr


def test_agent_prelaunch_blocks_when_resource_lease_is_held(tmp_path: Path) -> None:
    project = _project(tmp_path)
    held = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "resource_lease.py"),
            "--project-dir",
            str(project),
            "acquire",
            "auth",
            "--agent-id",
            "other-agent",
            "--session-id",
            "other-session",
            "--reason",
            "parallel auth work",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    assert held.returncode == 0, held.stderr

    blocked = _run_hook(
        "agent-prelaunch.sh",
        {"tool_name": "Agent", "tool_use_id": "agent-tool-2", "tool_input": {"description": "modify auth policy"}},
        project,
    )

    assert blocked.returncode == 2
    assert "ADR-108 RESOURCE LEASE BLOCK" in blocked.stderr


def test_claim_validator_consults_approval_ledger(tmp_path: Path) -> None:
    project = _project(tmp_path)
    missing = _run_hook(
        "claim-validator.sh",
        {
            "tool_name": "Agent",
            "tool_input": {"description": "migration work"},
            "tool_response": "migrated db/users.sql",
        },
        project,
    )
    assert missing.returncode == 0, missing.stderr
    assert "ADR-108 APPROVAL LEDGER" in missing.stderr

    record = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "approval_ledger.py"),
            "--project-dir",
            str(project),
            "record",
            "--category",
            "migrated",
            "--scope",
            "db/users.sql",
            "--reason",
            "approved migration",
            "--approved-by",
            "operator",
            "--verification-command",
            "python3 -m pytest tests/migrations -q",
            "--rollback-plan",
            "revert migration",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    assert record.returncode == 0, record.stderr

    approved = _run_hook(
        "claim-validator.sh",
        {
            "tool_name": "Agent",
            "tool_input": {"description": "migration work"},
            "tool_response": "migrated db/users.sql",
        },
        project,
    )
    assert approved.returncode == 0, approved.stderr
    assert "ADR-108 APPROVAL LEDGER" not in approved.stderr
