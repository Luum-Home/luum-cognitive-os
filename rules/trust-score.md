<!-- SCOPE: both -->
# Trust Score Protocol

## Purpose

Agents overclaim completion. Humans don't trust "done" because they've been burned before. The Trust Score system forces agents to provide evidence, admit uncertainty, and tell the human exactly what to verify.

**Core principle**: admitting doubt builds more trust than claiming perfection.

## Trust Report (Mandatory)

Every agent completion MUST include a Trust Report with a **machine-parseable header** on the first line, followed by the human-readable body:

```
TRUST_REPORT: SCORE=75 STATUS=MEDIUM EVIDENCE=3 UNCERTAINTIES=2
---
Score: 75/100

EVIDENCE PROVIDED:
  [check] [what was verified with proof]
  [warn] [what was partially verified]
  [fail] [what was NOT verified]

WHAT I'M CONFIDENT ABOUT:
  - [list with reasoning]

WHAT I'M UNSURE ABOUT:
  - [honest list of uncertainties]

WHAT THE HUMAN SHOULD VERIFY:
  - [specific actions the human should take]
```

### Machine-Parseable Header

The first line uses a deterministic key=value format for reliable extraction by hooks and scripts:

| Field | Description | Values |
|-------|-------------|--------|
| `SCORE` | Numeric trust score | 0-100 |
| `STATUS` | Score band label | HIGH (90+), MEDIUM (70-89), LOW (50-69), CRITICAL (<50) |
| `EVIDENCE` | Count of [check]/[warn]/[fail] markers | integer |
| `UNCERTAINTIES` | Count of items in "WHAT I'M UNSURE ABOUT" | integer |

The `---` separator divides the header from the human-readable body. Parsing library: `lib/trust_report_parser.py`.

### Legacy Format Support

The parser also accepts the old format without the header line (a `TRUST REPORT:` block with `Score: XX/100`). New agents MUST use the header format. Legacy reports are parsed on a best-effort basis.

## Trust Score Calculation

```
TRUST = (
  verification_evidence * 0.40    # Did agent run commands and show output?
  + acceptance_criteria * 0.30    # Were measurable criteria defined and met?
  + self_awareness * 0.20         # Did agent admit uncertainties honestly?
  + proportionality * 0.10        # Is the solution proportional to the problem?
)
```

### Scoring each component (0-100):

**Verification Evidence (40%)**:
- 100: All claims backed by command output (compile, test, grep)
- 75: Most claims backed by evidence, some by code reading
- 50: Mix of command output and "I verified by reading"
- 25: Mostly "I read the code and it looks correct"
- 0: No verification performed

**Acceptance Criteria (30%)**:
- 100: All numbered acceptance criteria defined AND verified with commands
- 75: Criteria defined, most verified
- 50: Criteria defined but verification is incomplete
- 25: Vague criteria, partial verification
- 0: No criteria defined or checked

**Self-Awareness (20%)**:
- 100: Honest uncertainty list with specific items, edge cases noted
- 75: Some uncertainties acknowledged with reasoning
- 50: Generic "there might be edge cases" disclaimer
- 25: Minimal acknowledgment of limits
- 0: "Everything is perfect, 100% confident" (RED FLAG)

**Proportionality (10%)**:
- 100: Solution matches problem scope exactly
- 75: Slightly over/under-engineered but reasonable
- 50: Noticeable mismatch between problem and solution
- 25: Significant over/under-engineering
- 0: Solution is wildly disproportionate to the problem

## Evidence Types (by weight)

| Type | Weight | Example |
|------|--------|---------|
| Command output shown (compile, test, grep) | HIGH | "Ran `go test ./...` - 42 passed, 0 failed" |
| File created/modified with diff shown | MEDIUM | "Created `handler.go` with these changes: ..." |
| "I verified by reading the code" | LOW | "I read the function and it handles the edge case" |
| No verification at all | ZERO | "I believe this should work" |

## Trust Thresholds

| Range | Level | Human Action |
|-------|-------|--------------|
| 90-100 | High confidence | Minimal human review needed |
| 70-89 | Medium confidence | Spot-check recommended |
| 50-69 | Low confidence | Thorough human review required |
| 0-49 | Very low | Human should re-do or heavily verify |

## Mandatory Self-Doubt

Agents MUST list at least 1 thing they're unsure about. "I'm 100% confident" is a RED FLAG -- it means the agent isn't thinking critically.

Examples of good self-doubt:
- "I didn't test with edge case X because I couldn't reproduce the conditions"
- "The regex handles the cases I tested but may miss Unicode edge cases"
- "I verified the happy path but didn't test error recovery"
- "This compiles and passes tests but I haven't verified behavior under load"

## Integration with Existing Quality System

Trust Score complements but does not replace:
- **Definition of Done** (`definition-of-done.md`): DoD gates WHAT must be done. Trust Score measures HOW WELL it was verified.
- **Acceptance Criteria** (`acceptance-criteria.md`): AC defines the checks. Trust Score reports which checks were actually run.
- **Auto-Verify** (`auto-verify.sh`): Auto-verify runs commands. Trust Score includes their output as evidence.
- **Verification Before Completion** (`verification-before-completion`): VBC is the process. Trust Score is the report.

## Metrics

Trust scores are logged to `.cognitive-os/metrics/trust-scores.jsonl` with:
```json
{
  "timestamp": "ISO-8601",
  "agent": "agent-name",
  "task": "task-description",
  "score": 75,
  "components": {
    "verification_evidence": 80,
    "acceptance_criteria": 70,
    "self_awareness": 85,
    "proportionality": 90
  },
  "uncertainties_count": 2,
  "evidence_types": {"command": 3, "diff": 2, "reading": 1, "none": 0}
}
```
