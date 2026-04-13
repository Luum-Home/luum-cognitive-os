# scope: both
"""Cross Verifier — Use a second model to verify primary model output.

Provides independent verification by asking a DIFFERENT model to review
the primary model's output. The verifier forms an independent opinion
without seeing the original model's trust score or self-assessment.

Usage:
    from lib.cross_verifier import cross_verify, should_cross_verify

    if should_cross_verify(task, output):
        cv = cross_verify(task, output, verifier_model="haiku")
        print(cv.agreement, cv.confidence, cv.discrepancies)

Works without ClaudeExecutor — returns a skipped result when unavailable.
Python 3.9+ compatible.
Author: luum
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CrossVerification:
    """Result of cross-verification by a second model."""

    original_model: str
    verifier_model: str
    original_output: str
    verification_prompt: str
    verifier_response: str
    agreement: bool
    confidence: float  # 0.0-1.0
    discrepancies: List[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


def build_verification_prompt(task: str, output: str) -> str:
    """Build a prompt for the verifier model.

    The prompt asks the verifier to:
    1. Check if the output actually addresses the task
    2. Look for claims that seem incorrect or unsubstantiated
    3. Identify potential hallucinations (made-up files, functions, test results)
    4. Rate confidence in the output (0-100)
    5. List any specific discrepancies found

    IMPORTANT: The verifier does NOT see the original model's trust score
    or self-assessment — it forms an independent opinion.
    """
    # Truncate output to avoid blowing up the verifier's context
    max_output_len = 8000
    truncated_output = output[:max_output_len]
    if len(output) > max_output_len:
        truncated_output += "\n\n[... truncated, %d chars total ...]" % len(output)

    return (
        "You are a verification agent. Your job is to independently assess "
        "whether the following agent output is truthful and complete.\n\n"
        "## Original Task\n%s\n\n"
        "## Agent Output to Verify\n%s\n\n"
        "## Your Assessment\n"
        "Analyze the output and respond with EXACTLY this format:\n\n"
        "AGREEMENT: YES or NO\n"
        "CONFIDENCE: <number 0-100>\n"
        "DISCREPANCIES:\n"
        "- <discrepancy 1 or NONE>\n"
        "- <discrepancy 2>\n\n"
        "Rules:\n"
        "- Check if file paths mentioned look plausible\n"
        "- Check if claimed test counts seem reasonable\n"
        "- Check if the output actually addresses the original task\n"
        "- Look for made-up function names, file paths, or test results\n"
        "- Look for claims without evidence (\"I verified\" without showing output)\n"
        "- Be skeptical but fair — not everything needs proof\n"
        "- Do NOT invent discrepancies where none exist\n"
    ) % (task[:3000], truncated_output)


def _parse_verifier_response(response: str) -> tuple:
    """Parse the verifier's structured response.

    Returns (agreement: bool, confidence: float, discrepancies: List[str]).
    """
    agreement = True
    confidence = 0.5
    discrepancies: List[str] = []

    # Parse AGREEMENT
    agreement_match = re.search(
        r"AGREEMENT:\s*(YES|NO|yes|no|Yes|No)", response
    )
    if agreement_match:
        agreement = agreement_match.group(1).upper() == "YES"

    # Parse CONFIDENCE
    confidence_match = re.search(r"CONFIDENCE:\s*(\d+)", response)
    if confidence_match:
        raw = int(confidence_match.group(1))
        confidence = max(0.0, min(1.0, raw / 100.0))

    # Parse DISCREPANCIES
    discrepancy_section = False
    for line in response.split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith("DISCREPANCIES"):
            discrepancy_section = True
            continue
        if discrepancy_section:
            if stripped.startswith("- "):
                text = stripped[2:].strip()
                if text.upper() != "NONE" and text:
                    discrepancies.append(text)
            elif stripped and not stripped.startswith("-"):
                # End of discrepancies section
                discrepancy_section = False

    return agreement, confidence, discrepancies


def cross_verify(
    task: str,
    output: str,
    verifier_model: str = "haiku",
    original_model: str = "unknown",
) -> CrossVerification:
    """Run cross-verification using a different model.

    Default verifier is haiku (cheapest) for cost efficiency.
    For critical tasks, use sonnet or opus.

    Cost: ~$0.002 per verification (haiku)

    If ClaudeExecutor is not available, returns a CrossVerification with
    agreement=True and a note saying cross-verification was skipped.
    """
    prompt = build_verification_prompt(task, output)

    # Try to import and use ClaudeExecutor
    try:
        from lib.claude_executor import ClaudeExecutor

        executor = ClaudeExecutor(default_model=verifier_model, default_timeout=120)
        result = executor.run(prompt, model=verifier_model)

        if not result.success:
            logger.warning(
                "Cross-verification failed: %s", result.error_message[:200]
            )
            return CrossVerification(
                original_model=original_model,
                verifier_model=verifier_model,
                original_output=output[:500],
                verification_prompt=prompt[:500],
                verifier_response="",
                agreement=True,
                confidence=0.0,
                discrepancies=[],
                skipped=True,
                skip_reason="Verifier execution failed: %s"
                % result.error_message[:200],
            )

        agreement, confidence, discrepancies = _parse_verifier_response(
            result.result_text
        )

        return CrossVerification(
            original_model=original_model,
            verifier_model=verifier_model,
            original_output=output[:500],
            verification_prompt=prompt[:500],
            verifier_response=result.result_text[:2000],
            agreement=agreement,
            confidence=confidence,
            discrepancies=discrepancies,
        )

    except ImportError:
        logger.debug("ClaudeExecutor not available, skipping cross-verification")
        return CrossVerification(
            original_model=original_model,
            verifier_model=verifier_model,
            original_output=output[:500],
            verification_prompt=prompt[:500],
            verifier_response="",
            agreement=True,
            confidence=0.0,
            discrepancies=[],
            skipped=True,
            skip_reason="Cross-verification skipped (executor not available)",
        )
    except Exception as e:
        logger.warning("Cross-verification error: %s", e)
        return CrossVerification(
            original_model=original_model,
            verifier_model=verifier_model,
            original_output=output[:500],
            verification_prompt=prompt[:500],
            verifier_response="",
            agreement=True,
            confidence=0.0,
            discrepancies=[],
            skipped=True,
            skip_reason="Cross-verification error: %s" % str(e),
        )


def should_cross_verify(
    task: str,
    output: str,
    trust_score: Optional[int] = None,
    phase: str = "reconstruction",
    complexity: str = "small",
) -> bool:
    """Decide if cross-verification is needed.

    YES if:
    - Task involves deletion or destructive operations
    - Output claims >10 files modified
    - Output has low trust score (<70)
    - Task is in production/maintenance phase
    - Task complexity is large/critical

    NO if:
    - Task is trivial (single file, <20 lines)
    - Output is documentation-only
    - Dry-run mode
    """
    import os

    # Skip in dry-run mode
    if os.environ.get("DRY_RUN", "").lower() == "true":
        return False

    # Always verify in production/maintenance
    if phase in ("production", "maintenance"):
        return True

    # Always verify large/critical tasks
    if complexity in ("large", "critical"):
        return True

    # Low trust score
    if trust_score is not None and trust_score < 70:
        return True

    # Destructive operations
    destructive_keywords = [
        "delete",
        "remove",
        "drop",
        "destroy",
        "truncate",
        "wipe",
        "purge",
    ]
    task_lower = task.lower()
    if any(kw in task_lower for kw in destructive_keywords):
        return True

    # Many files modified
    file_count_match = re.search(
        r"(?:modified|changed|updated|created)\s+(\d+)\s+files?",
        output,
        re.IGNORECASE,
    )
    if file_count_match:
        count = int(file_count_match.group(1))
        if count > 10:
            return True

    # Documentation-only output (skip)
    if _is_doc_only(output):
        return False

    # Trivial task (skip)
    if complexity == "trivial":
        return False

    return False


def _is_doc_only(output: str) -> bool:
    """Heuristic: check if output is documentation-only."""
    output_lower = output.lower()
    doc_indicators = ["readme", "documentation", "changelog", ".md"]
    code_indicators = [
        ".go",
        ".py",
        ".ts",
        ".js",
        ".java",
        "def ",
        "func ",
        "function ",
        "class ",
        "import ",
    ]

    doc_score = sum(1 for d in doc_indicators if d in output_lower)
    code_score = sum(1 for c in code_indicators if c in output_lower)

    return doc_score > 0 and code_score == 0


def format_cross_verification(cv: CrossVerification) -> str:
    """Format cross-verification result as part of a trust report."""
    lines = ["### Cross-Verification"]

    if cv.skipped:
        lines.append("")
        lines.append("Status: SKIPPED")
        lines.append("Reason: %s" % cv.skip_reason)
        return "\n".join(lines)

    lines.append("")
    lines.append(
        "Verifier: %s (independent from %s)" % (cv.verifier_model, cv.original_model)
    )
    lines.append("Agreement: %s" % ("YES" if cv.agreement else "NO"))
    lines.append("Confidence: %.0f%%" % (cv.confidence * 100))

    if cv.discrepancies:
        lines.append("")
        lines.append("Discrepancies found:")
        for d in cv.discrepancies:
            lines.append("- %s" % d)
    else:
        lines.append("No discrepancies found.")

    return "\n".join(lines)
