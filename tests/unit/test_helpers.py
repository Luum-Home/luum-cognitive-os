"""Smoke tests for tests/unit/_helpers.py.

Verifies that the helper functions work as expected before relying on
them in the actual test suite.
"""
import time

import pytest

from tests.unit._helpers import (
    assert_all_concepts_present,
    assert_faster_than_baseline,
    assert_preamble_contains_concepts,
    assert_within_absolute,
    VALKEY_AVAILABLE,
    BASH_AVAILABLE,
    requires_valkey,
    requires_bash,
    skip_when_valkey_running,
)


class TestAssertPreambleContainsConcepts:
    def test_passes_when_any_concept_present(self):
        assert_preamble_contains_concepts(
            "## Escalation Protocol — use ESCALATION: marker",
            ["Escalation Protocol", "ESCALATION:"],
        )

    def test_passes_with_different_case(self):
        assert_preamble_contains_concepts(
            "preserve exactly: code blocks",
            ["PRESERVE EXACTLY"],  # upper-case check on lower-case text
        )

    def test_passes_when_only_second_concept_present(self):
        assert_preamble_contains_concepts(
            "Output Compression rules apply here",
            ["## Output Compression", "Output Compression"],
        )

    def test_fails_when_no_concept_present(self):
        with pytest.raises(AssertionError, match="None of the expected concepts"):
            assert_preamble_contains_concepts(
                "This text has nothing relevant",
                ["missing_concept", "also_missing"],
            )

    def test_empty_text_fails(self):
        with pytest.raises(AssertionError):
            assert_preamble_contains_concepts("", ["something"])

    def test_empty_concepts_list_with_empty_text(self):
        # Empty concept list: trivially passes (no concepts to find)
        assert_preamble_contains_concepts("anything", [])


class TestAssertAllConceptsPresent:
    def test_passes_when_all_present(self):
        assert_all_concepts_present(
            "loop_detected no_progress error_repeat severity suggest",
            ["loop_detected", "no_progress", "error_repeat"],
        )

    def test_fails_when_one_missing(self):
        with pytest.raises(AssertionError, match="Missing concepts"):
            assert_all_concepts_present(
                "loop_detected no_progress",
                ["loop_detected", "no_progress", "error_repeat"],
            )

    def test_case_insensitive(self):
        assert_all_concepts_present(
            "SUGGEST RECOMMEND URGENT",
            ["suggest", "recommend", "urgent"],
        )


class TestAssertFasterThanBaseline:
    def test_fast_function_passes(self):
        def fast():
            time.sleep(0.01)  # 10ms

        elapsed = assert_faster_than_baseline(fast, factor=10.0)
        assert elapsed < 1.0

    def test_slow_function_fails(self):
        call_count = [0]

        def alternating():
            call_count[0] += 1
            if call_count[0] == 1:
                time.sleep(0.01)   # baseline: 10ms
            else:
                time.sleep(1.0)    # measured: 1000ms >> 3× baseline

        with pytest.raises(AssertionError, match="exceeds"):
            assert_faster_than_baseline(alternating, factor=3.0)


class TestAssertWithinAbsolute:
    def test_passes_within_limit(self):
        assert_within_absolute(0.5, limit_s=1.0, slack_factor=1.5)

    def test_passes_at_exact_slack_boundary(self):
        # 0.99 < 1.0 * 1.5 = 1.5 → passes
        assert_within_absolute(0.99, limit_s=1.0, slack_factor=1.5)

    def test_fails_over_slack_limit(self):
        with pytest.raises(AssertionError, match="Elapsed"):
            assert_within_absolute(2.0, limit_s=1.0, slack_factor=1.5)  # 2.0 > 1.5


class TestMarkerAvailability:
    def test_valkey_available_is_bool(self):
        assert isinstance(VALKEY_AVAILABLE, bool)

    def test_bash_available_is_bool(self):
        assert isinstance(BASH_AVAILABLE, bool)

    def test_bash_is_available(self):
        # bash is available on all our CI platforms
        assert BASH_AVAILABLE, "bash should be on PATH in test environments"

    def test_skip_when_valkey_running_is_marker(self):
        # Just ensure it is importable and is a pytest mark
        assert skip_when_valkey_running is not None
