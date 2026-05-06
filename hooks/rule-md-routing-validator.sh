#!/usr/bin/env bash
# SCOPE: os-only
# PostToolUse Write hook: rules/*.md Routing Pattern Validator (ADR-179)
#
# When a Write tool call targets a rules/*.md file, validate frontmatter:
#   - enforcement: present and one of {hook, agent-instruction, hybrid}
#   - if agent-instruction or hybrid: routing_patterns: present
#   - if hook: corresponding hook file exists OR rule listed in
#              hooks/_lib/registration-allowlist.txt
#
# Non-blocking advisory hook — warns to stderr, never blocks the write.
# Logs to .cognitive-os/metrics/rule-md-routing-validator.jsonl
#
# Event:    PostToolUse Write
# Type:     command
# Async:    true
# Exit:     always 0
# Latency:  <100ms (pure bash, optional python for JSON log)
#
# Killswitch: DISABLE_HOOK_RULE_MD_ROUTING_VALIDATOR=1
# Allowlist:  hooks/_lib/registration-allowlist.txt

set -uo pipefail

if [[ "${DISABLE_HOOK_RULE_MD_ROUTING_VALIDATOR:-0}" == "1" ]]; then
  exit 0
fi

INPUT="$(cat)"

FILE_PATH=""
if command -v jq &>/dev/null; then
  FILE_PATH="$(echo "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || true)"
else
  FILE_PATH="$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*: *"//' | sed 's/"//' | head -1 || true)"
fi

# Only inspect files under rules/ ending in .md (excluding RULES-COMPACT/ROADMAP).
if [[ -z "$FILE_PATH" ]]; then exit 0; fi
case "$FILE_PATH" in
  */rules/*.md|rules/*.md) : ;;
  *) exit 0 ;;
esac
base="$(basename "$FILE_PATH")"
case "${base^^}" in
  RULES-COMPACT.MD|ROADMAP.MD|README.MD) exit 0 ;;
esac

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
RULE_NAME="${base%.md}"

# Read the file content (PostToolUse — file is on disk).
if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi
CONTENT="$(cat "$FILE_PATH" 2>/dev/null || true)"

if [[ -z "$CONTENT" ]]; then
  exit 0
fi

# Skip files without YAML frontmatter (legacy rules).
if ! printf '%s\n' "$CONTENT" | head -1 | grep -q '^---$' && \
   ! printf '%s\n' "$CONTENT" | head -5 | grep -q '^---$'; then
  exit 0
fi

ENFORCEMENT="$(printf '%s\n' "$CONTENT" | awk '/^---$/{c++; next} c==1 && /^enforcement:/{print $2; exit}' | tr -d '"' | tr -d "'")"
HAS_ROUTING="$(printf '%s\n' "$CONTENT" | awk '/^---$/{c++; next} c==1 && /^routing_patterns:/{print "yes"; exit}')"

STATUS="ok"
DETAIL=""

if [[ -z "$ENFORCEMENT" ]]; then
  STATUS="missing-enforcement"
  DETAIL="No 'enforcement:' field in frontmatter."
elif [[ "$ENFORCEMENT" == "agent-instruction" || "$ENFORCEMENT" == "hybrid" ]]; then
  if [[ "$HAS_ROUTING" != "yes" ]]; then
    STATUS="missing-routing-patterns"
    DETAIL="enforcement=$ENFORCEMENT requires routing_patterns: block."
  fi
elif [[ "$ENFORCEMENT" == "hook" ]]; then
  HOOK_FILE="$PROJECT_DIR/hooks/${RULE_NAME}.sh"
  ALLOWLIST="$PROJECT_DIR/hooks/_lib/registration-allowlist.txt"
  if [[ ! -f "$HOOK_FILE" ]]; then
    if [[ ! -f "$ALLOWLIST" ]] || ! grep -qE "^${RULE_NAME}\.sh\b" "$ALLOWLIST" 2>/dev/null; then
      STATUS="stale-hook-reference"
      DETAIL="enforcement=hook but neither hooks/${RULE_NAME}.sh nor allowlist entry exists."
    fi
  fi
elif [[ "$ENFORCEMENT" != "hook" && "$ENFORCEMENT" != "agent-instruction" && "$ENFORCEMENT" != "hybrid" ]]; then
  STATUS="invalid-enforcement"
  DETAIL="enforcement='$ENFORCEMENT' is not one of {hook, agent-instruction, hybrid}."
fi

# Append to JSONL log.
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
mkdir -p "$METRICS_DIR" 2>/dev/null || true
LOG_FILE="$METRICS_DIR/rule-md-routing-validator.jsonl"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# Avoid embedding raw paths with quotes — use jq if available, else fallback.
if command -v jq &>/dev/null; then
  jq -nc \
    --arg ts "$TS" \
    --arg path "$FILE_PATH" \
    --arg rule "$RULE_NAME" \
    --arg enf "$ENFORCEMENT" \
    --arg status "$STATUS" \
    --arg detail "$DETAIL" \
    '{ts:$ts, file_path:$path, rule:$rule, enforcement:$enf, status:$status, detail:$detail}' \
    >> "$LOG_FILE" 2>/dev/null || true
else
  printf '{"ts":"%s","file_path":"%s","rule":"%s","enforcement":"%s","status":"%s","detail":"%s"}\n' \
    "$TS" "$FILE_PATH" "$RULE_NAME" "$ENFORCEMENT" "$STATUS" "$DETAIL" >> "$LOG_FILE" 2>/dev/null || true
fi

if [[ "$STATUS" != "ok" ]]; then
  cat >&2 <<WARNING

[rule-md-routing-validator] ADVISORY -- ${FILE_PATH}
  rule:        ${RULE_NAME}
  status:      ${STATUS}
  detail:      ${DETAIL}

This rule will not be visible to the orchestrator's RuleRouter (ADR-179) until
the issue is resolved. The write proceeds — this hook is non-blocking.
WARNING
fi

exit 0
