# ADR-101 — Intent-Aware Rate Limiter Flow Control

<!-- SCOPE: OS -->

**Status**: Accepted
**Date**: 2026-05-01
**Author**: Matias Nahuel Améndola
**Related**: ADR-086 (hook execution observability), ADR-096 (review-agent pattern), ADR-098 (multi-agent file coordination), ADR-100 (resource-governed test execution)

## Status

Accepted and implemented on 2026-05-01.

## Context

The action-count rate limiter existed because a real orchestrator cascade produced hundreds of repeated tool calls in one session. The original fixed-window limiter was useful as a circuit breaker, but it treated two materially different patterns as equivalent:

1. legitimate short bursts from operator-driven work or parallel agents, and
2. accidental loops that repeat the same action signature until the hook chain or queue saturates.

The prior design was phase-aware and tool-aware, and it already queued blocked work instead of dropping it. The missing layer was behavioral flow control: the limiter needed to preserve throughput for normal bursts while detecting sustained pressure and loop-like repetition earlier.

## Decision

Replace fixed-window blocking semantics with token-bucket flow control and add three intent signals around it.

### 1. Token bucket per action type

Each action type keeps a persisted token bucket:

| Action type | Refill rate source | Window |
|---|---:|---:|
| `tool_call` | `max_tool_calls_per_minute` | 60s |
| `bash_command` | `max_bash_commands_per_minute` | 60s |
| `file_write` | `max_file_writes_per_minute` | 60s |
| `agent_launch` | `max_agent_launches_per_hour` | 3600s |

The project phase multiplier still applies to the refill rate. Bucket capacity is `ceil(effective_limit * burst_multiplier)`, default `1.5x`.

This preserves protection against sustained overload while allowing reasonable bursts such as several related git commands or a short fan-out of legitimate actions.

### 2. Operator priority reserve

Normal/orchestrator work may not consume the bottom `operator_reserve_ratio` of the bucket, default `20%`. The `operator` priority lane can use those reserved tokens.

This prevents background retries or orchestrator cascades from trapping the human operator behind the same queue.

The hook derives lane as follows:

- `COS_RATE_LIMIT_PRIORITY_LANE` wins when explicitly set.
- queued retries (`RATE_LIMIT_RETRY_COUNT > 0`) use `orchestrator`.
- fresh hook invocations default to `operator`.

### 3. Soft warnings before block

When a bucket or cost cap crosses `warning_threshold`, default `80%`, the limiter emits `RATE_LIMIT_WARNING` without blocking.

Warnings are advisory and intended to let the operator slow or batch work before a hard block.

### 4. Diversity penalty for repeated signatures

The limiter tracks recent action signatures inside the same action window. For Bash, the signature is the command hash already captured by `hooks/rate-limiter.sh`.

If at least `diversity_penalty_min_events` events exist and one signature accounts for at least `diversity_penalty_threshold` of the window, the next matching action costs `diversity_penalty_cost` tokens, default `2.0`.

This does not ban repeated commands. It makes loop-like repetition drain burst capacity faster than diverse productive work.

## Consequences

### Positive

- Short legitimate bursts pass without waiting for a fixed-window reset.
- Sustained pressure still depletes buckets and queues blocked actions.
- Operator work keeps a reserve even when background retries are active.
- Repeated-command loops are throttled earlier than diverse command sequences.
- The 80% warning gives an observable intervention point before a hard block.

### Negative

- Status output is more complex: operators now see refill limit, burst capacity, bucket tokens, normal-lane reserve, and warning state.
- Some tests that asserted fixed-window boundaries had to be rewritten around bucket semantics.
- Priority-lane inference is best-effort because harness hook payloads do not carry a universal “user initiated” bit.

### Neutral

- The old timestamp lists remain in state for status/history compatibility.
- Existing queue retry semantics remain intact.
- Cost cap remains hourly and phase-adjusted; it is not token-bucketed.

## Alternatives rejected

| Alternative | Why rejected |
|---|---|
| Keep fixed windows and only raise limits | Delays both productive work and loops; no behavioral distinction. |
| Add only diversity detection | Helps loops but still punishes normal bursts at arbitrary window boundaries. |
| Disable limiter during reconstruction | Reintroduces the original cascade risk exactly when high-throughput refactors happen. |
| Separate queues only | Queue priority helps after block; bucket reserve prevents the operator from being starved before and during block. |

## Implementation

| Layer | File |
|---|---|
| Runtime library | `lib/rate_limiter.py` |
| Hook integration | `hooks/rate-limiter.sh`, `hooks/rate-limit-drain.sh` |
| Operator docs | `rules/rate-limiting.md` |
| Architecture explainer | `docs/architecture/rate-limiter-flow-control.md` |
| Tests | `tests/unit/test_rate_limiter.py`, `tests/unit/test_rate_limiter_behavior.py`, `tests/unit/test_rate_limit_queue.py`, `tests/unit/test_rate_limiter_edge_matrix.py` |

## Verification

```bash
python3 -m pytest tests/unit/test_rate_limiter.py tests/unit/test_rate_limiter_behavior.py tests/unit/test_rate_limit_queue.py tests/unit/test_rate_limiter_edge_matrix.py tests/audit/test_hook_disable_env.py tests/integration/test_rate_limit_drainer_executes.py tests/integration/test_rate_limiter_hook_retry_flow.py -q
bash -n hooks/rate-limiter.sh
python3 -m py_compile lib/rate_limiter.py
```

## Acceptance criteria

1. `RateLimiter.check()` uses token bucket state instead of fixed-window length for action blocking.
2. The hook passes command signatures and lane context into the limiter.
3. `RateLimiter.warnings()` surfaces soft warning messages at `warning_threshold`.
4. Operator lane can use reserved tokens after normal lane is blocked.
5. Repeated identical signatures drain faster than diverse signatures.
6. Existing queue retry tests continue to pass.
7. Edge matrix covers controlled refill, malformed bucket/signature state, invalid and partial config parser boundaries, concurrent persisted writes, hook warnings, hook lane override, hook disable bypass, legacy state compatibility, and block→queue→drain→retry execution.
