"""Unit tests for lib/return_contract_validator.py (WS2)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "lib"))

import pytest
from return_contract_validator import ReturnContractValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_RESULT_BLOCK = """\
Some agent prose here.

RESULT:
  status: completed
  summary: Implemented the auth middleware and wrote unit tests.
  files_created: lib/auth.py, tests/unit/test_auth.py
  files_modified: main.py, requirements.txt
  tests: 12 passed, 0 failed, 1 xfail
  discoveries: JWT secret must be at least 32 bytes
  discoveries: - Middleware order matters for rate limiting

TRUST_REPORT: SCORE=85 STATUS=HIGH EVIDENCE=3 UNCERTAINTIES=1
---
Score: 85/100
"""

AGENT_OUTPUT_NO_BLOCK = """\
I have completed the implementation. The code is clean and tests pass.
All acceptance criteria have been met. The system is working correctly.
"""

PARTIAL_RESULT_BLOCK = """\
RESULT:
  status: partial
  summary: Implemented 3 of 5 endpoints; blocked on missing DB schema.
  files_created: none
  files_modified: internal/api/handler.go

TRUST_REPORT: SCORE=60 STATUS=MEDIUM EVIDENCE=2 UNCERTAINTIES=3
"""

REALISTIC_AGENT_OUTPUT = """\
Starting implementation of the user endpoint.

PROGRESS: [step 1/4] Reading existing patterns
PROGRESS: [step 2/4] Creating handler file
PROGRESS: [step 3/4] Writing tests
PROGRESS: [step 4/4] Running tests

FILES_CREATED: internal/users/handler.go, tests/unit/test_handler_test.go
FILES_MODIFIED: internal/users/router.go

All tests pass. The endpoint is functional and follows ginext patterns.

RESULT:
  status: completed
  summary: Created GET /users/:id endpoint with unit tests.
  files_created: internal/users/handler.go, tests/unit/test_handler_test.go
  files_modified: internal/users/router.go
  tests: 8 passed, 0 failed
  discoveries: ginext requires explicit error mapping for 404s
  discoveries: - Router registration must happen after middleware

TRUST_REPORT: SCORE=90 STATUS=HIGH EVIDENCE=4 UNCERTAINTIES=1
---
Score: 90/100
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestExtractStructuredReturn:
    def setup_method(self):
        self.validator = ReturnContractValidator()

    def test_extract_structured_return(self):
        result = self.validator.extract_structured_return(VALID_RESULT_BLOCK)
        assert result is not None
        assert result["status"] == "completed"
        assert "auth middleware" in result["summary"]
        assert "lib/auth.py" in result["files_created"]
        assert "main.py" in result["files_modified"]

    def test_extract_no_block(self):
        result = self.validator.extract_structured_return(AGENT_OUTPUT_NO_BLOCK)
        assert result is None

    def test_extract_tests_parsed(self):
        result = self.validator.extract_structured_return(VALID_RESULT_BLOCK)
        assert result is not None
        tests = result.get("tests", {})
        assert tests.get("passed") == 12
        assert tests.get("failed") == 0
        assert tests.get("xfail") == 1

    def test_extract_from_real_agent_output(self):
        result = self.validator.extract_structured_return(REALISTIC_AGENT_OUTPUT)
        assert result is not None
        assert result["status"] == "completed"
        assert "GET /users/:id" in result["summary"]
        assert len(result.get("files_created", [])) == 2
        tests = result.get("tests", {})
        assert tests.get("passed") == 8

    def test_extract_partial_status(self):
        result = self.validator.extract_structured_return(PARTIAL_RESULT_BLOCK)
        assert result is not None
        assert result["status"] == "partial"

    def test_extract_discoveries(self):
        result = self.validator.extract_structured_return(VALID_RESULT_BLOCK)
        assert result is not None
        discoveries = result.get("discoveries", [])
        assert len(discoveries) >= 1
        assert any("JWT" in d or "Middleware" in d for d in discoveries)

    def test_extract_files_none(self):
        result = self.validator.extract_structured_return(PARTIAL_RESULT_BLOCK)
        assert result is not None
        # "none" should parse to empty list
        assert result.get("files_created", []) == []


class TestValidateReturn:
    def setup_method(self):
        self.validator = ReturnContractValidator()

    def test_validate_missing_status(self):
        issues = self.validator.validate_return({"summary": "did something"})
        assert any("status" in i for i in issues)

    def test_validate_missing_summary(self):
        issues = self.validator.validate_return({"status": "completed"})
        assert any("summary" in i for i in issues)

    def test_validate_complete(self):
        issues = self.validator.validate_return({"status": "completed", "summary": "done"})
        assert issues == []

    def test_validate_invalid_status(self):
        issues = self.validator.validate_return({"status": "done", "summary": "done"})
        assert any("invalid status" in i for i in issues)

    def test_validate_all_valid_statuses(self):
        for status in ("completed", "failed", "partial"):
            issues = self.validator.validate_return({"status": status, "summary": "s"})
            assert issues == [], f"Expected no issues for status={status}"


class TestFormatCompactSummary:
    def setup_method(self):
        self.validator = ReturnContractValidator()

    def test_format_compact_summary(self):
        structured = {
            "status": "completed",
            "summary": "Implemented the auth middleware.",
            "files_created": ["lib/auth.py"],
            "files_modified": ["main.py"],
            "tests": {"passed": 12, "failed": 0, "xfail": 1},
            "discoveries": ["JWT secret must be 32+ bytes"],
        }
        result = self.validator.format_compact_summary(structured)
        assert len(result) < 500
        assert "COMPLETED" in result
        assert "auth middleware" in result

    def test_format_with_tests(self):
        structured = {
            "status": "completed",
            "summary": "All done.",
            "tests": {"passed": 8, "failed": 2, "xfail": 0},
        }
        result = self.validator.format_compact_summary(structured)
        assert "8" in result
        assert "2" in result
        assert "passed" in result.lower() or "Tests:" in result

    def test_format_output_under_500_chars(self):
        structured = {
            "status": "completed",
            "summary": "Implemented everything requested including all edge cases.",
            "files_created": ["a.py", "b.py", "c.py"],
            "files_modified": ["main.py", "config.py"],
            "tests": {"passed": 100, "failed": 0, "xfail": 5},
            "discoveries": ["Discovery 1", "Discovery 2", "Discovery 3"],
            "trust_score": 92,
        }
        result = self.validator.format_compact_summary(structured)
        assert len(result) <= 500

    def test_format_failed_status(self):
        structured = {"status": "failed", "summary": "Build broke."}
        result = self.validator.format_compact_summary(structured)
        assert "FAILED" in result

    def test_format_includes_trust_score(self):
        structured = {
            "status": "completed",
            "summary": "Done.",
            "trust_score": 87,
        }
        result = self.validator.format_compact_summary(structured)
        assert "87" in result
