#!/usr/bin/env bash
# ROLE: operator-recovery
# CANONICAL: scripts/cos-startup-recover.sh
# Activate bounded startup safe mode and clear stale locks after a Claude Code
# startup hang/re-spawn storm. Advisory: never deletes Git locks while a Git
# process appears active for this repo.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$("$SCRIPT_DIR/cos-root" project)"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
SAFE_FILE="$RUNTIME_DIR/startup-safe-mode.json"
TTL_SECONDS="${COS_STARTUP_SAFE_MODE_TTL_SECONDS:-300}"
NOW_EPOCH="$(date +%s 2>/dev/null || python3 -c 'import time; print(int(time.time()))')"
EXPIRES_EPOCH="$((NOW_EPOCH + TTL_SECONDS))"

mkdir -p "$RUNTIME_DIR"

removed_runtime=0
for lock in "$RUNTIME_DIR"/*.lock "$RUNTIME_DIR"/*/*.lock; do
  [ -e "$lock" ] || continue
  rm -f "$lock" 2>/dev/null && removed_runtime=$((removed_runtime + 1)) || true
done

GIT_DIR="$(git -C "$PROJECT_DIR" rev-parse --git-dir 2>/dev/null || true)"
if [ -n "$GIT_DIR" ]; then
  case "$GIT_DIR" in
    /*) ;;
    *) GIT_DIR="$PROJECT_DIR/$GIT_DIR" ;;
  esac
fi

git_active=0
if [ -n "$GIT_DIR" ]; then
  # Conservative: if any git process mentions this repo path or git dir, do not
  # remove Git's own lock files. We may miss edge cases, but false positives are
  # safer than deleting an active lock.
  if ps -axo command= 2>/dev/null | grep '[g]it' | grep -F "$PROJECT_DIR" >/dev/null 2>&1; then
    git_active=1
  elif ps -axo command= 2>/dev/null | grep '[g]it' | grep -F "$GIT_DIR" >/dev/null 2>&1; then
    git_active=1
  fi
fi

removed_git=0
skipped_git=0
if [ -n "$GIT_DIR" ] && [ -d "$GIT_DIR" ]; then
  if [ "$git_active" -eq 0 ]; then
    for lock in "$GIT_DIR/index.lock" "$GIT_DIR/config.lock" "$GIT_DIR/cos-self-install-git-config.lock"; do
      [ -e "$lock" ] || continue
      rm -f "$lock" 2>/dev/null && removed_git=$((removed_git + 1)) || true
    done
  else
    skipped_git=1
  fi
fi

python3 - "$SAFE_FILE" "$NOW_EPOCH" "$EXPIRES_EPOCH" "$TTL_SECONDS" <<'PYEOF'
import json
import os
import sys
from pathlib import Path

safe_file, now, expires, ttl = sys.argv[1:5]
payload = {
    "activated_at": int(now),
    "expires_at": int(expires),
    "ttl_seconds": int(ttl),
    "reason": "operator_recovery",
    "source": "scripts/cos-startup-recover.sh",
}
path = Path(safe_file)
path.parent.mkdir(parents=True, exist_ok=True)
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(payload, indent=2) + "\n")
os.replace(tmp, path)
PYEOF

cat <<EOF
COS startup recovery applied.

Project: $PROJECT_DIR
Safe mode: $SAFE_FILE
Safe mode TTL: ${TTL_SECONDS}s (expires epoch $EXPIRES_EPOCH)
Runtime locks removed: $removed_runtime
Git locks removed: $removed_git
Git locks skipped because git appears active: $skipped_git

Next steps:
  1. Open a fresh Claude Code conversation in this repo.
  2. Watch: tail -f .cognitive-os/metrics/hook-timing.jsonl
  3. Expected while safe mode is active: SessionStart records show safe_mode=1, skipped=1.
  4. Clear manual disable if present: rm -f .cognitive-os/runtime/disable-sessionstart-hooks

Emergency one-shot launch:
  COS_STARTUP_SAFE_MODE=1 claude
EOF
