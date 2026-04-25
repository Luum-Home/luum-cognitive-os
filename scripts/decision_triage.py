#!/usr/bin/env python3
"""decision_triage.py — Aggregate unanswered operator decisions from research reports
and ADRs into a unified, ranked view.

READ-ONLY against source files (docs/reports/*.md, docs/adrs/ADR-*.md,
.cognitive-os/reports/research/*.md). Never deletes or modifies those files.

Usage:
    python3 scripts/decision_triage.py
    python3 scripts/decision_triage.py --since 2026-04-01
    python3 scripts/decision_triage.py --only-research
    python3 scripts/decision_triage.py --only-adrs
    python3 scripts/decision_triage.py --output path/to/decisions.md
    python3 scripts/decision_triage.py --critical-only
    python3 scripts/decision_triage.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "docs" / "reports"
RESEARCH_REPORTS_DIR = REPO_ROOT / ".cognitive-os" / "reports" / "research"
ADRS_DIR = REPO_ROOT / "docs" / "adrs"

# Section headers we scan for decisions (case-insensitive)
REPORT_SECTION_PATTERNS = [
    re.compile(r"^##\s+open\s+questions?\s*(?:for\s+operator)?$", re.IGNORECASE),
    re.compile(r"^##\s+decision\s+points?(?:\s*\(operator\s+answers?\s+needed\))?$", re.IGNORECASE),
    re.compile(r"^##\s+operator\s+decisions?\s+pending$", re.IGNORECASE),
    re.compile(r"^##\s+decisions?\s+for\s+operator$", re.IGNORECASE),
]

ADR_SECTION_PATTERN = re.compile(r"^##\s+open\s+questions?$", re.IGNORECASE)

# Urgency keyword patterns
CRITICAL_PATTERNS = re.compile(
    r"\b(blocker|critical|must decide|decision needed before|blocks|required before)\b",
    re.IGNORECASE,
)
SOFT_PATTERNS = re.compile(
    r"\b(future|post-1\.0|next session|eventually|someday|later|whenever|optional)\b",
    re.IGNORECASE,
)

RECENT_DAYS = 7   # Files modified within this many days are "recent"
OLD_ADR_DAYS = 30  # ADR questions older than this are downgraded to soft


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Decision:
    source_path: str          # relative to repo root
    source_type: str          # "report" or "adr"
    section: str              # section header where found
    text: str                 # decision text (stripped)
    index: int                # position within section (1-based)
    urgency: str = "important"  # "critical" | "important" | "soft"
    status: str = "PENDING"   # "PENDING" | "ANSWERED" | "PENDING (engram unavailable)"
    engram_ref: Optional[str] = None
    file_mtime: Optional[float] = None  # for recency ranking

    def short_id(self) -> str:
        fname = Path(self.source_path).stem
        return f"{fname} §{self.section} #{self.index}"


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _file_mtime(path: Path) -> Optional[float]:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _is_recent(mtime: Optional[float], days: int = RECENT_DAYS) -> bool:
    if mtime is None:
        return False
    age_days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400
    return age_days <= days


def _classify_urgency(text: str, source_type: str, mtime: Optional[float]) -> str:
    """Apply simple heuristic to classify urgency tier."""
    if CRITICAL_PATTERNS.search(text):
        return "critical"
    if SOFT_PATTERNS.search(text):
        return "soft"
    # Recent research reports default to important
    if source_type == "report" and _is_recent(mtime):
        return "important"
    # Old ADR questions default to soft
    if source_type == "adr" and mtime is not None:
        age_days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400
        if age_days > OLD_ADR_DAYS:
            return "soft"
    return "important"


def _parse_section_items(lines: list[str], section_name: str) -> list[str]:
    """Extract decision items from section body lines.

    Handles:
    - Numbered items: ``1. text``
    - Bullet items: ``- text`` or ``* text``
    - Markdown table rows (non-header, non-separator): ``| 1 | ... | ... |``
    """
    items: list[str] = []
    in_table = False
    header_seen = False

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # Detect table rows
        if line.startswith("|"):
            cols = [c.strip() for c in line.strip("|").split("|")]
            # Skip separator rows like |---|---|
            if all(re.match(r"^[-: ]+$", c) for c in cols if c):
                in_table = True
                header_seen = True
                continue
            if not header_seen:
                # First row = header
                header_seen = True
                in_table = True
                continue
            # Data row — join all columns (skip pure numeric index col if present)
            non_empty = [c for c in cols if c]
            if non_empty:
                # Use column 2 onward for decision text (skip numeric index)
                if len(non_empty) >= 2 and re.match(r"^\d+$", non_empty[0]):
                    text = " | ".join(non_empty[1:])
                else:
                    text = " | ".join(non_empty)
                items.append(text)
            continue

        in_table = False
        header_seen = False

        # Numbered item
        m = re.match(r"^\d+\.\s+(.+)$", line)
        if m:
            items.append(m.group(1).strip())
            continue

        # Bullet item
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            items.append(m.group(1).strip())
            continue

    return items


def _extract_decisions_from_file(
    path: Path,
    source_type: str,
    section_patterns: list[re.Pattern],
) -> list[Decision]:
    """Read a single markdown file and extract decisions from matching sections."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"WARNING: cannot read {path}: {exc}", file=sys.stderr)
        return []

    mtime = _file_mtime(path)
    try:
        rel_path = str(path.relative_to(REPO_ROOT))
    except ValueError:
        rel_path = str(path)
    decisions: list[Decision] = []

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        matched_section: Optional[str] = None
        for pat in section_patterns:
            if pat.match(line):
                matched_section = line.lstrip("#").strip()
                break

        if matched_section is not None:
            # Collect lines until next ## heading or EOF
            section_lines: list[str] = []
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if re.match(r"^##\s+", next_line):
                    break
                section_lines.append(next_line)
                i += 1

            items = _parse_section_items(section_lines, matched_section)
            for idx, item_text in enumerate(items, start=1):
                urgency = _classify_urgency(item_text, source_type, mtime)
                decisions.append(Decision(
                    source_path=rel_path,
                    source_type=source_type,
                    section=matched_section,
                    text=item_text,
                    index=idx,
                    urgency=urgency,
                    status="PENDING",
                    file_mtime=mtime,
                ))
        else:
            i += 1

    return decisions


