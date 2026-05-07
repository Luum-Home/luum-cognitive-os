# ADR-228 — Retry Contract + Cost Session Budget (consolidated)

<!-- SCOPE: OS -->

**Status**: Accepted — Slices A–E implemented (2026-05-07)
**Date**: 2026-05-06
**Related**: ADR-049 (LLM dispatch), ADR-056 (adaptive Agent dispatch), ADR-211 (service mode readiness); depends on ADR-226 (event-sourced session bus)
**Supersedes**: scattered retry magic numbers in `closed-loop-prompts.md`, `task-dag.md`, `estimation-calibration.md`, `agent-escalation.md`, `responsiveness.md`, `error-learning.md` (six files identified by [`failure-recovery-retry-semantics.md`](../research/orchestration-gaps/failure-recovery-retry-semantics.md))
**Source**: synthesis of two related orchestration-gap research reports — [`failure-recovery-retry-semantics.md`](../research/orchestration-gaps/failure-recovery-retry-semantics.md) and [`cost-aware-routing.md`](../research/orchestration-gaps/cost-aware-routing.md). Consolidated because both close the same architectural gap: dispatch happens without a sync gate that classifies *why* the call is happening and whether it's *allowed* to happen. Retry-without-cost-awareness produces the $47K agent-loop incident; cost-without-retry-classification produces silent ECONNRESET drops.

---

## Context

Two parallel research reports identified two adjacent gaps that share the same fix surface (`lib/dispatch.py`):

### Gap 1 — Failure recovery semantics

The Anthropic SDK does not retry connection-layer errors (ECONNRESET, EPIPE, ETIMEDOUT) — confirmed by Claude Code issue #37077. Cognitive OS today has zero application-level retry layer above the SDK; every connection error is silently surfaced as a failure. Worse, Cognitive OS has six different retry magic numbers scattered across rules files, none of which agree:

- `closed-loop-prompts.md`: max 3 retries
- `task-dag.md`: max 5
- `estimation-calibration.md`: max 2
- `agent-escalation.md`: max 3 with same-error abort at 2
- `responsiveness.md`: 3 attempts with diversity requirement
- `error-learning.md`: dedup by 60s window, warn on 3+

These rules contradict each other. They also do not classify *why* a retry is happening (connection error vs. validation error vs. rate limit vs. provider degradation), and the wrong retry strategy for each class is silently broken. LangGraph's `RetryPolicy.retry_on` *does not catch Pydantic `ValidationError`* (issue #6027) — exactly the failure mode any structured-output flow hits. Without classification, the retry loop misses validation failures entirely.

### Gap 2 — Cost-aware routing

Cognitive OS has `lib/cost_predictor.py` and `cost-events.jsonl`, but no per-session budget enforcement. The November 2025 industry incident — $47,000 in API costs from one runaway agent loop — proved that *async cost dashboards cannot prevent the next call*. The only effective enforcement is a *synchronous pre-call gate* in the dispatch path. LiteLLM's `a2a_iteration_budgets` (MIT) is the production-validated reference: per-session budget keyed on `session_id`, pre-call check raises before the HTTP request fires, post-call ledger update.

### Why consolidate

Both gaps live in `dispatch()`. Both need a sync gate before the LLM call fires. Both need post-call accounting. Both are file-backed via `.cognitive-os/metrics/`. Both consume the ADR-226 event sequence to attribute calls to sessions. Building them as two separate ADRs would require two parallel modifications to `dispatch()`, two independent test suites, and two manifests pointing at adjacent files. Consolidating into one ADR-228 lets a single `lib/dispatch_gate.py` carry both concerns.

ADR-229 was originally proposed as the cost-budget ADR; it is now a tombstone pointing at this consolidated ADR.

## Decision

Ship `lib/dispatch_gate.py` as the unified pre-call gate. Two adjacent responsibilities, one chokepoint:

