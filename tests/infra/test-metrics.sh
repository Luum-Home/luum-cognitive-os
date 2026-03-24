#!/usr/bin/env bash
# Layer 1: Metrics Infrastructure Tests
# Verifies metrics directory and JSONL file validity.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
METRICS_DIR="$AOS/metrics"

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
warn() { WARN=$((WARN + 1)); echo "  WARN: $1"; }

echo "=== METRICS INFRASTRUCTURE TESTS ==="
echo ""

# ---- Test 1: Metrics directory exists ----
if [ -d "$METRICS_DIR" ]; then
  pass "Metrics directory exists"
else
  fail "Metrics directory missing: $METRICS_DIR"
  echo ""
  echo "=== METRICS SUMMARY ==="
  echo "  PASS: $PASS  FAIL: $FAIL  WARN: $WARN"
  exit 1
fi

# ---- Test 2: JSONL files are valid ----
echo ""
echo "--- JSONL validation ---"
for jsonl in "$METRICS_DIR"/*.jsonl; do
  [ ! -f "$jsonl" ] && continue
  name=$(basename "$jsonl")
  lines=$(wc -l < "$jsonl" | tr -d ' ')

  if [ "$lines" -eq 0 ]; then
    pass "$name: empty (0 lines)"
    continue
  fi

  # Validate each non-empty line is valid JSON
  INVALID=0
  LINE_NUM=0
  while IFS= read -r line; do
    LINE_NUM=$((LINE_NUM + 1))
    [ -z "$line" ] && continue
    if ! echo "$line" | python3 -c "import json,sys; json.loads(sys.stdin.read())" 2>/dev/null; then
      INVALID=$((INVALID + 1))
      if [ "$INVALID" -le 3 ]; then
        echo "    Invalid JSON at line $LINE_NUM in $name"
      fi
    fi
  done < "$jsonl"

  if [ "$INVALID" -eq 0 ]; then
    pass "$name: valid ($lines lines)"
  else
    fail "$name: $INVALID/$lines lines are invalid JSON"
  fi
done

# ---- Test 3: Report line counts ----
echo ""
echo "--- Metrics file sizes ---"
for jsonl in "$METRICS_DIR"/*.jsonl; do
  [ ! -f "$jsonl" ] && continue
  name=$(basename "$jsonl")
  lines=$(wc -l < "$jsonl" | tr -d ' ')
  size=$(wc -c < "$jsonl" | tr -d ' ')
  echo "  $name: $lines lines, $size bytes"
done

# ---- Summary ----
echo ""
echo "=== METRICS SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  WARN: $WARN"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
