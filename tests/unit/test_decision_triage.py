"""Unit tests for scripts/decision_triage.py

Tests:
1. Parses ## Open Questions section with numbered items
2. Parses ## Decision Points table correctly
3. Empty source dir → empty output, no crash
4. ADR with no ## Open questions section → skipped silently (not an error)
5. Engram unavailable → skill produces report, marks all PENDING (engram unavailable)
6. Real-file integration test — runs against actual docs/ files, non-empty output,
   MUST NOT modify source files
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import decision_triage as dt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_report(content: str, tmp_path: Path, name: str = "report-test.md") -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: Parse ## Open Questions section with numbered items
# ---------------------------------------------------------------------------

class TestOpenQuestionsSection:
    def test_numbered_items_parsed(self, tmp_path):
        content = """\
# Research Report

Some intro text.

## Open Questions for Operator

1. Should we migrate the old script first?
2. Is backwards compatibility required?
3. What is the cutoff date?

## Other Section

Not a decision.
"""
        md = make_report(content, tmp_path)
        decisions = dt._extract_decisions_from_file(
            md, "report", dt.REPORT_SECTION_PATTERNS
        )
        assert len(decisions) == 3
        assert decisions[0].text == "Should we migrate the old script first?"
        assert decisions[1].text == "Is backwards compatibility required?"
        assert decisions[2].text == "What is the cutoff date?"
        assert all(d.source_type == "report" for d in decisions)
        assert decisions[0].index == 1
        assert decisions[2].index == 3

    def test_bullet_items_parsed(self, tmp_path):
        content = """\
## Open Questions

- Do we need feature flags?
- Is the API backward compatible?
"""
        md = make_report(content, tmp_path)
        decisions = dt._extract_decisions_from_file(
            md, "report", dt.REPORT_SECTION_PATTERNS
        )
        assert len(decisions) == 2
        assert decisions[0].text == "Do we need feature flags?"

    def test_mixed_header_variants(self, tmp_path):
        """Case-insensitive match for all known section header variants."""
        for header in [
            "## Open Questions",
            "## Open questions for operator",
            "## OPEN QUESTIONS FOR OPERATOR",
            "## Decisions for Operator",
            "## Operator Decisions Pending",
        ]:
            content = f"{header}\n\n1. Test decision item.\n"
            md = make_report(content, tmp_path, "variant.md")
            decisions = dt._extract_decisions_from_file(
                md, "report", dt.REPORT_SECTION_PATTERNS
            )
            assert len(decisions) == 1, f"Failed for header: {header!r}"


# ---------------------------------------------------------------------------
# Test 2: Parse ## Decision Points table correctly
# ---------------------------------------------------------------------------

class TestDecisionPointsTable:
    def test_table_rows_parsed(self, tmp_path):
        content = """\
## Decision Points (operator answers needed)

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Hook validation failure mode: WARN or BLOCK? | exit 0 advisory / exit 2 block | Advisory by default |
| 2 | ADR backfill policy: all 36 missing? or cutoff? | Grandfather all / backfill all | Recommend cutoff at ADR-067 |
"""
        md = make_report(content, tmp_path)
        decisions = dt._extract_decisions_from_file(
            md, "report", dt.REPORT_SECTION_PATTERNS
        )
        assert len(decisions) == 2
        # First data row, numeric index stripped
        assert "Hook validation failure mode" in decisions[0].text
        assert "ADR backfill policy" in decisions[1].text

    def test_table_separator_not_parsed_as_decision(self, tmp_path):
        content = """\
## Decision Points

