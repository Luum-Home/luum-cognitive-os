# scope: both
"""Requirement-to-test traceability checker.

Discovers requirements from documentation, then checks whether each has a
corresponding spec, code commit, and test.  Produces a TraceabilityReport
with per-requirement links and gap analysis.

Author: luum
Python 3.9+ compatible.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Requirement:
    """A single discovered requirement."""

    id: str        # e.g. "REQ-user-authentication"
    title: str     # e.g. "User Authentication"
    source_file: str  # Relative path to the doc file


@dataclass
class TraceabilityLink:
    """Traceability status for one requirement."""

    requirement: Requirement
    has_spec: bool
    has_code: bool
    has_test: bool
    spec_ref: str
    code_ref: str
    test_ref: str
    status: str  # COMPLETE | PARTIAL | MISSING


@dataclass
class TraceabilityGap:
    """A requirement that is not fully traceable."""

    requirement: Requirement
    missing: List[str]   # subset of ["spec", "code", "test"]
    severity: str        # HIGH (all missing) | MEDIUM (some missing)


@dataclass
class TraceabilityReport:
    """Full traceability analysis across all discovered requirements."""

    links: List[TraceabilityLink]
    gaps: List[TraceabilityGap]
    coverage_pct: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Convert a heading title to a kebab-case slug."""
    return _SLUG_RE.sub("-", text.lower()).strip("-")


def _grep_files(pattern: str, paths: List[Path], case_insensitive: bool = True) -> Tuple[bool, str]:
    """Search for *pattern* in a list of files using Python's re module.

    Returns (found, first_match_reference).
    """
    flags = re.IGNORECASE if case_insensitive else 0
    compiled = re.compile(pattern, flags)
    for p in paths:
        try:
            text = p.read_text(errors="replace")
            m = compiled.search(text)
            if m:
                return True, str(p)
        except Exception:
            pass
    return False, ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def discover_requirements(project_dir: str) -> List[Requirement]:
    """Discover requirements from documentation files.

    Scans:
    - ``docs/05-features/*.md``
    - ``docs/01-context/*.md``

    Extracts:
    - Lines starting with ``## `` or ``### `` as feature headings
    - Lines matching ``- [ ]`` or ``- [x]`` as checklist items

    Args:
        project_dir: Root of the project.

    Returns:
        List of Requirement objects, deduplicated by ID.
    """
    root = Path(project_dir)
    doc_dirs = [
        root / "docs" / "05-features",
        root / "docs" / "01-context",
    ]

    seen_ids: set = set()
    requirements: List[Requirement] = []

    for doc_dir in doc_dirs:
        if not doc_dir.is_dir():
            continue
        for md_file in sorted(doc_dir.glob("*.md")):
            rel_path = str(md_file.relative_to(root))
            try:
                lines = md_file.read_text(errors="replace").splitlines()
            except Exception:
                continue
            for line in lines:
                title: str | None = None

                # Headings: ## or ###
                heading_match = re.match(r"^#{2,3}\s+(.+)", line)
                if heading_match:
                    title = heading_match.group(1).strip()

                # Checklist items: - [ ] or - [x]
                if title is None:
                    check_match = re.match(r"^-\s+\[[ xX]\]\s+(.+)", line)
                    if check_match:
                        title = check_match.group(1).strip()

                if title is None:
                    continue

                # Skip very short or obviously boilerplate headings
                if len(title) < 3:
                    continue

                req_id = "REQ-" + _slugify(title)
                if req_id in seen_ids:
                    continue
                seen_ids.add(req_id)
                requirements.append(Requirement(id=req_id, title=title, source_file=rel_path))

    return requirements


def check_spec_exists(project_dir: str, requirement: Requirement) -> Tuple[bool, str]:
    """Check whether a spec document references this requirement.

    Searches:
    - All ``*.md`` files under ``docs/``
    - ``*.md`` files under ``.engram/exports/``

    Excludes the requirement's own source file to avoid false positives.

    Args:
        project_dir: Root of the project.
        requirement: The requirement to search for.

    Returns:
        Tuple of (found, reference_path_or_empty_string).
    """
    root = Path(project_dir)
    candidates: List[Path] = []

    docs_dir = root / "docs"
    if docs_dir.is_dir():
        candidates.extend(docs_dir.rglob("*.md"))

    engram_exports = root / ".engram" / "exports"
    if engram_exports.is_dir():
        candidates.extend(engram_exports.rglob("*.md"))

    # Exclude the requirement's own source file
    own_path = root / requirement.source_file
    candidates = [p for p in candidates if p.resolve() != own_path.resolve()]

    # Search for title or ID
    pattern = re.escape(requirement.title[:40]) + "|" + re.escape(requirement.id)
    return _grep_files(pattern, candidates)


def check_code_exists(project_dir: str, requirement: Requirement) -> Tuple[bool, str]:
    """Check whether any code commit or source comment references this requirement.

    Strategies:
    1. ``git log --oneline --all --grep="{title[:30]}"``
    2. Search source files for the requirement ID in comments

    Args:
        project_dir: Root of the project.
        requirement: The requirement to search for.

    Returns:
        Tuple of (found, reference_description).
    """
    root = Path(project_dir)

    # Strategy 1: git log grep
    title_fragment = requirement.title[:30]
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--all", f"--grep={title_fragment}"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            first_line = result.stdout.strip().splitlines()[0]
            return True, f"git: {first_line}"
    except Exception:
        pass

    # Strategy 2: search source files for requirement ID in comments
    source_extensions = {".go", ".ts", ".js", ".py", ".java", ".kt", ".swift", ".rb", ".rs"}
    candidates: List[Path] = []
    for ext in source_extensions:
        candidates.extend(root.rglob(f"*{ext}"))
    # Exclude .cognitive-os and hidden dirs
    candidates = [
        p for p in candidates
        if ".cognitive-os" not in p.parts
        and "node_modules" not in p.parts
        and "__pycache__" not in p.parts
    ]

    found, ref = _grep_files(re.escape(requirement.id), candidates)
    if found:
        return True, ref

    return False, ""


