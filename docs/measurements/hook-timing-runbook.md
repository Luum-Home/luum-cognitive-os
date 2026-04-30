# Hook Timing Instrumentation — Runbook

> ADR: none (pure instrumentation, no architectural tradeoff).
> Incident: 2026-04-30 wrapper stderr/FIFO reporting leaked orphaned bash processes; wrapper summary/FIFO output is now opt-in.
> Log: `.cognitive-os/metrics/hook-timing.jsonl`
> Wrapper: `scripts/hook-timing-wrapper.sh`
> Report: `scripts/hook_timing_report.py`

## What this is

Every hook invocation writes one JSON line to `hook-timing.jsonl` with
the harness event name (Stop, PreToolUse, PostToolUse, etc.), hook name,
wall-clock duration in milliseconds, exit code, and PID. This makes silent
2-7 minute turn hangs diagnosable without adding user-visible hook chatter.

The wrapper is deliberately quiet by default. Do not enable stderr summaries or
FIFO streaming globally: async hooks can outlive the harness-side reader, and
inherited stream writes caused orphaned wrapper processes on 2026-04-30.

## How to see which hook is blocking your turn (live)

Open a second terminal and run:

```bash
python3 scripts/hook_timing_report.py --live
```

This reads the JSONL file; it does not require FIFO streaming. Output streams each hook invocation as it completes:

```
  TIMESTAMP               EVENT                 HOOK                                 DUR  EXIT
  ─────────────────────── ─────────────────────  ─────────────────────────────────── ──── ────
  2026-04-30 17:03:14     PreToolUse             session-heartbeat                  168ms    0
  2026-04-30 17:03:14     PreToolUse             rate-limit-precheck                258ms    0
  2026-04-30 17:03:14     PreToolUse             rate-limiter                       288ms    0  ⚠ SLOW
```

Hooks marked `⚠ SLOW` exceed 5 seconds. If Claude appears stuck, this stream
shows you exactly which hook is still running.

One-liner alternative using raw `tail`:

```bash
tail -f .cognitive-os/metrics/hook-timing.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        r=json.loads(line)
        print(f\"{r['timestamp']} {r['event']:20} {r['hook']:35} {r['duration_ms']:6}ms exit={r['exit_code']}\")
    except: pass
"
```

## How to find the slowest hooks of the day

```bash
python3 scripts/hook_timing_report.py
```

Output includes:
- Per-hook table sorted by p95 duration (who is reliably slow)
- Top-10 slowest individual invocations (outlier hunting)
- Failed (non-zero exit) counts

Filter by event type to isolate which lifecycle point is responsible:

```bash
# See only Stop hooks (fires between turns — most likely source of inter-turn hangs)
python3 scripts/hook_timing_report.py --event Stop

# See only PreToolUse hooks (fires before every tool call)
python3 scripts/hook_timing_report.py --event PreToolUse

# Last hour only
python3 scripts/hook_timing_report.py --since 1h

# Top 20 slowest
python3 scripts/hook_timing_report.py --top 20
```

## How to interpret the JSONL

Each line is a JSON object:

```json
{
  "timestamp":  "2026-04-30T17:03:14Z",   // UTC ISO-8601
  "event":      "PreToolUse",              // harness lifecycle event
  "hook":       "rate-limiter",            // hook filename without .sh
  "duration_ms": 288,                      // wall-clock ms (wrapper overhead ~93ms)
  "exit_code":  0,                         // hook's actual exit code
  "pid":        19888                      // wrapper process PID
}
```

Note: `duration_ms` includes wrapper overhead (~93ms on macOS due to 2x python3
subprocess launch). For absolute hook timing, subtract ~93ms. For comparative
analysis (which hook is slower than others), the overhead is constant and does
not distort rankings.

## How to disable timing

If the wrapper itself causes problems, disable it without touching settings.json:

```bash
export COS_HOOK_TIMING_DISABLE=1
```

With this env var set, the wrapper execs the real hook directly with zero
overhead. Unset to re-enable logging.

Debug-only opt-ins:

```bash
export COS_HOOK_TIMING_VERBOSE=1  # stderr summary; short local sessions only
export COS_HOOK_TIMING_FIFO=1     # FIFO stream; only when a reader is attached
```

Do not set either variable in committed settings or long-running sessions unless
you are explicitly testing stream behavior.

To permanently disable, regenerate settings.json without the wrapper (revert
the `hook_entry` functions in `scripts/apply-efficiency-profile.sh`).

## Understanding inter-turn hangs

The Claude harness fires hooks synchronously at these points:

| Event | When it fires | Hangs between |
|---|---|---|
| `Stop` | After Claude finishes its turn | Turn N and turn N+1 |
| `PreToolUse` | Before every tool call | Tool invocation start |
| `PostToolUse` | After every tool call | Tool invocation end |
| `UserPromptSubmit` | On user message | User sends, Claude starts |
| `SessionStart` | On session open | First turn |

The most likely source of 2-7 minute inter-turn hangs is `Stop` hooks
(7 hooks: session-summary-reminder, session-learning, session-cleanup,
git-context-capture, session-changelog, kpi-trigger, engram-crystallize).

To check Stop hook timing from the last session:

```bash
python3 scripts/hook_timing_report.py --event Stop --since 2h
```

## Quick diagnosis workflow

1. User reports hang: "Claude took 4 minutes between my last response and this one."
2. Run: `python3 scripts/hook_timing_report.py --event Stop --since 2h`
3. Find the slowest hook(s) in the p95 column.
4. Cross-reference with `benchmark-hooks.sh` to confirm reproducibility:
   ```bash
   bash scripts/benchmark-hooks.sh --warn-ms 500 --fail-ms 2000
   ```
5. If a hook is consistently slow, check its logs (most hooks write to
   `.cognitive-os/metrics/<hook-name>.jsonl`) and consider making it `async`.

## Async vs sync hook classification

All slow hooks that do not need to block Claude should be marked `|async` in
`scripts/apply-efficiency-profile.sh`. Async hooks run in the background and do
not block the next turn. Current async hooks: `host-tool-doctor.sh`,
`engram-daemon-launcher.sh`, `infra-health.sh`, `context-watchdog.sh`,
`auto-checkpoint.sh`, `doc-sync-detector.sh`, `auto-repair-dispatcher.sh`,
`dequeue-notify.sh`, `state-heartbeat.sh`, and others.

If timing reveals a sync hook consistently taking >2 seconds, assess whether
it can be made async.
