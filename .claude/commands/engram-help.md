---
description: Load full engram memory protocol (save/search/session lifecycle)
---

# Engram Persistent Memory Protocol

Full protocol for `mem_save`, `mem_search`, `mem_context`, `mem_session_summary`, `mem_get_observation`.

## PROACTIVE SAVE TRIGGERS

Call `mem_save` IMMEDIATELY after:
- Architecture/design decisions
- Conventions established
- Workflow changes
- Library choices with tradeoffs
- Bug fixes (include root cause)
- Features with non-obvious approach
- Config/environment changes
- Codebase discoveries, gotchas, edge cases
- Patterns established
- User preferences learned

**Self-check after EVERY task**: "Did I decide, fix, discover, or establish something? → `mem_save` NOW."

## SAVE FORMAT

- **title**: short verb+what, searchable (e.g. "JWT auth middleware", "Fixed FTS5 special chars")
- **type**: `decision` | `architecture` | `bugfix` | `pattern` | `config` | `discovery` | `learning`
- **scope**: `project` (default) | `personal`
- **topic_key**: stable key for evolving topics (enables upsert via `mem_update`)
- **content**: structured — use `**What**`, `**Why**`, `**Where**`, `**Learned**`

**Topic rules**: different topics MUST NOT share keys. Same topic evolving → same topic_key (upsert). Unsure → `mem_suggest_topic_key` first. Known ID → `mem_update`.

## WHEN TO SEARCH

On recall requests ("remember", "recall", "what did we do", "recordar", "acordate"):
1. `mem_context` first (recent observations)
2. `mem_search` if not found
3. `mem_get_observation <id>` for full content (search results are truncated to 300 chars)

**Search proactively when**:
- Starting work that might have been done before
- User mentions an unknown topic
- User's FIRST message references the project

## SESSION CLOSE (MANDATORY)

Before ending session: `mem_session_summary` with
- Goal
- Instructions (user preferences)
- Discoveries
- Accomplished
- Next Steps
- Relevant Files

**NOT optional.**

## AFTER COMPACTION

1. IMMEDIATELY `mem_session_summary` (persists pre-compaction work)
2. `mem_context` to recover additional context
3. ONLY THEN continue working

## ANTI-PATTERNS

- ❌ Waiting for user to ask before saving
- ❌ Saving ephemeral task state (use TodoWrite instead)
- ❌ Different topics sharing `topic_key`
- ❌ Skipping session_summary at close
