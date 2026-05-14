# ADR-311: Primitive Closure Ratchets and Subagent Budget Enforcement

- **Status**: Accepted
- **Date**: 2026-05-14
- **Owner**: Cognitive OS maintainers
- **Scope**: governance, hooks, runtime enforcement, routing audit debt

## Context

Recent gap reviews exposed the same failure mode in multiple forms: a primitive
can be documented, projected, or audited without closing the loop that proves the
runtime behavior still exists.

Examples:

1. Hook-enforced rules can drift from the actual harness projections.
2. Mandatory skill invocation can be present as a router suggestion but needs a
   blocking hook proof.
3. Language-routing regex debt can remain visible forever unless it has a
   ratcheted baseline and migration policy.
4. Subagents can be instructed to stop at 50 tool calls without a runtime budget
   guard that forces an `ESCALATION:` handoff.
5. Governance authority files can be edited while a session claims closure unless
   the closure path explicitly checks or declares dirty authority state.

The OS already has many individual primitives. The missing primitive is a small
closure layer that checks whether high-risk primitives are actually wired,
covered by a falsification test, and bounded by a ratchet.

## Decision

Add an ADR-311 closure layer with two first implementation slices:

1. **`subagent-budget-enforcer` hook**
   - Runs on `PostToolUse` for all tools in Claude Code projection.
   - Detects subagent sessions from wrapper-provided session kind, agent ids, or
     subagent transcript paths.
   - Counts tool calls per `(session_id, agent_id)`.
   - Warns at the configured budget, default `50`.
   - Blocks after the budget unless the subagent emits `ESCALATION:` or an
     audited bypass is present.
   - Logs observations to `.cognitive-os/metrics/subagent-budget-enforcer.jsonl`.

2. **`primitive-closure-ratchet` audit**
   - Reads `manifests/primitive-closure-ratchet.yaml`.
   - Blocks if language-dependence actionable medium+ findings exceed the current baseline (`0`).
   - Blocks if required high-risk runtime proof tests are missing.
   - Blocks if required hook projections are missing from canonical or generated
     harness surfaces.
   - Optionally warns on dirty governance authority paths via `--check-dirty`.

This ADR does not attempt to solve all closure gaps at once. It establishes the
ratchet shape and implements the highest-risk runtime gap: subagents exceeding
50 tool calls without escalation.

## Consequences

### Positive

- The "50 tool calls" subagent budget becomes runtime-enforced instead of only
  a preamble instruction.
- The language-dependence audit has a zero-actionable medium+ ratchet; future work cannot add un-semantic natural-language regex debt unnoticed.
- Runtime proof tests become first-class evidence for mandatory governance
  primitives.
- Projection drift is caught by a small, fast audit before broad lanes.

### Negative / Tradeoffs

- A subagent doing legitimate long-running investigation must either emit a
  structured `ESCALATION:` handoff or use an audited bypass.
- The language audit still preserves low-severity compatibility inventory for legacy regex_with_intents; ADR-311 prevents new actionable medium/high debt but does not delete compatibility fallbacks without benchmark evidence.
- Codex cannot currently enforce subagent lifecycle parity because it does not
  emit `SubagentStart` and only emits Bash `PreToolUse`/`PostToolUse` events.

## Alternatives Considered

### Keep enforcement in preambles only

Rejected. Preambles are useful guidance but do not create a machine-checkable
contract.

### Add one giant governance hook

Rejected. A monolithic hook would increase hot-path cost and create a new drift
surface. ADR-311 keeps the runtime hook narrow and puts cross-primitive checks in
a CLI ratchet.

### Immediately migrate all language regex patterns

Rejected for this slice. The existing semantic fallback makes runtime behavior
safer, but the audit debt needs a baseline first. Migration or severity downgrades
can proceed under the ratchet.

## Implementation

- `hooks/subagent-budget-enforcer.sh`
- `scripts/primitive_closure_ratchet.py`
- `scripts/cos-primitive-closure-ratchet`
- `manifests/primitive-closure-ratchet.yaml`
- `tests/contracts/test_subagent_budget_enforcer.py`
- `tests/contracts/test_primitive_closure_ratchet.py`

## Acceptance Criteria

1. `bash -n hooks/subagent-budget-enforcer.sh` exits `0`.
2. A simulated subagent with `COS_SUBAGENT_TOOL_CALL_BUDGET=2` blocks on the
   third tool call with exit code `2` and a message containing `ESCALATION:`.
3. `scripts/cos-primitive-closure-ratchet --json` exits `0` on the current
   baseline.
4. A manifest baseline lower than the current actionable language audit count fails the ratchet.
5. Claude projection includes `hooks/subagent-budget-enforcer.sh`.

## Follow-up

- Continue reducing low-severity `regex_with_intents` compatibility inventory when benchmark evidence proves semantic routing parity.
- Extend the closure manifest with more high-risk primitives after the first
  slice is stable.
- Add release-lane wiring for `scripts/cos-primitive-closure-ratchet` once the
  baseline is accepted by maintainers.
