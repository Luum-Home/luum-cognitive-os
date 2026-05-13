#!/usr/bin/env python3
# SCOPE: both
"""Create neutral ADR tombstones without reusing decision numbers."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

try:
    from lib.session_coordination import adr_tombstone_findings
except Exception:  # pragma: no cover - script must remain importable in minimal copies
    adr_tombstone_findings = None

REQUIRED_SECTIONS = (
    "Status",
    "Context",
    "Decision",
    "Consequences",
    "Alternatives rejected",
    "Verification",
)

SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv"}
SKIP_PREFIXES = (
    (".claude", "plugins"),
    ("dashboard", "node_modules"),
)


@dataclass(frozen=True)
class TombstoneResult:
    """Result from applying an ADR tombstone."""

    path: str
    adr_id: str
    number: int
    title: str
    wrote: bool
    removed_paths: list[str]
    updated_references: list[str]


def utc_date() -> str:
    """Return the current UTC date."""

    return datetime.now(timezone.utc).date().isoformat()


def normalize_title(value: str) -> str:
    """Return a compact title for a tombstone ADR."""

    title = " ".join(value.strip().split())
    return title or "Removed architecture decision"


def adr_id(number: int) -> str:
    """Return the canonical ADR id for a number."""

    if number < 1:
        raise ValueError("ADR number must be positive")
    return f"ADR-{number:03d}"


def adr_number_from_name(path: Path) -> int | None:
    """Extract the project ADR number from a filename."""

    match = re.match(r"ADR-0*([0-9]+)", path.name)
    return int(match.group(1)) if match else None


def iter_adr_files(adrs_dir: Path, number: int) -> list[Path]:
    """Return every project-level ADR file for a number, including addenda."""

    return sorted(path for path in adrs_dir.glob("ADR-*.md") if adr_number_from_name(path) == number)


def first_party_text_files(project_dir: Path) -> Iterable[Path]:
    """Yield first-party text-ish files that can safely receive link rewrites."""

    allowed_suffixes = {
        ".md",
        ".txt",
        ".yaml",
        ".yml",
        ".json",
        ".py",
        ".sh",
        ".toml",
        ".lock",
    }
    for path in project_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(project_dir)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        if any(relative.parts[: len(prefix)] == prefix for prefix in SKIP_PREFIXES):
            continue
        if path.suffix.lower() in allowed_suffixes or path.name in {"README", "Makefile"}:
            yield path


def render_frontmatter(*, number: int, title: str, date: str, implementation_files: Sequence[str]) -> str:
    """Render tombstone frontmatter."""

    impl_lines = "\n".join(f"  - {item}" for item in implementation_files) or "  []"
    return (
        "---\n"
        f"adr: {number}\n"
        f"title: {title}\n"
        "status: tombstone\n"
        f"date: {date}\n"
        "supersedes: []\n"
        "superseded_by: null\n"
        f"implementation_files:\n{impl_lines}\n"
        "tier: maintainer\n"
        "tags: [adr, tombstone, governance]\n"
        "---\n"
    )


def render_body(*, number: int, title: str, date: str, reason: str, verification_command: str) -> str:
    """Render the contract-compliant tombstone body."""

    aid = adr_id(number)
    return f"""# {aid}: {title}

## Status

**Tombstone** — {date}

## Context

{reason}

This ADR number remains reserved so the project decision ledger stays auditable.
The removed decision content is not active architecture and must not be recreated
under the same number.

## Decision

Keep {aid} as a neutral tombstone. Do not reuse this number for a different
decision. If a future decision is needed, allocate a new ADR number through the
canonical ADR authoring flow.

## Consequences

### Positive

- ADR numbering remains contiguous and machine-checkable.
- Historical references to this number resolve to an explicit neutral record.
- Removed decision content stays out of active runtime, docs, hooks, manifests,
  and tests.

### Negative

- The tombstone intentionally preserves only the number, not the removed prose.
- Readers must use surrounding ADR history or git history for deeper archaeology.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Delete the ADR number entirely | Rejected because it creates a silent numbering gap and makes audits ambiguous. |
| Reuse the number for a new decision | Rejected because ADR numbers are stable identifiers, not recyclable slots. |
| Keep removed prose in active docs | Rejected because removed integration details can be mistaken for supported architecture. |

## Verification

