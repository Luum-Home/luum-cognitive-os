#!/usr/bin/env bash
# SCOPE: os-only
# rate-limit-detector.sh — PostToolUse advisory
#
# Detects Claude Code subscription rate-limit errors in tool output and
# suggests falling back to direct-SDK overflow providers (ADR-049).
#
# Canonical patterns matched in stderr / tool-result payloads:
#   "out of extra usage"
#   "resets [0-9]+[apm]+"
#   "approximate[ly]* usage limit"
#   "rate limit exceeded" (Anthropic generic)
#   "You're approaching your usage limit"
#
# Behavior:
#   - Append a JSONL record to .cognitive-os/metrics/rate-limit-events.jsonl
#   - Emit a one-line advisory to stderr when the pattern first matches
#     in the current session (deduped via session state file)
#   - If ALIBABA_QWEN_API_KEY is set in env AND lib/qwen_provider.py exists,
#     suggest flipping to direct-SDK dispatch. If not, tell the user what
#     they need to subscribe/configure.
#   - Exits 0 ALWAYS (advisory, never blocks).
#
# Hook input contract (Claude Code PostToolUse hooks):
#   stdin: JSON with `tool_name`, `tool_input`, `tool_response` fields.
#   We only care about tool_response.error or tool_response.stderr contents.
#
# Reference: docs/02-Decisions/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CLAUDE_SESSION_ID:-default}}"
SESSION_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
METRICS_FILE="$METRICS_DIR/rate-limit-events.jsonl"
SEEN_FLAG="$SESSION_DIR/rate-limit-advised.flag"

# Read stdin (hook input). If nothing, silent exit.
INPUT=""
if [ -t 0 ]; then
  # No stdin piped — probably run manually. Exit silently.
  exit 0
fi
INPUT="$(cat || true)"
[ -z "$INPUT" ] && exit 0

# Extract relevant text blobs from the hook payload. We grep the entire
# payload rather than parsing JSON to avoid a jq dependency and handle
# both structured errors and plain-text stderr.
# Limit to first 50KB to bound cost on large tool outputs.
PAYLOAD="$(printf '%s' "$INPUT" | head -c 51200)"

# Known rate-limit patterns (case-insensitive). Keep as a pipe-alternated regex.
# Update this list as Claude's error wording evolves.
PATTERNS='out of extra usage|approximate.{0,12}usage limit|approaching your usage limit|You'\''re out of|rate limit exceeded|resets [0-9]+ *[apm]'

if ! printf '%s' "$PAYLOAD" | grep -Eqi "$PATTERNS"; then
  exit 0
fi

# Pattern matched — record and advise (dedup per session).
mkdir -p "$METRICS_DIR" "$SESSION_DIR" 2>/dev/null || true

ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")
# Extract the first matching snippet (~120 chars) for the JSONL record.
snippet=$(printf '%s' "$PAYLOAD" | grep -Eoi "$PATTERNS" | head -1 | head -c 120)

# Structured record (always append — not deduped, so we can count hits)
printf '{"ts":"%s","session_id":"%s","match":"%s"}\n' \
  "$ts" "$SESSION_ID" "${snippet//\"/\\\"}" \
  >> "$METRICS_FILE" 2>/dev/null || true

# Advisory (dedup: only first occurrence per session emits stderr)
if [ -f "$SEEN_FLAG" ]; then
  exit 0
fi
touch "$SEEN_FLAG" 2>/dev/null || true

# Build the advisory message based on what's actually configured
if [ -n "${ALIBABA_QWEN_API_KEY:-}" ] && [ -f "$PROJECT_DIR/lib/qwen_provider.py" ]; then
  cat >&2 <<'ADV'
[rate-limit-detector] Claude Code subscription rate-limit detected.
  Overflow available: Alibaba Qwen Coding Plan Pro (ADR-049).
  Dispatch via lib/qwen_provider.py.call() instead of the native Agent
  tool for remaining sub-agents this session. Or run:
    python3 -c "from lib.qwen_provider import call; print(call([{'role':'user','content':'hi'}]).text)"
ADV
elif [ -f "$PROJECT_DIR/lib/qwen_provider.py" ]; then
  cat >&2 <<'ADV'
[rate-limit-detector] Claude Code subscription rate-limit detected.
  ADR-049 overflow module present (lib/qwen_provider.py) but NOT configured.
  To activate: subscribe to Alibaba Qwen Coding Plan Pro ($50/mo) at
  https://www.alibabacloud.com/en/campaign/ai-coding-plan, then add
  ALIBABA_QWEN_API_KEY=<your-key> to .env. See ADR-049 for rationale.
ADV
else
  cat >&2 <<'ADV'
[rate-limit-detector] Claude Code subscription rate-limit detected.
  No direct-SDK overflow module found (lib/qwen_provider.py missing).
  See docs/02-Decisions/adrs/ADR-049-llm-gateway-selection-and-overflow-providers.md
  for the recommended overflow stack.
ADV
fi

exit 0
