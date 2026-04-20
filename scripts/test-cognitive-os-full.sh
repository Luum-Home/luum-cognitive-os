#!/usr/bin/env bash
# SCOPE: os-only
# Cognitive OS Full Test Suite Runner
# Runs all 3 layers: Infrastructure, Behavior, Quality
# Usage: bash .cognitive-os/scripts/test-cognitive-os-full.sh [--skip-quality] [--skip-behavior]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AOS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$AOS_DIR/.." && pwd)"
INFRA_DIR="$AOS_DIR/tests/infra"
BEHAVIOR_DIR="$AOS_DIR/tests/behavior"
QUALITY_DIR="$AOS_DIR/tests/quality"
METRICS_DIR="$AOS_DIR/metrics"
RESULTS_FILE="$METRICS_DIR/test-results.jsonl"

SKIP_QUALITY=false
SKIP_BEHAVIOR=false

for arg in "$@"; do
  case "$arg" in
    --skip-quality) SKIP_QUALITY=true ;;
    --skip-behavior) SKIP_BEHAVIOR=true ;;
  esac
done

# Counters per layer
L1_PASS=0; L1_FAIL=0; L1_WARN=0
L2_PASS=0; L2_FAIL=0; L2_SKIP=0
L3_STATUS="skipped"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "================================================================"
echo "  Cognitive OS — Full Test Suite"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"
echo ""

# ============================================================
# Layer 1: Infrastructure Tests (must ALL pass to continue)
# ============================================================
echo "================================================================"
echo "  LAYER 1: Infrastructure Tests (deterministic)"
echo "================================================================"
echo ""

L1_RESULTS=()
L1_ALL_PASS=true

run_infra_test() {
  local test_file="$1"
  local name=$(basename "$test_file" .sh)

  echo "--- $name ---"
  OUTPUT=$(bash "$test_file" 2>&1)
  EXIT_CODE=$?
  echo "$OUTPUT"

  P=$(echo "$OUTPUT" | grep -E '^\s+PASS:' | tail -1 | awk '{print $2}' || echo "0")
  F=$(echo "$OUTPUT" | grep -E '^\s+FAIL:' | tail -1 | awk '{print $2}' || echo "0")
  W=$(echo "$OUTPUT" | grep -E '^\s+WARN:' | tail -1 | awk '{print $2}' || echo "0")
  P=${P:-0}; F=${F:-0}; W=${W:-0}

  L1_PASS=$((L1_PASS + P))
  L1_FAIL=$((L1_FAIL + F))
  L1_WARN=$((L1_WARN + W))

  if [ "$EXIT_CODE" -ne 0 ]; then
    L1_ALL_PASS=false
    L1_RESULTS+=("FAIL $name")
  else
    L1_RESULTS+=("PASS $name")
  fi
  echo ""
}

for test_file in "$INFRA_DIR"/test-*.sh; do
  [ ! -f "$test_file" ] && continue
  run_infra_test "$test_file"
done

echo "Layer 1 results: $L1_PASS pass, $L1_FAIL fail, $L1_WARN warn"
echo ""

if ! $L1_ALL_PASS; then
  echo "WARNING: Layer 1 has failures. Continuing to Layer 2 anyway for full report."
  echo ""
fi

# ============================================================
# Layer 2: Behavior Tests
# ============================================================
if $SKIP_BEHAVIOR; then
  echo "================================================================"
  echo "  LAYER 2: Behavior Tests — SKIPPED (--skip-behavior)"
  echo "================================================================"
  echo ""
