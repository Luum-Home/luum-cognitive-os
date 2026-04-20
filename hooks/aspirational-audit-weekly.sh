#!/usr/bin/env bash
# SCOPE: os-only
# aspirational-audit-weekly.sh — SessionStart hook
#
# Runs aspirational-audit.py at most once every 7 days.
# Emits an advisory to stderr when dormant+aspirational ratio > 40%.
# Always exits 0 (fail-open — never blocks the session).
#
# Registration: SessionStart
# Killswitch:   respected (non-critical hook)

set -euo pipefail

# ── Killswitch check ────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib/killswitch_check.sh
if [[ -f "${SCRIPT_DIR}/_lib/killswitch_check.sh" ]]; then
    source "${SCRIPT_DIR}/_lib/killswitch_check.sh"
fi

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
METRICS_DIR="${PROJECT_DIR}/.cognitive-os/metrics"
MARKER_FILE="${METRICS_DIR}/.last-aspirational-audit"
AUDIT_SCRIPT="${PROJECT_DIR}/scripts/aspirational-audit.py"
SEVEN_DAYS_S=$((7 * 24 * 3600))

# ── Throttle: skip if last run < 7 days ago ──────────────────────────────────
if [[ -f "${MARKER_FILE}" ]]; then
    last_run=$(cat "${MARKER_FILE}" 2>/dev/null || echo "0")
    now=$(date +%s)
    age=$(( now - ${last_run%.*} ))
    if (( age < SEVEN_DAYS_S )); then
        exit 0
    fi
fi

# ── Python availability check ────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    exit 0
fi

if [[ ! -f "${AUDIT_SCRIPT}" ]]; then
    exit 0
fi

# ── Run audit in background with 30s timeout ─────────────────────────────────
SUMMARY_JSON=""
AUDIT_FAILED=0

run_audit() {
    timeout 30 python3 "${AUDIT_SCRIPT}" \
        --json \
        --project-root "${PROJECT_DIR}" \
        2>/dev/null
}

SUMMARY_JSON=$(run_audit 2>/dev/null) || AUDIT_FAILED=1

if [[ "${AUDIT_FAILED}" -eq 1 ]] || [[ -z "${SUMMARY_JSON}" ]]; then
    # Fail-open: audit failed, don't block session
    exit 0
fi

# Also trigger the full (write) run so JSONL and report are written
timeout 30 python3 "${AUDIT_SCRIPT}" \
    --project-root "${PROJECT_DIR}" \
    >/dev/null 2>&1 || true

# ── Parse ratio and emit advisory ────────────────────────────────────────────
ratio=$(echo "${SUMMARY_JSON}" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('dormant_aspirational_ratio', 0))
except Exception:
    print(0)
" 2>/dev/null || echo "0")

total=$(echo "${SUMMARY_JSON}" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('total', 0))
except Exception:
    print(0)
" 2>/dev/null || echo "0")

# Compare ratio > 0.40 using python (bash float arithmetic is unreliable)
is_high=$(python3 -c "print('1' if float('${ratio}') > 0.40 else '0')" 2>/dev/null || echo "0")

if [[ "${is_high}" == "1" ]]; then
    ratio_pct=$(python3 -c "print(f'{float(\"${ratio}\")*100:.0f}')" 2>/dev/null || echo "?")
    today=$(date +%Y-%m-%d)
    echo "📊 Aspirational audit: ${ratio_pct}% dormant/aspirational (${total} components). Review: docs/reports/aspirational-audit-${today}.md" >&2
fi

exit 0
