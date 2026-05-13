#!/usr/bin/env python3
# SCOPE: both
"""Audit ADR tier claims for evidence-backed profile purity.

ADR-132/ADR-133 discipline: an ADR claiming `tier: core` or `tier: team`
must include a `## Evidence` section with a `cos-boring-reliability` proof.
This keeps adoption profiles from becoming aspirational marketing labels.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADR_DIR = REPO_ROOT / "docs" / "02-Decisions" / "adrs"
PROMOTED_TIERS = {"core", "team"}
TIER_RE = re.compile(r"^tier:\s*([A-Za-z0-9_.-]+)\s*$", re.MULTILINE)
HEADING_RE = re.compile(r"^(#{2,6})\s+Evidence\s*$", re.IGNORECASE | re.MULTILINE)
NEXT_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)


@dataclass(frozen=True)
class Finding:
    path: str
    tier: str
    message: str


def _frontmatter_bounds(text: str) -> tuple[int, int] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    return 0, end + len("\n---")


def parse_tier(text: str) -> str | None:
    """Return ADR tier from YAML frontmatter or legacy top-level metadata."""
    bounds = _frontmatter_bounds(text)
    if bounds is not None:
        start, end = bounds
        match = TIER_RE.search(text[start:end])
        if match:
            return match.group(1).strip().lower()
    # Legacy ADRs may carry metadata lines outside YAML frontmatter.
    match = TIER_RE.search(text[:3000])
    if match:
        return match.group(1).strip().lower()
    return None


def evidence_section(text: str) -> str:
    match = HEADING_RE.search(text)
    if not match:
        return ""
    start = match.end()
    next_match = NEXT_HEADING_RE.search(text, start)
    end = next_match.start() if next_match else len(text)
    return text[start:end]


def has_boring_reliability_evidence(text: str) -> bool:
    section = evidence_section(text)
    if not section.strip():
        return False
    return "cos-boring-reliability" in section


def evaluate_file(path: Path, repo_root: Path = REPO_ROOT) -> Finding | None:
    text = path.read_text(encoding="utf-8")
    tier = parse_tier(text)
    if tier not in PROMOTED_TIERS:
        return None
    if has_boring_reliability_evidence(text):
        return None
    try:
        rel = path.relative_to(repo_root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return Finding(
        path=rel,
        tier=tier or "",
        message=(
            "ADR claims tier core/team but lacks a ## Evidence section with "
            "cos-boring-reliability output or command"
        ),
    )


def iter_adr_files(adr_dir: Path) -> Iterable[Path]:
    return sorted(path for path in adr_dir.glob("ADR-*.md") if path.is_file())


def build_report(adr_dir: Path = DEFAULT_ADR_DIR, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    files = list(iter_adr_files(adr_dir))
    findings = [finding for path in files if (finding := evaluate_file(path, repo_root))]
    promoted_count = 0
    tiers: dict[str, int] = {}
    for path in files:
        tier = parse_tier(path.read_text(encoding="utf-8"))
        if not tier:
            continue
        tiers[tier] = tiers.get(tier, 0) + 1
        if tier in PROMOTED_TIERS:
            promoted_count += 1
    return {
        "status": "pass" if not findings else "fail",
        "adr_dir": str(adr_dir),
        "adr_count": len(files),
        "promoted_tier_count": promoted_count,
        "tiers": tiers,
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "policy": "ADR tier core/team requires ## Evidence referencing cos-boring-reliability",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adr-dir", type=Path, default=DEFAULT_ADR_DIR)
    parser.add_argument("--project-dir", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.adr_dir.resolve(), args.project_dir.resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"tier-claim-audit: {report['status']}")
        for finding in report["findings"]:
            print(f"- {finding['path']} ({finding['tier']}): {finding['message']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
