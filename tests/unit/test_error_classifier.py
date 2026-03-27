"""Unit tests for lib/error_classifier.py

Validates error classification across all categories, retry strategies,
and formatted output.
"""

import pytest

from lib.error_classifier import (
    ErrorCategory,
    classify_error,
    format_classified_error,
    get_retry_strategy,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# classify_error — auth
# ---------------------------------------------------------------------------


class TestClassifyAuth:
    """Tests for AUTH error classification."""

    def test_401_status(self):
        """Should classify 401 Unauthorized as AUTH."""
        assert classify_error("HTTP 401 Unauthorized") == ErrorCategory.AUTH

    def test_403_forbidden(self):
        """Should classify 403 Forbidden as AUTH."""
        assert classify_error("Error: 403 Forbidden") == ErrorCategory.AUTH

    def test_unauthorized_text(self):
        """Should classify 'unauthorized' keyword as AUTH."""
        assert classify_error("Request unauthorized: invalid token") == ErrorCategory.AUTH

    def test_invalid_api_key(self):
        """Should classify invalid API key as AUTH."""
        assert classify_error("invalid api key provided") == ErrorCategory.AUTH


# ---------------------------------------------------------------------------
# classify_error — rate_limit
# ---------------------------------------------------------------------------


class TestClassifyRateLimit:
    """Tests for RATE_LIMIT error classification."""

    def test_429_status(self):
        """Should classify 429 as RATE_LIMIT."""
        assert classify_error("HTTP 429 Too Many Requests") == ErrorCategory.RATE_LIMIT

    def test_rate_limit_text(self):
        """Should classify rate limit message as RATE_LIMIT."""
        assert classify_error("rate limit exceeded, retry after 60s") == ErrorCategory.RATE_LIMIT

    def test_too_many_requests(self):
        """Should classify 'too many requests' as RATE_LIMIT."""
        assert classify_error("Error: too many requests") == ErrorCategory.RATE_LIMIT


# ---------------------------------------------------------------------------
# classify_error — context_overflow
# ---------------------------------------------------------------------------


class TestClassifyContextOverflow:
    """Tests for CONTEXT_OVERFLOW classification."""

    def test_context_exceeded(self):
        """Should classify context window exceeded as CONTEXT_OVERFLOW."""
        assert classify_error("context window exceeded") == ErrorCategory.CONTEXT_OVERFLOW

    def test_token_limit(self):
        """Should classify token limit as CONTEXT_OVERFLOW."""
        assert classify_error("token limit exceeded: max 200000") == ErrorCategory.CONTEXT_OVERFLOW


# ---------------------------------------------------------------------------
# classify_error — build_failure
# ---------------------------------------------------------------------------


class TestClassifyBuildFailure:
    """Tests for BUILD_FAILURE classification."""

    def test_build_failed(self):
        """Should classify 'build failed' as BUILD_FAILURE."""
        assert classify_error("FATAL: build failed with 3 errors") == ErrorCategory.BUILD_FAILURE

    def test_compilation_error(self):
        """Should classify compilation error as BUILD_FAILURE."""
        assert classify_error("compilation error in main.go:42") == ErrorCategory.BUILD_FAILURE

    def test_module_not_found(self):
        """Should classify module not found as BUILD_FAILURE."""
        assert classify_error("cannot find module 'react'") == ErrorCategory.BUILD_FAILURE


# ---------------------------------------------------------------------------
# classify_error — test_failure
# ---------------------------------------------------------------------------


class TestClassifyTestFailure:
    """Tests for TEST_FAILURE classification."""

    def test_fail_keyword(self):
        """Should classify FAIL as TEST_FAILURE."""
        assert classify_error("--- FAIL: TestGetUser (0.01s)") == ErrorCategory.TEST_FAILURE

    def test_assertion_error(self):
        """Should classify assertion error as TEST_FAILURE."""
        assert classify_error("AssertionError: expected 5 but got 3") == ErrorCategory.TEST_FAILURE

    def test_tests_failed(self):
        """Should classify 'tests failed' as TEST_FAILURE."""
        assert classify_error("12 tests failed, 40 passed") == ErrorCategory.TEST_FAILURE


# ---------------------------------------------------------------------------
# classify_error — network
# ---------------------------------------------------------------------------


class TestClassifyNetwork:
    """Tests for NETWORK classification."""

    def test_connection_refused(self):
        """Should classify connection refused as NETWORK."""
        assert classify_error("ECONNREFUSED: connection refused") == ErrorCategory.NETWORK

    def test_econnreset(self):
        """Should classify ECONNRESET as NETWORK."""
        assert classify_error("Error: ECONNRESET socket hang up") == ErrorCategory.NETWORK


# ---------------------------------------------------------------------------
# classify_error — unknown / edge cases
# ---------------------------------------------------------------------------


class TestClassifyUnknown:
    """Tests for UNKNOWN and edge case classification."""

    def test_random_text(self):
        """Should classify unrecognizable text as UNKNOWN."""
        assert classify_error("something weird happened xyz") == ErrorCategory.UNKNOWN

    def test_empty_text_no_exit_code(self):
        """Should classify empty input as UNKNOWN."""
        assert classify_error("") == ErrorCategory.UNKNOWN

    def test_exit_code_126_permission(self):
        """Should classify exit code 126 as PERMISSION."""
        assert classify_error("", exit_code=126) == ErrorCategory.PERMISSION

    def test_exit_code_127_not_found(self):
        """Should classify exit code 127 as NOT_FOUND."""
        assert classify_error("", exit_code=127) == ErrorCategory.NOT_FOUND


# ---------------------------------------------------------------------------
# get_retry_strategy
# ---------------------------------------------------------------------------


class TestGetRetryStrategy:
    """Tests for get_retry_strategy()."""

    def test_retryable_rate_limit(self):
        """Should return retryable=True for RATE_LIMIT."""
        strategy = get_retry_strategy(ErrorCategory.RATE_LIMIT)
        assert strategy["retryable"] is True
        assert strategy["max_retries"] > 0
        assert strategy["backoff"] == "exponential"

    def test_non_retryable_auth(self):
        """Should return retryable=False for AUTH."""
        strategy = get_retry_strategy(ErrorCategory.AUTH)
        assert strategy["retryable"] is False
        assert strategy["max_retries"] == 0

    def test_non_retryable_build(self):
        """Should return retryable=False for BUILD_FAILURE."""
        strategy = get_retry_strategy(ErrorCategory.BUILD_FAILURE)
        assert strategy["retryable"] is False

    def test_retryable_timeout(self):
        """Should return retryable=True for TIMEOUT."""
        strategy = get_retry_strategy(ErrorCategory.TIMEOUT)
        assert strategy["retryable"] is True

    def test_strategy_has_action(self):
        """Every strategy should include an action description."""
        for category in ErrorCategory:
            strategy = get_retry_strategy(category)
            assert "action" in strategy
            assert isinstance(strategy["action"], str)
            assert len(strategy["action"]) > 0


# ---------------------------------------------------------------------------
# format_classified_error
# ---------------------------------------------------------------------------


class TestFormatClassifiedError:
    """Tests for format_classified_error()."""

    def test_format_includes_category_prefix(self):
        """Should prefix the error text with the category label."""
        result = format_classified_error("401 Unauthorized", ErrorCategory.AUTH)
        assert result.startswith("[AUTH]")
        assert "401 Unauthorized" in result

    def test_format_truncates_long_text(self):
        """Should truncate error text longer than 500 chars."""
        long_text = "x" * 600
        result = format_classified_error(long_text, ErrorCategory.UNKNOWN)
        assert result.endswith("...")
        assert len(result) < 520  # prefix + 500 + "..."

    def test_format_network(self):
        """Should format NETWORK errors with correct prefix."""
        result = format_classified_error("ECONNREFUSED", ErrorCategory.NETWORK)
        assert result == "[NETWORK] ECONNREFUSED"
