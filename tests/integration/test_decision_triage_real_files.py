"""tests/integration/test_decision_triage_real_files.py

Real-file integration tests for scripts/decision_triage.py.

Runs against actual docs/reports/*.md and docs/adrs/ADR-*.md.
MUST NOT modify any source files.

Moved from tests/unit/test_decision_triage.py (TestRealFilesIntegration class).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import decision_triage as dt

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.timeout(300)
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
