#!/usr/bin/env bash
# SCOPE: os-only
# holaos-cleanroom-gate.sh — Pre-commit clean-room gate for holaOS adoptions
#
# ADR-259 §Implementation plan + Annexe F §7 audit trail.
# Verifies that no staged file contains literal strings from holaOS source.
# Runs as PreToolUse/Bash hook matching `git commit` commands.
#
# Event:    PreToolUse
# Matcher:  Bash
# Trigger:  command contains `git commit`
#
# Exit codes:
#   0 — clean (or skip/bypass)
#   1 — leak detected, commit blocked
#
# Environment variables:
#   COS_ALLOW_HOLAOS_LEAK=1  — bypass gate (logged as action: "bypass")
#
# Logs to: .cognitive-os/logs/holaos-cleanroom-gate.jsonl
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/holaos-cleanroom-gate.jsonl"
HOLAOS_SOURCE="/tmp/holaOS-investigation"

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# ── Helper: append JSONL log entry ──────────────────────────────────────────
_log() {
  mkdir -p "$LOG_DIR"
  printf '%s\n' "$1" >> "$LOG_FILE"
}

# ── Read hook input from stdin ───────────────────────────────────────────────
INPUT="$(cat)"

# Extract tool_name and command from hook JSON payload (Claude Code hook shape).
TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null || true)"
COMMAND="$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || true)"

# ── Only intercept `git commit` commands ─────────────────────────────────────
if [[ "$COMMAND" != *"git commit"* ]]; then
  exit 0
fi

# ── Bypass mode ──────────────────────────────────────────────────────────────
if [ "${COS_ALLOW_HOLAOS_LEAK:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_HOLAOS_LEAK=1\"}"
  exit 0
fi

# ── Skip gracefully if holaOS source repo is absent ──────────────────────────
if [ ! -d "$HOLAOS_SOURCE" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"skip\",\"reason\":\"source repo absent\",\"path\":\"$HOLAOS_SOURCE\"}"
  exit 0
fi

# ── Generic tokens to skip (not indicative of source copying) ────────────────
GENERIC_TOKENS="the function import from class return def const let var if else for while and or not in is as try except finally with pass break continue yield raise del global nonlocal lambda assert True False None self super print type str int float list dict set tuple bool bytes"

is_generic() {
  local tok="$1"
  for g in $GENERIC_TOKENS; do
    [ "$tok" = "$g" ] && return 0
  done
  return 1
}

# ── Scan staged files ─────────────────────────────────────────────────────────
STAGED_FILES="$(git -C "$ROOT_DIR" diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)"

if [ -z "$STAGED_FILES" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"pass\",\"files_scanned\":0,\"reason\":\"no staged files\"}"
  exit 0
fi

FILES_SCANNED=0
EXTENSIONS_RE='\.(py|ts|js|sh|md|yaml|yml)$'

while IFS= read -r rel_file; do
  [ -z "$rel_file" ] && continue

  # Filter by extension
  if ! printf '%s' "$rel_file" | grep -qE "$EXTENSIONS_RE"; then
    continue
  fi

  abs_file="$ROOT_DIR/$rel_file"
  [ -f "$abs_file" ] || continue

  # Skip large files (>100KB)
  file_size=$(wc -c < "$abs_file" 2>/dev/null || echo 0)
  if [ "$file_size" -gt 102400 ]; then
    continue
  fi

  FILES_SCANNED=$((FILES_SCANNED + 1))

  # Extract tokens: alphanumeric sequences of length >= 8, cap at 200 tokens
  TOKENS="$(grep -oE '[A-Za-z_][A-Za-z0-9_]{7,}' "$abs_file" 2>/dev/null | sort -u | head -200 || true)"

  while IFS= read -r token; do
    [ -z "$token" ] && continue

    # Skip generic tokens
    is_generic "$token" && continue

    # Search for exact token in holaOS source
    if grep -rqF "$token" "$HOLAOS_SOURCE" 2>/dev/null; then
      # Escape token for JSON
      safe_token="$(printf '%s' "$token" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null || printf '"%s"' "$token")"
      safe_file="$(printf '%s' "$rel_file" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))' 2>/dev/null || printf '"%s"' "$rel_file")"

      _log "{\"timestamp\":\"$TIMESTAMP\",\"file\":$safe_file,\"token\":$safe_token,\"action\":\"block\"}"

      echo "HOLAOS CLEANROOM VIOLATION: token $token found in staged file $rel_file matches holaOS source." >&2
      echo "  File:  $rel_file" >&2
      echo "  Token: $token" >&2
      echo "" >&2
      echo "COMMIT BLOCKED (ADR-259 clean-room policy)." >&2
      echo "If this is a false positive, set COS_ALLOW_HOLAOS_LEAK=1 to bypass (logged)." >&2
      exit 1
    fi
  done <<EOF
$TOKENS
EOF

done <<EOF
$STAGED_FILES
EOF

# ── All clear ─────────────────────────────────────────────────────────────────
_log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"pass\",\"files_scanned\":$FILES_SCANNED}"
exit 0
HOOKEOF