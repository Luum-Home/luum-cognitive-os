<!-- SCOPE: both -->
---
name: session-backlog
description: Inventory all pending work across plans, engram, tasks, todos, audits, and git. Classify by priority and produce a structured backlog document for future sessions.
user-invocable: true
version: 1.0.0
last-updated: 2026-04-10
audience: both
tags: [session, planning, backlog, inventory]
summary_line: "Inventory all pending work across plans, engram, tasks, todos, audits, and git."

---

# Session Backlog — Pending Work Inventory

Scan all sources of pending work, classify by priority, and produce a structured backlog document ready for future sessions.

## Instructions

### Step 1: Determine Project Root and Date

```bash
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TODAY=$(date -u +"%Y-%m-%d")
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"
```

### Step 2: Scan Source A — Plan Files

Read all files under `.cognitive-os/plans/**/*.md` (features, bugs, chores, migrations, evaluations).

For each plan file found:
1. Read its content
2. Extract: plan name (from filename or `# Title`), phase markers (`Phase N:`), task checkboxes (`- [ ]` = pending, `- [x]` = done), and any explicit `Status:`, `Pending`, or `TODO` labels
3. Classify the plan as: **done** (all checkboxes checked, or "Status: Completed"), **in-progress** (mixed checked/unchecked), or **pending** (no checkboxes checked)
4. For in-progress and pending plans, extract the list of uncompleted tasks

If `.cognitive-os/plans/` does not exist, note "No plan files found" and continue.

### Step 3: Scan Source B — Engram Queued Items

Run these searches:
```
mem_search(query: "queued pending next steps")
mem_search(query: "deferred future session backlog")
mem_search(query: "next session TODO remaining work")
```

For each observation returned:
- If the title or content contains "queued", "deferred", "pending", "next steps", "TODO", "future session", or "remaining": extract the actionable item(s)
- Note the observation title and topic_key as the source

Deduplicate items that appear in multiple search results.

### Step 4: Scan Source C — Active Tasks File

Read `.cognitive-os/tasks/active-tasks.json`. If absent, skip this step.

Extract all tasks where `status` is `"in_progress"`, `"pending"`, `"failed"`, or `"queued"`. For each:
- Record: id, description, status, launchedAt (if set)
- Classify as "resume immediately" (in_progress/failed) or "queued" (pending/queued)

Also read `.cognitive-os/tasks/dispatch-queue.json` if it exists. Extract queued agent launches (id, description, model, priority, enqueued_at).

### Step 5: Scan Source D — Session TODOs

Search engram for session summaries with pending next steps:
```
mem_search(query: "session summary next steps")
mem_search(query: "session/backlog")
```

For each session summary found, extract the "Next Steps" section. Collect all items not marked as completed.

### Step 6: Scan Source E — Audit Results with Unimplemented Recommendations

Search engram for audit and verification results:
```
mem_search(query: "audit recommendations unimplemented")
mem_search(query: "sdd verify report CONCERN BLOCKER")
mem_search(query: "skill-atomicity docs-to-skills component-scope")
mem_search(query: "verify-report failed recommendations")
```

For each result found that contains findings, extract:
- The recommendation text (BLOCKER/CONCERN/SUGGESTION items)
- Whether each has been addressed (look for follow-up engram observations about the same topic)
- Mark as "pending" only recommendations with no evidence of resolution

### Step 7: Scan Source F — Git State

Run these commands:
```bash
git -C "$PROJECT_DIR" status --porcelain 2>/dev/null
git -C "$PROJECT_DIR" stash list 2>/dev/null
git -C "$PROJECT_DIR" branch --no-merged HEAD 2>/dev/null | grep -v 'main\|master' | head -10
```

Collect:
- Uncommitted files (modified, untracked)
- Stash entries (especially those named `cos-*` from crash recovery)
- Branches with unmerged work (potential feature branches)

### Step 7b: Scan Source G — User Request Queue

Read the user request queue for this session:
```bash
cat "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/user-requests.jsonl" 2>/dev/null
```

Or use the lib module:
```python
from lib.request_queue import get_pending_requests, format_pending_summary
pending = get_pending_requests(session_dir=f".cognitive-os/sessions/{session_id}")
print(format_pending_summary(session_dir=f".cognitive-os/sessions/{session_id}"))
```

Collect all requests with `status: "pending"` — these are user messages that arrived mid-session and were not yet resolved. They are the HIGHEST priority items because the user explicitly asked for them.

### Step 8: Classify and Prioritize All Items

Group all collected items into four priority tiers:

**Priority 1 — In-Progress (resume immediately)**
Items that were actively being worked on: tasks with status `in_progress` or `failed`, plans marked in-progress with recent activity, stash entries from crash recovery.

