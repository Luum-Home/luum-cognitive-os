---

adr: 244
title: Trust Report Claim-Validator Must Enforce, Not Advise
status: accepted
implementation_status: implemented
classification_basis: 'claim enforcer, blocking hook behavior, rule update, and behavior tests satisfy the ADR enforcement scope'
date: 2026-05-08
supersedes: []
superseded_by: null
extends: [ADR-105, ADR-238]
implementation_files:
  - hooks/claim-validator.sh
  - scripts/orchestrator_claim_gate.py
  - rules/trust-score.md
  - tests/behavior/test_claim_enforcer.py
tier: maintainer
tags: [trust, agent-quality, verification-gates, postmortem-2026-05-08]
---
# ADR-244: Trust Report Claim-Validator Must Enforce, Not Advise

## Status

Accepted — Slice A implemented. `scripts/claim_enforcer.py` enforces structured `verification:` evidence for high-stakes claims, `hooks/claim-validator.sh` blocks failed verification, and behavior tests cover pass/fail/manual/no-op paths. Drafted during the 2026-05-08 pre-public readiness session after
multiple agent completions reported "fixed" or "tests pass" while the
referenced commands immediately contradicted the claim. Requires operator
review before implementation.

## Context

The trust-report system (`rules/trust-score.md`,
`hooks/claim-validator.sh`, `scripts/orchestrator_claim_gate.py`) requires
agents to declare verifiable evidence with their completions. The
validator is currently advisory: it scores the claim, surfaces concerns,
and lets the orchestrator accept the agent's `completed` status either
way.

That model fails the simplest stress test. During the 2026-05-08 session,
a bug-fix agent reported `Bug #4 fixed, 4/4 tests pass` and returned a
`completed` status. A re-run of the cited test command seconds later
showed the test was still red. Several other agents in the same session
returned analogous "completed" claims with cited evidence the test suite
contradicted at the next tick. The advisory validator scored these and
moved on; the orchestrator accepted them and moved on.

The anti-pattern is **scoring without enforcing**. A trust report whose
worst outcome is a lower score does not prevent regressions; it merely
documents them.

## Decision

Promote the claim-validator from advisory to blocking for high-stakes
claims. The validator is renamed `claim-enforcer` (with
`hooks/claim-validator.sh` retained as a back-compat shim for one
release).

1. **Trigger patterns.** When an agent's `TRUST_REPORT` body matches any
   of:
   - `\d+\s*(passed|tests pass|tests passing)`
   - `(fix|fixed|closes|resolves)\s+#?\d+`
   - `\b(green|all green|all passing)\b`
   the validator MUST run the cited verification command(s) and require
   exit-0 before the orchestrator accepts a `completed` status.
2. **Verification source.** The agent declares the verification command
   in a structured `verification:` field in the trust report (existing
   schema in `rules/trust-score.md`). If absent, the validator selects
   the test target from the agent's task DAG (e.g. focused tests for the
   files the agent touched).
3. **Failure path.** If the verification command exits non-zero, the
   agent's status is **downgraded** from `completed` to `partial`, the
   failing command and its output are attached as evidence, and the
   orchestrator surfaces the downgrade to the operator. No retry is
   automatic; the orchestrator decides per ADR-238 escalation rules.
4. **Manual opt-out.** Trust reports may declare `verification: manual`
   when the claim is not shell-runnable (UI smoke, design review, doc
   read-through). The enforcer skips the run but records the manual
   opt-out in the audit trail. Repeated `verification: manual` from the
   same agent identity is a quality-signal flag, not a block.

## Operational Guide

### What changes for the operator

Before this ADR, the claim-validator was advisory: it scored agent trust reports
and surfaced concerns, but the orchestrator could accept a `completed` status
regardless of what the score said. A false "tests pass" claim produced a lower
trust score and nothing else.

After this ADR, the behavior changes at the boundary of high-stakes trigger
patterns:

- When an agent's `TRUST_REPORT` matches a trigger (e.g., `4/4 tests pass`,
  `fixes #7`, `all green`), the claim-enforcer (`scripts/claim_enforcer.py`,
  invoked by `hooks/claim-validator.sh`) re-runs the cited verification command
  in a fresh context.
- If that command exits non-zero, the agent's status is **downgraded to
  `partial`** and the failing output is attached as evidence. The orchestrator
  sees a `partial` result — not a `completed` one — and decides what to do per
  ADR-238 escalation rules.
