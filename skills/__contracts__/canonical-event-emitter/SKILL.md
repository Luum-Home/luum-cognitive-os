<!-- SCOPE: os-only -->
<!-- TIER: 0 -->
---
name: canonical-event-emitter
description: >
  Reference skill for harness-agnostic canonical event parity testing. Emits a
  deterministic sequence of canonical lifecycle events; used by
  tests/integration/test_harness_agnostic_skill_run.py to verify each harness
  adapter produces byte-identical events.
version: "1.0.0"
user-invocable: false
auto-generated: false
audience: os
args: []
model: not-applicable
summary_line: Reference contract skill — emits deterministic canonical event sequence for harness parity verification.
platforms: ["claude-code", "codex", "bare_cli"]
prerequisites: []
tags: [contracts, verification, harness-agnostic, adr-064]
---

# Canonical Event Emitter — Reference Contract Skill

## Status

**Active contract.** This skill is the ground truth for ADR-064 harness-agnostic verification. It is not user-invocable; it is invoked by the integration test suite.

## Purpose

Any harness adapter that claims ADR-064 compliance MUST be able to execute this skill and produce a canonical event stream structurally identical to the Claude Code reference stream (modulo legitimately harness-specific fields). This skill defines that contract: the event sequence below is what "a valid skill execution" looks like across all harnesses.

This is NOT a real skill that performs useful work. It is a deterministic probe designed to produce predictable, verifiable output that can be byte-compared across harness boundaries.

## Canonical Event Sequence

When this skill is executed, the following events MUST be emitted in order:

| # | Event Type | Key Fields |
|---|-----------|------------|
| 1 | `session_start` | `harness`, `session_id`, `started_at`, `cwd` |
| 2 | `user_prompt_submit` | `prompt_summary="canonical-event-emitter: emit reference sequence"`, `harness`, `session_id`, `submitted_at` |
| 3 | `tool_use_start` | `tool_name="bash"`, `command="echo canonical-event-emitter-marker-2026"`, `harness`, `session_id` |
| 4 | `tool_use_end` | `tool_name="bash"`, `exit_status="success"`, `output="canonical-event-emitter-marker-2026"`, `harness`, `session_id` |
| 5 | `session_end` | `exit_status="success"`, `harness`, `session_id`, `ended_at` |

### Literal prompt

The `user_prompt_submit` event MUST carry the literal prompt:

```
canonical-event-emitter: emit reference sequence
```

### Literal bash command

The `tool_use_start` / `tool_use_end` events MUST carry the literal command:

```
echo canonical-event-emitter-marker-2026
```

And the output of the command MUST be exactly:

```
canonical-event-emitter-marker-2026
```

(no trailing newline variation — harness normalization is expected to strip it)

## Invariants — What MUST be byte-identical across harnesses

After stripping the allowed-diff fields listed below, the following MUST be structurally identical between any two harness runs:

1. **Event count**: exactly 5 canonical events in sequence (no extras, no gaps).
2. **Event types**: the `event_type` string value at each position in the sequence.
3. **Key set**: the set of keys present in each event dict (excluding allowed-diff fields).
4. **Value types**: for every non-excluded key, the Python type of the value.
5. **`event_type` literal values**: must match the registry in `lib/harness_adapter/base.py`.
6. **Tool name**: `tool_name="bash"` at positions 3 and 4.
7. **Exit status**: `exit_status="success"` at positions 4 and 5.
8. **Output marker**: `output="canonical-event-emitter-marker-2026"` at position 4.

## Allowed-diff Fields — What MAY differ between harnesses

These fields are legitimately harness-specific and are excluded from byte-identity assertions:

```python
ALLOWED_DIFF_FIELDS = {
    "harness",        # "claude_code" vs "codex" — by definition differs
    "session_id",     # harness-assigned, cannot be equal
    "started_at",     # wall-clock; not reproducible
    "ended_at",       # wall-clock
    "submitted_at",   # wall-clock
    "prompt_hash",    # content-derived; may differ by harness hash function
    "prompt_summary", # may be truncated differently per harness
    "version",        # harness version string
    "cwd",            # workspace path
    "source",         # originator field
    "duration_ms",    # harness runtime; not reproducible
}
```

This list is the canonical definition. The integration test in
`tests/integration/test_harness_agnostic_skill_run.py` imports `ALLOWED_DIFF_FIELDS`
conceptually from this contract (the test file holds the live Python constant).

## Known Exceptions — Codex Tool-Coverage Gap

Codex v0.124.0+ fires `PreToolUse`/`PostToolUse` only for the Bash tool
(ADR-064 lines 24–27, ADR-081 §Capability gaps). Since events 3 and 4 in this
contract use Bash, Codex DOES produce `tool_use_start`/`tool_use_end` for this
skill. There is no gap exception for this contract skill — Bash is explicitly
chosen for maximum harness coverage.

If a future version of this skill adds a non-Bash tool call, the Codex adapter
MUST emit `ParseError(reason="codex_tool_coverage_gap")` for those positions,
and the test must explicitly assert the gap marker rather than structural parity.

## Verification

This contract is enforced by two test files:

1. **`tests/integration/test_harness_agnostic_skill_run.py`** — the ADR-064
   acceptance gate. Parameterized over `(claude_code, codex)` harnesses.
   Drives both adapters with representative lifecycle payloads from
   `tests/fixtures/codex-live-session/` and asserts structural byte-identity
   after stripping allowed-diff fields. This is the live gate; 4/4 cases pass
   as of 2026-04-30 (commit `259f766`).

2. **`tests/audit/test_canonical_event_emitter_contract.py`** — behavioral
   contract test. Asserts this file exists at the canonical path, frontmatter
   is parseable with TIER: 0 and SCOPE: os-only, and the documented event
   sequence is consistent with the fixture files in
   `tests/fixtures/codex-live-session/`.

## Canonical Schema Reference

The authoritative `CanonicalEvent` registry and `HarnessAdapter` ABC are defined in:

```
lib/harness_adapter/base.py
```

All event types referenced in the table above correspond to dataclasses
registered in that file. The `event_type` string values are the `event_type`
class attribute on each dataclass.

## Non-Invocability

This skill MUST NOT appear in the user-facing skill catalog or be suggested by
the skill router. The `user-invocable: false` frontmatter flag signals this.
The `skills/__contracts__/` namespace prefix (`__` delimiters) is a structural
signal to catalog generators that these skills are internal verification
artifacts, not user procedures.
