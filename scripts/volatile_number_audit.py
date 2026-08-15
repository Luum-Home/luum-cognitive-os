#!/usr/bin/env python3
"""Detect volatile primitive counts hardcoded in documentation prose.

A number is VOLATILE when it would become wrong without anyone editing the
document that carries it: censuses of hooks, skills, rules, ADRs, primitives,
gates, tests, lib modules. Those belong in a census command or in
manifests/documentation-truth-claims.yaml, not in prose.

A number STAYS when it is part of the historical record or of a contract:
  - dated observations  ("on 2026-05-10 settings.json had 30 hooks")
  - frozen decisions    ("ADR-267 froze 5 globs")
  - thresholds/limits   ("max 3 retries", "top 5 rules")

Read-only. Deterministic. Never writes outside --update-baseline.

Exit codes:
  0  no unbaselined volatile numbers
  1  volatile numbers found that are not in the baseline
  2  execution error (bad args, unreadable baseline, ...)

Usage:
  scripts/volatile_number_audit.py                     # audit against baseline
  scripts/volatile_number_audit.py --format json
  scripts/volatile_number_audit.py --classify-only     # full classification, exit 0
  scripts/volatile_number_audit.py --tier 1            # only highest-damage paths
  scripts/volatile_number_audit.py --update-baseline   # re-freeze accepted debt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = REPO / "manifests" / "volatile-number-baseline.json"

# Nouns whose counts are produced by a census and therefore drift on their own.
CENSUS_NOUNS = (
    r"primitives?|hooks?|skills?|rules?|ADRs?|gates?|instruments?|"
    r"tests?|lib modules?|library modules?|claims?|harnesses|harness|"
    r"agents?|scripts?|checks?"
)
NUMBER_RE = re.compile(
    rf"(?<![\w.\-§#])(?P<num>\d{{1,5}})\+?\s+(?P<noun>{CENSUS_NOUNS})\b",
    re.IGNORECASE,
)

# Counts about OTHER projects. Real numbers, but no census of ours produces them,
# so "reference the census" is not an available fix — they are a separate finding.
EXTERNAL_MARKERS = re.compile(
    r"\b(aguara|hermes|semgrep|p/ai-best-practices|spec-kit|agent ?zero|cursor|"
    r"pi coding agent|kiro|copilot|devin|openhands|aider|cline|roo|windsurf|"
    r"competitor|vs\.? alternatives|nous research)\b",
    re.IGNORECASE,
)
EXTERNAL_PATHS = (
    "docs/08-References/root/competitive-",
    "docs/08-References/root/vs-alternatives",
    "docs/08-References/root/patterns-adopted",
    "rules/aguara-integration.md",
)
# A number inside quotes is being shown as sample wording or quoted from another
# document, not asserted as the current state.
QUOTED_RE = re.compile(r"[\"“”`']")

# Documents that record a delivery which already happened.
RECORD_DOC_RE = re.compile(
    r"(case-stud(y|ies)|post-?mortem|retrospective|external-review|"
    r"status-report|session-\d)",
    re.IGNORECASE,
)

# --- ADR decided-vs-observed boundary ---------------------------------------------
# In an ADR the question is whether the document DECIDES the number or OBSERVES it.
# Decided numbers are the contract the ADR fixes; deleting them destroys the ADR.
ADR_PATH = "docs/02-Decisions/adrs/"
ADR_DECISION_RE = re.compile(
    r"\b(decision|we (?:chose|choose|set|fix|freeze|froze|cap|allow|require)|"
    r"decidimos|se (?:elig|fij|congel)[a-zó]*|"
    r"froze|frozen|fixed at|set to|capped at|must (?:be|have|not)|"
    r"contract|invariant|mandat(?:e|ory)|enforced|required|exactly|"
    r"consequences?|alternatives considered)\b",
    re.IGNORECASE,
)
# Observation of the state of the world at authoring time — expires the next day.
ADR_OBSERVATION_RE = re.compile(
    r"\b(there are|currently|today|the repo (?:has|contains)|"
    r"registered|canonical|inventory|census|total of|counted|"
    r"as it stands|at present|existing|reclassif|surface(?: area)?)\b",
    re.IGNORECASE,
)

# --- historical / contract signals -------------------------------------------------
DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
FILENAME_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

HISTORICAL_WORDS = re.compile(
    r"\b(froze|frozen|congel[oó]|migrated|migr[oó]|was|were|had|used to|"
    r"originally|previously|formerly|at the time|as of|before the|after the|"
    r"pre-|post-mortem|en su momento|ten[ií]a|hab[ií]a|qued[oó]|"
    r"baseline (?:was|of)|snapshot|hist[oó]ric)\b",
    re.IGNORECASE,
)
CONTRACT_WORDS = re.compile(
    r"\b(max|maximum|min|minimum|at most|at least|up to|limit|limited to|"
    r"more than|fewer than|less than|no more than|never load|keep .* bounded|"
    r"threshold|budget|cap|quota|per (?:minute|hour|turn|session|agent)|"
    r"top|first|only the|exactly|exit \d)\b",
    re.IGNORECASE,
)
# "Phase 1 rules", "Section 2 hooks", "v3 skills" — the digit is an ordinal that
# belongs to the preceding word, not a count of the noun that follows.
ORDINAL_PREFIX_RE = re.compile(
    r"\b(phase|section|tier|level|stage|step|slice|wave|part|chapter|round|"
    r"appendix|figure|table|v|version)\s*$",
    re.IGNORECASE,
)
# Past-participle migration verbs: the count describes work already done.
DONE_VERBS = re.compile(
    r"\b(renamed|deleted|removed|added|converted|shipped|drafted|landed|"
    r"created|implemented|consolidated|trimmed|replaced|merged|split|"
    r"renombrad|eliminad|agregad|convertid)\w*\b",
    re.IGNORECASE,
)
# Present-tense state claims — the strongest volatility signal.
LIVE_WORDS = re.compile(
    r"\b(has|have|ships?|includes?|includes|contains?|loads?|runs?|syncs?|"
    r"currently|today|now|total|across|wraps?|adds?|provides?|there are|"
    r"consta de|actualmente|hoy|tiene|incluye)\b",
    re.IGNORECASE,
)

# Paths that are a dated logbook by construction: numbers there document a
# measurement of that day and are correct forever.
LOGBOOK_PREFIXES = (
    "docs/06-Daily/",
    "docs/01-Build-Log/",
    "docs/99-Archive/",
)

# Damage tiers. Tier 1 is read every session or by every newcomer.
TIER1 = (
    "README.md",
    "rules/",
    "docs/00-MOCs/",
    "docs/08-References/",
    "CLAUDE.md",
)
TIER2 = (
    "docs/02-Decisions/adrs/",
    "docs/04-Concepts/",
    "docs/07-Capabilities/",
    "docs/09-Quality/",
)

SCAN_ROOTS = ("docs", "rules", "README.md", "CLAUDE.md")
SCAN_SUFFIXES = {".md"}


@dataclass
class Finding:
    path: str
    line: int
    tier: int
    verdict: str  # volatile | historical | contract
    reason: str
    number: str
    noun: str
    snippet: str

    @property
    def key(self) -> str:
        """Line-number-independent identity, so edits elsewhere do not churn."""
        norm = re.sub(r"\s+", " ", self.snippet).strip().lower()
        digest = hashlib.sha256(f"{self.path}|{norm}".encode()).hexdigest()[:16]
        return f"{self.path}#{digest}"


def tier_of(path: str) -> int:
    if any(path == p or path.startswith(p) for p in TIER1):
        return 1
    if any(path.startswith(p) for p in TIER2):
        return 2
    return 3


def in_logbook(path: str) -> bool:
    return any(path.startswith(p) for p in LOGBOOK_PREFIXES)


def classify(path: str, line_no: int, line: str, m: re.Match, in_code: bool) -> tuple[str, str]:
    """Return (verdict, reason). Order matters: keep signals decidable and auditable."""
    fname = Path(path).name

    if in_code:
        return "contract", "inside fenced code block (command/output, not prose)"

    if m.group("num") == "0":
        return "contract", "zero is a comparison cell, not a census"

    # "Phase 1 rules" — the digit is an ordinal of the preceding word.
    if ORDINAL_PREFIX_RE.search(line[:m.start()]):
        return "contract", "ordinal of the preceding word, not a count"

    # A trailing "+" marks a bound ("50+ agents causes exhaustion"), not a census.
    if line[m.end("num"):m.end("num") + 1] == "+":
        return "contract", "trailing '+' marks a bound, not an exact count"

    if DONE_VERBS.search(line):
        return "historical", "count describes work already completed"

    # A dated filename makes the whole document a measurement of that date —
    # anywhere in the tree, not only under the logbook directories.
    if FILENAME_DATE_RE.search(fname):
        return "historical", "dated document (filename carries the date)"

    # A case study / post-mortem / retrospective records a delivery that already
    # happened: its counts describe that engagement, not the current repo.
    if RECORD_DOC_RE.search(path):
        return "historical", "record of a past engagement (case study / post-mortem)"
    if in_logbook(path) and DATE_RE.search(line):
        return "historical", "logbook line carries an explicit date anchor"

    # An explicit date next to the claim makes it a fixed observation.
    if DATE_RE.search(line):
        return "historical", "claim is anchored to an explicit date"

    # Counts about third-party projects: no census of ours can replace them.
    if any(path.startswith(p) for p in EXTERNAL_PATHS) or EXTERNAL_MARKERS.search(line):
        return "external", "count describes a third-party project, not this repo"

    # Sample wording or a quotation of another document, not a state assertion.
    if QUOTED_RE.search(line[max(0, m.start() - 40):m.end() + 40]):
        return "illustrative", "number appears inside quoted/sample text"

    # Inside an ADR the boundary is: is the ADR DECIDING this number, or OBSERVING it?
    if path.startswith(ADR_PATH):
        if line.lstrip().startswith("#") and line_no <= 3:
            return "adr-title", "number in an ADR title — renaming breaks links, escalate"
        if ADR_OBSERVATION_RE.search(line) and not ADR_DECISION_RE.search(line):
            return "volatile", "ADR observes system state at authoring time"
        if ADR_DECISION_RE.search(line):
            return "contract", "ADR decides this number (the contract it fixes)"

    # A frozen decision: "ADR-267 froze 5 globs".
    if re.search(r"\bADR-\d+\b", line) and HISTORICAL_WORDS.search(line):
        return "historical", "frozen decision attributed to an ADR"

    if HISTORICAL_WORDS.search(line):
        return "historical", "past-tense / snapshot framing"

    if CONTRACT_WORDS.search(line):
        return "contract", "threshold, limit or enumerated constant"

    reason = "present-tense state claim" if LIVE_WORDS.search(line) else "bare census count in prose"
    return "volatile", reason


def scan_file(path: Path) -> list[Finding]:
    rel = path.relative_to(REPO).as_posix()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out: list[Finding] = []
    in_code = False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        for m in NUMBER_RE.finditer(line):
            verdict, reason = classify(rel, i, line, m, in_code)
            snippet = line.strip()
            if len(snippet) > 200:
                start = max(0, m.start() - 90)
                snippet = "..." + line[start:m.end() + 90].strip() + "..."
            out.append(
                Finding(
                    path=rel,
                    line=i,
                    tier=tier_of(rel),
                    verdict=verdict,
                    reason=reason,
                    number=m.group("num"),
                    noun=m.group("noun").lower(),
                    snippet=snippet,
                )
            )
    return out


def collect(roots: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for root in roots:
        p = REPO / root
        if p.is_file():
            findings.extend(scan_file(p))
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix in SCAN_SUFFIXES:
                    findings.extend(scan_file(f))
    return findings


def load_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("accepted", []))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    ap.add_argument("--update-baseline", action="store_true",
                    help="freeze the CURRENT volatile set as accepted debt (only writes the baseline)")
    ap.add_argument("--classify-only", action="store_true",
                    help="report the full classification and always exit 0")
    ap.add_argument("--tier", type=int, choices=(1, 2, 3), default=None,
                    help="restrict to findings at this damage tier or better")
    ap.add_argument("--write-report", action="store_true",
                    help="write docs/06-Daily/reports/volatile-numbers-latest.{json,md}")
    ap.add_argument("--roots", nargs="*", default=list(SCAN_ROOTS))
    args = ap.parse_args()

    try:
        findings = collect(args.roots)
        baseline_path = Path(args.baseline)
        if not baseline_path.is_absolute():
            baseline_path = REPO / baseline_path
        baseline = set() if args.update_baseline else load_baseline(baseline_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.tier:
        findings = [f for f in findings if f.tier <= args.tier]

    volatile = [f for f in findings if f.verdict == "volatile"]
    new = [f for f in volatile if f.key not in baseline]

    if args.update_baseline:
        payload = {
            "schema_version": "volatile-number-baseline.v1",
            "generated_by": "scripts/volatile_number_audit.py --update-baseline",
            "note": "Accepted volatile-number debt. The ratchet only allows this to shrink. "
                    "Never raise it to silence a red: fix the prose or declare a claim in "
                    "manifests/documentation-truth-claims.yaml.",
            "count": len(volatile),
            "accepted": sorted(f.key for f in volatile),
        }
        baseline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"baseline written: {len(volatile)} accepted entries -> {baseline_path.relative_to(REPO)}")
        return 0

    counts = {v: sum(1 for f in findings if f.verdict == v) for v in ("volatile", "historical", "contract", "external", "illustrative", "adr-title")}

    if args.write_report:
        rep = REPO / "docs" / "06-Daily" / "reports"
        by_tier = {t: sum(1 for f in findings if f.verdict == "volatile" and f.tier == t) for t in (1, 2, 3)}
        (rep / "volatile-numbers-latest.json").write_text(json.dumps({
            "schema_version": "volatile-numbers.v1",
            "generated_by": "scripts/volatile_number_audit.py --write-report",
            "totals": {"findings": len(findings), "files": len({f.path for f in findings}), **counts},
            "volatile_by_tier": by_tier,
            "baselined": len(baseline),
            "new_volatile": len(new),
            "volatile": [asdict(f) | {"key": f.key} for f in sorted(
                (x for x in findings if x.verdict == "volatile"), key=lambda x: (x.tier, x.path, x.line))],
        }, indent=2) + "\n", encoding="utf-8")
        lines = [
            "# Volatile numbers in documentation prose (latest)",
            "",
            "Generated by `scripts/volatile_number_audit.py --write-report`. Do not edit by hand.",
            "",
            f"- findings: {len(findings)} across {len({f.path for f in findings})} files",
            f"- volatile: {counts['volatile']} (tier1={by_tier[1]}, tier2={by_tier[2]}, tier3={by_tier[3]})",
            f"- historical: {counts['historical']}  contract: {counts['contract']}",
            f"- external: {counts['external']}  illustrative: {counts['illustrative']}",
            f"- baselined: {len(baseline)}  new: {len(new)}",
            "",
            "## Tier-1 volatile (highest damage)",
            "",
            "| file | line | number | noun |",
            "| --- | --- | --- | --- |",
        ]
        for f in sorted((x for x in findings if x.verdict == "volatile" and x.tier == 1),
                        key=lambda x: (x.path, x.line)):
            lines.append(f"| `{f.path}` | {f.line} | {f.number} | {f.noun} |")
        (rep / "volatile-numbers-latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"report written: docs/06-Daily/reports/volatile-numbers-latest.{{json,md}}")
    stale = sorted(baseline - {f.key for f in volatile})

    if args.format == "json":
        print(json.dumps({
            "totals": {"findings": len(findings), "files": len({f.path for f in findings}), **counts},
            "baselined": len(baseline),
            "new_volatile": [asdict(f) for f in new],
            "stale_baseline_entries": stale,
            "findings": [asdict(f) | {"key": f.key} for f in findings],
        }, indent=2))
    else:
        print(f"scanned roots: {' '.join(args.roots)}")
        print(f"files with numeric census claims: {len({f.path for f in findings})}")
        print(f"findings: {len(findings)}  volatile={counts['volatile']} "
              f"historical={counts['historical']} contract={counts['contract']} "
              f"external={counts['external']} illustrative={counts['illustrative']}")
        print(f"baselined: {len(baseline)}   new (unbaselined) volatile: {len(new)}")
        if stale:
            print(f"\nstale baseline entries ({len(stale)}) — fixed upstream, run --update-baseline to shrink:")
            for k in stale[:20]:
                print(f"  {k}")
        if new:
            print("\nNEW volatile numbers (fix the prose or declare a claim):")
            for f in sorted(new, key=lambda x: (x.tier, x.path, x.line)):
                print(f"  [T{f.tier}] {f.path}:{f.line}  {f.number} {f.noun}  ({f.reason})")
                print(f"        {f.snippet[:160]}")
        if args.classify_only:
            print("\nper-tier volatile breakdown:")
            for t in (1, 2, 3):
                n = sum(1 for f in volatile if f.tier == t)
                print(f"  tier {t}: {n}")

    if args.classify_only:
        return 0
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