else
  echo "================================================================"
  echo "  LAYER 2: Behavior Tests (semi-deterministic)"
  echo "================================================================"
  echo ""

  L2_RESULTS=()

  run_behavior_test() {
    local test_file="$1"
    local name=$(basename "$test_file" .sh)

    echo "--- $name ---"
    OUTPUT=$(bash "$test_file" 2>&1)
    EXIT_CODE=$?
    echo "$OUTPUT"

    P=$(echo "$OUTPUT" | grep -E '^\s+PASS:' | tail -1 | awk '{print $2}' || echo "0")
    F=$(echo "$OUTPUT" | grep -E '^\s+FAIL:' | tail -1 | awk '{print $2}' || echo "0")
    S=$(echo "$OUTPUT" | grep -E '^\s+SKIP:' | tail -1 | awk '{print $2}' || echo "0")
    P=${P:-0}; F=${F:-0}; S=${S:-0}

    L2_PASS=$((L2_PASS + P))
    L2_FAIL=$((L2_FAIL + F))
    L2_SKIP=$((L2_SKIP + S))

    if [ "$EXIT_CODE" -ne 0 ]; then
      L2_RESULTS+=("FAIL $name")
    else
      L2_RESULTS+=("PASS $name")
    fi
    echo ""
  }

  for test_file in "$BEHAVIOR_DIR"/test-*.sh; do
    [ ! -f "$test_file" ] && continue
    run_behavior_test "$test_file"
  done

  echo "Layer 2 results: $L2_PASS pass, $L2_FAIL fail, $L2_SKIP skip"
  echo ""
fi

# ============================================================
# Layer 3: Quality Tests (optional)
# ============================================================
if $SKIP_QUALITY; then
  echo "================================================================"
  echo "  LAYER 3: Quality Tests — SKIPPED (--skip-quality)"
  echo "================================================================"
  L3_STATUS="skipped"
  echo ""
else
  echo "================================================================"
  echo "  LAYER 3: Quality Tests (LLM-evaluated, optional)"
  echo "================================================================"
  echo ""

  QUALITY_RUNNER="$QUALITY_DIR/run-quality-tests.sh"
  if [ -f "$QUALITY_RUNNER" ]; then
    bash "$QUALITY_RUNNER" 2>&1
    if [ $? -eq 0 ]; then
      L3_STATUS="passed"
    else
      L3_STATUS="failed"
    fi
  else
    echo "  Quality test runner not found"
    L3_STATUS="missing"
  fi
  echo ""
fi

# ============================================================
# Final Summary
# ============================================================
echo "================================================================"
echo "  FULL TEST SUITE SUMMARY"
echo "================================================================"
echo ""
echo "  Layer 1 (Infra):    $L1_PASS pass, $L1_FAIL fail, $L1_WARN warn"
if ! $SKIP_BEHAVIOR; then
  echo "  Layer 2 (Behavior): $L2_PASS pass, $L2_FAIL fail, $L2_SKIP skip"
fi
echo "  Layer 3 (Quality):  $L3_STATUS"
echo ""

TOTAL_PASS=$((L1_PASS + L2_PASS))
TOTAL_FAIL=$((L1_FAIL + L2_FAIL))
TOTAL=$((TOTAL_PASS + TOTAL_FAIL))
if [ "$TOTAL" -gt 0 ]; then
  PASS_RATE=$((TOTAL_PASS * 100 / TOTAL))
else
  PASS_RATE=0
fi

echo "  Overall: $TOTAL_PASS/$TOTAL passed ($PASS_RATE%)"
echo ""

# ============================================================
# Save results to metrics
# ============================================================
mkdir -p "$METRICS_DIR"
cat >> "$RESULTS_FILE" << EOF
{"timestamp":"$TIMESTAMP","layer1":{"pass":$L1_PASS,"fail":$L1_FAIL,"warn":$L1_WARN},"layer2":{"pass":$L2_PASS,"fail":$L2_FAIL,"skip":$L2_SKIP},"layer3":"$L3_STATUS","total_pass":$TOTAL_PASS,"total_fail":$TOTAL_FAIL,"pass_rate":$PASS_RATE}
EOF

echo "  Results saved to: $RESULTS_FILE"
echo "================================================================"

[ "$TOTAL_FAIL" -gt 0 ] && exit 1
exit 0
