---
adr: 293
title: 'Typed Hook Event Contracts: Frozen Dataclasses for Claude Code Hook Payloads'
status: accepted
implementation_status: implemented
date: '2026-05-13'
supersedes: [ADR-290]
superseded_by: null
implementation_files:
  - lib/hook_event_types.py
tier: maintainer
tags:
  - hooks
  - contracts
  - schema
  - reliability
classification_basis: canonical schema module with per-event-type dataclasses, dispatcher, and roundtrip parse tests; existing hooks remain on untyped dicts until the staged migration plan completes
verification:
  level: strong
  commands:
    - python3 -m pytest tests/unit/test_hook_event_types.py -q
  proves:
    - hook_event_payload_parses_to_typed_dataclass
    - missing_required_field_raises_hookpayloaderror
    - unknown_hook_event_name_raises_clear_error
---

# ADR-293 — Typed Hook Event Contracts

## Status

Accepted

**Date:** 2026-05-13
**Owner:** orchestrator
**Tier:** maintainer
**Authors:** orchestrator
**Supersedes:** ADR-290 (Pattern 2 split out of the original five-pattern bundle)
**Related:** ADR-292, ADR-294, ADR-295 (peer splits of ADR-290)

---

## Context

237 hook scripts parse JSON event payloads as ad-hoc dicts with manual key fishing (`payload.get("tool_name")`). There is no central schema describing what fields each hook event carries, no static guarantee that a misspelled field name surfaces at parse time, and no roundtrip contract.

Symptoms observed:

- A typo like `tool_inpiut` returns `None` from `.get()` and the hook proceeds with broken behavior.
- New hook authors copy field-fishing patterns from existing hooks; the implicit schema drifts.
- There is no single place to look up "what fields can a `PreToolUse` payload carry?".

This concern is a contract/schema decision, not a runtime-performance primitive (ADR-292) or a memory schema extension (ADR-294) or an agent runtime feature (ADR-295). It is therefore split into its own ADR.

---

## Decision

Introduce a single canonical schema module `lib/hook_event_types.py` that defines a frozen dataclass per Claude Code hook event type, a `parse_event(payload: dict) -> HookEvent` dispatcher that routes by `hook_event_name`, and a `HookPayloadError` raised at parse time for unknown event names and missing required fields.

Event types covered: `SessionStartEvent`, `PreToolUseEvent`, `PostToolUseEvent`, `StopEvent`, `SubagentStartEvent`.

The module is the **canonical schema only**. Existing hooks are not rewritten in this ADR; the migration is staged (see Migration Plan below).

**Test approach.** Round-trip parse-then-inspect for each event type. Missing-field payload raises `HookPayloadError` with the field name surfaced. Unknown `hook_event_name` raises a clear error.

---

## Operational Guide

- New hooks import `parse_event` and obtain a typed event object: `event = parse_event(json.loads(sys.stdin.read()))`.
- Existing hooks continue to work on untyped dicts until the staged migration reaches them.
- Schema additions are additive: new optional fields land in `lib/hook_event_types.py` first, then hooks adopt them.

---

## Migration Plan (inline — not deferred)

ADR-290 left "237 hooks not migrated" as an open item. This ADR closes that openness with a concrete staged plan rather than deferring to an unnamed follow-up.

| Phase | Scope | Trigger | Exit criterion |
|---|---|---|---|
| Phase A — canonical schema (this ADR) | `lib/hook_event_types.py` + tests | merged with this ADR | `parse_event` is callable and round-trips all five event types |
| Phase B — opportunistic adoption | Any hook newly created or substantively edited MUST adopt `parse_event` | per-PR rule, enforced at review | Every hook touched after this ADR uses `parse_event` |
| Phase C — high-traffic sweep | The 20 most-invoked hooks (by `agent-heartbeat.jsonl` count over a 30-day window) | scheduled batch | Top-20 sweep merged in a single ADR-NNN follow-up batch (the follow-up reuses the schema, does not amend it) |
| Phase D — long tail | Remaining hooks | as touched | One-by-one, no dedicated ADR required because no schema change is involved |

**Explicit boundary.** This ADR does not commit a date for Phase C. The audit at Phase B exit (every new hook uses `parse_event`) is the gate that makes Phase C scheduleable. Until then, the migration is staged, not deferred — every new hook is on the typed schema.

---

## Consequences

### Positive

- A single source of truth for hook payload shape.
- Misspelled field names fail at parse time, not at field-access time.
- New hooks pay zero migration cost — they adopt the schema by default.

### Negative

- Existing 237 hooks remain on untyped dicts until Phase C/D touches them. The schema lives, the legacy callers do not benefit immediately.
- Two patterns will coexist in the codebase during the migration window: typed events for new hooks, untyped dicts for legacy hooks.

### Risks

- A schema change inside `lib/hook_event_types.py` after Phase B has begun could break opportunistic adopters silently. Mitigated by treating the dataclass fields as a stable contract: additions allowed, renames or removals require a follow-up ADR.

---

## Alternatives Rejected

1. **Rewrite all 237 hooks in one sweep.** Rejected because the hook surface is large, stateful, and produces side effects that are hard to unit-test in bulk. The safer migration is to provide the canonical parser now and adopt it opportunistically. The "one big sweep" approach also entangles a schema decision (this ADR) with 237 unrelated behavior changes.
2. **TypedDict instead of frozen dataclass.** Rejected because `TypedDict` only provides static checking; it cannot raise `HookPayloadError` at runtime for missing fields. Hooks run in subprocesses where static checking is not enforced.
3. **JSON schema validation library.** Rejected because the schema is small, the validation logic fits in one module, and adding a dependency for five event types is disproportionate.

---

## Alternatives rejected

- **Leave the behavior as implicit agent instruction only.** Rejected because this ADR records a runtime/authoring contract that needs durable tests or audits rather than conversation-only memory.

## Verification

```bash
python3 -m pytest tests/unit/test_hook_event_types.py -q
python3 -m pytest tests/audit/test_adr_contracts.py -q
```

These checks prove that hook payloads parse into typed dataclasses, missing fields raise `HookPayloadError` with the field name surfaced, unknown event names raise a clear error, and the ADR satisfies the post-ADR-067 documentation contract.
