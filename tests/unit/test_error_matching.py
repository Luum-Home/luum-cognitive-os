"""Tests for lib/error_matching.py — error signature matching."""

import sys
import os

# Ensure lib is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lib.error_matching import (
    normalize_signature,
    calculate_similarity,
    find_matching_error,
    extract_error_signature,
)


# ── normalize_signature ──────────────────────────────────────────────────────


class TestNormalizeSignature:
    def test_normalize_strips_numbers(self) -> None:
        result = normalize_signature("error on line 42 column 7")
        assert "42" not in result
        assert "7" not in result
        assert "error" in result
        assert "line" in result

    def test_normalize_strips_paths(self) -> None:
        result = normalize_signature(
            "failed to open /usr/local/bin/myapp: no such file"
        )
        assert "/usr/local/bin/myapp" not in result
        assert "failed" in result
        assert "open" in result

    def test_normalize_truncates(self) -> None:
        long_text = "error " * 100  # 600 chars
        result = normalize_signature(long_text)
        assert len(result) <= 200

    def test_normalize_strips_timestamps(self) -> None:
        result = normalize_signature(
            "2026-03-27T12:00:00Z error: connection refused"
        )
        assert "2026" not in result
        assert "connection refused" in result

    def test_normalize_strips_uuids(self) -> None:
        result = normalize_signature(
            "user 550e8400-e29b-41d4-a716-446655440000 not found"
        )
        assert "550e8400" not in result
        assert "user" in result
        assert "not found" in result

    def test_normalize_strips_hex(self) -> None:
        result = normalize_signature("panic at address 0x7fff5fbff8c0")
        assert "0x7fff5fbff8c0" not in result
        assert "panic" in result

    def test_normalize_empty_string(self) -> None:
        assert normalize_signature("") == ""

    def test_normalize_lowercases(self) -> None:
        result = normalize_signature("ERROR: Connection REFUSED")
        assert result == result.lower()


# ── calculate_similarity ─────────────────────────────────────────────────────


class TestCalculateSimilarity:
    def test_similarity_identical(self) -> None:
        sig = "error connection refused to database"
        assert calculate_similarity(sig, sig) == 1.0

    def test_similarity_completely_different(self) -> None:
        sig_a = "alpha bravo charlie"
        sig_b = "delta echo foxtrot"
        assert calculate_similarity(sig_a, sig_b) == 0.0

    def test_similarity_partial_overlap(self) -> None:
        sig_a = "error connection refused"
        sig_b = "error connection timeout"
        score = calculate_similarity(sig_a, sig_b)
        # "error" and "connection" overlap (2 of 4 unique words)
        assert 0.0 < score < 1.0
        # Jaccard: intersection=2, union=4 -> 0.5
        assert abs(score - 0.5) < 0.01

    def test_similarity_empty_both(self) -> None:
        assert calculate_similarity("", "") == 1.0

    def test_similarity_one_empty(self) -> None:
        assert calculate_similarity("error", "") == 0.0
        assert calculate_similarity("", "error") == 0.0


# ── find_matching_error ──────────────────────────────────────────────────────


class TestFindMatchingError:
    def test_find_matching_above_threshold(self) -> None:
        known_errors = [
            {"message": "error: connection refused to database server"},
            {"message": "error: file not found in directory"},
        ]
        result = find_matching_error(
            "error: connection refused to database server", known_errors
        )
        assert result is not None
        assert result["similarity"] >= 0.7

    def test_find_matching_below_threshold(self) -> None:
        known_errors = [
            {"message": "error: connection refused to database"},
        ]
        result = find_matching_error(
            "warning: disk space low on volume", known_errors
        )
        assert result is None

    def test_find_matching_empty_known(self) -> None:
        result = find_matching_error("error: something broke", [])
        assert result is None

    def test_find_matching_returns_best(self) -> None:
        known_errors = [
            {"message": "error: timeout connecting to redis cache"},
            {"message": "error: timeout connecting to database server"},
        ]
        result = find_matching_error(
            "error: timeout connecting to database", known_errors
        )
        assert result is not None
        assert "database" in result["message"]

    def test_find_matching_uses_presaved_signature(self) -> None:
        known_errors = [
            {
                "message": "original error text with /path/to/file on line 42",
                "signature": "original error text with on line",
            },
        ]
        result = find_matching_error(
            "original error text with /other/path on line 99", known_errors
        )
        assert result is not None

    def test_find_matching_empty_new_error(self) -> None:
        known_errors = [{"message": "some error"}]
        result = find_matching_error("", known_errors)
        assert result is None


# ── extract_error_signature ──────────────────────────────────────────────────


class TestExtractErrorSignature:
    def test_extract_error_from_test_output(self) -> None:
        output = """
Running tests...
test_user_create ... ok
test_user_delete ... FAIL: expected 200 but got 404
test_user_update ... ok
1 failed, 2 passed
"""
        result = extract_error_signature(output)
        assert result is not None
        assert "expected" in result or "FAIL" in result

    def test_extract_error_from_build_output(self) -> None:
        output = """
Compiling project...
src/main.go:42:5: ERROR: undefined variable 'userService'
Build failed.
"""
        result = extract_error_signature(output)
        assert result is not None
        assert "undefined" in result or "userService" in result

    def test_extract_error_returns_none_on_success(self) -> None:
        output = """
Running tests...
test_user_create ... ok
test_user_delete ... ok
test_user_update ... ok
3 passed, 0 failed
All tests passed!
"""
        result = extract_error_signature(output)
        assert result is None

    def test_extract_panic(self) -> None:
        output = "panic: runtime error: index out of range [5] with length 3"
        result = extract_error_signature(output)
        assert result is not None
        assert "runtime error" in result or "index out of range" in result

    def test_extract_exception(self) -> None:
        output = """
Traceback (most recent call last):
  File "app.py", line 10, in main
    result = process(data)
ValueError: invalid literal for int()
"""
        result = extract_error_signature(output)
        assert result is not None

    def test_extract_empty_output(self) -> None:
        assert extract_error_signature("") is None
        assert extract_error_signature(None) is None  # type: ignore[arg-type]
