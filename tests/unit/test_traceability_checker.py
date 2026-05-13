"""Unit tests for lib/traceability_checker.py."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from lib.traceability_checker import (
    check_traceability,
    discover_requirements,
    find_gaps,
    format_gap_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git_init(path: Path) -> None:
    """Initialise a minimal git repository in *path*."""
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )


def _git_commit(path: Path, message: str) -> None:
    """Stage all files and create a commit."""
    subprocess.run(["git", "add", "-A"], cwd=str(path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message, "--allow-empty"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ---------------------------------------------------------------------------
# D1: Complete traceability (spec + code + test all present)
# ---------------------------------------------------------------------------


class TestCompleteTraceability:
    def test_complete_traceability(self, tmp_path: Path) -> None:
        """D1: A requirement with matching spec, commit, and test is COMPLETE."""
        _git_init(tmp_path)

        # Feature doc
        _write(
            tmp_path / "docs" / "05-features" / "auth.md",
            "# Auth\n\n## User Authentication\n\nUsers must log in.\n",
        )
        _git_commit(tmp_path, "docs: add auth feature spec")

        # Spec (separate doc referencing the requirement)
        _write(
            tmp_path / "docs" / "04-security" / "auth-spec.md",
            "# Auth Spec\n\nUser Authentication is handled via JWT.\n",
        )
        _git_commit(tmp_path, "docs: auth spec")

        # Test file
        _write(
            tmp_path / "tests" / "test_auth.py",
            "def test_user_authentication():\n    # User Authentication\n    assert True\n",
        )

        # Commit with the requirement title in the message
        _git_commit(tmp_path, "feat: User Authentication via JWT")

        report = check_traceability(str(tmp_path))

        # Find the auth link
        auth_links = [
            lnk for lnk in report.links
            if "user-authentication" in lnk.requirement.id.lower()
        ]
        assert auth_links, f"No auth link found. Links: {[l.requirement.id for l in report.links]}"
        auth_link = auth_links[0]
        assert auth_link.status == "COMPLETE", (
            f"Expected COMPLETE, got {auth_link.status}. "
            f"has_spec={auth_link.has_spec}, has_code={auth_link.has_code}, has_test={auth_link.has_test}"
        )

    def test_complete_traceability_link_fields(self, tmp_path: Path) -> None:
        """COMPLETE links should have True for all three has_* fields."""
        _git_init(tmp_path)

        _write(
            tmp_path / "docs" / "05-features" / "feature.md",
            "## Email Notifications\n\nSend emails on signup.\n",
        )
        _write(
            tmp_path / "docs" / "02-design" / "email-design.md",
            "Email Notifications design: use SES.\n",
        )
        _write(
            tmp_path / "tests" / "test_email.py",
            "def test_email_notifications():\n    # Email Notifications\n    pass\n",
        )
        # Commit with requirement title in message so git-log grep picks it up
        _git_commit(tmp_path, "feat: Email Notifications using SES")

        report = check_traceability(str(tmp_path))
        link = next(
            (l for l in report.links if "email-notifications" in l.requirement.id), None
        )
        assert link is not None
        assert link.has_spec is True
        assert link.has_code is True
        assert link.has_test is True


# ---------------------------------------------------------------------------
# D2: Missing traceability
# ---------------------------------------------------------------------------


class TestMissingTraceability:
    def test_missing_traceability(self, tmp_path: Path) -> None:
        """D2: A requirement with no spec, code, or test is MISSING with 3 gap items."""
        _git_init(tmp_path)

        # Only the feature doc itself — no spec, no commits, no test
        _write(
            tmp_path / "docs" / "05-features" / "payments.md",
            "# Payments\n\n## Payment Processing\n\nProcess credit card payments.\n",
        )
        _git_commit(tmp_path, "docs: add payments feature doc")

        report = check_traceability(str(tmp_path))

        payment_links = [
            lnk for lnk in report.links
            if "payment-processing" in lnk.requirement.id
        ]
        assert payment_links, f"No payment link found. Links: {[l.requirement.id for l in report.links]}"
        payment_link = payment_links[0]
        assert payment_link.status == "MISSING"

        gaps = find_gaps(report)
        payment_gaps = [g for g in gaps if "payment-processing" in g.requirement.id]
        assert payment_gaps, "No payment gap found"
        gap = payment_gaps[0]
        assert "spec" in gap.missing
        assert "code" in gap.missing
        assert "test" in gap.missing
        assert gap.severity == "HIGH"

    def test_missing_requirement_not_in_complete_count(self, tmp_path: Path) -> None:
        """A MISSING requirement reduces coverage_pct."""
        _git_init(tmp_path)

        _write(
            tmp_path / "docs" / "05-features" / "incomplete.md",
            "## Incomplete Feature\n\nNot implemented yet.\n",
        )
        _git_commit(tmp_path, "docs: stub feature")

        report = check_traceability(str(tmp_path))
        assert report.coverage_pct < 100.0


# ---------------------------------------------------------------------------
# D3: Coverage percentage
# ---------------------------------------------------------------------------


class TestCoveragePercentage:
    def _make_full_requirement(self, tmp_path: Path, name: str, slug: str) -> None:
        """Create a fully-traceable requirement (feature doc + spec + commit + test)."""
        _write(
            tmp_path / "docs" / "05-features" / f"{slug}.md",
            f"## {name}\n\n{name} details.\n",
        )
        _write(
            tmp_path / "docs" / "02-design" / f"{slug}-spec.md",
            f"Spec for {name}.\n",
        )
        _write(
            tmp_path / "tests" / f"test_{slug}.py",
            f"def test_{slug}():\n    # {name}\n    pass\n",
        )
        # Stage the files first, then commit with the req name in message
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"feat: {name}", "--allow-empty"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )

    def _make_empty_requirement(self, tmp_path: Path, name: str, slug: str) -> None:
        """Create a requirement with only a feature doc (no spec/code/test)."""
        _write(
            tmp_path / "docs" / "05-features" / f"{slug}.md",
            f"## {name}\n\nNot implemented.\n",
        )

    def test_coverage_percentage(self, tmp_path: Path) -> None:
        """D3: 3 complete out of 5 requirements → 60% coverage."""
        _git_init(tmp_path)

        full_reqs = [
            ("Alpha Feature", "alpha"),
            ("Beta Feature", "beta"),
            ("Gamma Feature", "gamma"),
        ]
        empty_reqs = [
            ("Delta Feature", "delta"),
            ("Epsilon Feature", "epsilon"),
        ]

        for name, slug in full_reqs:
            self._make_full_requirement(tmp_path, name, slug)

        # Stage the stub docs, then commit once
        for name, slug in empty_reqs:
            self._make_empty_requirement(tmp_path, name, slug)
        _git_commit(tmp_path, "docs: add stub requirements")

        report = check_traceability(str(tmp_path))

        # We should find exactly 5 requirements
        req_ids = {lnk.requirement.id for lnk in report.links}
        assert len(report.links) == 5, (
            f"Expected 5 requirements, got {len(report.links)}: {sorted(req_ids)}"
        )

        complete = [lnk for lnk in report.links if lnk.status == "COMPLETE"]
        assert len(complete) == 3, (
            f"Expected 3 COMPLETE links, got {len(complete)}: "
            f"{[(l.requirement.id, l.status) for l in report.links]}"
        )
        assert report.coverage_pct == pytest.approx(60.0, abs=0.1)

    def test_zero_requirements_returns_zero_coverage(self, tmp_path: Path) -> None:
        """No docs → no requirements → 0% coverage, no crash."""
        _git_init(tmp_path)
        report = check_traceability(str(tmp_path))
        assert report.coverage_pct == 0.0
        assert report.links == []
        assert report.gaps == []


# ---------------------------------------------------------------------------
# Additional: discover_requirements, find_gaps, format_gap_report
# ---------------------------------------------------------------------------


class TestDiscoverRequirements:
    def test_discovers_heading_requirements(self, tmp_path: Path) -> None:
        """## and ### headings in feature docs should produce requirements."""
        _write(
            tmp_path / "docs" / "05-features" / "multi.md",
            "## Feature One\n### Sub Feature\n## Feature Two\n",
        )
        reqs = discover_requirements(str(tmp_path))
        ids = {r.id for r in reqs}
        assert "REQ-feature-one" in ids
        assert "REQ-sub-feature" in ids
        assert "REQ-feature-two" in ids

    def test_discovers_checklist_requirements(self, tmp_path: Path) -> None:
        """Checklist items (- [ ] / - [x]) should also become requirements."""
        _write(
            tmp_path / "docs" / "05-features" / "checklist.md",
            "- [ ] Dark Mode Support\n- [x] Export to CSV\n",
        )
        reqs = discover_requirements(str(tmp_path))
        ids = {r.id for r in reqs}
        assert "REQ-dark-mode-support" in ids
        assert "REQ-export-to-csv" in ids

    def test_deduplicates_requirements(self, tmp_path: Path) -> None:
        """The same heading in two files should appear only once."""
        for fname in ("a.md", "b.md"):
            _write(
                tmp_path / "docs" / "05-features" / fname,
                "## Shared Requirement\n",
            )
        reqs = discover_requirements(str(tmp_path))
        count = sum(1 for r in reqs if r.id == "REQ-shared-requirement")
        assert count == 1


