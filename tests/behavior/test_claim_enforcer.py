from __future__ import annotations

from pathlib import Path

from scripts.claim_enforcer import evaluate, extract_verification, high_stakes


def test_no_trigger_is_noop(tmp_path: Path) -> None:
    report = evaluate("TRUST_REPORT: SCORE=80 STATUS=MEDIUM EVIDENCE=1 UNCERTAINTIES=1\nNo operational closure claimed.", tmp_path)

    assert report["ok"] is True
    assert report["status"] == "noop"


def test_trigger_with_passing_verification_allows(tmp_path: Path) -> None:
    text = """
TRUST_REPORT: SCORE=80 STATUS=MEDIUM EVIDENCE=1 UNCERTAINTIES=1
Fixed #123 and 1 test passed.
verification: python3 -c "raise SystemExit(0)"
"""

    report = evaluate(text, tmp_path, timeout_seconds=5)

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert report["evidence"]["returncode"] == 0


def test_trigger_with_failing_verification_blocks_and_downgrades(tmp_path: Path) -> None:
    text = """
TRUST_REPORT: SCORE=80 STATUS=MEDIUM EVIDENCE=1 UNCERTAINTIES=1
Fixed #123 and 1 test passed.
verification: python3 -c "raise SystemExit(7)"
"""

    report = evaluate(text, tmp_path, timeout_seconds=5)

    assert report["ok"] is False
    assert report["status"] == "block"
    assert report["downgraded_status"] == "partial"
    assert any(f["code"] == "verification-command-failed" for f in report["findings"])


def test_trigger_with_manual_verification_allows_with_audit_warning(tmp_path: Path) -> None:
    text = """
TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=1 UNCERTAINTIES=1
All green after visual review.
verification: manual
"""

    report = evaluate(text, tmp_path)

    assert report["ok"] is True
    assert report["status"] == "manual"
    assert any(f["code"] == "verification-manual" for f in report["findings"])


def test_trigger_without_verification_blocks(tmp_path: Path) -> None:
    report = evaluate("Fixed #123 and 2 tests passed.", tmp_path)

    assert report["ok"] is False
    assert report["downgraded_status"] == "partial"
    assert any(f["code"] == "verification-field-missing" for f in report["findings"])


def test_verification_line_accepts_backticks() -> None:
    assert extract_verification("verification: `python3 -m pytest -q`") == "python3 -m pytest -q"
    assert high_stakes("all green") is True
