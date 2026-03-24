#!/usr/bin/env bash
# test-metrics-rotation.sh — Integration test for metrics-rotation.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

FAILURES=0
TESTS=0
TMPDIR_BASE=""

setup() {
  TMPDIR_BASE=$(mktemp -d)
  export COGNITIVE_OS_PROJECT_DIR="$TMPDIR_BASE/project"
  export COGNITIVE_OS_HOOK_HEARTBEAT="false"
  export COGNITIVE_OS_SESSION_ID=""
  export COGNITIVE_OS_METRICS_MAX_LINES=5000
  export COGNITIVE_OS_METRICS_KEEP_LINES=2500
  export COGNITIVE_OS_METRICS_RETENTION_DAYS=30
  mkdir -p "$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics"
}

teardown() {
  rm -rf "$TMPDIR_BASE" 2>/dev/null
}

assert_eq() {
  local label="$1" expected="$2" actual="$3"
  TESTS=$((TESTS + 1))
  if [ "$expected" = "$actual" ]; then
    return 0
  else
    echo "  FAIL: $label (expected='$expected', got='$actual')"
    FAILURES=$((FAILURES + 1))
    return 1
  fi
}

assert_true() {
  local label="$1"
  shift
  TESTS=$((TESTS + 1))
  if "$@"; then
    return 0
  else
    echo "  FAIL: $label"
    FAILURES=$((FAILURES + 1))
    return 1
  fi
}

# Helper: generate N JSONL lines
generate_jsonl() {
  local file="$1"
  local count="$2"
  for i in $(seq 1 "$count"); do
    echo "{\"line\":$i,\"ts\":\"2025-01-01T00:00:00Z\"}" >> "$file"
  done
}

# ─── Test: file with 6000 lines gets truncated to 2500 ──────────────────────

test_rotation_truncates() {
  setup

  local metrics_file="$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/test-rotation.jsonl"
  generate_jsonl "$metrics_file" 6000

  local before_lines
  before_lines=$(wc -l < "$metrics_file" | tr -d ' ')
  assert_eq "pre-rotation: 6000 lines" "6000" "$before_lines"

  # Run rotation
  bash "$PROJECT_ROOT/hooks/metrics-rotation.sh" 2>/dev/null

  local after_lines
  after_lines=$(wc -l < "$metrics_file" | tr -d ' ')
  assert_eq "post-rotation: 2500 lines kept" "2500" "$after_lines"

  # Verify the kept lines are the LAST 2500 (most recent)
  local first_line_num
  first_line_num=$(head -1 "$metrics_file" | jq -r '.line' 2>/dev/null)
  assert_eq "post-rotation: first kept line is 3501" "3501" "$first_line_num"

  teardown
}

# ─── Test: archive is created in .archive/ ───────────────────────────────────

test_archive_created() {
  setup

  local metrics_file="$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/test-archive.jsonl"
  generate_jsonl "$metrics_file" 6000

  bash "$PROJECT_ROOT/hooks/metrics-rotation.sh" 2>/dev/null

  local archive_dir="$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/.archive"
  assert_true "archive directory exists" test -d "$archive_dir"

  local archive_count
  archive_count=$(find "$archive_dir" -name "test-archive-*.jsonl.gz" 2>/dev/null | wc -l | tr -d ' ')
  assert_eq "archive file created" "1" "$archive_count"

  teardown
}

# ─── Test: archive is gzipped ────────────────────────────────────────────────

test_archive_is_gzipped() {
  setup

  local metrics_file="$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/test-gzip.jsonl"
  generate_jsonl "$metrics_file" 6000

  bash "$PROJECT_ROOT/hooks/metrics-rotation.sh" 2>/dev/null

  local archive_dir="$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/.archive"
  local gz_file
  gz_file=$(find "$archive_dir" -name "test-gzip-*.jsonl.gz" 2>/dev/null | head -1)

  assert_true "gzip archive exists" test -f "$gz_file"

  if [ -f "$gz_file" ]; then
    # Verify it's valid gzip
    gzip -t "$gz_file" 2>/dev/null
    local rc=$?
    assert_eq "archive is valid gzip" "0" "$rc"

    # Verify content: should have 3500 archived lines (6000 - 2500)
    local archived_lines
    archived_lines=$(gzip -dc "$gz_file" 2>/dev/null | wc -l | tr -d ' ')
    assert_eq "archive contains 3500 lines" "3500" "$archived_lines"
  fi

  teardown
}

# ─── Test: old archive (40 days) is deleted ──────────────────────────────────

test_old_archive_deleted() {
  setup

  local archive_dir="$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/.archive"
  mkdir -p "$archive_dir"

  # Create an old archive file
  local old_archive="$archive_dir/old-metrics-20240101-000000.jsonl.gz"
  echo "old data" | gzip > "$old_archive"

  # Set modification time to 40 days ago using touch
  # macOS touch: -t format is [[CC]YY]MMDDhhmm[.SS]
  local old_date
  old_date=$(date -v-40d +%Y%m%d%H%M 2>/dev/null || date -d '40 days ago' +%Y%m%d%H%M 2>/dev/null)
  if [ -n "$old_date" ]; then
    touch -t "$old_date" "$old_archive" 2>/dev/null
  fi

  # Also create a JSONL file that triggers rotation (so the cleanup runs)
  local metrics_file="$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/trigger.jsonl"
  generate_jsonl "$metrics_file" 6000

  bash "$PROJECT_ROOT/hooks/metrics-rotation.sh" 2>/dev/null

  # The old archive should be deleted
  TESTS=$((TESTS + 1))
  if [ ! -f "$old_archive" ]; then
    : # pass — old archive was cleaned up
  else
    echo "  FAIL: old archive (40 days) not deleted"
    FAILURES=$((FAILURES + 1))
  fi

  teardown
}

# ─── Test: files under MAX_LINES are not touched ────────────────────────────

test_small_files_untouched() {
  setup

  local metrics_file="$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/small.jsonl"
  generate_jsonl "$metrics_file" 100

  bash "$PROJECT_ROOT/hooks/metrics-rotation.sh" 2>/dev/null

  local lines
  lines=$(wc -l < "$metrics_file" | tr -d ' ')
  assert_eq "small file untouched: still 100 lines" "100" "$lines"

  # No archive should be created for this file
  local archive_count
  archive_count=$(find "$COGNITIVE_OS_PROJECT_DIR/.cognitive-os/metrics/.archive" -name "small-*.gz" 2>/dev/null | wc -l | tr -d ' ')
  assert_eq "small file: no archive created" "0" "$archive_count"

  teardown
}

# ─── Run all tests ───────────────────────────────────────────────────────────

test_rotation_truncates
test_archive_created
test_archive_is_gzipped
test_old_archive_deleted
test_small_files_untouched

echo "metrics-rotation: $TESTS tests, $FAILURES failures"
[ "$FAILURES" -eq 0 ] && exit 0 || exit 1
