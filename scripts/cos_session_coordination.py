#!/usr/bin/env python3
# SCOPE: both
"""Cross-session coordination CLI for claims, ADR ownership, and worktree intake."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.session_coordination import (  # noqa: E402
    acquire_claim,
    adr_tombstone_findings,
    findings_to_dict,
    read_claims,
    record_worktree_intake,
    release_claim,
    worktree_intake_findings,
)


def project_dir(args: argparse.Namespace) -> Path:
    return Path(
        args.project_dir
        or os.environ.get("COGNITIVE_OS_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    ).resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    claim = sub.add_parser("claim", help="Acquire an intent claim")
    claim.add_argument("--kind", required=True, choices=["task", "adr-number", "path", "policy", "skill", "primitive"])
    claim.add_argument("--subject", required=True)
    claim.add_argument("--session-id", default=None)
    claim.add_argument("--owner", default=None)
    claim.add_argument("--ttl-seconds", type=int, default=86400)
    claim.add_argument("--metadata", action="append", default=[], help="key=value metadata pairs")

    release = sub.add_parser("release", help="Release an owned claim")
    release.add_argument("--kind", required=True)
    release.add_argument("--subject", required=True)
    release.add_argument("--session-id", default=None)

    sub.add_parser("list", help="List active claims")

    tombstone = sub.add_parser("check-adr-tombstone", help="Check whether an ADR number can be tombstoned")
    tombstone.add_argument("--number", type=int, required=True)
    tombstone.add_argument("--session-id", default=None)

    intake = sub.add_parser("record-worktree-intake", help="Record review of a sibling worktree")
    intake.add_argument("--other-worktree", required=True)
    intake.add_argument("--policy", required=True, choices=["read-only", "import-approved", "ignore-approved"])
    intake.add_argument("--summary", required=True)
    intake.add_argument("--session-id", default=None)

    check = sub.add_parser("check", help="Run coordination checks")
    check.add_argument("--require-worktree-intake", action="store_true")
    check.add_argument("--warn-only", action="store_true")
    return parser


def parse_metadata(pairs: Sequence[str]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"metadata must be key=value: {pair}")
        metadata[key] = value
    return metadata


def emit(args: argparse.Namespace, payload: dict[str, object], human: str, *, ok: bool = True) -> int:
    if args.json:
        print(json.dumps({"ok": ok, **payload}, indent=2, sort_keys=True))
    else:
        print(human)
    return 0 if ok else 2


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv or sys.argv[1:]))
    project = project_dir(args)

    if args.command == "claim":
        result = acquire_claim(
            project,
            kind=args.kind,
            subject=args.subject,
            session_id=args.session_id,
            owner=args.owner,
            ttl_seconds=args.ttl_seconds,
            metadata=parse_metadata(args.metadata),
        )
        if result.status == "blocked":
            return emit(args, result.to_dict(), f"BLOCKED: {args.kind} {args.subject} is held by another session", ok=False)
        claim = result.claim or {}
        return emit(args, result.to_dict(), f"CLAIMED: {claim.get('kind')} {claim.get('subject')} session={claim.get('session_id')}")

    if args.command == "release":
        result = release_claim(project, kind=args.kind, subject=args.subject, session_id=args.session_id)
        return emit(args, result.to_dict(), f"{result.status.upper()}: {args.kind} {args.subject}", ok=result.status != "blocked")

    if args.command == "list":
        claims = read_claims(project)
        if args.json:
            print(json.dumps({"ok": True, "claims": claims}, indent=2, sort_keys=True))
        else:
            for claim in claims:
                print(f"{claim.get('kind')} {claim.get('subject')} session={claim.get('session_id')} branch={claim.get('branch')}")
        return 0

    if args.command == "check-adr-tombstone":
        findings = adr_tombstone_findings(project, number=args.number, session_id=args.session_id)
        ok = not any(f.status == "FAIL" for f in findings)
        if args.json:
            print(json.dumps({"ok": ok, "findings": findings_to_dict(findings)}, indent=2, sort_keys=True))
        elif ok:
            print(f"ADR-{args.number:03d}: tombstone allowed")
        else:
            for finding in findings:
                print(f"{finding.status}: {finding.message} ({finding.evidence})", file=sys.stderr)
        return 0 if ok else 2

    if args.command == "record-worktree-intake":
        record = record_worktree_intake(
            project,
            other_worktree=args.other_worktree,
            policy=args.policy,
            summary=args.summary,
            session_id=args.session_id,
        )
        return emit(args, {"record": record}, f"RECORDED: {record['policy']} {record['other_worktree']}")

    if args.command == "check":
        findings = []
        if args.require_worktree_intake:
            findings.extend(worktree_intake_findings(project, require_for_all=not args.warn_only))
        ok = not any(f.status == "FAIL" for f in findings)
        if args.json:
            print(json.dumps({"ok": ok, "findings": findings_to_dict(findings)}, indent=2, sort_keys=True))
        elif ok:
            print("session-coordination: PASS")
        else:
            for finding in findings:
                print(f"{finding.status}: {finding.message} ({finding.evidence})", file=sys.stderr)
        return 0 if ok else 2

    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
