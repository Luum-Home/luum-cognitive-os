"""Unit tests for lib/ground_truth.py

Validates claim extraction, claim verification against filesystem,
hallucination score calculation, and report formatting.
"""

import os

import pytest

from lib.ground_truth import (
    Claim,
    VerificationResult,
    extract_claims,
    format_verification_report,
    verify_all_claims,
    verify_claim,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# extract_claims
# ---------------------------------------------------------------------------


class TestExtractClaims:
    """Tests for extract_claims()."""

    def test_finds_created_file(self):
        """Should detect 'Created file.py' pattern."""
        output = "Created src/auth.py with the new handler."
        claims = extract_claims(output)
        assert any(c.claim_type == "file_exists" and "auth.py" in c.target for c in claims)

    def test_finds_wrote_file(self):
        """Should detect 'Wrote file.go' pattern."""
        output = "Wrote internal/users/handler.go successfully."
        claims = extract_claims(output)
        assert any(c.claim_type == "file_exists" and "handler.go" in c.target for c in claims)

    def test_finds_modified_file(self):
        """Should detect 'Modified file.ts' pattern."""
        output = "Modified src/components/Button.tsx to add dark mode."
        claims = extract_claims(output)
        assert any(c.claim_type == "file_exists" and "Button.tsx" in c.target for c in claims)

    def test_finds_test_count_passing(self):
        """Should detect 'N tests passing' pattern."""
        output = "All 15 tests passing successfully."
        claims = extract_claims(output)
        assert any(
            c.claim_type == "count" and c.expected == "15" and c.target == "test_count"
            for c in claims
        )

    def test_finds_test_count_collected(self):
        """Should detect 'N tests collected' pattern."""
        output = "42 tests collected in 3.2s"
        claims = extract_claims(output)
        assert any(
            c.claim_type == "count" and c.expected == "42"
            for c in claims
        )

    def test_finds_modified_n_files(self):
        """Should detect 'Modified N files' pattern."""
        output = "Modified 7 files across the project."
        claims = extract_claims(output)
        assert any(
            c.claim_type == "count" and c.expected == "7" and c.target == "file_count"
            for c in claims
        )

    def test_finds_build_succeeded(self):
        """Should detect 'Build succeeded' pattern."""
        output = "Build succeeded with no errors."
        claims = extract_claims(output)
        assert any(c.claim_type == "command_output" and c.target == "build" for c in claims)

    def test_finds_lint_clean(self):
        """Should detect 'Lint clean' pattern."""
        output = "Lint clean, no issues found."
        claims = extract_claims(output)
        assert any(c.claim_type == "command_output" and c.target == "lint" for c in claims)

    def test_finds_no_errors(self):
        """Should detect 'No errors' / '0 errors' pattern."""
        output = "Compilation finished with 0 errors."
        claims = extract_claims(output)
        assert any(c.claim_type == "command_output" and c.target == "errors" for c in claims)

    def test_finds_function_in_file(self):
        """Should detect 'function X in file Y' pattern."""
        output = "Added function GetUserByID in internal/users/handler.go"
        claims = extract_claims(output)
        assert any(
            c.claim_type == "function_exists" and "GetUserByID" in c.target
            for c in claims
        )

    def test_ignores_non_claims(self):
        """Should not extract claims from regular prose."""
        output = "The architecture follows clean patterns. We use dependency injection."
        claims = extract_claims(output)
        # No file, count, or command claims should be found
        file_claims = [c for c in claims if c.claim_type == "file_exists"]
        assert len(file_claims) == 0

    def test_empty_output_returns_no_claims(self):
        """Should return empty list for empty output."""
        claims = extract_claims("")
        assert claims == []

    def test_deduplicates_file_claims(self):
        """Should not produce duplicate claims for the same file."""
        output = "Created src/auth.go. Then I updated src/auth.go with tests."
        claims = extract_claims(output)
        file_claims = [c for c in claims if c.claim_type == "file_exists" and "auth.go" in c.target]
        assert len(file_claims) == 1

    def test_handles_backtick_paths(self):
        """Should handle file paths wrapped in backticks."""
        output = "Created `lib/helper.py` with utility functions."
        claims = extract_claims(output)
        assert any(c.claim_type == "file_exists" and "helper.py" in c.target for c in claims)

    def test_handles_quoted_paths(self):
        """Should handle file paths wrapped in quotes."""
        output = 'Created "lib/helper.py" with utility functions.'
        claims = extract_claims(output)
        assert any(c.claim_type == "file_exists" and "helper.py" in c.target for c in claims)


# ---------------------------------------------------------------------------
# verify_claim
# ---------------------------------------------------------------------------


class TestVerifyClaim:
    """Tests for verify_claim()."""

    def test_file_exists_true(self, tmp_path):
        """Should verify file exists when it actually does."""
        test_file = tmp_path / "existing.py"
        test_file.write_text("print('hello')\n")

        claim = Claim(text="Created existing.py", claim_type="file_exists", target="existing.py")
        result = verify_claim(claim, str(tmp_path))
        assert result.verified is True
        assert "exists" in result.actual.lower()

    def test_file_exists_false_hallucination(self, tmp_path):
        """Should detect hallucination when file does not exist."""
        claim = Claim(
            text="Created nonexistent.py",
            claim_type="file_exists",
            target="nonexistent.py",
        )
        result = verify_claim(claim, str(tmp_path))
        assert result.verified is False
        assert result.discrepancy is not None
        assert "does not exist" in result.discrepancy.lower()

    def test_function_exists_true(self, tmp_path):
        """Should verify function exists when it does."""
        test_file = tmp_path / "handler.py"
        test_file.write_text("def get_user():\n    return None\n")

        claim = Claim(
            text="Function get_user in handler.py",
            claim_type="function_exists",
            target="handler.py:get_user",
        )
        result = verify_claim(claim, str(tmp_path))
        assert result.verified is True

    def test_function_exists_false(self, tmp_path):
        """Should detect when function does not exist."""
        test_file = tmp_path / "handler.py"
        test_file.write_text("def other_func():\n    pass\n")

        claim = Claim(
            text="Function missing_func in handler.py",
            claim_type="function_exists",
            target="handler.py:missing_func",
        )
        result = verify_claim(claim, str(tmp_path))
        assert result.verified is False

    def test_count_test_unverifiable(self, tmp_path):
        """Count claims for tests should be marked unverifiable."""
        claim = Claim(text="15 tests passing", claim_type="count", target="test_count", expected="15")
        result = verify_claim(claim, str(tmp_path))
        assert result.verified is False
        assert result.discrepancy is None  # unverifiable, not a hallucination

    def test_command_output_unverifiable(self, tmp_path):
        """Command output claims should be marked unverifiable."""
        claim = Claim(
            text="Build succeeded",
            claim_type="command_output",
            target="build",
            expected="success",
        )
        result = verify_claim(claim, str(tmp_path))
        assert result.verified is False
        assert result.discrepancy is None


# ---------------------------------------------------------------------------
# verify_all_claims
# ---------------------------------------------------------------------------


class TestVerifyAllClaims:
    """Tests for verify_all_claims()."""

    def test_mixed_results(self, tmp_path):
        """Should handle mix of verified and hallucinated claims."""
        # Create one real file
        real_file = tmp_path / "real.py"
        real_file.write_text("x = 1\n")

        output = "Created real.py and also created fake.py"
        results = verify_all_claims(output, str(tmp_path))

        assert results["total"] >= 2
        assert results["verified"] >= 1
        assert results["failed"] >= 1

    def test_hallucination_score_all_true(self, tmp_path):
        """Hallucination score should be 0.0 when all claims are true."""
        real = tmp_path / "exists.go"
        real.write_text("package main\n")

        output = "Created exists.go"
        results = verify_all_claims(output, str(tmp_path))

        assert results["hallucination_score"] == 0.0

    def test_hallucination_score_all_false(self, tmp_path):
        """Hallucination score should be 1.0 when all verifiable claims are false."""
        output = "Created nonexistent_a.py and created nonexistent_b.py"
        results = verify_all_claims(output, str(tmp_path))

        if results["failed"] > 0:
            assert results["hallucination_score"] == 1.0

    def test_hallucination_score_calculation(self, tmp_path):
        """Hallucination score should be failed/verifiable."""
        real = tmp_path / "one.py"
        real.write_text("a = 1\n")

        output = "Created one.py and created two.py and created three.py"
        results = verify_all_claims(output, str(tmp_path))

        verifiable = results["verified"] + results["failed"]
        if verifiable > 0:
            expected_score = round(results["failed"] / verifiable, 4)
            assert results["hallucination_score"] == expected_score

    def test_empty_output(self, tmp_path):
        """Empty output should return zero claims."""
        results = verify_all_claims("", str(tmp_path))
        assert results["total"] == 0
        assert results["verified"] == 0
        assert results["failed"] == 0
        assert results["hallucination_score"] == 0.0


# ---------------------------------------------------------------------------
# format_verification_report
# ---------------------------------------------------------------------------


class TestFormatReport:
    """Tests for format_verification_report()."""

    def test_report_has_table(self, tmp_path):
        """Report should contain a markdown table."""
        real = tmp_path / "file.go"
        real.write_text("package main\n")

        results = verify_all_claims("Created file.go", str(tmp_path))
        report = format_verification_report(results)

        assert "| Claim" in report
        assert "| Type" in report
        assert "Hallucination Score" in report

    def test_report_empty_output(self):
        """Report for empty output should note no claims."""
        results = verify_all_claims("", "/tmp")
        report = format_verification_report(results)
        assert "No verifiable claims" in report

    def test_report_shows_pass_and_fail(self, tmp_path):
        """Report should show both PASS and FAIL statuses."""
        real = tmp_path / "good.py"
        real.write_text("pass\n")

        results = verify_all_claims("Created good.py and created bad.py", str(tmp_path))
        report = format_verification_report(results)

        assert "PASS" in report
        assert "FAIL" in report


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases for ground truth verification."""

    def test_relative_vs_absolute_paths(self, tmp_path):
        """Should handle both relative and absolute paths."""
        subdir = tmp_path / "src"
        subdir.mkdir()
        target = subdir / "app.py"
        target.write_text("x = 1\n")

        # Relative path
        claim_rel = Claim(text="Created src/app.py", claim_type="file_exists", target="src/app.py")
        result_rel = verify_claim(claim_rel, str(tmp_path))
        assert result_rel.verified is True

        # Absolute path
        claim_abs = Claim(
            text="Created %s" % str(target),
            claim_type="file_exists",
            target=str(target),
        )
        result_abs = verify_claim(claim_abs, str(tmp_path))
        assert result_abs.verified is True

    def test_path_with_dots(self, tmp_path):
        """Should handle paths with dots in directory names."""
        dotdir = tmp_path / "v1.0"
        dotdir.mkdir()
        target = dotdir / "config.yaml"
        target.write_text("key: value\n")

        claim = Claim(text="Created v1.0/config.yaml", claim_type="file_exists", target="v1.0/config.yaml")
        result = verify_claim(claim, str(tmp_path))
        assert result.verified is True

    def test_nonexistent_project_root(self):
        """Should handle nonexistent project root gracefully."""
        claim = Claim(text="Created file.py", claim_type="file_exists", target="file.py")
        result = verify_claim(claim, "/nonexistent/path/12345")
        assert result.verified is False
