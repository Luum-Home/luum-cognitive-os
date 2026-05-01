#!/usr/bin/env bash
# SCOPE: os-only
# self-knowledge-refresh.sh — SessionStart hook for ADR-037 self-knowledge base.
#
# Compares .cognitive-os/self-knowledge/.mtime against newest mtime in
# lib/, hooks/, scripts/, docs/adrs/, packages/*/lib/. If stale (or missing),
# rebuilds the index in the background so session startup is never blocked.
#
# Always exits 0. Logs to .cognitive-os/metrics/self-knowledge-refresh.jsonl.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
KNOWLEDGE_DIR="$PROJECT_DIR/.cognitive-os/self-knowledge"
MTIME_FILE="$KNOWLEDGE_DIR/.mtime"
METRICS_FILE="$PROJECT_DIR/.cognitive-os/metrics/self-knowledge-refresh.jsonl"
GENERATOR="$PROJECT_DIR/scripts/cos_build_self_knowledge.py"
LOGFILE="$PROJECT_DIR/.cognitive-os/self-knowledge/build.log"

NOW_EPOCH=$(date +%s 2>/dev/null || echo 0)
NOW_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "")

# ── Helpers ────────────────────────────────────────────────────────────────

log_metric() {
  local status="$1"
  local reason="$2"
  mkdir -p "$(dirname "$METRICS_FILE")"
  printf '{"timestamp":"%s","status":"%s","reason":"%s","pid":"%s"}\n' \
    "$NOW_ISO" "$status" "$reason" "$$" \
    >> "$METRICS_FILE" 2>/dev/null || true
}

rebuild_background() {
  local reason="$1"
  if [ ! -f "$GENERATOR" ]; then
    log_metric "skip" "generator_not_found"
    exit 0
  fi
  mkdir -p "$KNOWLEDGE_DIR"
  # Run in background; redirect output to build log
  nohup python3 "$GENERATOR" --project-dir "$PROJECT_DIR" \
    > "$LOGFILE" 2>&1 &
  log_metric "rebuild_triggered" "$reason"
  echo "[self-knowledge-refresh] Rebuilding index in background (reason: $reason)" >&2
}

# ── Stale check ────────────────────────────────────────────────────────────

if [ ! -f "$MTIME_FILE" ]; then
  rebuild_background "index_missing"
  exit 0
fi

INDEX_MTIME=$(date -r "$MTIME_FILE" +%s 2>/dev/null || echo 0)

# Collect newest mtime across source trees using Python os.stat() — avoids
# spawning one `date -r` subprocess per file (O(N) was the 5.8s p95 root cause).
NEWEST_MTIME=$(python3 - "$PROJECT_DIR" "$INDEX_MTIME" <<'PYSTAT' 2>/dev/null || echo 0
import os, sys
from pathlib import Path

project_dir = sys.argv[1]
index_mtime = int(sys.argv[2])
dirs = ["lib", "hooks", "scripts", "docs/adrs", "packages"]
exts = {".py", ".sh", ".md"}
newest = 0

for d in dirs:
    base = Path(project_dir) / d
    if not base.is_dir():
        continue
    for root, _, files in os.walk(base):
        # Respect maxdepth 4
        depth = len(Path(root).relative_to(base).parts)
        if depth > 4:
            continue
        for fname in files:
            if Path(fname).suffix in exts:
                try:
                    mtime = int(os.stat(os.path.join(root, fname)).st_mtime)
                    if mtime > newest:
                        newest = mtime
                        # Early exit: already newer than index
                        if newest > index_mtime:
                            print(newest)
                            sys.exit(0)
                except OSError:
                    pass

print(newest)
PYSTAT
)

if [ "$NEWEST_MTIME" -gt "$INDEX_MTIME" ]; then
  rebuild_background "stale"
else
  log_metric "up_to_date" "mtime_check"
fi

exit 0
