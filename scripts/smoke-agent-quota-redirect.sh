#!/usr/bin/env bash
# Smoke: ADR-056 Level 2 agent-quota-redirect hook
# Seeds high-pressure metrics + enables opt-in + invokes hook +
# verifies block (exit 2) + AGENT_REDIRECT block is parseable.
#
# Runs in a tempdir so it never mutates the real .cognitive-os/metrics tree.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$REPO/hooks/agent-quota-redirect.sh"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "[smoke] repo=$REPO work=$WORK"

# Build fake project layout
PROJ="$WORK/proj"
mkdir -p "$PROJ/.cognitive-os/metrics"
ln -s "$REPO/lib" "$PROJ/lib"

# Seed 2 rate-limit events ~30s old
TS_NOW="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
for _ in 1 2; do
  echo "{\"ts\":\"$TS_NOW\",\"session_id\":\"smoke\",\"match\":\"out of extra usage\"}" \
    >> "$PROJ/.cognitive-os/metrics/rate-limit-events.jsonl"
done
echo "[smoke] seeded 2 rate-limit events"

# Invoke the hook with opt-in enabled. Unset PYTEST_CURRENT_TEST + CI so
# the bypass branches don't fire.
PAYLOAD='{"tool_name":"Agent","tool_input":{"prompt":"test task with `backticks`"}}'

set +e
OUTPUT=$(
  env -i \
    PATH="$PATH" HOME="$HOME" \
    CLAUDE_PROJECT_DIR="$PROJ" \
    COS_AUTO_REDIRECT_AGENT=1 \
    bash "$HOOK" <<< "$PAYLOAD" 2>&1
)
STATUS=$?
set -e

echo "[smoke] hook exit status: $STATUS"
echo "[smoke] hook output:"
echo "----------------------------------------"
echo "$OUTPUT"
echo "----------------------------------------"

if [ "$STATUS" -ne 2 ]; then
  echo "[smoke] FAIL: expected exit 2 (block), got $STATUS" >&2
  exit 1
fi

# Verify AGENT_REDIRECT block is parseable via the Python library.
if ! PARSED=$(printf '%s' "$OUTPUT" | uv run python3 -c "
import sys
sys.path.insert(0, '$REPO')
from lib.agent_redirect_protocol import parse_redirect_message
parsed = parse_redirect_message(sys.stdin.read())
if not parsed:
    sys.exit(1)
print(f\"reason={parsed['reason']} pressure={parsed['pressure']:.2f}\")
print(f\"command={parsed['command']}\")
"); then
  echo "[smoke] FAIL: could not parse AGENT_REDIRECT block" >&2
  exit 1
fi

echo "[smoke] parsed successfully:"
echo "$PARSED"

# Verify the event was logged.
EVENTS="$PROJ/.cognitive-os/metrics/agent-redirect.jsonl"
if [ ! -s "$EVENTS" ]; then
  echo "[smoke] FAIL: agent-redirect.jsonl was not written" >&2
  exit 1
fi
LAST_DECISION=$(tail -1 "$EVENTS" | uv run python3 -c "import json,sys; print(json.loads(sys.stdin.read())['decision'])")
if [ "$LAST_DECISION" != "block" ]; then
  echo "[smoke] FAIL: last event decision=$LAST_DECISION (expected block)" >&2
  exit 1
fi

echo "[smoke] OK — ADR-056 L2 hook blocks + emits parseable AGENT_REDIRECT"
exit 0
