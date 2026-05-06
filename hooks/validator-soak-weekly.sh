#!/usr/bin/env bash
# SCOPE: os-only
# validator-soak-weekly.sh — SessionStart hook
#
# Runs evaluate_validator_soak() at most once every 7 days.
# When the FP rate is below threshold and enough soak data exists, emits a
# propose-only promotion artifact (advisory → blocking).  Never blocks the
# session — always exits 0.
#
# Registration: SessionStart
# Killswitch:   respected (non-critical hook)
# ADR:          ADR-174-bis Part B

set -euo pipefail

# ── Killswitch check ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/_lib/killswitch_check.sh" ]]; then
    # shellcheck source=_lib/killswitch_check.sh
    source "${SCRIPT_DIR}/_lib/killswitch_check.sh"
fi

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
METRICS_DIR="${PROJECT_DIR}/.cognitive-os/metrics"
MARKER_FILE="${METRICS_DIR}/.last-validator-soak-eval"
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

# ── Python availability check ─────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    exit 0
fi

# ── Run evaluator ─────────────────────────────────────────────────────────────
# cd to project root so `lib.validator_soak_evaluator` is importable as a module
cd "${PROJECT_DIR}"

RESULT=$(python3 -m lib.validator_soak_evaluator \
    --soak-days 30 \
    --fp-threshold 0.05 \
    --min-entries 30 \
    2>/dev/null || echo "{}")

PROPOSAL_EMITTED=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('proposal_emitted','false'))" 2>/dev/null || echo "false")
PROPOSAL_PATH=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('proposal_path') or '')" 2>/dev/null || echo "")

if [[ "$PROPOSAL_EMITTED" == "True" ]] && [[ -n "$PROPOSAL_PATH" ]]; then
    echo "⚑ validator-soak-weekly: promotion proposal emitted → ${PROPOSAL_PATH}" >&2
fi

# ── Update marker ─────────────────────────────────────────────────────────────
mkdir -p "${METRICS_DIR}"
date +%s > "${MARKER_FILE}"

exit 0
