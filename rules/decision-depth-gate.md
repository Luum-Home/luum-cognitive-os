# Decision Depth Gate

## Purpose

Prevent surface-level "fixes" where an agent resolves a flagged finding by adding
clarifying prose instead of investigating the underlying relationship. Most
commonly triggered when a review flags "inconsistency between two values" and the
agent concludes "they're intentionally different, document why" without asking:
**are the values actually coherent given their relationship?**

## Trigger

This rule fires whenever an agent is about to close a finding whose type is:

- "inconsistency between two values / constants / defaults"
- "duplication / apparent duplication"
- "naming collision"
- "ambiguity between two similar concepts"

Either in an audit report (e.g. Code Reviewer output) or an SDD verify phase.

## Mandatory Gate (before resolution)

The agent MUST answer the following IN WRITING before choosing a resolution:

### Q1 — Relationship

Are the two values **functionally related**? Possible relationships:

- **Predictor**: one predicts/approximates the other (e.g. Phase A classifier → Phase B killer)
- **Bound**: one is a cap/floor on the other (e.g. warn threshold ≤ error threshold)
- **Default**: one is a default that the other overrides
- **Shared denominator**: both are proportions of the same underlying quantity
- **Independent**: no meaningful relationship — they just happen to share context

### Q2 — Coherence

If Q1 is anything other than "Independent", construct a concrete **numerical example**:

- Pick a value the underlying signal might take
- Compute what each constant implies for that value
- Check whether the two implications are coherent

Example (ADR-047 CPU thresholds, before unification):
- Phase A threshold = 1.0%, Phase B threshold = 5.0%
- Underlying signal: CPU = 3.0%
- Phase A implies: session is ACTIVE (3 > 1)
- Phase B implies: session is IDLE (3 < 5) → would be killed
- Coherence: BROKEN. Phase A fails to predict Phase B.

### Q3 — Resolution Menu

Given Q1 and Q2, pick from this menu (in preference order):

1. **Unify values** — if they serve the same purpose, collapse to one
2. **Enforce invariant as code** — write a test/assertion that captures the relationship (`assert value_a >= value_b`)
3. **Rename to disambiguate** — if the values are genuinely independent but collide in naming
4. **Separate concerns** — move one value to a different ADR / module where it belongs
5. **Document with binding rationale** — ONLY if options 1-4 are infeasible. Documentation alone legitimises the status quo without verifying it.

### Q4 — Forbidden shortcuts

The agent MUST NOT:

- Close the finding with only a comment/docstring change when Q2 reveals incoherence
- Write "these are intentionally different" without Q1 + Q2 + a coherence example
- Defer the coherence check to "future work" — that's how bugs accumulate

## Enforcement

This rule is agent-behavioral; no hook enforces it automatically (yet — see
`hooks/surface-fix-detector.sh` in the deferred work). Reviewers (human or
`code-reviewer` agent) should flag PRs that resolve such findings without the
Q1-Q4 trail visible in the commit message or PR description.

## Example: Applying This Rule Catches a Real Bug

The ADR-047 CPU threshold issue (5.0% vs 1.0%) was originally "resolved" by
adding a 5-line clarification note to the ADR explaining the two thresholds
served different purposes. That resolution satisfied the audit finding but:

- Q1 revealed the thresholds were in a PREDICTOR relationship
- Q2 produced a coherence example showing the predictor was broken at CPU=3%
- Q3 led to unification at 5.0% + an invariant test

The surface fix would have shipped a Phase A observation period that
systematically under-measures Phase B false-positive rate. The underlying
cost: user sessions killed that Phase A claimed were never at risk.

## Contextual Trigger

Always active. Applies to any agent running reviews, audits, or verification
phases, and to the orchestrator when it receives and resolves such findings.
