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

# ── Capture hook input once, then replay it to the real hook ─────────────────
# Claude sends hook input JSON on stdin. We need to inspect SessionStart input
# before launching expensive/mutating hooks, but each hook still expects the
# original stdin. Capture only when stdin is a pipe/file; avoid blocking manual
# invocations from a TTY.
HOOK_INPUT_JSON=""
if [ ! -t 0 ]; then
  HOOK_INPUT_JSON="$(cat 2>/dev/null || true)"
fi

# Export normalized context for hooks that want to gate behavior without
# re-parsing stdin. In current Claude Code docs, SessionStart receives `source`,
# `model`, and optionally `agent_type`; SubagentStart receives `agent_id` and
# `agent_type`. Some subagent transcripts also live under a /subagents/ path.
# Treat any of those subagent indicators as a lightweight subagent session.
COGNITIVE_OS_SESSION_SOURCE=""
COGNITIVE_OS_HOOK_AGENT_TYPE=""
COGNITIVE_OS_HOOK_AGENT_ID=""
COGNITIVE_OS_SESSION_KIND="${COGNITIVE_OS_SESSION_KIND:-orchestrator}"
if [ -n "$HOOK_INPUT_JSON" ] && command -v python3 >/dev/null 2>&1; then
  _hook_meta=$(HOOK_INPUT_JSON="$HOOK_INPUT_JSON" python3 - <<'PYMETA' 2>/dev/null || true
import json, os
try:
    data = json.loads(os.environ.get("HOOK_INPUT_JSON", "") or "{}")
except Exception:
    data = {}
source = str(data.get("source") or "")
agent_type = str(data.get("agent_type") or "")
agent_id = str(data.get("agent_id") or "")
transcript = str(data.get("transcript_path") or "")
kind = "orchestrator"
if agent_id or "/subagents/" in transcript or (data.get("hook_event_name") == "SessionStart" and agent_type):
    kind = "subagent"
print("source=" + source.replace("\n", " "))
print("agent_type=" + agent_type.replace("\n", " "))
print("agent_id=" + agent_id.replace("\n", " "))
print("kind=" + kind)
PYMETA
)
  while IFS='=' read -r key value; do
    case "$key" in
      source) COGNITIVE_OS_SESSION_SOURCE="$value" ;;
      agent_type) COGNITIVE_OS_HOOK_AGENT_TYPE="$value" ;;
      agent_id) COGNITIVE_OS_HOOK_AGENT_ID="$value" ;;
      kind) COGNITIVE_OS_SESSION_KIND="$value" ;;
    esac
  done <<EOF_META
$_hook_meta
EOF_META
fi

if [ -n "${CLAUDE_SUBAGENT_ID:-${COS_SUBAGENT_ID:-}}" ]; then
  COGNITIVE_OS_SESSION_KIND="subagent"
fi
export COGNITIVE_OS_SESSION_SOURCE COGNITIVE_OS_HOOK_AGENT_TYPE COGNITIVE_OS_HOOK_AGENT_ID COGNITIVE_OS_SESSION_KIND

# ── Invoke the real hook ─────────────────────────────────────────────────────
# Stdin/stdout/stderr are forwarded unchanged unless we explicitly short-circuit
# a subagent SessionStart below. PreToolUse and SubagentStart stdout are part of
# the hook protocol, so this wrapper must remain transparent for normal hooks.
HOOK_NAME="$(basename "${HOOK_PATH%.sh}")"
HOOK_PID=$$
HOOK_SKIPPED=0
HOOK_SAFE_MODE=0
HOOK_SKIP_REASON=""
HOOK_BODY_DURATION_MS=0

