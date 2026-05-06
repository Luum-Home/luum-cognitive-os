from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from lib.agent_message_bus import ack_message, blocker_findings, inbox, send_message, unacked_blockers


pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos_agent_message.py"


def test_send_message_appears_in_target_inbox(tmp_path: Path) -> None:
    message = send_message(
        tmp_path,
        from_session="auditor",
        to_session="operator",
        message_type="audit_finding",
        severity="block",
        target="docs/adrs/ADR-171-tombstone.md",
        body="ADR-171 collides with active ownership.",
    )

    rows = inbox(tmp_path, session_id="operator")

    assert [row["message_id"] for row in rows] == [message["message_id"]]
    assert unacked_blockers(tmp_path, session_id="operator")[0]["message_id"] == message["message_id"]


def test_ack_removes_message_from_default_inbox_and_blockers(tmp_path: Path) -> None:
    message = send_message(
        tmp_path,
        from_session="auditor",
        to_session="operator",
        message_type="implementation_request",
        severity="block",
        body="Fix collision.",
    )

    ack_message(tmp_path, message_id_value=message["message_id"], session_id="operator", status="applied", note="fixed")

    assert inbox(tmp_path, session_id="operator") == []
    with_acked = inbox(tmp_path, session_id="operator", include_acked=True)
    assert with_acked[0]["ack"]["status"] == "applied"
    assert unacked_blockers(tmp_path, session_id="operator") == []


def test_blocker_findings_are_session_scoped(tmp_path: Path) -> None:
    send_message(tmp_path, from_session="auditor", to_session="operator-a", message_type="audit_finding", severity="block", body="A")
    send_message(tmp_path, from_session="auditor", to_session="operator-b", message_type="audit_finding", severity="warn", body="B")

    findings = blocker_findings(tmp_path, session_id="operator-a")

    assert len(findings) == 1
    assert "unacknowledged blocking agent message" in findings[0].message
    assert blocker_findings(tmp_path, session_id="operator-b") == []


def test_cli_send_inbox_ack_check(tmp_path: Path) -> None:
    send = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-dir",
            str(tmp_path),
            "--json",
            "send",
            "--from-session",
            "auditor",
            "--to-session",
            "operator",
            "--severity",
            "block",
            "--body",
            "Fix ADR collision.",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert send.returncode == 0
    message_id = json.loads(send.stdout)["message"]["message_id"]

    check = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-dir", str(tmp_path), "--json", "check", "--session-id", "operator"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert check.returncode == 2
    assert json.loads(check.stdout)["findings"][0]["source"] == message_id

    ack = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-dir",
            str(tmp_path),
            "--json",
            "ack",
            "--message-id",
            message_id,
            "--session-id",
            "operator",
            "--status",
            "applied",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert ack.returncode == 0

    post = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-dir", str(tmp_path), "--json", "check", "--session-id", "operator"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert post.returncode == 0