def check_test_exists(project_dir: str, requirement: Requirement) -> Tuple[bool, str]:
    """Check whether a test file references this requirement.

    Scans test files matching common patterns:
    - ``*_test.go``, ``*.spec.ts``, ``*.test.ts``, ``*.spec.js``, ``*.test.js``
    - ``test_*.py``, ``*_test.py``

    Args:
        project_dir: Root of the project.
        requirement: The requirement to search for.

    Returns:
        Tuple of (found, reference_path_or_empty_string).
    """
    root = Path(project_dir)
    test_patterns = [
        "*_test.go",
        "*.spec.ts",
        "*.test.ts",
        "*.spec.js",
        "*.test.js",
        "test_*.py",
        "*_test.py",
    ]
    candidates: List[Path] = []
    for pat in test_patterns:
        candidates.extend(root.rglob(pat))
    candidates = [
        p for p in candidates
        if ".cognitive-os" not in p.parts
        and "node_modules" not in p.parts
        and "__pycache__" not in p.parts
    ]

    # Search for title or ID
    pattern = re.escape(requirement.title[:40]) + "|" + re.escape(requirement.id)
    return _grep_files(pattern, candidates)


def check_traceability(project_dir: str) -> TraceabilityReport:
    """Run full traceability analysis for all discovered requirements.

    Args:
        project_dir: Root of the project.

    Returns:
        TraceabilityReport with per-requirement links, gaps, and coverage %.
    """
    requirements = discover_requirements(project_dir)
    links: List[TraceabilityLink] = []

    for req in requirements:
        has_spec, spec_ref = check_spec_exists(project_dir, req)
        has_code, code_ref = check_code_exists(project_dir, req)
        has_test, test_ref = check_test_exists(project_dir, req)

        present_count = sum([has_spec, has_code, has_test])
        if present_count == 3:
            status = "COMPLETE"
        elif present_count == 0:
            status = "MISSING"
        else:
            status = "PARTIAL"

        links.append(
            TraceabilityLink(
                requirement=req,
                has_spec=has_spec,
                has_code=has_code,
                has_test=has_test,
                spec_ref=spec_ref,
                code_ref=code_ref,
                test_ref=test_ref,
                status=status,
            )
        )

    total = len(links)
    complete_count = sum(1 for lnk in links if lnk.status == "COMPLETE")
    coverage_pct = round((complete_count / total * 100.0) if total > 0 else 0.0, 2)

    gaps = find_gaps(TraceabilityReport(links=links, gaps=[], coverage_pct=coverage_pct))

    return TraceabilityReport(links=links, gaps=gaps, coverage_pct=coverage_pct)


def find_gaps(report: TraceabilityReport) -> List[TraceabilityGap]:
    """Extract gaps from a TraceabilityReport.

    A gap is any link where status != COMPLETE.

    Args:
        report: The report to analyse (gaps field is ignored; recomputed).

    Returns:
        List of TraceabilityGap objects sorted HIGH-first.
    """
    gaps: List[TraceabilityGap] = []
    for lnk in report.links:
        if lnk.status == "COMPLETE":
            continue
        missing: List[str] = []
        if not lnk.has_spec:
            missing.append("spec")
        if not lnk.has_code:
            missing.append("code")
        if not lnk.has_test:
            missing.append("test")
        severity = "HIGH" if len(missing) == 3 else "MEDIUM"
        gaps.append(TraceabilityGap(requirement=lnk.requirement, missing=missing, severity=severity))

    # HIGH gaps first
    gaps.sort(key=lambda g: (0 if g.severity == "HIGH" else 1, g.requirement.id))
    return gaps


def format_gap_report(gaps: List[TraceabilityGap]) -> str:
    """Format a list of gaps as a Markdown report.

    Args:
        gaps: List of TraceabilityGap objects (typically from find_gaps()).

    Returns:
        Markdown-formatted string.
    """
    lines: List[str] = ["# Traceability Gaps", ""]

    high_gaps = [g for g in gaps if g.severity == "HIGH"]
    medium_gaps = [g for g in gaps if g.severity == "MEDIUM"]

    lines.append("## HIGH Severity (no spec, code, or test)")
    if high_gaps:
        for gap in high_gaps:
            missing_str = ", ".join(gap.missing)
            lines.append(f"- {gap.requirement.id}: {gap.requirement.title} — missing: {missing_str}")
    else:
        lines.append("_None._")

    lines += ["", "## MEDIUM Severity (partial coverage)"]
    if medium_gaps:
        for gap in medium_gaps:
            missing_str = ", ".join(gap.missing)
            lines.append(f"- {gap.requirement.id}: {gap.requirement.title} — missing: {missing_str}")
    else:
        lines.append("_None._")

    return "\n".join(lines) + "\n"
