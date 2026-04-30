#!/usr/bin/env bash
# SCOPE: project
# pre-commit-gate.sh — Git pre-commit hook that gates commits on structural checks
#
# ADR-028 D4 fix (2026-04-20): Removed inline pytest block (BLOCKER — test_run_inside_hook).
# Pytest is owned exclusively by hooks/global-verify.sh (ADR-027 Phase 1).
# Running the full test suite inside a pre-commit hook blocks VCS operations
# indefinitely and re-introduces the WS11 orphan-process pattern.
#
# This hook now performs only structural checks:
#   1. Coverage artifact check (advisory warn only, never blocks)
#   2. Content-policy check on staged files
#
# Full test verification: run `bash hooks/global-verify.sh` before committing,
# or rely on CI. Do NOT add pytest back here.
#
# Environment variables:
#   COVERAGE_THRESHOLD  — minimum composite coverage % (default: 80)
#
# Exit codes:
#   0 — structural checks pass, commit allowed
#   1 — content policy violation, commit blocked
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

COVERAGE_THRESHOLD="${COVERAGE_THRESHOLD:-80}"
METRICS_DIR="$ROOT_DIR/.cognitive-os/metrics"
COVERAGE_HISTORY="$METRICS_DIR/coverage-history.jsonl"

# ─── Step 1 (formerly Step 2): Check persisted coverage artifact ─────────────
#
# This git hook must not launch test or coverage runs. Coverage measurement is
# produced explicitly by tests/coverage-report.sh; the gate only consumes the
# latest persisted summary/json artifact.

artifact_helper="$ROOT_DIR/scripts/cos_test_artifact_status.py"

if [ -f "$artifact_helper" ] && command -v python3 >/dev/null 2>&1; then
  coverage_status_json=$(
    python3 "$artifact_helper" \
      --project-root "$ROOT_DIR" \
      --artifact-kind coverage \
      --coverage-threshold "$COVERAGE_THRESHOLD" \
      --json 2>/dev/null || true
  )

  if [ -n "$coverage_status_json" ]; then
    coverage_pct=$(printf '%s' "$coverage_status_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("coverage_pct",""))' 2>/dev/null || true)
    coverage_status=$(printf '%s' "$coverage_status_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("status","missing"))' 2>/dev/null || echo "missing")
    coverage_run=$(printf '%s' "$coverage_status_json" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("run_dir",""))' 2>/dev/null || true)

    if [ -n "$coverage_pct" ] && [ "$coverage_status" = "fail" ]; then
      echo "WARNING: Persisted composite coverage ${coverage_pct}% is below threshold ${COVERAGE_THRESHOLD}%" >&2
      [ -n "$coverage_run" ] && echo "  Artifact: $coverage_run" >&2
      echo "Run tests/coverage-report.sh to refresh coverage evidence before release." >&2
      # Warning only — does NOT block the commit
    fi

    # Persist coverage measurement to history for singularity.py to consume.
    if [ -n "$coverage_pct" ]; then
      mkdir -p "$METRICS_DIR"
      COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
      TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
      artifact_run_json=$(printf '%s' "$coverage_run" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo '""')
      printf '{"timestamp":"%s","source":"pre-commit-gate","event_type":"coverage_measurement","payload":{"coverage_pct":%s,"commit_sha":"%s","threshold":%s,"artifact_run":%s}}\n' \
        "$TIMESTAMP" "$coverage_pct" "$COMMIT_SHA" "$COVERAGE_THRESHOLD" "$artifact_run_json" \
        >> "$COVERAGE_HISTORY"
    fi
  fi
fi

# ─── Step 2 (formerly Step 3): Content policy check ───────────────────────────

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
