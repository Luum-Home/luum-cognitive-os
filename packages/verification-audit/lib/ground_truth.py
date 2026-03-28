"""Ground Truth Checker — Verify agent claims against filesystem reality.

Extracts verifiable claims from agent output (file creation, test counts,
build status, modification counts) and checks them against the actual
filesystem state. Produces a hallucination score indicating what fraction
of claims are false.

Usage:
    from lib.ground_truth import verify_all_claims, format_verification_report

    results = verify_all_claims(agent_output, project_root="/path/to/project")
    print(format_verification_report(results))

Python 3.9+ compatible.
Author: luum
"""

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Claim:
    """A single verifiable claim extracted from agent output."""

    text: str  # The original claim text
    claim_type: str  # file_exists, function_exists, test_passes, command_output, count
    target: str  # file path, function name, command
    expected: Optional[str] = None  # expected value (if applicable)


@dataclass
class VerificationResult:
    """Result of verifying a single claim against reality."""

    claim: Claim
    verified: bool  # True if claim matches reality
    actual: str  # What reality actually is
    discrepancy: Optional[str] = None  # Description of mismatch (if any)


# --- Claim extraction patterns ---

# "Created file X", "File X exists", "Wrote file X", "Generated X"
_FILE_CREATED_PATTERNS = [
    re.compile(
        r"(?:created|wrote|generated|added|producing)\s+"
        r"(?:file\s+|the\s+file\s+)?"
        r"[`\"']?([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)[`\"']?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:file|output)\s+[`\"']?([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)[`\"']?\s+"
        r"(?:has been |was )?(?:created|written|generated)",
        re.IGNORECASE,
    ),
]

# "Modified file X", "Updated file X", "Edited file X"
_FILE_MODIFIED_PATTERNS = [
    re.compile(
        r"(?:modified|updated|edited|changed|patched)\s+"
        r"(?:file\s+|the\s+file\s+)?"
        r"[`\"']?([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)[`\"']?",
        re.IGNORECASE,
    ),
    re.compile(
        r"[`\"']?([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)[`\"']?\s+"
        r"(?:has been |was )?(?:modified|updated|edited)",
        re.IGNORECASE,
    ),
]

# "N tests passing", "N tests collected", "N tests succeeded"
_TEST_COUNT_PATTERN = re.compile(
    r"(\d+)\s+tests?\s+(?:pass(?:ing|ed)?|collect(?:ed)?|succeed(?:ed)?|ran)",
    re.IGNORECASE,
)

# "Modified N files", "Changed N files", "Updated N files"
_FILE_COUNT_PATTERN = re.compile(
    r"(?:modified|changed|updated|created|edited)\s+(\d+)\s+files?",
    re.IGNORECASE,
)

# "Build succeeded", "Build passed", "Compilation successful"
_BUILD_SUCCESS_PATTERN = re.compile(
    r"(?:build|compilation)\s+(?:succeeded|passed|successful|complete)",
    re.IGNORECASE,
)

# "Lint clean", "No lint errors", "0 lint errors"
_LINT_CLEAN_PATTERN = re.compile(
    r"(?:lint\s+clean|no\s+lint\s+errors?|0\s+lint\s+(?:errors?|issues?))",
    re.IGNORECASE,
)

# "No errors", "0 errors", "0 failures"
_NO_ERRORS_PATTERN = re.compile(
    r"(?:no\s+errors?|0\s+errors?|0\s+failures?|zero\s+errors?)",
    re.IGNORECASE,
)

# "Function X in file Y" / "def X" / "func X"
_FUNCTION_PATTERN = re.compile(
    r"(?:function|method|def|func)\s+[`\"']?(\w+)[`\"']?\s+"
    r"(?:in|inside|within)\s+[`\"']?([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)[`\"']?",
    re.IGNORECASE,
)


