#!/usr/bin/env bash
# SCOPE: os-only
# edit-lock-process-negotiations.sh — ADR-098 Phase D2: surface incoming lock negotiations
#
# Heartbeat-driven: registered under UserPromptSubmit (which fires on every
# user interaction, giving a "heartbeat-like" periodic signal without requiring
# a separate cron). Also works as a Stop hook.
#
# For each lock owned by THIS session, checks
#   .cognitive-os/runtime/edit-negotiations/<my-session>/
# for incoming request YAML files from other sessions. For each:
#   - Surface to stderr in a structured format the agent can act on
#   - Mark as "seen" by appending  seen_at: <iso>  to the request YAML
#   - Does NOT auto-grant — surface only
#
# Idempotent: already-seen requests (seen_at present) are skipped silently.
# Graceful: missing dirs / missing primitive → exit 0.
set -uo pipefail
source "$(dirname "$0")/../scripts/_lib/session-id.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

# ── Identity helpers ──────────────────────────────────────────────────────────
_session_id() {
  cos_session_id
}

_iso8601() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# ── Runtime dirs ──────────────────────────────────────────────────────────────
RUNTIME="$PROJECT_DIR/.cognitive-os/runtime"
NEGOTIATIONS_ROOT="$RUNTIME/edit-negotiations"
ME="$(_session_id)"
MY_INBOX="$NEGOTIATIONS_ROOT/$ME"

[ -d "$MY_INBOX" ] || exit 0   # no inbox → nothing to process

# ── Also verify this session actually holds at least one lock ─────────────────
# (Light check — avoids emitting noise when session has no active locks)
LOCKS_ROOT="$RUNTIME/edit-locks"
has_lock=0
if [ -d "$LOCKS_ROOT" ]; then
  for lock_meta in "$LOCKS_ROOT"/*/meta.yaml; do
    [ -f "$lock_meta" ] || continue
    holder="$(sed -n 's/^session_id: *"\(.*\)"$/\1/p' "$lock_meta" | head -1)"
    if [ "$holder" = "$ME" ]; then
      has_lock=1
      break
    fi
  done
fi

# We still process even with no locks (the request might be for a file we
# previously held), but emit a note.
if [ "$has_lock" -eq 0 ]; then
  echo "[edit-lock-process-negotiations] session=$ME has no active locks; processing inbox anyway" >&2
fi

# ── Process each incoming request ─────────────────────────────────────────────
processed=0
skipped_seen=0

for req_file in "$MY_INBOX"/*.yaml "$MY_INBOX"/*.yml; do
  [ -f "$req_file" ] || continue

  # Check if already seen (idempotent).
  if grep -q "^seen_at:" "$req_file" 2>/dev/null; then
    skipped_seen=$(( skipped_seen + 1 ))
    continue
  fi

  # Extract structured fields for the surface report.
  requester="$(sed -n 's/^requester_session: *"\(.*\)"$/\1/p' "$req_file" | head -1)"
  target_file="$(sed -n 's/^target_file: *"\(.*\)"$/\1/p' "$req_file" | head -1)"
  intent="$(sed -n 's/^intent: *"\(.*\)"$/\1/p' "$req_file" | head -1)"
  purpose="$(sed -n 's/^purpose: *"\(.*\)"$/\1/p' "$req_file" | head -1)"
  requested_at="$(sed -n 's/^requested_at: *"\(.*\)"$/\1/p' "$req_file" | head -1)"

  now="$(_iso8601)"

  # Surface to stderr in a structured, agent-readable format.
  cat >&2 <<EOF
EDIT-LOCK NEGOTIATION REQUEST (ADR-098)
  Request file:   $req_file
  From session:   ${requester:-unknown}
  Wants to edit:  ${target_file:-unknown}
  Intent:         ${intent:-unspecified}
  Purpose:        ${purpose:-unspecified}
  Requested at:   ${requested_at:-unknown}

  ACTION REQUIRED (do NOT auto-grant — decide manually):
    GRANT:   Run  bash scripts/edit-coop.sh release "${target_file:-<file>}"
             then notify session $requester that it may proceed.
    DEFER:   Append a denial reason to $req_file and continue.
    IGNORE:  Take no action; requester will retry on next heartbeat.

EOF

  # Mark as seen by appending seen_at field.
  printf 'seen_at: "%s"\n' "$now" >> "$req_file"
  echo "[edit-lock-process-negotiations] marked seen: $req_file" >&2

  processed=$(( processed + 1 ))
done

if [ "$processed" -gt 0 ]; then
  echo "[edit-lock-process-negotiations] surfaced $processed negotiation request(s)" >&2
fi
if [ "$skipped_seen" -gt 0 ]; then
  echo "[edit-lock-process-negotiations] skipped $skipped_seen already-seen request(s)" >&2
fi

exit 0
