# SCOPE: both
"""ADR-228 failure classifier and retry policy table."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class FailureClass(StrEnum):
    CONNECTION_LAYER = "connection_layer"
    RATE_LIMIT = "rate_limit"
    PROVIDER_5XX = "provider_5xx"
    VALIDATION_ERROR = "validation_error"
    AUTH_ERROR = "auth_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RetryPolicy:
    failure_class: FailureClass
    max_attempts: int
    backoff: str
    diversity_required: bool = False
    escalation_after_n: int | None = None


POLICIES: dict[FailureClass, RetryPolicy] = {
    FailureClass.CONNECTION_LAYER: RetryPolicy(FailureClass.CONNECTION_LAYER, 4, "exponential_with_jitter", escalation_after_n=4),
    FailureClass.RATE_LIMIT: RetryPolicy(FailureClass.RATE_LIMIT, 6, "respect_retry_after_header_else_exponential", escalation_after_n=6),
    FailureClass.PROVIDER_5XX: RetryPolicy(FailureClass.PROVIDER_5XX, 3, "exponential_with_jitter", escalation_after_n=3),
    FailureClass.VALIDATION_ERROR: RetryPolicy(FailureClass.VALIDATION_ERROR, 2, "immediate", diversity_required=True, escalation_after_n=2),
    FailureClass.AUTH_ERROR: RetryPolicy(FailureClass.AUTH_ERROR, 0, "none", escalation_after_n=0),
    FailureClass.QUOTA_EXCEEDED: RetryPolicy(FailureClass.QUOTA_EXCEEDED, 0, "none", escalation_after_n=0),
    FailureClass.UNKNOWN: RetryPolicy(FailureClass.UNKNOWN, 1, "exponential_with_jitter", diversity_required=True, escalation_after_n=1),
}


def _status_code(obj: Any) -> int | None:
    for attr in ("status_code", "status"):
        value = getattr(obj, attr, None)
        if isinstance(value, int):
            return value
    if isinstance(obj, dict):
        value = obj.get("status_code") or obj.get("status")
        if isinstance(value, int):
            return value
    return None


def classify_failure(error_or_response: Any) -> FailureClass:
    status = _status_code(error_or_response)
    text = f"{type(error_or_response).__module__}.{type(error_or_response).__name__} {error_or_response}".lower()
    if status in {401, 403} or "unauthorized" in text or "forbidden" in text:
        return FailureClass.AUTH_ERROR
    if status == 429 and ("quota" in text or "credit" in text or "exhaust" in text):
        return FailureClass.QUOTA_EXCEEDED
    if status == 429 or "rate limit" in text or "ratelimit" in text:
        return FailureClass.RATE_LIMIT
    if status is not None and 500 <= status <= 599:
        return FailureClass.PROVIDER_5XX
    if any(token.lower() in text for token in ("ECONNRESET", "EPIPE", "ETIMEDOUT", "ConnectionError", "TimeoutError")):
        return FailureClass.CONNECTION_LAYER
    if "validationerror" in text or "jsondecodeerror" in text or "schema" in text:
        return FailureClass.VALIDATION_ERROR
    return FailureClass.UNKNOWN


def retry_policy_for(failure: FailureClass) -> RetryPolicy:
    return POLICIES[failure]
