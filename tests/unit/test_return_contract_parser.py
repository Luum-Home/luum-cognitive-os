"""
Tests for lib/return_contract_parser.py

Covers:
- Parsing a complete, valid RESULT: block
- Parsing with all fields present
- Parsing with missing optional fields (BLOCKERS, TOKENS_ESTIMATE)
- Parsing STATUS variations (success, partial, failed)
- Returns None when no RESULT: block is present
- Validation: missing STATUS → violation
- Validation: empty SUMMARY → violation
- Validation: failed/partial with no blockers → violation
- Validation: too many KEY_FINDINGS → violation
- format_compact_result produces a compact (~200-token) string
"""

from lib.return_contract_parser import (
    parse_return_contract,
    validate_return_contract,
    format_compact_result,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

FULL_OUTPUT = """\
PROGRESS: [step 1/3] Implementing the parser
PROGRESS: [step 2/3] Writing tests
PROGRESS: [step 3/3] Verifying

RESULT:
  STATUS: success
  SUMMARY: Implemented return_contract_parser with parse, validate, and format functions.
  FILES_CHANGED:
    - lib/return_contract_parser.py — created parser module
    - tests/unit/test_return_contract_parser.py — created test suite
  KEY_FINDINGS:
    - The RESULT: block must appear before TRUST_REPORT:
    - List sections use "  - " prefix (two-space indent + dash + space)
  BLOCKERS: none
  TOKENS_ESTIMATE: 3200

TRUST_REPORT: SCORE=85 STATUS=HIGH EVIDENCE=3 UNCERTAINTIES=1
---
Score: 85/100

EVIDENCE PROVIDED:
  [check] Tests pass: pytest tests/unit/test_return_contract_parser.py — 10 passed
  [check] Module imports without error
  [warn] Integration with completion-gate.sh not verified

WHAT I'M CONFIDENT ABOUT:
  - Parser handles all documented contract fields

WHAT I'M UNSURE ABOUT:
  - Edge cases with multi-line BLOCKERS not fully tested
"""

PARTIAL_OUTPUT = """\
RESULT:
  STATUS: partial
  SUMMARY: Completed 3 of 5 tasks; database migration step could not run.
  FILES_CHANGED:
    - internal/users/handler.go — added new endpoint
  KEY_FINDINGS:
    - Migration requires manual DB access
  BLOCKERS: Database migration requires DBA access not available in CI

TRUST_REPORT: SCORE=60 STATUS=MEDIUM EVIDENCE=2 UNCERTAINTIES=2
"""

FAILED_OUTPUT = """\
RESULT:
  STATUS: failed
  SUMMARY: Build failed due to missing dependency.
  FILES_CHANGED:
  KEY_FINDINGS:
  BLOCKERS: go.sum is out of sync; run 'go mod tidy' to fix

TRUST_REPORT: SCORE=30 STATUS=LOW EVIDENCE=1 UNCERTAINTIES=3
"""

MINIMAL_OUTPUT = """\
RESULT:
  STATUS: success
  SUMMARY: Renamed variable across 3 files.
  FILES_CHANGED:
    - main.go — renamed oldVar to newVar

TRUST_REPORT: SCORE=90 STATUS=HIGH EVIDENCE=2 UNCERTAINTIES=0
"""

NO_CONTRACT_OUTPUT = """\
I completed the task. Here is what I did:
- Modified main.go
- Updated the tests

TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=2 UNCERTAINTIES=1
"""


# ---------------------------------------------------------------------------
# parse_return_contract tests
# ---------------------------------------------------------------------------

class TestParseReturnContract:

    def test_parse_full_valid_block(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        assert parsed["status"] == "success"
        assert "return_contract_parser" in parsed["summary"]
        assert len(parsed["files_changed"]) == 2
        assert len(parsed["key_findings"]) == 2
        assert parsed["blockers"] == "none"
        assert parsed["tokens_estimate"] == 3200

    def test_parse_all_fields_present(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        for key in ("status", "summary", "files_changed", "key_findings", "blockers", "tokens_estimate"):
            assert key in parsed, f"Missing key: {key}"

    def test_parse_missing_optional_blockers(self):
        # MINIMAL_OUTPUT has no BLOCKERS or TOKENS_ESTIMATE lines
        parsed = parse_return_contract(MINIMAL_OUTPUT)
        assert parsed is not None
        assert parsed["status"] == "success"
        assert parsed["blockers"] == "none"  # default
        assert parsed["tokens_estimate"] is None  # not present

    def test_parse_missing_tokens_estimate(self):
        parsed = parse_return_contract(MINIMAL_OUTPUT)
        assert parsed is not None
        assert parsed["tokens_estimate"] is None

    def test_parse_status_success(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        assert parsed["status"] == "success"

    def test_parse_status_partial(self):
        parsed = parse_return_contract(PARTIAL_OUTPUT)
        assert parsed is not None
        assert parsed["status"] == "partial"

    def test_parse_status_failed(self):
        parsed = parse_return_contract(FAILED_OUTPUT)
        assert parsed is not None
        assert parsed["status"] == "failed"

    def test_parse_files_changed_list(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        assert any("return_contract_parser.py" in f for f in parsed["files_changed"])
        assert any("test_return_contract_parser.py" in f for f in parsed["files_changed"])

    def test_parse_key_findings_list(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        assert len(parsed["key_findings"]) == 2
        assert any("TRUST_REPORT" in f for f in parsed["key_findings"])

    def test_parse_partial_blockers(self):
        parsed = parse_return_contract(PARTIAL_OUTPUT)
        assert parsed is not None
        assert "DBA access" in parsed["blockers"]

    def test_parse_failed_blockers(self):
        parsed = parse_return_contract(FAILED_OUTPUT)
        assert parsed is not None
        assert "go mod tidy" in parsed["blockers"]

    def test_returns_none_when_no_result_block(self):
        parsed = parse_return_contract(NO_CONTRACT_OUTPUT)
        assert parsed is None

    def test_returns_none_on_empty_string(self):
        parsed = parse_return_contract("")
        assert parsed is None

    def test_returns_none_on_none_input(self):
        parsed = parse_return_contract(None)  # type: ignore[arg-type]
        assert parsed is None

    def test_parse_empty_files_and_findings(self):
        # FAILED_OUTPUT has empty FILES_CHANGED and KEY_FINDINGS sections
        parsed = parse_return_contract(FAILED_OUTPUT)
        assert parsed is not None
        assert parsed["files_changed"] == []
        assert parsed["key_findings"] == []

    def test_parse_stops_at_trust_report(self):
        # Content after TRUST_REPORT: should not bleed into the parsed block
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        assert "Score: 85/100" not in parsed.get("summary", "")
        assert "Score: 85/100" not in " ".join(parsed.get("key_findings", []))

    def test_parse_tokens_estimate_with_comma(self):
        output = """\
RESULT:
  STATUS: success
  SUMMARY: Done.
  FILES_CHANGED:
  KEY_FINDINGS:
  BLOCKERS: none
  TOKENS_ESTIMATE: 12,500
"""
        parsed = parse_return_contract(output)
        assert parsed is not None
        assert parsed["tokens_estimate"] == 12500

    def test_parse_case_insensitive_status_normalised(self):
        output = """\
RESULT:
  STATUS: SUCCESS
  SUMMARY: Done.
  FILES_CHANGED:
  KEY_FINDINGS:
  BLOCKERS: none
"""
        parsed = parse_return_contract(output)
        assert parsed is not None
        assert parsed["status"] == "success"



def test_parse_current_agent_preamble_contract_shape():
    output = """
RESULT:
  status: completed
  summary: Implemented bounded agent digest rendering.
  files_created: tests/unit/test_format_converter.py
  files_modified: lib/notification_digest.py, lib/return_contract_parser.py
  tests: 12 passed, 0 failed, 1 skipped
  blockers: none

TRUST_REPORT: SCORE=82 STATUS=MEDIUM EVIDENCE=4 UNCERTAINTIES=1
"""
    parsed = parse_return_contract(output)
    assert parsed is not None
    assert parsed["status"] == "completed"
    assert parsed["files_created"] == ["tests/unit/test_format_converter.py"]
    assert "lib/notification_digest.py" in parsed["files_modified"]
    assert parsed["tests"] == {"passed": 12, "failed": 0, "xfail": 0, "skipped": 1}
    assert validate_return_contract(parsed) == []
    compact = format_compact_result(parsed)
    assert "COMPLETED" in compact
    assert "12 passed" in compact

# ---------------------------------------------------------------------------
# validate_return_contract tests
# ---------------------------------------------------------------------------

class TestValidateReturnContract:

    def test_valid_full_contract_no_violations(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        violations = validate_return_contract(parsed)
        assert violations == []

    def test_valid_partial_contract_no_violations(self):
        parsed = parse_return_contract(PARTIAL_OUTPUT)
        assert parsed is not None
        violations = validate_return_contract(parsed)
        assert violations == []

    def test_missing_status_is_violation(self):
        parsed = {
            "status": "",
            "summary": "Did something.",
            "files_changed": [],
            "key_findings": [],
            "blockers": "none",
            "tokens_estimate": None,
        }
        violations = validate_return_contract(parsed)
        assert any("STATUS" in v for v in violations)

    def test_invalid_status_value_is_violation(self):
        parsed = {
            "status": "done",  # not a valid value
            "summary": "Did something.",
            "files_changed": [],
            "key_findings": [],
            "blockers": "none",
            "tokens_estimate": None,
        }
        violations = validate_return_contract(parsed)
        assert any("STATUS" in v for v in violations)

    def test_empty_summary_is_violation(self):
        parsed = {
            "status": "success",
            "summary": "",
            "files_changed": [],
            "key_findings": [],
            "blockers": "none",
            "tokens_estimate": None,
        }
        violations = validate_return_contract(parsed)
        assert any("SUMMARY" in v for v in violations)

    def test_failed_with_none_blockers_is_violation(self):
        parsed = {
            "status": "failed",
            "summary": "Something broke.",
            "files_changed": [],
            "key_findings": [],
            "blockers": "none",
            "tokens_estimate": None,
        }
        violations = validate_return_contract(parsed)
        assert any("BLOCKERS" in v for v in violations)

    def test_partial_with_empty_blockers_is_violation(self):
        parsed = {
            "status": "partial",
            "summary": "Half done.",
            "files_changed": [],
            "key_findings": [],
            "blockers": "",
            "tokens_estimate": None,
        }
        violations = validate_return_contract(parsed)
        assert any("BLOCKERS" in v for v in violations)

    def test_too_many_key_findings_is_violation(self):
        parsed = {
            "status": "success",
            "summary": "Done.",
            "files_changed": [],
            "key_findings": ["a", "b", "c", "d", "e", "f"],  # 6 > max 5
            "blockers": "none",
            "tokens_estimate": None,
        }
        violations = validate_return_contract(parsed)
        assert any("KEY_FINDINGS" in v for v in violations)

    def test_exactly_five_key_findings_is_valid(self):
        parsed = {
            "status": "success",
            "summary": "Done.",
            "files_changed": [],
            "key_findings": ["a", "b", "c", "d", "e"],
            "blockers": "none",
            "tokens_estimate": None,
        }
        violations = validate_return_contract(parsed)
        assert not any("KEY_FINDINGS" in v for v in violations)

    def test_success_with_none_blockers_is_valid(self):
        parsed = {
            "status": "success",
            "summary": "Done.",
            "files_changed": [],
            "key_findings": [],
            "blockers": "none",
            "tokens_estimate": None,
        }
        violations = validate_return_contract(parsed)
        assert violations == []


# ---------------------------------------------------------------------------
# format_compact_result tests
# ---------------------------------------------------------------------------

class TestFormatCompactResult:

    def test_format_includes_status_and_summary(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        compact = format_compact_result(parsed)
        assert "SUCCESS" in compact
        assert "return_contract_parser" in compact

    def test_format_includes_file_paths(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        compact = format_compact_result(parsed)
        assert "return_contract_parser.py" in compact

    def test_format_includes_key_findings(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        compact = format_compact_result(parsed)
        assert "FINDINGS" in compact

    def test_format_excludes_none_blockers(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        compact = format_compact_result(parsed)
        # "none" blockers should not appear as a BLOCKERS: line
        assert "BLOCKERS:" not in compact

    def test_format_includes_blockers_when_present(self):
        parsed = parse_return_contract(PARTIAL_OUTPUT)
        assert parsed is not None
        compact = format_compact_result(parsed)
        assert "BLOCKERS" in compact
        assert "DBA access" in compact

    def test_format_includes_token_estimate(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        compact = format_compact_result(parsed)
        assert "3,200" in compact or "3200" in compact

    def test_format_is_concise(self):
        parsed = parse_return_contract(FULL_OUTPUT)
        assert parsed is not None
        compact = format_compact_result(parsed)
        # Rough proxy: ~200 tokens ≈ 800 characters. Be lenient but check it's not huge.
        assert len(compact) < 2000, f"Compact result too long: {len(compact)} chars"

    def test_format_none_input_returns_placeholder(self):
        compact = format_compact_result(None)  # type: ignore[arg-type]
        assert "no return contract" in compact.lower()

    def test_format_caps_files_at_five_with_overflow_note(self):
        parsed = {
            "status": "success",
            "summary": "Done.",
            "files_changed": [f"file{i}.go — changed" for i in range(8)],
            "key_findings": [],
            "blockers": "none",
            "tokens_estimate": None,
        }
        compact = format_compact_result(parsed)
        assert "and 3 more" in compact

    def test_format_partial_status(self):
        parsed = parse_return_contract(PARTIAL_OUTPUT)
        assert parsed is not None
        compact = format_compact_result(parsed)
        assert "PARTIAL" in compact
