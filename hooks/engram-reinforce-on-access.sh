#!/usr/bin/env bash
# SCOPE: both
# PURPOSE: Reinforce engram observations on mem_search and mem_get_observation access
# EVENT: PostToolUse
# MATCHER: mcp__plugin_engram_engram__mem_search|mcp__plugin_engram_engram__mem_get_observation
# EXIT_CODES: 0=advisory (never blocks — reinforcement failure is non-critical)
#
# This hook is DORMANT until registered in .claude/settings.json under PostToolUse.
# Registration is opt-in (separate concern from hook existence).
# To activate: add this hook under PostToolUse matcher in settings.json.
#
# Behavior:
#   Fires after mem_search and mem_get_observation MCP tool calls.
#   Extracts observation IDs from the tool result JSON, batches all reinforce()
#   calls into a SINGLE Python invocation to minimise subprocess + interpreter
#   startup overhead (~150ms per batch regardless of ID count).
#   Logs one JSONL event per observation to:
#     .cognitive-os/metrics/lifecycle-reinforcement.jsonl
#
# Latency budget:
#   Python startup + engram_client.get_observation + engram_client.save_observation
#   ≈ 150ms per reinforce() call (dominated by engram subprocess).
#   Batching means a 5-hit search fires ONE Python process for all 5 IDs.
#   Estimated wall-clock: 150ms * N_ids, but interpreter started once.
#
# Input: JSON on stdin per Claude Code hook contract:
#   {"tool_input": {...}, "tool_result": {...}}
#
# Bash 3.x compatible functions; kebab-case filename per rules/bash-naming.md.

set -euo pipefail

# Read full hook event from stdin
INPUT="$(cat)"

# FAST PATH: skip if neither tool name appears in the input
case "$INPUT" in
  *"mem_search"* | *"mem_get_observation"*) ;;
  *) exit 0 ;;
esac

# Determine which tool fired to include in the log event
TOOL_NAME="mem_search"
case "$INPUT" in
  *"mem_get_observation"*) TOOL_NAME="mem_get_observation" ;;
esac

# Resolve project root for metrics output.
# CLAUDE_PROJECT_DIR is set by the Claude Code harness when available.
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="${PROJECT_ROOT}/.cognitive-os/metrics"
METRICS_FILE="${METRICS_DIR}/lifecycle-reinforcement.jsonl"
TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"

# ---------------------------------------------------------------------------
# extract_observation_ids: parse observation IDs from the tool result JSON.
#
# mem_search returns a list of observations; mem_get_observation returns one.
# We look for "id" fields in the JSON via a single Python call (no jq dep).
# ---------------------------------------------------------------------------
extract_observation_ids() {
    ENGRAM_HOOK_INPUT="$INPUT" python3 - <<'PYEOF'
import json, sys
import os

data = json.loads(os.environ.get("ENGRAM_HOOK_INPUT", "{}"))

# The hook event JSON has top-level keys from the Claude Code hook contract.
# tool_result (or tool_output) holds the MCP tool's return value.
result = data.get("tool_result") or data.get("tool_output") or {}

ids = set()

def collect_ids(obj):
    if isinstance(obj, dict):
        if "id" in obj:
            try:
                ids.add(str(int(obj["id"])))
            except (TypeError, ValueError):
                pass
        for v in obj.values():
            collect_ids(v)
    elif isinstance(obj, list):
        for item in obj:
            collect_ids(item)

collect_ids(result)
print("\n".join(sorted(ids)))
PYEOF
}

# ---------------------------------------------------------------------------
# batch_reinforce: call EngramLifecycle.reinforce() for all IDs in one
# Python subprocess to amortise interpreter startup cost.
# ---------------------------------------------------------------------------
batch_reinforce() {
    local ids_json="$1"
    python3 - <<PYEOF
import sys, json, os

ids = json.loads("""${ids_json}""")
if not ids:
    sys.exit(0)

# Ensure lib/ is on sys.path regardless of cwd
project_root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
lib_dir = os.path.join(project_root, "lib")
if lib_dir not in sys.path:
    sys.path.insert(0, project_root)

try:
    from lib.engram_lifecycle import EngramLifecycle
    lc = EngramLifecycle()
    for obs_id in ids:
        try:
            lc.reinforce(obs_id)
        except Exception:
            pass  # advisory — never raises
except Exception:
    pass  # binary unavailable or import failure — exit 0
PYEOF
}

# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

# Extract IDs (may be empty if parsing fails)
RAW_IDS="$(extract_observation_ids 2>/dev/null || true)"

if [ -z "$RAW_IDS" ]; then
    exit 0
fi

# Convert newline-separated IDs to a JSON array for the Python batch call
IDS_JSON="$(printf '%s' "$RAW_IDS" | python3 -c "
import sys, json
lines = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]
print(json.dumps(lines))
" 2>/dev/null || echo '[]')"

if [ "$IDS_JSON" = "[]" ] || [ -z "$IDS_JSON" ]; then
    exit 0
fi

# Run reinforcement batch (advisory — failure does not block)
batch_reinforce "$IDS_JSON" 2>/dev/null || true

# Log one event per ID to the JSONL metrics file (best-effort)
if mkdir -p "$METRICS_DIR" 2>/dev/null; then
    printf '%s\n' "$RAW_IDS" | while IFS= read -r obs_id; do
        [ -z "$obs_id" ] && continue
        printf '{"timestamp":"%s","observation_id":"%s","tool":"%s"}\n' \
            "$TIMESTAMP" "$obs_id" "$TOOL_NAME" \
            >> "$METRICS_FILE" 2>/dev/null || true
    done
fi

exit 0
