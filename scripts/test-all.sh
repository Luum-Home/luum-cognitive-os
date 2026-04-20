#!/usr/bin/env bash
# SCOPE: os-only
# =============================================================================
# test-all.sh — Unified Cognitive OS Test Runner
# =============================================================================
# Runs ALL test suites: pytest (unit + integration) + bash layers (infra/behavior)
# Uses pytest-xdist for parallel execution when available.
#
# Usage:
#   bash scripts/test-all.sh                    # Full suite
#   bash scripts/test-all.sh --unit             # Unit tests only (fast, ~5s)
#   bash scripts/test-all.sh --integration      # Integration tests only (Docker required)
#   bash scripts/test-all.sh --no-docker        # Skip Docker-dependent tests
#   bash scripts/test-all.sh --parallel N       # Force N parallel workers (default: auto)
#   bash scripts/test-all.sh --help
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Defaults
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_BASH_LAYERS=true
PARALLEL="auto"
VERBOSE=""

for arg in "$@"; do
  case "$arg" in
    --unit)          RUN_INTEGRATION=false; RUN_BASH_LAYERS=false ;;
    --integration)   RUN_UNIT=false; RUN_BASH_LAYERS=false ;;
    --no-docker)     RUN_INTEGRATION=false ;;
    --verbose|-v)    VERBOSE="-v" ;;
    --parallel)      shift; PARALLEL="${1:-auto}" ;;
    --help|-h)
      echo "Usage: bash scripts/test-all.sh [--unit|--integration|--no-docker|--parallel N|-v|--help]"
      echo ""
      echo "  --unit          Unit tests only (fast, no Docker)"
      echo "  --integration   Integration tests only (requires Docker)"
      echo "  --no-docker     Skip Docker-dependent tests"
      echo "  --parallel N    Number of parallel workers (default: auto-detect CPUs)"
      echo "  -v, --verbose   Verbose pytest output"
      echo "  --help          Show this help"
      exit 0
      ;;
  esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

TOTAL_PASS=0
TOTAL_FAIL=0
TOTAL_SKIP=0
RESULTS=()
START_TIME=$(date +%s)

echo ""
echo "================================================================"
echo -e "  ${CYAN}Cognitive OS — Unified Test Runner${NC}"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================================"
echo ""

# Check for pytest-xdist
XDIST_FLAG=""
if python3 -c "import xdist" 2>/dev/null; then
  XDIST_FLAG="-n $PARALLEL"
  echo -e "  ${GREEN}pytest-xdist detected${NC} — parallel execution enabled (workers: $PARALLEL)"
else
  echo -e "  ${YELLOW}pytest-xdist not found${NC} — running sequentially"
  echo "  Install with: pip3 install pytest-xdist"
fi
echo ""

# ============================================================
# Phase 1: Unit Tests (fast, no dependencies)
# ============================================================
if $RUN_UNIT; then
  echo "================================================================"
  echo -e "  ${CYAN}PHASE 1: Unit Tests${NC} (parallel via xdist)"
  echo "================================================================"
  echo ""

  UNIT_OUTPUT=$(python3 -m pytest tests/unit/ $XDIST_FLAG $VERBOSE --tb=short -q 2>&1)
  UNIT_EXIT=$?
  echo "$UNIT_OUTPUT"

  # Extract counts from pytest summary line: "N passed, M failed, P skipped"
  UNIT_PASS=$(echo "$UNIT_OUTPUT" | grep -oE '[0-9]+ passed' | awk '{print $1}' || echo 0)
  UNIT_FAIL=$(echo "$UNIT_OUTPUT" | grep -oE '[0-9]+ failed' | awk '{print $1}' || echo 0)
  UNIT_SKIP=$(echo "$UNIT_OUTPUT" | grep -oE '[0-9]+ skipped' | awk '{print $1}' || echo 0)
  UNIT_PASS=${UNIT_PASS:-0}; UNIT_FAIL=${UNIT_FAIL:-0}; UNIT_SKIP=${UNIT_SKIP:-0}

  TOTAL_PASS=$((TOTAL_PASS + UNIT_PASS))
  TOTAL_FAIL=$((TOTAL_FAIL + UNIT_FAIL))
  TOTAL_SKIP=$((TOTAL_SKIP + UNIT_SKIP))

  if [ "$UNIT_EXIT" -eq 0 ]; then
    RESULTS+=("$(echo -e "${GREEN}PASS${NC}  Unit tests ($UNIT_PASS passed, $UNIT_SKIP skipped)")")
  else
    RESULTS+=("$(echo -e "${RED}FAIL${NC}  Unit tests ($UNIT_FAIL failed, $UNIT_PASS passed)")")
  fi
  echo ""
fi

