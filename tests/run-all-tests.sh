#!/usr/bin/env bash
# run-all-tests.sh — Master test runner for Cognitive OS
set -uo pipefail

TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
PASSED=0
FAILED=0
SKIPPED=0
FAILED_TESTS=""

run_test() {
  local test_file="$1"
  local test_name
  test_name=$(basename "$test_file" .sh)
  printf "  %-40s " "$test_name"
  local output
  output=$(bash "$test_file" 2>&1)
  local rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "PASS"
    PASSED=$((PASSED + 1))
  else
    echo "FAIL"
    FAILED=$((FAILED + 1))
    FAILED_TESTS="$FAILED_TESTS    $test_name\n"
    # Show failure details indented
    echo "$output" | grep -E 'FAIL:' | sed 's/^/      /'
  fi
}

echo "=== Cognitive OS Test Suite ==="
echo ""
echo "Unit Tests:"
for t in "$TESTS_DIR"/unit/test-*.sh; do
  [ -f "$t" ] && run_test "$t"
done

echo ""
echo "Integration Tests:"
for t in "$TESTS_DIR"/integration/test-*.sh; do
  [ -f "$t" ] && run_test "$t"
done

echo ""
echo "Infrastructure Tests:"
if command -v docker >/dev/null 2>&1; then
  for t in "$TESTS_DIR"/infra/test-docker*.sh; do
    [ -f "$t" ] && run_test "$t"
  done
else
  echo "  (skipped -- Docker not available)"
  SKIPPED=$((SKIPPED + 1))
fi

echo ""
echo "=== Results: $PASSED passed, $FAILED failed, $SKIPPED skipped ==="

if [ -n "$FAILED_TESTS" ]; then
  echo ""
  echo "Failed tests:"
  printf "$FAILED_TESTS"
fi

[ "$FAILED" -eq 0 ] && exit 0 || exit 1
