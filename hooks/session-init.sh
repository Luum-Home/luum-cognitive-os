#!/usr/bin/env bash
# SCOPE: both
# SessionStart hook: Initialize session isolation
# Creates a unique session directory with isolated tasks and metrics.
# Registers the session in active-sessions.json with file locking.
# Must complete in <3 seconds.

set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
source "$(dirname "${BASH_SOURCE[0]}")/_lib/portable.sh"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions"
ACTIVE_FILE="$SESSIONS_DIR/active-sessions.json"
LOCKS_DIR="$SESSIONS_DIR/locks"

# Generate unique session ID: timestamp-PID-random
SESSION_ID="$(date +%s)-$$-$(head -c 4 /dev/urandom | od -An -tx1 | tr -d ' \n')"

# Create session directory structure
SESSION_DIR="$SESSIONS_DIR/$SESSION_ID"
mkdir -p "$SESSION_DIR/metrics"
mkdir -p "$LOCKS_DIR"

# Create empty session-scoped tasks file
echo "[]" > "$SESSION_DIR/tasks.json"

# Write session metadata
cat > "$SESSION_DIR/meta.json" <<EOF
{
  "session_id": "$SESSION_ID",
  "pid": $$,
  "start_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "start_epoch": $(date +%s),
  "working_directory": "$PROJECT_DIR",
  "hostname": "$(hostname -s 2>/dev/null || echo 'unknown')",
  "user": "$(whoami 2>/dev/null || echo 'unknown')"
}
EOF

