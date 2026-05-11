#!/usr/bin/env bash
# SCOPE: os-only
# adoption-freeze-gate.sh — ADR-267 Hook #3 (Layer 1 — kill-switch).
#
# Reads manifests/external-tool-adoption-freeze.yaml. If `frozen: true`,
# blocks `git commit` that touches any path matching `gated_path_globs`.
# Permits the freeze yaml itself to be toggled when COS_ALLOW_FREEZE_TOGGLE=1
# and no other gated paths are staged.
#
# Event:    PreToolUse
# Matcher:  Bash
# Trigger:  command contains `git commit`
# Exit:     0 = allow / 1 = block
# Bypass:
#   COS_ALLOW_ADOPTION_FREEZE_BYPASS=1   — generic logged bypass
#   COS_ALLOW_FREEZE_TOGGLE=1            — allows commit of freeze yaml alone
# Log:      .cognitive-os/logs/adoption-freeze-gate.jsonl
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST="$ROOT_DIR/manifests/external-tool-adoption-freeze.yaml"
LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/adoption-freeze-gate.jsonl"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_log() { mkdir -p "$LOG_DIR"; printf '%s\n' "$1" >> "$LOG_FILE"; }

INPUT="$(cat 2>/dev/null || true)"
COMMAND="$(printf '%s' "$INPUT" | python3 -c "import json,sys
try: print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except: pass" 2>/dev/null || true)"

[[ "$COMMAND" != *"git commit"* ]] && exit 0

if [ ! -f "$MANIFEST" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"skip\",\"reason\":\"manifest absent\"}"
  exit 0
fi

# Parse manifest
manifest_data=$(python3 <<PYEOF 2>/dev/null || true
import yaml
try:
    m = yaml.safe_load(open("$MANIFEST")) or {}
    print("FROZEN=" + ("1" if m.get("frozen") is True else "0"))
    for g in (m.get("gated_path_globs") or []):
        print("GLOB=" + str(g))
except Exception as e:
    print("ERR=" + str(e))
PYEOF
)

FROZEN=0
GLOBS=()
ERR=""
while IFS= read -r line; do
  case "$line" in
    FROZEN=*) FROZEN="${line#FROZEN=}" ;;
    GLOB=*)   GLOBS+=("${line#GLOB=}") ;;
    ERR=*)    ERR="${line#ERR=}" ;;
  esac
done <<< "$manifest_data"

if [ -n "$ERR" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"skip\",\"reason\":\"parse error\",\"err\":\"$ERR\"}"
  exit 0
fi

if [ "$FROZEN" != "1" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"pass\",\"reason\":\"frozen=false\"}"
  exit 0
fi

# frozen=true: check staged files
STAGED="$(git -C "$ROOT_DIR" diff --cached --name-only --diff-filter=ACMRD 2>/dev/null || true)"
[ -z "$STAGED" ] && { _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"pass\",\"reason\":\"no staged\"}"; exit 0; }

NON_MANIFEST="$(printf '%s\n' "$STAGED" | grep -v -F "manifests/external-tool-adoption-freeze.yaml" || true)"
if [ "${COS_ALLOW_FREEZE_TOGGLE:-0}" = "1" ] && [ -z "$NON_MANIFEST" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_FREEZE_TOGGLE+manifest-only\"}"
  exit 0
fi

if [ "${COS_ALLOW_ADOPTION_FREEZE_BYPASS:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_ADOPTION_FREEZE_BYPASS=1\"}"
  exit 0
fi

# Scan staged paths against globs
BLOCKED=()
while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ "$f" = "manifests/external-tool-adoption-freeze.yaml" ] && continue
  for g in "${GLOBS[@]}"; do
    # shellcheck disable=SC2053
    case "$f" in $g) BLOCKED+=("$f"); break ;; esac
  done
done <<< "$STAGED"

if [ ${#BLOCKED[@]} -eq 0 ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"pass\",\"reason\":\"no gated paths touched\"}"
  exit 0
fi

blocked_json=$(printf '%s\n' "${BLOCKED[@]}" | python3 -c "import json,sys; print(json.dumps([l.rstrip() for l in sys.stdin if l.strip()]))")
_log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"block\",\"reason\":\"frozen=true\",\"blocked_files\":$blocked_json}"

echo "=== ADOPTION-FREEZE-GATE: BLOCKED ===" >&2
echo "External-tool adoption is FROZEN per manifests/external-tool-adoption-freeze.yaml" >&2
echo "Blocked gated paths:" >&2
for f in "${BLOCKED[@]}"; do echo "  - $f" >&2; done
echo "" >&2
echo "Resolve via ONE of:" >&2
echo "  1. Unfreeze: edit the freeze yaml (set frozen: false) with" >&2
echo "     COS_ALLOW_FREEZE_TOGGLE=1 git commit ... (yaml alone)" >&2
echo "  2. Bypass logged: COS_ALLOW_ADOPTION_FREEZE_BYPASS=1 git commit ..." >&2
echo "Reference: docs/adrs/ADR-267-license-compliance-enforcement-architecture.md" >&2
exit 1
