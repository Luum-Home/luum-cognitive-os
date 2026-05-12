# Sub-Agent Context Trim — Measurement Report

**Date**: 2026-04-20
**Author**: Orchestrator session
**Commits**: `2264356` (preamble/blast/gotchas), `3f36d8b` (task state dedup)

## Problem

Every sub-agent launch injected ~4-6 KB of boilerplate that repeated verbatim across every launch in a session:

- Full `templates/agent-preamble.md` (100 lines)
- Full `templates/project-gotchas.md` (46 lines) on every agent touching `lib/`, `hooks/`, `packages/`, `.cognitive-os/`, `settings.json`, or `cognitive-os.yaml`
- `BLAST RADIUS WARNING` on any prompt mentioning "migration" / "database" / "auth" keywords — 3 lines + signals + recommendation
- Duplicate `COS Task State` blocks: `task_bridge.py` and `task_panel_adapter.py` both listed the same tasks under different headers

User impact: orchestrator spent proportionally more time parsing repeated boilerplate than processing agent results. Four parallel agents ≈ 25 KB of overhead before signal.

## Changes applied

### 1. `templates/agent-preamble.md` — 100 → 34 lines

Commit `2264356`.

Removed:
- Explanatory prose ("Memory is a persistence layer across sessions...")
- Duplicated trust-report example (kept template header only)
- Verbose escalation protocol (kept 1-line summary + pointer to `rules/agent-escalation.md`)
- Context injection docs (kept 1-line rule)

Kept (structural only):
- No-flattery directive
- Retry/escalation 1-liners
- `NEEDS_CLARIFICATION:` trigger
- Engram save mandate
- Long-running command guard
- **Required `RESULT:` and `TRUST_REPORT:` templates** (the only thing agents actually need to copy)

Full reference pointers: `rules/agent-escalation.md`, `rules/trust-score.md`, `rules/closed-loop-prompts.md`.

### 2. `hooks/blast-radius.sh` — threshold raised, text compressed

Commit `2264356`.

Classification before:
```
CRITICAL  if  INFRA_HIT  OR  SECURITY_HIT  OR  file_score > 50
HIGH      if  file_score > 20
MEDIUM    if  file_score > 5
```

Classification after:
```
CRITICAL  if  (INFRA_HIT AND SECURITY_HIT)  OR  file_score > 100
HIGH      if  file_score > 40
(LOW/MEDIUM silent — JSONL log still captures all levels)
```

Text before (~400 B):
```
BLAST RADIUS WARNING: this operation is CRITICAL. Estimated impact: 23+ files. Signals:
FILE PATHS: 8 explicit file references detected
DIRECTORIES: 3 directory references (estimated ~15 files)
RECOMMENDATION: consider /sandbox-sample for validation before full-scale apply.
```

Text after (~85 B):
```
BLAST RADIUS: CRITICAL (~23 files, infra+security). Consider /sandbox-sample.
```

### 3. `hooks/inject-phase-context.sh` — gotchas dedup per session

Commit `2264356`.

First agent in session that touches COS internals still gets the full `templates/project-gotchas.md` (~1800 B).
Subsequent agents in the same session get a 1-line pointer (~75 B):

```
Gotchas reference: templates/project-gotchas.md (already loaded this session)
```

Marker file: `.cognitive-os/sessions/{SESSION_ID}/.gotchas-injected` (zero-byte). Falls back to `default` session id when `COGNITIVE_OS_SESSION_ID` is unset.

### 4. `hooks/_lib/task_panel_adapter.py` — skip tasks already in native panel

Commit `3f36d8b`.

`task_bridge.py` emits `## COS In-Progress with native Task panel link (N)` for tasks that have a `toolUseId`. `task_panel_adapter.py` was ALSO emitting the same tasks under `## COS Task State (not visible in native Task panel)`. Contradictory and wasteful.

Fix:
- Filter out tasks with `toolUseId` before formatting.
- If no `in_progress`/`queued`/`failed` items remain after filter, return empty (no header block).

Verified with 3 cases:
| Input | Output |
|---|---|
| empty list | empty string |
| all-bridge tasks (`toolUseId` set) | empty string |
| no-bridge tasks | block emitted (unchanged behavior) |
| completed-only | empty string (was a noise header before) |

## Measurement methodology

Launched two diagnostic sub-agents back-to-back in the same session, captured the `<system-reminder>` content injected into each:

- **Probe 1** — first agent in session, prompt mentions `lib/`, `hooks/`, `packages/`, `database migration`, `authentication` (intentionally triggers all old rules).
- **Probe 2** — second agent, same kind of prompt, immediately after probe 1.

## Results

| Component | Before (pre-trim) | Probe 1 (post-trim) | Probe 2 (post-trim) |
|---|---|---|---|
| BLAST RADIUS warning | ~400 B (3 lines + signals + rec) | 85 B (1 line) | 85 B (1 line) |
| Agent preamble | ~2500 B (100 lines) | 1328 B (36 lines) | 1328 B (36 lines) |
| Project gotchas | ~1800 B (full) | 1800 B (full — first in session) | ~75 B (pointer) |
| COS Task State duplicate | emitted alongside task_bridge | N/A (no tasks in probe) | N/A (no tasks in probe) |
| **Per-agent total** | **~4700 B** | **~3200 B (-32%)** | **~1500 B (-68%)** |

### Aggregate impact (typical: 4 agents in parallel)

| Scenario | Before | After |
|---|---|---|
| 4 parallel agents, full boilerplate each | ~19000 B | - |
| 4 parallel agents, 1 full + 3 deduped | - | ~7700 B (-60%) |

## Remaining out-of-scope

- **Agent output diet** (RESULT/TRUST_REPORT length on the return side). Not fixed with a hook — depends on agents internalizing the shorter preamble. Expected to shrink organically on next batch.
- **BLAST RADIUS per-session dedup for HIGH**. Currently HIGH fires every time. If the same signal pattern (e.g. `file_score=45`, infra=false, security=false) reappears in a single session, could suppress. Not done; low-priority.
- **Preamble per-session dedup**. The preamble is still injected on every agent call. Could apply the same marker approach as gotchas, but the preamble text is what tells the agent HOW to respond — riskier to dedup. Not done.

## Evidence artifacts

- Probe 1 agent id: `af757600be98e4d7e`
- Probe 2 agent id: `a958e291185a96d81`
- System-reminder content captured in session transcript (parent session `1776695202-2365-0c528bfb`)

## Reproduce the measurement

```bash
# With any fresh session (to reset gotchas marker):
rm -f .cognitive-os/sessions/default/.gotchas-injected 2>/dev/null

# Launch a probe agent with keywords that trigger all old rules:
# (via Claude Code Agent tool with a prompt mentioning
#  lib/, hooks/, packages/, "database migration", "authentication")

# Observe the <system-reminder> injected. Expected:
# - BLAST RADIUS: ~85 B one-liner (if any)
# - AGENT PREAMBLE: ~1300 B (36 lines)
# - PROJECT GOTCHAS: full ~1800 B first time, ~75 B pointer after

# Second launch in same session:
# - Gotchas pointer should replace full text
```

## Commits

| SHA | Change |
|---|---|
| `2264356` | preamble diet + blast-radius threshold + gotchas dedup |
| `3f36d8b` | task state dedup in task_panel_adapter |
