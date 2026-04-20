#!/usr/bin/env bash
# SCOPE: os-only
# metrics-rotation.sh — Rotate JSONL metrics files to prevent unbounded growth
# Part of: auto-repair-system (ARS-1-03)
# Trigger: SessionStart
#
# Rotates files exceeding MAX_LINES by keeping the most recent KEEP_LINES.
# Also rotates files older than COGNITIVE_OS_METRICS_AGE_DAYS (default 7) days.
# Archives rotated content as gzipped files with date suffix.
# Deletes archives older than RETENTION_DAYS.

_HOOK_NAME="metrics-rotation"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# ─── Configuration ───────────────────────────────────────────────────────────

MAX_LINES="${COGNITIVE_OS_METRICS_MAX_LINES:-5000}"
KEEP_LINES="${COGNITIVE_OS_METRICS_KEEP_LINES:-2500}"
RETENTION_DAYS="${COGNITIVE_OS_METRICS_RETENTION_DAYS:-30}"
AGE_DAYS="${COGNITIVE_OS_METRICS_AGE_DAYS:-7}"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
ARCHIVE_DIR="$METRICS_DIR/archive"

# ─── Helper ──────────────────────────────────────────────────────────────────

# _rotate_file <jsonl_file> <line_count>
# Archives the head of the file (all lines except the last KEEP_LINES) as a
# gzipped archive, then truncates the source to the tail.  Returns 0 on
# success, 1 on failure.
_rotate_file() {
  local jsonl_file="$1"
  local line_count="$2"
  local filename date_suffix archive_name lines_to_archive

  filename=$(basename "$jsonl_file")
  date_suffix=$(date +%Y%m%d-%H%M%S)
  archive_name="${filename%.jsonl}-${date_suffix}.jsonl"

  if [ "$line_count" -le "$KEEP_LINES" ]; then
    # Nothing to archive — just gzip the whole file and truncate
    gzip -c "$jsonl_file" > "$ARCHIVE_DIR/${archive_name}.gz" 2>/dev/null || return 1
    : > "$jsonl_file"
  else
    lines_to_archive=$((line_count - KEEP_LINES))
    head -n "$lines_to_archive" "$jsonl_file" | gzip > "$ARCHIVE_DIR/${archive_name}.gz" 2>/dev/null || return 1
    # Keep only the tail (atomic: write to temp, then replace)
    tail -n "$KEEP_LINES" "$jsonl_file" > "${jsonl_file}.tmp" && mv "${jsonl_file}.tmp" "$jsonl_file"
  fi
  return 0
}

# ─── Main ────────────────────────────────────────────────────────────────────

[ ! -d "$METRICS_DIR" ] && exit 0

mkdir -p "$ARCHIVE_DIR" 2>/dev/null

ROTATED=0
ROTATED_AGE=0
ARCHIVED=0
CLEANED=0

# Rotate oversized JSONL files
for jsonl_file in "$METRICS_DIR"/*.jsonl; do
  [ -f "$jsonl_file" ] || continue

  line_count=$(wc -l < "$jsonl_file" 2>/dev/null | tr -d ' ')
  [ "$line_count" -le "$MAX_LINES" ] && continue

  if _rotate_file "$jsonl_file" "$line_count"; then
    ROTATED=$((ROTATED + 1))
  fi
done

# Rotate age-expired JSONL files (mtime older than AGE_DAYS, non-empty)
while IFS= read -r aged_file; do
  [ -f "$aged_file" ] || continue
  aged_lines=$(wc -l < "$aged_file" 2>/dev/null | tr -d ' ')
  [ "${aged_lines:-0}" -eq 0 ] && continue

  if _rotate_file "$aged_file" "$aged_lines"; then
    ROTATED_AGE=$((ROTATED_AGE + 1))
  fi
done < <(find "$METRICS_DIR" -maxdepth 1 -name "*.jsonl" -mtime "+$((AGE_DAYS - 1))" 2>/dev/null)

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
if [ "$ROTATED" -gt 0 ] || [ "$ROTATED_AGE" -gt 0 ] || [ "$CLEANED" -gt 0 ]; then
  echo "[metrics-rotation] Rotated: $ROTATED files (size), Cleaned: $CLEANED archives (retention: ${RETENTION_DAYS}d)" >&2
fi
if [ "$ROTATED_AGE" -gt 0 ]; then
  echo "[metrics-rotation] rotated $ROTATED_AGE files by age (>= $AGE_DAYS days)" >&2
fi

exit 0
