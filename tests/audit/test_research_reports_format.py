"""Audit test — research report format validation.

Validates every .md file under .cognitive-os/reports/research/ follows the
structure required by rules/research-first-protocol.md and
templates/agent-research-only.md.

Marker: @pytest.mark.audit — run in isolation with:
    uv run pytest tests/audit/test_research_reports_format.py -v -m audit
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESEARCH_DIR = PROJECT_ROOT / ".cognitive-os" / "reports" / "research"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}$")


def _report_files() -> list[Path]:
    """Return all .md files in the research reports dir (skip .gitkeep)."""
    if not RESEARCH_DIR.exists():
        return []
    return [
        p
        for p in RESEARCH_DIR.iterdir()
        if p.suffix == ".md" and p.name != ".gitkeep"
    ]


def _has_h1(content: str) -> bool:
    """Return True if content has at least one H1 heading."""
    return bool(re.search(r"^#\s+\S", content, re.MULTILINE))


def _has_tldr_section(content: str) -> bool:
    """Return True if content has a TL;DR section (H2 or H3)."""
    return bool(
        re.search(r"^#{2,3}\s+TL[;:]?DR", content, re.MULTILINE | re.IGNORECASE)
    )


def _has_at_least_one_table(content: str) -> bool:
    """Return True if content has at least one markdown table (pipe-delimited)."""
    # A table row starts with optional whitespace then a pipe char
    return bool(re.search(r"^\s*\|.+\|", content, re.MULTILINE))


def _parse_date_from_filename(path: Path) -> str | None:
    """Extract the YYYY-MM-DD suffix from a report filename, or None."""
    stem = path.stem  # e.g. "cos-init-migration-2026-04-24"
    # Date is the last segment after splitting on hyphens (last 3 parts joined)
    parts = stem.rsplit("-", 3)
    if len(parts) >= 4:
        candidate = "-".join(parts[-3:])
        if DATE_PATTERN.match(candidate):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Parametrize or xfail when no reports exist
# ---------------------------------------------------------------------------

_REPORTS = _report_files()

_NO_REPORTS_REASON = (
    "no reports yet — the policy is shipped without examples; "
    "tests will activate once Phase 0 runs land"
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.audit
def test_research_dir_exists() -> None:
    """Runtime research reports are optional; validate format only once the dir exists."""
    if not RESEARCH_DIR.exists():
        pytest.skip(
            f"No runtime research report directory at {RESEARCH_DIR}; reports are generated on demand."
        )


def _reports_or_empty() -> list[Path]:
    """Return runtime reports; absence is checked once by test_research_dir_exists."""
    return _REPORTS


@pytest.mark.audit
def test_report_has_h1() -> None:
    """Every research report must have at least one H1 heading."""
    failures = []
    for report_path in _reports_or_empty():
        content = report_path.read_text(encoding="utf-8")
        if not _has_h1(content):
            failures.append(report_path.name)
    assert not failures, (
        "Research reports missing H1 heading. Reports must start with a top-level title, "
        f"e.g. '# Research: <topic>': {failures}"
    )


@pytest.mark.audit
def test_report_has_tldr_section() -> None:
    """Every research report must have a TL;DR section."""
    failures = []
    for report_path in _reports_or_empty():
        content = report_path.read_text(encoding="utf-8")
        if not _has_tldr_section(content):
            failures.append(report_path.name)
    assert not failures, (
        "Research reports missing TL;DR section. Add a section heading like '## TL;DR' "
        f"per templates/agent-research-only.md: {failures}"
    )


@pytest.mark.audit
def test_report_has_at_least_one_table() -> None:
    """Every research report must contain at least one markdown table.

    The template requires Decision Points and Risk Assessment as tables.
    """
    failures = []
    for report_path in _reports_or_empty():
        content = report_path.read_text(encoding="utf-8")
        if not _has_at_least_one_table(content):
            failures.append(report_path.name)
    assert not failures, (
        "Research reports without markdown table. Reports must include at least one table "
        f"(Decision Points or Risk Assessment): {failures}"
    )


@pytest.mark.audit
def test_report_filename_has_parseable_date() -> None:
    """Report filename must end with a parseable YYYY-MM-DD date suffix."""
    failures = []
    invalid_dates = []
    for report_path in _reports_or_empty():
        date_str = _parse_date_from_filename(report_path)
        if date_str is None:
            failures.append(report_path.name)
            continue
        year, month, day = date_str.split("-")
        if not (2020 <= int(year) <= 2099 and 1 <= int(month) <= 12 and 1 <= int(day) <= 31):
            invalid_dates.append(report_path.name)
    assert not failures, (
        "Research report filenames without YYYY-MM-DD suffix. Expected pattern: "
        f"<topic>-YYYY-MM-DD.md: {failures}"
    )
    assert not invalid_dates, f"Research report filenames with invalid date components: {invalid_dates}"
