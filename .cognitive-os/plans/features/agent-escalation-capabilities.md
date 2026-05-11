<!--
RECONCILIATION STATUS: ARCHIVE WITH SCOPE REDUCTION — 2026-05-11 (Opus refinement of 2026-05-10 Sonnet pass)
Reconciled-by: P3 plan triage Opus re-triage (see docs/reports/p3-plan-triage-2026-05-10.md §Opus refinement)
Decision: ARCHIVE (Phases 1+2 only) — Phase 3 budget/retry-count work TOMBSTONED in-place.
Opus rationale (delta from Sonnet ARCHIVE): The plan's unique product wedge — typed capability signals (NEEDS_DEEPER_REASONING / TOOL_ACCESS / MORE_CONTEXT / DOMAIN_EXPERT) with orchestrator re-dispatch carrying context handoff to an upgraded model tier — is NOT covered by ADR-228 (which classifies *failure errors* into FailureClasses with retry policy, not *capability ceilings* with model-upgrade chains) nor by ADR-251 (which standardizes the orchestration adapter boundary but does not define signal vocabulary). So the plan is NOT TOMBSTONE-by-supersession. However, Phase 3 (budget gate + retry counts + escalation cost tracking) IS now superseded: ADR-228 owns retry counts/escalation_after_n per FailureClass, `hooks/dispatch-gate.sh` + the dispatch retry/budget/circuit-breaker hardening shipped in v0.28.0 own budget gating, and `lib/cost_dashboard.py` already reports session cost. Reviving Phase 3 as-written would duplicate ADR-228/ADR-251 territory. ARCHIVE Phases 1+2; treat Phase 3 as TOMBSTONED in-place. Reactivate Phases 1+2 when (a) recurring capability-ceiling incidents accrue (≥3 per quarter), or (b) operator prioritizes the typed-capability-signal feature explicitly via the ADR-254 manifest path.
Sonnet 2026-05-10 decision: ARCHIVE (whole plan, no scope split). Opus disagreement: scope-reduce Phase 3 to TOMBSTONE because ADR-228 + ADR-251 + dispatch-gate now cover its work directly; the rest of the plan still carries non-duplicate signal-protocol value worth parking.
Older inline reconciliation history (preserved for audit):
ON ICE — 2026-04-27
Related ADRs: ADR-036 (sprint orchestration primitives), ADR-038 (preamble v2 — reasoning-cycles cap + retry diversity + memory tiers)
Reconciled: 2026-04-21 (initial scope note); re-audited 2026-04-27 (no engineering progress)
Audit 2026-04-27: All 24 DoD items unchecked. grep of lib/escalation_detector.py, lib/dispatch_helper.py, lib/model_router.py finds zero occurrences of publish_escalation, _upgrade_model, handle_capability_escalation, NEEDS_DEEPER_REASONING. Zero commits in last 60 entries touch escalation. Base lib files exist but were not extended. Marked ON ICE — re-activate when (a) a concrete agent failure mode signals horizontal escalation as the cure, or (b) operator explicitly prioritizes.
Remaining scope (preserved for unfreezing): Capability-aware horizontal escalation (auto model-tier upgrade + structured ESCALATION handoff carrying partial progress). Existing commits deliver preamble-level escalation text and retry diversity, not cross-capability re-dispatch.
-->

# Plan: Agent Escalation Capabilities

> Created: 2026-04-13
> Status: DRAFT
> Author: Orchestrator (claude-sonnet-4-6)

---

## 1. Problem

The Cognitive OS has vertical escalation (agent → orchestrator) but no horizontal or
capability-aware escalation. When an agent encounters a task that exceeds its capability
— it needs deeper reasoning, a tool it doesn't have, more context window, or domain
expertise — it can only do one of:

1. Silently fail and return a low-quality result
2. Emit a generic `ESCALATION:` block and stop

Neither path preserves accumulated context, upgrades the capability, or retries with a
stronger agent. The orchestrator receives a stop signal but has no structured way to
re-dispatch with what the failing agent learned.

**Impact**: Multi-step tasks that hit a capability ceiling require full manual
re-launch, losing partial progress. Budget is wasted when haiku-level tasks are
pre-assigned to opus, and opus-level tasks silently underperform when mis-routed to sonnet.

---

## 2. Current State (as of 2026-04-13)

### 2.1 Vertical escalation (exists)

