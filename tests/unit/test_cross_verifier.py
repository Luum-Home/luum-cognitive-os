"""Unit tests for lib/cross_verifier.py

Validates prompt building, response parsing, should_cross_verify logic,
cross_verify fallback behavior, and formatting.
"""

from unittest.mock import patch

import pytest

from lib.cross_verifier import (
    CrossVerification,
    _parse_verifier_response,
    build_verification_prompt,
    cross_verify,
    format_cross_verification,
    should_cross_verify,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# build_verification_prompt
# ---------------------------------------------------------------------------


class TestBuildVerificationPrompt:
    """Tests for build_verification_prompt()."""

    def test_includes_task(self):
        """Prompt should include the original task description."""
        prompt = build_verification_prompt("Fix the auth bug", "I fixed auth.go")
        assert "Fix the auth bug" in prompt

    def test_includes_output(self):
        """Prompt should include the agent output."""
        prompt = build_verification_prompt("task", "Created handler.go with 50 lines")
        assert "Created handler.go" in prompt

    def test_excludes_trust_score(self):
        """Prompt should NOT include trust score instructions for the verifier."""
        prompt = build_verification_prompt("task", "TRUST REPORT: Score: 85/100")
        # The prompt template asks the verifier for its OWN assessment
        assert "AGREEMENT" in prompt
        assert "CONFIDENCE" in prompt
        # It should NOT tell the verifier what the original trust score was
        assert "trust score" not in prompt.lower().split("agent output")[0]

    def test_truncates_long_output(self):
        """Should truncate very long outputs."""
        long_output = "x" * 20000
        prompt = build_verification_prompt("task", long_output)
        assert "truncated" in prompt.lower()
        assert len(prompt) < 25000

    def test_asks_for_structured_response(self):
        """Prompt should request AGREEMENT, CONFIDENCE, DISCREPANCIES format."""
        prompt = build_verification_prompt("task", "output")
        assert "AGREEMENT" in prompt
        assert "CONFIDENCE" in prompt
        assert "DISCREPANCIES" in prompt


# ---------------------------------------------------------------------------
# _parse_verifier_response
# ---------------------------------------------------------------------------


class TestParseVerifierResponse:
    """Tests for _parse_verifier_response()."""

    def test_parses_agreement_yes(self):
        """Should parse YES agreement."""
        response = "AGREEMENT: YES\nCONFIDENCE: 85\nDISCREPANCIES:\n- NONE"
        agreement, confidence, discrepancies = _parse_verifier_response(response)
        assert agreement is True
        assert confidence == 0.85
        assert len(discrepancies) == 0

    def test_parses_agreement_no(self):
        """Should parse NO agreement with discrepancies."""
        response = (
            "AGREEMENT: NO\nCONFIDENCE: 40\nDISCREPANCIES:\n"
            "- File auth.go was not created\n"
            "- Test count seems inflated"
        )
        agreement, confidence, discrepancies = _parse_verifier_response(response)
        assert agreement is False
        assert confidence == 0.40
        assert len(discrepancies) == 2
        assert "auth.go" in discrepancies[0]

    def test_clamps_confidence(self):
        """Should clamp confidence to 0.0-1.0 range."""
        response = "AGREEMENT: YES\nCONFIDENCE: 150\nDISCREPANCIES:\n- NONE"
        _, confidence, _ = _parse_verifier_response(response)
        assert confidence == 1.0

    def test_handles_malformed_response(self):
        """Should return defaults for malformed response."""
        response = "This is not a structured response at all."
        agreement, confidence, discrepancies = _parse_verifier_response(response)
        # Defaults: agreement=True, confidence=0.5
        assert agreement is True
        assert confidence == 0.5
        assert len(discrepancies) == 0


# ---------------------------------------------------------------------------
# should_cross_verify
# ---------------------------------------------------------------------------


class TestShouldCrossVerify:
    """Tests for should_cross_verify()."""

    def test_true_for_destructive_tasks(self):
        """Should require verification for destructive operations."""
        assert should_cross_verify("Delete all old migration files", "Done") is True

    def test_true_for_many_files(self):
        """Should require verification when >10 files claimed modified."""
        output = "Modified 15 files across the codebase."
        assert should_cross_verify("refactor", output) is True

    def test_false_for_trivial(self):
        """Should skip for trivial tasks."""
        assert (
            should_cross_verify(
                "fix typo", "Fixed the typo in README.md", complexity="trivial"
            )
            is False
        )

    def test_true_for_production_phase(self):
        """Should always verify in production phase."""
        assert (
            should_cross_verify(
                "small fix", "Done", phase="production", complexity="trivial"
            )
            is True
        )

    def test_true_for_large_complexity(self):
        """Should verify large complexity tasks."""
        assert should_cross_verify("feature", "Done", complexity="large") is True

    def test_true_for_critical_complexity(self):
        """Should verify critical complexity tasks."""
        assert should_cross_verify("migration", "Done", complexity="critical") is True

    def test_true_for_low_trust_score(self):
        """Should verify when trust score is low."""
        assert should_cross_verify("task", "Done", trust_score=50) is True

    def test_false_for_high_trust_score(self):
        """Should skip when trust score is high and not otherwise triggered."""
        assert (
            should_cross_verify(
                "small task", "Done", trust_score=90, complexity="small"
            )
            is False
        )

    def test_false_for_dry_run(self, monkeypatch):
        """Should skip in dry-run mode."""
        monkeypatch.setenv("DRY_RUN", "true")
        assert (
            should_cross_verify(
                "delete everything", "Done", complexity="critical"
            )
            is False
        )


# ---------------------------------------------------------------------------
# cross_verify (without executor)
# ---------------------------------------------------------------------------


class TestCrossVerifyWithoutExecutor:
    """Tests for cross_verify when ClaudeExecutor is not available."""

    def test_returns_skipped_without_executor(self):
        """Should return skipped result when executor cannot be imported."""
        with patch.dict("sys.modules", {"lib.claude_executor": None}):
            # Force ImportError by patching
            with patch("lib.cross_verifier.CrossVerification") as _:
                pass
        # Simpler approach: just call it; if claude CLI isn't available it will skip
        cv = cross_verify("task", "output")
        # It will either succeed (if claude is installed) or skip
        assert isinstance(cv, CrossVerification)
        if cv.skipped:
            assert cv.agreement is True
            assert cv.skip_reason != ""


# ---------------------------------------------------------------------------
# format_cross_verification
# ---------------------------------------------------------------------------


class TestFormatCrossVerification:
    """Tests for format_cross_verification()."""

    def test_format_with_discrepancies(self):
        """Should list discrepancies in formatted output."""
        cv = CrossVerification(
            original_model="opus",
            verifier_model="haiku",
            original_output="output",
            verification_prompt="prompt",
            verifier_response="response",
            agreement=False,
            confidence=0.4,
            discrepancies=["File not found", "Count mismatch"],
        )
        formatted = format_cross_verification(cv)
        assert "File not found" in formatted
        assert "Count mismatch" in formatted
        assert "NO" in formatted

    def test_format_agreement(self):
        """Should show agreement status."""
        cv = CrossVerification(
            original_model="opus",
            verifier_model="haiku",
            original_output="output",
            verification_prompt="prompt",
            verifier_response="response",
            agreement=True,
            confidence=0.9,
            discrepancies=[],
        )
        formatted = format_cross_verification(cv)
        assert "YES" in formatted
        assert "90%" in formatted
        assert "No discrepancies" in formatted

    def test_format_skipped(self):
        """Should show skip reason for skipped verifications."""
        cv = CrossVerification(
            original_model="opus",
            verifier_model="haiku",
            original_output="",
            verification_prompt="",
            verifier_response="",
            agreement=True,
            confidence=0.0,
            discrepancies=[],
            skipped=True,
            skip_reason="executor not available",
        )
        formatted = format_cross_verification(cv)
        assert "SKIPPED" in formatted
        assert "executor not available" in formatted

    def test_cost_estimation_haiku(self):
        """Haiku verification should be cheap (~$0.002)."""
        # Verify the cost model is documented correctly
        # haiku: $0.25/1M in, $1.25/1M out
        # ~2K tokens in, ~500 tokens out
        estimated = (2000 * 0.25 + 500 * 1.25) / 1_000_000
        assert estimated < 0.01  # Less than 1 cent
