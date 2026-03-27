# Fault Tolerance -- Comprehensive Resilience Guide

## Overview

The Cognitive OS implements a multi-layered resilience system that protects against data loss across all failure scenarios. This document covers every scenario, what happens, and how recovery works.

## Failure Scenarios and Recovery

| Scenario | What Happens | Recovery Mechanism | Data Risk |
|----------|-------------|-------------------|-----------|
| Normal session end | Stop hooks run, session summary saved to Engram, metrics merged | Automatic via `session-cleanup.sh` | None |
| Rate limit hit | API calls fail, agents die, no cleanup runs | `rate-limiter.sh` pauses and saves state; auto-checkpoint stash survives | Low |
| Context compaction | Context window shrinks, older turns lost | `pre-compaction-flush.sh` saves to Engram before compaction | Low |
| Terminal closed (Ctrl+C) | Stop hooks may or may not run | Auto-checkpoint stash survives in `.git/refs/stash`; `crash-recovery.sh` detects on next start | Low |
| Computer crash / power loss | Nothing runs, process killed instantly | Git stash from last auto-checkpoint survives on disk; checkpoint metadata in `.cognitive-os/checkpoints/` | Medium -- up to 5 min of work between checkpoints |
| Out of memory (OOM kill) | Process killed by OS, no cleanup | Same as crash -- git stash survives, `crash-recovery.sh` detects | Medium |
| Internet lost mid-session | API calls fail, agents die | Local stash survives; resume when online; `session-resume.sh` picks up incomplete tasks | Low |
| Disk full | Writes fail, state may corrupt | Atomic writes (`_atomic_write`) prevent partial JSON; git stash may fail | High |

## The 5-Tier Resilience Model

### Tier 1: Connection Resilience

Handles network interruptions and API failures.

- Automatic reconnection with exponential backoff
- Heartbeat monitoring via Agent Bus (when enabled)
- Graceful shutdown with 250ms grace period
- Rate limit detection with gradual delay

### Tier 2: LLM Call Resilience

Handles model API failures and token limits.

- Auth profile rotation on credential errors
- Rate limit detection with gradual delay
- Model fallback chain: opus -> sonnet -> haiku
- Thinking level reduction: extended -> normal -> low
- Max retry: 24 base + 8 per profile, cap 160

### Tier 3: Context Resilience

Handles context window exhaustion and compaction.

- Pre-compaction flush saves session state to Engram
- Context overflow triggers summarization with last N turns preserved
- Compaction diagnosis ID for post-mortem analysis
- Session summary saved to Engram on every compaction
- Context watchdog warns at 50%, 70%, 85% capacity

### Tier 4: Agent Resilience

Handles sub-agent failures and orphaned tasks.

- Sub-agent orphan detection (timeout-based)
- Parent notification on child failure
- Active tasks JSON for session recovery (`active-tasks.json`)
- Idempotent re-launch via `checkCommand`
- Session resume hook auto-checks incomplete tasks on restart

### Tier 5: Crash Resilience (WAL)

Handles catastrophic failures where no cleanup code runs.

- Auto-checkpoint every 5 minutes creates named git stashes
- Stashes survive in `.git/refs/stash` through any crash
- Checkpoint metadata saved alongside for context
- `crash-recovery.sh` SessionStart hook detects orphaned stashes
- `CheckpointManager` Python API for programmatic checkpoint operations

## Session Lifecycle and Safety Nets

```
Session Start
  |
  +-- session-init.sh (create session directory)
  +-- session-resume.sh (check for incomplete tasks)
  +-- crash-recovery.sh (check for orphaned stashes)
  |
  v
Normal Operation
  |
  +-- auto-checkpoint.sh (every 5 min, on Bash|Edit|Write)
  +-- error-pipeline.sh (capture errors)
  +-- context-management (agent behavioral guidelines at 50/70/85%)
  |
  v
Session End (normal)
  |
  +-- session-learning.sh (capture learnings)
  +-- session-cleanup.sh (merge metrics, deregister session)
  +-- kpi-trigger.sh (calculate KPI snapshot)
  +-- engram-auto-sync.sh (persist memory)
  |
  v
Session End (crash)
  |
  +-- [nothing runs]
  +-- Git stash from auto-checkpoint survives
  +-- Next session: crash-recovery.sh detects and reports
```

## Checkpoint System Details

### What Gets Checkpointed

1. All uncommitted file changes (via git stash)
2. Checkpoint metadata: timestamp, dirty file count, session ID

### What Survives Each Scenario

| Data | Normal End | Crash | OOM | Network Loss |
|------|-----------|-------|-----|-------------|
| Committed code | Yes | Yes | Yes | Yes |
| Git stash (auto-checkpoint) | Yes | Yes | Yes | Yes |
| Session state JSON | Yes | Maybe | Maybe | Yes |
| Engram memory | Yes | No | No | No |
| Active tasks JSON | Yes | Yes | Yes | Yes |
| Metrics JSONL | Yes | Partial | Partial | Yes |

### Recovery Priority

On session start, the system checks in this order:

1. `crash-recovery.sh` -- orphaned git stashes
2. `session-resume.sh` -- incomplete tasks in active-tasks.json
3. `engram-auto-import.sh` -- restore Engram context

## Configuration

Checkpoint interval and behavior are controlled by:

- Hook: `hooks/auto-checkpoint.sh` (interval hardcoded at 300s / 5 minutes)
- Lib: `lib/checkpoint_manager.py` (configurable `interval_minutes` parameter)
- Rule: `rules/crash-recovery.md` (behavioral documentation)

## Metrics and Monitoring

- Checkpoint events are tracked via `.cognitive-os/checkpoints/*.json` files
- Session cleanup status in `.cognitive-os/sessions/.last-cleanup`
- Infra health checked by `hooks/infra-health.sh` on session start
- Task lifecycle tracked in `.cognitive-os/tasks/active-tasks.json`

## Manual Recovery Commands

```bash
# List checkpoint stashes
git stash list | grep cos-

# Apply most recent checkpoint stash
git stash apply

# Apply a specific checkpoint
git stash apply stash@{N}

# Discard checkpoint stashes (after recovery)
git stash drop stash@{N}

# List checkpoint metadata
ls -lt .cognitive-os/checkpoints/cos-*.json

# View specific checkpoint details
cat .cognitive-os/checkpoints/cos-YYYYMMDD-HHMMSS.json | python3 -m json.tool
```