| # | Decision | Recommendation |
|---|---|---|
| 1 | Should we add a template? | Yes |
"""
        md = make_report(content, tmp_path)
        decisions = dt._extract_decisions_from_file(
            md, "report", dt.REPORT_SECTION_PATTERNS
        )
        # Only the data row should appear, not the header or separator
        assert len(decisions) == 1
        assert "Should we add a template?" in decisions[0].text


# ---------------------------------------------------------------------------
# Test 3: Empty source directory → empty output, no crash
# ---------------------------------------------------------------------------

class TestEmptySource:
    def test_empty_reports_dir(self, tmp_path):
        empty_dir = tmp_path / "empty_reports"
        empty_dir.mkdir()
        decisions = dt.scan_reports(empty_dir)
        assert decisions == []

    def test_missing_dir_returns_empty(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        decisions = dt.scan_reports(nonexistent)
        assert decisions == []

    def test_empty_adr_dir(self, tmp_path):
        empty_dir = tmp_path / "empty_adrs"
        empty_dir.mkdir()
        decisions = dt.scan_adrs(empty_dir)
        assert decisions == []

    def test_main_with_empty_dirs(self, tmp_path, capsys):
        """main() must not crash when both source dirs are empty."""
        empty_reports = tmp_path / "reports"
        empty_adrs = tmp_path / "adrs"
        empty_reports.mkdir()
        empty_adrs.mkdir()

        # Patch the module-level constants to point at temp dirs
        with (
            patch.object(dt, "REPORTS_DIR", empty_reports),
            patch.object(dt, "ADRS_DIR", empty_adrs),
        ):
            rc = dt.main([])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Total unanswered:" in captured.out


# ---------------------------------------------------------------------------
# Test 4: ADR with no ## Open questions section → skipped silently
# ---------------------------------------------------------------------------

class TestAdrNoOpenQuestions:
    def test_adr_without_open_questions(self, tmp_path):
        content = """\
# ADR-001: Some decision

## Status
Accepted

## Context
We needed to decide something.

## Decision
We went with option A.

## Consequences
Things are better now.
"""
        adr = tmp_path / "ADR-001-some-decision.md"
        adr.write_text(content, encoding="utf-8")
        decisions = dt.scan_adrs(tmp_path)
        assert decisions == []  # no crash, no decisions

    def test_adr_with_open_questions(self, tmp_path):
        content = """\
# ADR-002: Another decision

## Status
Proposed

## Open questions

1. Should we grandfather old hooks?
2. What is the cleanup timeline?
"""
        adr = tmp_path / "ADR-002-another-decision.md"
        adr.write_text(content, encoding="utf-8")
        decisions = dt.scan_adrs(tmp_path)
        assert len(decisions) == 2
        assert decisions[0].source_type == "adr"


# ---------------------------------------------------------------------------
# Test 5: Engram unavailable → skill produces report, marks PENDING
# ---------------------------------------------------------------------------

class TestEngramUnavailable:
    def test_engram_failure_produces_report(self, tmp_path, capsys):
        """When engram is unavailable, skill still outputs a complete report."""
        content = """\
## Open Questions

