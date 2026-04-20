<!-- SCOPE: both -->
# Split-and-Resume Pattern

## Purpose

Sub-agents sometimes encounter ambiguity mid-task that they cannot resolve independently. Rather than making incorrect assumptions (which waste tokens and produce wrong results), agents can signal "I need clarification" and the orchestrator handles resolution.

This is different from the clarification-gate (which blocks BEFORE launch). Split-and-resume operates DURING execution, when the agent discovers ambiguity while working.

## How It Works

### Agent Signals Clarification Needed

When a sub-agent encounters ambiguity that could lead to incorrect assumptions, it outputs:

```
NEEDS_CLARIFICATION:
1. What database engine should be used for the new service?
2. Should the API follow REST or GraphQL conventions?
```

The marker `NEEDS_CLARIFICATION:` followed by numbered questions triggers the split-and-resume flow.

### Orchestrator Resolution Flow

```
Agent returns NEEDS_CLARIFICATION:
    |
    v
clarification-interceptor.sh (PostToolUse) detects marker
    |
    v
Orchestrator extracts question(s)
    |
    v
Step 1: Search Engram for answers
    |
    ├── Found → inject answers, re-launch agent
    └── Not found
         |
         v
Step 2: Ask the USER the question(s)
    |
    v
Save user's answer to Engram (for future auto-resolution)
    |
    v
Step 3: Re-launch agent with CLARIFICATION ANSWERS: section
```

### Re-Launch Prompt Augmentation

The original agent prompt is NOT replaced. A new section is appended:

```
CLARIFICATION ANSWERS:
1. Q: What database engine should be used for the new service?
   A: PostgreSQL 16 — this is the standard for all new services.
2. Q: Should the API follow REST or GraphQL conventions?
   A: REST with JSON — we use REST for all backend services.
```

This preserves the full original context while adding the missing information.

## Limits

### Max Clarification Rounds: 2

A single agent launch can trigger at most 2 clarification rounds. If the agent returns `NEEDS_CLARIFICATION:` a third time, the orchestrator MUST:

1. Stop the clarification loop
2. Escalate to the human with the full question list
3. Report: "Agent has requested clarification 3 times. This task may be too ambiguous for autonomous execution."

### Why 2 Rounds?

- Round 1: Agent discovers primary ambiguity while working
- Round 2: Agent discovers secondary ambiguity after primary is resolved
- Round 3+: Task is fundamentally unclear; throwing more clarifications at it wastes tokens

## Engram Integration

### Saving Answers

When the user provides a clarification answer, save it to Engram for future auto-resolution:

```
mem_save(
  title: "Clarification: {short question summary}",
  type: "decision",
  scope: "project",
  topic_key: "clarification/{question-slug}",
  content: "**Question**: {full question}\n**Answer**: {user's answer}\n**Context**: {what task triggered this}"
)
```

### Auto-Resolution

Before asking the user, the orchestrator searches Engram:

```
mem_search(query: "{question keywords}", project: "{project}")
```

If a matching clarification is found with high relevance, the orchestrator auto-answers without bothering the user. This means the same question is only asked ONCE across all sessions.

## Metrics

All clarification events are logged to `.cognitive-os/metrics/clarifications.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "agent": "agent description (first 100 chars)",
  "round": 1,
  "questions": ["question 1", "question 2"],
  "resolution": "engram|user|escalation",
  "answers_found_in_engram": 0
}
```

## Hook

The `clarification-interceptor.sh` PostToolUse hook on Agent detects the `NEEDS_CLARIFICATION:` marker and outputs:

```
ORCHESTRATOR ACTION REQUIRED: Agent needs clarification.
Round: {N}/2
Questions:
  1. {question}
  2. {question}
```

The orchestrator reads this output and handles the resolution flow.

## Agent Instructions

Agents are instructed via the agent-preamble template:

> If you encounter ambiguity that could lead to incorrect assumptions, output `NEEDS_CLARIFICATION:` followed by your specific questions, one per line. The orchestrator will get answers and re-launch you with the answers injected. Do NOT guess — asking is cheaper than re-doing.

## Integration with Other Rules

| Rule | Integration |
|------|-------------|
| `clarification-gate` | Gate blocks BEFORE launch (vague prompts). Split-and-resume operates DURING execution. Complementary, not overlapping. |
| `trust-score` | Agents that ask for clarification instead of guessing should receive HIGHER trust scores (self-awareness component). |
| `acceptance-criteria` | Clarification answers may refine acceptance criteria mid-task. |
| `closed-loop-prompts` | Clarification rounds count toward the overall retry budget. If 2 clarification rounds + 3 auto-refine retries = 5 total agent launches for one task. |
| `cost-tracking` | Each re-launch adds cost. The 2-round limit prevents runaway spend. |
| `fault-tolerance` | Clarification state is tracked in metrics. If the session crashes mid-clarification, the orchestrator can detect incomplete rounds on resume. |

## Contextual Trigger

This rule is loaded when: agent clarification, NEEDS_CLARIFICATION, ambiguity during execution, split and resume.
