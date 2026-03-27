# Session Concurrency

## Overview

The Cognitive OS supports multiple concurrent Claude Code (or other IDE) sessions working on the same project. Each session is isolated for tasks and metrics, while sharing skills, rules, and Engram.

## How It Works

### Session Lifecycle

1. **SessionStart**: `session-init.sh` generates a unique session ID, creates `sessions/{id}/` with isolated `tasks.json` and `metrics/`, and registers in `active-sessions.json`.
2. **During session**: Hooks write metrics to session-scoped directories. File writes trigger advisory lock checks via `concurrent-write-guard.sh`.
3. **Stop**: `session-cleanup.sh` merges session metrics into global, deregisters from `active-sessions.json`, releases locks, and optionally removes the session directory.

### What Is Isolated (Per-Session)

- `sessions/{id}/tasks.json` -- task tracking
- `sessions/{id}/metrics/` -- skill metrics, error learning, auto-refine state
- `sessions/{id}/meta.json` -- session metadata (PID, start time, working directory)

### What Is Shared (Global)

- **Skills** (`skills/`) -- all sessions share the same skill definitions
- **Rules** (`rules/`) -- all sessions share the same rules
- **Engram** -- persistent memory is shared; Engram uses SQLite WAL mode which supports concurrent readers and a single writer safely
- **Configuration** (`cognitive-os.yaml`) -- shared configuration
- **Global metrics** (`metrics/`) -- session metrics are merged here on exit

## File Locking

Advisory file locking prevents accidental overwrites when two sessions edit the same file.

### Mechanism

- Before any Edit/Write, `concurrent-write-guard.sh` checks `sessions/locks/{file-hash}.lock`
- Lock contains: session ID, PID, file path, timestamp
- If another session holds the lock: **WARN** (advisory only, does NOT block)
- If same session holds the lock: silently refresh
- Locks auto-expire after `lock_timeout_seconds` (default: 300s)
- Stale locks (expired or PID dead) are automatically cleaned

### What To Do If You See a Lock Warning

1. The warning means another session is editing the same file
2. Your write will still proceed -- it is advisory only
3. Coordinate with the other session to avoid conflicting changes
4. If the other session is no longer active, the lock will auto-expire or you can run `/sessions cleanup`

## Configuration

In `cognitive-os.yaml`:

```yaml
sessions:
  concurrency: true
  isolation: per-session
  lock_strategy: advisory
  lock_timeout_seconds: 300
  cleanup_on_exit: true
  merge_metrics_on_exit: true
  max_concurrent: 10
```

## Session Management

Use `/sessions` to manage sessions:

- `/sessions list` -- show all active sessions
- `/sessions current` -- show current session info
- `/sessions cleanup` -- remove stale sessions (dead PIDs)
