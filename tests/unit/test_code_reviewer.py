"""Unit tests for lib/code_reviewer.py

Validates code review logic: file review, diff review, adversarial protocol
enforcement, engram integration helpers, and report formatting.
"""

import os
import textwrap

import pytest

from lib.code_reviewer import (
    CodeReviewer,
    ReviewFinding,
    ReviewReport,
    ReviewStatus,
    Severity,
    format_report,
    review_diff,
    review_files,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ReviewFinding
# ---------------------------------------------------------------------------


class TestReviewFinding:
    """Tests for ReviewFinding dataclass."""

    def test_to_dict(self):
        finding = ReviewFinding(
            severity=Severity.BLOCKER,
            file="src/auth.py",
            line=42,
            what="Hardcoded password",
            why="Security risk",
            recommendation="Use environment variable",
        )
        d = finding.to_dict()
        assert d["severity"] == "BLOCKER"
        assert d["file"] == "src/auth.py"
        assert d["line"] == 42
        assert d["what"] == "Hardcoded password"

    def test_to_dict_without_line(self):
        finding = ReviewFinding(
            severity=Severity.SUGGESTION,
            file="README.md",
            line=None,
            what="Missing docs",
            why="Maintainability",
            recommendation="Add documentation",
        )
        d = finding.to_dict()
        assert d["line"] is None


# ---------------------------------------------------------------------------
# ReviewReport
# ---------------------------------------------------------------------------


class TestReviewReport:
    """Tests for ReviewReport dataclass."""

    def test_status_failed_with_blockers(self):
        report = ReviewReport(
            status=ReviewStatus.FAILED,
            findings=[
                ReviewFinding(Severity.BLOCKER, "f.py", 1, "bad", "reason", "fix"),
            ],
            files_reviewed=1,
        )
        assert report.status == "FAILED"
        assert report.blocker_count == 1

    def test_status_passed_without_blockers(self):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(Severity.SUGGESTION, "f.py", 1, "ok", "reason", "fix"),
            ],
            files_reviewed=1,
        )
        assert report.status == "PASSED"
        assert report.blocker_count == 0

    def test_counts(self):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(Severity.BLOCKER, "a.py", 1, "a", "b", "c"),
                ReviewFinding(Severity.CONCERN, "a.py", 2, "a", "b", "c"),
                ReviewFinding(Severity.CONCERN, "a.py", 3, "a", "b", "c"),
                ReviewFinding(Severity.SUGGESTION, "a.py", 4, "a", "b", "c"),
                ReviewFinding(Severity.QUESTION, "a.py", 5, "a", "b", "c"),
            ],
            files_reviewed=1,
        )
        assert report.blocker_count == 1
        assert report.concern_count == 2
        assert report.suggestion_count == 1
        assert report.question_count == 1

    def test_to_dict(self):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(Severity.SUGGESTION, "f.py", 1, "ok", "r", "fix"),
            ],
            files_reviewed=1,
            engram_context_used=True,
            past_review_count=3,
        )
        d = report.to_dict()
        assert d["status"] == "PASSED"
        assert d["files_reviewed"] == 1
        assert d["engram_context_used"] is True
        assert d["past_review_count"] == 3
        assert d["summary"]["total"] == 1
        assert d["summary"]["suggestions"] == 1

    def test_default_review_dimensions(self):
        report = ReviewReport(status=ReviewStatus.PASSED, findings=[], files_reviewed=0)
        assert "correctness" in report.review_dimensions
        assert "security" in report.review_dimensions
        assert len(report.review_dimensions) == 5

    def test_timestamp_auto_set(self):
        report = ReviewReport(status=ReviewStatus.PASSED, findings=[], files_reviewed=0)
        assert report.timestamp != ""


# ---------------------------------------------------------------------------
# CodeReviewer.review_files
# ---------------------------------------------------------------------------


