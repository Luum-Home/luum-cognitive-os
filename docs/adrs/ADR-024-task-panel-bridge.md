---
adr: 24
title: Task Panel Bridge — Correlate COS Tasks with Claude Code tool_use_id
status: accepted
implementation_status: partial
date: '2026-04-16'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: implementation evidence plus partial/deferred/future signal
---

# ADR-024: Task Panel Bridge — Correlate COS Tasks with Claude Code tool_use_id

**Date:** 2026-04-16
**Status:** Accepted
**Supersedes:** None
**Related:** ADR-021 (adapter pattern), ADR-022 (prompt-type hooks), ADR-023 (updatedInput)

## Context

The Cognitive OS maintains its own task state in `.cognitive-os/tasks/active-tasks.json` (ADR-008 multi-tool support requires vendor-agnostic state). Claude Code has a native **Task panel** that shows `Agent` tool invocations and their status.

Prior to this ADR, the two were disconnected:
- COS-orchestrated tasks (circuit breaker pauses, rate-limit queue, workload scheduler) were **invisible** in Claude Code's UI
- Agent tool calls appeared in the panel but without COS metadata (task_id, retry count, which skill invoked it)
- The model could see one or the other, not both

ADR-021 proposed the adapter pattern as the general solution. This ADR is the first full bidirectional adapter: Task Panel Bridge.

## Decision

Capture Claude Code's native `tool_use_id` at `PreToolUse` time, store it alongside COS `task_id` in `active-tasks.json`, and expose correlated state back to the model via `hookSpecificOutput.additionalContext`.

### Flow

1. **PreToolUse hook on Agent** (`hooks/agent-prelaunch.sh`):
   - Extract `tool_use_id` from Claude Code's hook input JSON
   - Register task via `hooks/_lib/task_bridge.py register --tool-use-id ... --description ...`
   - Store both `id` (COS) and `toolUseId` (Claude Code) in `active-tasks.json`

2. **PostToolUse hook on Agent** (`hooks/task-bridge-notify.sh`):
   - Mark task completed by `tool_use_id` lookup
   - Emit `hookSpecificOutput.additionalContext` with:
     - In-progress tasks with both IDs (correlated to native panel)
     - In-progress tasks without `toolUseId` (queued, internal orchestration)
     - Rate-limit queue ready-for-drain items
     - Recent failures

3. **Library** (`hooks/_lib/task_bridge.py`):
   - `register`: creates/updates correlation
   - `complete`: marks complete by `tool_use_id`
   - `panel-context`: emits formatted `additionalContext` JSON

### What the model sees

After any `Agent` tool call completes, the model's context includes a markdown block like:

```
## COS Rate-Limit Queue (3 total, 2 ready)
Ready for drain — invoke `/drain-queue` or Task tool:
- `queued-001`: Refactor authentication module
- `queued-002`: Run security audit

## COS In-Progress with native Task panel link (2)
- `toolu_01ab`: Port hooks to Go validators
- `toolu_02cd`: Update documentation

## COS In-Progress (no native link, queued or internal) (1)
- `task-1776313539`: Background cleanup task
```

### What the USER sees

- Native Task panel: unchanged (Claude Code shows Agent invocations as usual)
- COS-internal state: surfaced via the model's explanations when relevant

## Alternatives Considered

### Alt 1: Wrap dispatch through Agent tool directly
- Each COS-launched task would invoke the Agent tool, making it natively visible
- **Rejected**: requires vendor lock-in, ties internal orchestration to Claude Code API
- Would break when running under Codex/Gemini/Cursor/Windsurf

### Alt 2: External dashboard (Datasette / web UI)
- Serve `active-tasks.json` over HTTP on localhost
- **Deferred**: valuable but orthogonal; doesn't solve in-session visibility
- Listed in FROZEN-BACKLOG

### Alt 3: Wait for Anthropic to expose Task panel API
- **Rejected**: no public roadmap, can't plan around it

### Alt 4 (chosen): additionalContext bridge
- Uses existing Claude Code hook API (`hookSpecificOutput`)
- No vendor lock-in (same approach works with Codex/Gemini adapter via ADR-021)
- Correlation via `tool_use_id` is generic — every tool-based coding agent has equivalent

## Consequences

### Positive
- Model has full visibility into COS orchestration state without polling
- Correlation between native panel entries and COS metadata
- Vendor-agnostic: adapter pattern lets us add Codex/Gemini equivalents
- User can debug COS behavior by asking the model "what's queued?" and getting real data
- Rate-limit queue becomes actionable — model sees ready items and can `/drain-queue`

### Negative
- `tool_use_id` correlation relies on Claude Code including it in hook input JSON (verified works)
- `additionalContext` has a 10K char limit — panel-context format is concise
- Model must parse markdown to act on it — not structured tool calls
- One more hook in PostToolUse path (~20-50ms overhead)

### Risks
- If Claude Code changes the `tool_use_id` field name, the bridge breaks
   - Mitigation: ADR-021 provider adapters isolate this to the Claude provider
- If many tasks are queued, output approaches 10K truncation
   - Mitigation: `panel-context` caps lists at top 5

## Implementation

Files added:
- `hooks/_lib/task_bridge.py` — correlation library (register/complete/panel-context)
- `hooks/task-bridge-notify.sh` — PostToolUse hook emitting context
- `tests/unit/test_task_bridge.py` — 10 behavioral tests, all passing

Files modified:
- `hooks/agent-prelaunch.sh` — captures `tool_use_id` into task entry
- `.claude/settings.json` — registers task-bridge-notify.sh

Registered in both `scripts/apply-efficiency-profile.sh` and `scripts/set-security-profile.sh`.

## Verification

Manual tests:
```bash
# Register a task
python3 hooks/_lib/task_bridge.py register \
  --tool-use-id "toolu_demo" \
  --description "Test task"

# See what the model would see
python3 hooks/_lib/task_bridge.py panel-context

# Complete it
python3 hooks/_lib/task_bridge.py complete \
  --tool-use-id "toolu_demo" \
  --summary "done"
```

Automated tests:
```bash
source .venv/bin/activate
python -m pytest tests/unit/test_task_bridge.py -v
# 10 passed in 0.68s
```

## References

- ADR-021: Vendor-Agnostic State with Provider Adapters
- `hooks/_lib/task_panel_adapter.py`: earlier (simpler) version, superseded by this
- Claude Code hooks docs: https://code.claude.com/docs/en/hooks (hookSpecificOutput schema)