```bash
{verification_command}
```
"""


def render_tombstone(
    *,
    number: int,
    title: str,
    reason: str,
    date: str | None = None,
    verification_command: str = "python3 -m pytest tests/unit/test_adr_tombstone.py tests/contracts/test_adr_numbering_integrity.py -q",
    implementation_files: Sequence[str] = ("scripts/adr_tombstone.py", "tests/unit/test_adr_tombstone.py"),
) -> str:
    """Render a full tombstone ADR."""

    title = normalize_title(title)
    actual_date = date or utc_date()
    text = render_frontmatter(
        number=number,
        title=title,
        date=actual_date,
        implementation_files=implementation_files,
    ) + render_body(
        number=number,
        title=title,
        date=actual_date,
        reason=reason,
        verification_command=verification_command,
    )
    issues = validate_tombstone_text(text, number=number, forbidden_tokens=())
    if issues:
        raise ValueError(f"Rendered tombstone failed validation: {issues}")
    return text


def validate_tombstone_text(text: str, *, number: int, forbidden_tokens: Sequence[str]) -> list[str]:
    """Return validation issues for tombstone text."""

    issues: list[str] = []
    if f"# {adr_id(number)}:" not in text:
        issues.append("heading-number")
    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in text:
            issues.append(f"section:{section}")
    if "status: tombstone" not in text:
        issues.append("frontmatter-status")
    lowered = text.lower()
    for token in forbidden_tokens:
        if token and token.lower() in lowered:
            issues.append(f"forbidden-token:{token}")
    return issues


def update_references(project_dir: Path, *, old_names: Sequence[str], new_name: str, dry_run: bool) -> list[str]:
    """Replace old ADR filenames with the new tombstone filename."""

    changed: list[str] = []
    if not old_names:
        return changed
    for path in first_party_text_files(project_dir):
        text = path.read_text(encoding="utf-8", errors="replace")
        updated = text
        for old_name in old_names:
            updated = updated.replace(old_name, new_name)
        if updated != text:
            changed.append(str(path.relative_to(project_dir)))
            if not dry_run:
                path.write_text(updated, encoding="utf-8")
    return changed


def assert_forbidden_tokens_absent(project_dir: Path, tokens: Sequence[str]) -> None:
    """Fail if any forbidden token appears in first-party paths or text."""

    offenders: list[str] = []
    lowered_tokens = [token.lower() for token in tokens if token]
    if not lowered_tokens:
        return
    for path in first_party_text_files(project_dir):
        relative = str(path.relative_to(project_dir))
        lowered_path = relative.lower()
        if any(token in lowered_path for token in lowered_tokens):
            offenders.append(relative)
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if any(token in text for token in lowered_tokens):
            offenders.append(relative)
    if offenders:
        raise ValueError("Forbidden token(s) remain in first-party files: " + ", ".join(sorted(offenders)))


def create_tombstone(
    *,
    project_dir: Path,
    number: int,
    title: str = "Removed architecture decision",
    reason: str = "The original decision content was removed from the active architecture surface.",
    date: str | None = None,
    forbidden_tokens: Sequence[str] = (),
    update_links: bool = True,
    validate_forbidden_tokens: bool = False,
    force_replace_active: bool = False,
    session_id: str | None = None,
    dry_run: bool = False,
) -> TombstoneResult:
    """Create a neutral tombstone for an ADR number.

    By default this refuses to replace active ADR files. A tombstone is a
    reservation for a removed decision, not a way to recycle or erase a number
    already owned by another session.
    """

    project_dir = project_dir.resolve()
    adrs_dir = project_dir / "docs" / "02-Decisions" / "adrs"
    adrs_dir.mkdir(parents=True, exist_ok=True)
    aid = adr_id(number)
    target = adrs_dir / f"{aid}-tombstone.md"
    existing = iter_adr_files(adrs_dir, number)
    old_names = [path.name for path in existing if path.name != target.name]
    if not force_replace_active and adr_tombstone_findings is not None:
        findings = adr_tombstone_findings(project_dir, number=number, session_id=session_id)
        if findings:
            rendered = "; ".join(f"{finding.message}: {finding.evidence}" for finding in findings)
            raise ValueError(rendered)
    text = render_tombstone(number=number, title=title, reason=reason, date=date)
    issues = validate_tombstone_text(text, number=number, forbidden_tokens=forbidden_tokens)
    if issues:
        raise ValueError(f"Tombstone failed validation: {issues}")

    removed: list[str] = []
    if not dry_run:
        target.write_text(text, encoding="utf-8")
        for path in existing:
            if path == target:
                continue
            removed.append(str(path.relative_to(project_dir)))
            path.unlink(missing_ok=True)
    else:
        removed = [str(path.relative_to(project_dir)) for path in existing if path != target]

    updated_refs = update_references(project_dir, old_names=old_names, new_name=target.name, dry_run=dry_run) if update_links else []
    if validate_forbidden_tokens and not dry_run:
        assert_forbidden_tokens_absent(project_dir, forbidden_tokens)

    return TombstoneResult(
        path=str(target.relative_to(project_dir)),
        adr_id=aid,
        number=number,
        title=normalize_title(title),
        wrote=not dry_run,
        removed_paths=removed,
        updated_references=updated_refs,
    )


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""

    parser = argparse.ArgumentParser(description="Create a neutral tombstone for a removed ADR number")
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--number", type=int, required=True)
    parser.add_argument("--title", default="Removed architecture decision")
    parser.add_argument("--reason", default="The original decision content was removed from the active architecture surface.")
    parser.add_argument("--date", default=None)
    parser.add_argument("--forbidden-token", action="append", default=[])
    parser.add_argument("--no-update-links", action="store_true")
    parser.add_argument("--validate-forbidden-tokens", action="store_true")
    parser.add_argument("--force-replace-active", action="store_true", help="Allow replacing active ADR files; requires explicit operator review")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    args = build_parser().parse_args(argv)
    try:
        result = create_tombstone(
            project_dir=Path(args.project_dir),
            number=args.number,
            title=args.title,
            reason=args.reason,
            date=args.date,
            forbidden_tokens=args.forbidden_token,
            update_links=not args.no_update_links,
            validate_forbidden_tokens=args.validate_forbidden_tokens,
            force_replace_active=args.force_replace_active,
            session_id=args.session_id,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}", file=os.sys.stderr)
        return 1
    payload = asdict(result)
    if args.json:
        print(json.dumps({"ok": True, **payload}, indent=2))
    else:
        print(f"{result.adr_id} tombstone -> {result.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
