#!/usr/bin/env bash
# SCOPE: os-only
# PURPOSE: Auto-reapply efficiency profile when apply-efficiency-profile.sh changes
# EVENT: SessionStart
# EXIT_CODES: 0=advisory (always)
#
# Hooks registered in scripts/apply-efficiency-profile.sh are dormant until the script
# is re-run. After a pull or a checkout that adds/removes hooks (e.g. ADR-071 added
# engram-reinforce-on-access.sh + engram-crystallize-on-session-end.sh), settings.json
# stays out of date until the operator manually runs `bash scripts/apply-efficiency-profile.sh`.
#
# This hook computes a SHA256 of the script and compares it to the last applied hash
# stored in .cognitive-os/runtime/last-applied-profile.sha. On mismatch, it re-applies
# the profile silently. Advisory only — never blocks session start. Output to stderr
# so it surfaces in the session log without polluting stdout.
#
# Opt-out: COS_DISABLE_PROFILE_AUTOAPPLY=1
# Force-once: rm .cognitive-os/runtime/last-applied-profile.sha
#
# Concurrency (incident 2026-05-01-session-3-spawn-hang): when N parallel sub-agents
# all fire SessionStart simultaneously and the hash is stale, all N detect drift and
# concurrently call apply-efficiency-profile.sh, racing to write .claude/settings.json.
# The IDE detects the partial writes and re-spawns the session, which fires another
# round of SessionStart hooks. Mitigation: non-blocking flock on a runtime lock file —
# the first invocation re-applies; the others exit 0 silently. Combined with the
# atomic write in apply-efficiency-profile.sh this eliminates the partial-write race.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# Opt-out
if [ "${COS_DISABLE_PROFILE_AUTOAPPLY:-0}" = "1" ] || [ "${COS_VALIDATION_MODE:-0}" = "1" ]; then
    exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"

VALIDATION_LOCK_LIB="$(dirname "${BASH_SOURCE[0]}")/_lib/validation-lock.sh"
if [ -f "$VALIDATION_LOCK_LIB" ]; then
    # shellcheck source=/dev/null
    source "$VALIDATION_LOCK_LIB"
    if cos_validation_lock_active "$PROJECT_DIR"; then
        echo "[profile-drift-autoapply] validation capsule active; skipping settings mutation" >&2
        exit 0
    fi
fi
SCRIPT_PATH="$PROJECT_DIR/scripts/apply-efficiency-profile.sh"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
HASH_FILE="$RUNTIME_DIR/last-applied-profile.sha"
LOCK_FILE="$RUNTIME_DIR/profile-autoapply.lock"
LOG_FILE="$RUNTIME_DIR/profile-autoapply.log"

# Skip if the script doesn't exist (not a cos repo, or fresh clone before bootstrap)
if [ ! -f "$SCRIPT_PATH" ]; then
    exit 0
fi

mkdir -p "$RUNTIME_DIR"

# ── Compute current hash (sha256 with portable fallback) ────────────────────
if command -v sha256sum &>/dev/null; then
    current_hash=$(sha256sum "$SCRIPT_PATH" | awk '{print $1}')
elif command -v shasum &>/dev/null; then
    current_hash=$(shasum -a 256 "$SCRIPT_PATH" | awk '{print $1}')
else
    # No SHA tool — silently skip (advisory anyway)
    exit 0
fi

# ── Acquire non-blocking lock; concurrent invocations exit 0 silently ───────
# Prefer util-linux flock when present. macOS does not ship flock, so fall back
# to a Python fcntl lock holder process that keeps the advisory lock until this
# shell exits.
exec 9>"$LOCK_FILE"
if command -v flock &>/dev/null; then
    if ! flock -n 9; then
        exit 0
    fi
else
    lock_status="$RUNTIME_DIR/profile-autoapply.lock.status.$$"
    rm -f "$lock_status"
    python3 - "$LOCK_FILE" "$lock_status" "$$" <<'PYLOCK' &
import fcntl
import os
import sys
import time
from pathlib import Path

lock_path, status_path, parent_pid = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
handle = open(lock_path, "a", encoding="utf-8")
try:
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    status_path.write_text("busy", encoding="utf-8")
    sys.exit(0)
status_path.write_text("acquired", encoding="utf-8")
while True:
    try:
        os.kill(parent_pid, 0)
    except OSError:
        break
    time.sleep(0.1)
PYLOCK
    lock_pid=$!
    while [ ! -f "$lock_status" ] && kill -0 "$lock_pid" 2>/dev/null; do
        sleep 0.02
    done
    lock_result="$(cat "$lock_status" 2>/dev/null || echo busy)"
    rm -f "$lock_status"
    if [ "$lock_result" != "acquired" ]; then
        wait "$lock_pid" 2>/dev/null || true
        exit 0
    fi
    trap 'kill "$lock_pid" 2>/dev/null || true; wait "$lock_pid" 2>/dev/null || true' EXIT
fi
# Lock held until process exit.

# ── Compare with last applied (re-read UNDER LOCK to avoid TOCTOU) ──────────
last_hash=""
if [ -f "$HASH_FILE" ]; then
    last_hash=$(cat "$HASH_FILE" 2>/dev/null || echo "")
fi

if [ "$current_hash" = "$last_hash" ]; then
    # No drift — nothing to do (someone else may have just applied while we waited)
    exit 0
fi

# ── Drift detected: re-apply ────────────────────────────────────────────────
ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "[profile-drift-autoapply] $ts: hash drift detected, re-applying profile" >>"$LOG_FILE"

if bash "$SCRIPT_PATH" >>"$LOG_FILE" 2>&1; then
    echo "$current_hash" >"$HASH_FILE"
    echo "[profile-drift-autoapply] $ts: re-applied OK, hash recorded" >>"$LOG_FILE"
    echo "[profile-drift-autoapply] efficiency profile re-applied (settings.json updated)" >&2
else
    echo "[profile-drift-autoapply] $ts: re-apply FAILED, leaving hash file as-is" >>"$LOG_FILE"
    echo "[profile-drift-autoapply] re-apply failed — see $LOG_FILE" >&2
fi

exit 0
