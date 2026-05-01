# SCOPE: both
# scope: both
"""Structured error classification for Cognitive OS.

TWO APIs in this module:

1. Text/exit-code classifier (original):
       classify_error(text, exit_code) -> ErrorCategory
       get_retry_strategy(category) -> dict
   Used by error-learning, auto-repair, and ClaudeExecutor retry logic.

2. JSONL taxonomy layer (ADR-080 Tier 2 #6):
       classify(record: dict) -> ErrorClass
       classify_jsonl(path: Path) -> list[ClassifiedError]
   Classifies raw records from error-learning.jsonl into structured
   categories with severity, transience, and suggested actions.
   Adapted from Hermes agent/error_classifier.py (MIT).
   See .cognitive-os/adoption-registry.yaml for license record.

   Optional LLM deep classify: set COS_ERROR_DEEP_CLASSIFY=1.
   Default behaviour is unchanged: error-learning.jsonl keeps appending
   raw entries via hooks/error-pipeline.sh. Classification is on-demand.

Python 3.9+ compatible.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

_DEFAULT_ERRORS_PATH = ".cognitive-os/metrics/error-learning.jsonl"


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


# ── JSONL taxonomy layer (ADR-080 Tier 2 #6) ────────────────────────────────
# Adapted from Hermes agent/error_classifier.py (MIT).
# This section adds a record-oriented API on top of the text classifier above.
# The two APIs are independent; existing callers of classify_error() are
# unaffected.

class RecordCategory(str, Enum):
    """Semantic category for a COS error-learning.jsonl record.

    Distinct from ErrorCategory (which is an older enum used by the text
    classifier) to avoid breaking existing callers. The values intentionally
    mirror the COS hook TYPE names where possible.
    """
    rate_limit       = "rate_limit"
    auth             = "auth"
    validation       = "validation"
    network          = "network"
    file_not_found   = "file_not_found"
    permission       = "permission"
    timeout          = "timeout"
    integration      = "integration"
    test_failure     = "test_failure"
    lint_error       = "lint_error"
    build_error      = "build_error"
    context_overflow = "context_overflow"
    unknown          = "unknown"


class RecordSeverity(str, Enum):
    critical = "critical"
    high     = "high"
    medium   = "medium"
    low      = "low"
    info     = "info"


class Transience(str, Enum):
    yes     = "yes"      # Will resolve on its own / with a retry
    no      = "no"       # Requires human action or code change
    unknown = "unknown"


@dataclass
class ErrorClass:
    """Classification result for a single error-learning.jsonl record."""

    category: RecordCategory
    severity: RecordSeverity
    transient: Transience
    suggested_action: str
    raw: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "transient": self.transient.value,
            "suggested_action": self.suggested_action,
            **{k: v for k, v in self.raw.items()
               if k not in ("category", "severity", "transient", "suggested_action")},
        }


@dataclass
class ClassifiedError:
    """A raw error record paired with its classification."""

    record: Dict[str, Any]
    classification: ErrorClass

    @property
    def category(self) -> RecordCategory:
        return self.classification.category

    @property
    def timestamp_epoch(self) -> Optional[float]:
        v = self.record.get("timestamp_epoch")
        return float(v) if v is not None else None

    @property
    def error_type(self) -> str:
        return self.record.get("type", "UNKNOWN")

    @property
    def fingerprint(self) -> str:
        return self.record.get("fingerprint", "")


# Pattern tables (adapted from Hermes, MIT)
_RL_PATTERNS = [
    "rate limit", "rate_limit", "too many requests", "throttled",
    "requests per minute", "tokens per minute", "try again in",
    "please retry after", "resource_exhausted", "throttlingexception",
]
_AUTH_MSG_PATTERNS = [
    "invalid api key", "invalid_api_key", "authentication", "unauthorized",
    "forbidden", "invalid token", "token expired", "access denied",
]
_NET_PATTERNS = [
    "connection refused", "connection reset", "network unreachable",
    "no route to host", "dns resolution", "name or service not known",
    "server disconnected", "peer closed connection", "unexpected eof",
]
_TO_PATTERNS = [
    "timed out", "timeout", "connect timeout", "read timeout",
    "deadline exceeded", "operation timed out",
]
_FNF_PATTERNS = [
    "no such file", "file not found", "cannot find", "enoent",
    "no matches found",
]
_PERM_PATTERNS = ["permission denied", "operation not permitted", "eacces", "eperm"]
_CTX_PATTERNS = [
    "context length", "context size", "maximum context", "token limit",
    "too many tokens", "context window", "prompt is too long",
]
_VAL_PATTERNS = [
    "invalid", "validation", "schema", "required field", "bad request",
    "malformed", "parse error", "syntax error",
]

# COS hook TYPE → RecordCategory (fast path, no pattern matching needed)
_TYPE_MAP: Dict[str, RecordCategory] = {
    "TEST_FAILURE":  RecordCategory.test_failure,
    "LINT_ERROR":    RecordCategory.lint_error,
    "BUILD_ERROR":   RecordCategory.build_error,
    "NETWORK_ERROR": RecordCategory.network,
    "TIMEOUT":       RecordCategory.timeout,
    "AUTH_ERROR":    RecordCategory.auth,
    "RATE_LIMIT":    RecordCategory.rate_limit,
}

# Category → (severity, transient, suggested_action)
_CAT_META: Dict[RecordCategory, tuple] = {
    RecordCategory.rate_limit: (
        RecordSeverity.high, Transience.yes,
        "Back off and retry; consider lowering COS_RATE_THROTTLE_PCT",
    ),
    RecordCategory.auth: (
        RecordSeverity.critical, Transience.no,
        "Rotate or refresh credentials; check env vars",
    ),
    RecordCategory.validation: (
        RecordSeverity.medium, Transience.no,
        "Fix input schema or command arguments",
    ),
    RecordCategory.network: (
        RecordSeverity.high, Transience.yes,
        "Check network connectivity; retry with backoff",
    ),
    RecordCategory.file_not_found: (
        RecordSeverity.medium, Transience.no,
        "Verify file path; check working directory",
    ),
    RecordCategory.permission: (
        RecordSeverity.high, Transience.no,
        "Check file/directory permissions",
    ),
    RecordCategory.timeout: (
        RecordSeverity.medium, Transience.yes,
        "Retry; consider increasing timeout or reducing workload",
    ),
    RecordCategory.integration: (
        RecordSeverity.high, Transience.unknown,
        "Check integration endpoint and credentials",
    ),
    RecordCategory.test_failure: (
        RecordSeverity.high, Transience.no,
        "Review failing tests and fix underlying code",
    ),
    RecordCategory.lint_error: (
        RecordSeverity.medium, Transience.no,
        "Run linter locally and resolve reported issues",
    ),
    RecordCategory.build_error: (
        RecordSeverity.critical, Transience.no,
        "Fix compilation/build errors before proceeding",
    ),
    RecordCategory.context_overflow: (
        RecordSeverity.high, Transience.yes,
        "Compress context or split into smaller requests",
    ),
    RecordCategory.unknown: (
        RecordSeverity.low, Transience.unknown,
        "Investigate manually; add pattern to error_classifier.py if recurring",
    ),
}


def _match(text: str, patterns: List[str]) -> bool:
    return any(p in text for p in patterns)


def _classify_record_by_message(msg: str) -> RecordCategory:
    m = msg.lower()
    if _match(m, _RL_PATTERNS):
        return RecordCategory.rate_limit
    if _match(m, _AUTH_MSG_PATTERNS):
        return RecordCategory.auth
    if _match(m, _TO_PATTERNS):
        return RecordCategory.timeout
    if _match(m, _NET_PATTERNS):
        return RecordCategory.network
    if _match(m, _CTX_PATTERNS):
        return RecordCategory.context_overflow
    if _match(m, _FNF_PATTERNS):
        return RecordCategory.file_not_found
    if _match(m, _PERM_PATTERNS):
        return RecordCategory.permission
    if _match(m, _VAL_PATTERNS):
        return RecordCategory.validation
    return RecordCategory.unknown


def _make_error_class(cat: RecordCategory, raw: Dict[str, Any]) -> ErrorClass:
    severity, transient, action = _CAT_META[cat]
    return ErrorClass(category=cat, severity=severity, transient=transient,
                      suggested_action=action, raw=raw)


def _deep_classify_record(record: Dict[str, Any]) -> Optional[RecordCategory]:
    """Optional LLM deep classify (COS_ERROR_DEEP_CLASSIFY=1). Returns None if unavailable."""
    if not os.environ.get("COS_ERROR_DEEP_CLASSIFY"):
        return None
    try:
        from lib.dispatch import dispatch_prompt  # type: ignore
    except ImportError:
        return None
    prompt = (
        "Classify the following COS error record into one of these categories:\n"
        + ", ".join(c.value for c in RecordCategory)
        + "\n\nError record (JSON):\n"
        + json.dumps(record, default=str)
        + "\n\nRespond with ONLY the category name, nothing else."
    )
    try:
        result = dispatch_prompt(prompt, priority="low", max_tokens=20)
        return RecordCategory(result.strip().lower())
    except Exception:  # noqa: BLE001
        return None


def classify(error_record: Dict[str, Any]) -> ErrorClass:
    """Classify a single error-learning.jsonl record into a structured ErrorClass.

    Pipeline (priority order):
      1. Direct TYPE field mapping (covers all COS hook-generated records)
      2. Pattern matching on command + message fields
      3. Optional LLM deep classify (COS_ERROR_DEEP_CLASSIFY=1, only if still unknown)
      4. Fallback: unknown

    Does not mutate the input record.
    """
    if not error_record:
        return _make_error_class(RecordCategory.unknown, error_record)

    # 1. Fast-path via TYPE
    cat = _TYPE_MAP.get((error_record.get("type") or "").upper())

    if cat is None:
        # 2. Pattern matching on text fields
        parts = []
        for f in ("command", "message", "output", "stderr", "error", "type"):
            v = error_record.get(f)
            if isinstance(v, str) and v.strip():
                parts.append(v)
        combined = " ".join(parts)
        cat = _classify_record_by_message(combined) if combined.strip() else RecordCategory.unknown

    # 3. LLM deep classify only when still unknown
    if cat is RecordCategory.unknown:
        deep = _deep_classify_record(error_record)
        if deep is not None:
            cat = deep

    return _make_error_class(cat, error_record)


def classify_jsonl(path: Path) -> List[ClassifiedError]:
    """Bulk-classify all records from an error-learning.jsonl file.

    Silently skips malformed/empty lines.
    """
    results: List[ClassifiedError] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                results.append(ClassifiedError(record=record, classification=classify(record)))
    except OSError as exc:
        logger.warning("error_classifier: cannot read %s: %s", path, exc)
    return results


def default_errors_path() -> Path:
    """Return the canonical error-learning.jsonl path for the current project."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir) / _DEFAULT_ERRORS_PATH