`templates/agent-preamble.md` defines an `ESCALATION:` block with four signal types:
- `loop_detected` — same file edited 3x
- `no_progress` — >10 calls without PROGRESS marker
- `error_repeat` — same error 2x
- `timeout_risk` — approaching token budget

`lib/escalation_detector.py` provides runtime detection for all four signals. It tracks
tool call patterns, progress markers, and confidence scores. Agents call
`detector.check_should_escalate()` and emit the formatted block.

The orchestrator parses `ESCALATION:` blocks from sub-agent output but re-dispatch logic
is ad-hoc — the orchestrator decides what to do manually with no typed signal to act on.

### 2.2 No capability signals (missing)

The `ESCALATION:` block has no typed capability signals. An agent cannot say:
- "This requires multi-step logical chain I cannot resolve" → need stronger model
- "I need the browser tool" → need tool access
- "This 300k-token codebase won't fit my context" → need larger window
- "This is a security audit, not a code task" → need domain expert

### 2.3 Static model routing (exists, not runtime-adaptive)

`rules/model-routing.md` defines routing per skill. `lib/model_router.py` implements
`select_model()`, `_downgrade_model()`, and a downgrade chain (`opus → sonnet → haiku`).
An upgrade chain is absent — `_downgrade_model()` exists but `_upgrade_model()` does not.

`lib/agent_bus.py` already has channels for `heartbeat`, `progress`, and `question`. No
escalation channel exists.

### 2.4 What exists that this plan builds on

| Component | Location | Role in this plan |
|-----------|----------|------------------|
| `EscalationDetector` | `lib/escalation_detector.py` | Extend with capability signal types |
| `AgentBus` | `lib/agent_bus.py` | Add `escalation` channel |
| `select_model()` | `lib/model_router.py` | Extend with `_upgrade_model()` |
| `ESCALATION:` block | `templates/agent-preamble.md` | Extend signal vocabulary |
| `dispatch_helper.py` | `lib/dispatch_helper.py` | Orchestrator re-dispatch entry point |
| `rules/agent-escalation.md` | `rules/agent-escalation.md` | Policy doc to update |

---

## 3. Proposal

### Phase 1: Capability Escalation Signal Protocol

**Goal**: Define four new typed capability signals that agents can emit. Wire them into
`EscalationDetector`, the preamble, and the agent bus.

#### 3.1.1 New signal types

Extend `EscalationSignal` in `lib/escalation_detector.py` with a new `capability_needed`
field and four new type literals:

| Signal | When to emit | What the orchestrator should do |
|--------|--------------|----------------------------------|
| `NEEDS_DEEPER_REASONING` | Task requires multi-step logical chain the agent cannot make progress on after 2 retries | Re-dispatch to next model tier |
| `NEEDS_TOOL_ACCESS` | Agent attempted to use a tool it doesn't have (browser, MCP, specific CLI) | Re-dispatch with tool access granted, or escalate to human |
| `NEEDS_MORE_CONTEXT` | Agent's context window is too small for the task (detected via `timeout_risk` + unsolved task) | Re-dispatch with summarized context or larger model tier |
| `NEEDS_DOMAIN_EXPERT` | Task is outside agent's domain (security audit, DB schema design, infra config) | Re-dispatch with domain-specific skill or escalate to human |

#### 3.1.2 Structured output format

Extend the `ESCALATION:` block with optional capability fields:

```
ESCALATION:
  Type: NEEDS_DEEPER_REASONING
  Capability: reasoning
  Attempted: [what was tried, 1-3 lines]
  Context_summary: [what was learned so far, for handoff]
  Partial_result: [any partial output the next agent can build on]
  Recommended_action: upgrade_model | grant_tool | expand_context | route_domain_expert
```

The `Type` field accepts all existing types plus the four new capability types. Existing
callers are unaffected — they only read `Type`.

#### 3.1.3 Detection logic in `EscalationDetector`

Add `_check_capability_ceiling()` method:
- Emits `NEEDS_DEEPER_REASONING` when: `error_repeat` triggered AND all errors are
  reasoning-class (AssertionError, wrong-output, wrong-logic — not syntax/compilation)
- Emits `NEEDS_MORE_CONTEXT` when: `timeout_risk` triggered AND task is not complete
  (no `RESULT:` block seen in output)
