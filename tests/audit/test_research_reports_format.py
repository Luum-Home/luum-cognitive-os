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


@pytest.mark.audit
@pytest.mark.xfail(len(_REPORTS) == 0, reason=_NO_REPORTS_REASON, strict=False)
@pytest.mark.parametrize("report_path", _REPORTS, ids=[p.name for p in _REPORTS])
def test_report_has_h1(report_path: Path) -> None:
    """Every research report must have at least one H1 heading."""
    content = report_path.read_text(encoding="utf-8")
    assert _has_h1(content), (
        f"{report_path.name}: missing H1 heading.\n"
        "Reports must start with a top-level title, e.g. '# Research: <topic>'"
    )


@pytest.mark.audit
@pytest.mark.xfail(len(_REPORTS) == 0, reason=_NO_REPORTS_REASON, strict=False)
@pytest.mark.parametrize("report_path", _REPORTS, ids=[p.name for p in _REPORTS])
def test_report_has_tldr_section(report_path: Path) -> None:
    """Every research report must have a TL;DR section."""
    content = report_path.read_text(encoding="utf-8")
    assert _has_tldr_section(content), (
        f"{report_path.name}: missing TL;DR section.\n"
        "Add a section heading like '## TL;DR' per templates/agent-research-only.md"
    )


@pytest.mark.audit
@pytest.mark.xfail(len(_REPORTS) == 0, reason=_NO_REPORTS_REASON, strict=False)
@pytest.mark.parametrize("report_path", _REPORTS, ids=[p.name for p in _REPORTS])
def test_report_has_at_least_one_table(report_path: Path) -> None:
    """Every research report must contain at least one markdown table.

    The template requires Decision Points and Risk Assessment as tables.
    """
    content = report_path.read_text(encoding="utf-8")
    assert _has_at_least_one_table(content), (
        f"{report_path.name}: no markdown table found.\n"
        "Reports must include at least one table (Decision Points or Risk Assessment)."
    )


@pytest.mark.audit
@pytest.mark.xfail(len(_REPORTS) == 0, reason=_NO_REPORTS_REASON, strict=False)
@pytest.mark.parametrize("report_path", _REPORTS, ids=[p.name for p in _REPORTS])
def test_report_filename_has_parseable_date(report_path: Path) -> None:
    """Report filename must end with a parseable YYYY-MM-DD date suffix."""
    date_str = _parse_date_from_filename(report_path)
    assert date_str is not None, (
        f"{report_path.name}: filename does not contain a YYYY-MM-DD date suffix.\n"
        "Expected pattern: <topic>-YYYY-MM-DD.md\n"
        "Example: cos-init-migration-2026-04-24.md"
    )
    # Validate the date components are in reasonable ranges
    year, month, day = date_str.split("-")
    assert 2020 <= int(year) <= 2099, f"Implausible year in filename: {year}"
    assert 1 <= int(month) <= 12, f"Invalid month in filename: {month}"
    assert 1 <= int(day) <= 31, f"Invalid day in filename: {day}"
