#!/usr/bin/env bash
# metrics-rotation.sh — Rotate JSONL metrics files to prevent unbounded growth
# Part of: auto-repair-system (ARS-1-03)
# Trigger: SessionStart
#
# Rotates files exceeding MAX_LINES by keeping the most recent KEEP_LINES.
# Archives rotated content as gzipped files with date suffix.
# Deletes archives older than RETENTION_DAYS.

_HOOK_NAME="metrics-rotation"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

set -uo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────

MAX_LINES="${COGNITIVE_OS_METRICS_MAX_LINES:-5000}"
KEEP_LINES="${COGNITIVE_OS_METRICS_KEEP_LINES:-2500}"
RETENTION_DAYS="${COGNITIVE_OS_METRICS_RETENTION_DAYS:-30}"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
ARCHIVE_DIR="$METRICS_DIR/archive"

# ─── Main ────────────────────────────────────────────────────────────────────

[ ! -d "$METRICS_DIR" ] && exit 0

mkdir -p "$ARCHIVE_DIR" 2>/dev/null

ROTATED=0
ARCHIVED=0
CLEANED=0

# Rotate oversized JSONL files
for jsonl_file in "$METRICS_DIR"/*.jsonl; do
  [ -f "$jsonl_file" ] || continue

  line_count=$(wc -l < "$jsonl_file" 2>/dev/null | tr -d ' ')
  [ "$line_count" -le "$MAX_LINES" ] && continue

  filename=$(basename "$jsonl_file")
  date_suffix=$(date +%Y%m%d-%H%M%S)
  archive_name="${filename%.jsonl}-${date_suffix}.jsonl"

  # Archive the old content (everything except the last KEEP_LINES)
  lines_to_archive=$((line_count - KEEP_LINES))
  head -n "$lines_to_archive" "$jsonl_file" | gzip > "$ARCHIVE_DIR/${archive_name}.gz" 2>/dev/null

  if [ $? -eq 0 ]; then
    # Keep only the tail (atomic: write to temp, then replace)
    tail -n "$KEEP_LINES" "$jsonl_file" > "${jsonl_file}.tmp" && mv "${jsonl_file}.tmp" "$jsonl_file"
    ROTATED=$((ROTATED + 1))
  fi
done

# Clean old archives
if [ -d "$ARCHIVE_DIR" ]; then
  while IFS= read -r old_archive; do
    rm -f "$old_archive" 2>/dev/null
    CLEANED=$((CLEANED + 1))
  done < <(find "$ARCHIVE_DIR" -name "*.gz" -mtime "+$RETENTION_DAYS" 2>/dev/null)
fi

# Clean stale test-e2e agent-bus directories (F-6: accumulate indefinitely)
TEST_E2E_TTL_DAYS="${COGNITIVE_OS_TEST_E2E_TTL_DAYS:-7}"
AGENT_BUS_DIR="$PROJECT_DIR/.cognitive-os/agent-bus"
STALE_E2E=0

if [ -d "$AGENT_BUS_DIR" ]; then
  while IFS= read -r stale_dir; do
    rm -rf "$stale_dir" 2>/dev/null
    STALE_E2E=$((STALE_E2E + 1))
  done < <(find "$AGENT_BUS_DIR" -maxdepth 1 -type d -name 'test-e2e-*' -mtime "+$TEST_E2E_TTL_DAYS" 2>/dev/null)
fi

if [ "$STALE_E2E" -gt 0 ]; then
  echo "[rotate-metrics] cleaned $STALE_E2E stale test-e2e dirs" >&2
fi

# Report if anything happened
if [ "$ROTATED" -gt 0 ] || [ "$CLEANED" -gt 0 ]; then
  echo "[metrics-rotation] Rotated: $ROTATED files, Cleaned: $CLEANED archives (retention: ${RETENTION_DAYS}d)" >&2
fi

exit 0
