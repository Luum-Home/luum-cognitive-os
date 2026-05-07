# Retry Contract

<!-- SCOPE: both -->

Canonical ADR-228 retry policy. Do not define independent retry counts in other rule files.

- connection_layer: 4 attempts, exponential with jitter
- rate_limit: 6 attempts, respect Retry-After else exponential
- provider_5xx: 3 attempts, exponential with jitter
- validation_error: 2 attempts, immediate, diversity required
- auth_error: 0 attempts, escalate
- quota_exceeded: 0 attempts, escalate
- unknown: 1 attempt, diversity required

Contextual Trigger: retry, failure, ECONNRESET, EPIPE, ETIMEDOUT, validation error, rate limit