class TestReviewFiles:
    """Tests for CodeReviewer.review_files."""

    def test_returns_review_report(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1\n")
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["test.py"])
        assert isinstance(report, ReviewReport)

    def test_nonexistent_file_produces_question(self, tmp_path):
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["nonexistent.py"])
        assert any(f.severity == Severity.QUESTION for f in report.findings)
        assert any("not found" in f.what.lower() for f in report.findings)

    def test_detects_hardcoded_password(self, tmp_path):
        test_file = tmp_path / "config.py"
        test_file.write_text('password = "super_secret_123"\n')
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["config.py"])
        assert any("password" in f.what.lower() or "hardcoded" in f.what.lower() for f in report.findings)

    def test_detects_eval_usage(self, tmp_path):
        test_file = tmp_path / "handler.py"
        test_file.write_text('result = eval(user_input)\n')
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["handler.py"])
        assert any("eval" in f.what.lower() for f in report.findings)

    def test_detects_todo_comments(self, tmp_path):
        test_file = tmp_path / "app.py"
        test_file.write_text("# TODO fix this later\nx = 1\n")
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["app.py"])
        assert any("todo" in f.what.lower() for f in report.findings)

    def test_at_least_one_finding_always_present(self, tmp_path):
        """Adversarial review: MUST produce at least one finding."""
        test_file = tmp_path / "clean.py"
        test_file.write_text("x = 1\ny = 2\nz = x + y\n")
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["clean.py"])
        assert len(report.findings) >= 1

    def test_findings_have_severity_tiers(self, tmp_path):
        test_file = tmp_path / "mixed.py"
        test_file.write_text(
            textwrap.dedent("""\
            # TODO fix
            password = "secret"
            x = eval("1+1")
            """)
        )
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["mixed.py"])
        severities = {f.severity for f in report.findings}
        # Should have findings — at least the security ones
        assert len(report.findings) >= 1
        # Every finding has a valid severity
        for finding in report.findings:
            assert finding.severity in {
                Severity.BLOCKER,
                Severity.CONCERN,
                Severity.SUGGESTION,
                Severity.QUESTION,
            }

    def test_findings_have_required_fields(self, tmp_path):
        test_file = tmp_path / "test.py"
        test_file.write_text("# FIXME broken\n")
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["test.py"])
        for finding in report.findings:
            assert finding.file != ""
            assert finding.what != ""
            assert finding.why != ""
            assert finding.recommendation != ""

    def test_failed_status_on_blocker(self, tmp_path):
        test_file = tmp_path / "bad.py"
        test_file.write_text('api_key = "sk-abc123456789012345678"\n')
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["bad.py"])
        assert report.status == ReviewStatus.FAILED

    def test_passed_status_without_blockers(self, tmp_path):
        test_file = tmp_path / "ok.py"
        test_file.write_text("# TODO improve\nx = 1\n")
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["ok.py"])
        # TODO is a SUGGESTION, not BLOCKER
        assert report.status == ReviewStatus.PASSED

    def test_multiple_files(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\n")
        (tmp_path / "b.py").write_text("y = 2\n")
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["a.py", "b.py"])
        assert report.files_reviewed == 2


# ---------------------------------------------------------------------------
# CodeReviewer.review_diff
# ---------------------------------------------------------------------------


