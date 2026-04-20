<!-- SCOPE: both -->
---
name: persistent-agent
description: >
  Create persistent agents that maintain their own state across sessions.
  Generates a skill directory with identity profile, event log, and
  auto-fixation checklist for continuous learning.
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-27
license: MIT
metadata:
  author: luum
audience: project
---

## Purpose

Create agents that accumulate knowledge and maintain state across sessions.
Each persistent agent gets its own skill directory with a profile document
(identity + learnings) and an append-only event log. Adapted from the Sprut
Agent Kit agent-builder pattern.

## Invocation

`/create-persistent-agent <name> [--domain <domain>]`

Arguments:
- `<name>` — kebab-case identifier for the agent (e.g., `code-style-enforcer`)
- `--domain <domain>` — optional specialization domain (e.g., `typescript`, `security`, `documentation`)

## What to Do

### Step 1: Validate Inputs

1. Parse `<name>` and `--domain` from arguments.
2. Ensure `<name>` is kebab-case (lowercase, alphanumeric, hyphens only).
3. Check that `skills/{name}/` does not already exist. If it does, ask the
   user whether to overwrite or abort.

### Step 2: Create Directory Structure

Create the following tree:

```
skills/{name}/
├── SKILL.md           # Agent instructions (generated below)
└── data/
    ├── profile.md     # Agent identity + accumulated knowledge
    └── events/
        └── log.md     # Interaction log (append-only)
```

### Step 3: Generate SKILL.md

Create `skills/{name}/SKILL.md` with the following content (fill in
placeholders from arguments):

```yaml
---
name: {name}
description: >
  Persistent agent specialized in {domain or "general assistance"}.
  Maintains state across sessions via profile and event log.
version: 1.0.0
user-invocable: true
auto-generated: true
last-updated: {today ISO date}
license: MIT
metadata:
  author: luum
  persistent: true
  domain: {domain or "general"}
---
```

The SKILL.md body should include:

1. **Purpose**: One paragraph describing the agent's role in its domain.
2. **Invocation**: `/{name}` or `/{name} <query>`.
3. **State Management**: Instructions to read `data/profile.md` at the start
   of every invocation and append to `data/events/log.md` at the end.
4. **Auto-Fixation Checklist** (see Step 5).
5. **Profile Update Rules**: When and how to update `data/profile.md`.

### Step 4: Generate Initial Profile

Create `skills/{name}/data/profile.md`:

```markdown
# Agent Profile: {name}

## Identity

- **Name**: {name}
- **Domain**: {domain or "general"}
- **Created**: {today ISO date}
- **Version**: 1.0.0

## Knowledge Base

_No knowledge accumulated yet. This section grows as the agent processes
interactions and discovers patterns._

## Patterns

_No patterns detected yet. Recurring observations will be recorded here._

## Preferences

_No preferences established yet. User corrections and feedback shape this
section over time._

## Known Limitations

_No limitations documented yet. Edge cases and failure modes are logged here._
```

### Step 5: Generate Initial Event Log

Create `skills/{name}/data/events/log.md`:

```markdown
# Event Log: {name}

> Append-only log. Each entry records an interaction, correction, discovery,
> or error. Never delete entries — they form the agent's learning history.

---

## {today ISO date} — Agent Created

- **Event**: initialization
- **Details**: Agent `{name}` created with domain `{domain or "general"}`
- **Outcome**: Profile and event log initialized
```

### Step 6: Auto-Fixation Checklist

Every persistent agent MUST run this checklist after each interaction. Include
it in the generated SKILL.md:

```markdown
## Auto-Fixation Checklist (mandatory after each interaction)

After completing any task, the agent MUST evaluate these four questions:

1. **Did this interaction produce new knowledge?**
   - If YES: Update `data/profile.md` — add to Knowledge Base section
   - Examples: new API behavior discovered, codebase convention learned,
     tool limitation found

2. **Did the user correct me?**
   - If YES: Log the correction in `data/events/log.md` with:
     - What was wrong
     - What the correct answer/approach is
     - Root cause of the error
   - Also update `data/profile.md` Preferences section if the correction
     reveals a user preference

3. **Did I discover a pattern?**
   - If YES: Add to `data/profile.md` Patterns section
   - Examples: recurring code style, repeated user request pattern,
     common error type in this codebase

4. **Did I make an error?**
   - If YES: Log in `data/events/log.md` with:
     - Error description
     - Root cause analysis
     - How to avoid it in the future
   - Update `data/profile.md` Known Limitations if the error reveals
     a systematic weakness
```

### Step 7: Register in Engram

Save the agent creation to Engram for cross-session discovery:

```
mem_save(
  title: "Created persistent agent: {name}",
  type: "decision",
  scope: "project",
  topic_key: "agent/{name}/sidecar",
  content: "**Agent**: {name}\n**Domain**: {domain}\n**Created**: {date}\n**Location**: skills/{name}/\n**State**: data/profile.md + data/events/log.md"
)
```

### Step 8: Report to User

Output a summary:

```
Persistent agent `{name}` created.

Files:
  skills/{name}/SKILL.md        — Agent instructions
  skills/{name}/data/profile.md — Identity + knowledge (grows over time)
  skills/{name}/data/events/log.md — Interaction history (append-only)

Invoke with: /{name}

The agent will read its profile at the start of each invocation and run the
auto-fixation checklist after each interaction to accumulate knowledge.
```

## Profile Update Rules

The generated agent MUST follow these rules when updating `data/profile.md`:

1. **Append, don't overwrite**: Add new entries to the appropriate section.
   Never remove existing entries unless they are explicitly superseded.
2. **Date every entry**: Prefix knowledge items with `[YYYY-MM-DD]`.
3. **Keep it concise**: Each entry should be 1-3 lines. Link to event log
   entries for full context.
4. **Merge duplicates**: If a new discovery confirms an existing pattern,
   update the existing entry instead of adding a duplicate.
5. **Cap size**: If a section exceeds 50 entries, summarize the oldest 25
   into a single consolidated entry.

## Event Log Format

Each event log entry follows this format:

```markdown
## {ISO date} — {short title}

- **Event**: {type: interaction | correction | discovery | error | update}
- **Details**: {what happened}
- **Outcome**: {result or lesson learned}
- **Profile updated**: {yes/no — which section}
```
