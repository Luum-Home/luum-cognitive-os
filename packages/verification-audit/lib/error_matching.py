# scope: both
"""
Error signature matching for the Cognitive OS error learning system.

Normalizes error messages, calculates similarity between error signatures,
and finds matching known errors. Used by the error-pattern-detector and
auto-repair systems to identify recurring error patterns.

Python 3.9+ compatible. No external dependencies.
"""

import re
from typing import Dict, List, Optional


# Patterns to strip during normalization
_NUMBER_PATTERN = re.compile(r"\b\d+\b")
_PATH_PATTERN = re.compile(
    r"(?:/[\w.\-]+)+/?|(?:[A-Za-z]:\\[\w.\-\\]+)"
)
_TIMESTAMP_PATTERN = re.compile(
    r"\d{4}[-/]\d{2}[-/]\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
)
_HEX_PATTERN = re.compile(r"\b0x[0-9a-fA-F]+\b")
_UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_WHITESPACE_PATTERN = re.compile(r"\s+")

# Patterns that indicate an error in bash output
_ERROR_INDICATORS = [
    re.compile(r"^.*(?:ERROR|error|Error):?\s*(.+)", re.MULTILINE),
    re.compile(r"^.*(?<!0 )(?:FAIL|FAILED|fail|failed):?\s*(.+)", re.MULTILINE),
    re.compile(r"^.*(?:panic):?\s*(.+)", re.MULTILINE),
    re.compile(r"^.*(?:Exception|exception):?\s*(.+)", re.MULTILINE),
    re.compile(r"^.*(?:fatal|FATAL):?\s*(.+)", re.MULTILINE),
    re.compile(r"^.*(?:Traceback \(most recent call last\))", re.MULTILINE),
    re.compile(r"^.*(?:AssertionError|TypeError|ValueError|KeyError|ImportError|ModuleNotFoundError):?\s*(.+)", re.MULTILINE),
]


def normalize_signature(error_text: str) -> str:
    """Strip numbers, paths, timestamps from error text. Return first 200 chars lowercase.

    Normalization removes volatile parts of error messages (line numbers, file paths,
    timestamps, UUIDs, hex addresses) so that structurally identical errors produce
    the same signature regardless of runtime-specific values.

    Args:
        error_text: Raw error message text.

    Returns:
        Normalized signature string, lowercase, max 200 characters.
    """
    if not error_text:
        return ""

    text = error_text

    # Strip timestamps first (before numbers, since timestamps contain numbers)
    text = _TIMESTAMP_PATTERN.sub("", text)

    # Strip UUIDs
    text = _UUID_PATTERN.sub("", text)

    # Strip hex addresses
    text = _HEX_PATTERN.sub("", text)

    # Strip file paths
    text = _PATH_PATTERN.sub("", text)

    # Strip remaining numbers
    text = _NUMBER_PATTERN.sub("", text)

    # Collapse whitespace
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()

    # Lowercase and truncate
    return text.lower()[:200]


def calculate_similarity(sig_a: str, sig_b: str) -> float:
    """Jaccard similarity on word sets. Returns 0.0-1.0.

    Computes the Jaccard index (intersection over union) of the word sets
    from two normalized signatures. This is a simple but effective measure
    for error message similarity.

    Args:
        sig_a: First normalized signature.
        sig_b: Second normalized signature.

    Returns:
        Float between 0.0 (completely different) and 1.0 (identical word sets).
    """
    if not sig_a and not sig_b:
        return 1.0
    if not sig_a or not sig_b:
        return 0.0

    words_a = set(sig_a.split())
    words_b = set(sig_b.split())

    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)


def find_matching_error(
    new_error: str, known_errors: List[Dict], threshold: float = 0.7
) -> Optional[Dict]:
    """Find best matching known error with similarity >= threshold.

    Normalizes the new error, compares against all known errors, and returns
    the best match if its similarity meets the threshold.

    Args:
        new_error: Raw error text to match.
        known_errors: List of dicts, each with at least a "message" or "error" key
                      containing the error text. May also have "signature" key with
                      a pre-computed normalized signature.
        threshold: Minimum similarity score to consider a match. Default 0.7.

    Returns:
        The best matching known error dict with an added "similarity" key,
        or None if no match meets the threshold.
    """
    if not new_error or not known_errors:
        return None

    new_sig = normalize_signature(new_error)
    if not new_sig:
        return None

    best_match: Optional[Dict] = None
    best_score = 0.0

    for known in known_errors:
        # Extract the error text from the known error dict
        known_text = known.get("signature") or known.get("message") or known.get("error", "")
        if not known_text:
            continue

        # If the known error already has a normalized signature, use it directly
        if "signature" in known:
            known_sig = known["signature"]
        else:
            known_sig = normalize_signature(known_text)

        score = calculate_similarity(new_sig, known_sig)

        if score >= threshold and score > best_score:
            best_score = score
            best_match = dict(known)
            best_match["similarity"] = score

    return best_match


def extract_error_signature(bash_output: str) -> Optional[str]:
    """Extract the error message from bash output.

    Searches for common error indicators (ERROR, FAIL, panic, Exception, etc.)
    and returns the first matched error line. Returns None if the output
    appears to be successful (no error indicators found).

    Args:
        bash_output: Raw output from a bash command (stdout + stderr).

    Returns:
        The extracted error message string, or None if no error is detected.
    """
    if not bash_output:
        return None

    for pattern in _ERROR_INDICATORS:
        match = pattern.search(bash_output)
        if match:
            # If there's a capture group, use it; otherwise use the full match
            if match.lastindex and match.lastindex >= 1:
                error_msg = match.group(1).strip()
            else:
                error_msg = match.group(0).strip()

            if error_msg:
                return error_msg

    return None
