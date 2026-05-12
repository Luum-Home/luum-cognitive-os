#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: research-quality, audit-symmetry, evidence
#
# PostToolUse hook on Edit|Write — when a markdown file is written under
# docs/06-Daily/reports/, score it on the four ADR-175 research-quality dimensions
# and log the result to .cognitive-os/metrics/research-quality.jsonl.
#
# Non-blocking. Latency budget < 300ms (we cap python with `timeout 1`).
# Killswitch: respects SO_KILLSWITCH and DISABLE_HOOK_RESEARCH_QUALITY_VALIDATOR.

set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="research-quality-validator"
source "$(dirname "$0")/_lib/common.sh" 2>/dev/null || true

# Runtime kill via env (matches the convention used in other validators).
if [[ "${DISABLE_HOOK_RESEARCH_QUALITY_VALIDATOR:-}" == "1" || \
      "${DISABLE_HOOK_RESEARCH_QUALITY_VALIDATOR:-}" == "true" ]]; then
  exit 0
fi

INPUT="$(cat)"

TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)"
case "$TOOL_NAME" in
  Edit|Write|MultiEdit) : ;;
  *) exit 0 ;;
esac

# File path lives under .tool_input.file_path for Write/Edit.
FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null)"
[[ -z "$FILE_PATH" ]] && exit 0

# Only score docs/06-Daily/reports/*.md
case "$FILE_PATH" in
  *docs/06-Daily/reports/*.md) : ;;
  *) exit 0 ;;
esac

[[ ! -f "$FILE_PATH" ]] && exit 0

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
# Locate the COS install (where lib/research_quality_advisor.py lives).
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
mkdir -p "$METRICS_DIR" 2>/dev/null || true
LOG_FILE="$METRICS_DIR/research-quality.jsonl"

# Score via Python (stdlib only).  Hard-cap latency.
SCORE_JSON="$(timeout 1 python3 - <<PYEOF 2>/dev/null
import json, sys, pathlib
sys.path.insert(0, "${COS_ROOT}")
sys.path.insert(0, "${PROJECT_DIR}")
try:
    from lib.research_quality_advisor import ResearchQualityAdvisor
except Exception as exc:
    print(json.dumps({"error": "import_failed", "detail": str(exc)}))
    sys.exit(0)

text = pathlib.Path("${FILE_PATH}").read_text(encoding="utf-8", errors="replace")
report = ResearchQualityAdvisor().score(text)
out = report.to_jsonable()
out["report_path"] = "${FILE_PATH}"
print(json.dumps(out))
PYEOF
)"

[[ -z "$SCORE_JSON" ]] && exit 0

# Append timestamp + record to JSONL.
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RECORD="$(printf '%s' "$SCORE_JSON" | jq -c --arg ts "$TIMESTAMP" '. + {timestamp:$ts}' 2>/dev/null)"
[[ -n "$RECORD" ]] && printf '%s\n' "$RECORD" >> "$LOG_FILE"

# Emit non-blocking warning if score below threshold (default 70).
SCORE="$(printf '%s' "$SCORE_JSON" | jq -r '.overall_score // 100' 2>/dev/null)"
THRESHOLD="${RESEARCH_QUALITY_THRESHOLD:-70}"

awk -v s="$SCORE" -v t="$THRESHOLD" 'BEGIN{exit !(s+0 < t+0)}' && {
  ASYM="$(printf '%s' "$SCORE_JSON" | jq -r '.asymmetric_rows // 0')"
  TOTAL="$(printf '%s' "$SCORE_JSON" | jq -r '.total_rows // 0')"
  echo "" >&2
  echo "WARNING [research-quality]: ${FILE_PATH}" >&2
  echo "  overall score: ${SCORE} (threshold ${THRESHOLD})" >&2
  echo "  asymmetric rows: ${ASYM}/${TOTAL}" >&2
  printf '%s' "$SCORE_JSON" | jq -r '.suggestions[]?' 2>/dev/null | sed 's/^/  - /' >&2
  echo "" >&2
}

exit 0
