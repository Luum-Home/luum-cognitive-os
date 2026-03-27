# Session Concurrency

## Problem Statement

Development teams often have multiple IDE windows or terminal sessions open on the same project simultaneously. Without session isolation, concurrent Cognitive OS sessions can:

- Overwrite each other's task tracking state
- Produce interleaved metrics that are impossible to attribute
- Create race conditions when writing to shared files

This feature provides safe multi-session support with per-session isolation for mutable state and advisory file locking.

## Architecture

```
Session A (Claude Code Window 1)          Session B (Claude Code Window 2)
    |                                          |
    v                                          v
session-init.sh                           session-init.sh
    |                                          |
    v                                          v
.cognitive-os/sessions/                       .cognitive-os/sessions/
  1711234567-1234-a1b2/                     1711234590-5678-c3d4/
    tasks.json          (isolated)            tasks.json          (isolated)
    metrics/            (isolated)            metrics/            (isolated)
    meta.json           (isolated)            meta.json           (isolated)

           \                 /
            v               v
    .cognitive-os/sessions/
      active-sessions.json    (shared, flock-protected)
      locks/                  (shared, advisory)

           \                 /
            v               v
    .cognitive-os/
      skills/       (shared, read-only during session)
      rules/        (shared, read-only during session)
      metrics/      (shared, merged on session exit)
      cognitive-os.yaml (shared configuration)

           \                 /
            v               v
          Engram (shared, SQLite WAL mode)
```

## What Is Isolated vs Shared

### Isolated (Per-Session)

| Resource | Path | Purpose |
|----------|------|---------|
| Tasks | `sessions/{id}/tasks.json` | Session-specific task tracking |
| Metrics | `sessions/{id}/metrics/` | Skill metrics, error learning, auto-refine |
| Metadata | `sessions/{id}/meta.json` | Session PID, start time, hostname |

### Shared (Global)

| Resource | Path | Concurrency Safety |
|----------|------|--------------------|
| Skills | `skills/` | Read-only during sessions |
| Rules | `rules/` | Read-only during sessions |
| Global Metrics | `metrics/` | Append-only on session exit (merged from session) |
| Configuration | `cognitive-os.yaml` | Rarely modified; read at startup |
| Engram | SQLite DB | WAL mode handles concurrent reads + single writer |
| Active Sessions | `sessions/active-sessions.json` | Protected by `flock` |
| File Locks | `sessions/locks/` | Per-file advisory locks |

## How Engram Handles Concurrency

Engram uses SQLite with WAL (Write-Ahead Logging) mode, which provides:

- **Multiple concurrent readers**: Any number of sessions can read from Engram simultaneously
- **Single writer with no reader blocking**: Writes do not block reads
- **Automatic conflict resolution**: SQLite handles write serialization internally

No additional locking is needed for Engram access.

## File Locking

### Strategy: Advisory

File locking is advisory, meaning it warns but does not block. This design choice:

- Avoids deadlocks and stalled sessions
- Lets developers override when they know what they are doing
- Still provides visibility into potential conflicts

### Lock Lifecycle

1. Before Edit/Write: `concurrent-write-guard.sh` fires as a PreToolUse hook
2. Computes a hash of the file path
3. Checks `sessions/locks/{hash}.lock` for existing lock
4. If locked by another active session: prints WARN
5. If locked by same session: refreshes timestamp silently
6. If lock is stale (expired or dead PID): removes it
7. Acquires/refreshes lock for current session

### Lock File Format

```json
{
  "session_id": "1711234567-1234-a1b2",
  "pid": 12345,
  "file_path": "/path/to/file.go",
  "timestamp_epoch": 1711234567,
  "timestamp": "2024-03-23T10:00:00Z"
}
```

### Stale Lock Detection

A lock is considered stale if:

- `lock_timeout_seconds` has elapsed (default: 300 seconds / 5 minutes)
- The locking PID is no longer running (`kill -0 $PID` fails)

Stale locks are automatically removed when encountered.

## How to Debug Session Issues

### Check active sessions

Run `/sessions list` to see all registered sessions with their PIDs and start times.

### Find stale sessions

Run `/sessions cleanup` to remove sessions whose PIDs are no longer running.

### Check for lock conflicts

Look in `.cognitive-os/sessions/locks/` for `.lock` files. Each contains the session ID and file path.

### Verify session metrics

Session metrics live in `.cognitive-os/sessions/{id}/metrics/`. On clean exit, they are merged into `.cognitive-os/metrics/`.

### If metrics are missing after a crash

If a session crashes without running the Stop hook, its metrics remain in the session directory. Run `/sessions cleanup` or manually merge them.

## Configuration

In `cognitive-os.yaml`:

```yaml
sessions:
  concurrency: true                # Enable multi-session support
  isolation: per-session           # Each session gets own tasks/metrics
  lock_strategy: advisory          # Warn on conflicts, don't block
  lock_timeout_seconds: 300        # Lock auto-expiry (5 minutes)
  cleanup_on_exit: true            # Remove session dir on exit
  merge_metrics_on_exit: true      # Append session metrics to global
  max_concurrent: 10               # Maximum simultaneous sessions
```

## Limitations

- **Local file system only**: Locking uses `flock` and PID checks, which only work on a single machine. Distributed locking across networked file systems is not supported.
- **Advisory only**: File locking does not prevent writes. It is a best-effort warning system.
- **PID reuse**: In rare cases, a PID could be reused by the OS, causing a stale lock to appear active. The timeout-based expiry mitigates this.
- **Session ID discovery**: Hooks discover the session ID via environment variable or PID-based file lookup. If neither works (e.g., a sub-process with a different PID), the hook falls back to global behavior.
