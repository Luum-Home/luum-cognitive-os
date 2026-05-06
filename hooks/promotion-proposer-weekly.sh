#!/usr/bin/env bash
# SCOPE: os-only
# promotion-proposer-weekly.sh — SessionStart hook (ADR-178)
#
# Runs cos-promotion-proposer at most once every 7 days.
# Async, non-blocking, fail-open. Always exits 0.
#
# Killswitch: DISABLE_PROMOTION_PROPOSER=1 env (respected by the python script).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_lib/killswitch_check.sh
if [[ -f "${SCRIPT_DIR}/_lib/killswitch_check.sh" ]]; then
    source "${SCRIPT_DIR}/_lib/killswitch_check.sh"
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
METRICS_DIR="${PROJECT_DIR}/.cognitive-os/metrics"
MARKER_FILE="${METRICS_DIR}/.last-promotion-proposer"
PROPOSER_SCRIPT="${PROJECT_DIR}/scripts/cos_promotion_proposer.py"
SEVEN_DAYS_S=$((7 * 24 * 3600))

mkdir -p "${METRICS_DIR}" 2>/dev/null || exit 0

# ── Throttle: skip if last run < 7 days ago ──────────────────────────────────
if [[ -f "${MARKER_FILE}" ]]; then
    last_run=$(cat "${MARKER_FILE}" 2>/dev/null || echo "0")
    now=$(date +%s)
    age=$(( now - ${last_run%.*} ))
    if (( age < SEVEN_DAYS_S )); then
        exit 0
    fi
fi

# ── Killswitch via env ────────────────────────────────────────────────────────
if [[ "${DISABLE_PROMOTION_PROPOSER:-}" == "1" ]]; then
    exit 0
fi

# ── Python availability ──────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    exit 0
fi

if [[ ! -f "${PROPOSER_SCRIPT}" ]]; then
    exit 0
fi

# Run with --apply to materialize proposal artifacts. Fail-open.
python3 "${PROPOSER_SCRIPT}" --apply >/dev/null 2>&1 || true

# Update marker (best-effort)
date +%s > "${MARKER_FILE}" 2>/dev/null || true

exit 0