# Register session in active-sessions.json with file locking
_register_session() {
  local lockfile="$SESSIONS_DIR/.active-sessions.lock"

  # Use flock for atomic read-modify-write
  (
    flock -w 5 200 || { echo "WARN: Could not acquire lock for session registration" >&2; return 1; }

    # Initialize if missing or invalid
    if [ ! -f "$ACTIVE_FILE" ] || ! jq empty "$ACTIVE_FILE" 2>/dev/null; then
      echo '{"sessions":[]}' > "$ACTIVE_FILE"
    fi

    # Prune stale sessions before counting. Without this, active-sessions.json
    # accumulates dead PIDs and makes concurrent-session diagnosis misleading.
    # TTL cache: only prune once per 60 s to avoid a cold Python start on every
    # SessionStart (the PYPRUNE heredoc was a top contributor to the 3.4s p95).
    _PRUNE_STAMP="$SESSIONS_DIR/.prune-last-run"
    _now_epoch=$(date +%s 2>/dev/null || echo 0)
    _last_prune=0
    [ -f "$_PRUNE_STAMP" ] && _last_prune=$(cat "$_PRUNE_STAMP" 2>/dev/null || echo 0)
    if [ $(( _now_epoch - _last_prune )) -ge 60 ]; then
      echo "$_now_epoch" > "$_PRUNE_STAMP" 2>/dev/null || true
    ACTIVE_FILE="$ACTIVE_FILE" python3 - <<'PYPRUNE' 2>/dev/null || true
import json, os, time
from datetime import datetime, timezone
from pathlib import Path

path = Path(os.environ["ACTIVE_FILE"])
try:
    data = json.loads(path.read_text())
except Exception:
    data = {"sessions": []}

sessions = data.get("sessions", [])
if not isinstance(sessions, list):
    sessions = []

now = time.time()
grace_seconds = int(os.environ.get("COS_ACTIVE_SESSION_PRUNE_GRACE_SECONDS", "900"))

def session_age_seconds(session):
    if not isinstance(session, dict):
        return 0
    start_epoch = session.get("start_epoch")
    if start_epoch is not None:
        try:
            return max(0, now - float(start_epoch))
        except Exception:
            pass
    start_time = session.get("start_time")
    if start_time:
        try:
            parsed = datetime.fromisoformat(str(start_time).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0, now - parsed.timestamp())
        except Exception:
            pass
    sid = str(session.get("id", ""))
    try:
        return max(0, now - float(sid.split("-", 1)[0]))
    except Exception:
        return grace_seconds + 1

def alive(pid):
    try:
        pid = int(pid)
    except Exception:
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False

data["sessions"] = [
    s for s in sessions
    if isinstance(s, dict) and (alive(s.get("pid")) or session_age_seconds(s) < grace_seconds)
]
path.write_text(json.dumps(data, indent=2) + "\n")
PYPRUNE
    fi  # end TTL-cache prune guard

    # Read max_concurrent from cognitive-os.yaml (default 10)
    MAX_CONCURRENT=10
    CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
    if [ -f "$CONFIG_FILE" ]; then
      PARSED_MAX=$(grep 'max_concurrent:' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*max_concurrent:[[:space:]]*//' | tr -d '[:space:]')
      if [[ "$PARSED_MAX" =~ ^[0-9]+$ ]]; then
        MAX_CONCURRENT="$PARSED_MAX"
      fi
    fi

    # Check current count
    CURRENT_COUNT=$(jq '.sessions | length' "$ACTIVE_FILE" 2>/dev/null || echo "0")
    if [ "$CURRENT_COUNT" -ge "$MAX_CONCURRENT" ]; then
      echo "WARN: Maximum concurrent sessions ($MAX_CONCURRENT) reached. Session registered but may degrade performance." >&2
    fi

    # Add this session
    jq --arg id "$SESSION_ID" \
       --arg pid "$$" \
       --arg start "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       --arg dir "$PROJECT_DIR" \
       '.sessions += [{"id": $id, "pid": ($pid | tonumber), "start_time": $start, "working_directory": $dir}]' \
       "$ACTIVE_FILE" > "$ACTIVE_FILE.tmp" && mv "$ACTIVE_FILE.tmp" "$ACTIVE_FILE"

  ) 200>"$lockfile"
}

_register_session

# Export session ID for downstream hooks.
# Child processes inherit this env var so session-cleanup.sh, error-pipeline.sh,
# git-context-capture.sh and other session-scoped writers can find the active
# session directory. Without the explicit export, COGNITIVE_OS_SESSION_ID was
# unset in hook subprocesses and 7 metrics files never landed on disk (ADR-028a §5.3).
export COGNITIVE_OS_SESSION_ID="$SESSION_ID"
export COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR"
echo ""
echo "=== COGNITIVE OS SESSION INITIALIZED ==="
echo "Session ID: $SESSION_ID"
echo "Session dir: $SESSION_DIR"
echo ""
echo "COGNITIVE_OS_SESSION_ID exported to child hooks."
echo ""

# ─── Previous state snapshot recovery ────────────────────────────────────────
# Surface orphaned state-snapshot.json recovery context on SessionStart before
# the new session continues. This keeps compaction/crash recovery visible across
# harnesses while leaving the dedicated crash-recovery hook as the implementation.
if [ -x "$(dirname "$0")/crash-recovery.sh" ]; then
  COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" bash "$(dirname "$0")/crash-recovery.sh" 2>/dev/null || true
fi

# ─── Level-1 skills catalog pointer ──────────────────────────────────────────
# LAZY-LOAD (default ON): CATALOG-COMPACT.md is NOT injected at SessionStart.
# Instead, hooks/lazy-catalog-injector.sh injects it on the first UserPromptSubmit
# that contains skill-related keywords. This saves ~3.5K tokens per session.
#
# To opt OUT of lazy-loading and restore eager injection at session start:
#   export COS_LAZY_CATALOG=0
#
# The env var is also set automatically by hooks/lazy-catalog-auto-revert.sh
# when the 24h suspected_missed_skills rate exceeds 2× baseline.
CATALOG_COMPACT="$PROJECT_DIR/skills/CATALOG-COMPACT.md"
if [ "${COS_LAZY_CATALOG:-1}" = "0" ]; then
  # Eager mode: inject now (opt-out of lazy-loading)
  if [ -f "$CATALOG_COMPACT" ]; then
    echo "Skills catalog: skills/CATALOG-COMPACT.md (run /catalog-full for details)"
    echo "[COS_LAZY_CATALOG=0] Eager catalog injection active."
  else
    echo "WARN: skills/CATALOG-COMPACT.md missing — run: python3 scripts/generate_compact_catalog.py" >&2
  fi
else
  # Lazy mode (default): catalog injected on first skill-related prompt
  if [ -f "$CATALOG_COMPACT" ]; then
    echo "Skills catalog available (lazy): catalog injected on first skill-related prompt."
    echo "Use /catalog-full for the full index, or mention any skill name to trigger injection."
  else
    echo "WARN: skills/CATALOG-COMPACT.md missing — run: python3 scripts/generate_compact_catalog.py" >&2
  fi
fi
echo ""

# Write session ID to a discoverable file so other hooks can read it
echo "$SESSION_ID" > "$SESSIONS_DIR/.current-session-$$"

# ─── Rich JSON context marker (ADR-088) ───────────────────────────────────────
# Writes .context-<pid>.json with session/kind/harness/parent_chain so that
# commit_provenance.py can resolve accurate attribution via PPID-chain lookup
# rather than env-var guessing (which fails when env is stripped by sub-shells).
# Fail-silent: if write_context_marker.py is unavailable the legacy plain-text
# marker above is still present as backwards-compat fallback.
# Fire write_context_marker in background — purely advisory, does not affect
# session startup and was a measurable contributor to the 3.4s p95 (cold start).
COGNITIVE_OS_SESSION_ID="$SESSION_ID" \
  python3 "$PROJECT_DIR/scripts/write_context_marker.py" orchestrator 2>/dev/null &

# ─── Prune stale context markers (ADR-088) ────────────────────────────────────
# Drop .context-<pid>.json files whose PID is no longer running OR that are
# older than 24 hours. Runs inline (< 50ms on typical repos) to keep the
# sessions dir tidy without a separate cron job.
python3 - <<'PRUNE_CONTEXT_MARKERS' 2>/dev/null || true
import os, time
from pathlib import Path

sessions_dir = Path(os.environ.get("COGNITIVE_OS_PROJECT_DIR", ".")) / ".cognitive-os" / "sessions"
max_age_seconds = 86400  # 24 hours
now = time.time()

def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but we can't signal it
    except OSError:
        return False

for marker in sessions_dir.glob(".context-*.json"):
    try:
        # Extract PID from filename .context-<pid>.json
        stem = marker.stem  # ".context-<pid>"
        pid = int(stem.split("-")[-1])
        age = now - marker.stat().st_mtime
        if not pid_alive(pid) or age > max_age_seconds:
            marker.unlink(missing_ok=True)
    except Exception:
        pass
PRUNE_CONTEXT_MARKERS

# ─── Self-improve + user model + work queue (consolidated) ────────────────────
# Consolidated into a single python3 call (was 3 cold starts).
SELF_IMPROVE_FLAG="$PROJECT_DIR/.cognitive-os/metrics/.self-improve-recommended" \
SESSION_DIR="$SESSION_DIR" \
COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
python3 "$(dirname "$0")/_lib/session_init_helper.py" 2>/dev/null || true

# ─── Singularity auto-suggestion ─────────────────────────────────────────────
# Advisory only — always exits 0. Lightweight file checks only (no subprocess).
# Function is extracted to _lib/singularity-suggestion.sh so tests can source
# it directly without running the full hook.
source "$(dirname "$0")/_lib/singularity-suggestion.sh"

_singularity_suggestion

# ─── Test baseline capture — DISABLED 2026-04-17 ─────────────────────────────
# WS11 baseline capture DISABLED — orphaning bug, see ADR-028 (commit 1b755cf = Bug 1 source).
# Ran `pytest` on every session start. Full-suite runs leaked ~190 orphaned
# processes holding ~300 MiB.
# Anti-confirmation-bias goal preserved via global-verify.sh; see docs/adrs/ADR-028a.md §1.
echo "baseline: disabled (see ADR-028a §1)" > "$SESSION_DIR/test-baseline.txt"

# ─── Pending-task reminder ─────────────────────────────────────────────────────
# Advisory nudge at session start: if the work-queue has active P1-P5 items
# still marked pending, remind the orchestrator to inspect them via the
# canonical skills. Does NOT auto-invoke — orchestrator or user decides.
# Fail-silent: any jq/path issue is ignored (exit 0 contract).
_WORK_QUEUE="$PROJECT_DIR/.cognitive-os/work-queue.json"
if [ -f "$_WORK_QUEUE" ] && command -v jq >/dev/null 2>&1; then
  _pending_count=$(jq '[.priority_queue[]? | select(.status=="pending")] | length' "$_WORK_QUEUE" 2>/dev/null || echo 0)
  _parked_count=$(jq '[.parked[]?] | length' "$_WORK_QUEUE" 2>/dev/null || echo 0)
  if [ "${_pending_count:-0}" -gt 0 ] 2>/dev/null; then
    echo "" >&2
    echo "📋 Pending tasks detected ($_pending_count active, $_parked_count parked)." >&2
    echo "   Inspect:  /session-backlog   (full P1-P5 list with first steps)" >&2
    echo "   Resume:   /resume-tasks      (re-launch any in-progress from last session)" >&2
    echo "   Report:   /session-report-executive" >&2
    echo "" >&2
  fi
fi

# Work queue check moved to _lib/session_init_helper.py (consolidated above)

# ─── Commit-nudge banner (ADR-030 Q2) ─────────────────────────────────────────
_NUDGE_FILE="$PROJECT_DIR/.cognitive-os/runtime/commit-nudge"
_NUDGE_STALE_HOURS="${COMMIT_NUDGE_STALE_HOURS:-24}"
if [ -f "$_NUDGE_FILE" ]; then
    # Filter: only commits from the last N hours (mtime-based)
    _now=$(date +%s)
    _mtime=$(portable_stat_mtime "$_NUDGE_FILE" 2>/dev/null || echo "$_now")
    _age_hours=$(( (_now - _mtime) / 3600 ))
    if [ "$_age_hours" -le "$_NUDGE_STALE_HOURS" ]; then
        _commit_count=$(wc -l < "$_NUDGE_FILE" 2>/dev/null | tr -d ' ')
        _latest=$(tail -1 "$_NUDGE_FILE" 2>/dev/null)
        if [ "${_commit_count:-0}" -gt 0 ]; then
            echo "" >&2
            echo "📋 Commits since last wrapup: $_commit_count." >&2
            echo "   Latest: $_latest" >&2
            echo "   Invoke /session-wrapup to archive today's work." >&2
            echo "" >&2
        fi
    fi
fi

exit 0
