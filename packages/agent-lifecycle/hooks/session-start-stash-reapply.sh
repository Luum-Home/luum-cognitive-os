#!/usr/bin/env bash
# SCOPE: both
# session-start-stash-reapply.sh — SessionStart hook for ADR-116 P4.3.
#
# On SessionStart, checks stash-provenance.jsonl for stash entries that match
# the current session_id. For each match:
#   - If working tree is dirty: skip (emit stash_reapply_skipped reason=working_tree_dirty)
#   - If COS_AUTO_REAPPLY_STASH=1: attempt git stash apply. On success, mark
#     reapplied (emit stash_reapply_success). On conflict: emit stash_reapply_conflict.
#   - Otherwise: emit stash_reapply_offered to stderr with ref + file list.
#
# Fail-soft: any error → log + exit 0 (NEVER blocks SessionStart).
#
# Reference: ADR-116 §P4.3 stash provenance auto-reapply.

set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Resolve to actual COS root. The canonical hook lives in packages/agent-lifecycle/hooks/;
# the symlink at hooks/ has HOOK_DIR = <root>/hooks — both resolve correctly:
#   packages/agent-lifecycle/hooks/ -> ../../.. -> project root
#   hooks/ -> .. -> project root (one level up for symlink realpath)
# Use the authoritative COS root from env or walk up to find cognitive-os.yaml.
if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ]; then
  OS_ROOT="$COGNITIVE_OS_PROJECT_DIR"
elif [ -f "$(pwd)/cognitive-os.yaml" ]; then
  OS_ROOT="$(pwd)"
else
  # Walk up from HOOK_DIR to find cognitive-os.yaml
  _walk="$HOOK_DIR"
  OS_ROOT=""
  for _ in 1 2 3 4; do
    _walk="$(dirname "$_walk")"
    if [ -f "$_walk/cognitive-os.yaml" ]; then
      OS_ROOT="$_walk"
      break
    fi
  done
  OS_ROOT="${OS_ROOT:-$(cd "$HOOK_DIR/../../.." && pwd)}"
fi
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$(pwd)}}}
"
PROJECT_DIR="${PROJECT_DIR%$'\n'}"

# ADR-222: stale Phase-1 plans mean launch never reached the commit boundary.
# Delete them before any stash reapply logic; no git stash was created.
if command -v python3 >/dev/null 2>&1; then
  PYTHONPATH="$OS_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$PROJECT_DIR" <<'PYEOF' 2>/dev/null || true
import sys
from pathlib import Path
try:
    from lib.snapshot_manager import sweep_snapshot_plans
    sweep_snapshot_plans(Path(sys.argv[1]), ttl_seconds=300)
except Exception:
    pass
PYEOF
fi

# Ensure stash_provenance module is importable
export PYTHONPATH="$OS_ROOT/packages/agent-coordination/lib:$OS_ROOT/lib:$OS_ROOT${PYTHONPATH:+:$PYTHONPATH}"

# ── Stash lock library ────────────────────────────────────────────────────────
STASH_LOCK_LIB="$HOOK_DIR/_lib/stash-lock.sh"
if [ -f "$STASH_LOCK_LIB" ]; then
  # shellcheck source=/dev/null
  source "$STASH_LOCK_LIB"
fi

# ── Helpers ───────────────────────────────────────────────────────────────────

_log() {
  echo "[session-start-stash-reapply] $*" >&2
}

# Emit a coordination event via session_bus.py if available; otherwise stderr.
_emit_event() {
  local event_type="$1"
  shift
  # Build a minimal JSON payload from key=value args
  local payload="{"
  local sep=""
  for kv in "$@"; do
    local key="${kv%%=*}"
    local val="${kv#*=}"
    payload="${payload}${sep}\"${key}\":\"${val}\""
    sep=","
  done
  payload="${payload}}"

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$event_type" "$payload" <<'PYEOF' 2>/dev/null || true
import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
try:
    from lib.session_bus import append_event
    event_type = sys.argv[1]
    payload = json.loads(sys.argv[2])
    append_event(event_type, payload)
except Exception:
    # session_bus unavailable — stderr only (already printed by caller)
    pass
PYEOF
  fi
  _log "event=$event_type $*"
}

# ── Resolve session_id ────────────────────────────────────────────────────────

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"

