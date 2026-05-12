---
adr: 86
title: Hook Execution Observability
status: accepted
implementation_status: partial
date: '2026-04-30'
supersedes: []
superseded_by: null
implementation_files: []
tier: maintainer
tags: []
classification_basis: accepted record with explicit partial/phase scope
partial_remaining: The user's global settings.json already uses `claude-hud` for the statusline; composing the hook status into claude-hud would require modifying the plugin — this is deferred.
remaining_in_scope: true
partial_remaining_basis: explicit body remaining signal
---

# ADR-086: Hook Execution Observability

<!-- Renumbered-from: attempted ADR-085 during the ADR reservation race documented in ADR-089. -->
<!-- Canonical-number: ADR-086. ADR-085 remains intentionally unused rather than reusing a contested slot. -->

**Status**: Accepted (2026-04-30)

## Status

Accepted. The canonical number is ADR-086; ADR-085 was an abandoned contested reservation during the concurrent ADR slot race documented by ADR-089.

## Context

COS hooks were causing silent hangs of 2–7 minutes during `SessionStart` and between harness turns. The hangs were invisible: no stderr output, no metrics, no way to identify the culprit hook without manual trial-and-error.

A deep audit (Engram: `cos/sessionstart-deep-audit`) measured the three primary culprits:

| Hook | Event | p95 latency |
|------|-------|------------|
| `content-policy` | SessionStart / Stop | 4.3s |
| `inject-phase-context` | SessionStart | 3.8s |
| `destructive-rm-blocker` | PreToolUse | 1.6s |

Total `SessionStart` wall time exceeded 2 minutes in the worst-case session, dominated by sequential hook execution with no timeout enforcement. Related Engram context: `cos/hook-timing-instrumentation` (the original wrapper design), `cos/hook-observability-followup` (partial follow-up identifying gaps).

The core problem: Claude Code provides no native hook timing instrumentation. Hooks are opaque processes; their wall time, exit codes, and event associations are not recorded anywhere accessible for analysis.

## Decision

Implement a four-layer observability stack for hook execution:

### Layer 1: Wrapper trampoline (`scripts/hook-timing-wrapper.sh`)

Every hook command in `settings.json` is invoked as:
```
bash scripts/hook-timing-wrapper.sh <event_name> <hook_path> [args]
```

The wrapper records a JSONL entry to `.cognitive-os/metrics/hook-timing.jsonl` for every hook invocation, capturing: timestamp, event name, hook name, wall-clock duration (ms), exit code, PID, and session ID. Overhead target: <10ms median.

**Why trampoline rather than per-hook self-instrumentation:** Zero coupling to hook internals. Hooks need no changes. Adding, removing, or rewriting a hook does not affect instrumentation. The wrapper can be disabled entirely via `COS_HOOK_TIMING_DISABLE=1` without touching any hook file.

### Layer 2: JSONL aggregation report (`scripts/hook_timing_report.py`)

Reads the JSONL log and produces p50/p95/p99 statistics per hook. Supports:
- `--live`: real-time tail of new entries
- `--event <name>`: filter to a harness event (e.g. `Stop`, `SessionStart`)
- `--session <id>`: scope to a single COS session ID
- `--since <duration>`: time window filtering

### Layer 3: FIFO stream (`scripts/hook-stream-statusline.sh`)

The wrapper can write compact human-readable lines to `.cognitive-os/runtime/hook-stream.fifo` when `COS_HOOK_TIMING_FIFO=1`. The reader script opens the FIFO O_RDWR | O_NONBLOCK (via Python) to avoid blocking when no writer is attached — a macOS requirement, since O_RDONLY on a FIFO blocks until a writer opens it.

**Why FIFO in addition to JSONL tail:** JSONL tail (`--live`) requires a live `tail -f` process. The FIFO provides a pull-on-demand model for statusline integrations that poll every few seconds without spawning persistent subprocesses.

### Layer 4: Discoverable skill (`skills/hook-timing/SKILL.md`)

The `/hook-timing` skill exposes all four invocation modes with documentation, so users and agents can find the observability surface without knowing the script path.

## Consequences

### Positive

- **Live observability**: any session hang can be diagnosed in real-time via `--live` or the FIFO reader.
- **Kill-switchable**: `COS_HOOK_TIMING_DISABLE=1` removes all overhead instantly.
- **Cross-project portable**: wrapper requires only bash + python3. No external dependencies.
- **Retrofittable**: existing hooks need no changes.
- **Discoverable**: skill catalog entry makes the tooling findable.

### Negative

- **Wrapper overhead**: ~93ms median per hook (python3 startup for `_now_ms()`). This is non-trivial if a hook chain has 20+ hooks firing synchronously. Mitigation: use `gdate` if GNU coreutils is available (reduces to ~5ms); or disable with the kill-switch.
- **FIFO requires a reader to be open**: writes from the wrapper fail silently when no reader is attached (macOS `ENXIO`). This is intentional (best-effort) but means the FIFO is only useful when something is actively reading it.
- **Statusline integration is partial**: the project `.claude/settings.json` `statusLine` key is generated by `apply-efficiency-profile.sh` and is not currently wired to `hook-stream-statusline.sh`. The user's global settings.json already uses `claude-hud` for the statusline; composing the hook status into claude-hud would require modifying the plugin — this is deferred. The reader script is documented as a standalone tool for now.
- **Session ID attribution**: session ID is inherited from environment variables (`COGNITIVE_OS_SESSION_ID`, `CLAUDE_SESSION_ID`, `CODEX_SESSION_ID`). If the harness does not set these, `session_id` is empty and `--session` filtering has no effect.

### Follow-up actions

1. Optimize the three measured slow hooks (`content-policy`, `inject-phase-context`, `destructive-rm-blocker`) — latency reduction, not observability.
2. Replace `python3 -c "import time..."` in `_now_ms()` with `gdate` detection to reduce wrapper overhead from ~93ms to ~5ms on machines with GNU coreutils.
3. Investigate composing `hook-stream-statusline.sh` output into the claude-hud statusline plugin rather than replacing it.

## Alternatives rejected

- Keep the previous behavior unchanged — rejected because the audit or runtime failure would remain deterministic and would continue masking real regressions.

## Verification

Run the focused contract for this decision:

```bash
python3 -m pytest tests/audit/test_hook_latency_budget.py -q
```
