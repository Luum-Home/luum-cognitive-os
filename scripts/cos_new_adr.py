#!/usr/bin/env python3
# SCOPE: both
"""Create contract-compliant ADR drafts from the canonical COS template."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from scripts import adr_reserve

REQUIRED_SECTIONS = (
    "Status",
    "Context",
    "Decision",
    "Consequences",
    "Alternatives rejected",
    "Verification",
)


@dataclass(frozen=True)
class AdrDraft:
    """Generated ADR draft metadata."""

    path: str
    adr_id: str
    title: str
    number: int
    status: str
    tier: str
    wrote: bool


def utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def normalize_tag(value: str) -> str:
    return "-".join(part for part in value.lower().replace("_", "-").split("-") if part)


def render_frontmatter(
    *,
    number: int,
    title: str,
    status: str,
    date: str,
    tier: str,
    tags: Sequence[str],
    implementation_files: Sequence[str],
    verification_command: str,
) -> str:
    tag_text = ", ".join(normalize_tag(tag) for tag in tags if normalize_tag(tag))
    impl_lines = "\n".join(f"  - {path}" for path in implementation_files)
    if not impl_lines:
        impl_lines = "  []"
    return (
        "---\n"
        f"adr: {number}\n"
        f"title: {title}\n"
        f"status: {status}\n"
        f"date: {date}\n"
        "supersedes: []\n"
        "superseded_by: null\n"
        f"implementation_files:\n{impl_lines}\n"
        "verification:\n"
        "  level: strong\n"
        "  commands:\n"
        f"    - {verification_command}\n"
        "  proves: [behavior_contract]\n"
        f"tier: {tier}\n"
        f"tags: [{tag_text}]\n"
        "---\n"
    )


def render_body(*, adr_id: str, title: str, status: str, date: str, context: str, decision: str, verification_command: str) -> str:
    status_label = status.capitalize()
    return f"""# {adr_id}: {title}

## Status

**{status_label}** — {date}

## Context

{context}

## Decision

{decision}

## Consequences

### Positive

- New ADRs start from a contract-compliant structure instead of relying on agent memory.
- Reservation, section shape, alternatives, and runnable verification are part of the authoring path.

### Negative

- The helper adds a small process step before writing a decision.
- Draft text still needs human/agent judgment; this primitive enforces shape, not architectural quality.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Hand-write ADRs from memory | Rejected because recent ADRs drifted on required sections and evidence shape. |
| Rely only on post-hoc audit tests | Rejected because the failure arrives after the authoring mistake instead of preventing it at draft creation. |

## Verification

```bash
{verification_command}
```
"""


def validate_rendered_contract(text: str) -> list[str]:
    missing = [section for section in REQUIRED_SECTIONS if f"## {section}" not in text]
    if "```" not in text:
        missing.append("Verification fenced code block")
    if "grep -rn 'ADR-" in text or 'grep -rn "ADR-' in text:
        missing.append("non-theatrical verification command")
    if "verification:" not in text or "proves:" not in text:
        missing.append("verification frontmatter")
    if "| Alternative | Why rejected |" not in text:
        missing.append("Alternatives rejected table")
    return missing


def create_adr(
    *,
    project_dir: Path,
    title: str,
    status: str = "proposed",
    tier: str = "maintainer",
    tags: Sequence[str] = ("adr", "governance"),
    implementation_files: Sequence[str] = (),
    context: str = "This ADR was created through the COS ADR authoring primitive. Replace this paragraph with the concrete problem, evidence, incident, or operator directive that motivated the decision.",
    decision: str = "Replace this paragraph with the decision. Keep it declarative and falsifiable.",
    verification_command: str = "python3 -m pytest tests/audit/test_adr_contracts.py -q",
    session_id: str | None = None,
    owner: str | None = None,
    ttl_seconds: int = 86400,
    dry_run: bool = False,
) -> AdrDraft:
    reservation = adr_reserve.reserve(
        project_dir=project_dir,
        title=title,
        session_id=session_id or adr_reserve.current_session(),
        owner=owner or os.environ.get("USER", "unknown"),
        ttl_seconds=ttl_seconds,
    )
    path = project_dir / reservation.path
    if path.exists():
        raise FileExistsError(f"ADR path already exists: {path}")
    date = utc_date()
    text = render_frontmatter(
        number=reservation.number,
        title=title,
        status=status,
        date=date,
        tier=tier,
        tags=tags,
        implementation_files=implementation_files,
        verification_command=verification_command,
    ) + render_body(
        adr_id=reservation.adr_id,
        title=title,
        status=status,
        date=date,
        context=context,
        decision=decision,
        verification_command=verification_command,
    )
    issues = validate_rendered_contract(text)
    if issues:
        raise ValueError(f"Generated ADR failed contract preflight: {issues}")
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return AdrDraft(
        path=reservation.path,
        adr_id=reservation.adr_id,
        title=title,
        number=reservation.number,
        status=status,
        tier=tier,
        wrote=not dry_run,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a contract-compliant ADR draft with an atomic reservation")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--title", required=True)
    parser.add_argument("--status", default="proposed", choices=["proposed", "accepted", "implemented", "superseded", "deprecated"])
    parser.add_argument("--tier", default="maintainer", choices=["core", "team", "maintainer", "lab", "lean", "standard", "strict", "meta"])
    parser.add_argument("--tag", action="append", dest="tags", default=[])
    parser.add_argument("--implementation-file", action="append", dest="implementation_files", default=[])
    parser.add_argument("--context", default=None)
    parser.add_argument("--decision", default=None)
    parser.add_argument("--verification-command", default="python3 -m pytest tests/audit/test_adr_contracts.py -q")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--owner", default=None)
    parser.add_argument("--ttl-seconds", type=int, default=86400)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tags = args.tags or ["adr", "governance"]
    draft = create_adr(
        project_dir=Path(args.project_dir).resolve(),
        title=args.title,
        status=args.status,
        tier=args.tier,
        tags=tags,
        implementation_files=args.implementation_files,
        context=args.context or "This ADR was created through the COS ADR authoring primitive. Replace this paragraph with the concrete problem, evidence, incident, or operator directive that motivated the decision.",
        decision=args.decision or "Replace this paragraph with the decision. Keep it declarative and falsifiable.",
        verification_command=args.verification_command,
        session_id=args.session_id,
        owner=args.owner,
        ttl_seconds=args.ttl_seconds,
        dry_run=args.dry_run,
    )
    payload = asdict(draft)
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        action = "would write" if not draft.wrote else "wrote"
        print(f"{action}: {draft.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
