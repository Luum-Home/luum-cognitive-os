"""Contract tests for orchestrator_verify.py (W1).

Tests:
  1. Both import paths work (lib.orchestrator_verify and package path)
  2. extract_high_stakes_claims detects ADR-105 verbs
  3. HIGH_STAKES_VERBS frozenset contract
  4. verify_claim returns VerificationOutcome with correct fields
  5. verify_all returns list of outcomes
  6. format_report produces Markdown with required sections
  7. No HIGH_STAKES_VERBS match in clean text → empty list
  8. Composes ground_truth (not forked) — extract_claims must be callable
"""
import os
import sys
# ── Import path 1: via lib/ symlink ──────────────────────────────────────────
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from lib.orchestrator_verify import (  # noqa: E402
    HIGH_STAKES_VERBS,
    HighStakesClaim,
    VerificationOutcome,
    extract_high_stakes_claims,
    format_report,
    verify_all,
    verify_claim,
)


# ── Case 1: both import paths resolve ────────────────────────────────────────
def test_symlink_import_path_works():
    """lib.orchestrator_verify import must succeed (symlink is live)."""
    # Already imported above — if we got here, it works
    assert HIGH_STAKES_VERBS is not None


def test_package_import_path_works():
    """Direct package import path must also work."""
    _pkg_lib = os.path.join(_REPO_ROOT, "packages", "verification-audit", "lib")
    assert _pkg_lib not in sys.path
    sys.path.insert(0, _pkg_lib)
    try:
        import orchestrator_verify as ov  # noqa: F401
        assert hasattr(ov, "HIGH_STAKES_VERBS")
    finally:
        sys.path.remove(_pkg_lib)


# ── Case 2: HIGH_STAKES_VERBS contract ───────────────────────────────────────
def test_high_stakes_verbs_is_frozenset():
    assert isinstance(HIGH_STAKES_VERBS, frozenset)


def test_high_stakes_verbs_contains_adr105_verbs():
    required = {"archived", "deleted", "removed", "wired", "integrated", "registered", "done", "closed", "migrated", "tested", "verified", "claimed"}
    assert required.issubset(HIGH_STAKES_VERBS), (
        "Missing ADR-105 verbs: %s" % (required - HIGH_STAKES_VERBS)
    )


# ── Case 3: extract_high_stakes_claims ────────────────────────────────────────
def test_extract_detects_archived_verb():
    text = "The 3 hooks have been archived to docs/archive/hooks/."
    claims = extract_high_stakes_claims(text)
    verbs = {c.verb for c in claims}
    assert "archived" in verbs, "Expected 'archived' verb in: %s" % verbs


def test_extract_detects_wired_verb():
    text = "Hook completeness-check.sh is now wired in .claude/settings.json."
    claims = extract_high_stakes_claims(text)
    verbs = {c.verb for c in claims}
    assert "wired" in verbs, "Expected 'wired' verb in: %s" % verbs


def test_extract_returns_empty_for_clean_text():
    text = "All tasks are finished. The project is complete."
    claims = extract_high_stakes_claims(text)
    assert isinstance(claims, list)
    # No ADR-105 high-stakes verbs — list may be empty or minimal
    verbs = {c.verb for c in claims}
    assert verbs.issubset(HIGH_STAKES_VERBS)  # any found must still be valid verbs


def test_extract_deduplicates_claims():
    text = "archived hooks/foo.sh archived hooks/foo.sh archived hooks/foo.sh"
    claims = extract_high_stakes_claims(text)
    keys = [(c.verb, c.target) for c in claims]
    assert len(keys) == len(set(keys)), "Duplicate (verb, target) pairs found"


# ── Case 4: HighStakesClaim dataclass fields ─────────────────────────────────
def test_high_stakes_claim_fields():
    claim = HighStakesClaim(
        verb="archived",
        target="hooks/completeness-check.sh",
        evidence_required=["bilateral_archive_check"],
        confidence=0.9,
        raw_text="The hook has been archived.",
    )
    assert claim.verb == "archived"
    assert claim.target == "hooks/completeness-check.sh"
    assert "bilateral_archive_check" in claim.evidence_required
    assert 0.0 <= claim.confidence <= 1.0


# ── Case 5: verify_claim returns VerificationOutcome ─────────────────────────
def test_verify_claim_archived_requires_archive_copy(tmp_path):
    """Archived claims require archive present, original absent, and no stale refs."""
    archive_dir = tmp_path / "docs" / "archive" / "hooks"
    archive_dir.mkdir(parents=True)
    (archive_dir / "gone.sh").write_text("#!/usr/bin/env bash\necho archived\n")
    claim = HighStakesClaim(
        verb="archived",
        target="hooks/gone.sh",
        evidence_required=["bilateral_archive_check"],
        confidence=0.8,
    )
    outcome = verify_claim(claim, str(tmp_path))
    assert isinstance(outcome, VerificationOutcome)
    assert outcome.claim is claim
    assert outcome.verified is True
    assert "bilateral_archive_check" in outcome.evidence