class TestReviewDiff:
    """Tests for CodeReviewer.review_diff."""

    def test_returns_review_report(self):
        diff = textwrap.dedent("""\
        diff --git a/test.py b/test.py
        --- a/test.py
        +++ b/test.py
        @@ -1,3 +1,4 @@
         x = 1
        +y = 2
         z = 3
        """)
        reviewer = CodeReviewer()
        report = reviewer.review_diff(diff)
        assert isinstance(report, ReviewReport)

    def test_empty_diff_produces_question(self):
        reviewer = CodeReviewer()
        report = reviewer.review_diff("")
        assert len(report.findings) >= 1
        assert any(f.severity == Severity.QUESTION for f in report.findings)
        assert report.files_reviewed == 0

    def test_whitespace_only_diff(self):
        reviewer = CodeReviewer()
        report = reviewer.review_diff("   \n  \n")
        assert len(report.findings) >= 1

    def test_detects_issue_in_added_lines(self):
        diff = textwrap.dedent("""\
        diff --git a/config.py b/config.py
        --- a/config.py
        +++ b/config.py
        @@ -1,2 +1,3 @@
         x = 1
        +password = "mysecret"
         z = 3
        """)
        reviewer = CodeReviewer()
        report = reviewer.review_diff(diff)
        assert any("password" in f.what.lower() or "hardcoded" in f.what.lower() for f in report.findings)

    def test_at_least_one_finding(self):
        """Adversarial: even a clean diff must produce a finding."""
        diff = textwrap.dedent("""\
        diff --git a/clean.py b/clean.py
        --- a/clean.py
        +++ b/clean.py
        @@ -1 +1,2 @@
         x = 1
        +y = 2
        """)
        reviewer = CodeReviewer()
        report = reviewer.review_diff(diff)
        assert len(report.findings) >= 1


# ---------------------------------------------------------------------------
# CodeReviewer.search_past_reviews
# ---------------------------------------------------------------------------


class TestSearchPastReviews:
    """Tests for search_past_reviews (engram query preparation)."""

    def test_returns_list(self):
        reviewer = CodeReviewer()
        queries = reviewer.search_past_reviews(["internal/users/handler.go"])
        assert isinstance(queries, list)

    def test_extracts_service_name(self):
        reviewer = CodeReviewer()
        queries = reviewer.search_past_reviews(["internal/users/handler.go"])
        assert any(q["service"] == "users" for q in queries)

    def test_deduplicates_services(self):
        reviewer = CodeReviewer()
        queries = reviewer.search_past_reviews([
            "internal/users/handler.go",
            "internal/users/dto.go",
            "internal/users/mapper.go",
        ])
        # Should have one query for "users", not three
        services = [q["service"] for q in queries]
        assert services.count("users") == 1

    def test_multiple_services(self):
        reviewer = CodeReviewer()
        queries = reviewer.search_past_reviews([
            "internal/users/handler.go",
            "internal/payments/service.go",
        ])
        services = {q["service"] for q in queries}
        assert "users" in services
        assert "payments" in services

    def test_empty_files_returns_empty(self):
        reviewer = CodeReviewer()
        queries = reviewer.search_past_reviews([])
        assert queries == []

    def test_query_contains_review_prefix(self):
        reviewer = CodeReviewer()
        queries = reviewer.search_past_reviews(["src/auth/login.py"])
        assert any("review/" in q["query"] for q in queries)


# ---------------------------------------------------------------------------
# CodeReviewer.save_review
# ---------------------------------------------------------------------------


class TestSaveReview:
    """Tests for save_review (engram save preparation)."""

    def test_returns_dict_for_mem_save(self):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(Severity.SUGGESTION, "internal/users/handler.go", 10, "ok", "r", "fix"),
            ],
            files_reviewed=1,
        )
        reviewer = CodeReviewer()
        result = reviewer.save_review(report)
        assert "title" in result
        assert "content" in result
        assert "type" in result
        assert "topic_key" in result
        assert result["type"] == "review"

    def test_topic_key_format(self):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(Severity.SUGGESTION, "internal/users/handler.go", 10, "ok", "r", "fix"),
            ],
            files_reviewed=1,
        )
        reviewer = CodeReviewer()
        result = reviewer.save_review(report)
        assert result["topic_key"].startswith("review/")

    def test_topic_key_with_change_name(self):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(Severity.SUGGESTION, "f.py", 1, "ok", "r", "fix"),
            ],
            files_reviewed=1,
        )
        reviewer = CodeReviewer()
        result = reviewer.save_review(report, change_name="feature/auth")
        assert "feature/auth" in result["topic_key"]

    def test_content_includes_findings(self):
        report = ReviewReport(
            status=ReviewStatus.FAILED,
            findings=[
                ReviewFinding(Severity.BLOCKER, "src/bad.py", 42, "Hardcoded secret", "Security", "Fix it"),
            ],
            files_reviewed=1,
        )
        reviewer = CodeReviewer()
        result = reviewer.save_review(report)
        assert "BLOCKER" in result["content"]
        assert "Hardcoded secret" in result["content"]
        assert "FAILED" in result["content"]


