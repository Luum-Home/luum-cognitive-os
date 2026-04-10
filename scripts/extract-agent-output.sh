#!/usr/bin/env bash
# extract-agent-output.sh — Extract assistant text from agent JSONL output files
#
# Usage:
#   extract-agent-output.sh <output-file>         # all assistant text
#   extract-agent-output.sh <output-file> --last  # final assistant message only
#   extract-agent-output.sh <output-file> --summary # one-line summary (tool_calls, tokens, duration)
#
# Requires: jq

set -euo pipefail

usage() {
    echo "Usage: $(basename "$0") <output-file> [--last|--summary]" >&2
    echo "" >&2
    echo "Extract assistant text from Claude Code agent JSONL output files." >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  --last      Only the final assistant message" >&2
    echo "  --summary   One-line summary: tool_calls, tokens, duration" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $(basename "$0") /tmp/claude-501/.../tasks/abc123.output" >&2
    echo "  $(basename "$0") /tmp/claude-501/.../tasks/abc123.output --last" >&2
    exit 1
}

if [[ $# -lt 1 ]]; then
    usage
fi

OUTPUT_FILE="$1"
MODE="${2:-}"

if [[ ! -f "$OUTPUT_FILE" ]]; then
    echo "Error: file not found: $OUTPUT_FILE" >&2
    exit 1
fi

if ! command -v jq &>/dev/null; then
    echo "Error: jq is required but not installed." >&2
    echo "Install: brew install jq  (macOS) or apt install jq (Linux)" >&2
    exit 1
fi

case "$MODE" in
    --last)
        # Extract text blocks from the last assistant message that has text content
        jq -r '
            select(.type == "assistant") |
            .message.content[]? |
            select(.type == "text") |
            .text
        ' "$OUTPUT_FILE" | tail -n +1 | awk '
            BEGIN { buf = ""; }
            { buf = (buf == "" ? $0 : buf "\n" $0) }
            END { print buf }
        ' | python3 -c "
import sys
lines = sys.stdin.read()
# Find last assistant message boundary by collecting all outputs and printing the last block
# Since jq above streams all text blocks, we re-parse via python for the true last message
import json, os

output_file = os.environ.get('_OUTPUT_FILE', '')
last_texts = []
with open('$OUTPUT_FILE', 'r') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get('type') != 'assistant':
            continue
        content = obj.get('message', {}).get('content', [])
        if not isinstance(content, list):
            continue
        texts = [b['text'] for b in content if isinstance(b, dict) and b.get('type') == 'text' and b.get('text')]
        if texts:
            last_texts = texts
print('\n\n'.join(last_texts))
"
        ;;
    --summary)
        # One-line summary using Python for accuracy
        python3 - "$OUTPUT_FILE" <<'PYEOF'
import sys, json
from datetime import datetime

path = sys.argv[1]
tool_calls = 0
tokens = 0
first_ts = last_ts = None

with open(path, 'r') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_str = obj.get('timestamp')
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
            except ValueError:
                pass
        if obj.get('type') != 'assistant':
            continue
        content = obj.get('message', {}).get('content', [])
        if isinstance(content, list):
            tool_calls += sum(1 for b in content if isinstance(b, dict) and b.get('type') == 'tool_use')
        tokens += obj.get('message', {}).get('usage', {}).get('output_tokens', 0)

duration_ms = 0
if first_ts and last_ts:
    duration_ms = int((last_ts - first_ts).total_seconds() * 1000)

print(f"tool_calls={tool_calls}  tokens={tokens}  duration={duration_ms}ms")
PYEOF
        ;;
    "")
        # Default: all assistant text, most recent last
        jq -rn '
            [inputs | select(.type == "assistant") |
             .message.content[]? | select(.type == "text") | .text] |
            join("\n\n")
        ' "$OUTPUT_FILE"
        ;;
    *)
        echo "Unknown option: $MODE" >&2
        usage
        ;;
esac
