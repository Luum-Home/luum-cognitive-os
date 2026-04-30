<!-- SCOPE: both -->
<!-- TIER: 2 -->
# Adversarial Review Protocol (BMAD v6 Pattern 1)

## Mandate

Every review MUST produce at least one finding. "Looks good" and "no issues found" are PROHIBITED responses.

## Trigger

This rule applies to:
- `sdd-verify` phase outputs
- `code-reviewer` agent runs
- `/evaluate-plan` skill executions
- Any agent or skill whose purpose is review, evaluation, or verification

## Zero-Findings HALT

If a reviewer produces zero findings, the orchestrator MUST:
1. HALT the review
2. Return this message to the reviewer: `"Review incomplete. You MUST identify at least one concern, suggestion, or question."`
3. Re-launch the reviewer with the halt message appended to the prompt
4. If the reviewer fails to produce findings after 2 retries, escalate to human

## Severity Tiers

Every finding MUST be classified into exactly one tier:

| Tier | Label | Meaning | Action Required |
|------|-------|---------|-----------------|
| S1 | **BLOCKER** | Prevents shipping. Security flaw, data loss risk, architectural violation, broken functionality. | Must fix before proceeding. |
| S2 | **CONCERN** | Likely to cause problems. Performance issue, missing edge case, weak test coverage. | Should fix before proceeding. Requires justification to skip. |
| S3 | **SUGGESTION** | Improvement opportunity. Better naming, cleaner pattern, additional test. | Fix if time allows. Track as tech debt if skipped. |
| S4 | **QUESTION** | Unclear intent or potential misunderstanding. Needs clarification from author or spec. | Must answer before proceeding. |

## Finding Format

Each finding must follow this structure:

```
### [TIER] Short description

**Location**: file path and/or component
**What**: What the issue is
**Why**: Why it matters
**Recommendation**: Suggested fix or action
```

## Review Quality Criteria

A review is considered COMPLETE when:
1. At least one finding is present (mandatory)
2. Every finding has a severity tier assigned
3. Every finding includes location, what, why, and recommendation
4. The reviewer has examined: correctness, security, performance, maintainability, test coverage
5. If no BLOCKERs or CONCERNs exist, at least one SUGGESTION or QUESTION is provided

## Integration with SDD

In `sdd-verify`, the adversarial review is the FIRST check. If the verify phase returns zero findings, the orchestrator treats the verification as FAILED and re-runs it.

## Orchestrator Enforcement

The orchestrator MUST NOT accept a review result that:
- Contains zero findings
- Has findings without severity tiers
- Uses phrases like "looks good", "LGTM", "no issues", "everything is fine"
- Fails to cover at least 3 of the 5 review dimensions (correctness, security, performance, maintainability, tests)

## Multi-Persona Pattern (skills/doc-review-personas)

`/doc-review-personas` implements the multi-persona variant of this rule:
N reviewer lenses (CFO, Tech Lead, Commercial, New Dev, Editor) run in parallel
over the same documentation corpus; findings are consolidated with the severity
tiers defined above. Each persona individually respects the ≥1-finding rule and
emits the machine-parseable `TRUST_REPORT` header from `rules/trust-score.md`.

The consolidator deduplicates findings by `(location, what-prefix)` and keeps
the highest severity when two personas independently flag the same issue. This
is the canonical implementation when the subject under review is docs, not
code — for code-level adversarial review, use `skills/code-review`.
