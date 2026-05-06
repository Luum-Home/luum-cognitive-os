#!/usr/bin/env bash
# SCOPE: both
# PreToolUse guard for ADR-194: cosd remote API requires explicit remote opt-in
# plus bearer-token auth; edits to cosd API/control-plane config require review.
set -uo pipefail

if [[ "${DISABLE_HOOK_COSD_AUTH_GUARD:-0}" == "1" || "${DISABLE_HOOK_COSD_AUTH_GUARD:-}" == "true" ]]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

OUT_FILE="${TMPDIR:-/tmp}/cosd-auth-guard.$$.$RANDOM.out"
ERR_FILE="${TMPDIR:-/tmp}/cosd-auth-guard.$$.$RANDOM.err"
trap 'rm -f "$OUT_FILE" "$ERR_FILE"' EXIT

PYTHONPATH="$COS_ROOT:${PYTHONPATH:-}" COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" \
python3 - "$PROJECT_DIR" "$INPUT" <<'PY' >"$OUT_FILE" 2>"$ERR_FILE" || true
from __future__ import annotations

import json
import sys
from pathlib import Path

from lib.cosd_auth_guard import append_audit, inspect_payload

project = Path(sys.argv[1])
try:
    payload = json.loads(sys.argv[2])
except Exception:
    payload = {}
findings = inspect_payload(payload, project_dir=project)
append_audit(project, findings)
print(json.dumps([finding.to_dict() for finding in findings], sort_keys=True))
PY

if [[ -s "$OUT_FILE" ]] && python3 - "$OUT_FILE" <<'PY' >/dev/null 2>&1
import json, sys
rows=json.loads(open(sys.argv[1]).read() or '[]')
raise SystemExit(0 if rows else 1)
PY
then
  echo "=== COSD AUTH GUARD: BLOCKED ===" >&2
  cat "$OUT_FILE" >&2
  exit 2
fi

exit 0