if [ -z "$SESSION_ID" ]; then
  # Try .cognitive-os/sessions/.context-<pid>.json
  CONTEXT_FILE="$PROJECT_DIR/.cognitive-os/sessions/.context-$$.json"
  if [ -f "$CONTEXT_FILE" ] && command -v python3 >/dev/null 2>&1; then
    SESSION_ID=$(python3 -c "
import json, sys
try:
    d = json.loads(open('$CONTEXT_FILE').read())
    print(d.get('session_id', ''))
except Exception:
    print('')
" 2>/dev/null || true)
  fi
fi

if [ -z "$SESSION_ID" ]; then
  # Nothing to do without a session id
  exit 0
fi

# ── Find matching provenance records ─────────────────────────────────────────

if ! command -v python3 >/dev/null 2>&1; then
  _log "python3 not available, skipping stash reapply check"
  exit 0
fi

MATCHES_JSON=$(
  COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
    python3 -m stash_provenance find-by-session "$SESSION_ID" --json 2>&1 || echo "[]"
)
# Strip any non-JSON lines (e.g. warnings) — keep only the last line that starts with '['
MATCHES_JSON=$(printf '%s\n' "$MATCHES_JSON" | grep '^[\[{]' | tail -1 || echo "[]")

if [ -z "$MATCHES_JSON" ] || [ "$MATCHES_JSON" = "[]" ]; then
  exit 0
fi

# ── Parse matches (use python3 to iterate) ───────────────────────────────────

python3 - "$MATCHES_JSON" "$SESSION_ID" "$PROJECT_DIR" \
  "${COS_AUTO_REAPPLY_STASH:-0}" \
  <<'PYEOF' || true
import json
import os
import subprocess
import sys

matches_json, session_id, project_dir, auto_flag = (
    sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
)

records = json.loads(matches_json)
if not records:
    sys.exit(0)

# Helpers

def log(msg):
    print(f"[session-start-stash-reapply] {msg}", file=sys.stderr)


def emit_event(event_type, **kw):
    """Emit via session_bus if available, always log to stderr."""
    log(f"event={event_type} " + " ".join(f"{k}={v}" for k, v in kw.items()))
    try:
        # session_bus lives at <project_dir>/lib/session_bus.py
        if project_dir not in sys.path:
            sys.path.insert(0, project_dir)
        from lib.session_bus import append_event
        append_event(event_type, kw)
    except Exception:
        pass


def working_tree_dirty():
    """Return True if any tracked or untracked (non .cognitive-os) files are modified."""
    result = subprocess.run(
        ["git", "-C", project_dir, "status", "--porcelain"],
        capture_output=True, text=True
    )
    lines = [
        ln for ln in result.stdout.splitlines()
        if not ln[3:].startswith(".cognitive-os")
    ]
    return bool(lines)


def record_provenance_mark_reapplied(stash_ref):
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = project_dir
    subprocess.run(
        ["python3", "-m", "stash_provenance", "mark-reapplied", stash_ref],
        cwd=project_dir, env=env, capture_output=True
    )


for rec in records:
    stash_ref = rec.get("stash_ref", "")
    original_files = rec.get("original_files", [])
    files_str = ",".join(original_files)

    if not stash_ref:
        log(f"skipping record with empty stash_ref: {rec}")
        continue

    # Verify stash still exists
    check = subprocess.run(
        ["git", "-C", project_dir, "stash", "show", stash_ref],
        capture_output=True, text=True
    )
    if check.returncode != 0:
        log(f"stash {stash_ref} no longer exists, skipping")
        continue

    if working_tree_dirty():
        emit_event(
            "stash_reapply_skipped",
            stash_ref=stash_ref,
            session_id=session_id,
            reason="working_tree_dirty",
        )
        continue

    if auto_flag != "1":
        emit_event(
            "stash_reapply_offered",
            stash_ref=stash_ref,
            session_id=session_id,
            files=files_str,
        )
        log(
            f"stash_reapply_offered: set COS_AUTO_REAPPLY_STASH=1 to auto-reapply "
            f"{stash_ref} (files: {files_str})"
        )
        continue

    # Auto-reapply
    apply = subprocess.run(
        ["git", "-C", project_dir, "stash", "apply", stash_ref],
        capture_output=True, text=True
    )
    if apply.returncode == 0:
        record_provenance_mark_reapplied(stash_ref)
        emit_event(
            "stash_reapply_success",
            stash_ref=stash_ref,
            session_id=session_id,
            files=files_str,
        )
    else:
        # If apply started but failed partway, restore clean state
        subprocess.run(
            ["git", "-C", project_dir, "checkout", "--", "."],
            capture_output=True
        )
        subprocess.run(
            ["git", "-C", project_dir, "clean", "-fd", "--", "."],
            capture_output=True
        )
        emit_event(
            "stash_reapply_conflict",
            stash_ref=stash_ref,
            session_id=session_id,
            reason="apply_conflict",
            stderr=apply.stderr.strip().replace("\n", " ")[:200],
        )

PYEOF

# Always advisory — never block SessionStart
exit 0
