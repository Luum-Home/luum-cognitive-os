#!/usr/bin/env bash
# SCOPE: both
# cos-validation-capsule.sh — run validation in an isolated git worktree.
#
# Protects the operator checkout from test/hook mutations and publishes a short
# validation lock that dispatch-gate/profile mutators respect. This is scoped
# isolation, not the global hook killswitch.

set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/cos-validation-capsule.sh [--ttl-seconds N] [--name NAME] [--allow-dirty] -- <command...>

Runs <command> in a detached temporary worktree at the current HEAD. The source
checkout gets .cognitive-os/runtime/validation-capsule.lock for the duration so
new Agent dispatches in that checkout are blocked while validation is running.
--allow-dirty is accepted for compatibility; dirty source worktrees are allowed
because the capsule validates HEAD in a separate worktree.
USAGE
}

TTL_SECONDS=7200
NAME="validation"
while [ $# -gt 0 ]; do
  case "$1" in
    --ttl-seconds)
      TTL_SECONDS="${2:-}"; shift 2 ;;
    --name)
      NAME="${2:-validation}"; shift 2 ;;
    --name=*)
      NAME="${1#--name=}"; shift ;;
    --allow-dirty|--allow-mutation)
      shift ;;
    --help|-h)
      usage; exit 0 ;;
    --)
      shift; break ;;
    *)
      echo "Error: unknown argument before --: $1" >&2; usage; exit 2 ;;
  esac
done
[ $# -gt 0 ] || { usage; exit 2; }

if [ "${COS_VALIDATION_CAPSULE_ACTIVE:-0}" = "1" ]; then
  exec "$@"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$("$SCRIPT_DIR/cos-root" project)"
cd "$REPO_ROOT"
# COS_VALIDATION_CAPSULE_SAFE_WORKTREE_FALLBACK: keep validation usable in
# minimal consumer repos that do not carry the COS helper library. The full COS
# checkout uses ADR-129 safe_worktree_remove; minimal repos get a logged,
# non-rm-rf git-worktree cleanup fallback.
if [ -f "$REPO_ROOT/hooks/_lib/safe-worktree-remove.sh" ]; then
  # shellcheck source=/dev/null
  source "$REPO_ROOT/hooks/_lib/safe-worktree-remove.sh"
else
  safe_worktree_remove() {
    local project_dir="${1:-}"
    local target="${2:-}"
    local caller="${3:-cos-validation-capsule-fallback}"
    [ -n "$project_dir" ] && [ -n "$target" ] || return 2
    [ -e "$target" ] || return 0
    mkdir -p "$project_dir/.cognitive-os/metrics" 2>/dev/null || true
    if git -C "$project_dir" worktree remove --force "$target" >/dev/null 2>&1; then
      printf '{"ts":"%s","action":"removed","target":"%s","caller":"%s","fallback":true}\n' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$target" "$caller" >> "$project_dir/.cognitive-os/metrics/worktree-removals.jsonl" 2>/dev/null || true
      return 0
    fi
    git -C "$project_dir" worktree prune 2>/dev/null || true
    printf '{"ts":"%s","action":"remove_failed","target":"%s","caller":"%s","fallback":true}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$target" "$caller" >> "$project_dir/.cognitive-os/metrics/worktree-removals.jsonl" 2>/dev/null || true
    return 1
  }
fi

HEAD_SHA="$(git rev-parse HEAD)"
RUNTIME_DIR="$REPO_ROOT/.cognitive-os/runtime"
LOCK_FILE="$RUNTIME_DIR/validation-capsule.lock"
mkdir -p "$RUNTIME_DIR"

now_epoch="$(date +%s)"
expires_at="$((now_epoch + TTL_SECONDS))"
safe_name="$(printf '%s' "$NAME" | tr -c 'A-Za-z0-9._=-' '-' | sed 's/--*/-/g' | cut -c1-60)"
[ -n "$safe_name" ] || safe_name="validation"
run_id="${safe_name}-$(date -u +%Y%m%dT%H%M%SZ)-$$"
base_dir="${TMPDIR:-/tmp}/cos-validation-capsules"
CAPSULE_DIR="$base_dir/$(basename "$REPO_ROOT")-$run_id"

if [ -f "$LOCK_FILE" ]; then
  if command -v python3 >/dev/null 2>&1; then
    if python3 - "$LOCK_FILE" <<'PYLOCK'
import json, os, sys, time
from pathlib import Path
p=Path(sys.argv[1])
try: d=json.loads(p.read_text())
except Exception: sys.exit(0)
exp=int(d.get('expires_at_epoch') or 0)
pid=int(d.get('pid') or 0)
stale = bool(exp and exp < int(time.time()))
if pid and not stale:
    try: os.kill(pid,0)
    except ProcessLookupError: stale=True
    except PermissionError: stale=False
if stale:
    try: p.unlink()
    except Exception: pass
    sys.exit(1)
sys.exit(0)
PYLOCK
    then
      echo "[validation-capsule] another validation lock is active: $LOCK_FILE" >&2
      exit 2
    fi
  else
    echo "[validation-capsule] lock exists and python3 unavailable: $LOCK_FILE" >&2
    exit 2
  fi
fi

mkdir -p "$base_dir"

# ADR-113: heartbeat configuration
HEARTBEAT_INTERVAL_SECONDS="${COS_VALIDATION_HEARTBEAT_INTERVAL:-30}"
HEARTBEAT_PID=""
ACTIVITY_LOG="$RUNTIME_DIR/validation-activity.jsonl"

cleanup() {
  status=$?
  # ADR-113: kill heartbeat first so it stops touching the lock
  if [ -n "$HEARTBEAT_PID" ]; then
    kill "$HEARTBEAT_PID" 2>/dev/null || true
    wait "$HEARTBEAT_PID" 2>/dev/null || true
  fi
  if [ -f "$LOCK_FILE" ] && grep -q "\"run_id\":\"$run_id\"" "$LOCK_FILE" 2>/dev/null; then
    rm -f "$LOCK_FILE"
  fi
  safe_worktree_remove "$REPO_ROOT" "$CAPSULE_DIR" "cos-validation-capsule-trap"
  exit "$status"
}
trap cleanup EXIT INT TERM

python3 - "$LOCK_FILE" "$run_id" "$HEAD_SHA" "$CAPSULE_DIR" "$expires_at" "$$" "$HEARTBEAT_INTERVAL_SECONDS" "$*" <<'PYJSON'
import json, sys, time
from pathlib import Path
path, run_id, head, capsule, expires, shell_pid, hb_interval, command = sys.argv[1:]
now = int(time.time())
payload = {
    "run_id": run_id,
    "pid": int(shell_pid),
    "head": head,
    "capsule_dir": capsule,
    "started_at_epoch": now,
    "expires_at_epoch": int(expires),
    "last_heartbeat_epoch": now,           # ADR-113 P1
    "heartbeat_interval_seconds": int(hb_interval),  # ADR-113 P1
    "command": command,
    "message": f"validation capsule {run_id} is running in {capsule}",
}
Path(path).write_text(json.dumps(payload, separators=(",", ":")) + "\n")
PYJSON

# ADR-113 P1: heartbeat writer background loop. Updates last_heartbeat_epoch
# every $HEARTBEAT_INTERVAL_SECONDS so dispatch-gate can detect hung processes
# (alive PID but no progress).
(
  while sleep "$HEARTBEAT_INTERVAL_SECONDS"; do
    [ -f "$LOCK_FILE" ] || exit 0
    python3 - "$LOCK_FILE" <<'PYHB'
import json, sys, time, os, tempfile
from pathlib import Path
p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text())
except Exception:
    sys.exit(0)
data["last_heartbeat_epoch"] = int(time.time())
# atomic write via tmpfile + rename
tmp = p.with_suffix(p.suffix + ".tmp")
tmp.write_text(json.dumps(data, separators=(",", ":")) + "\n")
os.replace(tmp, p)
PYHB
  done
) >/dev/null 2>&1 < /dev/null &
HEARTBEAT_PID=$!

