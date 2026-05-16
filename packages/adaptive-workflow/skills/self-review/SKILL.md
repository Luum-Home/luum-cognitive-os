---
name: self-review
description: 'Lightweight 4-question post-implementation checklist for non-SDD work.
  Quick self-assessment before claiming a task is done.

  '
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-27
license: MIT
metadata:
  author: luum
  pattern: superclaude-self-review
audience: project
summary_line: Lightweight 4-question post-implementation checklist for non-SDD work.
platforms:
- claude-code
prerequisites: []
routing_intents:
- review my implementation before marking it done
- run a self review checklist on this change
- check whether this task is actually complete
- verify my work before I claim completion
- do a lightweight post implementation review
triggers:
- self-review
- /self-review
- Lightweight 4-question post-implementation checklist for non-SDD work
---
<!-- SCOPE: both -->
## Purpose

A fast, lightweight alternative to the full SDD verify phase. Use this after
completing non-SDD tasks (bug fixes, small features, config changes) to catch
common oversights before reporting "done."

## Invocation

`/self-review`

## What to Do

Answer each of the 4 questions honestly. For each, produce a verdict:
PASS, FLAG, or CONCERN.

### Question 1: Did I run the tests?

Verify that relevant tests were executed and passed.

```
Check:
├── Which test suite(s) did you run? (name them specifically)
├── Did ALL tests pass? (report exact counts: N passed, M failed)
├── If no tests exist for this code, did you create any?
└── Did you run lint/build as well?
```

| Verdict | Condition |
|---------|-----------|
| PASS | Tests run, all pass, build and lint clean |
| FLAG | Tests run but some skipped or no tests exist for new code |
| CONCERN | Tests not run, or tests failing |

### Question 2: Did I handle edge cases?

Check that the implementation handles non-happy-path scenarios.

```
Check:
├── Empty inputs (nil, null, undefined, empty string, empty array)
├── Error conditions (network failure, invalid data, timeout)
├── Boundary values (zero, negative, max int, very long strings)
└── Concurrent access (if applicable)
```

| Verdict | Condition |
|---------|-----------|
| PASS | Edge cases identified and handled with tests or guards |
| FLAG | Some edge cases identified but not all handled |
| CONCERN | No edge case consideration at all |

### Question 3: Does this match what was asked?

Re-read the original request and compare against what was implemented.

```
Check:
├── Re-read the original user request or task description
├── Compare implemented scope against requested scope
├── Check for scope creep (did you add unrequested features?)
└── Check for scope shortfall (did you miss requested items?)
```

| Verdict | Condition |
|---------|-----------|
| PASS | Implementation matches the request exactly |
| FLAG | Minor deviations with justification |
| CONCERN | Significant mismatch between request and implementation |

### Question 4: What might I have missed?

Mandatory self-doubt. List at least 1 honest uncertainty.

```
Check:
├── What assumptions did you make?
├── What did you NOT test?
├── What could break in production that works in dev?
└── What would a code reviewer likely question?
```

| Verdict | Condition |
|---------|-----------|
| PASS | Uncertainties listed with mitigations or acceptance rationale |
| FLAG | Uncertainties listed but no mitigation identified |
| CONCERN | "Nothing, it's perfect" (this IS the concern — overconfidence) |

## Output Format

```markdown
## Self-Review Checklist

| # | Question | Verdict | Details |
|---|----------|---------|---------|
| 1 | Did I run the tests? | {PASS/FLAG/CONCERN} | {which tests, results} |
| 2 | Did I handle edge cases? | {PASS/FLAG/CONCERN} | {which cases, how handled} |
| 3 | Does this match what was asked? | {PASS/FLAG/CONCERN} | {comparison summary} |
| 4 | What might I have missed? | {PASS/FLAG/CONCERN} | {honest uncertainties} |

### Overall: {PASS / NEEDS ATTENTION / REVIEW REQUIRED}

{1-2 sentence summary}
```

### Overall Verdict Logic

- **PASS**: All 4 questions are PASS
- **NEEDS ATTENTION**: 1-2 questions are FLAG, none are CONCERN
- **REVIEW REQUIRED**: Any question is CONCERN, or 3+ are FLAG

## Rules

- Question 4 MUST have at least 1 uncertainty listed — "nothing" is always CONCERN
- This is a self-assessment, not a substitute for code review on large changes
- For SDD work, use `sdd-verify` instead (it is more thorough)
- Do NOT inflate verdicts — honest FLAGs are better than false PASSes
- Return a structured envelope with: `status`, `executive_summary`, `artifacts`, `next_recommended`, and `risks`

## Integration

| System | Relationship |
|--------|-------------|
| `trust-score` | Self-review feeds into the self-awareness component of trust score |
| `sdd-verify` | Self-review is the lightweight alternative for non-SDD work |
| `dod-check` | Self-review complements DoD by adding subjective assessment |
| `agent-quality` | Self-review is a quality gate for small/medium tasks |