# ── Startup circuit breaker / safe mode ─────────────────────────────────────
# SessionStart is the highest-risk event: hooks can mutate watched settings,
# launch daemons, acquire Git locks, and print model-visible context. If Claude
# Code re-spawns repeatedly, the wrapper must stop the chain centrally before
# individual hooks run. See ADR-101.
if [ "$EVENT_NAME" = "SessionStart" ] && [ "${COS_STARTUP_CIRCUIT_BREAKER_DISABLE:-0}" != "1" ] && command -v python3 >/dev/null 2>&1; then
  mkdir -p "$RUNTIME_DIR" 2>/dev/null || true
  _startup_cb_meta=$(RUNTIME_DIR="$RUNTIME_DIR" \
    COS_STARTUP_SAFE_MODE="${COS_STARTUP_SAFE_MODE:-0}" \
    COS_DISABLE_SESSIONSTART_HOOKS="${COS_DISABLE_SESSIONSTART_HOOKS:-0}" \
    COS_STARTUP_STORM_WINDOW_SECONDS="${COS_STARTUP_STORM_WINDOW_SECONDS:-20}" \
    COS_STARTUP_STORM_THRESHOLD="${COS_STARTUP_STORM_THRESHOLD:-3}" \
    COS_STARTUP_SAFE_MODE_TTL_SECONDS="${COS_STARTUP_SAFE_MODE_TTL_SECONDS:-300}" \
    python3 - <<'PYCIRCUIT' 2>/dev/null || true
import fcntl
import json
import os
import time
from pathlib import Path

runtime = Path(os.environ["RUNTIME_DIR"])
runtime.mkdir(parents=True, exist_ok=True)
events_dir = runtime / "startup-circuit-breaker"
events_dir.mkdir(parents=True, exist_ok=True)
events_file = events_dir / "events.jsonl"
lock_file = runtime / "startup-circuit-breaker.lock"
safe_file = runtime / "startup-safe-mode.json"
disable_file = runtime / "disable-sessionstart-hooks"

now = int(time.time())
reason = ""
safe = False
count = 0

def env_truth(name: str) -> bool:
    return os.environ.get(name, "") in {"1", "true", "TRUE", "yes", "on"}

def emit() -> None:
    print(f"safe_mode={1 if safe else 0}")
    print(f"reason={reason}")
    print(f"count={count}")

def activate(new_reason: str) -> None:
    global safe, reason
    safe = True
    reason = new_reason

if env_truth("COS_DISABLE_SESSIONSTART_HOOKS"):
    activate("manual_env_disable")
elif disable_file.exists():
    activate("manual_disable_file")
elif env_truth("COS_STARTUP_SAFE_MODE"):
    activate("env_safe_mode")
else:
    try:
        payload = json.loads(safe_file.read_text()) if safe_file.exists() else {}
        expires_at = int(payload.get("expires_at", 0))
        if expires_at > now:
            activate(str(payload.get("reason") or "startup_safe_mode"))
        elif safe_file.exists():
            safe_file.unlink(missing_ok=True)
    except Exception:
        try:
            safe_file.unlink(missing_ok=True)
        except Exception:
            pass

if not safe:
    try:
        threshold = int(os.environ.get("COS_STARTUP_STORM_THRESHOLD", "3"))
        window = int(os.environ.get("COS_STARTUP_STORM_WINDOW_SECONDS", "20"))
        ttl = int(os.environ.get("COS_STARTUP_SAFE_MODE_TTL_SECONDS", "300"))
    except ValueError:
        threshold, window, ttl = 3, 20, 300

    if threshold > 0 and window > 0 and ttl > 0:
        with open(lock_file, "w") as lock_fh:
            try:
                fcntl.flock(lock_fh, fcntl.LOCK_EX)
            except Exception:
                pass

            rows = []
            if events_file.exists():
                for line in events_file.read_text().splitlines():
                    try:
                        item = json.loads(line)
                    except Exception:
                        continue
                    ts = int(item.get("ts", 0))
                    if now - ts <= window:
                        rows.append(item)
            rows.append({"ts": now, "pid": os.getpid()})
            count = len(rows)
            events_file.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows))

            if count > threshold:
                payload = {
                    "activated_at": now,
                    "expires_at": now + ttl,
                    "reason": "startup_storm",
                    "window_seconds": window,
                    "threshold": threshold,
                    "count": count,
                }
                tmp = safe_file.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(payload, indent=2) + "\n")
                os.replace(tmp, safe_file)
                activate("startup_storm")

emit()
PYCIRCUIT
)
  while IFS='=' read -r key value; do
    case "$key" in
      safe_mode) HOOK_SAFE_MODE="$value" ;;
      reason) [ -n "$value" ] && HOOK_SKIP_REASON="$value" ;;
    esac
  done <<EOF_CIRCUIT
$_startup_cb_meta
EOF_CIRCUIT
fi

# Claude Code can fire the full SessionStart surface for subagent sessions. That
# is the wrong scope for COS: SubagentStart already handles subagent context,
# while SessionStart hooks do self-install, daemon launch, settings projection,
# and recovery work. Skipping here prevents 17x fan-out and settings/git races.
if [ "$EVENT_NAME" = "SessionStart" ] && [ "$HOOK_SAFE_MODE" = "1" ]; then
  HOOK_EXIT=0
  HOOK_SKIPPED=1
  [ -n "$HOOK_SKIP_REASON" ] || HOOK_SKIP_REASON="startup_safe_mode"
