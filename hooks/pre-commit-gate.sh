#!/usr/bin/env bash
# SCOPE: both
# pre-commit-gate.sh — Git pre-commit hook that gates commits on test health
#
# 1. Runs pytest and blocks commit if any tests fail
# 2. Runs coverage-report.sh and warns if composite coverage drops below threshold
# 3. Supports --no-verify (standard git behavior, handled by git itself)
#
# Environment variables:
#   COVERAGE_THRESHOLD  — minimum composite coverage % (default: 80)
#
# Exit codes:
#   0 — all tests pass, commit allowed
#   1 — tests failing, commit blocked
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

COVERAGE_THRESHOLD="${COVERAGE_THRESHOLD:-80}"

# ─── Step 1: Run tests ──────────────────────────────────────────────────────

test_output=$(python3 -m pytest tests/ -q --tb=no 2>&1 | tail -1)

# Check for failures — pytest summary line looks like "N failed, M passed"
# or "N passed" (all pass) or "no tests ran"
if echo "$test_output" | grep -qiE '[0-9]+ failed'; then
  # Extract the failure count
  failed_count=$(echo "$test_output" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+')
  echo "COMMIT BLOCKED: ${failed_count} tests failing" >&2
  echo "Test output: ${test_output}" >&2
  exit 1
fi

# Also block if pytest itself errored (no "passed" in output and non-empty)
if [ -n "$test_output" ] && ! echo "$test_output" | grep -qiE 'passed|no tests ran'; then
  echo "COMMIT BLOCKED: test suite did not complete successfully" >&2
  echo "Test output: ${test_output}" >&2
  exit 1
fi

# ─── Step 2: Check coverage ─────────────────────────────────────────────────

coverage_report="$ROOT_DIR/tests/coverage-report.sh"

if [ -f "$coverage_report" ]; then
  composite_line=$(bash "$coverage_report" 2>&1 | grep -i 'Composite')

  if [ -n "$composite_line" ]; then
    # Extract the percentage number from the Composite line
    coverage_pct=$(echo "$composite_line" | grep -oE '[0-9]+%' | head -1 | tr -d '%')

    if [ -n "$coverage_pct" ] && [ "$coverage_pct" -lt "$COVERAGE_THRESHOLD" ]; then
      echo "WARNING: Composite coverage ${coverage_pct}% is below threshold ${COVERAGE_THRESHOLD}%" >&2
      echo "Consider adding tests before committing." >&2
      # Warning only — does NOT block the commit
    fi
  fi
fi

# ─── Step 3: Content policy check ─────────────────────────────────────────────

POLICY_FILE="$ROOT_DIR/.cognitive-os/content-policy.yaml"

if [ -f "$POLICY_FILE" ]; then
  POLICY_VIOLATIONS=0

  # Get staged files
  staged_files=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)

  if [ -n "$staged_files" ]; then
    # Extract prohibited terms from YAML
    terms=$(grep '  - term:' "$POLICY_FILE" 2>/dev/null | sed 's/.*term:[[:space:]]*//' | tr -d '"' | tr -d "'")

    for term in $terms; do
      if [ -z "$term" ]; then
        continue
      fi
      # Check each staged file for the term
      matches=""
      while IFS= read -r sfile; do
        if [ -f "$ROOT_DIR/$sfile" ] && grep -qil "$term" "$ROOT_DIR/$sfile" 2>/dev/null; then
          matches="$matches $sfile"
        fi
      done <<EOF
$staged_files
EOF
      if [ -n "$matches" ]; then
        reason=$(grep -A1 "term:.*$term" "$POLICY_FILE" 2>/dev/null | grep "reason:" | head -1 | sed 's/.*reason:[[:space:]]*//' | tr -d '"' | tr -d "'")
        echo "CONTENT POLICY VIOLATION: '$term' found in staged files" >&2
        echo "  Reason: $reason" >&2
        echo "  Files:$matches" >&2
        POLICY_VIOLATIONS=$((POLICY_VIOLATIONS + 1))
      fi
    done

    if [ "$POLICY_VIOLATIONS" -gt 0 ]; then
      echo "COMMIT BLOCKED: $POLICY_VIOLATIONS content policy violation(s) found" >&2
      echo "Edit .cognitive-os/content-policy.yaml to manage prohibited terms." >&2
      exit 1
    fi
  fi
fi

# ─── All clear ───────────────────────────────────────────────────────────────

exit 0