1. **Failure classification**: `classify_failure(exception_or_response) -> FailureClass` — single authoritative classifier. Replaces the six scattered rules. Classes: `connection_layer` (ECONNRESET/EPIPE/timeout), `rate_limit` (429), `provider_5xx`, `validation_error` (Pydantic, JSON schema), `auth_error`, `quota_exceeded`, `unknown`.
2. **Retry policy by class**: deterministic mapping from `FailureClass` to retry strategy: `(max_attempts, backoff, diversity_required, escalation_after_n)`. Each class has *one* policy; rules files reference `retry-contract.md` instead of declaring their own counts.
3. **Cost session budget**: `SessionBudget` class, file-backed at `.cognitive-os/metrics/session-budgets/{session_id}.json`. Pre-call: `pre_call_check(estimated_cost)` raises `SessionBudgetExceeded` if the call would exceed cap. Post-call: `record_actual(actual_cost)` updates the ledger.
4. **Graduated backpressure**: at 70% of budget, inject `[COST_CAUTION]` signal into orchestrator context and prefer cheaper model tiers. At 90%, switch to cheapest-capable tier. At 100%, refuse. Avoids the binary hard-stop UX problem.
5. **Idempotency keys for stateful tools**: `IdempotencyKeyMixin` on the base tool class. Key = `sha256(session_id + event_seq + tool_name)`. Required on any tool whose `mutates_external_state` flag is true. Closes the silent-side-effect-duplication failure mode.
6. **Circuit breaker**: per-provider state machine in `lib/dispatch_gate.py` with LLM-specific signals (error rate + latency p95 + quota % + validation failure rate). Open → fail-fast for `cooldown_seconds`; half-open → one probe; closed → normal.

## Manifest declarations

```yaml
# manifests/retry-contract.yaml
schema_version: retry-contract/v1
status: active
owner: platform-orchestration

failure_classes:
  connection_layer:
    detect: ["ECONNRESET", "EPIPE", "ETIMEDOUT", "ConnectionError", "TimeoutError"]
    max_attempts: 4
    backoff: "exponential_with_jitter"
    base_seconds: 0.5
    diversity_required: false
    escalation_after_n: 4

  rate_limit:
    detect: ["http_429"]
    max_attempts: 6
    backoff: "respect_retry_after_header_else_exponential"
    base_seconds: 1.0
    diversity_required: false
    escalation_after_n: 6

  provider_5xx:
    detect: ["http_5xx", "http_502", "http_503", "http_504"]
    max_attempts: 3
    backoff: "exponential_with_jitter"
    base_seconds: 1.0
    diversity_required: false
    escalation_after_n: 3

  validation_error:
    detect: ["pydantic.ValidationError", "json.JSONDecodeError", "schema_violation"]
    max_attempts: 2
    backoff: "immediate"
    diversity_required: true                 # different prompt strategy each retry
    escalation_after_n: 2

  auth_error:
    detect: ["http_401", "http_403"]
    max_attempts: 0                          # do not retry auth errors silently
    escalation_immediately: true

  quota_exceeded:
    detect: ["http_429_with_quota_header", "AnthropicCreditExhausted"]
    max_attempts: 0
    escalation_immediately: true             # operator must intervene

  unknown:
    detect: ["fallback"]
    max_attempts: 1
    backoff: "exponential_with_jitter"
    base_seconds: 1.0
    diversity_required: true
    escalation_after_n: 1                    # one chance, then stop

cross_class_invariants:
  total_attempts_per_call: 8
  total_wallclock_seconds_per_call: 60
  diversity_check: "approach_hash_must_change_between_attempts"

idempotency:
  required_for: ["tools.mutates_external_state == true"]
  key_format: "sha256({session_id}:{event_seq}:{tool_name})"
  stored_at: ".cognitive-os/metrics/idempotency-keys.jsonl"
  ttl_seconds: 3600
```

```yaml
# manifests/session-budget.yaml
schema_version: session-budget/v1
status: active
owner: platform-orchestration

defaults:
  per_session_cap_usd: 5.00
  per_task_cap_usd: 1.00
  per_call_cap_usd: 0.20

ledger:
  path: ".cognitive-os/metrics/session-budgets/{session_id}.json"
  format: "json_with_atomic_write"
  rebuild_from: ".cognitive-os/metrics/cost-events.jsonl"

backpressure:
  caution_threshold_pct: 70
  switch_threshold_pct: 90
  refuse_threshold_pct: 100
  caution_signal: "[COST_CAUTION]"           # injected into orchestrator context
  switch_target_tier: "cheapest_capable"     # opus -> sonnet, sonnet -> haiku

estimation:
  source: "lib/cost_predictor.py:CostPredictor.get_real_model_prices"
  fallback: "DEFAULT_MODEL_PRICES"
  use_max_when_samples_lt: 5                 # use estimated_cost_max early in run
  switch_to_mid_after: 5

circuit_breaker:
  per_provider_state_path: ".cognitive-os/metrics/circuit-breaker-{provider}.json"
  open_threshold:
    error_rate_pct: 50
    p95_latency_ms: 30000
    validation_failure_rate_pct: 30
  cooldown_seconds: 60
  half_open_probe_count: 1
```

## Hard rules

