---
adr: 295
title: 'Agent Reflection Loop Primitive: Bounded Iterative Critique with Min/Max Floors'
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: [ADR-290]
superseded_by: null
implementation_files:
  - lib/agent_reflection.py
tier: maintainer
tags:
  - agents
  - reflection
  - runtime
classification_basis: leaf primitive that implements bounded iterative reflection with no caller coupling; deliberately scoped to the primitive only — runtime wiring is reserved for ADR-296 (follow-up)
verification:
  level: strong
  commands:
    - python3 -m pytest tests/unit/test_agent_reflection.py -q
  proves:
    - reflection_loop_respects_min_and_max
    - reflection_exits_early_on_yes_after_min_reflect
    - llm_call_none_raises_at_construction_time
---

# ADR-295 — Agent Reflection Loop Primitive

## Status

Accepted

**Date:** 2026-05-13
**Owner:** orchestrator
**Tier:** maintainer
**Authors:** orchestrator
**Supersedes:** ADR-290 (Pattern 5 split out of the original five-pattern bundle)
**Related:** ADR-292, ADR-293, ADR-294 (peer splits of ADR-290); ADR-296 (reserved — runtime wiring follow-up)

---

## Context

luum-cognitive-os has no reflection primitive today. Agents produce one response per call with no built-in critique step. The result is that any caller wanting iterative reflection rolls its own loop with ad-hoc termination conditions.

This is a feature gain, not a bug fix. It is split out of ADR-290 because it shares no caller, no test surface, and no domain with the other four patterns.

---

## Decision

Introduce `lib/agent_reflection.py` containing:

- `AgentReflector(config: ReflectionConfig)` — bounded iterative reflection loop.
- `ReflectionConfig` — carries `llm_call: Callable[[str], tuple[str, Literal["yes","no"]]]`, `min_reflect: int >= 1`, `max_reflect: int >= min_reflect`.
- `ReflectionResult` — one entry per iteration with the reflection text, the verdict, and a 1-indexed iteration number.
- `reflect(response: str) -> list[ReflectionResult]` — returns the full trajectory.

### Termination contract

1. The loop exits **early** on `"yes"` once `min_reflect` has been reached.
2. The loop exits **unconditionally** at `max_reflect`.
3. `llm_call=None` raises `ValueError` at construction time, not at first `reflect()` call.

### Test approach

- `"yes"` on iteration 1 with `min_reflect=1` exits after one iteration.
- `"no"`, `"no"`, `"yes"` exits after three iterations when `min_reflect=1`.
- `max_reflect=2` with always-`"no"` stops at two iterations.
- `min_reflect=2` with `"yes"` on iteration 1 continues through iteration 2 because the floor has not been reached.

---

## Scope — primitive only

This ADR delivers the **primitive only**. Wiring `AgentReflector` into `lib/agent_runner.py` (or any other caller) is **explicitly out of scope** and is reserved for ADR-296.

ADR-290 left this wiring as "deferred." That language is what this split repairs: "deferred" is open-ended, "reserved for ADR-296" is bounded. The follow-up ADR number is reserved at the time of this writing; no other ADR may take 296.

### Why the wiring is not in this ADR

- Wiring is a **policy decision**, not a primitive: it has to answer *when* the agent reflects (always? on low-confidence outputs? on specific tool calls?), *who* drives the critic (same model? a cheaper model? a separate prompt template?), and *what* the budget is. None of those questions has a primitive answer; all of them belong in a runtime-policy ADR.
- Shipping wiring with the primitive would entangle a reusable leaf with a policy that the team has not yet agreed on. The leaf is useful even if the policy never lands, because callers can compose it directly.

---

## Operational Guide

- Callers that want iterative reflection compose `AgentReflector(ReflectionConfig(llm_call=..., min_reflect=..., max_reflect=...))` around their existing LLM call.
- Callers that want a single-pass behavior do nothing.
- `agent_runner.py` does **not** call this primitive until ADR-296 lands.

---

## Consequences

### Positive

- First reflection primitive in the codebase, available for any caller to compose.
- Termination contract is precise: `min_reflect` is a floor, `max_reflect` is a ceiling, `"yes"` is honored only above the floor.
- No coupling to `agent_runner`, no coupling to a specific LLM provider.

### Negative

- The primitive is unused by the core runtime until ADR-296 wires it in. Adoption depends on the follow-up ADR landing.

### Risks

- `llm_call` is opaque to the primitive. If it raises, the exception propagates and the trajectory list is lost. By design — the caller decides retry policy.
- A naive caller that sets `max_reflect` very high and uses an expensive `llm_call` can spend significantly more tokens per response. The primitive does not enforce a cost ceiling; ADR-296 will.

---

## Alternatives Rejected

1. **Wire reflection directly into `agent_runner` in this ADR.** Rejected because runtime policy for when to reflect, which model to critique with, and what the cost budget is, is not yet decided. Bundling those decisions with the primitive would foreclose them prematurely. ADR-296 is reserved for that decision.
2. **Make `"yes"` an immediate exit regardless of `min_reflect`.** Rejected because the floor is the whole point of the loop: a caller asking for `min_reflect=2` wants at least two passes, even if the first pass self-reports satisfaction.
3. **Return only the final reflection, not the trajectory.** Rejected because callers benchmarking reflection quality need to see the per-iteration verdicts to tune `min_reflect`/`max_reflect` empirically.

---

## Verification

```bash
python3 -m pytest tests/unit/test_agent_reflection.py -q
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

These checks prove that the reflection loop respects `min_reflect` and `max_reflect`, that `"yes"` exits early only after the floor is reached, that `llm_call=None` raises at construction time, and that the ADR satisfies the post-ADR-067 documentation contract.
