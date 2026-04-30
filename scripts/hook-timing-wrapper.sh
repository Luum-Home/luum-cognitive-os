#!/usr/bin/env bash
# ROLE: instrumentation
# CANONICAL: scripts/hook-timing-wrapper.sh
# hook-timing-wrapper.sh — Trampoline that records per-invocation hook timing
#
# Every hook command in settings.json runs through this wrapper. It logs a
# structured JSONL record to .cognitive-os/metrics/hook-timing.jsonl with the
# harness event name, hook name, wall-clock duration, exit code, and PID.
# By default it does not emit hook summaries to stderr and does not touch the
# FIFO. Hook invocations may run async and outlive the harness-side reader; any
# inherited stdout/stderr/FIFO write can leak an orphaned wrapper process.
#
# Usage:
#   bash scripts/hook-timing-wrapper.sh <event_name> <hook_path> [args...]
#
# Environment:
#   COS_HOOK_TIMING_DISABLE=1   — bypass wrapper entirely (no logging, no fork)
#   COS_HOOK_TIMING_VERBOSE=1   — emit stderr summary (JSONL still written)
#   COS_HOOK_TIMING_FIFO=1      — write to hook-stream.fifo (best-effort)
#   COGNITIVE_OS_PROJECT_DIR     — canonical project root override
#   CODEX_PROJECT_DIR            — Codex project root
#   CLAUDE_PROJECT_DIR           — Claude Code project root
#
# Design constraints:
#   - NEVER block or fail the hook chain; all logging is best-effort
#   - stdout from the real hook MUST be passed through unchanged (for PreToolUse
#     additionalContext protocol)
#   - stderr from the real hook is forwarded to our stderr
#   - wrapper's own stderr/FIFO reporting is opt-in to avoid orphan leaks
#   - Overhead target: <10ms median on macOS without GNU coreutils

set -uo pipefail

# ── Kill-switch: bypass immediately ─────────────────────────────────────────
if [ "${COS_HOOK_TIMING_DISABLE:-}" = "1" ]; then
  shift  # drop event_name
  exec "$@"  # directly exec the hook (zero overhead)
fi

# ── Parse args ───────────────────────────────────────────────────────────────
if [ $# -lt 2 ]; then
  echo "hook-timing-wrapper: usage: <event_name> <hook_path> [args...]" >&2
  exit 1
fi

EVENT_NAME="$1"
HOOK_PATH="$2"
shift 2
HOOK_ARGS=("$@")

# ── Resolve metrics path ─────────────────────────────────────────────────────
PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-}}}"
if [ -z "$PROJECT_DIR" ]; then
  # Minimal fallback: walk up to find the repo root (cwd at hook invocation time
  # is the project root per harness contract, but be defensive).
  PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
TIMING_LOG="$METRICS_DIR/hook-timing.jsonl"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
FIFO_PATH="$RUNTIME_DIR/hook-stream.fifo"

# Ensure metrics dir exists (best-effort; don't fail wrapper if this errors)
[ -d "$METRICS_DIR" ] || mkdir -p "$METRICS_DIR" 2>/dev/null || true
# FIFO setup is opt-in. Async hooks can outlive the harness reader, so touching
# inherited streams or FIFOs by default is unsafe.
if [ "${COS_HOOK_TIMING_FIFO:-}" = "1" ] && [ ! -p "$FIFO_PATH" ]; then
  mkdir -p "$RUNTIME_DIR" 2>/dev/null || true
  mkfifo "$FIFO_PATH" 2>/dev/null || true
fi

# ── Millisecond-precision wall-clock ────────────────────────────────────────
# macOS ships BSD date which lacks %N (nanoseconds). Strategy:
#   1. python3 -c "import time; print(int(time.time()*1000))" — always available
#   2. gdate +%s%3N — if GNU coreutils installed via Homebrew
#   3. date +%s × 1000 — second precision fallback (1000ms granularity)
_now_ms() {
  python3 -c "import time; print(int(time.time()*1000))" 2>/dev/null \
    || { gdate +%s%3N 2>/dev/null; } \
    || echo $(( $(date +%s) * 1000 ))
}

