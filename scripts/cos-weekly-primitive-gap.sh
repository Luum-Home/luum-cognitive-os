#!/usr/bin/env bash
# SCOPE: os-only
# cos-weekly-primitive-gap.sh — local replacement for primitive-gap-audit.yml.
#
# Per ADR-131. Runs the full primitive-gap audit suite and writes outputs to
# docs/06-Daily/reports/, mirroring the workflow's behaviour but without committing or
# pushing. Operator can review and commit manually if desired.

set -uo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "$HOME/Projects/luum/luum-agent-os")"
cd "$REPO_ROOT"

echo "[cos-weekly-primitive-gap] $(date -u +%Y-%m-%dT%H:%M:%SZ) — start"

REPORTS=docs/06-Daily/reports
mkdir -p "$REPORTS"

run_step() {
  local label="$1"; shift
  echo "  ▶ $label"
  if "$@"; then
    echo "  ✓ $label"
  else
    echo "  ✗ $label (rc=$?)" >&2
  fi
}

run_step "primitive_gap_snapshot" \
  python3 scripts/primitive_gap_snapshot.py \
    --trend \
    --trend-path "$REPORTS/primitive-gap-history.jsonl" \
    --markdown "$REPORTS/primitive-gap-latest.md" \
    --regression-report "$REPORTS/primitive-gap-regressions.md" \
    --json
# stdout JSON discarded here; the markdown + regression files are the durable artifacts.

run_step "docs_duplicate_audit" \
  python3 scripts/docs_duplicate_audit.py \
    --baseline "$REPORTS/docs-duplicate-baseline.json" \
    --markdown "$REPORTS/docs-duplicate-latest.md"

run_step "primitive_row_audit" \
  python3 scripts/primitive_row_audit.py \
    --json-out "$REPORTS/primitive-row-audit-latest.json" \
    --md-out "$REPORTS/primitive-row-audit-latest.md"

run_step "claim_proof_audit" \
  python3 scripts/claim_proof_audit.py \
    --json-out "$REPORTS/claim-proof-latest.json" \
    --md-out "$REPORTS/claim-proof-latest.md"

run_step "reduction_backlog" \
  python3 scripts/reduction_backlog.py \
    --row-audit "$REPORTS/primitive-row-audit-latest.json" \
    --claim-audit "$REPORTS/claim-proof-latest.json" \
    --json-out "$REPORTS/reduction-backlog-latest.json" \
    --md-out "$REPORTS/reduction-backlog-latest.md"

run_step "primitive_surface_reduce (hooks)" \
  python3 scripts/primitive_surface_reduce.py \
    --family hooks \
    --plan \
    --json-out "$REPORTS/primitive-surface-reduction-latest.json" \
    --md-out "$REPORTS/primitive-surface-reduction-latest.md"

run_step "primitive_usage_map (scripts)" \
  python3 scripts/primitive_usage_map.py \
    --target-family scripts \
    --json-out "$REPORTS/primitive-usage-map-latest.json" \
    --md-out "$REPORTS/primitive-usage-map-latest.md"

run_step "primitive_coverage (json)" \
  python3 scripts/primitive_coverage.py \
    --adapter cognitive-os \
    --format json \
    --out "$REPORTS/primitive-coverage-latest.json"

run_step "primitive_coverage (markdown)" \
  python3 scripts/primitive_coverage.py \
    --adapter cognitive-os \
    --format markdown \
    --out "$REPORTS/primitive-coverage-latest.md"

run_step "docs_execution_audit" \
  python3 scripts/docs_execution_audit.py \
    --json-out "$REPORTS/docs-execution-latest.json" \
    --md-out "$REPORTS/docs-execution-latest.md"

echo "[cos-weekly-primitive-gap] outputs at $REPORTS/"
echo "[cos-weekly-primitive-gap] review and commit manually if changes warrant."
exit 0