# ---------------------------------------------------------------------------
# Format report
# ---------------------------------------------------------------------------


class TestFormatReport:
    """Tests for report formatting."""

    def test_format_report_contains_status(self):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(Severity.SUGGESTION, "f.py", 1, "ok", "reason", "fix"),
            ],
            files_reviewed=1,
        )
        text = CodeReviewer.format_report(report)
        assert "PASSED" in text
        assert "Code Review Report" in text

    def test_format_report_contains_findings(self):
        report = ReviewReport(
            status=ReviewStatus.FAILED,
            findings=[
                ReviewFinding(Severity.BLOCKER, "src/auth.py", 10, "Bad auth", "Security", "Fix"),
            ],
            files_reviewed=1,
        )
        text = CodeReviewer.format_report(report)
        assert "BLOCKER" in text
        assert "Bad auth" in text
        assert "src/auth.py" in text

    def test_format_report_shows_engram_status(self):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(Severity.SUGGESTION, "f.py", 1, "ok", "r", "fix"),
            ],
            files_reviewed=1,
            engram_context_used=True,
        )
        text = CodeReviewer.format_report(report)
        assert "Yes" in text  # Engram context used: Yes


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_review_files_function(self, tmp_path):
        (tmp_path / "test.py").write_text("x = 1\n")
        report = review_files(["test.py"], project_root=str(tmp_path))
        assert isinstance(report, ReviewReport)

    def test_review_diff_function(self):
        diff = "+++ b/test.py\n@@ -1 +1,2 @@\n x = 1\n+y = 2\n"
        report = review_diff(diff)
        assert isinstance(report, ReviewReport)

    def test_format_report_function(self):
        report = ReviewReport(
            status=ReviewStatus.PASSED,
            findings=[
                ReviewFinding(Severity.SUGGESTION, "f.py", 1, "ok", "r", "fix"),
            ],
            files_reviewed=1,
        )
        text = format_report(report)
        assert isinstance(text, str)
        assert "PASSED" in text


# ---------------------------------------------------------------------------
# Adversarial protocol enforcement
# ---------------------------------------------------------------------------


class TestAdversarialProtocol:
    """Tests verifying the adversarial review mandate."""

    def test_clean_file_still_has_finding(self, tmp_path):
        """Even perfectly clean code must produce at least one finding."""
        (tmp_path / "perfect.py").write_text("def add(a, b):\n    return a + b\n")
        reviewer = CodeReviewer(project_root=str(tmp_path))
        report = reviewer.review_files(["perfect.py"])
        assert len(report.findings) >= 1

    def test_clean_diff_still_has_finding(self):
        """Even a clean diff must produce at least one finding."""
        diff = "+++ b/clean.py\n@@ -1 +1 @@\n-old = 1\n+new = 1\n"
        reviewer = CodeReviewer()
        report = reviewer.review_diff(diff)
        assert len(report.findings) >= 1

    def test_enforce_adversarial_with_empty_list(self):
        """_enforce_adversarial should add a finding when list is empty."""
        result = CodeReviewer._enforce_adversarial([], ["test.py"])
        assert len(result) == 1
        assert result[0].severity == Severity.SUGGESTION

    def test_enforce_adversarial_preserves_existing(self):
        """_enforce_adversarial should not modify non-empty lists."""
        existing = [ReviewFinding(Severity.BLOCKER, "f.py", 1, "bad", "r", "fix")]
        result = CodeReviewer._enforce_adversarial(existing, ["f.py"])
        assert len(result) == 1
        assert result[0].severity == Severity.BLOCKER
