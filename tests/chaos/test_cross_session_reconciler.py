from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.chaos

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_LEASE = ROOT / "scripts" / "resource_lease.py"
WORK_LEDGER = ROOT / "scripts" / "agent_work_ledger.py"
APPROVAL_LEDGER = ROOT / "scripts" / "approval_ledger.py"
RECONCILER = ROOT / "scripts" / "cross_session_reconciler.py"


def run_script(script: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--project-dir", str(cwd), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_cross_session_reconciler_reports_mixed_runtime_state(tmp_path: Path) -> None:
    (tmp_path / "cognitive-os.yaml").write_text(
        """
concurrency_safety:
  resource_leases:
    critical_domains:
      - auth
      - deploy
""".lstrip(),
        encoding="utf-8",
    )

    assert run_script(
        RESOURCE_LEASE,
        "acquire",
        "auth",
        "--agent-id",
        "agent-a",
        "--session-id",
        "s1",
        "--reason",
        "chaos interrupted auth edit",
        "--ttl-seconds",
        "60",
        cwd=tmp_path,
    ).returncode == 0
    assert run_script(
        WORK_LEDGER,
        "record",
        "--agent-id",
        "agent-a",
        "--session-id",
        "s1",
        "--task",
        "auth edit",
        "--status",
        "started",
        "--scope",
        "auth/policy.py",
        cwd=tmp_path,
    ).returncode == 0
    assert run_script(
        APPROVAL_LEDGER,
        "record",
        "--category",
        "critical-domain",
        "--scope",
        "auth",
        "--reason",
        "critical auth change",
        "--approved-by",
        "human-reviewer",
        "--verification-command",
        "python3 -m pytest tests/auth -q",
        "--rollback-plan",
        "revert auth policy change",
        cwd=tmp_path,
    ).returncode == 0

    report_proc = run_script(RECONCILER, "--json", cwd=tmp_path)
    assert report_proc.returncode == 0, report_proc.stderr
    report = json.loads(report_proc.stdout)

    assert report["config"]["resource_leases"]["critical_domains"] == ["auth", "deploy"]
    assert report["resource_leases"][0]["resource"] == "auth"
    assert report["agent_work_events"][0]["status"] == "started"
    assert report["approval_events"][0]["category"] == "critical-domain"
    assert report["preserve_branches"]["available"] is False