def extract_claims(agent_output: str) -> List[Claim]:
    """Extract verifiable claims from agent output text.

    Detects patterns like:
    - "Created file X" / "File X exists" -> file_exists claim
    - "Function X in file Y" -> function_exists claim
    - "N tests passing" / "N tests collected" -> count claim
    - "Build succeeded" / "Lint clean" -> command_output claim
    - "Modified N files" -> count claim
    - "No errors" / "0 failures" -> command_output claim
    """
    claims: List[Claim] = []
    seen_targets: set = set()

    # File creation claims
    for pattern in _FILE_CREATED_PATTERNS:
        for match in pattern.finditer(agent_output):
            filepath = match.group(1)
            if filepath not in seen_targets and _is_plausible_path(filepath):
                seen_targets.add(filepath)
                claims.append(
                    Claim(
                        text="Created %s" % filepath,
                        claim_type="file_exists",
                        target=filepath,
                    )
                )

    # File modification claims
    for pattern in _FILE_MODIFIED_PATTERNS:
        for match in pattern.finditer(agent_output):
            filepath = match.group(1)
            if filepath not in seen_targets and _is_plausible_path(filepath):
                seen_targets.add(filepath)
                claims.append(
                    Claim(
                        text="Modified %s" % filepath,
                        claim_type="file_exists",
                        target=filepath,
                    )
                )

    # Test count claims
    for match in _TEST_COUNT_PATTERN.finditer(agent_output):
        count = match.group(1)
        claim_text = match.group(0).strip()
        claims.append(
            Claim(
                text=claim_text,
                claim_type="count",
                target="test_count",
                expected=count,
            )
        )

    # File count claims
    for match in _FILE_COUNT_PATTERN.finditer(agent_output):
        count = match.group(1)
        claim_text = match.group(0).strip()
        claims.append(
            Claim(
                text=claim_text,
                claim_type="count",
                target="file_count",
                expected=count,
            )
        )

    # Build success claims
    for match in _BUILD_SUCCESS_PATTERN.finditer(agent_output):
        claims.append(
            Claim(
                text=match.group(0).strip(),
                claim_type="command_output",
                target="build",
                expected="success",
            )
        )

    # Lint clean claims
    for match in _LINT_CLEAN_PATTERN.finditer(agent_output):
        claims.append(
            Claim(
                text=match.group(0).strip(),
                claim_type="command_output",
                target="lint",
                expected="clean",
            )
        )

    # No errors claims
    for match in _NO_ERRORS_PATTERN.finditer(agent_output):
        claims.append(
            Claim(
                text=match.group(0).strip(),
                claim_type="command_output",
                target="errors",
                expected="0",
            )
        )

    # Function exists claims
    for match in _FUNCTION_PATTERN.finditer(agent_output):
        func_name = match.group(1)
        filepath = match.group(2)
        target_key = "%s:%s" % (filepath, func_name)
        if target_key not in seen_targets and _is_plausible_path(filepath):
            seen_targets.add(target_key)
            claims.append(
                Claim(
                    text="Function %s in %s" % (func_name, filepath),
                    claim_type="function_exists",
                    target="%s:%s" % (filepath, func_name),
                )
            )

    return claims


def _is_plausible_path(path: str) -> bool:
    """Check if a string looks like a plausible file path."""
    if not path or len(path) < 3:
        return False
    # Must have at least one path separator or start with a known prefix
    if "/" not in path and "\\" not in path:
        # Single filename is OK if it has an extension
        parts = path.rsplit(".", 1)
        if len(parts) != 2 or len(parts[1]) > 10:
            return False
    # Reject common false positives
    false_positives = {
        "e.g.",
        "i.e.",
        "etc.",
        "vs.",
        "no.",
        "v1.0",
        "v2.0",
        "v0.1",
    }
    if path.lower() in false_positives:
        return False
    return True


def verify_claim(claim: Claim, project_root: str) -> VerificationResult:
    """Verify a single claim against reality.

    For file_exists: os.path.exists(target)
    For function_exists: grep for function definition in file
    For count: not auto-verified (marked as unverifiable)
    For command_output: not auto-verified (marked as unverifiable)
    """
    if claim.claim_type == "file_exists":
        return _verify_file_exists(claim, project_root)
    elif claim.claim_type == "function_exists":
        return _verify_function_exists(claim, project_root)
    elif claim.claim_type == "count":
        return _verify_count(claim, project_root)
    elif claim.claim_type == "command_output":
        # Command output claims are not auto-verified to avoid running
        # arbitrary commands. They are flagged for manual verification.
        return VerificationResult(
            claim=claim,
            verified=False,
            actual="Not auto-verified (requires command execution)",
            discrepancy=None,
        )
    else:
        return VerificationResult(
            claim=claim,
            verified=False,
            actual="Unknown claim type: %s" % claim.claim_type,
            discrepancy="Cannot verify unknown claim type",
        )


def _verify_file_exists(claim: Claim, project_root: str) -> VerificationResult:
    """Verify that a claimed file actually exists."""
    target = claim.target

    # Try absolute path first
    if os.path.isabs(target):
        exists = os.path.isfile(target)
        if exists:
            size = os.path.getsize(target)
            line_count = _count_lines(target)
            return VerificationResult(
                claim=claim,
                verified=True,
                actual="File exists (%d lines, %d bytes)" % (line_count, size),
            )
        return VerificationResult(
            claim=claim,
            verified=False,
            actual="File does NOT exist at %s" % target,
            discrepancy="Claimed file does not exist",
        )

    # Try relative to project root
    full_path = os.path.join(project_root, target)
    if os.path.isfile(full_path):
        size = os.path.getsize(full_path)
        line_count = _count_lines(full_path)
        return VerificationResult(
            claim=claim,
            verified=True,
            actual="File exists (%d lines, %d bytes)" % (line_count, size),
        )

    return VerificationResult(
        claim=claim,
        verified=False,
        actual="File does NOT exist at %s" % full_path,
        discrepancy="Claimed file does not exist",
    )


