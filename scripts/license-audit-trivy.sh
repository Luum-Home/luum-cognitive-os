#!/usr/bin/env bash
# SCOPE: both
# license-audit-trivy.sh — Run Trivy license scan and produce structured output
#
# Outputs:
#   - .cognitive-os/reports/license-audit/license-audit-trivy-{TIMESTAMP}.json  (raw JSON)
#   - .cognitive-os/reports/license-audit/license-audit-trivy-latest.json        (copy of latest)
#   - stdout summary with findings count by severity
#
# Exit codes:
#   0 — clean (no UNKNOWN, HIGH, or CRITICAL license findings)
#   1 — findings present (UNKNOWN, HIGH, or CRITICAL)
#   2 — Trivy not installed or scan failed
#
# See: .cognitive-os/strategy/research/11-cross-stack-license-audit-tools.md
set -euo pipefail

PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}"
REPORT_DIR="${PROJECT_ROOT}/.cognitive-os/reports/license-audit"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_FILE="${REPORT_DIR}/license-audit-trivy-${TIMESTAMP}.json"
LATEST_LINK="${REPORT_DIR}/license-audit-trivy-latest.json"

if ! command -v trivy >/dev/null 2>&1; then
  echo "ERROR: trivy not found on PATH."
  echo "Install via: bash scripts/install-trivy.sh"
  exit 2
fi

mkdir -p "${REPORT_DIR}"

TRIVY_VERSION_OUTPUT="$(trivy --version 2>/dev/null | head -1 || true)"
case "${TRIVY_VERSION_OUTPUT}" in
  *0.69.4*|*0.69.5*|*0.69.6*)
    echo "ERROR: ${TRIVY_VERSION_OUTPUT} is blocked by ADR-212 due to the March 2026 Trivy supply-chain incident." >&2
    exit 2
    ;;
esac


echo "Running Trivy license scan on ${PROJECT_ROOT}..."
echo ""

# Run scan: license-only mode, all severity levels, structured JSON output
# --skip-dirs avoids noise from common artifact dirs
if ! trivy fs \
  --scanners license \
  --license-full \
  --severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL \
  --skip-dirs ".cognitive-os,node_modules,.venv,vendor,dist,build,.git,reference,.claude/plugins" \
  --format json \
  --output "${OUTPUT_FILE}" \
  --quiet \
  "${PROJECT_ROOT}" 2>&1; then
  echo "ERROR: Trivy scan failed."
  exit 2
fi

# Update "latest" pointer (copy, not symlink, for portability across stash ops)
cp "${OUTPUT_FILE}" "${LATEST_LINK}"

# Summarize
if command -v jq >/dev/null 2>&1; then
  echo "=== License findings summary ==="
  jq -r '
    [.Results[]?.Licenses[]?] as $licenses
    | reduce $licenses[] as $l ({}; .[$l.Severity // "UNKNOWN"] += 1)
    | to_entries
    | sort_by(.key)
    | .[]
    | "  \(.key): \(.value)"
  ' "${OUTPUT_FILE}" 2>/dev/null || echo "  (no findings or unexpected format)"
  echo ""

  # Top 10 critical/high findings
  echo "=== Top concerning findings ==="
  jq -r '
    [.Results[]? | .Target as $target | .Licenses[]? | select(.Severity == "CRITICAL" or .Severity == "HIGH" or .Severity == "UNKNOWN")
     | "  [\(.Severity)] \(.PkgName // "unknown") (\(.Name)) — \($target)"]
    | unique
    | .[0:10] | .[]
  ' "${OUTPUT_FILE}" 2>/dev/null || echo "  (none)"
  echo ""

  # Determine exit code based on findings
  CRITICAL_COUNT=$(jq -r '
    [.Results[]?.Licenses[]? | select(.Severity == "CRITICAL" or .Severity == "HIGH" or .Severity == "UNKNOWN")] | length
  ' "${OUTPUT_FILE}" 2>/dev/null || echo "0")

  echo "Output: ${OUTPUT_FILE}"
  echo "Latest pointer: ${LATEST_LINK}"
  echo ""

  if [ "${CRITICAL_COUNT}" -gt 0 ]; then
    echo "FINDINGS PRESENT: ${CRITICAL_COUNT} UNKNOWN/HIGH/CRITICAL license issues."
    exit 1
  else
    echo "CLEAN: no UNKNOWN/HIGH/CRITICAL license issues."
    exit 0
  fi
else
  echo "WARNING: jq not installed; skipping summary."
  echo "Raw output: ${OUTPUT_FILE}"
  echo "Install jq for human-readable summary: brew install jq"
  exit 0
fi
