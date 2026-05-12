# Cognitive OS Agent-Computer Interface

> Status: MVP implemented for normalized observations.

The Cognitive OS ACI defines how tool results should be represented before they are reused by agents, reports, benchmarks, or safety gates.

## Principles

1. Observations are bounded by default.
2. Empty success is explicit.
3. Errors include exit code, retryability, suspected cause, and next action.
4. Risk tags travel with observations.
5. Full logs become artifacts when truncated.

## Runtime surface

- Library: `lib/aci_observation.py`
- Tests: `tests/unit/test_aci_observation.py`
