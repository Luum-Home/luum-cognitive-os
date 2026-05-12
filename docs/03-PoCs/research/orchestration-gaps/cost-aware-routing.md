# Cost-Aware Routing: Budget Enforcement Architectures for LLM Agent Orchestration

**Date:** 2026-05-06
**Status:** Research — no code changes
**Scope:** Budget enforcement patterns, prediction-vs-actual reconciliation, and wiring recommendations for `lib/cost_predictor.py` into per-session enforcement within COS.

---

## 1. The Core Gap

COS today has model-routing rules per skill (opus/sonnet/haiku mapped in `PHASE_MODEL_DEFAULTS` and the `CLAUDE.md` routing table), a predictive cost engine (`lib/cost_predictor.py`), a dispatch layer (`lib/dispatch.py`) with an ADR-050 `budget_max_usd_per_call` parameter, and a dispatch auto-optimizer (`lib/dispatch_optimizer.py`). What is absent is a **per-session / per-agent budget ledger with synchronous enforcement**. The prediction engine accumulates historical data and produces a range estimate. The dispatch layer enforces a single-call cap. Nothing ties these together to enforce an aggregate dollar ceiling for a session or an SDD pipeline run, nor does the system apply backpressure when a rolling spend approaches a configured limit.

This gap is precisely the failure mode documented in the "$47,000 agent loop" incident (November 2025): agents with monitoring but without execution-layer enforcement can exhaust budgets before any alert has time to fire [1].

---

## 2. Industry Reference Implementations

### 2.1 LiteLLM BudgetManager and Provider Budget Routing

LiteLLM provides the most complete open-source reference for multi-layer budget enforcement [2][3][4].

**BudgetManager** operates at the user or session level. Before each LLM call, the implementation checks `budget_manager.get_current_cost(user) <= budget_manager.get_total_budget(user)`. If the check fails, it raises `BudgetExceededError` synchronously, blocking the call. Budgets reset on configurable intervals (daily, weekly, monthly, yearly). Storage is either in-memory or backed by a remote database via self-hosted `/get_budget` and `/set_budget` endpoints. The class supports two cost-tracking modes: completion-object-based (exact) and text-based (estimated), which allows pre-flight estimation before a response is even received.

**Provider Budget Routing** extends this to the provider tier [3]. Each provider (OpenAI, Azure, etc.) has a `budget_limit` in USD and a `time_period` string. Spend is tracked in Redis across all proxy instances and synced via TTL-keyed counters. When a provider exceeds its budget, the router skips it in the cascade. If all providers have exceeded their budgets, the proxy returns HTTP 429 with message: "No deployments available - crossed budget for provider." Reset is automatic when the TTL expires.

**Agent Iteration Budgets** — the most relevant pattern for COS [4] — adds two controls specifically for agentic loops:
- `max_budget_per_session`: A dollar ceiling per trace/session ID. After each successful call, cost is accumulated. Before each call, the accumulated spend is checked. Exceeding the cap returns HTTP 429: "Session budget exceeded for session [ID]. Current spend: $[x], max_budget_per_session: $[cap]."
- `max_iterations`: A hard cap on the number of LLM calls in a session, also returning 429 when exceeded.
- Sessions are keyed via `x-litellm-trace-id` header or `metadata.session_id`. Counters expire after one hour by default.

This architecture demonstrates that session-level budget enforcement requires three components: a session identity, a running accumulator, and a synchronous pre-call check gate.

### 2.2 OpenRouter Provider Selection and Cost Routing

OpenRouter implements cost-aware provider selection at the request dispatch layer [5][6].

The default strategy is inverse-square load balancing weighted by price: a provider at $1/M tokens receives 9x more traffic than one at $3/M. The algorithm evaluates three criteria in order: recent stability (excluding providers with outages in the last 30 seconds), lowest pricing among stable options, and availability as fallbacks.

Two shortcut routing modes are exposed:
- **`:floor`** (appended to model slug): disables load balancing entirely, always routes to the cheapest available provider.
- **`:nitro`**: prioritizes throughput over cost.

Hard budget enforcement uses the `max_price` field, which specifies maximum acceptable rates per prompt token, completion token, request, or image. Unlike performance thresholds that merely deprioritize options, `max_price` violations **prevent request execution entirely** rather than deprioritizing — making it a synchronous budget gate rather than a soft signal [5].

