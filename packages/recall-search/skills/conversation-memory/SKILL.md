<!-- SCOPE: both -->
---
name: conversation-memory
description: Search and learn from past Cognitive OS sessions — the system's long-term memory
trigger: what did we do, remember session, past sessions, conversation history, session search, recall
model: sonnet
audience: project
version: "1.0.0"
platforms: ["claude-code"]
prerequisites: []
---

# Conversation Memory

## Purpose
Cognitive OS learns from its own history. This skill searches past sessions, finds relevant context, and surfaces patterns that inform current work.

## Protocol

### 1. Search past sessions
Sources (in priority order):
1. **Engram session summaries** — `mem_search` with keywords from user query
2. **Transcript index** — `metrics/transcripts/transcript-index.jsonl` for session stats
3. **Session learnings** — `metrics/session-learnings.jsonl` for error/success patterns
4. **KPI history** — `metrics/kpi-history.jsonl` for performance trends

### 2. Contextual recall
When user asks about past work:
1. Extract keywords from their question
2. Search Engram with `mem_search(query: keywords)`
3. For matches, get full content with `mem_get_observation(id)`
4. Cross-reference with transcript index for session stats
5. Present findings with dates, what was done, what was learned

### 3. Pattern mining
Proactively analyze session history for:
- **Recurring errors**: same error across 3+ sessions → flag for permanent fix
- **Skill evolution**: which skills improved over time (success rate trend)
- **Cost patterns**: which tasks are expensive, which are cheap
- **Time patterns**: when does the team work, what's most productive
- **Knowledge gaps**: topics searched in Engram with no results

### 4. Self-referential learning
After every significant session, verify:
- Did we solve something that was attempted before? → Link sessions
- Did we make a decision that contradicts a past decision? → Flag for review
- Did we discover something that would have helped in a past session? → Note for future

### 5. Output format

#### Session Recall
| Date | Session | Goal | Key Outcomes | Errors | Skills |
|------|---------|------|-------------|--------|--------|

#### Pattern Report
- **Recurring issues**: [list with frequency]
- **Improving trends**: [metrics getting better]
- **Degrading trends**: [metrics getting worse]
- **Knowledge built**: [decisions, conventions, discoveries count]

## Privacy
- Respects private-mode: sessions marked private are never indexed
- Transcript content is NOT stored (only metadata + Engram summaries)
- Search results come from Engram observations, not raw transcripts
