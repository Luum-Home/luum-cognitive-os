#!/usr/bin/env bash
# SCOPE: os-only
# eas-validation-gate.sh — EAS validation gate for review surfaces.
#
# Trigger: Stop hook (blocks session stop when active review surface has
# uncovered EAS rows) or invoked directly by sdd-verify / code-review flows.
#
# Surface detection (in priority order):
#   1. COS_REVIEW_SURFACE env var — set by skill or orchestrator before invoke.
#      Valid values: sdd-verify, pr-review, code-review, doc-review
#   2. COS_EAS_PATH env var — explicit path to EAS Markdown file to validate.
#   3. No surface set → no-op (exit 0). Hook is safe to install globally.
#
# Exit behavior (Claude Code Stop hook protocol — ADR-064):
#   exit 0, no JSON      — allow (no review surface or validation passed)
#   exit 0, JSON block   — block stop with context when errors found
#
# Performance: <500ms for empty surface (early exit 0 before any Python).
#
# ADR-319 + ADR-324: EAS validation gate implementation.

set -uo pipefail

# A/B benchmark master kill-switch
[ "${COS_DISABLE_ALL_GOVERNANCE:-}" = "1" ] && exit 0

# Runtime disable
[ "${DISABLE_HOOK_EAS_VALIDATION_GATE:-}" = "true" ] && exit 0

# Fast path: if no review surface is set, this hook is a no-op.
REVIEW_SURFACE="${COS_REVIEW_SURFACE:-}"
EAS_PATH="${COS_EAS_PATH:-}"

if [ -z "$REVIEW_SURFACE" ] && [ -z "$EAS_PATH" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}}}"

# Drain stdin (required by Stop hook protocol) but ignore content.
_STDIN=$(cat 2>/dev/null || true)

# Python must be available; degrade safely if not.
if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

# Locate EAS file: prefer explicit path, then auto-discover by surface.
_resolve_eas_path() {
  if [ -n "$EAS_PATH" ]; then
    echo "$EAS_PATH"
    return
  fi

  # Convention: EAS files live in openspec/changes/*/eas.md or docs/ tree.
  local candidates
  candidates=$(find "$PROJECT_DIR/openspec/changes" -name "eas.md" 2>/dev/null | head -5)
  if [ -z "$candidates" ]; then
    candidates=$(find "$PROJECT_DIR/docs" -name "eas.md" 2>/dev/null | head -5)
  fi

  echo "$candidates"
}

EAS_FILES=$(_resolve_eas_path)

if [ -z "$EAS_FILES" ]; then
  # No EAS file found for this surface — not an error.
  exit 0
fi

# Run validator on each discovered EAS file.
_ERRORS=""
_WARNINGS=""
_FILE_COUNT=0

while IFS= read -r eas_file; do
  [ -z "$eas_file" ] && continue
  [ ! -f "$eas_file" ] && continue
  _FILE_COUNT=$((_FILE_COUNT + 1))

  RESULT=$(python3 "$PROJECT_DIR/scripts/eas_validate.py" --json "$eas_file" 2>/dev/null || true)
  [ -z "$RESULT" ] && continue

  FILE_OK=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print('true' if d.get('ok') else 'false')" "$RESULT" 2>/dev/null || echo "true")
  FILE_ERRORS=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print('\n'.join(d.get('errors', [])))" "$RESULT" 2>/dev/null || true)
  FILE_WARNINGS=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print('\n'.join(d.get('warnings', [])))" "$RESULT" 2>/dev/null || true)

  if [ "$FILE_OK" = "false" ] && [ -n "$FILE_ERRORS" ]; then
    _ERRORS="${_ERRORS}[${eas_file}]\n${FILE_ERRORS}\n"
  fi
  if [ -n "$FILE_WARNINGS" ]; then
    _WARNINGS="${_WARNINGS}[${eas_file}] WARN: ${FILE_WARNINGS}\n"
  fi
done <<< "$EAS_FILES"

# No files processed — no-op.
if [ "$_FILE_COUNT" -eq 0 ]; then
  exit 0
fi

# Pass: no errors.
if [ -z "$_ERRORS" ]; then
  if [ -n "$_WARNINGS" ]; then
    printf '[eas-validation-gate] Passed with warnings (surface=%s):\n%b\n' "$REVIEW_SURFACE" "$_WARNINGS" >&2
  fi
  exit 0
fi

# Block: emit structured JSON to stdout (Claude Code Stop hook block protocol).
SUMMARY="EAS validation failed on review surface '${REVIEW_SURFACE}'. Uncovered or malformed EAS rows must be resolved before this review surface can close."
DETAILS=$(printf '%b' "$_ERRORS")
if [ -n "$_WARNINGS" ]; then
  DETAILS="${DETAILS}\nWarnings:\n$(printf '%b' "$_WARNINGS")"
fi

python3 - "$SUMMARY" "$DETAILS" "$REVIEW_SURFACE" <<'PYEOF'
import json, sys

summary = sys.argv[1]
details = sys.argv[2]
surface = sys.argv[3]

payload = {
    "decision": "block",
    "reason": summary,
    "hookSpecificOutput": {
        "additionalContext": (
            f"EAS Validation Gate blocked stop for review surface '{surface}'.\n\n"
            f"{details}\n\n"
            "Resolve all ERROR rows in the EAS Markdown file(s) above, then re-run "
            "the review surface. Set DISABLE_HOOK_EAS_VALIDATION_GATE=true to bypass "
            "(not recommended — requires explicit operator override)."
        )
    },
}
print(json.dumps(payload))
PYEOF
