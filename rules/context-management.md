<!-- TIER: 1 -->
<!-- SCOPE: both -->
# Context Window Management — Proactive Summarization Protocol

## Overview

Context window is a finite resource. Losing context to compaction without saving state means the next session starts blind. This protocol defines behavior at each capacity threshold to ensure graceful degradation.

## Capacity Thresholds

### 50% — Efficiency Mode

The context-watchdog hook emits an informational note.

**Agent behavior:**
- Continue work normally
- Be concise in responses — avoid verbose explanations
- Avoid reading entire large files when a targeted read suffices
- If key decisions have been made, save them to Engram now rather than later
- Prefer Grep over Read for searching

### 70% — Save and Summarize

The context-watchdog hook emits a WARNING. This is the critical save point.

**Agent behavior (mandatory):**
1. **Save to Engram immediately** — call `mem_save` for:
   - Decisions made (architecture, library choices, approach)
   - Bugs fixed (root cause, solution, affected files)
   - Discoveries (gotchas, patterns, non-obvious behavior)
   - Current task state (what is done, what remains)
2. **Reduce verbosity** — short answers, no explanations unless asked
3. **Stop exploring** — no speculative reads or searches
4. **Plan wrap-up** — estimate if current task can complete in ~15 tool calls
5. **If task is large** — checkpoint progress and note remaining work for next session

### 85% — Finish and Handoff

The context-watchdog hook emits an URGENT warning. Compaction is imminent.

**Agent behavior (mandatory):**
1. **Stop new work** — do not start any new tasks
2. **Complete or checkpoint** the current task
3. **Call `mem_session_summary`** with full session state including:
   - Goal of the session
   - What was accomplished
   - What remains (next steps)
   - Files modified
   - Relevant discoveries
4. **Final `mem_save`** for anything not yet persisted
5. **Inform the user** that context is nearly full

### 95% — Pre-Compaction Flush (existing)

The `pre-compaction-flush.sh` hook activates at actual compaction time.
This is the last-resort safety net — the 70% and 85% thresholds should have already persisted critical state.

## Integration with Existing Hooks

```
Compaction     → pre-compaction-flush.sh: LAST RESORT (emergency save)
```

Note: The `context-watchdog.sh` hook (which would emit threshold warnings at 50/70/85% tool call counts) is NOT currently registered in `settings.local.json`. The thresholds above are AGENT BEHAVIORAL GUIDELINES that the agent should self-monitor based on approximate tool call count awareness. The `pre-compaction-flush.sh` hook is the only registered automated safety net.

## Heuristic Accuracy

Tool-call-count thresholds are approximate behavioral guides:
- Average tool call + response: ~500-1000 tokens
- 100 tool calls ~ 50k-100k tokens of context
- Thresholds are conservative — better to save early than lose data

## Anti-Patterns

- DO NOT ignore the 70% warning — this is the primary save point
- DO NOT start large multi-file operations after 70%
- DO NOT wait for the 85% warning to save decisions — save at 70%
- DO NOT rely solely on pre-compaction-flush — it may not have enough time to save everything
