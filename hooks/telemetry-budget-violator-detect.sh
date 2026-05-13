#!/usr/bin/env bash
# SCOPE: os-only
# Hourly lane hook (ADR-304): aggregates telemetry streams against
# manifests/observability-slo.yaml and appends breach findings to the
# control-plane remediation queue.
#
# Idempotent (stable_id dedupes), fail-silent (exit 0 contract for hourly lane).

set -u
PROJECT_DIR="${COS_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Prefer .venv, fall back to system python3.
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="python3"

"$PYTHON_BIN" scripts/cos-telemetry-aggregate --lane hourly --quiet >/dev/null 2>&1 || true
exit 0
