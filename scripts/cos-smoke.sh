#!/usr/bin/env bash
# SCOPE: both
# ROLE: opt-in critical-path startup smoke; not the default broad test runner.
# CANONICAL: cos-test broad for default validation; use this only for startup wiring smoke.
# cos-smoke.sh — Run the COS critical-path e2e smoke suite.
#
# Usage:
#   bash scripts/cos-smoke.sh          # normal run
#   bash scripts/cos-smoke.sh -v       # verbose pytest output
#   bash scripts/cos-smoke.sh --help   # show this help
#
# Exit codes:
#   0  all 6 smoke steps passed
#   1  one or more steps failed
#   2  pytest not found

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERBOSE=""
for arg in "$@"; do
    case "$arg" in
        -v|--verbose) VERBOSE="-v" ;;
        --help|-h)
            grep '^#' "$0" | sed 's/^# \?//'
            exit 0
            ;;
    esac
done

if ! command -v pytest >/dev/null 2>&1; then
    echo "ERROR: pytest not found. Install with: pip install pytest pytest-timeout" >&2
    exit 2
fi

echo "=== COS Smoke Suite ==="
echo "repo: $REPO_ROOT"
echo "time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

START_TS=$(date +%s)

PYTHONPATH="$REPO_ROOT" pytest \
    "$REPO_ROOT/tests/e2e/test_cos_smoke.py" \
    -m e2e \
    --timeout=30 \
    --tb=short \
    --no-header \
    -q \
    $VERBOSE \
    "$@" 2>&1

EXIT_CODE=$?
END_TS=$(date +%s)
ELAPSED=$(( END_TS - START_TS ))

echo ""
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "PASS — smoke suite completed in ${ELAPSED}s"
else
    echo "FAIL — smoke suite failed in ${ELAPSED}s (exit $EXIT_CODE)"
fi

exit "$EXIT_CODE"
