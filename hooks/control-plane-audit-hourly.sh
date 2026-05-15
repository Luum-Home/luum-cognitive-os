#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: primitive-coherence, postmortem-regression, periodic-drift
# ADR-248 hourly/session-end control-plane sweep with cooldown.
set -euo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime/control-plane-audit"
STAMP="$RUNTIME_DIR/hourly.last"
COOLDOWN_SECONDS="${COS_CONTROL_PLANE_HOURLY_COOLDOWN_SECONDS:-3600}"
mkdir -p "$RUNTIME_DIR" 2>/dev/null || true
now="$(date -u +%s)"
last=0
[ -f "$STAMP" ] && last="$(cat "$STAMP" 2>/dev/null || printf '0')"
if [ $((now - last)) -lt "$COOLDOWN_SECONDS" ]; then
  exit 0
fi
printf '%s\n' "$now" > "$STAMP" 2>/dev/null || true
COS_CONTROL_PLANE_AUDIT_LANE=hourly COS_CONTROL_PLANE_AUDIT_MODE=warn bash "$PROJECT_DIR/hooks/control-plane-audit.sh" </dev/null || true