**Priority 2 — Ready to Start (dependencies met)**
Items where all prerequisites are satisfied: pending plan phases where prior phases are complete, queued agent launches, engram items explicitly marked "ready" or "next".

**Priority 3 — Planned (needs prerequisites)**
Items with defined scope but blocked by other work: later phases of in-progress plans, recommendations whose prerequisite fixes are not yet done.

**Priority 4 — Backlog (no urgency)**
Everything else: deferred items, suggestions, future-session notes without urgency markers.

Estimate effort for each item using this scale:
- `< 30min` — trivial (typo, config, single file)
- `1 session` — small (1-3 files, clear scope)
- `2-3 sessions` — medium (multi-file, new feature)
- `> 3 sessions` — large (multi-service, complex)

### Step 9: Build Plans Status Summary

For each plan file scanned in Step 2:

| Plan | Progress | Next Phase | Est. Remaining |
|------|----------|------------|----------------|
| {filename} | {X/Y tasks done} | {next pending phase or "Complete"} | {effort estimate} |

### Step 10: Determine Recommendations for Next Session

Based on the prioritized backlog:
1. **Start with**: the single highest-priority incomplete task (Priority 1 if any, else Priority 2)
2. **Quick wins**: up to 3 items estimated at `< 30min`
3. **Can parallelize**: items with no dependencies on each other (suitable for multi-agent dispatch)

### Step 11: Write Backlog Document

Write the backlog to `.cognitive-os/sessions/{SESSION_ID}/backlog.md` (create directories as needed).

Use this exact format:

```markdown
# Session Backlog — {TODAY}

> Generated by /session-backlog. Sources scanned: plans, engram, active-tasks, dispatch-queue, session TODOs, audit results, git state.

## Priority 1: In-Progress (resume immediately)

| Task | Source | Context | Est. Effort |
|------|--------|---------|-------------|
| {description} | {plan/engram/tasks} | {what's needed to continue} | {estimate} |

_(empty if none)_

## Priority 2: Ready to Start (dependencies met)

| Task | Source | Blocked by | Est. Effort |
|------|--------|-----------|-------------|

_(empty if none)_

## Priority 3: Planned (needs prerequisites)

| Task | Source | Prerequisites | Est. Effort |
|------|--------|--------------|-------------|

_(empty if none)_

## Priority 4: Backlog (no urgency)

| Task | Source | Notes | Est. Effort |
|------|--------|-------|-------------|

_(empty if none)_

## Plans Status Summary

| Plan | Progress | Next Phase | Est. Remaining |
|------|----------|------------|----------------|

## Recommendations for Next Session

1. **Start with**: {highest priority incomplete task}
2. **Quick wins**: {up to 3 tasks < 30min}
3. **Can parallelize**: {independent tasks for multi-agent dispatch}

---
_Backlog generated: {TIMESTAMP} | Items: {TOTAL_COUNT} | Sources: {SOURCES_WITH_RESULTS}_
```

If a priority section is empty, write `_(none found)_` instead of an empty table.

### Step 12: Save to Engram

Save the backlog to engram:

```
mem_save(
  title: "Session Backlog — {TODAY}",
  type: "discovery",
  scope: "project",
  topic_key: "session/backlog/{TODAY}",
  content: "{full backlog markdown}"
)
```

Also upsert the "latest" backlog for easy retrieval next session:

```
mem_save(
  title: "Session Backlog — latest",
  type: "discovery",
  scope: "project",
  topic_key: "session/backlog/latest",
  content: "{full backlog markdown}"
)
```

### Step 13: Report to User

Output a concise summary:

```
SESSION BACKLOG COMPLETE
========================
Total items: {N}
  Priority 1 (resume): {N1}
  Priority 2 (ready):  {N2}
  Priority 3 (planned): {N3}
  Priority 4 (backlog): {N4}

Top priority for next session: {description of P1 or P2 item}
Quick wins available: {N quick-win items}

Backlog written to: .cognitive-os/sessions/{SESSION_ID}/backlog.md
Saved to engram: session/backlog/{TODAY}
```

## Edge Cases

- **No pending work found**: Report "Backlog is empty — all tracked work appears complete." and write an empty backlog document.
- **Engram unavailable**: Skip Steps 3, 5, 6, and 12. Note "Engram unavailable — engram sources skipped." in the document header.
- **`.cognitive-os/plans/` absent**: Skip Step 2, note in document.
- **Active tasks file absent**: Skip Step 4, note in document.
- **Git not available**: Skip Step 7, note in document.
- **Large number of items (> 50)**: Limit each priority table to 10 items and append a count: "_and N more items not shown_".
