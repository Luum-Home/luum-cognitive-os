#!/usr/bin/env python3
# SCOPE: os-only
"""Audit administrative plan closures that are not implementation claims.

This audit keeps plan-closure disposition honest: legacy checklist items may be
closed by disposition, but they must reference the disposition ledger and a live
successor plan must exist for transferred/deferred work.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "plan-closure-disposition-audit/v1"
DEFAULT_LEDGER = Path("docs/06-Daily/reports/plan-closure-disposition-2026-05-20.md")
DEFAULT_SUCCESSOR = Path(".cognitive-os/plans/architecture/implementation-backlog-from-plan-closure-2026-05-20.md")
PLAN_GLOBS = (
    ".cognitive-os/plans/architecture/*.md",
    ".cognitive-os/plans/features/*.md",
    ".cognitive-os/plans/roadmaps/*.md",
)
DISPOSITION_MARKER_RE = re.compile(r"closed:\s*(?P<reason>.*?)(?:;\s*verified:\s*(?P<proof>[^)]+))?\)")
CHECKED_LINE_RE = re.compile(r"^- \[x\]\s+(?P<text>.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class DispositionRow:
    plan: str
    line: int
    text: str
    reason: str
    proof: str | None
    status: str
    findings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan,
            "line": self.line,
            "text": self.text,
            "reason": self.reason,
            "proof": self.proof,
            "status": self.status,
            "findings": list(self.findings),
        }


def resolve_project_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    for env in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        if os.environ.get(env):
            return Path(os.environ[env]).resolve()
    return Path.cwd().resolve()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def iter_plan_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for glob in PLAN_GLOBS:
        files.extend(root.glob(glob))
    return sorted(set(files))


def classify_disposition(reason: str) -> str:
    low = reason.lower()
    if "archived" in low or "tombstone" in low:
        return "archived_or_tombstoned"
    if "deferred" in low or "shape-b" in low or "future-only" in low:
        return "deferred"
    if "rejected" in low:
        return "rejected"
    if "transferred" in low:
        return "transferred"
    if "implemented" in low or "evidence" in low:
        return "implemented_elsewhere"
    return "closed_by_disposition"


def audit(root: Path, *, ledger_path: Path = DEFAULT_LEDGER, successor_plan: Path = DEFAULT_SUCCESSOR) -> dict[str, Any]:
    ledger = root / ledger_path
    successor = root / successor_plan
    rows: list[DispositionRow] = []
    blockers: list[dict[str, Any]] = []
    ledger_text = ledger.read_text(encoding="utf-8") if ledger.exists() else ""

    for plan in iter_plan_files(root):
        try:
            lines = plan.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            checked = CHECKED_LINE_RE.match(line)
            if not checked or "closed:" not in line:
                continue
            marker = DISPOSITION_MARKER_RE.search(line)
            reason = marker.group("reason").strip() if marker else ""
            proof = marker.group("proof").strip() if marker and marker.group("proof") else None
            findings: list[str] = []
            if not marker:
                findings.append("missing-structured-closed-marker")
            if not proof or str(ledger_path) not in proof:
                findings.append("missing-disposition-ledger-proof")
            if not ledger.exists():
                findings.append("missing-disposition-ledger-file")
            elif rel(plan, root) not in ledger_text:
                findings.append("plan-not-mentioned-in-disposition-ledger")
            status = classify_disposition(reason)
            if status in {"transferred", "deferred", "closed_by_disposition"} and not successor.exists():
                findings.append("missing-successor-active-plan")
            row = DispositionRow(
                plan=rel(plan, root),
                line=line_no,
                text=checked.group("text"),
                reason=reason,
                proof=proof,
                status=status,
                findings=tuple(findings),
            )
            rows.append(row)
            for finding in findings:
                blockers.append({"plan": row.plan, "line": row.line, "finding": finding})

    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project_dir": "<repo-root>",
        "status": "pass" if not blockers else "fail",
        "closed_by_disposition_count": len(rows),
        "by_status": dict(sorted(by_status.items())),
        "ledger": str(ledger_path),
        "successor_plan": str(successor_plan),
        "blockers": blockers,
        "rows": [row.to_dict() for row in rows],
    }


def render_md(payload: dict[str, Any]) -> str:
    lines = [
        f"# Plan Closure Disposition Audit — {payload['generated_at']}",
        "",
        f"Status: **{payload['status']}**",
        "",
        "This report distinguishes `closed_by_disposition` from shipped implementation.",
        "Legacy plan checkboxes closed by disposition are not implementation claims;",
        f"they are tied to `{payload['ledger']}` and successor plan `{payload['successor_plan']}`.",
        "",
        "## Summary",
        "",
        f"- closed_by_disposition_count: {payload['closed_by_disposition_count']}",
        f"- blockers: {len(payload['blockers'])}",
        f"- by_status: `{json.dumps(payload['by_status'], sort_keys=True)}`",
        "",
        "## Rows",
        "",
    ]
    for row in payload["rows"]:
        findings = ", ".join(row["findings"]) if row["findings"] else "none"
        lines.append(f"- `{row['plan']}:L{row['line']}` — {row['status']} — findings: {findings}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit plan checkboxes closed by disposition.")
    parser.add_argument("--project-dir")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    root = resolve_project_dir(args.project_dir)
    payload = audit(root)
    if args.write:
        out_dir = root / "docs" / "06-Daily" / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "plan-closure-disposition-audit-latest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out_dir / "plan-closure-disposition-audit-latest.md").write_text(render_md(payload), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"plan closure disposition audit: status={payload['status']} rows={payload['closed_by_disposition_count']} blockers={len(payload['blockers'])}")
    return 2 if args.strict and payload["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
