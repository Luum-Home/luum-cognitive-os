#!/usr/bin/env python3
# SCOPE: os-only
"""ADR-274 — Audit ADRs for §Operational Guide section presence.

Scans docs/02-Decisions/adrs/ADR-*.md, identifies ADRs subject to the §Operational Guide
contract (maintainer-tier accepted capability ADRs), and reports
compliance + prioritized backfill list.

Contract reference: ADR-274 §1-2.

Usage:
  python3 scripts/cos-operational-guide-audit.py             # JSON to stdout
  python3 scripts/cos-operational-guide-audit.py --write     # write reports
  python3 scripts/cos-operational-guide-audit.py --strict    # exit 2 if any missing P0/P1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ADR_GLOB = "docs/02-Decisions/adrs/ADR-*.md"
REPORT_JSON = "docs/06-Daily/reports/operational-guide-audit-latest.json"
REPORT_MD = "docs/06-Daily/reports/operational-guide-audit-latest.md"

# Section header detection (allow Operational Guide variants)
OPERATIONAL_GUIDE_RE = re.compile(r"^##\s*Operational\s+Guide\b", re.IGNORECASE | re.MULTILINE)
# Minimum sub-section detection (any 3 of these counts as compliant)
SUBSECTIONS_RE = re.compile(
    r"^###\s+("
    r"What changes for the operator"
    r"|What (?:this|the .+) answer"
    r"|Daily operational pattern"
    r"|When (?:sources|surface) disagree"
    r"|Reading guide for cold readers"
    r"|Anti-confusion"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
TIER_RE = re.compile(r"^tier:\s*([\w-]+)", re.IGNORECASE | re.MULTILINE)
STATUS_RE = re.compile(r"^(?:status|\*\*Status\*\*):\s*([\w-]+)", re.IGNORECASE | re.MULTILINE)
DATE_RE = re.compile(r"^date:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
IMPL_FILES_BLOCK = re.compile(r"^implementation_files:\s*\n((?:\s+-\s+.+\n)+)", re.MULTILINE)
EXEMPT_RE = re.compile(r"<!--\s*adr-274-exempt:\s*(.+?)\s*-->", re.IGNORECASE)


def _resolve_project_dir(arg: str | None) -> Path:
    if arg:
        return Path(arg).resolve()
    for env_var in ("COGNITIVE_OS_PROJECT_DIR", "CODEX_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        if env_var in os.environ:
            return Path(os.environ[env_var]).resolve()
    return Path.cwd().resolve()


def _parse_iso_date(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def classify_adr(path: Path, content: str, root: Path | None = None) -> dict[str, Any]:
    """Return a verdict dict per ADR."""
    name = path.stem  # e.g., ADR-273-pending-truth-...
    adr_num_m = re.match(r"ADR-(\d+)", name)
    adr_num = int(adr_num_m.group(1)) if adr_num_m else None

    tier_m = TIER_RE.search(content[:2000])
    tier = tier_m.group(1).lower() if tier_m else None
    status_m = STATUS_RE.search(content[:2000])
    status = status_m.group(1).lower() if status_m else None
    date_m = DATE_RE.search(content[:2000])
    date_iso = date_m.group(1) if date_m else None
    impl_block_m = IMPL_FILES_BLOCK.search(content[:3000])
    impl_count = 0
    if impl_block_m:
        impl_count = len([ln for ln in impl_block_m.group(1).splitlines() if ln.strip().startswith("-")])
    exempt_m = EXEMPT_RE.search(content)
    has_og = OPERATIONAL_GUIDE_RE.search(content) is not None
    subsections = SUBSECTIONS_RE.findall(content)

    # Determine if ADR is subject to the contract (ADR-274 §1)
    is_tombstone = "tombstone" in name.lower() or status == "tombstone"
    is_superseded = status == "superseded"
    is_maintainer = tier == "maintainer"
    is_accepted = status in {"accepted", "implemented"}
    has_capability = impl_count > 0

    subject_to_contract = (
        is_maintainer
        and is_accepted
        and has_capability
        and not is_tombstone
        and not is_superseded
    )

    if exempt_m:
        verdict = "exempt"
    elif not subject_to_contract:
        verdict = "not-applicable"
    elif has_og and len(subsections) >= 3:
        verdict = "compliant"
    elif has_og:
        verdict = "partial"  # section exists but lacks 3+ subsections
    else:
        verdict = "missing"

    # Priority for backfill
    age_days: int | None = None
    parsed_date = _parse_iso_date(date_iso) if date_iso else None
    if parsed_date:
        age_days = (datetime.now(timezone.utc) - parsed_date).days
    priority = None
    if verdict in {"missing", "partial"}:
        if age_days is not None and age_days <= 30:
            priority = "P0"
        elif is_maintainer and is_accepted:
            priority = "P1"
        else:
            priority = "P2"

    if root is not None:
        try:
            rel_path = path.relative_to(root).as_posix()
        except ValueError:
            rel_path = path.name
    else:
        rel_path = path.name

    return {
        "adr": name,
        "adr_num": adr_num,
        "path": rel_path,
        "tier": tier,
        "status": status,
        "date": date_iso,
        "age_days": age_days,
        "implementation_files_count": impl_count,
        "has_operational_guide": has_og,
        "subsection_count": len(subsections),
        "exemption_reason": exempt_m.group(1) if exempt_m else None,
        "subject_to_contract": subject_to_contract,
        "verdict": verdict,
        "priority": priority,
    }


def audit(root: Path) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for path in sorted(root.glob(ADR_GLOB)):
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        results.append(classify_adr(path, content, root=root))

    by_verdict: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for r in results:
        by_verdict[r["verdict"]] = by_verdict.get(r["verdict"], 0) + 1
        if r["priority"]:
            by_priority[r["priority"]] = by_priority.get(r["priority"], 0) + 1

    # Emit findings[] in the control-plane-audit runner shape (ADR-248).
    # Each missing/partial item becomes a "warn" finding; consumers can
    # promote to block via --strict.
    findings: list[dict[str, Any]] = []
    for r in results:
        if r["verdict"] in {"missing", "partial"}:
            findings.append({
                "severity": "warn",
                "code": "operational-guide-" + r["verdict"],
                "message": f"{r['adr']}: §Operational Guide {r['verdict']} ({r['subsection_count']}/3 sub-sections)",
                "details": {
                    "adr": r["adr"],
                    "path": r["path"],
                    "priority": r["priority"],
                    "tier": r["tier"],
                    "status": r["status"],
                    "age_days": r["age_days"],
                },
                "stable_id": f"adr-274/{r['adr']}",
                "adr": "ADR-274",
            })

    return {
        "schema_version": "operational-guide-audit/v1",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contract_ref": "ADR-274",
        "summary": {
            "total_adrs": len(results),
            "by_verdict": by_verdict,
            "by_priority": by_priority,
        },
        "findings": findings,
        "results": results,
    }


def render_md(payload: dict[str, Any]) -> str:
    lines = [
        f"# Operational Guide Audit — {payload['generated_at']}",
        "",
        f"> Per ADR-274. Schema: `{payload['schema_version']}`.",
        "> Audits all `docs/02-Decisions/adrs/ADR-*.md` for §Operational Guide section presence",
        "> on maintainer-tier accepted capability ADRs.",
        "",
        "## How to read this doc (operational guide for this audit)",
        "",
        "This audit answers: **which ADRs are missing operator-readable context?**",
        "",
        "Verdict taxonomy:",
        "- `compliant` — has §Operational Guide with ≥3 documented sub-sections",
        "- `partial` — has §Operational Guide but < 3 sub-sections (needs expansion)",
        "- `missing` — subject to contract but no §Operational Guide present (needs backfill)",
        "- `exempt` — explicitly marked `<!-- adr-274-exempt: <reason> -->`",
        "- `not-applicable` — tombstone, superseded, or non-maintainer/non-capability",
        "",
        "Priority for backfill (only applies to `missing`/`partial`):",
        "- **P0** — accepted ≤ 30 days ago",
        "- **P1** — maintainer-tier accepted (older)",
        "- **P2** — everything else",
        "",
        "Per ADR-274: rules without enforcement are honored ~50% historically;",
        "this audit + `adr-section-validator.sh` extension close the loop.",
        "",
        f"**Total ADRs scanned**: {payload['summary']['total_adrs']}",
        "",
        "## By verdict",
        "",
        "| Verdict | Count |",
        "|---|---:|",
    ]
    for k in sorted(payload["summary"]["by_verdict"]):
        lines.append(f"| {k} | {payload['summary']['by_verdict'][k]} |")
    lines.append("")
    lines.append("## By priority (backfill queue)")
    lines.append("")
    if payload["summary"]["by_priority"]:
        lines.append("| Priority | Count |")
        lines.append("|---|---:|")
        for k in sorted(payload["summary"]["by_priority"]):
            lines.append(f"| {k} | {payload['summary']['by_priority'][k]} |")
    else:
        lines.append("_no backfill required — all subject ADRs compliant or exempt_")
    lines.append("")
    # P0 + P1 backfill table
    backfill = [r for r in payload["results"] if r["priority"] in ("P0", "P1")]
    backfill.sort(key=lambda r: (r["priority"], r["age_days"] or 9999))
    if backfill:
        lines.append("## Backfill list (P0 + P1)")
        lines.append("")
        lines.append("| Priority | ADR | Verdict | Age (days) | Path |")
        lines.append("|---|---|---|---:|---|")
        for r in backfill[:50]:
            lines.append(f"| {r['priority']} | `{r['adr']}` | {r['verdict']} | {r['age_days'] if r['age_days'] is not None else '?'} | `{r['path']}` |")
        if len(backfill) > 50:
            lines.append(f"| _and {len(backfill) - 50} more not shown_ | | | | |")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADR-274 operational-guide audit")
    parser.add_argument("--project-dir", default=None)
    parser.add_argument("--write", action="store_true", help="Write JSON + MD reports")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary to stdout")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 if any P0/P1 backfill items present (CI gate use)",
    )
    args = parser.parse_args(argv)

    root = _resolve_project_dir(args.project_dir)
    if not root.exists():
        print(f"Error: project dir does not exist: {root}", file=sys.stderr)
        return 2

    payload = audit(root)

    if args.write:
        json_path = root / REPORT_JSON
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        md_path = root / REPORT_MD
        md_path.write_text(render_md(payload), encoding="utf-8")
        print(f"wrote {REPORT_JSON}", file=sys.stderr)
        print(f"wrote {REPORT_MD}", file=sys.stderr)

    if args.json or not args.write:
        # Full payload to stdout so the control-plane-audit runner (ADR-248)
        # can read findings[]. Includes schema_version, summary, findings,
        # and per-ADR results.
        print(json.dumps(payload, indent=2, ensure_ascii=False))

    if args.strict:
        p0_p1 = payload["summary"]["by_priority"].get("P0", 0) + payload["summary"]["by_priority"].get("P1", 0)
        if p0_p1 > 0:
            print(f"STRICT: {p0_p1} P0/P1 backfill items present", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
