# SCOPE: os-only
"""Orchestrator Verify — ADR-105 high-stakes claim extraction and verification.

Composes lib.ground_truth (does NOT fork it). Filters the general claim set
produced by ground_truth.extract_claims down to the specific ADR-105 verb set
that carries high blast-radius consequences ("archived", "wired", "tested",
"verified", "claimed"). For each matched claim, runs a bilateral verification
check appropriate to the verb.

Usage:
    from lib.orchestrator_verify import (
        extract_high_stakes_claims,
        verify_claim,
        verify_all,
        format_report,
        HIGH_STAKES_VERBS,
    )

    outcomes = verify_all(agent_output, project_root="/path/to/project")
    print(format_report(outcomes))

Python 3.9+ compatible.
Part of: red-team-harness Wave W1
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Compose with lib.ground_truth — do NOT fork.
# Import via package path; symlink in lib/ makes both paths work.
try:
    from lib.ground_truth import extract_claims, Claim
except ImportError:
    # Fallback for direct package invocation without symlink on sys.path
    import sys as _sys

    _pkg_lib = os.path.join(os.path.dirname(__file__), "..", "..", "lib")
    if _pkg_lib not in _sys.path:
        _sys.path.insert(0, _pkg_lib)
    from ground_truth import extract_claims, Claim  # type: ignore[import]


# ── ADR-105 verb set ──────────────────────────────────────────────────────────
# These verbs carry high-stakes completion claims per ADR-105.
# Extending this set requires an ADR update — do NOT add verbs ad-hoc.
HIGH_STAKES_VERBS: frozenset = frozenset(
    {"archived", "wired", "tested", "verified", "claimed"}
)

# Regex patterns to detect ADR-105 verbs directly in agent output.
# Supplements ground_truth.extract_claims() which is file-path oriented.
_VERB_PATTERNS = {
    verb: re.compile(
        r"\b(?:has been |have been |(?:was|were) )?%s\b" % re.escape(verb),
        re.IGNORECASE,
    )
    for verb in HIGH_STAKES_VERBS
}

# Evidence check types dispatched by verb
_VERB_EVIDENCE_MAP: Dict[str, List[str]] = {
    "archived": ["bilateral_archive_check"],
    "wired": ["config_reference_check"],
    "tested": ["test_result_check"],
    "verified": ["verification_output_check"],
    "claimed": ["claim_presence_check"],
}


# ── Public dataclasses ────────────────────────────────────────────────────────

@dataclass
class HighStakesClaim:
    """An ADR-105 high-stakes claim extracted from agent output."""

    verb: str               # one of HIGH_STAKES_VERBS
    target: str             # path or identifier the verb applies to
    evidence_required: List[str] = field(default_factory=list)   # bilateral check kinds
    confidence: float = 0.5  # 0.0–1.0 from extraction heuristics
    raw_text: str = ""      # the original sentence/fragment that triggered extraction


@dataclass
class VerificationOutcome:
    """Result of verifying a single HighStakesClaim against reality."""

    claim: HighStakesClaim
    verified: bool
    evidence: Dict[str, str] = field(default_factory=dict)   # check_kind → output snippet
    failure_reason: Optional[str] = None


# ── Extraction ────────────────────────────────────────────────────────────────

def extract_high_stakes_claims(agent_output: str) -> List[HighStakesClaim]:
    """Extract ADR-105 high-stakes claims from agent output text.

    Strategy (two-pass):
      Pass 1 — delegate to lib.ground_truth.extract_claims(), then filter
               only claims whose text contains a HIGH_STAKES_VERBS verb.
      Pass 2 — direct regex scan for verbs the general extractor may have
               missed (e.g. "The 3 hooks have been archived to docs/archive/").

    Returns deduplicated list sorted by verb then target.
    """
    results: List[HighStakesClaim] = []
    seen: set = set()

    # ── Pass 1: filter ground_truth general claims ──────────────────────────
    general_claims: List[Claim] = extract_claims(agent_output)
    for claim in general_claims:
        # Check if the claim text or target contains a high-stakes verb
        matched_verb = _detect_verb_in_text(claim.text + " " + claim.target)
        if matched_verb:
            key = (matched_verb, claim.target)
            if key not in seen:
                seen.add(key)
                results.append(
                    HighStakesClaim(
                        verb=matched_verb,
                        target=claim.target,
                        evidence_required=_VERB_EVIDENCE_MAP.get(matched_verb, []),
                        confidence=0.7,
                        raw_text=claim.text,
                    )
                )

    # ── Pass 2: direct verb scan for claims the general extractor missed ────
    lines = agent_output.split("\n")
    for line in lines:
        matched_verb = _detect_verb_in_text(line)
        if not matched_verb:
            continue
        # Extract a plausible target from the line
        target = _extract_target_from_line(line, matched_verb)
        if not target:
            target = line.strip()[:80]  # fallback: truncated line
        key = (matched_verb, target)
        if key not in seen:
            seen.add(key)
            results.append(
                HighStakesClaim(
                    verb=matched_verb,
                    target=target,
                    evidence_required=_VERB_EVIDENCE_MAP.get(matched_verb, []),
                    confidence=0.5,
                    raw_text=line.strip(),
                )
            )

    # Stable sort: verb asc, target asc
    results.sort(key=lambda c: (c.verb, c.target))
    return results


def _detect_verb_in_text(text: str) -> Optional[str]:
    """Return the first HIGH_STAKES_VERBS verb found in text, else None."""
    text_lower = text.lower()
    for verb, pattern in _VERB_PATTERNS.items():
        if pattern.search(text_lower):
            return verb
    return None


def _extract_target_from_line(line: str, verb: str) -> Optional[str]:
    """Heuristic: extract a file path or identifier from a line containing verb."""
    # Look for path-like tokens (contain / or have a . extension)
    path_re = re.compile(r"[`\"']?([a-zA-Z0-9_./-]+(?:/[a-zA-Z0-9_./-]+|\.[a-zA-Z0-9]{1,10}))[`\"']?")
    matches = path_re.findall(line)
    for m in matches:
        # Skip the verb itself and short noise tokens
        if m.lower() != verb and len(m) >= 3:
            return m
    return None


# ── Verification ──────────────────────────────────────────────────────────────

def verify_claim(claim: HighStakesClaim, project_root: str) -> VerificationOutcome:
    """Run bilateral verification for one HighStakesClaim.

    Dispatches by verb to the appropriate check function.
    All checks are read-only filesystem operations — no commands executed.
    """
    dispatch = {
        "archived": _verify_archived,
        "wired": _verify_wired,
        "tested": _verify_tested,
        "verified": _verify_verified,
        "claimed": _verify_claimed,
    }
    handler = dispatch.get(claim.verb, _verify_unknown)
    return handler(claim, project_root)


def verify_all(agent_output: str, project_root: str) -> List[VerificationOutcome]:
    """Convenience: extract high-stakes claims then verify each one.

    Returns list of VerificationOutcome objects in extraction order.
    """
    claims = extract_high_stakes_claims(agent_output)
    return [verify_claim(c, project_root) for c in claims]


# ── Per-verb verifiers ────────────────────────────────────────────────────────

def _verify_archived(claim: HighStakesClaim, project_root: str) -> VerificationOutcome:
    """Bilateral archive check: archive copy present AND original absent."""
    target = claim.target
    full_path = _resolve_path(target, project_root)

    # We cannot determine archive_dir from the claim alone without more context.
    # Check 1: Does the file exist at all? (existence = was NOT removed = red flag)
    if os.path.isfile(full_path):
        return VerificationOutcome(
            claim=claim,
            verified=False,
            evidence={"bilateral_archive_check": "FAIL — original still present at %s" % full_path},
            failure_reason=(
                "File '%s' still exists at source path — not truly archived. "
                "Use scripts/verify-archived.sh for bilateral check." % target
            ),
        )

    # File absent at claimed path — partial pass (archive copy location unknown to us)
    return VerificationOutcome(
        claim=claim,
        verified=True,
        evidence={
            "bilateral_archive_check": "PASS (source absent) — bilateral archive check "
            "requires scripts/verify-archived.sh for full confirmation"
        },
    )


def _verify_wired(claim: HighStakesClaim, project_root: str) -> VerificationOutcome:
    """Config reference check: target appears in settings/config files."""
    target = claim.target
    basename = os.path.basename(target)

    # Scan common config files for reference
    config_files = [
        ".claude/settings.json",
        "cognitive-os.yaml",
        ".codex/hooks.json",
    ]
    found_in: List[str] = []
    for cfg in config_files:
        cfg_path = os.path.join(project_root, cfg)
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", errors="replace") as f:
                    content = f.read()
                if basename in content or target in content:
                    found_in.append(cfg)
            except (OSError, IOError):
                pass

    if found_in:
        return VerificationOutcome(
            claim=claim,
            verified=True,
            evidence={"config_reference_check": "PASS — found in: %s" % ", ".join(found_in)},
        )
    return VerificationOutcome(
        claim=claim,
        verified=False,
        evidence={"config_reference_check": "FAIL — '%s' not found in any config file" % basename},
        failure_reason="Target '%s' not found wired in any config file" % target,
    )


def _verify_tested(claim: HighStakesClaim, project_root: str) -> VerificationOutcome:
    """Test result check: look for test file existence."""
    target = claim.target
    # Heuristic: check if a test file for target exists
    base = os.path.splitext(os.path.basename(target))[0]
    # Simple existence check without glob expansion overhead
    test_dirs = ["tests", "test", "spec"]
    found_test = False
    for td in test_dirs:
        td_path = os.path.join(project_root, td)
        if os.path.isdir(td_path):
            for root, _dirs, files in os.walk(td_path):
                for fname in files:
                    if base in fname and ("test" in fname.lower() or "spec" in fname.lower()):
                        found_test = True
                        break
                if found_test:
                    break
    if found_test:
        return VerificationOutcome(
            claim=claim,
            verified=True,
            evidence={"test_result_check": "PASS — test file found for '%s'" % base},
        )
    return VerificationOutcome(
        claim=claim,
        verified=False,
        evidence={"test_result_check": "UNVERIFIABLE — no test file found for '%s' (manual check required)" % base},
        failure_reason=None,  # not a hard failure; test run not auto-executed
    )


def _verify_verified(claim: HighStakesClaim, project_root: str) -> VerificationOutcome:
    """Verification output check: target file exists (as minimal evidence)."""
    target = claim.target
    full_path = _resolve_path(target, project_root)
    if os.path.isfile(full_path):
        size = os.path.getsize(full_path)
        return VerificationOutcome(
            claim=claim,
            verified=True,
            evidence={"verification_output_check": "PASS — file exists (%d bytes)" % size},
        )
    return VerificationOutcome(
        claim=claim,
        verified=False,
        evidence={"verification_output_check": "FAIL — file '%s' does not exist" % target},
        failure_reason="Claimed-verified file '%s' does not exist" % target,
    )


def _verify_claimed(claim: HighStakesClaim, project_root: str) -> VerificationOutcome:
    """Claim presence check: target file exists and is non-empty."""
    target = claim.target
    full_path = _resolve_path(target, project_root)
    if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
        return VerificationOutcome(
            claim=claim,
            verified=True,
            evidence={"claim_presence_check": "PASS — '%s' exists and non-empty" % target},
        )
    return VerificationOutcome(
        claim=claim,
        verified=False,
        evidence={"claim_presence_check": "FAIL — '%s' absent or empty" % target},
        failure_reason="Claimed artifact '%s' absent or empty" % target,
    )


def _verify_unknown(claim: HighStakesClaim, project_root: str) -> VerificationOutcome:
    return VerificationOutcome(
        claim=claim,
        verified=False,
        evidence={},
        failure_reason="Unknown verb '%s' — no verifier registered" % claim.verb,
    )


def _resolve_path(target: str, project_root: str) -> str:
    """Resolve target to an absolute path under project_root."""
    if os.path.isabs(target):
        return target
    return os.path.join(project_root, target)


# ── Report formatting ─────────────────────────────────────────────────────────

def format_report(outcomes: List[VerificationOutcome]) -> str:
    """Format VerificationOutcome list as a Markdown report for human review."""
    if not outcomes:
        return "## High-Stakes Claim Verification\n\nNo high-stakes claims detected.\n"

    lines = [
        "## High-Stakes Claim Verification",
        "",
        "| Verb | Target | Verified | Evidence |",
        "|------|--------|----------|----------|",
    ]

    verified_count = 0
    failed_count = 0

    for outcome in outcomes:
        verb = outcome.claim.verb
        target = outcome.claim.target[:50]
        status = "PASS" if outcome.verified else "FAIL"
        if outcome.verified:
            verified_count += 1
        else:
            failed_count += 1
        evidence_summary = "; ".join(
            "%s: %s" % (k, v[:60]) for k, v in outcome.evidence.items()
        ) or (outcome.failure_reason or "—")[:80]
        lines.append("| %s | %s | %s | %s |" % (verb, target, status, evidence_summary))

    lines.append("")
    lines.append("**Summary**: %d verified, %d failed out of %d claims." % (
        verified_count, failed_count, len(outcomes)
    ))
    if failed_count > 0:
        lines.append("")
        lines.append("### Failed Claims")
        for outcome in outcomes:
            if not outcome.verified and outcome.failure_reason:
                lines.append("- **%s** `%s`: %s" % (
                    outcome.claim.verb, outcome.claim.target, outcome.failure_reason
                ))

    return "\n".join(lines) + "\n"