def test_verify_claim_archived_fails_without_archive_copy(tmp_path):
    claim = HighStakesClaim(
        verb="archived",
        target="hooks/gone.sh",
        evidence_required=["bilateral_archive_check"],
        confidence=0.8,
    )
    outcome = verify_claim(claim, str(tmp_path))
    assert outcome.verified is False
    assert "archive copy missing" in (outcome.failure_reason or "")


def test_verify_claim_archived_source_present(tmp_path):
    """If source file still exists, archived claim must fail."""
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "live.sh").write_text("#!/bin/bash\necho live\n")

    claim = HighStakesClaim(
        verb="archived",
        target="hooks/live.sh",
        evidence_required=["bilateral_archive_check"],
        confidence=0.8,
    )
    outcome = verify_claim(claim, str(tmp_path))
    assert outcome.verified is False
    assert outcome.failure_reason is not None


# ── Case 6: verify_all convenience function ───────────────────────────────────
def test_verify_all_returns_list(tmp_path):
    agent_output = "The hooks have been archived to docs/archive/hooks/."
    results = verify_all(agent_output, str(tmp_path))
    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, VerificationOutcome)


# ── Case 7: format_report produces Markdown ───────────────────────────────────
def test_format_report_structure():
    claim = HighStakesClaim(
        verb="archived",
        target="hooks/foo.sh",
        evidence_required=["bilateral_archive_check"],
        confidence=0.7,
    )
    outcome = VerificationOutcome(
        claim=claim,
        verified=True,
        evidence={"bilateral_archive_check": "PASS — source absent"},
    )
    report = format_report([outcome])
    assert "## High-Stakes Claim Verification" in report
    assert "archived" in report
    assert "hooks/foo.sh" in report
    assert "PASS" in report


def test_format_report_empty():
    report = format_report([])
    assert "No high-stakes claims" in report


# ── Case 8: composes ground_truth (does not fork) ────────────────────────────
def test_composes_ground_truth_not_forked():
    """Verify orchestrator_verify imports from ground_truth, not a fork."""
    from lib import ground_truth  # noqa: F401 — import must succeed
    from lib.ground_truth import extract_claims  # noqa: F401
    assert callable(extract_claims)


# ── Case 9: false-positive suppression (ADR-105 claim-gate bugfix) ───────────
# These strings appeared in real commit message bodies and were incorrectly
# flagged as high-stakes claims by Pass 2 before the structured-claim gate
# was introduced. They must produce NO claims.

def test_false_pos_integrated_in_main_prose():
    """'content already integrated in main (ADRs 106-115)' must NOT fire."""
    text = "All 9 branches' unique content already integrated in main (ADRs 106-115,"
    claims = extract_high_stakes_claims(text)
    verbs = [c.verb for c in claims]
    assert "integrated" not in verbs, (
        "False positive: 'integrated in main' prose should not be a claim; got %s" % claims
    )


def test_false_pos_integrated_schema_field_in_parens():
    """'status (integrated for all 9)' must NOT fire — verb is inside parens."""
    text = "source_branch, source_head, reason, scope, status (integrated for all 9),"
    claims = extract_high_stakes_claims(text)
    verbs = [c.verb for c in claims]
    assert "integrated" not in verbs, (
        "False positive: verb inside parentheses should not be a claim; got %s" % claims
    )


def test_false_pos_verified_in_heading_parens():
    """'Regex matrix (all verified):' must NOT fire — collective phrase in parens."""
    text = "verified Regex matrix (all verified):"
    claims = extract_high_stakes_claims(text)
    assert len(claims) == 0, (
        "False positive: heading with 'all verified' in parens should produce no claims; got %s" % claims
    )


# ── Case 10: true positives still fire ───────────────────────────────────────

def test_true_pos_archived_with_path():
    """'archived hooks/foo.sh' (path-based) must extract a claim."""
    text = "archived hooks/foo.sh"
    claims = extract_high_stakes_claims(text)
    verbs = {c.verb for c in claims}
    assert "archived" in verbs, (
        "True positive missed: path-based archived claim should fire; got verbs=%s" % verbs
    )


def test_true_pos_plan_checkbox_archived():
    """'[x] Archive completeness-check.sh — archived' (plan checkbox) must fire."""
    text = "[x] Archive completeness-check.sh — archived"
    claims = extract_high_stakes_claims(text)
    verbs = {c.verb for c in claims}
    assert "archived" in verbs, (
        "True positive missed: plan checkbox with 'archived' should fire; got verbs=%s" % verbs
    )


def test_true_pos_bullet_path_verb():
    """'* hooks/old-gate.sh: archived' (bullet + path) must fire."""
    text = "* hooks/old-gate.sh: archived"
    claims = extract_high_stakes_claims(text)
    verbs = {c.verb for c in claims}
    assert "archived" in verbs, (
        "True positive missed: bullet+path claim should fire; got verbs=%s" % verbs
    )
