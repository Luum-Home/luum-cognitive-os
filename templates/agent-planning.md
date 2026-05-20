<!-- SCOPE: os-only -->

# Agent Planning Template (ADR-038 Wave 4)

Use this template when the task is explicitly planning/design/research-first, or when
the preamble's risk classification reaches the research-first threshold.

## Output contract

Return a plan only. Do not modify repository files unless the caller explicitly asks
for a durable planning artifact.

```
PLAN:
  goal: [one sentence]
  assumptions:
    - [assumption or none]
  acceptance_criteria:
    - [verifiable criterion]
  slices:
    - name: [small implementation slice]
      files: [expected files]
      validation: [commands or checks]
  risks:
    - [risk and mitigation]
  recommended_first_slice: [one slice name]

TRUST_REPORT: SCORE=<0-100> STATUS=<HIGH|MEDIUM|LOW|CRITICAL> EVIDENCE=<N> UNCERTAINTIES=<N>
---
WHAT I VERIFIED: <bullets>
UNSURE ABOUT: <at least 1 item>
HUMAN SHOULD CHECK: <bullets>
```

## Constraints

- Keep plans executable: every slice needs a validation check.
- Prefer 1-session slices over broad roadmaps.
- Escalate if a required decision is missing rather than inventing product policy.
- If implementation is safe and under one small slice, say so and recommend direct execution.
