from __future__ import annotations

import json

from lib.retry_classifier import FailureClass, classify_failure, retry_policy_for


class Response:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text

    def __str__(self) -> str:
        return self.text


def test_classify_failure_mapping() -> None:
    assert classify_failure(ConnectionError("ECONNRESET")) == FailureClass.CONNECTION_LAYER
    assert classify_failure(TimeoutError("ETIMEDOUT")) == FailureClass.CONNECTION_LAYER
    assert classify_failure(Response(429, "rate limit")) == FailureClass.RATE_LIMIT
    assert classify_failure(Response(429, "quota exhausted")) == FailureClass.QUOTA_EXCEEDED
    assert classify_failure(Response(503)) == FailureClass.PROVIDER_5XX
    assert classify_failure(Response(401)) == FailureClass.AUTH_ERROR
    assert classify_failure(json.JSONDecodeError("bad", "{", 0)) == FailureClass.VALIDATION_ERROR


def test_retry_policy_table() -> None:
    assert retry_policy_for(FailureClass.CONNECTION_LAYER).max_attempts == 4
    assert retry_policy_for(FailureClass.VALIDATION_ERROR).diversity_required is True
    assert retry_policy_for(FailureClass.AUTH_ERROR).max_attempts == 0
