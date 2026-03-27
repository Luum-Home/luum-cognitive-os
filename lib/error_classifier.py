"""Structured error classification for Cognitive OS.

Classifies error text and exit codes into structured categories with
associated retry strategies. Used by error-learning, auto-repair, and
the ClaudeExecutor retry logic.

Usage:
    from lib.error_classifier import classify_error, get_retry_strategy, ErrorCategory

    category = classify_error("401 Unauthorized", exit_code=1)
    strategy = get_retry_strategy(category)
    print(strategy["retryable"])  # False

Python 3.9+ compatible.
"""

import re
from enum import Enum
from typing import Dict, Optional, Union


class ErrorCategory(Enum):
    """Structured error categories for classification."""

    AUTH = "auth"
    RATE_LIMIT = "rate_limit"
    CONTEXT_OVERFLOW = "context_overflow"
    TIMEOUT = "timeout"
    BUILD_FAILURE = "build_failure"
    TEST_FAILURE = "test_failure"
    LINT_ERROR = "lint_error"
    NETWORK = "network"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    UNKNOWN = "unknown"


# Pattern definitions: list of (compiled regex, category) tuples.
# Order matters -- first match wins. More specific patterns come first.
_PATTERNS = [
    # Auth / authorization
    (re.compile(r"\b401\b|unauthorized|authentication failed|invalid.*token|"
                r"forbidden|403\b|access denied|invalid.*api.?key|"
                r"credentials.*invalid|auth.*error|not authenticated",
                re.IGNORECASE), ErrorCategory.AUTH),

    # Rate limiting
    (re.compile(r"\b429\b|rate.?limit|too many requests|throttl|"
                r"quota exceeded|retry.?after",
                re.IGNORECASE), ErrorCategory.RATE_LIMIT),

    # Context overflow
    (re.compile(r"context.*(overflow|exceeded|limit|window|length)|"
                r"token.*(limit|exceeded|maximum)|"
                r"maximum.*context|input.*too.*long|"
                r"prompt.*too.*long",
                re.IGNORECASE), ErrorCategory.CONTEXT_OVERFLOW),

    # Timeout
    (re.compile(r"timed?\s*out|timeout|deadline exceeded|"
                r"ETIMEDOUT|operation.*expired|"
                r"read timeout|connect timeout|"
                r"request timeout",
                re.IGNORECASE), ErrorCategory.TIMEOUT),

    # Test failures (before build, since test output can contain "build" words)
    (re.compile(r"\bFAIL\b|assertion.*error|assert.*fail|"
                r"test.*fail|expected.*but.*got|"
                r"tests?\s+failed|failing\s+tests?|"
                r"AssertionError|assertEqual|"
                r"pytest.*FAILED|jest.*fail",
                re.IGNORECASE), ErrorCategory.TEST_FAILURE),

    # Lint errors
    (re.compile(r"lint.*error|linting.*fail|eslint|golangci-lint|"
                r"flake8|pylint|stylelint|"
                r"tsc.*error|type.*check.*fail|go\s+vet|"
                r"no-unused-vars|no-undef",
                re.IGNORECASE), ErrorCategory.LINT_ERROR),

    # Build / compilation failures
    (re.compile(r"build.*fail|compilation.*error|compile.*error|"
                r"cannot.*compile|undefined.*reference|"
                r"linker.*error|make.*error|"
                r"cannot find module|module.*not found|"
                r"import.*error|no such module",
                re.IGNORECASE), ErrorCategory.BUILD_FAILURE),

    # Network
    (re.compile(r"ECONNREFUSED|ECONNRESET|ENOTFOUND|"
                r"connection.*refused|connection.*reset|"
                r"network.*error|dns.*resolution|"
                r"host.*not.*found|no.*route.*host|"
                r"socket.*error|ENETUNREACH|"
                r"ERR_CONNECTION|fetch.*failed",
                re.IGNORECASE), ErrorCategory.NETWORK),

    # Permission
    (re.compile(r"permission.*denied|EACCES|EPERM|"
                r"operation.*not.*permitted|"
                r"insufficient.*permissions|"
                r"read-?only.*file.*system",
                re.IGNORECASE), ErrorCategory.PERMISSION),

    # Not found
    (re.compile(r"\b404\b|not.?found|ENOENT|"
                r"no such file|file.*not.*exist|"
                r"does not exist|cannot find|"
                r"FileNotFoundError|path.*not.*found",
                re.IGNORECASE), ErrorCategory.NOT_FOUND),

    # Syntax errors
    (re.compile(r"syntax.*error|SyntaxError|"
                r"unexpected.*token|parse.*error|"
                r"invalid.*syntax|unterminated.*string|"
                r"missing.*semicolon|unexpected.*end",
                re.IGNORECASE), ErrorCategory.SYNTAX),

    # Runtime errors (broad catch)
    (re.compile(r"runtime.*error|panic|segfault|"
                r"SIGSEGV|SIGABRT|stack.*overflow|"
                r"null.*pointer|NullPointerException|"
                r"TypeError|ReferenceError|"
                r"unhandled.*exception|uncaught.*exception|"
                r"index.*out.*of.*range|KeyError|"
                r"ZeroDivisionError",
                re.IGNORECASE), ErrorCategory.RUNTIME),
]

