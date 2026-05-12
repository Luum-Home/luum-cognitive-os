#!/usr/bin/env bash
# SCOPE: os-only
# spdx-header-required.sh — ADR-267 Hook #4.
#
# Pre-commit gate. New source files under lib/, packages/*/lib/, scripts/
# (.py/.sh/.js/.ts) MUST carry an `SPDX-License-Identifier:` token within
# the first 10 lines. Existing files at hook-install snapshot time are
# grandfathered via manifests/spdx-grandfather.txt — they are exempt from
# enforcement even if modified.
#
# Event:    PreToolUse
# Matcher:  Bash
# Trigger:  command contains `git commit`
# Exit:     0 = allow / 1 = block
# Bypass:   COS_ALLOW_MISSING_SPDX=1 (logged)
# Log:      .cognitive-os/logs/spdx-header-required.jsonl
#
# Latency: typical <120ms (cached grandfather lookup), worst <800ms for
# large multi-file commits.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/spdx-header-required.jsonl"
GRANDFATHER="$ROOT_DIR/manifests/spdx-grandfather.txt"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_log() { mkdir -p "$LOG_DIR"; printf '%s\n' "$1" >> "$LOG_FILE"; }

INPUT="$(cat 2>/dev/null || true)"
CMD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except: pass' 2>/dev/null || true)"

[[ "$CMD" != *"git commit"* ]] && exit 0

if [ "${COS_ALLOW_MISSING_SPDX:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_MISSING_SPDX=1\"}"
  exit 0
fi

STAGED="$(git -C "$ROOT_DIR" diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)"
[ -z "$STAGED" ] && exit 0

GF_OPT=""
if [ -f "$GRANDFATHER" ]; then
  GF_OPT="$GRANDFATHER"
fi

PATH_RE='^(lib/|packages/[^/]+/lib/|scripts/)'
EXT_RE='\.(py|sh|js|ts)$'

MISSING=()
while IFS= read -r f; do
  [ -z "$f" ] && continue
  printf '%s' "$f" | grep -qE "$PATH_RE" || continue
  printf '%s' "$f" | grep -qE "$EXT_RE" || continue

  if [ -n "$GF_OPT" ] && grep -Fxq "$f" "$GF_OPT" 2>/dev/null; then
    continue
  fi

  abs="$ROOT_DIR/$f"
  [ -f "$abs" ] || continue

  if ! head -10 "$abs" 2>/dev/null | grep -q 'SPDX-License-Identifier:'; then
    MISSING+=("$f")
  fi
done <<< "$STAGED"

if [ ${#MISSING[@]} -eq 0 ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"pass\"}"
  exit 0
fi

payload=$(printf '%s\n' "${MISSING[@]}" | python3 -c 'import json,sys; print(json.dumps([l.rstrip() for l in sys.stdin if l.strip()]))')
_log "{\"timestamp\":\"$TS\",\"action\":\"block\",\"reason\":\"missing SPDX header\",\"files\":$payload}"

echo "=== SPDX-HEADER-REQUIRED: BLOCKED ===" >&2
echo "These new source files must declare an SPDX-License-Identifier in the first" >&2
echo "10 lines (per ADR-267 Layer 1 Hook #4):" >&2
for f in "${MISSING[@]}"; do echo "  - $f" >&2; done
echo "" >&2
echo "Add a comment-style header. Examples:" >&2
echo "  Python:    # SPDX-License-Identifier: Apache-2.0" >&2
echo "  Shell:     # SPDX-License-Identifier: Apache-2.0" >&2
echo "  JS/TS:     // SPDX-License-Identifier: Apache-2.0" >&2
echo "" >&2
echo "Bypass (logged): COS_ALLOW_MISSING_SPDX=1 git commit ..." >&2
echo "Reference: docs/02-Decisions/adrs/ADR-267-license-compliance-enforcement-architecture.md" >&2
exit 1
