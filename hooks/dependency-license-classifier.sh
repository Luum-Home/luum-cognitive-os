#!/usr/bin/env bash
# SCOPE: os-only
# dependency-license-classifier.sh — ADR-267 Hook #1.
#
# Pre-commit gate. Scans staged dep-manifest diffs for BLOCKER license strings
# per rules/license-policy.md.
#
# Event: PreToolUse / Matcher: Bash / Trigger: command contains commit verb
# Exit: 0 allow / 1 block
# Bypass: COS_ALLOW_LICENSE_CLASSIFIER_BYPASS=1
# Log: .cognitive-os/logs/dependency-license-classifier.jsonl
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/dependency-license-classifier.jsonl"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_log() { mkdir -p "$LOG_DIR"; printf '%s\n' "$1" >> "$LOG_FILE"; }

INPUT="$(cat 2>/dev/null || true)"
CMD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except: pass' 2>/dev/null || true)"

[[ "$CMD" != *"git commit"* ]] && exit 0

if [ "${COS_ALLOW_LICENSE_CLASSIFIER_BYPASS:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_LICENSE_CLASSIFIER_BYPASS=1\"}"
  exit 0
fi

BLOCKERS=("AGPL" "SSPL" "Server Side Public License" "BSL" "Business Source" "ELv2" "Elastic License" "Commons Clause" "FSL" "Functional Source")

STAGED="$(git -C "$ROOT_DIR" diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)"
[ -z "$STAGED" ] && exit 0

DEP_MFS=()
while IFS= read -r f; do
  case "$f" in
    requirements.txt|requirements-*.txt|*/requirements.txt|pyproject.toml|*/pyproject.toml) DEP_MFS+=("py:$f") ;;
    package.json|*/package.json) DEP_MFS+=("node:$f") ;;
    Cargo.toml|*/Cargo.toml) DEP_MFS+=("rust:$f") ;;
  esac
done <<< "$STAGED"

[ ${#DEP_MFS[@]} -eq 0 ] && exit 0

FOUND=()
for entry in "${DEP_MFS[@]}"; do
  ecosys="${entry%%:*}"
  path="${entry#*:}"
  added="$(git -C "$ROOT_DIR" diff --cached "$path" 2>/dev/null | grep -E '^\+' || true)"
  [ -z "$added" ] && continue
  for p in "${BLOCKERS[@]}"; do
    printf '%s' "$added" | grep -qi "$p" && FOUND+=("$path: matched BLOCKER '$p' (ecosystem=$ecosys)")
  done
done

[ ${#FOUND[@]} -eq 0 ] && exit 0

payload=$(printf '%s\n' "${FOUND[@]}" | python3 -c 'import json,sys; print(json.dumps([l.rstrip() for l in sys.stdin if l.strip()]))')
_log "{\"timestamp\":\"$TS\",\"action\":\"block\",\"reason\":\"BLOCKER license\",\"findings\":$payload}"

echo "=== DEPENDENCY-LICENSE-CLASSIFIER: BLOCKED ===" >&2
echo "Per rules/license-policy.md the staged dep-manifest changes reference" >&2
echo "a license category that blocks commercial / SaaS use." >&2
for f in "${FOUND[@]}"; do echo "  - $f" >&2; done
echo "Resolve: remove the dep, OR COS_ALLOW_LICENSE_CLASSIFIER_BYPASS=1 ..." >&2
echo "Reference: rules/license-policy.md + docs/adrs/ADR-267-*.md" >&2
exit 1
