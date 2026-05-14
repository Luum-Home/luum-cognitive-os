#!/usr/bin/env bash
# SCOPE: both
# scope-marker-portability-gate.sh — PreToolUse Bash hook for KD6 portability proof.
#
# Blocks `git commit` when a staged artifact declares `SCOPE: both` but lacks a
# paired portability test under tests/red_team/portability/.  This keeps
# cross-harness / cross-project claims executable instead of aspirational.
#
# Contract:
#   - Input: Claude/Codex PreToolUse JSON for Bash.
#   - Trigger: bash command containing `git commit`.
#   - Decision: exit 2 when any staged added/copied/modified/renamed file has a
#     scope marker in the first three lines and no paired portability test.
#   - Bypass: COS_ALLOW_UNPROVEN_SCOPE_BOTH=1 (logs warning and allows).

set -uo pipefail

_HOOK_NAME="scope-marker-portability-gate"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=hooks/_lib/common.sh
source "$SCRIPT_DIR/_lib/common.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}}"
METRICS_DIR="${COS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
METRICS_FILE="$METRICS_DIR/scope-marker-portability-gate.jsonl"

emit_metric() {
  local decision="$1" details="$2"
  mkdir -p "$METRICS_DIR" 2>/dev/null || true
  python3 - "$METRICS_FILE" "$decision" "$details" <<'PY' 2>/dev/null || true
import json, sys, time
path, decision, details = sys.argv[1:]
row = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "hook": "scope-marker-portability-gate",
    "decision": decision,
    "details": details,
}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, sort_keys=True) + "\n")
PY
}

INPUT=""
if [ ! -t 0 ]; then
  INPUT="$(cat 2>/dev/null || true)"
fi
[ -n "$INPUT" ] || exit 0

if ! command -v python3 >/dev/null 2>&1; then
  emit_metric "warn_no_python" "python3 unavailable; cannot inspect Bash command"
  exit 0
fi

TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read() or "{}"); print(d.get("tool_name", ""))' 2>/dev/null || true)"
[ "$TOOL_NAME" = "Bash" ] || exit 0

COMMAND="$(printf '%s' "$INPUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read() or "{}"); print((d.get("tool_input") or {}).get("command", ""))' 2>/dev/null || true)"
[ -n "$COMMAND" ] || exit 0

if ! printf '%s\n' "$COMMAND" | grep -Eq '(^|[;&|[:space:]])git[[:space:]]+commit([[:space:]]|$)'; then
  exit 0
fi

if [ "${COS_ALLOW_UNPROVEN_SCOPE_BOTH:-0}" = "1" ]; then
  emit_metric "bypass" "$COMMAND"
  exit 0
fi

if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  emit_metric "warn_not_git_repo" "$PROJECT_DIR"
  exit 0
fi

# Let amend-only metadata commits proceed when no path content is staged.
staged_files="$(git -C "$PROJECT_DIR" diff --cached --name-only --diff-filter=ACMRT 2>/dev/null || true)"
[ -n "$staged_files" ] || exit 0

missing_report=""
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  case "$rel" in
    tests/red_team/portability/*) continue ;;
  esac

  abs="$PROJECT_DIR/$rel"
  [ -f "$abs" ] || continue

  header="$(head -3 "$abs" 2>/dev/null || true)"
  if ! printf '%s\n' "$header" | grep -Eq '(^#|<!--)[[:space:]]*SCOPE:[[:space:]]*both'; then
    continue
  fi

  base="$(basename "$rel")"
  stem="${base%.*}"
  skill_candidate=""
  case "$rel" in
    skills/*/SKILL.md)
      skill_name="$(basename "$(dirname "$rel")" | tr '-' '_')"
      skill_candidate="tests/red_team/portability/test_skill_${skill_name}.py"
      ;;
  esac
  candidates="$skill_candidate
-tests/red_team/portability/$stem.bats
-tests/red_team/portability/$base.bats
-tests/red_team/portability/${stem}_test.py
-tests/red_team/portability/test_${stem}.py"

  found="false"
  while IFS= read -r candidate; do
    candidate="${candidate#-}"
    [ -n "$candidate" ] || continue
    if [ -f "$PROJECT_DIR/$candidate" ] || git -C "$PROJECT_DIR" ls-files --error-unmatch "$candidate" >/dev/null 2>&1; then
      found="true"
      break
    fi
  done <<EOF_CANDIDATES
$candidates
EOF_CANDIDATES

  [ "$found" = "true" ] && continue
  missing_report="$missing_report
- $rel declares SCOPE: both; expected one of: ${skill_candidate:+$skill_candidate, }tests/red_team/portability/$stem.bats, tests/red_team/portability/$base.bats, tests/red_team/portability/${stem}_test.py, tests/red_team/portability/test_${stem}.py"
done <<EOF_FILES
$staged_files
EOF_FILES

if [ -n "$missing_report" ]; then
  emit_metric "block_missing_portability_test" "$missing_report"
  cat >&2 <<EOF_BLOCK
[scope-marker-portability-gate] BLOCK: staged SCOPE: both artifact(s) lack paired portability tests.$missing_report

Add a real portability test with at least one falsification probe, or remove the SCOPE: both claim until the proof exists.
Bypass for an emergency only: COS_ALLOW_UNPROVEN_SCOPE_BOTH=1
EOF_BLOCK
  exit 2
fi

emit_metric "allow" "all staged SCOPE: both artifacts have portability tests"
exit 0