def _verify_function_exists(claim: Claim, project_root: str) -> VerificationResult:
    """Verify that a claimed function exists in a file."""
    parts = claim.target.split(":", 1)
    if len(parts) != 2:
        return VerificationResult(
            claim=claim,
            verified=False,
            actual="Invalid target format: %s" % claim.target,
            discrepancy="Cannot parse file:function format",
        )

    filepath, func_name = parts

    # Resolve path
    if not os.path.isabs(filepath):
        filepath = os.path.join(project_root, filepath)

    if not os.path.isfile(filepath):
        return VerificationResult(
            claim=claim,
            verified=False,
            actual="File %s does not exist" % filepath,
            discrepancy="File containing claimed function does not exist",
        )

    # Search for function definition
    pattern = r"(?:def|func|function|fn)\s+%s\b" % re.escape(func_name)
    try:
        with open(filepath, "r", errors="replace") as f:
            content = f.read()
        if re.search(pattern, content):
            return VerificationResult(
                claim=claim,
                verified=True,
                actual="Function '%s' found in %s" % (func_name, filepath),
            )
        return VerificationResult(
            claim=claim,
            verified=False,
            actual="Function '%s' NOT found in %s" % (func_name, filepath),
            discrepancy="Claimed function does not exist in the file",
        )
    except (OSError, IOError):
        return VerificationResult(
            claim=claim,
            verified=False,
            actual="Could not read file %s" % filepath,
            discrepancy="File unreadable",
        )


def _verify_count(claim: Claim, project_root: str) -> VerificationResult:
    """Verify count claims (test count, file count).

    Test counts require running the test suite which is too slow for
    inline verification. We mark them as unverifiable with a suggestion.
    File counts are verified via filesystem traversal when feasible.
    """
    if claim.target == "test_count":
        return VerificationResult(
            claim=claim,
            verified=False,
            actual="Not auto-verified (requires running test suite)",
            discrepancy=None,
        )
    elif claim.target == "file_count":
        # We cannot verify file_count without knowing which files were
        # supposed to be counted. Mark as unverifiable.
        return VerificationResult(
            claim=claim,
            verified=False,
            actual="Not auto-verified (scope of counted files unknown)",
            discrepancy=None,
        )
    return VerificationResult(
        claim=claim,
        verified=False,
        actual="Unknown count target: %s" % claim.target,
        discrepancy=None,
    )


def _count_lines(filepath: str) -> int:
    """Count lines in a file."""
    try:
        with open(filepath, "r", errors="replace") as f:
            return sum(1 for _ in f)
    except (OSError, IOError):
        return 0


def verify_all_claims(agent_output: str, project_root: str) -> Dict:
    """Extract and verify all claims in agent output.

    Returns a dict with:
        total: int - total claims found
        verified: int - claims confirmed true
        failed: int - claims confirmed false (hallucinations)
        unverifiable: int - claims that cannot be auto-checked
        results: List[VerificationResult] - all results
        hallucination_score: float - 0.0=all true, 1.0=all false
            (only counts verifiable claims in the denominator)
    """
    claims = extract_claims(agent_output)
    results: List[VerificationResult] = []
    verified = 0
    failed = 0
    unverifiable = 0

    for claim in claims:
        result = verify_claim(claim, project_root)
        results.append(result)
        if result.discrepancy is None and not result.verified:
            unverifiable += 1
        elif result.verified:
            verified += 1
        else:
            failed += 1

    verifiable_total = verified + failed
    hallucination_score = 0.0
    if verifiable_total > 0:
        hallucination_score = round(failed / verifiable_total, 4)

    return {
        "total": len(claims),
        "verified": verified,
        "failed": failed,
        "unverifiable": unverifiable,
        "results": results,
        "hallucination_score": hallucination_score,
    }


def format_verification_report(results: Dict) -> str:
    """Format verification results as a markdown report.

    Returns a human-readable table with claim verification status.
    """
    lines = ["## Ground Truth Verification", ""]

    if results["total"] == 0:
        lines.append("No verifiable claims detected in agent output.")
        return "\n".join(lines)

    lines.append("| Claim | Type | Verified? | Actual |")
    lines.append("|-------|------|-----------|--------|")

    for vr in results["results"]:
        claim_text = vr.claim.text[:50]
        claim_type = vr.claim.claim_type
        if vr.verified:
            status = "PASS"
        elif vr.discrepancy is None and not vr.verified:
            status = "UNVERIFIED"
        else:
            status = "FAIL"
        actual = vr.actual[:60]
        lines.append("| %s | %s | %s | %s |" % (claim_text, claim_type, status, actual))

    lines.append("")
    lines.append(
        "Hallucination Score: %.2f (%d of %d verifiable claims false)"
        % (
            results["hallucination_score"],
            results["failed"],
            results["verified"] + results["failed"],
        )
    )

    return "\n".join(lines)
