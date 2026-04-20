#!/usr/bin/env bash
# SCOPE: project
# PreToolUse hook: Reinvention Check
# Fires on "Agent" tool use — warns if agent may be recreating existing implementations.
# Advisory only (exit 0 always).

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="reinvention-check"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

check_private_mode
read_stdin_json

PROMPT=$(stdin_field '.tool_input.prompt' '')

[ -z "$PROMPT" ] && exit 0

# Only fire if prompt contains creation intent + file-type targets
if ! echo "$PROMPT" | grep -qiE '(create|implement|write|add)'; then
  exit 0
fi
if ! echo "$PROMPT" | grep -qE '(lib/|hooks/|new file|new hook|new script)'; then
  exit 0
fi

# Extract the thing being created
TARGET=$(echo "$PROMPT" | grep -oE '[a-z][a-z0-9_-]+\.(sh|py|go|ts|js)' | head -3 | tr '\n' ' ' || true)
[ -z "$TARGET" ] && TARGET=$(echo "$PROMPT" | grep -oE 'lib/[a-z_]+' | head -2 | tr '\n' ' ' || true)

METRICS_DIR=$(_resolve_metrics_dir)
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

FOUND_SOURCES=""
PLUGIN_DIRS=(
  "$_PROJECT_DIR/.claude/plugins/hermes-agent"
  "$_PROJECT_DIR/.claude/plugins/pi-mono"
  "$_PROJECT_DIR/lib"
  "$_PROJECT_DIR/hooks"
)

for TARGET_FILE in $TARGET; do
  BASE="${TARGET_FILE%.*}"
  for DIR in "${PLUGIN_DIRS[@]}"; do
    [ -d "$DIR" ] || continue
    MATCH=$(find "$DIR" -type f -name "*${BASE}*" 2>/dev/null | head -2 || true)
    if [ -n "$MATCH" ]; then
      FOUND_SOURCES="$FOUND_SOURCES $MATCH"
    fi
  done
done

if [ -n "$FOUND_SOURCES" ]; then
  echo "REINVENTION CHECK: Similar implementation(s) may already exist:" >&2
  for src in $FOUND_SOURCES; do
    echo "  - $src" >&2
  done
  echo "Consider reusing or extending existing code before creating new files." >&2

  safe_jsonl_append "$METRICS_DIR/reinvention-checks.jsonl" \
    "{\"timestamp\":\"$TIMESTAMP\",\"target\":\"${TARGET// /,}\",\"sources\":$(echo "$FOUND_SOURCES" | jq -Rs '.'),\"phase\":\"A\"}"
fi

# ADR-029b Phase B-α — semantic Jaccard advisory.
# Gated behind REINVENTION_PHASE_B=1; stays silent on any failure path.
if [ "${REINVENTION_PHASE_B:-0}" = "1" ]; then
  THRESHOLD="${REINVENTION_PHASE_B_THRESHOLD:-0.3}"
  # Use python3 if available; fall back silently otherwise.
  if command -v python3 >/dev/null 2>&1; then
    SEM_OUTPUT=$(
      PROJECT_ROOT="$_PROJECT_DIR" \
      REINV_QUERY="$PROMPT" \
      REINV_THRESHOLD="$THRESHOLD" \
      python3 - <<'PYEOF' 2>/dev/null || true
import json, os, sys
sys.path.insert(0, os.environ.get("PROJECT_ROOT", "."))
try:
    from lib.reinvention_semantic import SemanticIndex, DEFAULT_INDEX_RELPATH
except Exception:
    sys.exit(0)
root = os.environ.get("PROJECT_ROOT", ".")
idx = SemanticIndex(os.path.join(root, DEFAULT_INDEX_RELPATH))
if not idx.load():
    # No lazy build on the hot path (ADR-029b §6) — fall back to Phase A only.
    print(json.dumps({"reason": "index_missing", "matches": []}))
    sys.exit(0)
thr = float(os.environ.get("REINV_THRESHOLD", "0.3"))
q = os.environ.get("REINV_QUERY", "")
matches = idx.find_similar(q, top_k=3, min_score=thr)
print(json.dumps({"reason": "ok", "matches": matches, "threshold": thr}))
PYEOF
    )
    if [ -n "$SEM_OUTPUT" ]; then
      REASON=$(echo "$SEM_OUTPUT" | jq -r '.reason // "unknown"' 2>/dev/null || echo "unknown")
      MATCH_COUNT=$(echo "$SEM_OUTPUT" | jq -r '.matches | length' 2>/dev/null || echo "0")
      if [ "$REASON" = "ok" ] && [ "${MATCH_COUNT:-0}" -gt 0 ]; then
        echo "REINVENTION CHECK (Phase B-α semantic): possible duplicates by meaning:" >&2
        echo "$SEM_OUTPUT" | jq -r '.matches[] | "  - \(.path)  (score \(.score))"' >&2
        echo "Review before creating new files. Advisory only." >&2
      fi
      safe_jsonl_append "$METRICS_DIR/reinvention-checks.jsonl" \
        "{\"timestamp\":\"$TIMESTAMP\",\"phase\":\"B-alpha\",\"reason\":\"$REASON\",\"match_count\":${MATCH_COUNT:-0},\"threshold\":${THRESHOLD},\"action\":\"ADVISED\"}"
    fi
  fi
fi

exit 0