# Retry strategies per category
_RETRY_STRATEGIES: Dict[ErrorCategory, Dict[str, Union[bool, int, str]]] = {
    ErrorCategory.AUTH: {
        "retryable": False,
        "max_retries": 0,
        "backoff": "none",
        "action": "Fix credentials or permissions before retrying.",
    },
    ErrorCategory.RATE_LIMIT: {
        "retryable": True,
        "max_retries": 5,
        "backoff": "exponential",
        "action": "Wait and retry with exponential backoff.",
    },
    ErrorCategory.CONTEXT_OVERFLOW: {
        "retryable": False,
        "max_retries": 0,
        "backoff": "none",
        "action": "Reduce input size or split the task.",
    },
    ErrorCategory.TIMEOUT: {
        "retryable": True,
        "max_retries": 3,
        "backoff": "exponential",
        "action": "Retry with increased timeout or reduced scope.",
    },
    ErrorCategory.BUILD_FAILURE: {
        "retryable": False,
        "max_retries": 0,
        "backoff": "none",
        "action": "Fix the build error before retrying.",
    },
    ErrorCategory.TEST_FAILURE: {
        "retryable": False,
        "max_retries": 0,
        "backoff": "none",
        "action": "Fix the failing test before retrying.",
    },
    ErrorCategory.LINT_ERROR: {
        "retryable": False,
        "max_retries": 0,
        "backoff": "none",
        "action": "Fix lint violations before retrying.",
    },
    ErrorCategory.NETWORK: {
        "retryable": True,
        "max_retries": 3,
        "backoff": "exponential",
        "action": "Retry after checking network connectivity.",
    },
    ErrorCategory.PERMISSION: {
        "retryable": False,
        "max_retries": 0,
        "backoff": "none",
        "action": "Fix file or system permissions.",
    },
    ErrorCategory.NOT_FOUND: {
        "retryable": False,
        "max_retries": 0,
        "backoff": "none",
        "action": "Verify the resource path or URL exists.",
    },
    ErrorCategory.SYNTAX: {
        "retryable": False,
        "max_retries": 0,
        "backoff": "none",
        "action": "Fix the syntax error in source code.",
    },
    ErrorCategory.RUNTIME: {
        "retryable": False,
        "max_retries": 0,
        "backoff": "none",
        "action": "Debug the runtime error and fix the root cause.",
    },
    ErrorCategory.UNKNOWN: {
        "retryable": True,
        "max_retries": 1,
        "backoff": "linear",
        "action": "Investigate the error and retry once.",
    },
}


def classify_error(
    error_text: str,
    exit_code: Optional[int] = None,
) -> ErrorCategory:
    """Classify an error into a structured category based on text patterns and exit code.

    Scans the error text against known patterns. If no text pattern matches,
    falls back to exit code heuristics. Returns UNKNOWN if nothing matches.

    Args:
        error_text: The error message or output text.
        exit_code: Optional process exit code for additional context.

    Returns:
        The matching ErrorCategory.
    """
    if not error_text and exit_code is None:
        return ErrorCategory.UNKNOWN

    # Try text pattern matching first
    for pattern, category in _PATTERNS:
        if pattern.search(error_text):
            return category

    # Fallback: exit code heuristics
    if exit_code is not None:
        if exit_code == 126:
            return ErrorCategory.PERMISSION
        if exit_code == 127:
            return ErrorCategory.NOT_FOUND
        if exit_code == 137:
            return ErrorCategory.TIMEOUT  # OOM kill / SIGKILL often from timeout
        if exit_code == 139:
            return ErrorCategory.RUNTIME  # SIGSEGV

    return ErrorCategory.UNKNOWN


def get_retry_strategy(category: ErrorCategory) -> Dict[str, Union[bool, int, str]]:
    """Return retry strategy for an error category.

    Args:
        category: The error category to look up.

    Returns:
        Dict with keys: retryable (bool), max_retries (int),
        backoff (str: "none"|"linear"|"exponential"), action (str).
    """
    return dict(_RETRY_STRATEGIES.get(category, _RETRY_STRATEGIES[ErrorCategory.UNKNOWN]))


def format_classified_error(
    error_text: str,
    category: ErrorCategory,
) -> str:
    """Format error with category prefix for structured logging.

    Args:
        error_text: The original error text.
        category: The classified category.

    Returns:
        Formatted string like "[AUTH] 401 Unauthorized..."
    """
    label = category.value.upper()
    # Truncate long error text for log friendliness
    truncated = error_text[:500].strip()
    if len(error_text) > 500:
        truncated += "..."
    return "[%s] %s" % (label, truncated)
