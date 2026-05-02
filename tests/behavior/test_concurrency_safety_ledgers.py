from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_LEASE = ROOT / "scripts" / "resource_lease.py"
WORK_LEDGER = ROOT / "scripts" / "agent_work_ledger.py"
APPROVAL_LEDGER = ROOT / "scripts" / "approval_ledger.py"


def run_script(script: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--project-dir", str(cwd), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def payload(proc: subprocess.CompletedProcess[str]) -> dict:
    assert proc.stdout, proc.stderr
    return json.loads(proc.stdout)


def test_resource_lease_blocks_second_agent_until_release(tmp_path: Path) -> None:
    first = run_script(
        RESOURCE_LEASE,
        "acquire",
        "auth",
        "--agent-id",
        "agent-a",
        "--session-id",
        "s1",
        "--reason",
        "modify auth policy",
        "--ttl-seconds",
        "60",
        cwd=tmp_path,
    )
    assert first.returncode == 0
    assert payload(first)["status"] == "acquired"

    second = run_script(
        RESOURCE_LEASE,
        "acquire",
        "auth",
        "--agent-id",
        "agent-b",
        "--session-id",
        "s2",
        "--reason",
        "parallel auth edit",
        "--ttl-seconds",
        "60",
        cwd=tmp_path,
    )
    assert second.returncode == 2
    assert payload(second)["status"] == "blocked"

    released = run_script(
        RESOURCE_LEASE,
        "release",
        "auth",
        "--agent-id",
        "agent-a",
        cwd=tmp_path,
    )
    assert released.returncode == 0
    assert payload(released)["status"] == "released"

    reacquired = run_script(
        RESOURCE_LEASE,
        "acquire",
        "auth",
        "--agent-id",
        "agent-b",
        "--session-id",
        "s2",
        "--reason",
        "parallel auth edit",
        "--ttl-seconds",
        "60",
        cwd=tmp_path,
    )
    assert reacquired.returncode == 0
    assert payload(reacquired)["status"] == "acquired"


def test_agent_work_ledger_reports_active_then_completed_work(tmp_path: Path) -> None:
    start = run_script(
        WORK_LEDGER,
        "record",
        "--agent-id",
        "agent-a",
        "--session-id",
        "s1",
        "--task",
        "edit billing",
        "--status",
        "started",
        "--scope",
        "billing/invoice.py",
        cwd=tmp_path,
    )
    assert start.returncode == 0

    active = run_script(WORK_LEDGER, "summary", cwd=tmp_path)
    active_payload = payload(active)
    assert active_payload["total_events"] == 1
    assert active_payload["active_work"][0]["task"] == "edit billing"

    complete = run_script(
        WORK_LEDGER,
        "record",
        "--agent-id",
        "agent-a",
        "--session-id",
        "s1",
        "--task",
        "edit billing",
        "--status",
        "completed",
        "--scope",
        "billing/invoice.py",
        cwd=tmp_path,
    )
    assert complete.returncode == 0

    done = run_script(WORK_LEDGER, "summary", cwd=tmp_path)
    done_payload = payload(done)
    assert done_payload["total_events"] == 2
    assert done_payload["active_work"] == []


def test_approval_ledger_requires_matching_approval(tmp_path: Path) -> None:
    missing = run_script(
        APPROVAL_LEDGER,
        "require",
        "--category",
        "migration",
        "--scope",
        "db/users",
        cwd=tmp_path,
    )
    assert missing.returncode == 2
    assert payload(missing)["status"] == "missing"

    record = run_script(
        APPROVAL_LEDGER,
        "record",
        "--category",
        "migration",
        "--scope",
        "db/users",
        "--reason",
        "schema change",
        "--approved-by",
        "human-reviewer",
        "--verification-command",
        "python3 -m pytest tests/migrations -q",
        "--rollback-plan",
        "restore previous migration and rerun tests",
        cwd=tmp_path,
    )
    assert record.returncode == 0
    assert payload(record)["status"] == "recorded"

    approved = run_script(
        APPROVAL_LEDGER,
        "require",
        "--category",
        "migration",
        "--scope",
        "db/users",
        cwd=tmp_path,
    )
    assert approved.returncode == 0
    approved_payload = payload(approved)
    assert approved_payload["status"] == "approved"
    assert approved_payload["approval"]["rollback_plan"]
