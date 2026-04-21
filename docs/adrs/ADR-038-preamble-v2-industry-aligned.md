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
