#!/usr/bin/env bash
# SCOPE: both
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
if [ "${COS_DISABLE_PROFILE_AUTOAPPLY:-0}" = "1" ]; then
    exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
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

# ── Acquire non-blocking flock; concurrent invocations exit 0 silently ──────
# flock requires a file descriptor open on the lock file. exec 9>... opens fd 9
# for writing without truncating existing content (the lock file is opaque).
# `flock -n 9` returns immediately: 0 if acquired, 1 if another holder exists.
# When `flock` itself is unavailable, fall through to the direct path; this is
# the macOS-without-util-linux scenario, accepted because the race window is
# narrow enough to be a soft hazard rather than a hard incident.
exec 9>"$LOCK_FILE"
if command -v flock &>/dev/null; then
    if ! flock -n 9; then
        # Another process is already re-applying. No-op.
        exit 0
    fi
fi
# Lock held until process exit (fd 9 closes automatically).

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