def scan_reports(reports_dir: Path, since: Optional[datetime] = None) -> list[Decision]:
    """Scan all research reports in a given directory."""
    decisions: list[Decision] = []
    if not reports_dir.exists():
        return decisions
    for md_file in sorted(reports_dir.glob("*.md")):
        if since is not None:
            mtime = _file_mtime(md_file)
            if mtime is not None and mtime < since.timestamp():
                continue
        decisions.extend(
            _extract_decisions_from_file(md_file, "report", REPORT_SECTION_PATTERNS)
        )
    return decisions


def scan_research_reports(
    reports_dir: Path = REPORTS_DIR,
    research_dir: Path = RESEARCH_REPORTS_DIR,
    since: Optional[datetime] = None,
) -> list[Decision]:
    """Scan all research reports from docs/reports/ AND .cognitive-os/reports/research/.

    This is the canonical entry point used by main(). scan_reports() scans a single dir.
    """
    decisions: list[Decision] = []
    decisions.extend(scan_reports(reports_dir, since=since))
    decisions.extend(scan_reports(research_dir, since=since))
    return decisions


def scan_adrs(adrs_dir: Path, since: Optional[datetime] = None) -> list[Decision]:
    """Scan all ADRs in docs/adrs/."""
    decisions: list[Decision] = []
    if not adrs_dir.exists():
        return decisions
    for md_file in sorted(adrs_dir.glob("ADR-*.md")):
        if since is not None:
            mtime = _file_mtime(md_file)
            if mtime is not None and mtime < since.timestamp():
                continue
        decisions.extend(
            _extract_decisions_from_file(md_file, "adr", [ADR_SECTION_PATTERN])
        )
    return decisions


# ---------------------------------------------------------------------------
# Engram answers (canonical spec interface)
# ---------------------------------------------------------------------------

