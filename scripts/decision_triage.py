#!/usr/bin/env python3
# SCOPE: both
"""decision_triage.py — Aggregate unanswered operator decisions from research reports
and ADRs into a unified, ranked view.

READ-ONLY against source files (docs/06-Daily/reports/*.md, docs/02-Decisions/adrs/ADR-*.md,
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
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
REPORTS_DIR = REPO_ROOT / "docs" / "reports"
# NOTE: .cognitive-os/reports/research/ is gitignored — reports now live in docs/06-Daily/reports/.
# We keep this constant for legacy fallback but DO NOT scan it in normal operation.
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
#
# CRITICAL — explicit operator marker OR strong "blocks work" language.
# These FORCE critical regardless of score.
EXPLICIT_CRITICAL = re.compile(
    r"(\*\*priority:\s*critical\*\*|\[critical\]|\[blocker\]|\bMUST\s+decide\b)",
    re.IGNORECASE,
)
HARD_CRITICAL_PATTERNS = re.compile(
    r"\b(blocker|must decide before|blocks\s+(?:implementation|phase|work)|required before|critical to|critical decision)\b",
    re.IGNORECASE,
)
# SOFT — future-tense, low-urgency. FORCES soft regardless of score.
SOFT_PATTERNS = re.compile(
    r"\b(future\s+(?:work|session)|post-1\.0|next session|eventually|someday|nice-to-have|whenever\s+convenient|low priority)\b",
    re.IGNORECASE,
)
# IMPORTANT — language that pushes score up (not forcing).
IMPORTANT_BOOST = re.compile(
    r"\b(biggest\s+(?:gap|issue|risk|ambiguity|scope|stakes)|highest[-\s]stakes|answers?\s+needed|answer\s+pending|implementation\s+depends|phase\s+\d+\s+depends|before\s+(?:phase|implementation|merge|commit)|operator\s+decision)\b",
    re.IGNORECASE,
)
# HEDGE — softens score (not forcing).
HEDGE_BOOST = re.compile(
    r"\b(might|consider(?:ed)?|possibly|could|maybe|perhaps|in\s+the\s+future)\b",
    re.IGNORECASE,
)

RECENT_DAYS = 7    # Files modified within this many days are "recent"
VERY_RECENT_DAYS = 3  # Files modified within this many days score higher
OLD_ADR_DAYS = 30  # ADR questions older than this are downgraded toward soft

# Score thresholds (>= → tier)
CRITICAL_SCORE = 3
IMPORTANT_SCORE = 1


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


def _classify_urgency(text: str, source_type: str, mtime: Optional[float], section_name: str = "") -> str:
    """Score-based heuristic to classify urgency tier.

    Forced overrides (regardless of score):
      - Explicit `**Priority: critical**` / `[CRITICAL]` / `[BLOCKER]` markers → critical
      - Hard "blocks implementation" language → critical
      - "future work" / "next session" / "post-1.0" language → soft

    Otherwise, score signals:
      +2  research report from last 3 days (very fresh — needs decision soon)
      +1  research report from last 7 days
      +1  section is "Decision Points" (more imperative than "Open questions")
      +2  body mentions "biggest", "highest stakes", "answers needed",
          "implementation depends", "phase X depends", "before phase/implementation"
      -1  body uses hedging language ("might", "consider", "possibly")
      -2  ADR older than 30 days (low decay)

    Tiers: score >= 3 critical, >= 1 important, < 1 soft.
    """
    # FORCED overrides
    if EXPLICIT_CRITICAL.search(text) or HARD_CRITICAL_PATTERNS.search(text):
        return "critical"
    if SOFT_PATTERNS.search(text):
        return "soft"

    # Score-based
    score = 0
    if source_type == "report" and _is_recent(mtime, days=VERY_RECENT_DAYS):
        score += 2
    elif source_type == "report" and _is_recent(mtime, days=RECENT_DAYS):
        score += 1
    if "decision" in (section_name or "").lower():
        score += 1
    if IMPORTANT_BOOST.search(text):
        score += 2
    if HEDGE_BOOST.search(text):
        score -= 1
    if source_type == "adr" and mtime is not None:
        age_days = (datetime.now(timezone.utc).timestamp() - mtime) / 86400
        if age_days > OLD_ADR_DAYS:
            score -= 2

    if score >= CRITICAL_SCORE:
        return "critical"
    if score >= IMPORTANT_SCORE:
        return "important"
    return "soft"


def _parse_section_items(lines: list[str], section_name: str) -> list[str]:
    """Extract decision items from section body lines.

    Handles:
    - Numbered items: ``1. text``
    - Bullet items: ``- text`` or ``* text``
    - Markdown table rows (non-header, non-separator): ``| 1 | ... | ... |``
    """
    items: list[str] = []
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
                header_seen = True
                continue
            if not header_seen:
                # First row = header
                header_seen = True
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
                urgency = _classify_urgency(item_text, source_type, mtime, matched_section)
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
    """Scan research reports from docs/06-Daily/reports/ (canonical) and optionally .cognitive-os/reports/research/.

    Canonical path is docs/06-Daily/reports/ (git-tracked). The legacy .cognitive-os path is
    gitignored and should be empty after ADR-069 §5 fix (2026-04-27). We still scan
    it as a fallback to catch stale copies, but docs/06-Daily/reports/ is the source of truth.
    """
    decisions: list[Decision] = []
    decisions.extend(scan_reports(reports_dir, since=since))
    # Deduplicate: if a report exists in both dirs, prefer the docs/06-Daily/reports/ copy.
    tracked_stems = {d.source_path.split("/")[-1] for d in decisions}
    legacy_decisions = scan_reports(research_dir, since=since)
    for d in legacy_decisions:
        if Path(d.source_path).name not in tracked_stems:
            decisions.append(d)
    return decisions


def scan_adrs(adrs_dir: Path, since: Optional[datetime] = None) -> list[Decision]:
    """Scan all ADRs in docs/02-Decisions/adrs/."""
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

def _parse_engram_text_for_slugs(text: str) -> dict[str, bool]:
    """Extract decision slugs from engram CLI text output.

    Supports two patterns:
    1. Legacy (broken saves): `"topic_key": "decision/slug"` embedded in JSON snippets
    2. Correct saves (v1.14.5+): title lines like `— Decision answered: slug`
       or `[decision] — Decision answered: slug`
    """
    answered: dict[str, bool] = {}
    # Pattern 1: JSON snippet with topic_key
    for m in re.finditer(r'"topic_key":\s*"decision/([^"]+)"', text):
        answered[m.group(1)] = True
    # Pattern 2: Title line "Decision answered: <slug>"
    for m in re.finditer(r"Decision answered:\s*([\w][\w.-]+)", text):
        slug = m.group(1).strip()
        if slug:
            answered[slug] = True
    # Pattern 3: Topic line "Topic: decision/<slug>"
    for m in re.finditer(r"Topic:\s*decision/([\w][\w.-]+)", text):
        answered[m.group(1)] = True
    return answered


def _engram_search_for_answers(query: str, timeout: int = 5) -> dict[str, bool]:
    """Run one engram search and extract decision slugs from text output."""
    try:
        result = subprocess.run(
            ["engram", "search", query],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {}
        return _parse_engram_text_for_slugs(result.stdout)
    except Exception:
        return {}


def _probe_engram_available(timeout: int = 3) -> bool:
    """Return whether the Engram CLI is reachable for decision cross-reference.

    This probe is intentionally separate from answer retrieval so callers can
    distinguish "Engram is up but no matching answers exist" from "Engram is
    unavailable". That distinction matters for reports: unavailable memory must
    mark decisions as pending rather than silently treating an empty answer set
    as authoritative.
    """
    try:
        probe = subprocess.run(
            ["engram", "search", "Decision answered probe"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return probe.returncode == 0
    except Exception as exc:
        print(f"WARNING: engram unavailable for cross-reference: {exc}", file=sys.stderr)
        return False


def scan_engram_answers_with_status() -> tuple[dict[str, bool], bool]:
    """Retrieve answered decisions and return `(answers, engram_available)`."""
    if not _probe_engram_available():
        return {}, False

    answered: dict[str, bool] = {}

    # Multiple queries to cover all decision/* entries (engram limits to 10/query).
    # NOTE: engram uses semantic/vector search, not keyword prefix search.
    # Short specific queries return more relevant results than long compound queries.
    queries = [
        "Decision answered hook validation",
        "Decision answered audit placement",
        "Decision answered template location",
        "Decision answered yaml pyyaml",
        "Decision answered cos-init migration backward shim",
        "Decision answered subprocess wrapper tomllib",
        "Decision answered test strategy migration ordering bash",
        "Decision answered wrapt rich cryptography python",
        "Decision answered adr alternatives rejected",
        "Decision answered verification contextual trigger",
        "Decision answered settings driver generate project",
    ]
    for query in queries:
        answered.update(_engram_search_for_answers(query))

    return answered, True


def scan_engram_answers() -> dict[str, bool]:
    """Try to retrieve answered decisions from engram.

    Returns {topic_slug: True} for decisions that have been answered.
    Returns {} gracefully when engram is unavailable.

    Fix 2026-04-27: The engram CLI does NOT support --json flag — it treats it as
    part of the search query. Removed --json; parse text output for title/topic patterns.

    Engram returns at most 10 results per query. We run multiple targeted queries to
    cover all decision/* entries across different topic groups.
    """
    answered, _available = scan_engram_answers_with_status()
    return answered


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
    lines.append("> Generated by /decision-triage. Sources: docs/06-Daily/reports/, docs/02-Decisions/adrs/, engram (decision/* topics).")
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
    """Attempt an engram search via the engram CLI. Returns text output or None on failure.

    Uses the engram CLI subprocess (most stable contract — the Python module path
    has changed historically; the CLI is the stable interface).
    Bug fix 2026-04-27: replaced broken `from lib.engram import search` (module
    doesn't exist) with the CLI invocation already used by scan_engram_answers().
    """
    try:
        result = subprocess.run(
            ["engram", "search", query, "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
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
    """Try to cross-reference decisions against engram. Returns (decisions, engram_available).

    Performance fix 2026-04-27: replaced O(N) per-decision _engram_search() calls with
    bulk queries. Engram is limited to 10 results per semantic query, so we use multiple
    targeted queries then fall back to individual per-slug lookups for critical decisions.
    """
    # Bulk queries first (fast, covers most answers). Keep availability separate
    # from answer count so "Engram up with zero answers" is not confused with
    # "Engram unavailable".
    answered, engram_available = scan_engram_answers_with_status()

    if not engram_available:
        for d in decisions:
            d.status = "PENDING (engram unavailable)"
        return decisions, False

    # Mark decisions found in bulk results
    for d in decisions:
        slug = _infer_topic_key(d).removeprefix("decision/")
        if answered.get(slug):
            d.status = "ANSWERED"
            d.engram_ref = f"decision/{slug}"

    # For CRITICAL decisions NOT yet marked ANSWERED:
    # do targeted per-slug lookup (engram bulk search has 10-result limit).
    # Only critical (not important) to keep total lookup count bounded.
    # Cap at 25 to handle up to 25 critical decisions efficiently.
    unanswered_critical = [
        d for d in decisions
        if d.status != "ANSWERED" and d.urgency == "critical"
    ]
    for d in unanswered_critical[:25]:
        slug = _infer_topic_key(d).removeprefix("decision/")
        result = _engram_search(slug)
        if result and ("answered" in result.lower() or "Decision answered:" in result):
            d.status = "ANSWERED"
            d.engram_ref = f"decision/{slug}"

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
    parser.add_argument(
        "--mark-answered",
        metavar="SLUG",
        default=None,
        help=(
            "Mark a decision slug as ANSWERED in engram. "
            "Slug format: <topic-key> (no 'decision/' prefix). "
            "Optionally combine with --answer-text to provide the decision text."
        ),
    )
    parser.add_argument(
        "--answer-text",
        metavar="TEXT",
        default="Operator accepted",
        help="Decision text when using --mark-answered (default: 'Operator accepted')",
    )
    args = parser.parse_args(argv)

    # Handle --mark-answered as an early-exit sub-command
    if args.mark_answered:
        try:
            from lib.decision_tracker import mark_answered_by_slug  # noqa: PLC0415
        except ImportError as exc:
            print(f"ERROR: cannot import lib.decision_tracker: {exc}", file=sys.stderr)
            return 1
        slug = args.mark_answered
        answer = args.answer_text
        ok = mark_answered_by_slug(slug, answer_text=answer)
        if ok:
            print(f"OK: decision/{slug} marked as ANSWERED in engram.")
        else:
            print(
                f"WARNING: engram save may have failed for decision/{slug}. "
                "Check engram connectivity.",
                file=sys.stderr,
            )
        return 0 if ok else 1

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
