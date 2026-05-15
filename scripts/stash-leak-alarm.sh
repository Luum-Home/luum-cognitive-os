#!/usr/bin/env bash
# SCOPE: both
# Detect auto-pre-agent stashes that hide work from later sessions.
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
TTL="${COS_STASH_LEAK_TTL:-600}"
BLOCK_TTL="${COS_STASH_LEAK_BLOCK_TTL:-3600}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
ALARM_FILE="$RUNTIME_DIR/stash-leak-alarm.json"

if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "WARN not a git repository: $PROJECT_DIR"
  exit 0
fi

now=$(date -u +%s)
mkdir -p "$RUNTIME_DIR"
found=""
# Format: stash@{0}<US>epoch<US>message
while IFS=$'\037' read -r ref epoch subject; do
  [ -n "${ref:-}" ] || continue
  case "$subject" in
    *auto-pre-agent-*)
      age=$(( now - epoch ))
      if [ "$age" -ge "$TTL" ]; then
        found="$ref|$epoch|$subject|$age"
        break
      fi
      ;;
  esac
done < <(git -C "$PROJECT_DIR" stash list --date=unix --format='%gd%x1f%ct%x1f%gs' 2>/dev/null || true)

if [ -z "$found" ]; then
  echo "PASS no auto-pre-agent stash leak above TTL"
  exit 0
fi

IFS='|' read -r stash_ref stash_epoch stash_message age_seconds <<< "$found"
file_count=$(git -C "$PROJECT_DIR" stash show --name-only "$stash_ref" 2>/dev/null | sed '/^$/d' | wc -l | tr -d ' ')
blocking=false
if [ "$age_seconds" -ge "$BLOCK_TTL" ]; then
  blocking=true
fi

python3 - "$ALARM_FILE" "$stash_ref" "$stash_message" "$age_seconds" "$file_count" "$blocking" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, ref, msg, age, count, blocking = sys.argv[1:]
payload = {
    "detected_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "stash_ref": ref,
    "stash_message": msg,
    "age_seconds": int(age),
    "file_count": int(count),
    "blocking": blocking == "true",
    "remediation": [
        f"git stash show --name-status {ref}",
        f"git stash apply {ref}  # after inspection; drop only after verifying restore",
        f"git stash drop {ref}   # only after confirming it is obsolete",
        "rm -f .cognitive-os/runtime/stash-leak-alarm.json",
    ],
}
with open(path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2, sort_keys=True)
    fh.write("\n")
PY

if [ "$blocking" = true ]; then
  echo "BLOCK auto-pre-agent stash leak: $stash_ref age=${age_seconds}s files=$file_count"
  echo "Inspect with: git stash show --name-status $stash_ref"
  echo "Resolve with: inspect $stash_ref, then git stash apply $stash_ref or git stash drop $stash_ref only after confirming ownership; then rm -f .cognitive-os/runtime/stash-leak-alarm.json"
  exit 2
fi

echo "WARN auto-pre-agent stash leak: $stash_ref age=${age_seconds}s files=$file_count"
echo "Alarm written: $ALARM_FILE"
exit 0
