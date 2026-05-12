# Failure Recovery and Retry Semantics for AI Agent Orchestration

**Status:** Research — No code changes  
**Date:** 2026-05-06  
**Scope:** COS retry logic unification across hooks  
**Author:** Research agent (Claude Sonnet 4.6)  
**Sources:** 15 web sources, 7 searches, 11 fetches

---

## Executive Summary

COS retry logic is currently spread across at least six rule files (`closed-loop-prompts.md`, `task-dag.md`, `fault-tolerance.md`, `phase-aware-agents.md`, `rate-limiting.md`, `estimation-calibration.md`) with no single authoritative contract governing which failure type triggers which strategy, how backoff parameters are chosen, or when a circuit breaker should supersede a retry loop. This document maps the prior-art landscape across Codex, LangGraph, Anthropic SDK, OpenAI Agents SDK, AutoGen, and CrewAI; synthesizes a failure-mode taxonomy; presents a retry-strategy menu; and closes with a concrete recommendation for a unified retry contract in COS.

---

## 1. Prior Art Survey

### 1.1 LangGraph — RetryPolicy

LangGraph's `RetryPolicy` (introduced in v0.2.24) is a `NamedTuple` attached directly to graph nodes via `graph.add_node("name", fn, retry=policy)`. Its parameters are:

| Parameter | Purpose |
|---|---|
| `initial_interval` | Seed delay before the first retry attempt |
| `backoff_factor` | Multiplier applied to delay between successive attempts |
| `max_interval` | Ceiling on retry delay to prevent runaway waits |
| `max_attempts` | Total execution attempts permitted |
| `jitter` | Randomisation added to computed delay |
| `retry_on` | Exception class list or callable returning `bool`; defaults to retry on everything except `OSError` and non-5xx HTTP errors |

A critical production gap was documented in GitHub issue #6027: `ValidationError` from Pydantic (commonly raised when `with_structured_output` produces malformed LLM output) bypasses `RetryPolicy` entirely and propagates immediately, because Pydantic validation happens before the node body reaches the retry wrapper. This is the canonical example of a framework leaking the retry contract through its own internals.

State-modifying retry policies were added in PR #2957: the `retry_on` parameter can accept a `dict[ExceptionType, state_modifier_fn]`, allowing the workflow state to be updated before each retry. This is architecturally significant — it moves retry from a pure network concern into a reasoning concern, letting the agent receive richer context on each attempt.

After retries are exhausted, `RetryPolicy` raises rather than routing. To redirect flow, practitioners must either (a) handle retries manually inside the node and emit `Command(goto="fallback_node")`, or (b) use conditional edges keyed on a failure flag in state. The `error_handler=` parameter on `add_node` fires after all retries and can route via `Command`, but it is separate from `RetryPolicy` itself.

**Key lesson:** LangGraph separates retry policy (transient-error loop) from error handler (exhaustion routing). COS conflates both in `closed-loop-prompts.md`.

### 1.2 Anthropic SDK — Built-in Retry with Exponential Backoff

The Anthropic Python SDK implements automatic retry at the HTTP layer inside `BaseClient`. Configuration is minimal by design:

- `max_retries`: default `2` (3 total attempts); settable at client init or per-request
- Retried status codes: 408, 409, 429, 500–599
- Non-retried: 400–407, 410–428, 430–499 (client errors)
- The `x-should-retry` response header overrides the default classification

Backoff algorithm:
```
retry_count = min(max_retries - remaining_retries, 1000)
base_delay  = min(0.5 * 2^retry_count, 60)   # seconds
final_delay = base_delay * (1 - 0.25 * random())
```

First retry fires at approximately 0.375–0.5 s; second at 0.75–1 s; capped at 60 s. If a `Retry-After` header is present (milliseconds, seconds, or HTTP date format), the SDK honours it instead.

There are no user-facing retry hooks or callbacks. This is a deliberate design choice: the SDK treats retry as infrastructure, not application logic. The consequence for COS is that Anthropic API retries are invisible to COS's own retry accounting — a request that exhausts the SDK's 3 attempts arrives at COS as a single `RateLimitError` or `InternalServerError` with no metadata about elapsed time or attempt count.

