<!-- SCOPE: both -->
<!-- TIER: 1 -->
# Response Compression — Orchestrator Output Discipline

## Rule (Always Active)

The orchestrator MUST minimize its own token output. Every token spent on orchestrator prose is a token NOT spent on agent work.

## Response Budgets by Type

| Response Type | Max Lines | Max Chars | When |
|---|---|---|---|
| Agent completion acknowledgment | 3 | 200 | "WS2 done — 39 tests, committed" |
| Status update | 5 | 400 | Current progress summary |
| Error/failure report | 10 | 800 | What failed + what to do |
| Architecture decision | 15 | 1200 | When user asks for analysis |
| Risk/trade-off analysis | 10 | 800 | Tables preferred over prose |
| Queue/plan presentation | 20 | 1500 | Tables with columns, not paragraphs |

## Formatting Rules

1. **Tables over prose** — If data has >3 items, use a table
2. **No redundant confirmations** — "Done" not "I have successfully completed the task"
3. **Numbers over adjectives** — "39 tests, 67s" not "many tests passed quickly"
4. **No explaining what you're about to do** — just do it
5. **No re-explaining what an agent did** — the result speaks for itself
6. **Inline code for paths** — `lib/foo.py` not "the foo module in the lib directory"

## Anti-Patterns (Prohibited)

- "I'm going to..." → just do it
- "Let me..." → just do it
- "Great question!" → answer the question
- "Here's what happened:" → show what happened
- "I've successfully..." → state the result
- Repeating the user's question back
- Explaining obvious next steps that are already in the todo list

## Integration

This rule applies to the ORCHESTRATOR only, not to sub-agents (they have their own quality rules in `agent-quality.md`).

## Contextual Trigger

- When work relates to Response Compression — Orchestrator Output Discipline.