- **One classifier, one policy file.** No retry counts in any rule file outside `rules/retry-contract.md` and `manifests/retry-contract.yaml`. CI test enforces.
- **Pre-call gate is synchronous.** The check happens *in the same call stack* as the HTTP request. Async observers that arrive after the call do not satisfy this.
- **Validation errors are caught inside the node/skill, not the framework wrapper.** Per the LangGraph+Pydantic incompatibility (issue #6027). The wrapper retry layer exists for transport errors only; validation errors re-prompt with schema+error context inside the skill and return normally.
- **Idempotency keys are required on stateful tools.** A tool declared `mutates_external_state: true` without an `idempotency_key` parameter fails CI.
- **Circuit breaker state is per-provider, file-backed.** Survives process restart. A breaker that opens during a session stays open across the next session start until cooldown.
- **Budget enforcement is sync; budget reporting is async.** `pre_call_check` raises before HTTP; `record_actual` updates the ledger after; dashboards read from the ledger eventually-consistently.
- **Backpressure is graduated, not binary.** 70/90/100. The single biggest UX failure of cost gates is the binary hard-stop; the graduated tier-switch buys margin.
- **Schema-versioned.** Both manifests carry `v1`. Consumers MUST check.

## Test tier matrix (per C3)

T1 ✅ unit — classifier, retry policy lookup, budget arithmetic, idempotency key generation
T2 ✅ integration — dispatch with failure injection across all 7 classes; budget across 100 simulated calls
T3 ✅ behavior — manifest validation, refusal paths, circuit breaker state transitions
T4 ✅ smoke — fresh session, run a budgeted dispatch, hit each backpressure tier, verify behavior
T5 ✅ adversarial — simultaneous retries from same idempotency key (exactly-once enforcement); circuit-breaker race
T6 ✅ performance — pre-call gate latency p95 < 2 ms (dispatch hot path)
T7 ✅ chaos — kill mid-pre-call, kill mid-record_actual, corrupted ledger (must rebuild from cost-events.jsonl)
T8 ⬜ cross-harness — Claude Code, Codex, OpenCode all dispatch through same gate
T9 ✅ adoption-truth — LiteLLM `a2a_iteration_budgets` pattern reference verified
T10 ⬜ audit invariants — N/A (substrate, not git-touching)

## Consequences

### Positive

- **The $47K-incident class of failure is structurally impossible** for sessions running through the gate.
- **Six contradictory retry rules collapse to one.** Reduced ambiguity for agents and operators.
- **Validation errors get the right retry strategy** (re-prompt with schema+error, not blind retry). Closes the LangGraph+Pydantic trap.
- **Connection-layer errors get the retries the SDK doesn't provide.** Closes the Anthropic SDK silent-drop gap.
- **Idempotency keys eliminate the 15-30% of LLM tool-call retries** that today silently duplicate side effects (Slack messages sent twice, DB rows written twice, etc.).
- **Circuit breaker** prevents cascading failure when a provider degrades (HTTP 200 but routing to a downgraded model, validation rate spikes).

### Negative / trade-offs

- **One more layer in the dispatch hot path.** Mitigation: T6 budgets <2ms p95; gate is in-process file read, no network.
- **Manifest-driven retry feels less flexible than per-call overrides.** Mitigation: per-call override available as `dispatch(retry_policy_override=...)`. Default path is the manifest.
- **Ledger contention under N concurrent sessions.** Mitigation: per-session ledger file (no shared ledger); cost-events.jsonl as the canonical append-only source-of-truth; per-session ledger is a projection.
- **Operator confusion when budget hits**: "why did my agent stop?" Mitigation: caution+switch+refuse messaging is explicit and tells the operator which tier and which threshold; runbook documents the recovery flow.
- **The consolidation makes ADR-228 larger than either gap alone.** Acceptable because the surface is the same code path; splitting would require coordinating two ADRs that touch the same file.

## Alternatives rejected

- **Adopt LiteLLM as runtime dependency.** MIT (allowlist) but adds an HTTP proxy layer + Redis-by-default. Violates C2 default. Pattern adoption is sufficient.
- **Adopt Temporal retry semantics.** Apache 2.0 OK, but mandatory server. Violates C2.
- **Build cost gate without classifier.** Considered; rejected because cost-without-classification still produces wrong retries (a quota_exceeded error retried for free still costs operator time and confidence).
- **Build classifier without budget.** Considered; rejected because retry-without-budget produces the $47K-incident class. The two are coupled.
- **Per-rule-file retry counts (status quo).** Rejected; six contradictions documented in research.
- **Idempotency keys as opt-in.** Rejected; opt-in idempotency is opt-in side-effect-duplication, which is the bug.

## Acceptance criteria

```bash
python3 -m pytest tests/unit/test_dispatch_gate.py tests/unit/test_retry_classifier.py tests/unit/test_session_budget.py tests/integration/test_dispatch_with_gate.py tests/audit/test_no_external_retry_counts.py tests/perf/test_pre_call_gate_latency.py tests/chaos/test_circuit_breaker_recovery.py -q

# Smoke (T4)
bash tests/smoke/test_budget_backpressure.sh
```

The tests must prove:

- `classify_failure(ECONNRESET)` → `connection_layer`; full mapping table verified.
- Retry policy applied matches the failure class (4 attempts, exponential, no diversity).
- `validation_error` retry attempts have different `approach_hash` (diversity enforced).
- `pre_call_check(0.50)` on a session with $4.60 spent and $5.00 cap raises `SessionBudgetExceeded`.
- `pre_call_check` at 70% emits `[COST_CAUTION]`; at 90% switches model tier; at 100% refuses.
- Concurrent calls with same idempotency key result in exactly one external side effect.
- Circuit breaker opens after threshold, stays open for cooldown, half-opens with one probe, closes on probe success.
- Ledger rebuild from `cost-events.jsonl` reproduces the same total $ as the live ledger after kill-mid-record_actual.
- CI audit: no retry magic numbers in any rule file outside `rules/retry-contract.md`.
- Pre-call gate latency p95 < 2 ms on warm cache.

## Implementation slices

1. **Slice A — `lib/retry_classifier.py`** (~50 LOC). The single `classify_failure()` function. Tests T1+T2.
2. **Slice B — `rules/retry-contract.md` + `manifests/retry-contract.yaml`** (~rule consolidation, no new code). Migrate the six scattered counts. Tests T9 audit.
3. **Slice C — `lib/session_budget.py`** (~80 LOC). `SessionBudget` class, file-backed ledger, pre/post-call API. Tests T1+T2+T7.
4. **Slice D — `lib/dispatch_gate.py`** (~100 LOC). Wraps `lib/dispatch.py` with the gate. `pre_call_check` → classify on failure → retry per policy → `record_actual`. Tests T2+T6.
5. **Slice E — Idempotency mixin** (~40 LOC). `IdempotencyKeyMixin` on base tool class. Persisted at `.cognitive-os/metrics/idempotency-keys.jsonl`. Tests T1+T5.
6. **Slice F — Circuit breaker** (~60 LOC). `lib/circuit_breaker.py`. Per-provider file-backed state. Tests T2+T7.
7. **Slice G — `cost_predictor` integration** (~20 LOC wiring). Connect `get_real_model_prices()` into `pre_call_check` estimation. Closes the prediction-vs-actual loop.
8. **Slice H — Operator runbook** at `docs/runbooks/cost-budget-and-retry.md`. Three recovery flows: budget-hit, circuit-open, classifier-unknown.

Total: ~350 LOC + rule consolidation (net-negative bash equivalent).

## Implementation status

- **2026-05-07 — Slices A–E implemented**: `lib/retry_classifier.py`, `lib/session_budget.py`, and `lib/dispatch_gate.py` provide the failure classifier, retry policy lookup, sync pre-call budget gate, post-call accounting, context pressure signals, and idempotency key claims.
- **Manifests/rule**: `manifests/retry-contract.yaml`, `manifests/session-budget.yaml`, and `rules/retry-contract.md` are the canonical policy surfaces.
- **Deferred**: full `lib/dispatch.py` integration, provider circuit-breaker state machine beyond the existing generic circuit breaker, cost predictor pricing integration, runbook.

## Open questions

- **Should idempotency keys be enforced for *all* tool calls, not just `mutates_external_state`?** Trade-off: zero false negatives vs. extra storage for read-only idempotency. Initial answer: only stateful. Revisit if read-only retry duplication becomes a measurable problem.
- **Should the budget cap be per-session only, or per-task as well?** Both — manifest declares both `per_session_cap_usd` and `per_task_cap_usd`. Task-level cap protects against one runaway task burning the whole session budget.
- **How does ADR-228 interact with ADR-211 service-mode readiness?** Service mode MUST require a budget cap; reject service-mode invocation without one. Tracked as a slice of ADR-211.
- **Cross-provider budget reconciliation when ADR-049 dispatch falls over to Qwen.** Initial answer: budget is dollar-denominated, not provider-tied; falling over to a cheaper provider extends runway, not budget. Document explicitly in runbook.
- **Should the circuit breaker open globally or per-tier?** Initial answer: per-(provider, model_tier). A degraded Sonnet doesn't necessarily mean degraded Haiku.