class TestFindGaps:
    def test_find_gaps_high_severity(self, tmp_path: Path) -> None:
        """Requirements missing all three artefacts get HIGH severity."""
        _git_init(tmp_path)
        _write(
            tmp_path / "docs" / "05-features" / "orphan.md",
            "## Orphan Feature\nNo code, no spec, no test.\n",
        )
        _git_commit(tmp_path, "docs: orphan feature")
        report = check_traceability(str(tmp_path))
        gaps = find_gaps(report)
        high_gaps = [g for g in gaps if g.severity == "HIGH"]
        assert any("orphan-feature" in g.requirement.id for g in high_gaps)

    def test_no_gaps_when_all_complete(self, tmp_path: Path) -> None:
        """Fully-traced requirement should produce no gaps."""
        _git_init(tmp_path)
        _write(
            tmp_path / "docs" / "05-features" / "complete.md",
            "## Fully Traced Feature\nAll good.\n",
        )
        _write(
            tmp_path / "docs" / "02-spec" / "complete-spec.md",
            "Fully Traced Feature details.\n",
        )
        _write(
            tmp_path / "tests" / "test_complete.py",
            "# Fully Traced Feature\ndef test_it(): pass\n",
        )
        _git_commit(tmp_path, "feat: Fully Traced Feature implemented")
        report = check_traceability(str(tmp_path))
        gaps = find_gaps(report)
        traced_gaps = [g for g in gaps if "fully-traced-feature" in g.requirement.id]
        assert len(traced_gaps) == 0


class TestFormatGapReport:
    def test_format_gap_report_structure(self, tmp_path: Path) -> None:
        """Format a gap report from a real traceability run."""
        _git_init(tmp_path)
        _write(
            tmp_path / "docs" / "05-features" / "missing.md",
            "## Missing Feature\nNot done.\n",
        )
        _git_commit(tmp_path, "docs: missing feature stub")

        report = check_traceability(str(tmp_path))
        gaps = find_gaps(report)
        md = format_gap_report(gaps)

        assert "# Traceability Gaps" in md
        assert "HIGH Severity" in md
        assert "MEDIUM Severity" in md

    def test_format_gap_report_empty(self) -> None:
        """Empty gaps list should still produce valid Markdown with no entries."""
        md = format_gap_report([])
        assert "# Traceability Gaps" in md
        assert "_None._" in md
