#!/usr/bin/env bash
# SCOPE: both
# edit-lock-drain-parked.sh — ADR-098 Phase D1: parked-edit drain notification
#
# PostToolUse[Edit|Write] hook (also usable as a Stop hook).
#
# When this session releases a lock on file X — or after every edit so that
# parked edits are surfaced promptly — scan
#   .cognitive-os/runtime/parked-edits/
# for any SIBLING session's parked edit on the same file. If found:
#   - Log discovery to stderr (discovery only; user/orchestrator approves apply)
#   - Touch a marker file under
#       .cognitive-os/runtime/parked-edits-pending/<parked-session>/<safe-file>.notice
#     so that session sees it on its next interaction.
#
# Idempotent: touching an existing marker is a no-op.
# Graceful: missing primitive or runtime dirs → exit 0.
#
# Bypass: COS_BYPASS_EDIT_LOCK=1 suppresses this hook too.
set -uo pipefail
source "$(dirname "$0")/../scripts/_lib/session-id.sh"

[ "${COS_BYPASS_EDIT_LOCK:-}" = "1" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

# ── Identity helpers ──────────────────────────────────────────────────────────
_session_id() {
  cos_session_id
}

_safe_path() {
  printf '%s' "$1" | sed 's|/|--|g; s|\.\.||g'
}

# ── Runtime dirs ──────────────────────────────────────────────────────────────
RUNTIME="$PROJECT_DIR/.cognitive-os/runtime"
PARKED_ROOT="$RUNTIME/parked-edits"
PENDING_ROOT="$RUNTIME/parked-edits-pending"

[ -d "$PARKED_ROOT" ] || exit 0   # nothing parked → nothing to drain

ME="$(_session_id)"

# ── Determine which file(s) were just edited ──────────────────────────────────
# PostToolUse receives the tool result JSON on stdin. We try to extract the
# file_path the same way the pre-tool hook does.
input="$(cat 2>/dev/null || true)"
edited_file=""
if [ -n "$input" ]; then
  edited_file="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
# PostToolUse envelope: {"tool_input":{"file_path":"..."}, "tool_response":...}
ti = data.get("tool_input") or {}
fp = ti.get("file_path") or ti.get("path") or ""
if fp:
    print(fp)
' 2>/dev/null)"
fi

# Normalise to repo-relative.
if [ -n "$edited_file" ]; then
  case "$edited_file" in
    "$PROJECT_DIR"/*) edited_file="${edited_file#$PROJECT_DIR/}" ;;
  esac
fi

# ── Scan parked-edits for matching sessions/files ─────────────────────────────
found=0

for session_dir in "$PARKED_ROOT"/*/; do
  [ -d "$session_dir" ] || continue
  parked_session="$(basename "$session_dir")"

  # Skip own parked edits.
  [ "$parked_session" = "$ME" ] && continue

  for parked_file in "$session_dir"*.json "$session_dir"*.yaml "$session_dir"*.yml; do
    [ -f "$parked_file" ] || continue

    # Derive the file key encoded in the parked filename.
    parked_basename="$(basename "$parked_file")"
    # Strip trailing .json/.yaml/.yml to get the safe-path key.
    file_key="${parked_basename%.json}"
    file_key="${file_key%.yaml}"
    file_key="${file_key%.yml}"

    # If we know which file was edited, only surface matching parked edits.
    if [ -n "$edited_file" ]; then
      expected_key="$(_safe_path "$edited_file")"
      [ "$file_key" = "$expected_key" ] || continue
    fi

    # Found a parked edit from a sibling session.
    found=$(( found + 1 ))
    echo "[edit-lock-drain-parked] PARKED EDIT FOUND: session=$parked_session file_key=$file_key" >&2
    echo "[edit-lock-drain-parked]   Parked file: $parked_file" >&2
    echo "[edit-lock-drain-parked]   The parked session should now re-attempt its edit." >&2

    # Touch a notice marker so the parked session sees it on next interaction.
    notice_dir="$PENDING_ROOT/$parked_session"
    mkdir -p "$notice_dir"
    notice_file="$notice_dir/${file_key}.notice"
    if [ ! -f "$notice_file" ]; then
      cat > "$notice_file" <<EOF
discovered_at: "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
released_by_session: "$ME"
parked_file: "$parked_file"
file_key: "$file_key"
EOF
      echo "[edit-lock-drain-parked]   Notice written: $notice_file" >&2
    else
      # Idempotent: marker already exists.
      echo "[edit-lock-drain-parked]   Notice already present (idempotent): $notice_file" >&2
    fi
  done
done

if [ "$found" -eq 0 ] && [ -n "$edited_file" ]; then
  echo "[edit-lock-drain-parked] no parked edits for $edited_file" >&2
fi

exit 0
