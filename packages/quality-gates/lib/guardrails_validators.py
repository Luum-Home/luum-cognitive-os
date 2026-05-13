# SCOPE: both
# scope: both
"""Guardrails AI validators for the Cognitive OS safety mesh.

Wraps guardrails-ai validators for PII detection, jailbreak detection,
and toxic content detection. Provides graceful degradation when the
guardrails-ai package is not installed.

Usage:
    from lib.guardrails_validators import check_pii, check_jailbreak, check_toxic

    findings = check_pii("My SSN is 123-45-6789")
    for f in findings:
        print(f"{f['severity']}: {f['type']} - {f['message']}")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

# Attempt to import guardrails-ai; fall back to pattern-based detection
_GUARDRAILS_AVAILABLE = False
try:
    import guardrails  # noqa: F401

    _GUARDRAILS_AVAILABLE = True
except ImportError:
    pass


@dataclass
class Finding:
    """A single validation finding from a guardrail check."""

    severity: str  # WARNING, CRITICAL, INFO
    type: str  # PII, JAILBREAK, TOXIC
    category: str  # ssn, credit_card, email, injection, etc.
    message: str
    match: str = ""  # The matched text (redacted for display)
    start: int = 0  # Start position in text
    end: int = 0  # End position in text

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "type": self.type,
            "category": self.category,
            "message": self.message,
            "match": self.match,
            "start": self.start,
            "end": self.end,
        }


# ---------------------------------------------------------------------------
# PII Detection Patterns (fallback when guardrails-ai is not installed)
# ---------------------------------------------------------------------------

_PII_PATTERNS = {
    "ssn": {
        "pattern": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "severity": "CRITICAL",
        "message": "Social Security Number detected",
    },
    "credit_card": {
        "pattern": re.compile(
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|"
            r"3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|"
            r"(?:2131|1800|35\d{3})\d{11})\b"
        ),
        "severity": "CRITICAL",
        "message": "Credit card number detected",
    },
    "credit_card_formatted": {
        "pattern": re.compile(
            r"\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b"
        ),
        "severity": "CRITICAL",
        "message": "Formatted credit card number detected",
    },
    "phone_us": {
        "pattern": re.compile(
            r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        "severity": "WARNING",
        "message": "US phone number detected",
    },
    "email": {
        "pattern": re.compile(
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
        ),
        "severity": "WARNING",
        "message": "Email address detected",
    },
    "api_key_generic": {
        "pattern": re.compile(
            r"\b(?:sk-[a-zA-Z0-9]{20,}|"
            r"ghp_[a-zA-Z0-9]{36}|"
            r"AKIA[0-9A-Z]{16}|"
            r"xox[bpoas]-[a-zA-Z0-9-]+)\b"
        ),
        "severity": "CRITICAL",
        "message": "API key or token detected",
    },
    "ip_address": {
        "pattern": re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        ),
        "severity": "INFO",
        "message": "IP address detected",
    },
}

# ---------------------------------------------------------------------------
# Jailbreak Detection Patterns
# ---------------------------------------------------------------------------

_JAILBREAK_PATTERNS = {
    "ignore_instructions": {
        "pattern": re.compile(
            r"(?i)ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions"
        ),
        "severity": "CRITICAL",
        "message": "Prompt injection: ignore previous instructions",
    },
    "override_rules": {
        "pattern": re.compile(
            r"(?i)(?:override|bypass|disable|turn off)\s+(?:all\s+)?(?:rules|safety|guardrails|restrictions)"
        ),
        "severity": "CRITICAL",
        "message": "Prompt injection: attempt to override safety rules",
    },
    "pretend_mode": {
        "pattern": re.compile(
            r"(?i)(?:pretend|act as if|imagine)\s+you\s+(?:are|have|can|don't have)\s+(?:no\s+)?(?:rules|restrictions|limits)"
        ),
        "severity": "CRITICAL",
        "message": "Prompt injection: pretend/roleplay to bypass rules",
    },
    "developer_mode": {
        "pattern": re.compile(
            r"(?i)(?:enter|enable|activate|switch to)\s+(?:developer|admin|god|sudo|root|debug)\s+mode"
        ),
        "severity": "CRITICAL",
        "message": "Prompt injection: developer/admin mode activation",
    },
    "dan_prompt": {
        "pattern": re.compile(
            r"(?i)(?:you are now|from now on you are|you will act as)\s+(?:DAN|an? (?:unrestricted|uncensored|unfiltered))"
        ),
        "severity": "CRITICAL",
        "message": "Prompt injection: DAN/unrestricted mode",
    },
    "system_message_spoof": {
        "pattern": re.compile(
            r"(?i)(?:\[system\]|\[admin\]|system message:|admin override:)"
        ),
        "severity": "WARNING",
        "message": "Possible system message spoofing",
    },
}

# ---------------------------------------------------------------------------
# Toxic Content Patterns (basic keyword-based)
# ---------------------------------------------------------------------------

_TOXIC_PATTERNS = {
    "threat": {
        "pattern": re.compile(
            r"(?i)\b(?:i will|gonna|going to)\s+(?:kill|harm|hurt|destroy|attack)\b"
        ),
        "severity": "CRITICAL",
        "message": "Threatening language detected",
    },
    "hate_speech_indicator": {
        "pattern": re.compile(
            r"(?i)\b(?:all\s+\w+\s+(?:should|must|deserve to)\s+(?:die|be killed|be eliminated))\b"
        ),
        "severity": "CRITICAL",
        "message": "Hate speech indicator detected",
    },
}


def is_available() -> bool:
    """Check if the guardrails-ai package is available."""
    return _GUARDRAILS_AVAILABLE


def check_pii(text: str) -> List[Finding]:
    """Detect PII in text.

    Uses guardrails-ai validators when available, falls back to
    regex pattern matching.

    Args:
        text: The text to scan for PII.

    Returns:
        List of Finding objects for each PII instance detected.
    """
    if not text:
        return []

    findings: List[Finding] = []

    if _GUARDRAILS_AVAILABLE:
        try:
            # Use guardrails-ai PII detection
            from guardrails.hub import DetectPII  # type: ignore

            guard = guardrails.Guard().use(DetectPII, on_fail="noop")
            result = guard.validate(text)
            if result.validation_passed is False:
                for log in getattr(result, "validation_summaries", []):
                    findings.append(
                        Finding(
                            severity="WARNING",
                            type="PII",
                            category="guardrails_detected",
                            message=str(log),
                        )
                    )
            if findings:
                return findings
        except Exception as e:
            logger.debug("guardrails-ai PII detection failed, falling back to regex: %s", e)

    # Fallback: regex-based PII detection
    for category, config in _PII_PATTERNS.items():
        for match in config["pattern"].finditer(text):
            matched_text = match.group()
            # Redact the middle of the match for display
            if len(matched_text) > 6:
                redacted = matched_text[:3] + "***" + matched_text[-3:]
            else:
                redacted = "***"

            findings.append(
                Finding(
                    severity=config["severity"],
                    type="PII",
                    category=category,
                    message=config["message"],
                    match=redacted,
                    start=match.start(),
                    end=match.end(),
                )
            )

    return findings


def check_jailbreak(text: str) -> List[Finding]:
    """Detect jailbreak attempts in prompts.

    Uses guardrails-ai validators when available, falls back to
    regex pattern matching.

    Args:
        text: The prompt text to scan for jailbreak attempts.

    Returns:
        List of Finding objects for each jailbreak pattern detected.
    """
    if not text:
        return []

    findings: List[Finding] = []

    if _GUARDRAILS_AVAILABLE:
        try:
            from guardrails.hub import DetectJailbreak  # type: ignore

            guard = guardrails.Guard().use(DetectJailbreak, on_fail="noop")
            result = guard.validate(text)
            if result.validation_passed is False:
                for log in getattr(result, "validation_summaries", []):
                    findings.append(
                        Finding(
                            severity="CRITICAL",
                            type="JAILBREAK",
                            category="guardrails_detected",
                            message=str(log),
                        )
                    )
            if findings:
                return findings
        except Exception as e:
            logger.debug("guardrails-ai jailbreak detection failed, falling back to regex: %s", e)

    # Fallback: regex-based jailbreak detection
    for category, config in _JAILBREAK_PATTERNS.items():
        for match in config["pattern"].finditer(text):
            findings.append(
                Finding(
                    severity=config["severity"],
                    type="JAILBREAK",
                    category=category,
                    message=config["message"],
                    match=match.group()[:50],
                    start=match.start(),
                    end=match.end(),
                )
            )

    return findings


def check_toxic(text: str) -> List[Finding]:
    """Detect toxic content in text.

    Uses guardrails-ai validators when available, falls back to
    regex pattern matching.

    Args:
        text: The text to scan for toxic content.

    Returns:
        List of Finding objects for each toxic pattern detected.
    """
    if not text:
        return []

    findings: List[Finding] = []

    if _GUARDRAILS_AVAILABLE:
        try:
            from guardrails.hub import ToxicLanguage  # type: ignore

            guard = guardrails.Guard().use(ToxicLanguage, on_fail="noop")
            result = guard.validate(text)
            if result.validation_passed is False:
                for log in getattr(result, "validation_summaries", []):
                    findings.append(
                        Finding(
                            severity="WARNING",
                            type="TOXIC",
                            category="guardrails_detected",
                            message=str(log),
                        )
                    )
            if findings:
                return findings
        except Exception as e:
            logger.debug("guardrails-ai toxic detection failed, falling back to regex: %s", e)

    # Fallback: regex-based toxic content detection
    for category, config in _TOXIC_PATTERNS.items():
        for match in config["pattern"].finditer(text):
            findings.append(
                Finding(
                    severity=config["severity"],
                    type="TOXIC",
                    category=category,
                    message=config["message"],
                    match=match.group()[:50],
                    start=match.start(),
                    end=match.end(),
                )
            )

    return findings