# ADR-113 P2: initialize activity log; subprocess can append events.
printf '{"ts":"%s","capsule":"%s","action":"capsule_start","detail":"%s"}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$run_id" "$*" >> "$ACTIVITY_LOG" 2>/dev/null || true

git worktree add --detach "$CAPSULE_DIR" "$HEAD_SHA" >/dev/null
if [ -d "$REPO_ROOT/.venv" ] && [ ! -e "$CAPSULE_DIR/.venv" ]; then
  ln -s "$REPO_ROOT/.venv" "$CAPSULE_DIR/.venv"
fi
mkdir -p "$CAPSULE_DIR/.cognitive-os/metrics" "$CAPSULE_DIR/.cognitive-os/runtime" "$CAPSULE_DIR/.cognitive-os/reports"

printf '[validation-capsule] running in %s\n' "$CAPSULE_DIR" >&2
(
  cd "$CAPSULE_DIR"
  # Keep test behavior representative. The source checkout is protected by the
  # validation lock; the isolated worktree should run hooks/tests normally.
  unset COGNITIVE_OS_PROJECT_DIR CLAUDE_PROJECT_DIR CODEX_PROJECT_DIR
  unset COS_VALIDATION_MODE COS_SUPPRESS_AGENT_SNAPSHOT COS_DISABLE_PROFILE_AUTOAPPLY COS_VALIDATION_CAPSULE_ACTIVE
  export COS_VALIDATION_SOURCE_PROJECT_DIR="$REPO_ROOT"
  exec "$@"
)
