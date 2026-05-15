#!/usr/bin/env bash
# SCOPE: os-only
# engram-obsidian-export-on-stop.sh — optional Stop hook for Engram → Obsidian export.
#
# This hook is deliberately opt-in:
#   - unset COS_OBSIDIAN_VAULT: no-op
#   - set COS_OBSIDIAN_VAULT=/absolute/vault/path: write one-way export
#
# It never imports from Obsidian and never blocks session shutdown.

set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HOOK_DIR/_lib/common.sh"
source "$HOOK_DIR/_lib/safe-jsonl.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}}"
VAULT="${COS_OBSIDIAN_VAULT:-}"

if [ -z "$VAULT" ]; then
  exit 0
fi

PROJECT_NAME="${COS_OBSIDIAN_PROJECT:-${ENGRAM_PROJECT:-$(basename "$PROJECT_DIR")}}"
LIMIT="${COS_OBSIDIAN_EXPORT_LIMIT:-100}"
METRICS_DIR="$(resolve_session_dir)"
METRICS_FILE="$METRICS_DIR/obsidian-export.jsonl"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date +%Y-%m-%dT%H:%M:%SZ)"
EXPORT_SCRIPT="$PROJECT_DIR/scripts/export-engram-to-obsidian.sh"

if [ ! -x "$EXPORT_SCRIPT" ] && [ ! -f "$EXPORT_SCRIPT" ]; then
  safe_jsonl_append "$METRICS_FILE" "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"engram_obsidian_export\",\"status\":\"skipped\",\"reason\":\"missing_export_script\",\"vault\":\"$VAULT\",\"project\":\"$PROJECT_NAME\"}" || true
  exit 0
fi

OUTPUT="$(bash "$EXPORT_SCRIPT" --vault "$VAULT" --project "$PROJECT_NAME" --limit "$LIMIT" --write --json 2>&1)"
STATUS=$?

if [ "$STATUS" -eq 0 ]; then
  SAFE_OUTPUT="$(printf '%s' "$OUTPUT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '""')"
  safe_jsonl_append "$METRICS_FILE" "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"engram_obsidian_export\",\"status\":\"ok\",\"vault\":\"$VAULT\",\"project\":\"$PROJECT_NAME\",\"output\":$SAFE_OUTPUT}" || true
else
  SAFE_OUTPUT="$(printf '%s' "$OUTPUT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()[-2000:]))' 2>/dev/null || printf '\"export failed\"')"
  safe_jsonl_append "$METRICS_FILE" "{\"timestamp\":\"$TIMESTAMP\",\"event\":\"engram_obsidian_export\",\"status\":\"failed_non_blocking\",\"exit_code\":$STATUS,\"vault\":\"$VAULT\",\"project\":\"$PROJECT_NAME\",\"output\":$SAFE_OUTPUT}" || true
fi

exit 0