Model fallbacks [6] are ordered arrays: the system tries providers sequentially, and you pay based on whichever model processes the request. Budget-aware triggering is not built in — fallbacks respond to availability failures, not spend thresholds. This gap is important: cost degradation (e.g., escalating from a cheap Qwen call to Claude) is not automatically modeled as a budget event.

### 2.3 Anthropic Claude Code Cost Controls

Claude Code (Anthropic's reference implementation) provides workspace-level controls but leaves per-session enforcement to the application layer [7].

Key mechanisms:
- **Workspace spend limits** via the Claude Console API — an org-level ceiling on total monthly spend for the "Claude Code" workspace.
- **Rate limit tables** per team size (e.g., 15k-20k TPM per user for 100-500 user orgs) to prevent one user starving others.
- **PreToolUse hooks** as a cost-reduction primitive: hooks can filter, compress, or reject tool inputs before they generate tokens. A grep-for-ERROR hook reduces a 10,000-line log context to hundreds of lines.
- **Subagent isolation**: delegating verbose operations to subagents keeps verbose output in the subagent's context window, returning only a summary to the orchestrator.
- **Extended thinking budget**: `MAX_THINKING_TOKENS=8000` caps reasoning token spend per request.
- **Background usage**: conversation summarization and `/usage` command generate background tokens (~$0.04/session), establishing a baseline cost floor.

Notably absent from Anthropic's own implementation: per-session dollar caps that can be enforced without workspace-level admin access. The `/usage` command provides estimates but these are local computations, not enforcement.

### 2.4 Helicone Cost Observability and Session Tracking

Helicone provides the reference pattern for cost observability as a proxy layer [8].

Sessions are tracked by passing `Helicone-Session-Id` and `Helicone-Session-Name` HTTP headers. This groups all requests within a workflow into a cost-attributed session. Cost properties (`Helicone-Property-*`) enable segmentation by user tier, feature, and environment.

Budget alerts fire at graduated thresholds (50%, 80%, 95% of configured budget) via email or Slack. The key architectural distinction Helicone makes is between **observability** (tracking what was spent) and **enforcement** (blocking what would be spent). Their product provides the former with alert hooks that can trigger external enforcement — but the enforcement itself must be implemented by the application. This is the canonical pattern for read-path observability combined with write-path enforcement at the execution layer.

### 2.5 Aider `--cache-prompts` Cost Behavior

Aider implements a prompt caching strategy that functions as a passive budget optimization [9].

When `--cache-prompts` is enabled, Aider organizes its context so that the system prompt, read-only files, repository map, and editable files are cached on the provider side (Anthropic Sonnet/Haiku and DeepSeek Chat are supported). This directly reduces input token costs by avoiding re-processing of stable context on every message.

The keepalive mechanism (`--cache-keepalive-pings N`) sends up to N pings at 5-minute intervals after each message to prevent Anthropic's default 5-minute cache expiration from flushing the cached prefix. This converts what would otherwise be repeated full-context charges into cache read charges — typically 10x cheaper on Anthropic (cache read: $0.30/MTok vs. cache write: $3.75/MTok for Sonnet).

The cost implication for COS: skills that are invoked repeatedly within a session (e.g., `run-tests` called after every `sdd-apply` iteration) are paying full input token cost on each call because COS does not currently send `cache_control` markers to the Anthropic API. Aider's pattern suggests that stable prefix content (CLAUDE.md, skill definitions, project context) should be explicitly marked as cacheable, turning a repeated per-call cost into a one-time write with cheap subsequent reads.

### 2.6 Backpressure Patterns: Beyond Exponential Backoff

Recent systems research identifies four complementary patterns that work together for LLM pipeline resilience [10]:

**Token Bucket Queuing**: Rather than reacting to 429 errors, consume a local token bucket proportional to estimated request size. When the bucket is empty, requests wait in queue rather than firing and failing. This aligns the application's own admission control with the provider's actual enforcement model and prevents oscillation loops (retry bursts that repeatedly exhaust quota).

**Priority Lane Routing**: A three-tier system (P0: interactive, P1: non-interactive API, P2+: batch) prevents background work from blocking user-facing requests. Research shows priority scheduling improves SLO attainment by 40-90% over FIFO queuing. For COS, this maps directly to: interactive orchestrator messages (P0), SDD pipeline phases (P1), batch archiving/doc generation (P2).

**Token-Aware Circuit Breakers**: Standard error-rate circuit breakers miss cost-dimension failures. Production circuit breakers should monitor: token consumption rate (trip at 85% of provider TPM), P95 latency thresholds, **hourly cost caps**, and consecutive 429 counts. COS already has a rate-limit tracker (`lib/rate_limit_tracker.py`) that implements the 85% TPM threshold — the missing dimension is the hourly cost cap.

**Proactive Load Shedding**: Under overload, accepting every request and failing most is worse than rejecting early. When a session's running cost approaches its ceiling, the system should return a 503-equivalent immediately rather than attempting the call and receiving a provider-level 429.

### 2.7 AgentBudget: Real-Time Execution Layer Enforcement

AgentBudget [11] demonstrates the minimal viable architecture for per-process enforcement as a pure Python library with no external infrastructure.

The pattern:
```python
import agentbudget
agentbudget.init(budget=0.50)   # $0.50 session ceiling

# SDK patching — intercepts Anthropic/OpenAI calls at the client level
# Before each call: check agentbudget.remaining() >= estimated_cost
# After each call: agentbudget.spent() += actual_cost

if agentbudget.remaining() < MINIMUM_VIABLE_CALL_COST:
    raise BudgetExhaustedError("Session ceiling reached")
```

The library patches OpenAI and Anthropic SDK clients directly. Loop detection ("automatic loop detection kills runaway sessions") addresses the specific failure mode where agents get stuck retrying tool calls — a pattern that multiplies cost without progress. The `AsyncBudgetSession` class handles concurrent agent sessions with independent budget accounting per session ID.

### 2.8 The Alerts-vs-Enforcement Distinction

The "$47,000 agent loop" incident [1] provides the clearest statement of the architectural requirement: monitoring operates asynchronously (dashboards, alerts, emails) while budget enforcement must operate synchronously in the critical path of each API call. A cost dashboard that fires an alert at $1,000 spent cannot prevent the next call that costs $500. Only a pre-call check gate — evaluated before the HTTP request leaves the process — can enforce an absolute ceiling.

Three additional failure modes require enforcement at the infrastructure layer rather than the application layer [12]:
1. If the agent crashes and restarts, application-level counters reset. Infrastructure-level enforcement (Redis-backed, or persistent file) survives restarts.
2. Multi-process agent fleets (parallel COS sub-agents) must share a budget ledger. In-process counters are per-process by definition.
3. Adversarial agent behavior (an agent that catches BudgetExceededError and retries) can bypass application-layer checks.

### 2.9 Capability-Tier Escalation Patterns

The field has converged on a three-tier capability escalation model [13][14]:

**Tier 1 — Haiku (Lightweight)**: binary/multi-class classification, simple extraction, high-volume repetitive tasks. 70% cheaper per token. Target: 60% of all requests.

**Tier 2 — Sonnet (Mid-Tier Reasoning)**: complex extraction, multi-step reasoning, nuanced classification, code tasks. 5-7% better accuracy than Haiku on ambiguous tasks. Target: 30% of requests.

**Tier 3 — Opus (Heavy Reasoning)**: architectural decisions, root cause analysis, novel problem synthesis. ~5x cost multiplier over Sonnet. Target: 10% of requests.

The escalation pattern: attempt with Haiku, check confidence or quality score, escalate to Sonnet if below threshold, escalate to Opus only if Sonnet confidence is insufficient. If escalation rate from Haiku to Sonnet exceeds 30%, the confidence threshold is miscalibrated or the task type should default to Sonnet.

For 100,000 daily classification requests:
- All-Haiku: ~$1,080/month
- All-Sonnet: ~$4,050/month  
- All-Opus: ~$20,000+/month
- Tiered with 60/30/10 split: ~$2,600/month

A well-calibrated routing system saves 50-80% versus worst-case model selection [14].

The key insight missing from COS: COS has static per-phase model assignments (`PHASE_MODEL_DEFAULTS`). It lacks dynamic quality checking that would allow a Sonnet `apply` phase to escalate to Opus if the task exceeds a complexity threshold detected at runtime.

### 2.10 Pre-Flight Cost Prediction

The PreflightLLMCost tool [15] demonstrates pre-call estimation as a gating mechanism. Before submitting an inference request, it:
1. Tokenizes the prompt using the target model's tokenizer
2. Estimates output tokens from historical distribution for the task type
3. Computes predicted cost using current price tables
4. Compares against a session budget ceiling
5. Blocks execution if predicted cost would exceed remaining budget

This is the integration point COS is closest to achieving: `CostPredictor.predict()` already produces `estimated_cost_mid` and a confidence range. The missing wire is: call `predict()` before launching each sub-agent, compare `estimated_cost_mid` against a session `remaining_budget`, and refuse to dispatch if the prediction exceeds it.

---

## 3. Budget Enforcement Architecture Patterns

Drawing from the field, three architectures are viable for COS:

### 3.1 Pattern A: Proxy-Based Enforcement (LiteLLM / Helicone style)

A sidecar proxy intercepts all LLM API calls, maintains a Redis-backed spend ledger keyed by session ID, and enforces budget limits at the HTTP layer. This is infrastructure-heavy but supports multi-process agent fleets.

```
Orchestrator → Dispatch → [COS Budget Proxy] → Provider API
                                ↑
                         Redis spend ledger
                         (session_id → cumulative_cost)
```

Advantages: Survives agent restarts. Enforces across parallel sub-agents. Requires no changes to each skill. Disadvantages: Adds network latency per call (~50ms), requires Redis or equivalent.

### 3.2 Pattern B: In-Process Session Ledger (AgentBudget style)

A lightweight in-process class wraps the dispatch layer, accumulates cost post-call, and checks remaining budget pre-call.

```python
class SessionBudget:
    def __init__(self, ceiling_usd: float, session_id: str):
        self._ceiling = ceiling_usd
        self._spent = 0.0
        self._session_id = session_id
    
    def pre_call_check(self, predicted_cost: float) -> None:
        if self._spent + predicted_cost > self._ceiling:
            raise SessionBudgetExceeded(
                f"Session {self._session_id}: spent=${self._spent:.4f}, "
                f"ceiling=${self._ceiling:.2f}, predicted=${predicted_cost:.4f}"
            )
    
    def record_actual(self, actual_cost: float) -> None:
        self._spent += actual_cost
```

Advantages: Zero infrastructure dependency. Integrates directly into `dispatch()`. Disadvantages: Does not survive crashes. Does not aggregate across parallel sub-agents (unless persisted to file).

### 3.3 Pattern C: File-Backed Session Ledger (COS native)

Extends Pattern B by persisting the session ledger to `.cognitive-os/metrics/session-budget-{session_id}.json`. This provides crash survivability without Redis. On process restart, the session ledger is reloaded and enforcement continues from the accumulated spend.

```
dispatch() → SessionBudgetLedger.pre_call_check()
                     ↑
    .cognitive-os/metrics/session-budget-{id}.json
                     ↑
    dispatch() → SessionBudgetLedger.record_actual()
```

This is the recommended pattern for COS given existing infrastructure. The `.cognitive-os/metrics/` directory already exists and is used by `cost-events.jsonl` and `llm-dispatch.jsonl`.

---

## 4. Prediction-vs-Actual Reconciliation

All three architectures face the same problem: cost predictions are wrong. The field has converged on two reconciliation strategies:

**Calibration Factor Approach** (used by COS `CostPredictor._get_calibration_factor()`): track the ratio of predicted to actual costs across historical tasks. When actual exceeds predicted by a consistent factor, multiply all future predictions by that factor. COS already implements this via `lib/estimation_calibrator.py`. The gap: this factor is applied to task-level predictions but not to per-call dispatch-time estimates.

**Running Average Approach**: for each (model, task_type) tuple, maintain a rolling average of actual cost per call. Use this as the dispatch-time estimate rather than the static `DEFAULT_MODEL_PRICES` table. LiteLLM's provider budget routing uses this pattern via Redis-accumulated spend divided by call count.

COS's `get_real_model_prices()` method in `CostPredictor` already implements the running-average approach for model price discovery (measuring actual $/token from `cost-events.jsonl`). The reconciliation gap is that this measured price is not fed back into the dispatch-time pre-call estimate — `dispatch.py` does not call `CostPredictor`.

The reconciliation loop that should exist:
```
Task prediction (CostPredictor.predict) 
    → Session budget allocation
    → Per-call pre-flight check (estimated cost from real model prices)
    → Call execution
    → Actual cost recording (cost-events.jsonl)
    → Calibration update (estimation_calibrator)
    → Next task prediction uses updated calibration
```

Currently steps 2, 3 (budget allocation and pre-flight check) are absent.

---

## 5. Wiring Recommendations for `lib/cost_predictor.py`

### 5.1 Introduce `lib/session_budget.py`

Create a `SessionBudget` class implementing Pattern C (file-backed session ledger). This class should:
- Accept a `ceiling_usd` and `session_id` at construction
- Load existing spend from `.cognitive-os/metrics/session-budget-{session_id}.json` if it exists (crash recovery)
- Expose `pre_call_check(predicted_usd: float)` that raises `SessionBudgetExceeded` when `spent + predicted > ceiling`
- Expose `record_actual(actual_usd: float)` that persists to the ledger file after each call
- Expose `remaining_usd()` and `spent_usd()` properties
- On `SessionBudgetExceeded`, include the session ID, spent amount, remaining amount, and which call triggered the exception

### 5.2 Wire `CostPredictor.get_real_model_prices()` into Dispatch

In `dispatch()`, add an optional `session_budget: SessionBudget | None = None` parameter. Before attempting a provider:
1. Use `CostPredictor().get_real_model_prices()` to get the measured cost per token for the target model
2. Estimate the call cost from the prompt token count (tokenize or use a rough 1 token/4 chars estimate)
3. Call `session_budget.pre_call_check(estimated_cost)` if a budget is attached
4. After a successful call, call `session_budget.record_actual(result.cost_usd)`

This wire costs approximately 5-10ms per call (one file read on first check, file write on record) and requires no external infrastructure.

### 5.3 Attach Budgets at SDD Pipeline Phase Transitions

In the SDD orchestration flow, before each phase agent is launched:
1. Call `CostPredictor.estimate_per_phase(task_type)` to get the phase-specific estimate
2. Check that the remaining session budget covers the estimate
3. If not, surface a budget warning to the operator before proceeding — do not silently degrade to a cheaper model without operator visibility

This converts the current "predict once before task" pattern into "check before each phase", enabling per-phase budget gates without changing the overall task-level prediction architecture.

### 5.4 Add Graduated Backpressure Signals

Mirroring the iteration budget pressure pattern from the NousResearch hermes-agent proposal [16], add graduated warnings as the session budget is consumed:

- At 70% spend: inject a `[COST_CAUTION]` marker into the orchestrator context — still operating normally but signal to prefer cheaper models for remaining work
- At 90% spend: surface `[COST_WARNING]` — switch remaining phases to the cheapest capable model tier
- At 100% spend: raise `SessionBudgetExceeded` — do not dispatch further calls

This avoids the binary hard-stop problem (no warning before termination) while still providing real enforcement at 100%.

### 5.5 Expose Session Budget via `/cost-predict` Skill Integration

The existing `cost-predictor` skill produces a one-time prediction. Augment it to also accept a `--session-ceiling` parameter that allocates a `SessionBudget` for the current session and attaches it to subsequent dispatch calls. This gives operators a one-command way to set a session budget before starting an SDD pipeline.

---

## 6. Gaps and Risks

**Estimation accuracy**: `CostPredictor` uses Jaccard word similarity for task matching. For novel tasks without close historical analogues, the model-routing fallback produces wide ranges (0.7x to 1.5x mid-point). Blocking a call based on a high-confidence overestimate would be a false positive. Recommendation: use `estimated_cost_max` (not `mid`) for the pre-call check when the session is early (first 30% of budget), and switch to `estimated_cost_mid` once the historical base is well-populated (confidence > 0.6).

**Multi-agent parallelism**: File-backed session ledgers have a write-race condition when multiple sub-agents run in parallel. Mitigation: use file-locking (Python `fcntl` or a lockfile pattern) or accept a small overrun window with a 10% budget buffer. A Redis-backed ledger (Pattern A) eliminates the race entirely at the cost of infrastructure dependency.

**Provider-reported vs. estimated cost**: `dispatch.py` records `cost_usd` from the provider response. Providers sometimes return 0.0 for cost when the API call does not include usage metadata (observed with some Qwen responses). `record_actual(0.0)` would silently under-count spend. Recommendation: fall back to the estimated cost when the provider-reported cost is 0 and the call was successful.

**Cache interactions**: Anthropic prompt caching means the actual cost of a repeated call is 10-12x lower than the estimated cost (cache read price vs. cache write price). The pre-flight estimate should distinguish between first-occurrence calls (full price) and repeated calls with a stable prefix (cache read price). This is complex to implement correctly without knowing the cache state, but a conservative fallback is to use the full price for estimation and accept underspend.

---

## 7. Summary

The LLM cost governance field has converged on a layered architecture with distinct responsibilities:

| Layer | Responsibility | COS Current State |
|---|---|---|
| Prediction (pre-task) | Estimate task cost from history | Implemented (`CostPredictor`) |
| Pre-call estimation | Estimate single-call cost from prompt + model prices | Partially (price table exists, not wired to dispatch) |
| Pre-call enforcement | Block call if predicted cost exceeds session remaining | Absent (ADR-050 `budget_max_usd_per_call` exists but is per-call, not session) |
| Actual recording | Capture actual cost post-call | Implemented (`cost-events.jsonl`) |
| Session accumulation | Running sum of actual cost for session | Absent |
| Calibration update | Adjust future predictions based on prediction error | Implemented (`estimation_calibrator`) |
| Graduated backpressure | Warn operator as budget is consumed | Absent |
| Tier escalation | Dynamically route to cheaper model based on quality | Static per-phase (no runtime confidence check) |

The minimum viable enforcement gap to close: a `SessionBudget` class (Pattern C, file-backed) wired into `dispatch()` as an optional parameter, with a pre-call check using `get_real_model_prices()` and post-call recording. This requires no new infrastructure and builds directly on existing COS components.

---

## Sources

1. [The $47,000 Agent Loop: Why Token Budget Alerts Aren't Budget Enforcement](https://dev.to/waxell/the-47000-agent-loop-why-token-budget-alerts-arent-budget-enforcement-389i)
2. [LiteLLM Budget Manager](https://docs.litellm.ai/docs/budget_manager)
3. [LiteLLM Budget Routing](https://docs.litellm.ai/docs/proxy/provider_budget_routing)
4. [LiteLLM Agent Iteration Budgets](https://docs.litellm.ai/docs/a2a_iteration_budgets)
5. [OpenRouter Provider Selection](https://openrouter.ai/docs/05-Methodology/guides/routing/provider-selection)
6. [OpenRouter Model Fallbacks](https://openrouter.ai/docs/05-Methodology/guides/routing/model-fallbacks)
7. [Manage costs effectively — Claude Code Docs](https://code.claude.com/docs/en/costs)
8. [Helicone Cost Tracking](https://docs.helicone.ai/guides/cookbooks/cost-tracking)
9. [Prompt caching — Aider](https://aider.chat/docs/05-Methodology/usage/caching.html)
10. [Backpressure Patterns for LLM Pipelines: Why Exponential Backoff Isn't Enough](https://tianpan.co/blog/2026-04-15-backpressure-llm-pipelines)
11. [AgentBudget — Real-time cost enforcement for AI agents](https://agentbudget.dev)
12. [Agent Runaway Costs: How to Set LLM Budget Limits Before Costs Spiral](https://relayplane.com/blog/agent-runaway-costs-2026)
13. [Claude Sonnet 4.6 vs Haiku 4.5: The Model Routing Decision Tree](https://www.padiso.co/blog/claude-sonnet-4-6-vs-haiku-4-5-model-routing-decision-tree/)
14. [Best AI Model for Routing Guide — Augment Code](https://www.augmentcode.com/guides/ai-model-routing-guide)
15. [PreflightLLMCost — GitHub](https://github.com/aatakansalar/PreflightLLMCost)
16. [Feature: Iteration Budget Pressure — hermes-agent Issue #414](https://github.com/NousResearch/hermes-agent/issues/414)
17. [OpenCode: token usage, costs, and access control — Portkey](https://portkey.ai/blog/opencode-token-usage-costs-and-access-control/)
18. [LiteLLM cost tracking — Statsig](https://www.statsig.com/perspectives/litellm-cost-tracking)
