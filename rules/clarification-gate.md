<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Mandatory Clarification Gate

## Purpose

Prevents agents from launching with vague, ambiguous prompts. Ambiguous prompts let agents interpret scope minimally, producing incomplete results that waste tokens and require re-work. Unlike the completeness-check hook (which is advisory), the clarification gate is a BLOCKING gate for severely ambiguous prompts.

## How It Works

The `clarification-gate.sh` PreToolUse hook fires on every Agent tool use and scores the prompt for ambiguity on a 0-100 scale.

### Scoring

| Signal | Points | Description |
|--------|--------|-------------|
| No file paths | +15 | No `.go`, `.ts`, `.py`, etc. file references or directory paths detected |
| Scope without quantifiers | +20 | Words like "all", "every", "complete" used without counts (e.g., "47 endpoints") |
| Missing tech specification | +15 | Creation/implementation verb without naming the technology or framework |
| Action verbs without targets | +20 | "add auth", "improve performance" without specifying which files or components |
| Unanswered questions | +15 | Prompt contains "which?", "what type?", "where should?" — needs answers first |
| Very short prompt | +20 | Agent prompt under 50 characters — insufficient detail for reliable execution |
| No success criteria | +10 | No acceptance criteria, verification commands, or expected results |

Score is capped at 100.

### Verdicts

| Score | Verdict | Behavior |
|-------|---------|----------|
| 0-29 | PASS | Silent pass-through. Prompt is clear enough. |
| 30-60 | WARN | Advisory warning with suggested clarifications. Agent still launches. |
| 61-100 | BLOCK | Blocks agent launch (exit code 2). Lists specific questions to answer. |

## Examples

### BLOCKED (score > 60)

```
"Add auth to the project"
```
- No file paths (+15)
- No tech specification (+15)
- Action without target (+20)
- No success criteria (+10)
- Score: 60+ -> BLOCKED

Questions generated:
1. Which files or directories should be modified?
2. Which technology or framework should be used?
3. Where exactly should this change be applied?
4. No success/acceptance criteria found. How will completion be verified?

### WARNED (score 30-60)

```
"Add JWT authentication to src/auth/ using Go and the project's HTTP framework"
```
- Has file paths (0)
- Has tech specification (0)
- No success criteria (+10)
- Score: ~25-35 -> WARNING or PASS

### PASSED (score < 30)

```
"Implement CreateOrder use case in internal/orders/application/use_cases/create_order.go using the declared framework.

ACCEPTANCE CRITERIA:
1. `go build ./...` exits 0
2. `go test ./internal/orders/...` exits 0
3. Endpoint POST /api/orders returns 201 with order data"
```
- Has file paths (0)
- Has tech (0)
- Has acceptance criteria (0)
- Score: 0 -> PASS (silent)

## Integration with Other Rules

| Rule | Relationship |
|------|-------------|
| Completeness Check (`completeness-check`) | Complementary. Completeness checks for exhaustiveness (advisory). Clarification gate checks for basic clarity (blocking). |
| Acceptance Criteria (`acceptance-criteria`) | Clarification gate checks for presence of criteria. Acceptance criteria rule defines the format. |
| Agent Quality (`agent-quality`) | Clarification gate is the first line of defense in the quality chain. |
| Closed-Loop Prompts (`closed-loop-prompts`) | Clarification gate ensures prompts have enough detail for the closed-loop to work. |

## Metrics

Events are logged to `.cognitive-os/metrics/clarification-events.jsonl`:
```json
{
  "timestamp": "ISO-8601",
  "score": 65,
  "questions": 4,
  "verdict": "BLOCK",
  "agent": "first 100 chars of prompt..."
}
```

Track the ratio of BLOCK vs WARN vs PASS to measure prompt quality improvement over time.

## Configuration

The clarification gate is always active. To adjust sensitivity, modify the point values in `hooks/clarification-gate.sh`.

## Contextual Trigger

This rule is always active. It applies to every agent launch via the PreToolUse hook.