- No automatic retry occurs. The operator or orchestrator decides next steps.

Agents that declare `verification: manual` bypass the execution check but
are flagged in the audit trail. Repeated `verification: manual` from the same
agent identity is a quality-signal flag, not a block.

### What this answers (and what it doesn't)

**Answers:**
- "Can a failing test suite slip through as a `completed` claim?" — No, if the
  agent cited a verification command that matches a trigger pattern.
- "How do I know if enforcement ran?" — Check `agent-audit-trail.jsonl` for
  enforcement decision entries, or inspect the agent's returned status field.
- "What if the verification command is not shell-runnable?" — Declare
  `verification: manual` in the trust report. The enforcer skips execution and
  logs the opt-out.

**Does not answer:**
- Whether the claim would have been correct if the cited command had been run
  inside the agent (the enforcer runs in a fresh context specifically to avoid
  that self-referential failure).
- Whether claims that do not match a trigger pattern are correct. Non-trigger
  claims remain advisory under the existing trust-score rules.

### Daily operational pattern

When a sub-agent returns a trust report:

1. The enforcer auto-runs on trigger-pattern matches via the hook — no manual
   invocation needed.
2. To verify enforcement is working:
   ```bash
   python3 -m pytest tests/behavior/test_claim_enforcer.py -q
   grep -RIn "verification:" rules/trust-score.md
   ```
3. To inspect a specific enforcement decision in the audit trail:
   ```bash
   grep "claim-enforcer" .cognitive-os/logs/agent-audit-trail.jsonl | tail -5
   ```
4. If an agent is repeatedly marked `partial` on legitimate work, check whether
   its verification command is flaky or depends on agent-internal state that is
   not reproducible in a fresh context. The correct fix is to declare
   `verification: manual` with an explanation, not to suppress the gate.

## Alternatives rejected

- **Keep the validator advisory and improve trust-score weighting** —
  rejected because the 2026-05-08 incidents show that scoring is
  decoupled from outcomes. A perfectly-scored claim that the test suite
  contradicts seconds later is the failure mode this ADR addresses.
- **Run the cited command inside the agent before it returns** —
  rejected because the agent is the entity whose claim is being
  validated. Self-verification by the same context that produced the
  claim does not catch the worst class of failure (sycophantic
  completion). The verification must happen in a fresh context.
- **Block all completions on a global test-suite run** — rejected as
  too costly. A focused enforcement on the agent's cited evidence runs
  in seconds; a global run runs in minutes and would create a queue
  that incentivizes operators to disable the gate.
- **Require human review for every claim** — rejected because it
  defeats the purpose of agent autonomy and would not scale to the
  10-15 agent/sprint cadence the responsiveness rules assume.

## Consequences

### Positive

- A regression detected by the agent's own cited evidence cannot reach
  `completed` status.
- Agents have an incentive to cite a verification command they actually
  ran, because the enforcer will run it again in a fresh context.
- The audit trail gains a strong "claim vs. reality" record, useful
  for the agent-KPI rules in `rules/RULES-COMPACT.md`.

### Negative

- Every high-stakes claim incurs the cost of an extra command
  execution. For focused tests this is sub-second; for slow suites it
  is more.
- Agents whose verification commands legitimately rely on
  agent-internal state (rare) will need to mark `verification: manual`
  and accept the audit-trail flag.
- The `claim-validator.sh` back-compat shim is one more deprecation
  surface to remove on the next release.

## Acceptance criteria

1. `hooks/claim-validator.sh` (or its renamed successor) blocks
   completion when a trust-report claim matches a trigger pattern and
   the cited verification exits non-zero.
2. `scripts/orchestrator_claim_gate.py` downgrades the agent's status
   from `completed` to `partial` on enforcer failure, with the failing
   command captured as evidence.
3. `rules/trust-score.md` documents the trigger patterns and the
   `verification: manual` opt-out.
4. `tests/behavior/test_claim_enforcer.py` covers: trigger-match with
   passing verification (allow), trigger-match with failing
   verification (block + downgrade), trigger-match with `manual`
   opt-out (allow + audit flag), no-trigger claim (no-op).
5. Audit trail entries are emitted for every enforcement decision,
   including manual opt-outs.

## Verification

```bash
python3 -m pytest tests/behavior/test_claim_enforcer.py -q
grep -RIn "verification:" rules/trust-score.md
```
