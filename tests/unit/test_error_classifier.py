"""Unit tests for lib/error_classifier.py

Validates:
  1. Text/exit-code classifier (original): classify_error, get_retry_strategy, format_classified_error
  2. JSONL taxonomy layer (ADR-080 Tier 2 #6): classify(), classify_jsonl(), ErrorClass, ClassifiedError
"""

import json

import pytest

from lib.error_classifier import (
    # Original text-classifier API
    ErrorCategory,
    classify_error,
    format_classified_error,
    get_retry_strategy,
    # JSONL taxonomy API (ADR-080 Tier 2 #6)
    ClassifiedError,
    RecordCategory,
    RecordSeverity,
    Transience,
    classify,
    classify_jsonl,
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


# ---------------------------------------------------------------------------
# JSONL taxonomy layer — classify() (ADR-080 Tier 2 #6)
# ---------------------------------------------------------------------------


class TestClassifyRecord:
    """Tests for the JSONL record-level classify() API."""

    def _record(self, **kwargs):
        base = {"timestamp": "2026-04-30T00:00:00Z", "timestamp_epoch": 1777000000}
        base.update(kwargs)
        return base

    # Fast-path: TYPE field
    def test_type_test_failure(self):
        rec = self._record(type="TEST_FAILURE", command="go test ./...", exit_code=1)
        result = classify(rec)
        assert result.category is RecordCategory.test_failure
        assert result.severity is RecordSeverity.high
        assert result.transient is Transience.no

    def test_type_lint_error(self):
        result = classify(self._record(type="LINT_ERROR", command="golangci-lint run"))
        assert result.category is RecordCategory.lint_error

    def test_type_build_error(self):
        result = classify(self._record(type="BUILD_ERROR", command="go build ./..."))
        assert result.category is RecordCategory.build_error
        assert result.severity is RecordSeverity.critical

    def test_type_network_error(self):
        result = classify(self._record(type="NETWORK_ERROR"))
        assert result.category is RecordCategory.network

    def test_type_timeout(self):
        result = classify(self._record(type="TIMEOUT"))
        assert result.category is RecordCategory.timeout
        assert result.transient is Transience.yes

    def test_type_auth_error(self):
        result = classify(self._record(type="AUTH_ERROR"))
        assert result.category is RecordCategory.auth
        assert result.severity is RecordSeverity.critical
        assert result.transient is Transience.no

    def test_type_rate_limit(self):
        result = classify(self._record(type="RATE_LIMIT"))
        assert result.category is RecordCategory.rate_limit
        assert result.transient is Transience.yes

    # Pattern-based: TYPE is unknown, fall through to message matching
    def test_message_rate_limit(self):
        rec = self._record(type="UNKNOWN_TYPE", command="curl ... rate limit exceeded")
        result = classify(rec)
        assert result.category is RecordCategory.rate_limit

    def test_message_timeout(self):
        rec = self._record(type="UNKNOWN_TYPE", command="curl ...", message="operation timed out")
        result = classify(rec)
        assert result.category is RecordCategory.timeout

    def test_message_permission(self):
        rec = self._record(command="chmod 000 /etc/hosts && cat /etc/hosts", message="permission denied")
        result = classify(rec)
        assert result.category is RecordCategory.permission

    def test_message_file_not_found(self):
        rec = self._record(command="ls /nonexistent", message="no such file or directory")
        result = classify(rec)
        assert result.category is RecordCategory.file_not_found

    def test_message_network(self):
        rec = self._record(command="curl http://x", message="connection refused")
        result = classify(rec)
        assert result.category is RecordCategory.network

    def test_message_context_overflow(self):
        rec = self._record(command="llm call", message="context window exceeded")
        result = classify(rec)
        assert result.category is RecordCategory.context_overflow

    def test_message_auth(self):
        rec = self._record(command="api call", message="unauthorized: invalid token")
        result = classify(rec)
        assert result.category is RecordCategory.auth

    # Edge cases
    def test_empty_record(self):
        result = classify({})
        assert result.category is RecordCategory.unknown

    def test_record_no_useful_fields(self):
        result = classify({"fingerprint": "abc123", "exit_code": 1})
        assert result.category is RecordCategory.unknown

    def test_suggested_action_present(self):
        result = classify({"type": "TEST_FAILURE", "command": "pytest"})
        assert isinstance(result.suggested_action, str)
        assert len(result.suggested_action) > 0

    def test_as_dict_passthrough(self):
        rec = {"type": "TEST_FAILURE", "fingerprint": "abc", "timestamp_epoch": 100}
        result = classify(rec)
        d = result.as_dict()
        assert d["category"] == "test_failure"
        assert d["fingerprint"] == "abc"

    def test_raw_preserved(self):
        rec = {"type": "LINT_ERROR", "command": "eslint .", "service": "frontend"}
        result = classify(rec)
        assert result.raw.get("service") == "frontend"


class TestClassifyJsonl:
    """Tests for classify_jsonl()."""

    def _write_jsonl(self, records, path):
        with open(path, "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

    def test_bulk_classifies_all_records(self, tmp_path):
        records = [
            {"type": "TEST_FAILURE", "timestamp_epoch": 1000},
            {"type": "LINT_ERROR", "timestamp_epoch": 1001},
            {"type": "BUILD_ERROR", "timestamp_epoch": 1002},
        ]
        p = tmp_path / "error-learning.jsonl"
        self._write_jsonl(records, p)
        result = classify_jsonl(p)
        assert len(result) == 3
        assert result[0].category is RecordCategory.test_failure
        assert result[1].category is RecordCategory.lint_error
        assert result[2].category is RecordCategory.build_error

    def test_skips_malformed_lines(self, tmp_path):
        p = tmp_path / "errors.jsonl"
        with open(p, "w") as f:
            f.write('{"type": "TEST_FAILURE"}\n')
            f.write("NOT JSON\n")
            f.write('{"type": "LINT_ERROR"}\n')
        result = classify_jsonl(p)
        assert len(result) == 2

    def test_skips_empty_lines(self, tmp_path):
        p = tmp_path / "errors.jsonl"
        with open(p, "w") as f:
            f.write('{"type": "TEST_FAILURE"}\n')
            f.write("\n")
            f.write("   \n")
        result = classify_jsonl(p)
        assert len(result) == 1

    def test_empty_file(self, tmp_path):
        p = tmp_path / "errors.jsonl"
        p.write_text("")
        result = classify_jsonl(p)
        assert result == []

    def test_missing_file(self, tmp_path):
        p = tmp_path / "nonexistent.jsonl"
        result = classify_jsonl(p)
        assert result == []

    def test_single_record(self, tmp_path):
        p = tmp_path / "errors.jsonl"
        self._write_jsonl([{"type": "AUTH_ERROR"}], p)
        result = classify_jsonl(p)
        assert len(result) == 1
        assert result[0].category is RecordCategory.auth

    def test_classified_error_accessors(self, tmp_path):
        p = tmp_path / "errors.jsonl"
        self._write_jsonl([
            {"type": "TEST_FAILURE", "fingerprint": "abc123", "timestamp_epoch": 9999},
        ], p)
        ce = classify_jsonl(p)[0]
        assert isinstance(ce, ClassifiedError)
        assert ce.fingerprint == "abc123"
        assert ce.timestamp_epoch == 9999.0
        assert ce.error_type == "TEST_FAILURE"

    def test_large_file_performance(self, tmp_path):
        """classify_jsonl should handle 1000+ records without error."""
        records = [
            {"type": "TEST_FAILURE", "fingerprint": f"fp{i}", "timestamp_epoch": 1000 + i}
            for i in range(1200)
        ]
        p = tmp_path / "large.jsonl"
        self._write_jsonl(records, p)
        result = classify_jsonl(p)
        assert len(result) == 1200
        assert all(ce.category is RecordCategory.test_failure for ce in result)