def scan_engram_answers() -> dict[str, bool]:
    """Try to retrieve answered decisions from engram.

    Returns {topic_slug: True} for decisions that have been answered.
    Returns {} gracefully when engram is unavailable.
    """
    try:
        result = subprocess.run(
            ["engram", "search", "decision/", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                answered: dict[str, bool] = {}
                items = data if isinstance(data, list) else data.get("results", [])
                for item in items:
                    key = item.get("topic_key", "") or item.get("key", "")
                    if key.startswith("decision/"):
                        slug = key[len("decision/"):]
                        answered[slug] = True
                return answered
            except (json.JSONDecodeError, AttributeError):
                return {}
        return {}
    except Exception as exc:
        print(f"WARNING: engram unavailable for cross-reference: {exc}", file=sys.stderr)
        return {}


def filter_unanswered(
    decisions: list[Decision], answered: dict[str, bool]
) -> list[Decision]:
    """Drop decisions whose topic_slug appears in the answered map."""
    if not answered:
        return decisions
    result: list[Decision] = []
    for d in decisions:
        slug = _infer_topic_key(d).removeprefix("decision/")
        if answered.get(slug):
            d.status = "ANSWERED"
        else:
            result.append(d)
    return result


def sort_by_urgency(decisions: list[Decision]) -> list[Decision]:
    """Sort decisions: HIGH → MEDIUM → LOW; newest file first within each tier.

    The urgency field uses two naming conventions internally:
    - "critical" maps to HIGH
    - "important" maps to MEDIUM
    - "soft" maps to LOW
    """
    _order = {"critical": 0, "high": 0, "important": 1, "medium": 1, "soft": 2, "low": 2}

    def _key(d: Decision) -> tuple[int, float]:
        tier = _order.get(d.urgency.lower(), 1)
        recency = -(d.file_mtime or 0.0)  # negative = newest first
        return (tier, recency)

    return sorted(decisions, key=_key)


def write_report(decisions: list[Decision], output_path: Path) -> None:
    """Write the triage report markdown to output_path (creates parent dirs)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    urgency_buckets: dict[str, list[Decision]] = {
        "high": [],
        "medium": [],
        "low": [],
    }
    _map = {"critical": "high", "high": "high", "important": "medium", "medium": "medium", "soft": "low", "low": "low"}
    for d in decisions:
        bucket = _map.get(d.urgency.lower(), "medium")
        urgency_buckets[bucket].append(d)

    lines: list[str] = []
    lines.append(f"# Decision Triage — {today}")
    lines.append("")
    lines.append("> Generated by /decision-triage. Sources: docs/reports/, docs/adrs/, engram (decision/* topics).")
    lines.append("")
    lines.append(f"## Pending decisions: {len(decisions)}")
    lines.append("")

    emoji = {"high": "🔴 HIGH urgency", "medium": "🟡 MEDIUM urgency", "low": "🟢 LOW urgency"}
    for tier in ("high", "medium", "low"):
        tier_decisions = urgency_buckets[tier]
        lines.append(f"### {emoji[tier]} ({len(tier_decisions)})")
        if tier_decisions:
            lines.append("| # | Source | Topic | Question | Date |")
            lines.append("|---|---|---|---|---|")
            for n, d in enumerate(tier_decisions, start=1):
                src = Path(d.source_path).name
                topic = Path(d.source_path).stem
                q_short = d.text[:80] + ("…" if len(d.text) > 80 else "")
                date_str = ""
                if d.file_mtime:
                    date_str = datetime.fromtimestamp(d.file_mtime, tz=timezone.utc).strftime("%Y-%m-%d")
                lines.append(f"| {n} | {src} | {topic} | {q_short} | {date_str} |")
        else:
            lines.append("_No decisions in this tier._")
        lines.append("")

    # Answered count
    lines.append("---")
    lines.append(f"*Generated: {ts}*")
    lines.append("*To answer a decision: save engram observation under `decision/<topic_slug>` with your answer*")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Engram cross-reference (legacy — used by enrich_with_engram)
# ---------------------------------------------------------------------------

def _engram_search(query: str, timeout: int = 5) -> Optional[str]:
    """Attempt an engram search via subprocess. Returns text output or None on failure."""
    try:
        result = subprocess.run(
            ["python3", "-c",
             f"from lib.engram import search; print(search('{query}'))"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=REPO_ROOT,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception:
        return None


def _infer_topic_key(decision: Decision) -> str:
    """Derive a rough engram topic key from the decision text."""
    # Take first 5 words, lowercase, join with dashes
    words = re.findall(r"\w+", decision.text.lower())[:5]
    return "decision/" + "-".join(words)


def enrich_with_engram(decisions: list[Decision]) -> tuple[list[Decision], bool]:
    """Try to cross-reference decisions against engram. Returns (decisions, engram_available)."""
    # Quick availability probe
    probe = _engram_search("decision/probe-test", timeout=3)
    engram_available = probe is not None

    if not engram_available:
        for d in decisions:
            d.status = "PENDING (engram unavailable)"
        return decisions, False

    for d in decisions:
        topic_key = _infer_topic_key(d)
        result = _engram_search(topic_key)
        if result and "answered" in result.lower():
            d.status = "ANSWERED"
            d.engram_ref = topic_key

    return decisions, True


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

URGENCY_EMOJI = {
    "critical": "🔴 Critical (block other work)",
    "important": "🟡 Important (decide this session or next)",
    "soft": "🟢 Soft (whenever)",
}

URGENCY_ORDER = ["critical", "important", "soft"]


def _format_text_report(
    decisions: list[Decision],
    engram_available: bool,
    today: str,
    critical_only: bool = False,
) -> str:
    lines: list[str] = []
    lines.append(f"# Decision Triage — {today}")
    lines.append("")

    visible = [d for d in decisions if d.status != "ANSWERED"]
    if critical_only:
        visible = [d for d in visible if d.urgency == "critical"]

    total = len(visible)
    sources = len({d.source_path for d in visible})
    lines.append(f"Total unanswered: **{total} decisions** across **{sources} sources**.")
    lines.append("")

    # --- By urgency ---
    lines.append("## By urgency")
    lines.append("")

    for urgency in URGENCY_ORDER:
        if critical_only and urgency != "critical":
            continue
        tier = [d for d in visible if d.urgency == urgency]
        if not tier:
            continue
        lines.append(f"### {URGENCY_EMOJI[urgency]}")
        lines.append("")
        lines.append("| # | Source | Decision | Section |")
        lines.append("|---|---|---|---|")
        for n, d in enumerate(tier, start=1):
            src = Path(d.source_path).name
            text_short = d.text[:100] + ("…" if len(d.text) > 100 else "")
            lines.append(f"| {n} | {src} | {text_short} | {d.section} #{d.index} |")
        lines.append("")

    if not any(
        [d for d in visible if d.urgency == u]
        for u in (URGENCY_ORDER if not critical_only else ["critical"])
    ):
        lines.append("_No unanswered decisions found._")
        lines.append("")

    # --- By source ---
    if not critical_only:
        lines.append("## By source")
        lines.append("")
        by_source: dict[str, list[Decision]] = {}
        for d in visible:
            by_source.setdefault(d.source_path, []).append(d)

        for src_path, src_decisions in sorted(by_source.items()):
            lines.append(f"### {src_path}")
            lines.append("")
            for d in src_decisions:
                status_badge = f"→ {d.status}"
                text_short = d.text[:120] + ("…" if len(d.text) > 120 else "")
                lines.append(f"- **Decision {d.index}**: {text_short}  {status_badge}")
            lines.append("")

    # --- Engram status ---
    lines.append("## Engram cross-ref status")
    lines.append("")
    lines.append(f"- Engram available: {'yes' if engram_available else 'no'}")
    answered = sum(1 for d in decisions if d.status == "ANSWERED")
    lines.append(f"- Decisions matched: {answered} / {len(decisions)}")
    lines.append("")

    return "\n".join(lines)


def _format_json(decisions: list[Decision], engram_available: bool, today: str) -> str:
    payload = {
        "date": today,
        "engram_available": engram_available,
        "total": len(decisions),
        "unanswered": sum(1 for d in decisions if d.status != "ANSWERED"),
        "decisions": [asdict(d) for d in decisions],
    }
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate unanswered operator decisions from research reports and ADRs.",
    )
    parser.add_argument(
        "--source",
        choices=["reports", "adrs", "all"],
        default="all",
        help="Which sources to scan (default: all)",
    )
    parser.add_argument(
        "--only-research",
        action="store_true",
        help="Scan only research reports (alias for --source reports)",
    )
    parser.add_argument(
        "--only-adrs",
        action="store_true",
        help="Scan only ADRs (alias for --source adrs)",
    )
    parser.add_argument(
        "--since",
        metavar="DATE",
        default=None,
        help="Only include decisions from files modified on or after DATE (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Write report to this file path (in addition to stdout)",
    )
    parser.add_argument(
        "--critical-only",
        action="store_true",
        help="Show only critical-tier decisions",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output machine-readable JSON",
    )
    args = parser.parse_args(argv)

    # Resolve source filter
    if args.only_research:
        source = "reports"
    elif args.only_adrs:
        source = "adrs"
    else:
        source = args.source

    # Parse --since date
    since_dt: Optional[datetime] = None
    if args.since:
        try:
            since_dt = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"ERROR: --since date must be YYYY-MM-DD, got: {args.since!r}", file=sys.stderr)
            return 1

    decisions: list[Decision] = []

    if source in ("reports", "all"):
        decisions.extend(scan_research_reports(
            reports_dir=REPORTS_DIR,
            research_dir=RESEARCH_REPORTS_DIR,
            since=since_dt,
        ))

    if source in ("adrs", "all"):
        decisions.extend(scan_adrs(ADRS_DIR, since=since_dt))

    # Engram enrichment — must not crash on failure
    try:
        decisions, engram_available = enrich_with_engram(decisions)
    except Exception as exc:
        print(f"WARNING: engram enrichment failed: {exc}", file=sys.stderr)
        for d in decisions:
            d.status = "PENDING (engram unavailable)"
        engram_available = False

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.json_output:
        output = _format_json(decisions, engram_available, today)
    else:
        output = _format_text_report(
            decisions,
            engram_available,
            today,
            critical_only=args.critical_only,
        )

    print(output)

    # Write to --output path if specified
    if args.output:
        out_path = Path(args.output)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
        except OSError as exc:
            print(f"WARNING: could not write output file: {exc}", file=sys.stderr)

    # Optional: write to session dir if env var is set (and no explicit --output)
    if not args.output:
        session_id = os.environ.get("COGNITIVE_OS_SESSION_ID")
        if session_id:
            session_dir = REPO_ROOT / ".cognitive-os" / "sessions" / session_id
            if session_dir.is_dir():
                out_file = session_dir / "decision-triage.md"
                try:
                    out_file.write_text(output, encoding="utf-8")
                except OSError as exc:
                    print(f"WARNING: could not write session output: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