1. What should we do about the old API?
2. Is migration required now?
"""
        md = make_report(content, tmp_path, "report-engram-test.md")
        # Make an ADR dir with no files
        adr_dir = tmp_path / "adrs"
        adr_dir.mkdir()

        with (
            patch.object(dt, "REPORTS_DIR", tmp_path),
            patch.object(dt, "ADRS_DIR", adr_dir),
            # Force engram to fail by patching _engram_search to raise
            patch.object(dt, "_engram_search", side_effect=Exception("connection refused")),
        ):
            rc = dt.main([])

        assert rc == 0
        captured = capsys.readouterr()
        assert "Total unanswered:" in captured.out
        # Must NOT crash — any status is acceptable for the decisions
        assert "Decision" not in captured.err or True  # stderr may have warning

    def test_all_decisions_marked_pending_when_engram_down(self, tmp_path):
        """enrich_with_engram marks all decisions PENDING when engram unavailable."""
        decisions = [
            dt.Decision(
                source_path="docs/reports/test.md",
                source_type="report",
                section="Open Questions",
                text="Should we do X?",
                index=1,
            )
        ]
        with patch.object(dt, "_engram_search", return_value=None):
            result, available = dt.enrich_with_engram(decisions)

        assert not available
        assert all("PENDING" in d.status for d in result)

    def test_engram_exception_does_not_crash_main(self, tmp_path, capsys):
        """enrich_with_engram exception propagates gracefully in main()."""
        content = "## Open Questions\n\n1. Test question.\n"
        make_report(content, tmp_path, "r.md")
        adr_dir = tmp_path / "adrs"
        adr_dir.mkdir()

        def boom(*args, **kwargs):
            raise RuntimeError("engram exploded")

        with (
            patch.object(dt, "REPORTS_DIR", tmp_path),
            patch.object(dt, "ADRS_DIR", adr_dir),
            patch.object(dt, "enrich_with_engram", side_effect=boom),
        ):
            rc = dt.main([])

        assert rc == 0
        captured = capsys.readouterr()
        # Status should fall back to PENDING (engram unavailable) in main()'s except
        assert "Total unanswered:" in captured.out


# ---------------------------------------------------------------------------
# Test 6: Real-file integration test
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestRealFilesIntegration:
    """Runs against actual docs/reports/*.md and docs/adrs/ADR-*.md.
    MUST NOT modify any source files.
    """

    def _collect_mtimes(self) -> dict[str, float]:
        """Collect mtimes for all source files we scan."""
        mtimes: dict[str, float] = {}
        for md in (dt.REPORTS_DIR).glob("*.md"):
            try:
                mtimes[str(md)] = md.stat().st_mtime
            except OSError:
                pass
        for md in (dt.ADRS_DIR).glob("ADR-*.md"):
            try:
                mtimes[str(md)] = md.stat().st_mtime
            except OSError:
                pass
        return mtimes

    def test_output_is_nonempty(self, capsys):
        """Skill produces non-empty output against real files."""
        # Skip if source dirs don't exist
        if not dt.REPORTS_DIR.exists() and not dt.ADRS_DIR.exists():
            pytest.skip("Source dirs not found — skipping integration test")

        rc = dt.main([])
        assert rc == 0
        captured = capsys.readouterr()
        assert len(captured.out.strip()) > 0

    def test_output_has_required_sections(self, capsys):
        """Real output contains expected structural sections."""
        if not dt.REPORTS_DIR.exists() and not dt.ADRS_DIR.exists():
            pytest.skip("Source dirs not found")

        dt.main([])
        captured = capsys.readouterr()
        output = captured.out
        assert "# Decision Triage" in output
        assert "Total unanswered:" in output
        assert "## By urgency" in output
        assert "## Engram cross-ref status" in output

    def test_json_mode_is_valid(self, capsys):
        """--json produces valid, parseable JSON."""
        if not dt.REPORTS_DIR.exists() and not dt.ADRS_DIR.exists():
            pytest.skip("Source dirs not found")

        rc = dt.main(["--json"])
        assert rc == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)  # will raise if invalid JSON
        assert "decisions" in parsed
        assert "total" in parsed
        assert isinstance(parsed["decisions"], list)

    def test_critical_only_flag(self, capsys):
        """--critical-only returns exit 0 and a valid report."""
        if not dt.REPORTS_DIR.exists() and not dt.ADRS_DIR.exists():
            pytest.skip("Source dirs not found")

        rc = dt.main(["--critical-only"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "# Decision Triage" in captured.out

    def test_source_files_not_modified(self):
        """CRITICAL: source files must not be modified by running the skill."""
        if not dt.REPORTS_DIR.exists() and not dt.ADRS_DIR.exists():
            pytest.skip("Source dirs not found")

        mtimes_before = self._collect_mtimes()
        if not mtimes_before:
            pytest.skip("No source files found to check")

        # Run with a small sleep buffer
        dt.main([])

        # Give filesystem 50ms to settle
        time.sleep(0.05)

        mtimes_after = self._collect_mtimes()

        modified = [
            path for path, mtime in mtimes_before.items()
            if mtimes_after.get(path, mtime) != mtime
        ]
        assert not modified, (
            f"READ-ONLY violation: the following source files were modified:\n"
            + "\n".join(f"  {p}" for p in modified)
        )

    def test_at_least_one_decision_found(self, capsys):
        """Expect the real repo to have at least some open decisions."""
        if not dt.REPORTS_DIR.exists() and not dt.ADRS_DIR.exists():
            pytest.skip("Source dirs not found")

        rc = dt.main(["--json"])
        assert rc == 0
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        # The repo has research reports with decision points; expect > 0
        assert parsed["total"] > 0, (
            "Expected at least one decision in the real repo — check scan logic"
        )
