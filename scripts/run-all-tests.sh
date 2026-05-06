#!/usr/bin/env bash
# SCOPE: both
# ROLE: legacy release/integrity sweep (Python + Go + file integrity).
# CANONICAL: cos-test broad for normal validation; use this only for release hardening or integrity audits.
# =============================================================================
# Cognitive OS — Full Test Suite (Python + Go + File Integrity)
# =============================================================================
# Usage: bash scripts/run-all-tests.sh [--quick] [--parallel]
#
# Runs ALL tests: Python (pytest) + Go (go test) + verifies no files deleted.
# Exit code: 0 if all pass, 1 if any failures.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

QUICK=false
PARALLEL=false
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=true ;;
    --parallel) PARALLEL=true ;;
  esac
done

echo "===================================="
echo "  Cognitive OS Full Test Suite"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "===================================="
echo ""

# ── File integrity: BEFORE ───────────────────────────────────────
HOOKS_BEFORE=$(ls hooks/*.sh 2>/dev/null | wc -l | tr -d ' ')
SKILLS_BEFORE=$(find skills/ -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
RULES_BEFORE=$(ls rules/*.md 2>/dev/null | wc -l | tr -d ' ')
LIBS_BEFORE=$(ls lib/*.py 2>/dev/null | wc -l | tr -d ' ')

echo "Files before: hooks=$HOOKS_BEFORE skills=$SKILLS_BEFORE rules=$RULES_BEFORE libs=$LIBS_BEFORE"
echo ""

FAILED=0

# ── Python tests ─────────────────────────────────────────────────
echo "=== Python Tests ==="
if [ "$QUICK" = true ]; then
  PYTEST_ARGS="-q --tb=line -x"
elif [ "$PARALLEL" = true ]; then
  PYTEST_ARGS="-q --tb=line -n auto"
else
  PYTEST_ARGS="-q --tb=line"
fi

if python3 -m pytest tests/ $PYTEST_ARGS; then
  echo "Python: PASS"
else
  echo "Python: FAIL"
  FAILED=1
fi
echo ""

# ── Go tests ─────────────────────────────────────────────────────
echo "=== Go Tests ==="
if (cd cmd/cos && go test ./... -count=1); then
  echo "Go: PASS"
else
  echo "Go: FAIL"
  FAILED=1
fi
echo ""

# ── File integrity: AFTER ────────────────────────────────────────
HOOKS_AFTER=$(ls hooks/*.sh 2>/dev/null | wc -l | tr -d ' ')
SKILLS_AFTER=$(find skills/ -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
RULES_AFTER=$(ls rules/*.md 2>/dev/null | wc -l | tr -d ' ')
LIBS_AFTER=$(ls lib/*.py 2>/dev/null | wc -l | tr -d ' ')

echo "=== File Integrity ==="
echo "Files after:  hooks=$HOOKS_AFTER skills=$SKILLS_AFTER rules=$RULES_AFTER libs=$LIBS_AFTER"

if [ "$HOOKS_BEFORE" != "$HOOKS_AFTER" ] || \
   [ "$SKILLS_BEFORE" != "$SKILLS_AFTER" ] || \
   [ "$RULES_BEFORE" != "$RULES_AFTER" ] || \
   [ "$LIBS_BEFORE" != "$LIBS_AFTER" ]; then
  echo ""
  echo "!!! FILE INTEGRITY VIOLATION !!!"
  echo "Files were deleted or created during test run."
  echo "  hooks:  $HOOKS_BEFORE -> $HOOKS_AFTER"
  echo "  skills: $SKILLS_BEFORE -> $SKILLS_AFTER"
  echo "  rules:  $RULES_BEFORE -> $RULES_AFTER"
  echo "  libs:   $LIBS_BEFORE -> $LIBS_AFTER"
  FAILED=1
else
  echo "File integrity: PASS (no files lost)"
fi
echo ""

# ── Git status check ─────────────────────────────────────────────
echo "=== Git Status ==="
DIRTY=$(git status --short | wc -l | tr -d ' ')
if [ "$DIRTY" -gt 0 ]; then
  echo "WARNING: $DIRTY uncommitted changes"
  git status --short | head -5
else
  echo "Working tree: clean"
fi
echo ""

# ── Summary ──────────────────────────────────────────────────────
echo "===================================="
if [ "$FAILED" -eq 0 ]; then
  echo "  ALL TESTS PASSED"
else
  echo "  SOME TESTS FAILED"
fi
echo "===================================="

exit $FAILED
