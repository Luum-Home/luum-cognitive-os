---
name: session-wrapup
description: End-of-session routine — run session-backlog inventory, save to engram, write session summary, and report what was accomplished and what comes next.
user-invocable: true
version: 1.0.0
last-updated: 2026-04-10
audience: both
tags: [session, closing, summary, backlog]
---

# Session Wrapup — End-of-Session Routine

Chain all end-of-session activities: inventory pending work, persist state to engram, and produce a session summary.

## Instructions

### Step 1: Collect Session Context

Before generating any output, gather context about what happened this session:

1. Read `.cognitive-os/tasks/active-tasks.json` — identify tasks completed this session (status `"completed"` with a recent `completedAt`)
2. Check git log for commits made this session:
   ```bash
   git -C "${CLAUDE_PROJECT_DIR:-$(pwd)}" log --oneline --since="8 hours ago" 2>/dev/null | head -20
   ```
3. Search engram for context saved in this session:
   ```
   mem_context()
   ```
   Note any decisions, discoveries, or fixes recorded.
4. Note the current date/time: `TODAY=$(date -u +"%Y-%m-%dT%H:%M:%SZ")`

### Step 2: Run /session-backlog

Execute the full `/session-backlog` skill as defined in `skills/session-backlog/SKILL.md`.

This produces:
- A prioritized backlog document at `.cognitive-os/sessions/{SESSION_ID}/backlog.md`
- Engram saves under `session/backlog/{date}` and `session/backlog/latest`
- A count of pending items by priority

Capture the output: total item count, top priority item description, quick-win count.

### Step 3: Compose Session Summary

Synthesize what happened this session into a structured summary. Fill in each section honestly — if a section has nothing to report, write "None" rather than omitting it.

**Goal**: What was the session trying to accomplish? (infer from tasks, commits, and engram context if the user did not state it explicitly)

**Accomplished**: What was actually completed?
- List commits made (from git log)
- List tasks marked completed in active-tasks.json
- List engram saves that represent decisions or fixes

**Discoveries**: What was learned that should be remembered?
- Non-obvious behaviors, gotchas, patterns established
- Architecture or library decisions made
- Bug root causes found

**Blockers encountered**: What slowed down or stopped progress?
- Failed attempts, rate limits, missing dependencies
- Ambiguities that caused clarification rounds

**Next Steps**: The top 3 items from the backlog (Priority 1 and 2 items).

**Relevant Files**: Files created or significantly modified this session.

### Step 4: Save Session Summary to Engram

Call `mem_session_summary` with the composed summary:

```
mem_session_summary(
  goal: "{session goal}",
  instructions: "{any user preferences or conventions established}",
  discoveries: "{discoveries section}",
  accomplished: "{accomplished section}",
  next_steps: "{next steps — top 3 from backlog}",
  relevant_files: "{comma-separated list of key files}"
)
```

### Step 5: Save Backlog Reference to Engram

Ensure the backlog is cross-linked from the session summary by saving a brief reference:

```
mem_save(
  title: "Session closed — {TODAY date only}",
  type: "discovery",
  scope: "project",
  topic_key: "session/close/{TODAY date only}",
  content: "Session wrapped up. Backlog: {N} items. Top priority: {description}. Backlog at: session/backlog/{TODAY date only}"
)
```

### Step 5b: Update Plan Statuses

For each plan file in `.cognitive-os/plans/features/*.md`:
1. Check if any workstream/phase was completed this session (cross-reference with commits, engram saves, completed tasks)
2. If yes, update the plan file: change status from pending/in-progress to DONE with date
3. This keeps plans as living documents, not static artifacts

Also check the master plan (`self-optimizing-pipeline.md`) specifically:
- For each WS, check if work was done this session
- Update the execution priority table if statuses changed

### Step 5c: Persist Pending User Requests

Read the user request queue:
```python
from lib.request_queue import get_pending_requests, format_pending_summary
pending = get_pending_requests(session_dir=f".cognitive-os/sessions/{SESSION_ID}")
```

If there are pending requests:
1. Include them in the backlog as Priority 1 items
2. Save to engram under `session/pending-requests/{date}` so next session picks them up
3. Report the count to the user: "N user requests were not completed this session"

### Step 6: Report to User

Output the final wrapup report:

```
SESSION WRAPUP COMPLETE
========================
Accomplished this session:
  - {item 1}
  - {item 2}
  - {item 3}

Backlog: {N} items pending
  Priority 1 (resume next): {N1 items}
  Priority 2 (ready):       {N2 items}
  Priority 3 (planned):     {N3 items}
  Priority 4 (backlog):     {N4 items}

Top priority for next session:
  {description of highest-priority item}

Quick wins (< 30min):
  {list up to 3}

Session summary saved to engram.
Backlog saved to: .cognitive-os/sessions/{SESSION_ID}/backlog.md
```

## Integration with Claude Code's native /recap

Claude Code ships a native `/recap` slash command that summarises the
current session for the user. Per ADR-021 (vendor-agnostic state with
provider adapters), this skill remains the **canonical** source of session
state — the adapter at `hooks/_lib/recap_adapter.py` (invoked from
`hooks/recap-sync.sh` on the Stop event) reads the same
`.cognitive-os/sessions/{SESSION_ID}/` artifacts this skill writes (summary,
backlog, metrics) and emits them as `additionalContext` so Claude Code's
native `/recap` UI shows the COS-managed work alongside its native event log.

Sync direction is one-way: this skill writes the canonical state, the
adapter only reads. /recap output never overwrites COS files. Other
providers (Codex/Gemini/Cursor/Windsurf) can ship their own adapters
against the same canonical artifacts.

## When to Use This Skill

- At the end of any work session before closing Claude Code
- After completing a major task or milestone
- When switching context to a different project
- When handing off work to another session or team member

## What This Skill Does NOT Do

- It does not commit or push code (use git commands for that)
- It does not close or terminate the Claude Code session
- It does not modify any source files

## Edge Cases

- **Engram unavailable**: Skip all `mem_save` / `mem_session_summary` calls. Write the backlog document to disk only. Report: "Engram unavailable — session summary not persisted to memory."
- **session-backlog produces no items**: Session wrapup still completes. Summary notes "Backlog is empty."
- **No commits this session**: Note "No commits made this session" in the Accomplished section.
- **No active-tasks.json**: Infer accomplishments from git log and engram context only.
