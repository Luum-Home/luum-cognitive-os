---
name: hook-timing
description: 'Use when you need this Cognitive OS skill: Report hook execution timing
  statistics (p50/p95/p99) from the COS hook-timing wrapper. Supports live tail, event
  filtering, and session scoping.; do not use when a narrower skill directly matches
  the task.'
version: 1.0.0
user-invocable: true
auto-generated: false
audience: os
model: sonnet
summary_line: Analyze hook execution latency — full stats, live tail, per-event or
  per-session views.
platforms:
- claude-code
prerequisites: []
tags:
- observability
- performance
- debugging
routing_patterns:
- pattern: \bhook[- ]?timing\b
  confidence: 0.95
- pattern: \bhook\s+(stats|timing|performance|p50|p95|p99)\b
  confidence: 0.85
routing_intents:
- intent: hook_timing_request
  description: User asks to report hook execution timing statistics (p50/p95/p99)
    from the COS hook-timing wrapper. Supports live tail, event filtering, and session
    scoping.
  confidence: 0.85
triggers:
- hook-timing
- /hook-timing
- Hook Timing Skill
- Analyze hook execution latency — full stats, live tail, per-event or per-session
  views
---
<!-- SCOPE: os-only -->
# Hook Timing Skill

Inspect hook execution latency recorded by `scripts/hook-timing-wrapper.sh`. The wrapper runs as a trampoline around every hook in `settings.json` and appends structured JSONL records to `.cognitive-os/metrics/hook-timing.jsonl`. This skill surfaces that data in human-readable form.

Use this skill when:
- Diagnosing silent hangs or slow turn-around between SessionStart and first prompt.
- Identifying which hook is responsible for a latency spike.
- Monitoring hook health in real-time during a debugging session.
- Scoping timing data to a specific COS session ID.

## Invocation Modes

### `/hook-timing` (default)
Full aggregate report: p50/p95/p99 latency for every hook across all recorded data, plus a top-10 slowest individual invocations list.

```bash
python3 scripts/hook_timing_report.py
```

### `/hook-timing --live`
Tail the JSONL file and print each new hook invocation in real-time as the session runs. Useful for diagnosing hangs interactively. Press Ctrl+C to stop.

```bash
python3 scripts/hook_timing_report.py --live
```

### `/hook-timing --event Stop`
Filter the report to only hooks that fired on the `Stop` harness event (between-turn hooks). Replace `Stop` with any event name: `PreToolUse`, `PostToolUse`, `SessionStart`, etc.

```bash
python3 scripts/hook_timing_report.py --event Stop
```

### `/hook-timing --session <id>`
Scope the report to a single COS session. `<id>` matches the `COGNITIVE_OS_SESSION_ID` (or `CLAUDE_SESSION_ID` / `CODEX_SESSION_ID`) value stamped in each JSONL record.

```bash
python3 scripts/hook_timing_report.py --session <id>
```

## Additional Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--top N` | 10 | Show top N slowest individual invocations |
| `--since Nh` | (all) | Limit to last N hours/minutes/days (e.g. `1h`, `30m`, `2d`) |
| `--json` | off | Machine-readable JSON output |
| `--path <file>` | auto | Override path to `hook-timing.jsonl` |

Flags compose freely: `--event Stop --since 1h --top 20`.

## Instructions

### Step 1: Determine mode

Parse the invocation arguments to select the correct flag combination:
- No arguments → default full report
- `--live` present → live tail mode
- `--event <name>` → pass `--event` to the script
- `--session <id>` → pass `--session` to the script

### Step 2: Run the script

```bash
python3 scripts/hook_timing_report.py [flags]
```

The script is self-contained and requires no imports beyond the Python standard library.

### Step 3: Interpret and report

**For the default report:**
Present the p95 column as the primary latency signal (worst-case typical). Flag any hook with p95 > 2000ms as a candidate for optimization. The three historically slow hooks are `content-policy` (p95 ~4.3s), `inject-phase-context` (~3.8s), and `destructive-rm-blocker` (~1.6s).

**For live mode:**
Relay lines as they appear. Lines marked `⚠ SLOW` indicate hooks exceeding 5s — surface these immediately to the user.

**For session/event filtered reports:**
Summarize the filter applied and total records matched before presenting stats.

## Kill-switch

If the wrapper is causing overhead that needs to be disabled immediately:

```bash
export COS_HOOK_TIMING_DISABLE=1
```

This causes the wrapper to `exec` the real hook directly with zero instrumentation overhead.

## FIFO / Real-time Stream

The wrapper can also write to `.cognitive-os/runtime/hook-stream.fifo` when `COS_HOOK_TIMING_FIFO=1` is set. A standalone reader is available at `scripts/hook-stream-statusline.sh` for external tooling that wants a non-blocking one-line status feed without tailing the JSONL.

## Data Location

- JSONL log: `.cognitive-os/metrics/hook-timing.jsonl`
- FIFO stream: `.cognitive-os/runtime/hook-stream.fifo`
- Wrapper: `scripts/hook-timing-wrapper.sh`
- ADR: `docs/02-Decisions/adrs/ADR-086-hook-execution-observability.md`
