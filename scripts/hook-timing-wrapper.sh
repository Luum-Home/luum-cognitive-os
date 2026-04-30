#!/usr/bin/env bash
# ROLE: instrumentation
# CANONICAL: scripts/hook-timing-wrapper.sh
# hook-timing-wrapper.sh — Trampoline that records per-invocation hook timing
#
# Every hook command in settings.json runs through this wrapper. It logs a
# structured JSONL record to .cognitive-os/metrics/hook-timing.jsonl with the
# harness event name, hook name, wall-clock duration, exit code, and PID.
#
# Usage:
#   bash scripts/hook-timing-wrapper.sh <event_name> <hook_path> [args...]
#
# Environment:
#   COS_HOOK_TIMING_DISABLE=1   — bypass wrapper entirely (no logging, no fork)
#   CLAUDE_PROJECT_DIR           — used to locate metrics dir (required by all hooks)
#
# Design constraints:
#   - NEVER block or fail the hook chain; all logging is best-effort
#   - stdout from the real hook MUST be passed through unchanged (for PreToolUse
#     additionalContext protocol)
#   - stderr from the real hook is forwarded to our stderr
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
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-}}"
if [ -z "$PROJECT_DIR" ]; then
  # Minimal fallback: walk up to find the repo root (cwd at hook invocation time
  # is the project root per harness contract, but be defensive).
  PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
TIMING_LOG="$METRICS_DIR/hook-timing.jsonl"

# Ensure metrics dir exists (best-effort; don't fail wrapper if this errors)
[ -d "$METRICS_DIR" ] || mkdir -p "$METRICS_DIR" 2>/dev/null || true

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

JSON_LINE="{\"timestamp\":\"$START_TS\",\"event\":\"$SAFE_EVENT\",\"hook\":\"$SAFE_HOOK\",\"duration_ms\":$DURATION_MS,\"exit_code\":$HOOK_EXIT,\"pid\":$HOOK_PID}"

# Append to JSONL — redirect all errors to /dev/null so a full disk or
# read-only filesystem never breaks the hook chain.
echo "$JSON_LINE" >> "$TIMING_LOG" 2>/dev/null || true

# ── Return the hook's exit code ──────────────────────────────────────────────
exit $HOOK_EXIT
