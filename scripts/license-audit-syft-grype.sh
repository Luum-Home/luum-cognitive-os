#!/usr/bin/env bash
# SCOPE: project
# license-audit-syft-grype.sh — Primary ADR-212 cross-stack SBOM + vulnerability/license audit
set -euo pipefail

PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}"
REPORT_DIR="${PROJECT_ROOT}/.cognitive-os/reports/license-audit"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SBOM_FILE="${REPORT_DIR}/syft-sbom-${TIMESTAMP}.spdx.json"
GRYPE_FILE="${REPORT_DIR}/grype-scan-${TIMESTAMP}.json"
LATEST_SBOM="${REPORT_DIR}/syft-sbom-latest.spdx.json"
LATEST_GRYPE="${REPORT_DIR}/grype-scan-latest.json"

if ! command -v syft >/dev/null 2>&1; then
  echo "ERROR: syft not found on PATH. Install via: bash scripts/install-syft-grype.sh" >&2
  exit 2
fi
if ! command -v grype >/dev/null 2>&1; then
  echo "ERROR: grype not found on PATH. Install via: bash scripts/install-syft-grype.sh" >&2
  exit 2
fi

mkdir -p "${REPORT_DIR}"

echo "Generating Syft SBOM for ${PROJECT_ROOT}..."
syft "${PROJECT_ROOT}" -o spdx-json > "${SBOM_FILE}"
cp "${SBOM_FILE}" "${LATEST_SBOM}"

echo "Scanning SBOM with Grype..."
if ! grype "sbom:${SBOM_FILE}" -o json > "${GRYPE_FILE}"; then
  echo "ERROR: grype scan failed." >&2
  exit 2
fi
cp "${GRYPE_FILE}" "${LATEST_GRYPE}"

if command -v jq >/dev/null 2>&1; then
  MATCHES=$(jq '[.matches[]?] | length' "${GRYPE_FILE}" 2>/dev/null || echo "0")
  HIGH=$(jq '[.matches[]? | select(.vulnerability.severity == "High" or .vulnerability.severity == "Critical")] | length' "${GRYPE_FILE}" 2>/dev/null || echo "0")
  echo "SBOM: ${SBOM_FILE}"
  echo "Scan: ${GRYPE_FILE}"
  echo "Findings: ${MATCHES} total; ${HIGH} high/critical"
  if [ "${HIGH}" -gt 0 ]; then
    exit 1
  fi
else
  echo "SBOM: ${SBOM_FILE}"
  echo "Scan: ${GRYPE_FILE}"
  echo "WARNING: jq not installed; cannot summarize severity."
fi
