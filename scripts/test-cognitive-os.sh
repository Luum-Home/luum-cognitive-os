#!/usr/bin/env bash
# SCOPE: os-only
# ROLE: legacy Layer-1 shell infrastructure runner.
# CANONICAL: cos-test cluster --lane hooks or targeted shell checks; keep this for compatibility with legacy infra tests.
# Cognitive OS Infrastructure Test Runner (Layer 1 only)
# Runs all infra tests and outputs a summary.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_DIR/tests/infra"

TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_WARN=0
RESULTS=()

echo "============================================"
echo "  Cognitive OS — Infrastructure Tests (Layer 1)"
echo "============================================"
echo ""

run_test() {
  local test_file="$1"
  local name=$(basename "$test_file" .sh)

  echo "--------------------------------------------"
  echo "  Running: $name"
  echo "--------------------------------------------"

  OUTPUT=$(bash "$test_file" 2>&1)
  EXIT_CODE=$?
  echo "$OUTPUT"

  # Extract summary counts
  P=$(echo "$OUTPUT" | grep -E '^\s+PASS:' | tail -1 | awk '{print $2}')
  F=$(echo "$OUTPUT" | grep -E '^\s+FAIL:' | tail -1 | awk '{print $2}')
  W=$(echo "$OUTPUT" | grep -E '^\s+WARN:' | tail -1 | awk '{print $2}')

  P=${P:-0}
  F=${F:-0}
  W=${W:-0}

  TOTAL_PASS=$((TOTAL_PASS + P))
  TOTAL_FAIL=$((TOTAL_FAIL + F))
  TOTAL_WARN=$((TOTAL_WARN + W))

  if [ "$EXIT_CODE" -eq 0 ]; then
    RESULTS+=("  PASS  $name ($P pass, $W warn)")
  else
    RESULTS+=("  FAIL  $name ($F fail, $P pass, $W warn)")
  fi

  echo ""
}

# Run each infra test
for test_file in "$TESTS_DIR"/test-*.sh; do
  [ ! -f "$test_file" ] && continue
  run_test "$test_file"
done

# Final summary
echo "============================================"
echo "  INFRASTRUCTURE TEST SUMMARY"
echo "============================================"
for r in "${RESULTS[@]}"; do
  echo "$r"
done
echo ""
echo "  Totals: $TOTAL_PASS pass, $TOTAL_FAIL fail, $TOTAL_WARN warn"
echo "============================================"

[ "$TOTAL_FAIL" -gt 0 ] && exit 1
exit 0