- `NEEDS_TOOL_ACCESS` and `NEEDS_DOMAIN_EXPERT` are agent-declared only (agent emits
  explicitly, detector doesn't auto-detect these)

#### 3.1.4 Agent bus channel

Add `cos:agent:{id}:escalation` channel to `AgentBus`:

```python
def publish_escalation(self, signal_type: str, capability: str,
                        context_summary: str, recommended_action: str) -> None:
```

The orchestrator subscribes via the existing `subscribe_all()` pattern.

#### 3.1.5 Preamble update

Add the four new types to the `ESCALATION:` block documentation in
`templates/agent-preamble.md`. Add a decision tree:

```
Before emitting ESCALATION:
1. Am I stuck due to my own model limitations? → NEEDS_DEEPER_REASONING
2. Am I missing a required tool? → NEEDS_TOOL_ACCESS
3. Is the codebase too large for my context? → NEEDS_MORE_CONTEXT
4. Is this task outside my training domain? → NEEDS_DOMAIN_EXPERT
5. None of the above → use existing types (loop_detected, no_progress, etc.)
```

---

### Phase 2: Orchestrator Re-dispatch

**Goal**: When the orchestrator receives a capability escalation signal, it re-launches
a new agent with upgraded capability and the failing agent's context handoff.

#### 3.2.1 Re-dispatch entry point

Add `handle_capability_escalation()` to `lib/dispatch_helper.py`:

```python
def handle_capability_escalation(
    original_task: str,
    signal: EscalationSignal,
    original_agent_id: str,
    retry_count: int = 0,
) -> AgentLaunchConfig:
```

The function:
1. Reads `signal.capability_needed` and `signal.recommended_action`
2. Determines new model via `_upgrade_model()` or domain routing
3. Assembles context handoff: original task + `signal.context_summary` + `signal.partial_result`
4. Returns `AgentLaunchConfig` ready to pass to the sub-agent launcher

#### 3.2.2 Context handoff format

The re-dispatched agent receives a prepended context block:

```
## Handoff Context (from prior agent {agent_id})

Prior agent: {model_tier} — escalated due to: {signal.type}
What was attempted: {signal.attempted}
What was learned: {signal.context_summary}
Partial result available: {signal.partial_result}

Resume from this state. Do NOT restart from scratch.
```

This block is injected before the original task description, NOT appended (so it appears
in the agent's early context window, not truncated at the end).

#### 3.2.3 Re-dispatch policies per signal type

| Signal | New model | Tools granted | Max retries |
|--------|-----------|---------------|-------------|
| `NEEDS_DEEPER_REASONING` | Upgrade 1 tier (haiku→sonnet, sonnet→opus) | Same as original | 2 |
| `NEEDS_TOOL_ACCESS` | Same tier | + requested tool if safe | 1, then human |
| `NEEDS_MORE_CONTEXT` | Same tier (larger context window) or upgrade | Same | 1 |
| `NEEDS_DOMAIN_EXPERT` | Route by domain (see table below) | Domain-specific | 1, then human |

Domain routing for `NEEDS_DOMAIN_EXPERT`:

| Domain hint in signal | Routed skill |
|-----------------------|--------------|
| `security` | Launch with security-reviewer skill |
| `database` | Launch with db-schema skill (if exists) or opus with DB context |
| `frontend` | Launch with frontend skill or sonnet with frontend context |
| `infrastructure` | Escalate to human immediately (infra changes are HALT triggers) |

#### 3.2.4 Escalation tracking in Engram

Every re-dispatch is logged:

```python
mem_save(
    title: "Escalation: {task_slug} — {signal.type}",
    type: "decision",
    topic_key: "escalation/{agent_id}",
    content: {original_model, new_model, signal, context_summary, retry_count}
)
```

This enables the error-pattern-detector to identify recurring capability ceilings per
task type and update routing rules proactively.

---

### Phase 3: Progressive Escalation Chain + Budget Integration

**Goal**: Make escalation cost-aware. Start with the cheapest capable model, escalate
only when needed, track total escalation cost against budget.

#### 3.3.1 Upgrade chain in `model_router.py`

Add `_upgrade_model()` symmetric to the existing `_downgrade_model()`:

```python
UPGRADE_CHAIN: Dict[str, Optional[str]] = {
    "haiku": "sonnet",
    "claude-haiku-3.5": "claude-sonnet-4",
    "sonnet": "opus",
    "claude-sonnet-4": "claude-opus-4-6",
    "opus": None,           # already at ceiling
    "claude-opus-4-6": None,
}
```

`select_model()` gains an `allow_upgrade: bool = False` parameter. When the orchestrator
re-dispatches, it calls `select_model(task, allow_upgrade=True)` with the escalation
signal to get the upgraded model.

#### 3.3.2 Progressive chain protocol

Default first-attempt model selection is unchanged (routing table as-is). The progressive
chain activates only on capability escalation:

```
Attempt 1: routing-table model (cheapest that fits the task type)
    |
    ├── Success → Done
    └── NEEDS_DEEPER_REASONING → _upgrade_model()
            |
            v
Attempt 2: upgraded model + context handoff
    |
    ├── Success → Done
    └── NEEDS_DEEPER_REASONING (second time) → upgrade again if possible
            |
            v
Attempt 3: max tier (opus) + full context handoff
    |
    ├── Success → Done
    └── Any ESCALATION → Escalate to human with full attempt history
```

Max escalation attempts: 3 (matches existing retry limit). Escalation count is tracked
in the same `retry_count` field used by the apply-verify cycle.

#### 3.3.3 Budget integration

`handle_capability_escalation()` checks budget before upgrading:

```python
estimated_upgrade_cost = estimate_cost(new_model, expected_input, expected_output)
if current_spend + estimated_upgrade_cost > daily_alert_usd:
    # Warn but proceed (advisory)
if current_spend + estimated_upgrade_cost > monthly_limit_usd:
    # BLOCK upgrade, escalate to human instead
    return human_escalation_config(signal, reason="budget_ceiling")
```

Budget governance events are logged to `.cognitive-os/metrics/resource-checks.jsonl`
with `action: "escalation_upgrade"` and the cost delta.

#### 3.3.4 Escalation cost reporting

Add escalation cost tracking to session summary:

```
Escalations this session:
  - task-foo: haiku→sonnet (NEEDS_DEEPER_REASONING) — $0.04 overhead
  - task-bar: sonnet→opus (NEEDS_DEEPER_REASONING x2) — $0.18 overhead
  Total escalation overhead: $0.22 (12% of session cost)
```

Agents that consistently trigger escalation for the same task type are flagged for routing
table update via `/model-optimizer`.

---

## 4. Files Affected

### Phase 1 (signal protocol)

| File | Change |
|------|--------|
| `lib/escalation_detector.py` | Add 4 capability signal types; add `_check_capability_ceiling()` method; add `capability_needed`, `context_summary`, `partial_result`, `recommended_action` fields to `EscalationSignal` |
| `lib/agent_bus.py` | Add `publish_escalation()` method; add `cos:agent:{id}:escalation` channel to channel map |
| `templates/agent-preamble.md` | Extend `ESCALATION:` block with new types and decision tree |
| `rules/agent-escalation.md` | Document capability signals, decision tree, and re-dispatch expectations |

### Phase 2 (re-dispatch)

| File | Change |
|------|--------|
| `lib/dispatch_helper.py` | Add `handle_capability_escalation()` function; add context handoff assembly |
| `lib/model_router.py` | Add `_upgrade_model()` function; add `allow_upgrade` param to `select_model()` |

### Phase 3 (progressive chain + budget)

| File | Change |
|------|--------|
| `lib/model_router.py` | Add `UPGRADE_CHAIN` dict; wire into `select_model()` |
| `lib/dispatch_helper.py` | Add budget check in `handle_capability_escalation()` |
| `lib/cost_dashboard.py` | Add escalation cost breakdown to session report format |
| `rules/model-routing.md` | Document progressive escalation chain and upgrade path |
| `rules/resource-governance.md` | Add escalation budget check policy |

### New files

| File | Purpose |
|------|---------|
| `tests/unit/test_capability_escalation.py` | Unit tests for new signal types, detection logic, and upgrade chain |

---

## 5. Effort Estimate

| Phase | Complexity | Model | Sessions |
|-------|------------|-------|----------|
| Phase 1: Signal protocol | Small | sonnet | 1 |
| Phase 2: Orchestrator re-dispatch | Medium | sonnet | 1.5 |
| Phase 3: Progressive chain + budget | Medium | sonnet | 1 |
| Tests | Small | sonnet | 0.5 |
| **Total** | | | **~4 sessions** |

---

## 6. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `lib/escalation_detector.py` | Exists | Phase 1 extends it in-place |
| `lib/agent_bus.py` | Exists | Phase 1 adds one channel |
| `lib/model_router.py` | Exists | Phase 2+3 add upgrade chain |
| `lib/dispatch_helper.py` | Exists | Phase 2 adds re-dispatch function |
| Valkey agent bus | Optional | Falls back to file-based signaling (existing pattern) |
| Budget tracking | Exists | Phase 3 reads existing `resource-checks.jsonl` format |

No new infrastructure required. All phases build on existing components.

---

## 7. Success Metrics

### Functional

- [ ] `EscalationDetector.check_should_escalate()` returns all four new capability signal
  types when triggered
- [ ] `AgentBus.publish_escalation()` publishes to `cos:agent:{id}:escalation` channel
  (or file fallback)
- [ ] `handle_capability_escalation()` produces a valid `AgentLaunchConfig` for each
  signal type
- [ ] `_upgrade_model("haiku")` returns `"sonnet"`; `_upgrade_model("opus")` returns `None`
- [ ] All unit tests in `tests/unit/test_capability_escalation.py` pass

### Behavioral

- [ ] A haiku agent that emits `NEEDS_DEEPER_REASONING` is re-dispatched to sonnet with
  context handoff (verifiable in escalation Engram entries)
- [ ] A sonnet agent escalating twice reaches opus on attempt 3
- [ ] Escalation over budget ceiling routes to human instead of upgrading
- [ ] Session summary reports escalation overhead cost separately

### Quality

- [ ] No regressions in existing `EscalationDetector` tests
- [ ] Existing `ESCALATION:` block format backward-compatible (new fields are optional)
- [ ] `lib/model_router.py` `UPGRADE_CHAIN` is strict inverse of `DOWNGRADE_CHAIN`
  (roundtrip: `_upgrade_model(_downgrade_model(m)) == m` for all non-boundary tiers)

---

## 8. Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Context handoff adds noise instead of signal — re-dispatched agent confused by prior partial work | MEDIUM | MEDIUM | Cap context_summary at 500 tokens; structured format separates facts from speculation |
| Escalation loops — re-dispatched agent also escalates, creating infinite chain | LOW | HIGH | `retry_count` cap at 3; after 3 escalations always route to human, never auto-retry |
| Budget overrun from aggressive escalation | LOW | MEDIUM | Budget gate in `handle_capability_escalation()` blocks upgrade when monthly > limit |
| `NEEDS_DOMAIN_EXPERT` with `infrastructure` domain causes silent drop if human not available | LOW | MEDIUM | Emit a queued task in `active-tasks.json` rather than silently discarding |
| Adding 4 new signal types breaks orchestrators that pattern-match on exact ESCALATION Type values | LOW | LOW | New types are additive; old types (`loop_detected` etc.) unchanged |
| Upgrade chain routes to opus for tasks that are fundamentally unanswerable — wasting tokens | MEDIUM | MEDIUM | `NEEDS_DEEPER_REASONING` requires 2 prior retry failures before triggering upgrade; one-shot tasks cannot auto-escalate |

---

## 9. Definition of Done

- [ ] `EscalationSignal` dataclass has `capability_needed`, `context_summary`, `partial_result`,
  `recommended_action` fields (all optional, backward-compatible)
- [ ] Four new signal type constants defined and documented
- [ ] `_check_capability_ceiling()` implemented and covered by unit tests
- [ ] `AgentBus` has `publish_escalation()` with Valkey + file fallback
- [ ] `handle_capability_escalation()` in `dispatch_helper.py` handles all four signal types
- [ ] `_upgrade_model()` is the strict inverse of `_downgrade_model()` for non-boundary tiers
- [ ] Progressive chain (haiku → sonnet → opus) terminates after 3 attempts maximum
- [ ] Budget gate blocks upgrade when `monthly_limit_usd` would be exceeded
- [ ] `templates/agent-preamble.md` documents all new signal types and the decision tree
- [ ] `rules/agent-escalation.md` updated with capability signals and re-dispatch policy
- [ ] `tests/unit/test_capability_escalation.py` covers: signal detection, upgrade chain,
  budget gate, context handoff assembly, human escalation fallback
- [ ] All existing tests pass (no regressions)
