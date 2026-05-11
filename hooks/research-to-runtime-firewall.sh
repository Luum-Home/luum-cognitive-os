#!/usr/bin/env bash
# SCOPE: os-only
# research-to-runtime-firewall.sh — ADR-267 Hook #6.
#
# Pre-commit gate. Blocks if staged content under lib/, packages/, scripts/
# imports from or string-references .cognitive-os/external-source-cache/.
# Closes the research -> runtime leak path: clones in the external cache are
# research-only; they must not feed runtime modules.
#
# Event: PreToolUse / Matcher: Bash / Trigger: command contains commit verb
# Exit: 0 allow / 1 block
# Bypass: COS_ALLOW_RESEARCH_RUNTIME_LEAK=1
# Log: .cognitive-os/logs/research-to-runtime-firewall.jsonl
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/research-to-runtime-firewall.jsonl"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

CACHE_REF=".cognitive-os/external-source-cache"
RUNTIME_DIRS_RE='^(lib|packages|scripts)/'
SCAN_EXT_RE='\.(py|ts|tsx|js|jsx|sh|rs|go|toml|yaml|yml|json)$'

_log() { mkdir -p "$LOG_DIR"; printf '%s\n' "$1" >> "$LOG_FILE"; }

INPUT="$(cat 2>/dev/null || true)"
CMD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except: pass' 2>/dev/null || true)"

[[ "$CMD" != *"git commit"* ]] && exit 0

if [ "${COS_ALLOW_RESEARCH_RUNTIME_LEAK:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_RESEARCH_RUNTIME_LEAK=1\"}"
  exit 0
fi

STAGED="$(git -C "$ROOT_DIR" diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)"
[ -z "$STAGED" ] && exit 0

FOUND=()
while IFS= read -r f; do
  [ -z "$f" ] && continue
  # Only scan runtime dirs
  printf '%s' "$f" | grep -qE "$RUNTIME_DIRS_RE" || continue
  # Only scan scannable extensions
  printf '%s' "$f" | grep -qE "$SCAN_EXT_RE" || continue
  abs="$ROOT_DIR/$f"
  [ -f "$abs" ] || continue
  # Skip if too big (defensive)
  sz=$(wc -c < "$abs" 2>/dev/null || echo 0)
  [ "$sz" -gt 524288 ] && continue
  # Scan staged content for reference to cache path
  if grep -q "$CACHE_REF" "$abs" 2>/dev/null; then
    # Capture line refs for the error message
    line_no="$(grep -n "$CACHE_REF" "$abs" 2>/dev/null | head -3 | cut -d: -f1 | tr '\n' ',' | sed 's/,$//')"
    FOUND+=("$f (lines: $line_no)")
  fi
done <<< "$STAGED"

[ ${#FOUND[@]} -eq 0 ] && exit 0

payload=$(printf '%s\n' "${FOUND[@]}" | python3 -c 'import json,sys; print(json.dumps([l.rstrip() for l in sys.stdin if l.strip()]))')
_log "{\"timestamp\":\"$TS\",\"action\":\"block\",\"reason\":\"runtime referencing external-source-cache\",\"findings\":$payload}"

echo "=== RESEARCH-TO-RUNTIME-FIREWALL: BLOCKED ===" >&2
echo "Runtime files (lib/, packages/, scripts/) must not import or reference" >&2
echo ".cognitive-os/external-source-cache/. Research-only clones cannot feed" >&2
echo "runtime modules — keeps clean-room defendibility intact." >&2
for f in "${FOUND[@]}"; do echo "  - $f" >&2; done
echo "Resolve: remove the cache reference from runtime code (extract behavioral" >&2
echo "spec to docs/research/ first), OR COS_ALLOW_RESEARCH_RUNTIME_LEAK=1 ..." >&2
echo "Reference: docs/adrs/ADR-267-*.md §Layer 1 Hook #6" >&2
exit 1
