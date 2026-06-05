#!/usr/bin/env python3
# SCOPE: both
"""Directed auditor/operator message bus for cross-session agents."""

from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))
from lib.script_helpers import emit_result as emit

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.agent_message_bus import (  # noqa: E402
    ack_message,
    blocker_findings,
    current_session,
    findings_to_dict,
    inbox,
    send_message,
)


def project_dir(args: argparse.Namespace) -> Path:
    return Path(args.project_dir or os.environ.get("COGNITIVE_OS_PROJECT_DIR") or os.getcwd()).resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    send = sub.add_parser("send", help="Send a directed message")
    send.add_argument("--from-session", default=None)
    send.add_argument("--to-session", required=True)
    send.add_argument("--type", default="audit_finding", choices=["audit_finding", "implementation_request", "question", "reply", "status"])
    send.add_argument("--severity", default="info", choices=["info", "warn", "block"])
    send.add_argument("--role", default="auditor")
    send.add_argument("--target", default="")
    send.add_argument("--body", required=True)

    box = sub.add_parser("inbox", help="Show inbox for a session")
    box.add_argument("--session-id", default=None)
    box.add_argument("--include-acked", action="store_true")

    ack = sub.add_parser("ack", help="Acknowledge a message")
    ack.add_argument("--message-id", required=True)
    ack.add_argument("--session-id", default=None)
    ack.add_argument("--status", required=True, choices=["accepted", "applied", "rejected", "needs-clarification", "seen"])
    ack.add_argument("--note", default="")

    check = sub.add_parser("check", help="Fail on unacknowledged blocking messages")
    check.add_argument("--session-id", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv or sys.argv[1:]))
    project = project_dir(args)

    if args.cmd == "send":
        row = send_message(
            project,
            from_session=args.from_session or current_session(),
            to_session=args.to_session,
            message_type=args.type,
            severity=args.severity,
            role=args.role,
            target=args.target,
            body=args.body,
        )
        return emit(args, {"message": row}, f"SENT {row['message_id']} severity={row['severity']} to={row['to_session']}")

    if args.cmd == "inbox":
        rows = inbox(project, session_id=args.session_id or current_session(), include_acked=args.include_acked)
        if args.json:
            print(json.dumps({"ok": True, "messages": rows}, indent=2, sort_keys=True))
        else:
            for row in rows:
                print(f"{row.get('message_id')} [{row.get('severity')}] from={row.get('from_session')} target={row.get('target')} {row.get('body')}")
        return 0

    if args.cmd == "ack":
        row = ack_message(project, message_id_value=args.message_id, session_id=args.session_id or current_session(), status=args.status, note=args.note)
        return emit(args, {"ack": row}, f"ACK {row['message_id']} status={row['status']}")

    if args.cmd == "check":
        findings = blocker_findings(project, session_id=args.session_id or current_session())
        ok = not findings
        if args.json:
            print(json.dumps({"ok": ok, "findings": findings_to_dict(findings)}, indent=2, sort_keys=True))
        elif ok:
            print("agent-message: PASS")
        else:
            for finding in findings:
                print(f"{finding.status}: {finding.message} ({finding.evidence})", file=sys.stderr)
        return 0 if ok else 2

    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
