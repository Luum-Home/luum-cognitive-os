---
adr: 38
title: 'Preamble v2: Industry-Aligned Contract'
status: proposed
implementation_status: planned
date: '2026-04-20'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: explicit prose status migration for previously prose-only ADR
---

# ADR-038 — Preamble v2: Industry-Aligned Contract

> Originally drafted in `.cognitive-os/pending-tasks/adr-038-preamble-v2-industry-aligned.md`; canonical location is `docs/adrs/`.

## Status

Proposed

Close the 8 gaps identified in orchestrator research (2026-04-20, engram topic `research/orchestrator-prompt-composition-survey`).

## Gaps addressed (from industry comparison)
1. Typed input variable contract (no schema for fields sub-agent receives)
2. Token/context budget explícito (only `max 50 tool calls`, no `max_tokens` or layers)
3. Typed output schema (TRUST_REPORT is text convention, not Pydantic/JSON)
4. Iteration cap (reasoning cycles, separate from tool-call cap)
5. Escalation routing spec (text-only, no typed handoff like AutoGen)
6. Planning template separado (smolagents-unique, enables pre-computation)
7. Retry diversity protocol (each retry must use different approach)
8. Memory scope declaration (SEARCH_PERMISSION binary, no tiers)

## Rollout waves

### Wave 1 (~3h, sonnet) — quick wins
- #4 `max_reasoning_cycles` field
- #7 retry-approach hashing + enforcement
- #8 memory tiers: `public | project | personal | none`

### Wave 2 (~4h, sonnet) — medium
- #1 `input_schema: {field: type}` in preamble
- #2 4-layer context budget (static|turn|user|cache) per ADK model

### Wave 3 (~1 session, opus) — breaking
- #3 Pydantic `TrustReport` schema, validate on completion, reject malformed
- #5 Typed handoff: `{handoff: {to, context, reason}}`

### Wave 4 (~2h, optional)
- #6 Separate planning template (smolagents pattern)

## Effort
~2-3 sessions total.

## Acceptance per wave
Each wave has its own AC; full v2 preamble when all 4 merged.

## Dependencies
- Wave 3 touches ADR-033 harness_adapter base schema (breaking)
- Wave 4 optional — only if precomputation benefit justifies complexity

---

## Wave 2 — Implemented (2026-04-30)

Closed Gap #1 (typed input schema) and Gap #2 (4-layer context budget).

### Gap #1 — Typed input variable contract (`INPUT SCHEMA:`)

**Problem**: Sub-agents had no machine-readable schema for the fields they receive.
Peer frameworks (Semantic Kernel, LlamaIndex) declare typed `input_variables[]`.

**Solution**: `templates/agent-preamble.md` now contains an `INPUT SCHEMA:` block
(lines added after the CONTEXT BUDGET block) that:
- Documents the canonical fields (`task_description`, `acceptance_criteria`,
  `blast_radius`, `working_dir`) with types and required/optional markers.
- States the validation rule: missing `required` fields → `ESCALATION:` and stop.
- Allows per-launch custom fields declared by the orchestrator.

No library changes required for Wave 2; enforcement is convention-based until
Wave 3 ships Pydantic validation.

### Gap #2 — 4-layer context budget (`CONTEXT BUDGET:`)

**Problem**: Only `MAX 50 tool calls` existed. Google ADK uses 4 layers:
static / turn / user / cache.

**Solution**:
- `cognitive-os.yaml` — new top-level `context_budget:` block with four integer keys:
  `static_max_tokens: 4000`, `turn_max_tokens: 8000`,
  `user_max_tokens: 12000`, `cache_max_tokens: 32000`.
- `templates/agent-preamble.md` — new `CONTEXT BUDGET:` block surfaces these
  values to sub-agents and instructs them to summarise + save to Engram when
  context grows large.

Enforcement (Pydantic, hard stop) is **out of scope** — deferred to Wave 3.

### Verification

```
grep -c "INPUT SCHEMA" templates/agent-preamble.md   # >= 1
grep -c "CONTEXT BUDGET" templates/agent-preamble.md  # >= 1
grep -c "context_budget" cognitive-os.yaml            # >= 1
pytest tests/integration/test_preamble_v2_wave2.py -v # 4+ pass
pytest tests/integration/test_preamble_v2_wave1.py -v # all pass (no regression)
```

### Files changed
- `templates/agent-preamble.md` — INPUT SCHEMA block + CONTEXT BUDGET block
- `cognitive-os.yaml` — `context_budget:` section (before `sessions:`)
- `docs/adrs/ADR-038-preamble-v2-industry-aligned.md` — this section
- `tests/integration/test_preamble_v2_wave2.py` — new test file (4 tests)
