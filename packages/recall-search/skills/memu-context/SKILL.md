<!-- SCOPE: both -->
---
name: memu-context
description: Query memU proactive memory for relevant context before starting work
trigger: what do I know about, context for, remember, prior context, memu, proactive context
model: haiku
audience: project
---

# memU Context Loader

## Purpose
Query memU's 3-layer memory to proactively load relevant context before starting a task. memU predicts what context you'll need based on the task description.

## Protocol

1. Check memU availability: `curl -s http://localhost:8765/health`
2. If available, query memU with the current task/topic:
   - `GET /api/items?category=cognitive-os/*&query={task_description}`
3. memU returns relevant items organized by category:
   - cognitive-os/errors — past error patterns related to this area
   - cognitive-os/repairs — what fixes worked before
   - cognitive-os/decisions — architectural decisions
   - cognitive-os/discoveries — non-obvious findings
4. Also query Engram for cross-reference: `mem_search(query: task_keywords)`
5. Combine both sources and present a context summary

## Output
- **From memU**: Proactive context (errors, repairs, decisions related to current task)
- **From Engram**: Structured observations (what/why/where/learned)
- **Combined**: Unified context brief for the agent

## When memU is not running
Fall back to Engram-only context (existing behavior).