elif [ "$EVENT_NAME" = "SessionStart" ]   && [ "$COGNITIVE_OS_SESSION_KIND" = "subagent" ]   && [ "${COS_DISABLE_SUBAGENT_SESSIONSTART_SKIP:-0}" != "1" ]; then
  HOOK_EXIT=0
  HOOK_SKIPPED=1
  HOOK_SKIP_REASON="subagent_sessionstart"
else
  HOOK_BODY_START_MS=$(_now_ms)
  # For SessionStart/UserPromptSubmit, Claude Code treats stdout as model
  # context. Most COS hooks print human diagnostics, not intentional context;
  # leak them to stderr instead when invoked through the wrapper. Direct script
  # invocations keep their historical stdout for tests/operator debugging.
  QUARANTINE_STDOUT=0
  if [ "${COS_DISABLE_HOOK_STDOUT_QUARANTINE:-0}" != "1" ]; then
    case "$EVENT_NAME:$HOOK_NAME" in
      SessionStart:session-startup-protocol|SessionStart:session-resume)
        QUARANTINE_STDOUT=0
        ;;
      SessionStart:*|UserPromptSubmit:user-prompt-capture)
        QUARANTINE_STDOUT=1
        ;;
    esac
  fi

  if [ "$QUARANTINE_STDOUT" = "1" ]; then
    STDOUT_TMP="$(mktemp "${TMPDIR:-/tmp}/cos-hook-stdout.XXXXXX")"
    if [ ${#HOOK_ARGS[@]} -gt 0 ]; then
      printf '%s' "$HOOK_INPUT_JSON" | bash "$HOOK_PATH" "${HOOK_ARGS[@]}" >"$STDOUT_TMP"
    else
      printf '%s' "$HOOK_INPUT_JSON" | bash "$HOOK_PATH" >"$STDOUT_TMP"
    fi
    HOOK_EXIT=$?
    if [ -s "$STDOUT_TMP" ]; then
      cat "$STDOUT_TMP" >&2 || true
    fi
    rm -f "$STDOUT_TMP" 2>/dev/null || true
  else
    if [ ${#HOOK_ARGS[@]} -gt 0 ]; then
      printf '%s' "$HOOK_INPUT_JSON" | bash "$HOOK_PATH" "${HOOK_ARGS[@]}"
    else
      printf '%s' "$HOOK_INPUT_JSON" | bash "$HOOK_PATH"
    fi
    HOOK_EXIT=$?
  fi
  HOOK_BODY_END_MS=$(_now_ms)
  HOOK_BODY_DURATION_MS=$(( HOOK_BODY_END_MS - HOOK_BODY_START_MS ))
fi

# ── Record timing (best-effort) ──────────────────────────────────────────────
END_MS=$(_now_ms)
DURATION_MS=$(( END_MS - START_MS ))

# Escape hook name and event for JSON safety (no quotes or backslashes expected,
# but guard defensively).
SAFE_HOOK=$(printf '%s' "$HOOK_NAME" | tr -d '"\\')
SAFE_EVENT=$(printf '%s' "$EVENT_NAME" | tr -d '"\\')
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-}}}"
SAFE_SESSION=$(printf '%s' "$SESSION_ID" | tr -d '"\\')

SAFE_SKIP_REASON=$(printf '%s' "$HOOK_SKIP_REASON" | tr -d '"\\')

HOOK_SIGNAL=""
if [ "$HOOK_EXIT" -ge 128 ] 2>/dev/null; then
  HOOK_SIGNAL=$(( HOOK_EXIT - 128 ))
fi
if [ "$HOOK_SKIPPED" = "1" ]; then
  HOOK_EXECUTION_STATUS="skipped"
elif [ -n "$HOOK_SIGNAL" ]; then
  HOOK_EXECUTION_STATUS="signal"
elif [ "$HOOK_EXIT" -eq 0 ]; then
  HOOK_EXECUTION_STATUS="ok"
else
  HOOK_EXECUTION_STATUS="error"
fi

JSON_LINE="{\"timestamp\":\"$START_TS\",\"event\":\"$SAFE_EVENT\",\"hook\":\"$SAFE_HOOK\",\"duration_ms\":$DURATION_MS,\"body_duration_ms\":$HOOK_BODY_DURATION_MS,\"execution_status\":\"$HOOK_EXECUTION_STATUS\",\"exit_code\":$HOOK_EXIT,\"signal\":\"$HOOK_SIGNAL\",\"pid\":$HOOK_PID,\"session_id\":\"$SAFE_SESSION\",\"session_kind\":\"$COGNITIVE_OS_SESSION_KIND\",\"skipped\":$HOOK_SKIPPED,\"safe_mode\":$HOOK_SAFE_MODE,\"skip_reason\":\"$SAFE_SKIP_REASON\"}"

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
