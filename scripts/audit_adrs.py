#!/usr/bin/env python3
"""audit_adrs.py — Validate ADR YAML frontmatter and implementation file existence.

Walks docs/adrs/*.md and docs/architecture/adrs/*.md, parses the YAML
frontmatter block (between leading --- delimiters), and reports:

  MISSING_FRONTMATTER      — ADR has no YAML frontmatter (warn only)
  MALFORMED_YAML           — frontmatter exists but fails yaml.safe_load()
  STATUS_REALITY_MISMATCH  — status: implemented but implementation_files missing
  SUPERSEDES_BROKEN_REF    — supersedes[] lists an ADR number not found on disk
  OK                       — frontmatter parses, files verified (or none declared)

CLI flags:
  --json          Machine-readable JSON output (CI-friendly)
  --strict        Exit non-zero on any finding (except MISSING_FRONTMATTER)
  --migrate-from-prose
                  Dry-run: suggest frontmatter for ADRs that lack it (no writes)

Usage:
  python3 scripts/audit_adrs.py
  python3 scripts/audit_adrs.py --strict
  python3 scripts/audit_adrs.py --json
  python3 scripts/audit_adrs.py --migrate-from-prose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML not installed — run: pip install pyyaml")

# ── Repo layout ───────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[1]

ADR_DIRS: list[Path] = [
    REPO_ROOT / "docs" / "adrs",
    REPO_ROOT / "docs" / "architecture" / "adrs",
]

# ── Finding level constants ───────────────────────────────────────────────────

LEVEL_OK = "OK"
LEVEL_WARN = "WARN"
LEVEL_FAIL = "FAIL"

# Finding codes
CODE_MISSING_FRONTMATTER = "MISSING_FRONTMATTER"
CODE_MALFORMED_YAML = "MALFORMED_YAML"
CODE_STATUS_REALITY_MISMATCH = "STATUS_REALITY_MISMATCH"
CODE_SUPERSEDES_BROKEN_REF = "SUPERSEDES_BROKEN_REF"

# Status values that require implementation_files verification
IMPLEMENTED_STATUSES = {"implemented"}

# Valid status values
VALID_STATUSES = {"proposed", "accepted", "implemented", "superseded", "deprecated"}

# ── Helpers ───────────────────────────────────────────────────────────────────


def _extract_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_string_or_None, body_remainder).

    Frontmatter must start at line 1 with '---' and close with '---' before
    any non-whitespace body content.
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return None, text
    if lines[0].rstrip() != "---":
        return None, text

    closing_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            closing_idx = i
            break

    if closing_idx is None:
        return None, text

    fm_lines = lines[1:closing_idx]
    body = "".join(lines[closing_idx + 1 :])
    return "".join(fm_lines), body


def _adr_number_from_filename(path: Path) -> int | None:
    """Extract ADR number from filename like ADR-105-... or 105-..."""
    m = re.match(r"(?:ADR-)?0*([0-9]+)", path.stem)
    return int(m.group(1)) if m else None


def _collect_adr_files() -> list[Path]:
    """Return all ADR markdown files from both ADR directories.

    Deduplicates by ADR number (not filename stem) so that files in
    docs/adrs/ADR-006-*.md and docs/architecture/adrs/006-*.md with the same
    ADR number are treated as one record. The docs/adrs/ version takes
    precedence when both exist for the same number.
    """
    by_number: dict[int | None, Path] = {}
    # Process docs/adrs first so it takes precedence
    for d in ADR_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            if p.stem.upper() == "README":
                continue
            num = _adr_number_from_filename(p)
            # Only insert if not yet seen (first dir wins = docs/adrs takes precedence)
            if num not in by_number:
                by_number[num] = p
    return sorted(by_number.values(), key=lambda p: _adr_number_from_filename(p) or 0)


def _known_adr_numbers(files: list[Path]) -> set[int]:
    nums: set[int] = set()
    for f in files:
        n = _adr_number_from_filename(f)
        if n is not None:
            nums.add(n)
    return nums


def _verify_implementation_files(
    impl_files: list[str],
) -> tuple[list[str], list[str]]:
    """Return (present, missing) lists.

    Uses Path.resolve() for symlink-aware existence checks per project rules.
    """
    present: list[str] = []
    missing: list[str] = []
    for rel in impl_files:
        # Accept both relative and absolute paths; resolve from repo root
        candidate = REPO_ROOT / rel
        resolved = candidate.resolve()
        if resolved.exists():
            present.append(rel)
        else:
            missing.append(rel)
    return present, missing


def _extract_prose_status(body: str) -> str | None:
    """Extract status from common prose patterns for migration suggestions."""
    patterns = [
        r"\*\*Status\*\*:\s*(.+)",
        r"^#+\s*Status\s*$",
        r"^Status:\s*(.+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, body, re.MULTILINE | re.IGNORECASE)
        if m and m.lastindex:
            raw = m.group(1).strip()
            # Map common prose values to schema values
            lower = raw.lower()
            if "implement" in lower:
                return "implemented"
            if "accept" in lower:
                return "accepted"
            if "proposed" in lower or "draft" in lower:
                return "proposed"
            if "superseded" in lower:
                return "superseded"
            if "deprecated" in lower or "retired" in lower:
                return "deprecated"
    return None


def _suggest_frontmatter(path: Path, body: str) -> str:
    """Generate a suggested frontmatter block for an ADR lacking it."""
    adr_num = _adr_number_from_filename(path) or 0
    # Extract title from first heading
    title = "UNKNOWN"
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = re.sub(r"^#+\s*", "", stripped)
            title = re.sub(r"\s*—.*$", "", title).strip()
            break

    status = _extract_prose_status(body) or "accepted"

    lines = [
        "---",
        f"adr: {adr_num}",
        f'title: "{title}"',
        f"status: {status}",
        "date: YYYY-MM-DD",
        "supersedes: []",
        "superseded_by: null",
        "implementation_files: []",
        "tier: standard",
        "tags: []",
        "---",
    ]
    return "\n".join(lines)


# ── Audit core ────────────────────────────────────────────────────────────────


def audit_file(path: Path, known_adrs: set[int]) -> dict[str, Any]:
    """Audit a single ADR file. Returns a findings dict."""
    adr_num = _adr_number_from_filename(path) or 0
    text = path.read_text(encoding="utf-8")
    fm_str, _body = _extract_frontmatter(text)

    base: dict[str, Any] = {"adr": adr_num, "file": str(path.relative_to(REPO_ROOT))}

    # ── No frontmatter ────────────────────────────────────────────────────────
    if fm_str is None:
        return {
            **base,
            "level": LEVEL_WARN,
            "code": CODE_MISSING_FRONTMATTER,
            "message": "No YAML frontmatter found (prose-only ADR)",
        }

    # ── Parse YAML ────────────────────────────────────────────────────────────
    try:
        fm: dict[str, Any] = yaml.safe_load(fm_str) or {}
    except yaml.YAMLError as exc:
        return {
            **base,
            "level": LEVEL_FAIL,
            "code": CODE_MALFORMED_YAML,
            "message": f"YAML parse error: {exc}",
        }

    if not isinstance(fm, dict):
        return {
            **base,
            "level": LEVEL_FAIL,
            "code": CODE_MALFORMED_YAML,
            "message": "Frontmatter parsed but is not a YAML mapping",
        }

    status: str = str(fm.get("status", "")).lower()
    impl_files: list[str] = fm.get("implementation_files") or []
    supersedes: list[int] = fm.get("supersedes") or []

    findings: list[dict[str, Any]] = []

    # ── Supersedes reference check ────────────────────────────────────────────
    for ref_num in supersedes:
        if isinstance(ref_num, int) and ref_num not in known_adrs:
            findings.append(
                {
                    **base,
                    "level": LEVEL_WARN,
                    "code": CODE_SUPERSEDES_BROKEN_REF,
                    "message": f"supersedes references ADR-{ref_num} which was not found on disk",
                }
            )

    # ── Implementation file verification ─────────────────────────────────────
    if status in IMPLEMENTED_STATUSES:
        present, missing = _verify_implementation_files(impl_files)
        if missing:
            findings.append(
                {
                    **base,
                    "level": LEVEL_FAIL,
                    "code": CODE_STATUS_REALITY_MISMATCH,
                    "status": status,
                    "missing_files": missing,
                    "files_verified": len(present),
                    "message": (
                        f"status={status!r} but {len(missing)} file(s) missing: "
                        + ", ".join(missing)
                    ),
                }
            )
        else:
            return {
                **base,
                "level": LEVEL_OK,
                "code": CODE_OK if not findings else findings[0]["code"],
                "status": status,
                "files_verified": len(present),
                "message": f"OK — {len(present)} file(s) verified",
            }

    if findings:
        # Return worst finding first
        findings.sort(key=lambda f: (0 if f["level"] == LEVEL_FAIL else 1))
        return findings[0]

    return {
        **base,
        "level": LEVEL_OK,
        "code": "OK",
        "status": status,
        "files_verified": 0,
        "message": f"OK — status={status!r}, no implementation_files declared",
    }


# Needed after defining audit_file
CODE_OK = "OK"


def run_audit(
    strict: bool = False,
    output_json: bool = False,
    migrate_from_prose: bool = False,
) -> int:
    """Main audit runner. Returns exit code."""
    adr_files = _collect_adr_files()
    known_adrs = _known_adr_numbers(adr_files)

    findings: list[dict[str, Any]] = []
    migration_suggestions: list[dict[str, str]] = []

    for path in adr_files:
        result = audit_file(path, known_adrs)
        findings.append(result)

        if migrate_from_prose and result.get("code") == CODE_MISSING_FRONTMATTER:
            text = path.read_text(encoding="utf-8")
            _fm, body = _extract_frontmatter(text)
            suggestion = _suggest_frontmatter(path, body)
            migration_suggestions.append(
                {
                    "file": result["file"],
                    "suggested_frontmatter": suggestion,
                }
            )

    total = len(findings)
    with_frontmatter = sum(
        1
        for f in findings
        if f.get("code") not in (CODE_MISSING_FRONTMATTER, CODE_MALFORMED_YAML)
        or f.get("level") == LEVEL_OK
    )
    # Recount: has frontmatter = did not get MISSING_FRONTMATTER
    with_frontmatter = sum(
        1 for f in findings if f.get("code") != CODE_MISSING_FRONTMATTER
    )

    has_failures = any(f.get("level") == LEVEL_FAIL for f in findings)

    if output_json:
        output: dict[str, Any] = {
            "scanned": total,
            "with_frontmatter": with_frontmatter,
            "findings": findings,
        }
        if migration_suggestions:
            output["migration_suggestions"] = migration_suggestions
        print(json.dumps(output, indent=2))
    else:
        _print_human_report(findings, migration_suggestions)

    if strict and has_failures:
        return 1
    return 0


def _print_human_report(
    findings: list[dict[str, Any]],
    suggestions: list[dict[str, str]],
) -> None:
    total = len(findings)
    with_fm = sum(1 for f in findings if f.get("code") != CODE_MISSING_FRONTMATTER)
    ok_count = sum(1 for f in findings if f.get("level") == LEVEL_OK)
    warn_count = sum(1 for f in findings if f.get("level") == LEVEL_WARN)
    fail_count = sum(1 for f in findings if f.get("level") == LEVEL_FAIL)

    print(
        f"\nADR Frontmatter Audit — {total} files scanned, "
        f"{with_fm} with frontmatter\n"
        f"  OK: {ok_count}  WARN: {warn_count}  FAIL: {fail_count}\n"
    )

    for f in findings:
        level = f.get("level", "?")
        code = f.get("code", "?")
        adr = f.get("adr", "?")
        msg = f.get("message", "")
        if level == LEVEL_OK:
            print(f"  [OK]   ADR-{adr:03d}  {msg}")
        elif level == LEVEL_WARN:
            print(f"  [WARN] ADR-{adr:03d}  {code}: {msg}")
        else:
            print(f"  [FAIL] ADR-{adr:03d}  {code}: {msg}")

    if suggestions:
        print("\n--- Migration suggestions (--migrate-from-prose) ---\n")
        for s in suggestions:
            print(f"# {s['file']}")
            print(s["suggested_frontmatter"])
            print()


# ── CLI entry point ───────────────────────────────────────────────────────────


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit ADR YAML frontmatter and validate implementation_files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on any FAIL finding",
    )
    parser.add_argument(
        "--migrate-from-prose",
        action="store_true",
        dest="migrate_from_prose",
        help="Dry-run: suggest frontmatter for ADRs that lack it (no writes)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    exit_code = run_audit(
        strict=args.strict,
        output_json=args.output_json,
        migrate_from_prose=args.migrate_from_prose,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
