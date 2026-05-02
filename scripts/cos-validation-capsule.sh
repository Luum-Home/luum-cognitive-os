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

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

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
cleanup() {
  status=$?
  if [ -f "$LOCK_FILE" ] && grep -q "\"run_id\":\"$run_id\"" "$LOCK_FILE" 2>/dev/null; then
    rm -f "$LOCK_FILE"
  fi
  git worktree remove --force "$CAPSULE_DIR" >/dev/null 2>&1 || rm -rf "$CAPSULE_DIR"
  exit "$status"
}
trap cleanup EXIT INT TERM

python3 - "$LOCK_FILE" "$run_id" "$HEAD_SHA" "$CAPSULE_DIR" "$expires_at" "$$" "$*" <<'PYJSON'
import json, sys, time
from pathlib import Path
path, run_id, head, capsule, expires, shell_pid, command = sys.argv[1:]
payload = {
    "run_id": run_id,
    "pid": int(shell_pid),
    "head": head,
    "capsule_dir": capsule,
    "started_at_epoch": int(time.time()),
    "expires_at_epoch": int(expires),
    "command": command,
    "message": f"validation capsule {run_id} is running in {capsule}",
}
Path(path).write_text(json.dumps(payload, separators=(",", ":")) + "\n")
PYJSON

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
