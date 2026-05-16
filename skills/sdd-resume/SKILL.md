---
name: sdd-resume
command: /sdd-resume
version: 1.0.0
description: 'Use when you need this Cognitive OS skill: Resume an SDD pipeline from
  its last completed phase with timing and state visibility; do not use when a narrower
  skill directly matches the task.'
trigger: User invokes /sdd-resume [change-name] [--from phase], or needs to inspect/continue
  SDD state
inputs:
- change-name (optional): SDD change to resume. If omitted, lists all in-progress
    changes.
- --from (optional): Force resume from a specific phase (skips auto-detection).
audience: project
outputs:
- next_phase: The phase to execute next
- state_summary: Current pipeline state with timing data
- timing_table: ASCII table of per-phase durations and costs
summary_line: Resume an SDD pipeline from its last completed phase with timing and
  state…
routing:
  tier: cheap
  providers_preferred:
  - qwen
  - claude
  fallback_on_rate_limit: true
  fallback_on_any_error: true
  budget_max_usd_per_call: 0.25
platforms:
- claude-code
prerequisites: []
routing_patterns:
- pattern: \bsdd[- ]?resume\b
  confidence: 0.96
- pattern: \bresume\s+(the\s+)?sdd\b
  confidence: 0.9
- pattern: \blast\s+completed\s+(sdd\s+)?phase\b
  confidence: 0.84
routing_intents:
- intent: resume_sdd_from_last_completed_phase
  description: User wants to restart an SDD pipeline from detected progress or a specified phase with state visibility.
  confidence: 0.9
- intent: report_sdd_phase_timing
  description: User asks for SDD continuation with per-phase timing and cost context, distinct from general next-action recommendation.
  confidence: 0.86
triggers:
- sdd-resume
- /sdd-resume
- SDD Resume
- Resume an SDD pipeline from its last completed phase with timing and state…
---
<!-- SCOPE: both -->
# SDD Resume

## Purpose

Resume an SDD pipeline from its last completed phase. Provides state inspection, timing summaries, and cost estimates. Integrates with Engram for cross-session state persistence.

## Invocation

```
/sdd-resume                        # List all in-progress SDD changes
/sdd-resume <change-name>          # Resume the named change
/sdd-resume <change-name> --from spec  # Force resume from a specific phase
```

## Procedure

### Step 1: Load State

1. Search Engram for existing state:
   ```
   mem_search(query: "planning/{change-name}/state", project: "{project}")
   ```
2. If found, retrieve full content:
   ```
   mem_get_observation(id: {id})
   ```
3. Parse the JSON state from the observation content.

### Step 2: Determine Action

**If no change-name provided:**
1. Search Engram for all SDD states: `mem_search(query: "planning/ state", project: "{project}")`
2. For each result, parse state and collect: change_name, progress, current_phase
3. Display a summary table of all in-progress changes:
   ```
   In-Progress SDD Changes:
   | Change           | Progress | Current Phase | Retries | Total Time |
   |------------------|----------|---------------|---------|------------|
   | auth-refactor    | 5/8      | apply         | 0       | 12m 30s    |
   | payment-gateway  | 3/8      | design        | 1       | 8m 15s     |
   ```
4. Ask which change to resume (if multiple exist).

**If change-name provided:**
1. Use `lib/sdd_resume.py::resume(change_name, state_json, start_from)` to determine next phase.
2. Display state summary using `lib/sdd_resume.py::format_state_summary()`.
3. Display timing table using `lib/phase_timing.py::format_timing_table()`.

### Step 3: Show State and Timing Summary

Display the following for the selected change:

```
SDD Change: {change-name}
Progress: {completed}/{total} phases completed
Completed: explore, propose, spec, design, tasks
Remaining: apply, verify, archive
Current Phase: None
Retry Count: 0

Phase Timing:
+----------+----------+--------+-----------+
| Phase    | Duration | Model  | Est. Cost |
+----------+----------+--------+-----------+
| explore  | 1m 20s   | sonnet | $0.0540   |
| propose  | 3m 45s   | opus   | $0.4950   |
| spec     | 2m 10s   | sonnet | $0.1500   |
| design   | 4m 00s   | opus   | $0.5100   |
| tasks    | 1m 15s   | sonnet | $0.1560   |
+----------+----------+--------+-----------+
| TOTAL    | 12m 30s  | ---    | $1.3650   |
+----------+----------+--------+-----------+
```

### Step 4: Resume Execution

1. Report the next phase to execute and the reason.
2. The orchestrator decides whether to launch the phase.
3. This skill does NOT launch the phase itself -- it only determines and reports what should run next.

### Step 5: Persist Timing After Phase Completion

After the orchestrator completes a phase, it should call:
1. `lib/phase_timing.py::append_timing_jsonl()` to log to `metrics/sdd-timings.jsonl`
2. `lib/sdd_resume.py::save_state()` to update the pipeline state
3. Save updated state to Engram with topic_key `planning/{change-name}/state`

## State Format

State is persisted as JSON in Engram under `planning/{change-name}/state`:

```json
{
  "change_name": "auth-refactor",
  "current_phase": null,
  "phases_completed": ["explore", "propose", "spec", "design", "tasks"],
  "retry_count": 0,
  "max_retries": 3,
  "timings": {
    "explore": 80.5,
    "propose": 225.3,
    "spec": 130.0,
    "design": 240.1,
    "tasks": 75.8
  },
  "history": [
    {"phase": "explore", "status": "completed", "duration_secs": 80.5, "timestamp": "2026-03-26T10:00:00Z", "action": "completed"},
    {"phase": "propose", "status": "completed", "duration_secs": 225.3, "timestamp": "2026-03-26T10:05:00Z", "action": "completed"}
  ],
  "created_at": "2026-03-26T10:00:00Z",
  "updated_at": "2026-03-26T10:30:00Z"
}
```

## Library Dependencies

This skill uses two library modules:

- `lib/sdd_resume.py` — State management, phase determination, change listing
- `lib/phase_timing.py` — PhaseTimer context manager, ASCII table rendering, JSONL persistence, cost estimation

## Integration with SDD Pipeline

The orchestrator integrates timing into the SDD flow:

```python
from lib.phase_timing import PhaseTimer, append_timing_jsonl
from lib.sdd_resume import save_state

# Before launching a phase
with PhaseTimer("apply", change_name="auth-refactor") as timer:
    # ... run the phase ...
    pass

# After phase completes
result = save_state(
    change_name="auth-refactor",
    phase="apply",
    status="completed",
    timing_secs=timer.duration_secs,
    state_json=existing_state,
)

# Persist to JSONL
append_timing_jsonl(
    "metrics/sdd-timings.jsonl",
    phase="apply",
    duration_secs=timer.duration_secs,
    change_name="auth-refactor",
)

# Persist state to Engram
# mem_save(title=result["engram_title"], content=result["state_json"],
#          topic_key=result["topic_key"], type="pattern")
```

## Error Handling

- If Engram has no state for the change, a fresh state is created automatically.
- If `--from` specifies a phase with unmet dependencies, the skill reports the missing dependencies and does not proceed.
- If retry_count >= max_retries, the skill reports that human intervention is required.

## Result Contract

Returns:
- `status`: "ok" or "blocked"
- `executive_summary`: One-line description of next action
- `next_phase`: Phase name or null if pipeline is complete/blocked
- `timing_table`: ASCII table string (if timings exist)
- `state`: Full state dict
