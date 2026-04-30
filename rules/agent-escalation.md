<!-- SCOPE: both -->
<!-- TIER: 0 -->
# Agent Escalation Protocol

## Purpose

Agents currently retry 3 times mechanically then fail. They do not detect loops, do not measure their own progress, and do not escalate with diagnosis. This protocol gives agents the ability to self-detect unproductive patterns and escalate early with structured diagnosis instead of spinning on dead ends.

The key insight: it is better to escalate after 30 seconds of being stuck than to waste 3 minutes of retries that never had a chance of succeeding. Like a junior developer who should ask for help after 30 minutes, not after 3 hours.

## When to Escalate

| Signal | Condition | Meaning |
|--------|-----------|---------|
| `loop_detected` | Same file edited 3+ times, or same command run 3+ times | The fix approach is not converging. Retrying the same thing will not produce different results. |
| `no_progress` | >10 tool calls without a `PROGRESS:` marker | The agent is working but not making measurable forward progress. |
| `confidence_drop` | Error rate >50% in last 5 tool calls | The agent is failing more than succeeding. The current approach is wrong. |
| `error_repeat` | Same error message seen 2+ times | The error is not being resolved between attempts. The root cause is not being addressed. |
| `timeout_risk` | >80% of expected tool call budget consumed | The agent is running out of runway. Remaining work may not fit. |

## How to Escalate

When a signal is detected, the agent outputs the `ESCALATION:` marker:

```
ESCALATION:
  Type: loop_detected
  Severity: recommend
  Evidence: File tests/foo.py edited 4 times with same error
  Tool calls: 15
  Diagnosis: Test expects value X but code produces Y. May need architectural change.
  Recommendation: Re-launch with different approach or escalate to human.
```

The `ESCALATION:` marker is detected by the orchestrator's PostToolUse hooks, similar to `NEEDS_CLARIFICATION:` and `PROGRESS:`.

## Severity Levels

| Severity | Agent Behavior | Orchestrator Response |
|----------|---------------|----------------------|
| `suggest` | Agent continues working but flags the concern | Orchestrator logs it; may adjust strategy at next checkpoint |
| `recommend` | Agent pauses current approach, outputs diagnosis | Orchestrator re-launches with different model, approach, or context |
| `urgent` | Agent stops immediately, outputs full diagnosis | Orchestrator escalates to human with the agent's diagnosis |

### Severity Assignment

| Condition | Severity |
|-----------|----------|
| Same file edited 3x | suggest |
| Same file edited 6x+ | recommend |
| Same file edited 9x+ | urgent |
| Same error 2x | suggest |
| Same error 3x+ | recommend |
| 8-14 calls without progress | suggest |
| 15-24 calls without progress | recommend |
| 25+ calls without progress | urgent |
| Error rate 50-80% | suggest |
| Error rate >80% | recommend |
| Budget 80-90% used | suggest |
| Budget 90-95% used | recommend |
| Budget >95% used | urgent |

## Orchestrator Response Protocol

When the orchestrator receives an `ESCALATION:` marker:

### On `suggest`
1. Log the signal to `.cognitive-os/metrics/escalation-events.jsonl`
2. Let the agent continue
3. If a second `suggest` signal fires for the same type, treat as `recommend`

### On `recommend`
1. Log the signal
2. Save the agent's partial progress to Engram
3. Choose ONE of:
   - Re-launch with a different model (e.g., switch from sonnet to opus for debugging)
   - Re-launch with a different approach (inject the diagnosis as context)
   - Re-launch with additional context from Engram (search for related past solutions)
4. The re-launched agent receives the original task PLUS the escalation diagnosis

### On `urgent`
1. Log the signal
2. Save the agent's partial progress and full diagnosis to Engram
3. Report to the human with the full escalation report
4. Do NOT auto-retry -- human decides next step

## Relationship to Existing Retry Mechanism

The escalation protocol complements the closed-loop 3-retry mechanism from `closed-loop-prompts.md`:

```
Agent starts task
    |
    v
Attempt 1 -> Verify
    |
    ├── Pass -> Done
    └── Fail -> [check escalation signals]
         |
         ├── Signal detected -> ESCALATE (skip remaining retries)
         └── No signal -> Continue to Attempt 2
              |
              v
Attempt 2 -> Verify
    |
    ├── Pass -> Done
    └── Fail -> [check escalation signals]
         |
         ├── Signal detected -> ESCALATE
         └── No signal -> Continue to Attempt 3
              |
              v
Attempt 3 -> Verify
    |
    ├── Pass -> Done
    └── Fail -> ESCALATE (retries exhausted, always escalate)
```

The escalation detector can fire BEFORE the 3 retries are exhausted. If the same error appears on attempt 1 and attempt 2 (error_repeat), escalation fires immediately instead of wasting a third attempt on the same failure.

## Anti-Patterns

### Escalating too early (<5 tool calls)
Not enough data to diagnose the problem. The agent should attempt reasonable fixes before escalating. Exception: if the very first error is clearly outside scope (wrong language, missing dependency, permission denied).

### Never escalating (overclaiming)
An agent that retries 3 times and reports "failed" without ever outputting `ESCALATION:` is wasting tokens. After the first retry failure, the agent MUST check escalation signals.

### Escalating without diagnosis
The `ESCALATION:` output MUST include a `Diagnosis:` field with the agent's best guess at root cause. "I don't know why it fails" is not acceptable. The agent should at least state what it observed.

### Escalating without saving progress
Before escalating, the agent MUST save any partial progress to Engram. The next agent (or human) should not have to redo completed work.

## Detection Library

The detection logic lives in `lib/escalation_detector.py`:

| Function | Description |
|----------|-------------|
| `EscalationDetector()` | Create a new detector for an agent run |
| `record_tool_call(tool, success, error_msg, target_file, command)` | Record each tool call |
| `record_progress(marker)` | Record a PROGRESS marker (resets no-progress counter) |
| `check_should_escalate()` | Analyze patterns, return signal or None |
| `format_escalation(signal)` | Format the ESCALATION: output |
| `get_escalation_metrics()` | Return metrics dict for KPI tracking |
| `save_metrics(metrics_dir)` | Persist to escalation-events.jsonl |

## Metrics

Escalation events are logged to `.cognitive-os/metrics/escalation-events.jsonl`:

```json
{
  "timestamp": "ISO-8601",
  "escalation_count": 1,
  "tool_calls_total": 15,
  "progress_markers": 2,
  "error_rate": 0.4,
  "error_count": 6,
  "files_modified_unique": 3,
  "stuck_duration": 8,
  "escalation_types": {"loop_detected": 1}
}
```

## Integration with Other Rules

| Rule | Relationship |
|------|-------------|
| Closed-Loop Prompts (`closed-loop-prompts`) | Escalation fires within the retry loop, potentially short-circuiting retries. |
| Trust Score (`trust-score`) | Agents that escalate appropriately get higher self-awareness scores than agents that spin silently. |
| Agent Quality (`agent-quality`) | Escalation prevents the "minimum viable retry" anti-pattern where agents retry mechanically without analysis. |
| Agent KPIs (`agent-kpis`) | Escalation rate, resolution rate, and time-to-escalate are tracked KPIs. |
| Split-and-Resume (`split-and-resume`) | NEEDS_CLARIFICATION is for ambiguity. ESCALATION is for being stuck. Different signals, same orchestrator handling pattern. |
| Auto-Refine (`closed-loop-prompts`) | Auto-refine retries should check escalation signals between retries. |

## Contextual Trigger

This rule is loaded when: escalation, agent stuck, retry failure, loop detected, no progress, error repeat.
