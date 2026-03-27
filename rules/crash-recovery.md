# Crash Recovery Protocol

## Purpose

Uncommitted work MUST survive crashes, power loss, OOM kills, and network failures. The auto-checkpoint system acts as a Write-Ahead Log (WAL) for the Cognitive OS.

## How It Works

1. The `auto-checkpoint.sh` PostToolUse hook runs on every Bash, Edit, and Write tool use.
2. It checks a timestamp marker; if fewer than 5 minutes have elapsed, it exits immediately (< 1ms overhead).
3. When the interval has elapsed and dirty files exist, it creates a named git stash (`cos-YYYYMMDD-HHMMSS`) and immediately pops it, leaving the working directory unchanged. The stash survives in `.git/refs/stash` even through crashes.
4. Checkpoint metadata (timestamp, dirty file count) is saved to `.cognitive-os/checkpoints/{id}.json`.

## Session Start Recovery

The `crash-recovery.sh` SessionStart hook detects orphaned checkpoint stashes:
- Searches `git stash list` for `cos-` entries
- Reports stash count and last checkpoint metadata
- Suggests restore, discard, or resume actions

## Key Guarantees

- Uncommitted work is recoverable from git stash after any crash scenario
- Checkpoint metadata persists alongside stashes for context
- The hook is lightweight: timestamp check exits in < 1ms on non-checkpoint runs
- No interference with normal git workflow (stash push + pop is transparent)

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Interval | 5 minutes | Time between checkpoints |
| Marker | `.cognitive-os/checkpoints/.last-checkpoint` | Timestamp file |
| Metadata | `.cognitive-os/checkpoints/cos-*.json` | Checkpoint records |

## Integration

- **Lib**: `lib/checkpoint_manager.py` provides the Python API for checkpoint operations
- **Hook (PostToolUse)**: `hooks/auto-checkpoint.sh` on Bash, Edit, Write
- **Hook (SessionStart)**: `hooks/crash-recovery.sh` detects orphaned stashes
- **Fault Tolerance**: Extends Tier 4 (Agent Resilience) with periodic checkpoints
