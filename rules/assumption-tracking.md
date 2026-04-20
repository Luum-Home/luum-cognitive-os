<!-- SCOPE: both -->
# Assumption Tracking

## Purpose

Tracks when agents make assumptions instead of working from verified requirements. High assumption counts indicate the agent is guessing rather than executing from clear specifications. This creates visibility into where requirements were unclear and where agent outputs may need verification.

## How It Works

The `assumption-tracker.sh` PostToolUse hook fires after every Agent tool completion and scans the response text for assumption language.

### Detected Patterns

#### HIGH Confidence (explicit assumption language)

| Pattern | Example |
|---------|---------|
| "I assume" | "I assume the database is PostgreSQL" |
| "I'm assuming" | "I'm assuming you want unit tests" |
| "I'll assume" | "I'll assume the default port is 3000" |
| "assuming that" | "Assuming that auth is handled by middleware" |
| "presumably" | "This is presumably for the admin panel" |
| "without more info" | "Without more info, I'll use REST" |
| "in the absence of" | "In the absence of specs, I chose Redis" |
| "based on context" | "Based on context, I used the repository pattern" |

#### MEDIUM Confidence (hedging/uncertainty language)

| Pattern | Example |
|---------|---------|
| "I think" | "I think this should go in the domain layer" |
| "probably" | "This probably needs a migration" |
| "likely" | "The error is likely a null pointer" |
| "it seems" | "It seems like the API expects JSON" |
| "appears to be" | "The config appears to be YAML-based" |
| "I believe" | "I believe the port is 8080" |
| "my best guess" | "My best guess is a race condition" |
| "if I had to guess" | "If I had to guess, it's a timeout" |

### Thresholds

| Count | Action |
|-------|--------|
| 0-2 | Silent. Logged to metrics only. Normal amount of uncertainty. |
| 3+ | WARNING output. Lists all detected assumptions. Recommends clarifying requirements. |

## Why This Matters

Assumptions are a leading indicator of quality problems:

1. **Unverified requirements**: The agent filled in gaps instead of asking. The filled-in answers may be wrong.
2. **Hidden decisions**: Each assumption is an implicit decision that was never reviewed. These decisions may contradict project conventions.
3. **Compounding risk**: 5 assumptions in one task means 5 points where reality could differ from what the agent guessed.

## Integration with Other Rules

| Rule | Relationship |
|------|-------------|
| Clarification Gate (`clarification-gate`) | Upstream defense. If the clarification gate catches ambiguity, the assumption tracker sees fewer assumptions. |
| Trust Score (`trust-score`) | Assumption count feeds into self-awareness scoring. More acknowledged assumptions = higher self-awareness score. |
| Agent Quality (`agent-quality`) | Assumptions indicate the agent is doing minimum interpretation of ambiguous inputs. |
| Acceptance Criteria (`acceptance-criteria`) | Clear acceptance criteria reduce the need for assumptions. |

## Metrics

Assumptions are logged to `.cognitive-os/metrics/assumptions.jsonl`:
```json
{
  "timestamp": "ISO-8601",
  "assumption_count": 4,
  "agent": "first 100 chars of prompt...",
  "assumptions": "[HIGH] I assume the database is PostgreSQL...\n[MEDIUM] I think this needs a migration..."
}
```

### Analysis Queries

```bash
# Count assumptions per day
cat .cognitive-os/metrics/assumptions.jsonl | jq -s 'group_by(.timestamp[:10]) | map({date: .[0].timestamp[:10], total: (map(.assumption_count) | add)})'

# Find agents with most assumptions
cat .cognitive-os/metrics/assumptions.jsonl | jq -s 'sort_by(-.assumption_count) | .[0:5]'

# Average assumptions per agent completion
cat .cognitive-os/metrics/assumptions.jsonl | jq -s '(map(.assumption_count) | add) / length'
```

## Reducing Assumptions

When assumption counts are consistently high:

1. **Improve prompt quality**: Use `/exhaustive-prompt` to enumerate scope before launching agents
2. **Add acceptance criteria**: Clear criteria reduce ambiguity
3. **Clarify architecture**: Document patterns in `.claude/rules/` so agents don't guess
4. **Use clarification gate**: Ensure the gate catches vague prompts before they reach agents

## Contextual Trigger

This rule is always active. It applies to every agent completion via the PostToolUse hook.