# ============================================================
# Phase 2: Integration Tests (Docker required, sequential)
# ============================================================
if $RUN_INTEGRATION; then
  # Check Docker availability
  if ! docker info >/dev/null 2>&1; then
    echo "================================================================"
    echo -e "  ${YELLOW}PHASE 2: Integration Tests — SKIPPED (Docker not running)${NC}"
    echo "================================================================"
    RESULTS+=("$(echo -e "${YELLOW}SKIP${NC}  Integration tests (Docker not running)")")
  else
    echo "================================================================"
    echo -e "  ${CYAN}PHASE 2: Integration Tests${NC} (sequential — Docker containers)"
    echo "================================================================"
    echo ""

    # Integration tests run sequentially (containers may share ports via testcontainers)
    # Use longer timeout (300s per test via conftest.py override)
    INT_OUTPUT=$(python3 -m pytest tests/integration/ $VERBOSE --tb=short -q \
      -m "not slow" \
      --timeout=300 2>&1)
    INT_EXIT=$?
    echo "$INT_OUTPUT"

    INT_PASS=$(echo "$INT_OUTPUT" | grep -oE '[0-9]+ passed' | awk '{print $1}' || echo 0)
    INT_FAIL=$(echo "$INT_OUTPUT" | grep -oE '[0-9]+ failed' | awk '{print $1}' || echo 0)
    INT_SKIP=$(echo "$INT_OUTPUT" | grep -oE '[0-9]+ skipped' | awk '{print $1}' || echo 0)
    INT_PASS=${INT_PASS:-0}; INT_FAIL=${INT_FAIL:-0}; INT_SKIP=${INT_SKIP:-0}

    TOTAL_PASS=$((TOTAL_PASS + INT_PASS))
    TOTAL_FAIL=$((TOTAL_FAIL + INT_FAIL))
    TOTAL_SKIP=$((TOTAL_SKIP + INT_SKIP))

    if [ "$INT_EXIT" -eq 0 ]; then
      RESULTS+=("$(echo -e "${GREEN}PASS${NC}  Integration tests ($INT_PASS passed, $INT_SKIP skipped)")")
    else
      RESULTS+=("$(echo -e "${RED}FAIL${NC}  Integration tests ($INT_FAIL failed, $INT_PASS passed)")")
    fi
  fi
  echo ""
fi

# ============================================================
# Phase 3: Bash Layer Tests (infra + behavior)
# ============================================================
if $RUN_BASH_LAYERS; then
  echo "================================================================"
  echo -e "  ${CYAN}PHASE 3: Bash Layer Tests${NC} (infra + behavior)"
  echo "================================================================"
  echo ""

  for layer_script in "$SCRIPT_DIR"/test-cognitive-os.sh; do
    if [ -f "$layer_script" ]; then
      LAYER_NAME=$(basename "$layer_script" .sh)
      echo "--- Running: $LAYER_NAME ---"
      LAYER_OUTPUT=$(bash "$layer_script" 2>&1)
      LAYER_EXIT=$?

      LP=$(echo "$LAYER_OUTPUT" | grep -oE '[0-9]+ pass' | tail -1 | awk '{print $1}' || echo 0)
      LF=$(echo "$LAYER_OUTPUT" | grep -oE '[0-9]+ fail' | tail -1 | awk '{print $1}' || echo 0)
      LP=${LP:-0}; LF=${LF:-0}

      TOTAL_PASS=$((TOTAL_PASS + LP))
      TOTAL_FAIL=$((TOTAL_FAIL + LF))

      if [ "$LAYER_EXIT" -eq 0 ]; then
        RESULTS+=("$(echo -e "${GREEN}PASS${NC}  $LAYER_NAME ($LP passed)")")
      else
        RESULTS+=("$(echo -e "${RED}FAIL${NC}  $LAYER_NAME ($LF failed, $LP passed)")")
      fi
      echo ""
    fi
  done
fi

# ============================================================
# Summary
# ============================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "================================================================"
echo -e "  ${CYAN}TEST SUITE SUMMARY${NC}"
echo "================================================================"
echo ""
for r in "${RESULTS[@]}"; do
  echo "  $r"
done
echo ""

TOTAL=$((TOTAL_PASS + TOTAL_FAIL))
if [ "$TOTAL" -gt 0 ]; then
  PASS_RATE=$((TOTAL_PASS * 100 / TOTAL))
else
  PASS_RATE=0
fi

if [ "$TOTAL_FAIL" -eq 0 ]; then
  echo -e "  ${GREEN}ALL PASSED${NC}: $TOTAL_PASS tests ($TOTAL_SKIP skipped) in ${DURATION}s"
else
  echo -e "  ${RED}FAILURES${NC}: $TOTAL_FAIL failed, $TOTAL_PASS passed ($PASS_RATE%) in ${DURATION}s"
fi
echo "================================================================"

[ "$TOTAL_FAIL" -gt 0 ] && exit 1
exit 0