START_MS=$(_now_ms)
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)

# ── Invoke the real hook ─────────────────────────────────────────────────────
# Stdin is forwarded. Stdout is forwarded (critical for PreToolUse
# additionalContext: the harness reads hook stdout as structured JSON).
# We capture the exit code but never suppress output.
HOOK_NAME="$(basename "${HOOK_PATH%.sh}")"
HOOK_PID=$$

# Run hook; forward stdin/stdout/stderr unchanged.
if [ ${#HOOK_ARGS[@]} -gt 0 ]; then
  bash "$HOOK_PATH" "${HOOK_ARGS[@]}"
else
  bash "$HOOK_PATH"
fi
HOOK_EXIT=$?

# ── Record timing (best-effort) ──────────────────────────────────────────────
END_MS=$(_now_ms)
DURATION_MS=$(( END_MS - START_MS ))

# Escape hook name and event for JSON safety (no quotes or backslashes expected,
# but guard defensively).
SAFE_HOOK=$(printf '%s' "$HOOK_NAME" | tr -d '"\\')
SAFE_EVENT=$(printf '%s' "$EVENT_NAME" | tr -d '"\\')
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-}}}"
SAFE_SESSION=$(printf '%s' "$SESSION_ID" | tr -d '"\\')

JSON_LINE="{\"timestamp\":\"$START_TS\",\"event\":\"$SAFE_EVENT\",\"hook\":\"$SAFE_HOOK\",\"duration_ms\":$DURATION_MS,\"exit_code\":$HOOK_EXIT,\"pid\":$HOOK_PID,\"session_id\":\"$SAFE_SESSION\"}"

# Append to JSONL — redirect all errors to /dev/null so a full disk or
# read-only filesystem never breaks the hook chain.
echo "$JSON_LINE" >> "$TIMING_LOG" 2>/dev/null || true

# ── Human-readable stderr summary ───────────────────────────────────────────
# Format: [hook] <basename> <event> <duration_ms>ms <status> [⚠ if slow]
# Disabled by default: async/orphaned hooks can block forever on inherited
# stderr sockets after the harness reader exits. Use COS_HOOK_TIMING_VERBOSE=1
# only for short local debugging sessions.
if [ "${COS_HOOK_TIMING_VERBOSE:-}" = "1" ]; then
  if [ "$HOOK_EXIT" -eq 0 ]; then
    STATUS_STR="ok"
  else
    STATUS_STR="FAIL($HOOK_EXIT)"
  fi
  SLOW_MARKER=""
  [ "$DURATION_MS" -ge 1000 ] && SLOW_MARKER=" ⚠"
  SUMMARY_LINE="[hook] $HOOK_NAME $EVENT_NAME ${DURATION_MS}ms $STATUS_STR$SLOW_MARKER"
  printf '%s\n' "$SUMMARY_LINE" >&2
fi

# ── FIFO write (non-blocking, best-effort) ───────────────────────────────────
# Use Python's os.O_NONBLOCK because POSIX shell redirection to a FIFO can block
# forever when no reader is attached. If no reader exists, the write is dropped.
if [ "${COS_HOOK_TIMING_FIFO:-}" = "1" ] && [ -p "$FIFO_PATH" ]; then
  FIFO_PATH="$FIFO_PATH" FIFO_LINE="${SUMMARY_LINE:-[hook] $HOOK_NAME $EVENT_NAME ${DURATION_MS}ms}" python3 - <<'PYFIFO' 2>/dev/null || true
import os

path = os.environ["FIFO_PATH"]
line = os.environ["FIFO_LINE"] + "\n"
fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
try:
    os.write(fd, line.encode("utf-8", errors="replace"))
finally:
    os.close(fd)
PYFIFO
fi

# ── Return the hook's exit code ──────────────────────────────────────────────
exit $HOOK_EXIT