A live production bug (Claude Code issue #37077) documents that connection-level errors (ECONNRESET, EPIPE, ETIMEDOUT) are never retried by the SDK — they surface immediately as `APIConnectionError`. This is a gap COS must fill at the orchestrator layer.

### 1.3 OpenAI Agents SDK — ModelRetrySettings and Tool Error Recovery

The OpenAI Agents SDK structures failures into a typed exception hierarchy: `ModelBehaviorError` (malformed tool arguments), `UserError` (developer misconfiguration), and infrastructure errors. Failed runs expose `RunErrorDetails` containing error category, triggering input, items generated before failure, and model responses — making post-mortem analysis first-class.

Retry configuration is opt-in through `ModelRetrySettings`:

| Policy | Trigger |
|---|---|
| `provider_suggested` | Respects `Retry-After` headers from the model provider |
| `network_error` | Connection timeouts, DNS failures |
| `http_status` | Status codes 429, 503 |

Backoff uses exponential strategies with configurable `base_delay`, `max_delay`, and `jitter`.

Tool failures are handled via `failure_error_function`: when a tool call fails, the function returns an error string that is fed back to the model as tool output. This lets the LLM reason about the failure and decide whether to retry, substitute, or escalate — a semantically richer mechanism than a blind retry loop.

MCP server connections employ protocol-level retries with `max_retry_attempts` and `retry_backoff_seconds_base`, separate from model-level retries. Arguments are validated against cached schemas before dispatch, raising `UserError` locally for invalid inputs rather than incurring a network call. This two-layer architecture (local validation + remote retry) is a pattern COS should adopt for skill dispatch.

### 1.4 Codex (openai/codex) — Agent Loop Depth Controls

The Codex CLI is implemented primarily in Rust and exposes agent loop controls including `max_turns` (equivalent to `agents.max_depth` in Agents SDK terminology) to prevent runaway recursive delegation. The AGENTS.md file format governs instruction discovery (`project_doc_max_bytes: 32 KiB` default) but does not directly encode retry semantics.

The practical implication is that Codex treats depth exhaustion as a hard stop rather than a recoverable failure. There is no built-in compensation path when `max_turns` is reached — the session terminates with a context message. This is distinct from retry (which handles transient failures at a fixed step) and represents a separate failure class: *depth budget exhaustion*.

### 1.5 AutoGen — Configurable Agent-Level Retries

AutoGen exposes `max_retries` and `timeout` inside `llm_config`. When an agent encounters an error, the `UserProxyAgent` prompts for user input and retries; if retries fail, the task is passed to another agent as a handoff. This "agent-level failover" pattern is distinct from node-level retry: rather than repeating the same agent, AutoGen routes to a different agent entirely, with the prior agent's output (including error context) visible in the shared conversation history.

AutoGen's typed state transitions (explicit state schemas) make retry logic cleaner by ensuring the agent knows exactly what state to restore to before reattempting. Production deployments using AutoGen often wrap the outer `GroupChat` loop in an exponential backoff shell to handle rate limits that occur during multi-agent coordination rounds.

### 1.6 CrewAI — max_retry_limit and Guardrail-Driven Retries

CrewAI implements retry at two levels:

1. **Agent-level**: `max_retry_limit` controls how many times an agent attempts a task before handing off or failing. Setting `max_retry_limit=1` implements "fail fast" semantics for precision-critical tasks.

2. **Task guardrail-level**: Guardrails are validation functions that run immediately after an agent produces output. If a guardrail fails, CrewAI retries the task up to two more times with the guardrail failure message included in the retry prompt. This is validation-driven retry — semantically, the agent is told "your output was invalid, here is why, try again."

The guardrail retry pattern is powerful for output schema enforcement, acting as a structured self-correction loop. However, CrewAI does not natively emit idempotency keys for tool calls made during retry rounds, which means stateful tool calls (e.g., sending a Slack message) can execute multiple times if the guardrail fires after the tool was already invoked.

---

## 2. Cross-Cutting Patterns

### 2.1 Circuit Breaker vs. Exponential Backoff

Exponential backoff and circuit breakers are complementary, not alternative, strategies. They operate on different time horizons and address different failure patterns.

**Exponential backoff with jitter** is appropriate for:
- Transient single-request failures (rate limits, brief 5xx, connection resets)
- Per-request retry scope (the caller waits and reattempts the same request)
- Failure rate below threshold: each failure is independent

The standard formula used across all surveyed frameworks:
```
wait_time = min(base_delay * 2^attempt, max_delay) * (1 - jitter_factor * random())
```
AWS research on distributed systems shows that adding jitter reduces retry storms by 60–80% compared to pure exponential backoff.

**Circuit breakers** operate at service-level scope across many requests:

| State | Behaviour | Trigger |
|---|---|---|
| CLOSED | Normal operation; failures increment counter | — |
| OPEN | Fast-fail without calling downstream | Failure rate > threshold (e.g., 50% over 60 s) |
| HALF-OPEN | One probe request; restore on success | Cooldown elapsed (e.g., 30 s, doubling on repeat trips) |

LLM-specific circuit breaker metrics extend beyond binary pass/fail:
- **Token consumption**: open at 80% of quota capacity
- **Latency degradation**: open when >30% of requests exceed "degraded" threshold (15–30 s)
- **Semantic validation failures**: hallucination/schema violations count as errors

The critical difference from microservice circuit breakers: LLM providers can silently degrade (routing to quantized models, reducing context window) while returning HTTP 200. A well-implemented LLM circuit breaker therefore monitors response *quality*, not just status codes.

Fallback hierarchy for open circuits: attempt lower-tier model → use cached response → apply rule-based fallback → human escalation.

### 2.2 Saga Pattern and Compensation Actions

For multi-step agent workflows where steps have external side effects (database writes, API calls, emails), the saga pattern provides rollback semantics absent from simple retry loops.

Each step defines a forward action and a compensation action. A stack of compensations accumulates as steps succeed. On failure at step N, compensations are executed in reverse order from N-1 to 1.

Two implementation variants:
- **Orchestration saga**: A central coordinator directs compensation sequence (analogous to COS orchestrator directing sub-agents). Provides centralized visibility; single point of failure.
- **Choreography saga**: Each agent reacts to failure events and executes its own compensation independently. Higher resilience; harder to trace.

The AWS prescriptive guidance framework positions orchestration sagas as the preferred model for LLM-based workflows because reasoning agents require centralized state and the orchestrator's context window serves as the saga log.

Prompt chaining maps naturally onto the saga pattern: each prompt chain step is a local transaction; LLM-directed self-correction is the compensation mechanism. Unlike traditional database transactions, saga compensations in LLM workflows are *approximate* — an LLM cannot "un-send" an email, but it can draft a follow-up correction. This asymmetry is fundamental and must be tracked at the application layer, not assumed away.

### 2.3 Idempotency Keys in Agent Tools

The Adaline production guide documents that LLM agents retry tool calls 15–30% of the time due to timeouts, validation errors, or model uncertainty. Without idempotency controls, stateful tool calls duplicate their side effects on each retry.

The Stripe-derived pattern:
1. Generate a deterministic key from stable workflow context: `f"{workflow_run_id}:{step_index}:{action_type}"`
2. Never include timestamps or random values in the key
3. Pass the key as a header or request parameter to downstream services
4. Downstream services deduplicate on the key and return the cached result on replay

Three distinct idempotency scopes (per AxonFlow analysis):
1. **API call boundary**: Protects a single outbound HTTP call; useless for surrounding workflow state
2. **Workflow boundary**: Protects all steps within a single run; requires separate completion-state tracking
3. **Cross-workflow boundary**: Protects business operations across multiple workflow instances; largely unsolved in current platforms

The four outcomes that require distinct tracking: success, explicit failure, timeout (ambiguous), and unknown (requires human review). A retry that follows a timeout is unsafe without idempotency because the write may have succeeded before the timeout fired.

When using durable execution frameworks (Temporal, Conductor), idempotency is guaranteed at the Activity level automatically. Temporal's event history makes the workflow deterministic: a worker resuming after a crash replays the exact same sequence and produces the same results. For COS, which does not currently use a durable execution framework, idempotency must be implemented explicitly at the tool dispatch layer.

---

## 3. Failure-Mode Taxonomy

The following taxonomy synthesises all surveyed frameworks into seven distinct failure classes, each requiring a different primary strategy:

| ID | Class | Examples | Retriable? | Primary Strategy |
|---|---|---|---|---|
| F1 | **Transient infrastructure** | Network reset, DNS failure, TLS error, brief 5xx | Yes | Exponential backoff + jitter, max 3 attempts |
| F2 | **Rate limit / quota** | HTTP 429, TPM/RPM exhaustion | Yes (with delay) | Honour `Retry-After`; exponential backoff base 2 s, max 7 attempts |
| F3 | **Output schema violation** | Pydantic ValidationError, malformed JSON, missing required field | Yes (limited) | Validation-driven retry: include schema + error in next prompt; max 3 |
| F4 | **Tool execution failure** | API timeout, file lock, external service 503 | Conditional | Per-tool timeout + idempotency key; retry only if idempotent or key present |
| F5 | **Semantic / quality failure** | Hallucination detected, guardrail failed, trust score < threshold | Conditional | Re-prompt with failure context; escalate to human after 2 attempts |
| F6 | **Depth / budget exhaustion** | max_turns reached, retry budget consumed, cost cap hit | No | Hard stop; emit structured error; route to human or fallback agent |
| F7 | **Non-retriable client error** | 400 Bad Request, 401 Auth, 403 Forbidden, malformed tool args | No | Fail immediately; log structured error; do not retry |

**Decision rule at failure time:**
```
classify(error) ->
  F7 or F6 -> FAIL FAST
  F1 or F2 -> BACKOFF_RETRY (check circuit breaker state first)
  F3       -> VALIDATION_RETRY (structured re-prompt)
  F4       -> TOOL_RETRY (check idempotency key, then retry or queue)
  F5       -> SEMANTIC_RETRY (2 attempts) -> HUMAN_ESCALATION
```

---

## 4. Retry-Strategy Menu

### Strategy A: Exponential Backoff with Jitter (F1, F2)
```
attempts:     3 (F1) or 7 (F2)
base_delay:   0.5 s (F1) or 2.0 s (F2)
multiplier:   2
max_delay:    60 s
jitter:       0–25% of computed delay
honour_header: Retry-After (override computed delay)
```
Apply at: Anthropic SDK call site (infrastructure layer); also at orchestrator layer for F2 since SDK retries are opaque.

### Strategy B: Validation-Driven Re-prompt (F3)
```
attempts:     3
re_prompt_template: "Your previous output failed validation.\nSchema: {schema}\nError: {error}\nPrevious output: {output}\nPlease correct and try again."
backoff:      none (validation failures are not rate-limited)
state_update: inject schema + error into agent context before retry
```
Apply at: skill dispatch layer, after `with_structured_output` fails. This is the LangGraph state-modifying retry pattern adapted for COS.

### Strategy C: Idempotent Tool Retry (F4)
```
key_generation: sha256(f"{workflow_id}:{step_idx}:{tool_name}")
timeout_budget: per-tool (fast API: 2 s, code sandbox: 20 s, pipeline: 120 s)
retry_on:       timeout or 5xx AND idempotency_key_confirmed_absent
skip_retry_on:  timeout AND idempotency_key_status == "unknown"
max_attempts:   3
escalation:     route to human review if outcome is unknown
```
Apply at: tool execution layer for all stateful tool calls.

### Strategy D: Circuit Breaker (F1/F2 at scale)
```
window:         60 s (LLM calls), 10 s (inter-agent)
error_threshold: 50% failure rate over 20+ requests
open_duration:  30 s (doubling on repeated trips)
half_open:      10% traffic, probe with simplified prompt
metrics:        error_rate + latency_p95 + token_quota_pct + validation_failure_rate
fallback_chain: [lower_model, cached_response, rule_based, human]
```
Apply at: provider gateway / LLM dispatch layer (`lib/dispatch.py`).

### Strategy E: Saga Compensation (multi-step workflows)
```
step_registration: on step_start, push (step_id, compensation_fn) to saga_stack
compensation_trigger: on failure at step N
compensation_order: reverse stack from N-1 to 0
compensation_timeout: 30 s per compensation action
partial_compensation: mark steps that cannot be fully reversed with "approximate" flag
log: emit saga_event per step transition to audit log
```
Apply at: orchestrator layer for any workflow with external side effects spanning >1 tool call.

### Strategy F: Human Escalation Gate (F5, F6)
```
trigger: semantic_retry_count >= 2 OR depth_budget_exhausted OR saga_compensation_failed
action:
  1. Emit structured escalation event with: failure_class, attempt_history, last_error, workflow_state_snapshot
  2. Pause workflow (suspend, do not terminate)
  3. Wait for human response with timeout (default 24 h)
  4. On approval: resume from checkpoint
  5. On rejection or timeout: execute saga compensation if applicable, then fail
```
Apply at: orchestrator layer; hook into existing phase-aware approval gate (production/maintenance phases already require human approval per `phase-aware-agents.md`).

---

## 5. Recommendation: Unified Retry Contract for COS

### 5.1 Current State

COS retry semantics are distributed and inconsistent:
- `closed-loop-prompts.md` defines "max 3 retries" with no failure classification
- `task-dag.md` uses FAILED → READY transitions with max 3, but no backoff specification
- `fault-tolerance.md` references "max retry: 24 base + 8 per profile, cap 160" — these are for a different subsystem and create misleading precedent
- `phase-aware-agents.md` correctly distinguishes automatic retry (reconstruction/stabilization) from human-approved retry (production/maintenance) but does not define *which* failures qualify
- `rate-limiting.md` handles queuing but not exponential backoff
- None of the above address circuit breakers, saga compensation, or idempotency keys

### 5.2 Proposed Contract: `rules/retry-contract.md`

The contract should define three layers:

**Layer 1 — Infrastructure (transparent to agent logic)**
- Anthropic SDK handles F1/F2 automatically (opaque; COS cannot observe retry count)
- COS orchestrator adds a second F1/F2 loop for connection errors the SDK does not retry (ECONNRESET etc.)
- Circuit breaker lives here; state shared across all provider calls via `lib/dispatch.py`

**Layer 2 — Skill/Agent dispatch (COS-owned)**
- Classify failure on receipt using the F1–F7 taxonomy
- Apply per-class strategy from the menu above
- Emit a `retry_event` to `error-learning.jsonl` with: `{failure_class, attempt_number, workflow_id, step_id, error_type, backoff_ms}`
- Respect phase-aware gate: auto-retry in reconstruction/stabilization; require approval in production/maintenance (existing rule preserved)

**Layer 3 — Workflow orchestration (saga + idempotency)**
- All stateful tool calls receive deterministic idempotency keys
- Multi-step workflows with external effects register saga stacks
- Exhaustion of retry budget at any layer triggers escalation gate (Strategy F)

### 5.3 Specific Implementation Steps

1. **Create `lib/retry_contract.py`** implementing `classify_failure(exc) -> FailureClass` and `get_strategy(failure_class, phase) -> RetryStrategy`. This is the single authoritative classification point.

2. **Update `lib/dispatch.py`** to add circuit breaker state machine around provider calls (Strategy D). Use an in-process state store initially; replace with Valkey when `agent-communication` is active.

3. **Add `IdempotencyKeyMixin`** to the base tool class. Generate keys from `workflow_id + step_idx + tool_name`. Store key → outcome in a short-TTL cache (10 min) to handle same-session retries.

4. **Consolidate retry rules** into a single `rules/retry-contract.md` that references `lib/retry_contract.py` as the authoritative implementation. Deprecate per-file retry magic numbers.

5. **Extend `error-learning.jsonl` schema** to include `failure_class` and `strategy_applied` fields, enabling automated detection of retry patterns across sessions.

### 5.4 What NOT to Unify

The phase-aware human-approval gate (`phase-aware-agents.md`) should remain separate — it is a governance policy, not a retry mechanism. The SDD apply-verify retry loop (max 3, CRITICAL-only re-runs) is a quality gate, not an error recovery mechanism, and should remain in `sdd-apply` skill logic.

---

## 6. Uncertainty and Caveats

- **Codex `max_depth` specifics**: The Codex CLI source is in Rust; public documentation does not expose the full parameter surface for `agents.max_depth`. The analysis is based on AGENTS.md documentation and changelog entries. Verify by reading `codex-rs/src/` source directly before implementation.
- **AutoGen v0.4 vs v0.2**: AutoGen underwent a major API redesign in v0.4; retry behavior described here reflects v0.2 `llm_config` patterns. The v0.4 event-driven model may expose different retry hooks.
- **Pydantic ValidationError bypass in LangGraph**: Issue #6027 was open as of research date. Verify fix status before adopting LangGraph's `retry_on` for structured output failures.
- **Saga compensation approximation**: LLM-based compensation (re-prompting to "undo" an action) is semantically approximate. For high-stakes workflows (billing, external API mutations), saga stacks must be augmented with explicit API-level reversal calls where available.

---

## Sources

1. LangGraph RetryPolicy API Reference — https://reference.langchain.com/python/langgraph/types/RetryPolicy
2. LangGraph error handling guide (DEV Community) — https://dev.to/aiengineering/a-beginners-guide-to-handling-errors-in-langgraph-with-retry-policies-h22
3. LangGraph GitHub issue #6027 — ValidationError bypasses RetryPolicy — https://github.com/langchain-ai/langgraph/issues/6027
4. LangGraph forum — flow control after retries exhausted — https://forum.langchain.com/t/the-best-way-in-langgraph-to-control-flow-after-retries-exhausted/1574
5. LangGraph state-modifying retry PR #2957 — https://github.com/langchain-ai/langgraph/pull/2957
6. Anthropic SDK Python — Request lifecycle and error handling (DeepWiki) — https://deepwiki.com/anthropics/anthropic-sdk-python/4.5-request-lifecycle-and-error-handling
7. Claude Code issue #37077 — Connection errors never retried — https://github.com/anthropics/claude-code/issues/37077
8. OpenAI Agents SDK — Error recovery patterns (DeepWiki) — https://deepwiki.com/openai/openai-agents-python/14.2-multi-agent-orchestration-examples
9. Portkey — Retries, fallbacks, circuit breakers in LLM apps — https://portkey.ai/blog/retries-fallbacks-and-circuit-breakers-in-llm-apps/
10. Circuit breaker patterns for AI agent reliability (Hendricks) — https://brandonlincolnhendricks.com/research/circuit-breaker-patterns-ai-agent-reliability
11. SRE circuit breaker patterns for LLM APIs (n1n.ai) — https://explore.n1n.ai/blog/circuit-breakers-llm-api-sre-reliability-patterns-2026-02-15
12. AI agent retry patterns taxonomy (Fast.io) — https://fast.io/resources/ai-agent-retry-patterns/
13. Reliable tool-using AI agents in production (Adaline) — https://labs.adaline.ai/p/reliable-tool-using-ai-agents-production
14. Saga orchestration patterns for AI — AWS Prescriptive Guidance — https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/saga-orchestration-patterns.html
15. Saga pattern for AI workflow orchestration (SparkCo) — https://sparkco.ai/blog/master-saga-pattern-for-ai-workflow-orchestration
16. Idempotency boundaries in multi-system AI automation (AxonFlow) — https://getaxonflow.com/blog/idempotency-boundaries-in-multi-system-ai-automation/
17. Claude Agent SDK + Temporal durable execution guide (ClaudeLab) — https://claudelab.net/en/articles/api-sdk/claude-agent-sdk-temporal-durable-ai-workflows-production-guide
18. Mastering retry logic agents — 2025 best practices (SparkCo) — https://sparkco.ai/blog/mastering-retry-logic-agents-a-deep-dive-into-2025-best-practices
19. Temporal — saga compensating transactions — https://temporal.io/blog/compensating-actions-part-of-a-complete-breakfast-with-sagas
