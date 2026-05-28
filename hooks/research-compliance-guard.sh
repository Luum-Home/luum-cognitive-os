#!/usr/bin/env bash
# SCOPE: both
# research-compliance-guard.sh — portable pre-commit guard for research/license boundaries.
#
# Blocks common research-to-runtime and proprietary/unlicensed research reuse
# mistakes in consumer projects without requiring COS maintainer-only companion
# manifests. This guard is intentionally conservative and self-contained so it
# can ship in the default/core install profile.
#
# Event: PreToolUse / Matcher: Bash / Trigger: command contains git commit
# Exit: 0 allow / 2 block
# Bypass: COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS=1
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

resolve_root() {
  if [ -n "${COGNITIVE_OS_PROJECT_DIR:-}" ] && [ -d "$COGNITIVE_OS_PROJECT_DIR" ]; then
    cd "$COGNITIVE_OS_PROJECT_DIR" 2>/dev/null && pwd && return 0
  fi
  if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "$CLAUDE_PROJECT_DIR" ]; then
    cd "$CLAUDE_PROJECT_DIR" 2>/dev/null && pwd && return 0
  fi
  if [ -n "${CODEX_PROJECT_DIR:-}" ] && [ -d "$CODEX_PROJECT_DIR" ]; then
    cd "$CODEX_PROJECT_DIR" 2>/dev/null && pwd && return 0
  fi
  git -C "${PWD:-.}" rev-parse --show-toplevel 2>/dev/null && return 0
  case "$SCRIPT_DIR" in
    */.cognitive-os/hooks/cos) cd "$SCRIPT_DIR/../../.." 2>/dev/null && pwd && return 0 ;;
  esac
  cd "$SCRIPT_DIR/.." 2>/dev/null && pwd
}

ROOT_DIR="$(resolve_root)"
LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/research-compliance-guard.jsonl"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_log() {
  mkdir -p "$LOG_DIR" 2>/dev/null || true
  printf '%s\n' "$1" >> "$LOG_FILE" 2>/dev/null || true
}

INPUT="$(cat 2>/dev/null || true)"
CMD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command", ""))
except Exception: pass' 2>/dev/null || true)"

if [ "${COS_RESEARCH_COMPLIANCE_FORCE:-0}" != "1" ] && [[ "$CMD" != *"git commit"* ]]; then
  exit 0
fi

if [ "${COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_RESEARCH_COMPLIANCE_BYPASS=1\"}"
  exit 0
fi

STAGED="$(git -C "$ROOT_DIR" diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)"
[ -z "$STAGED" ] && exit 0

failures=()

MAC_HOME_SEG='/'"Users"
LINUX_HOME_SEG='/'"home"
HOME_PATH_RE="(^|[^A-Za-z0-9_.-])((${MAC_HOME_SEG}|${LINUX_HOME_SEG})/[A-Za-z0-9._-]+|${MAC_HOME_SEG}/[^.][^/[:space:]]+/Projects/)"

add_failure() {
  failures+=("$1")
}

is_scannable_text() {
  case "$1" in
    *.md|*.mdx|*.txt|*.rst|*.adoc|*.yaml|*.yml|*.json|*.toml|*.py|*.js|*.jsx|*.ts|*.tsx|*.go|*.rs|*.sh|README|README.*) return 0 ;;
    *) return 1 ;;
  esac
}

while IFS= read -r rel; do
  [ -z "$rel" ] && continue
  abs="$ROOT_DIR/$rel"

  case "$rel" in
    .research/*|research/*|_research/*)
      add_failure "$rel: research clones/working copies must stay ignored and must not be committed"
      continue
      ;;
  esac

  [ -f "$abs" ] || continue
  is_scannable_text "$rel" || continue

  size="$(wc -c < "$abs" 2>/dev/null || echo 0)"
  [ "${size:-0}" -gt 1048576 ] && continue

  if grep -Eq "$HOME_PATH_RE" "$abs" 2>/dev/null; then
    add_failure "$rel: contains a personal absolute home path; use repo-local or redacted paths"
  fi

  case "$rel" in
    lib/*|packages/*|scripts/*|src/*|app/*|cmd/*)
      if grep -Eq '(\.research/|_research/|\.cognitive-os/external-source-cache)' "$abs" 2>/dev/null; then
        add_failure "$rel: runtime code references research-only source/cache paths"
      fi
      ;;
  esac

  case "$rel" in
    docs/*|README*|*.md|*.mdx)
      if grep -Eiq '(proprietary|all rights reserved|unlicensed|no license|license absent|unknown license)' "$abs" 2>/dev/null; then
        if ! grep -Eiq '(conceptual research only|conceptual-only|clean-room|no code[^[:alnum:]]+assets[^[:alnum:]]+prompts|no reuse|do not copy|do not port|do not vendor)' "$abs" 2>/dev/null; then
          add_failure "$rel: proprietary/unlicensed research must state conceptual-only/no-reuse/clean-room boundary"
        fi
        if grep -Eiq '(reference implementation|base(d)? on|adopt|port|copy|vendor)' "$abs" 2>/dev/null; then
          if ! grep -Eiq '(do not adopt|do not port|do not copy|do not vendor|not a reference implementation|avoid .*reference implementation)' "$abs" 2>/dev/null; then
            add_failure "$rel: unsafe reuse wording near proprietary/unlicensed research"
          fi
        fi
      fi
      ;;
  esac
done <<< "$STAGED"

if [ "${#failures[@]}" -eq 0 ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"pass\",\"files_scanned\":$(printf '%s\n' "$STAGED" | sed '/^$/d' | wc -l | tr -d ' ')}"
  exit 0
fi

payload="$(printf '%s\n' "${failures[@]}" | python3 -c 'import json,sys; print(json.dumps([l.rstrip() for l in sys.stdin if l.strip()]))' 2>/dev/null || echo '[]')"
_log "{\"timestamp\":\"$TS\",\"action\":\"block\",\"findings\":$payload}"

echo "=== RESEARCH-COMPLIANCE-GUARD: BLOCKED ===" >&2
echo "Research, license, or clean-room boundary issues were found:" >&2
for item in "${failures[@]}"; do
  echo "  - $item" >&2
done
echo "Resolve by keeping research clones ignored, using repo-local paths, and documenting proprietary/unlicensed research as conceptual-only with no code/assets/prompts/schema reuse." >&2
exit 2
