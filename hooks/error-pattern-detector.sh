#!/bin/bash
# Error Pattern Detector — PreToolUse for Agent
# Checks for repeated error patterns and injects warnings into agent context.
# Fast (<3s), non-blocking. Outputs warning text to stdout if patterns found.

set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_FILE="$PROJECT_DIR/.cognitive-os/metrics/error-learning.jsonl"

# No metrics file or empty — nothing to check
[ ! -s "$METRICS_FILE" ] && exit 0

# Calculate 24-hour cutoff (epoch seconds)
CUTOFF=$(date -v-24H +%s 2>/dev/null || date -d '24 hours ago' +%s 2>/dev/null || echo "0")

# Read recent entries (last 100 lines max for speed) and filter to last 24h
RECENT=$(tail -100 "$METRICS_FILE" 2>/dev/null | jq -c --argjson cutoff "$CUTOFF" \
  'select((.timestamp_epoch // 0) > $cutoff)' 2>/dev/null)

[ -z "$RECENT" ] && exit 0

# Group by service+type, count occurrences, find patterns with 3+
PATTERNS=$(echo "$RECENT" | jq -s '
  group_by(.service + "|" + .type) |
  map({
    key: (.[0].service + "|" + .[0].type),
    service: .[0].service,
    type: .[0].type,
    count: length,
    contexts: [.[] | .context] | unique | map(select(. != "")),
    frameworks: [.[] | .framework] | unique,
    latest_error: (sort_by(.timestamp_epoch) | last | .error | if length > 200 then .[0:200] + "..." else . end)
  }) |
  map(select(.count >= 3))
' 2>/dev/null)

# No patterns with 3+ occurrences
if [ -z "$PATTERNS" ] || [ "$PATTERNS" = "[]" ]; then
  exit 0
fi

# Build warning text
PATTERN_COUNT=$(echo "$PATTERNS" | jq 'length' 2>/dev/null)

if [ "$PATTERN_COUNT" -gt 0 ] 2>/dev/null; then
  echo ""
  echo "=== ERROR PATTERN WARNINGS ==="
  echo ""

  if [ "$PATTERN_COUNT" -eq 1 ]; then
    # Single pattern: keep the original WARNING: prefix format
    echo "$PATTERNS" | jq -r '.[] |
      "WARNING: KNOWN ERROR PATTERN: \(.service) has had \(.count) \(.type) errors in the last 24h.\n" +
      (if (.contexts | length) > 0 then "  Common cause: " + (.contexts | join(", ")) + "\n" else "" end) +
      "  Framework(s): " + (.frameworks | join(", ")) + "\n" +
      "  Latest error: " + .latest_error + "\n" +
      (if .type == "TEST_FAILURE" and (.contexts | any(contains("missing import"))) then
        "  Recommended: check imports and run dependency resolution before tests.\n"
      elif .type == "BUILD_ERROR" and (.contexts | any(contains("TypeScript"))) then
        "  Recommended: fix type errors before building.\n"
      elif .type == "LINT_ERROR" then
        "  Recommended: run auto-fix (eslint --fix / go fmt) before manual fixes.\n"
      elif .contexts | any(contains("connection refused")) then
        "  Recommended: verify infrastructure is running (docker-compose ps).\n"
      elif .contexts | any(contains("timeout")) then
        "  Recommended: check service health before running tests.\n"
      else
        "  Recommended: review error pattern before proceeding.\n"
      end)
    ' 2>/dev/null
  else
    # Multiple patterns: render as compact Markdown table via FormatConverter
    COMPACT=$(echo "$PATTERNS" | python3 -c "
import sys, json
try:
    from lib.format_converter import FormatConverter
except ImportError:
    import os, sys
    sys.path.insert(0, os.environ.get('CLAUDE_PROJECT_DIR', '.'))
    from lib.format_converter import FormatConverter

patterns = json.load(sys.stdin)
records = []
for p in patterns:
    records.append({
        'service': p.get('service', ''),
        'type': p.get('type', ''),
        'count': p.get('count', 0),
        'cause': ', '.join(p.get('contexts', []))[:50] or '—',
        'framework': ', '.join(p.get('frameworks', []))[:30] or '—',
    })
print(FormatConverter.to_markdown_table(records))
" 2>/dev/null)

    if [ -n "$COMPACT" ]; then
      echo "WARNING: KNOWN ERROR PATTERNS ($PATTERN_COUNT patterns in last 24h):"
      echo ""
      echo "$COMPACT"
    else
      # Fallback to original format if Python call fails
      echo "$PATTERNS" | jq -r '.[] |
        "WARNING: KNOWN ERROR PATTERN: \(.service) has had \(.count) \(.type) errors in the last 24h." +
        (if (.contexts | length) > 0 then " Cause: " + (.contexts | join(", ")) else "" end)
      ' 2>/dev/null
    fi
  fi

  echo ""
  echo "Run /error-analyzer for detailed analysis and skill improvement proposals."
  echo "=== END ERROR PATTERN WARNINGS ==="
  echo ""
fi

exit 0
