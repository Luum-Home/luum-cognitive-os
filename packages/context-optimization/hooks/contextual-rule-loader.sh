#!/usr/bin/env bash
# contextual-rule-loader.sh — PreToolUse hook on Agent
# Loads full rule files on demand when the agent prompt matches contextual triggers.
#
# When rules.loading.strategy is "compact", only RULES-COMPACT.md is loaded at startup.
# This hook injects the FULL rule content when the agent's prompt matches a trigger regex.
#
# Performance target: < 100ms
# Max rules injected per call: 3

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# ─── Source shared libraries ──────────────────────────────────────────────────

_HOOK_NAME="contextual-rule-loader"
source "$(dirname "$0")/_lib/common.sh"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

# ─── Gate: only Agent tool calls ──────────────────────────────────────────────

require_tool "Agent" "task" "delegate"

# ─── Early exits ──────────────────────────────────────────────────────────────

check_private_mode

# If strategy is "full", all rules are already loaded — skip
if [ -f "$_CONFIG_FILE" ]; then
  _strategy=$(grep -A5 '^rules:' "$_CONFIG_FILE" 2>/dev/null \
    | grep 'strategy:' | head -1 \
    | sed 's/.*strategy:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]')
  if [ "$_strategy" = "full" ]; then
    exit 0
  fi
fi

# ─── Extract prompt from stdin ────────────────────────────────────────────────

PROMPT=$(stdin_field '.tool_input.prompt' '')
[ -z "$PROMPT" ] && exit 0

# Lowercase the prompt for case-insensitive matching
PROMPT_LOWER=$(echo "$PROMPT" | tr '[:upper:]' '[:lower:]')

# ─── Parse contextual triggers from config ────────────────────────────────────

# Extract the contextual_triggers block from cognitive-os.yaml
# Format: rule-name: "regex pattern"
# We parse this with grep+sed for speed (no Python, no heavy YAML parser)

RULES_DIR="$_PROJECT_DIR/rules"
[ ! -d "$RULES_DIR" ] && exit 0
[ ! -f "$_CONFIG_FILE" ] && exit 0

# Extract trigger lines: indented key-value pairs under contextual_triggers
# Each line looks like:  auto-repair: "auto-repair|auto_repair|circuit.breaker|..."
_in_triggers=false
_triggers=""
while IFS= read -r line; do
  # Detect start of contextual_triggers block
  if echo "$line" | grep -qE '^\s+contextual_triggers:'; then
    _in_triggers=true
    continue
  fi
  # If in triggers block, collect indented key: "value" lines
  if [ "$_in_triggers" = "true" ]; then
    # Stop if we hit a non-indented line or a line with less indentation (new section)
    if echo "$line" | grep -qE '^[a-z#]|^\s{0,5}[a-z]'; then
      # Check if this is a comment or less-indented key (new YAML section)
      _indent=$(echo "$line" | sed 's/[^ ].*//' | wc -c)
      if [ "$_indent" -le 6 ]; then
        break
      fi
    fi
    # Skip comment lines and empty lines
    if echo "$line" | grep -qE '^\s*#|^\s*$'; then
      continue
    fi
    # Extract rule-name and pattern
    _rule_name=$(echo "$line" | sed 's/^[[:space:]]*//' | cut -d: -f1)
    _pattern=$(echo "$line" | sed 's/^[^"]*"//' | sed 's/"[[:space:]]*$//')
    if [ -n "$_rule_name" ] && [ -n "$_pattern" ]; then
      _triggers="${_triggers}${_rule_name}|${_pattern}"$'\n'
    fi
  fi
done < "$_CONFIG_FILE"

[ -z "$_triggers" ] && exit 0

# ─── Match prompt against triggers ────────────────────────────────────────────

MAX_RULES=3
_matched_rules=""
_match_count=0

while IFS='|' read -r _rule_name _pattern; do
  [ -z "$_rule_name" ] && continue
  [ -z "$_pattern" ] && continue
  [ "$_match_count" -ge "$MAX_RULES" ] && break

  # Use grep -iEq for fast regex matching against the prompt
  if echo "$PROMPT_LOWER" | grep -iEq "$_pattern"; then
    _rule_file="$RULES_DIR/${_rule_name}.md"
    if [ -f "$_rule_file" ]; then
      _matched_rules="${_matched_rules}${_rule_name}"$'\n'
      _match_count=$((_match_count + 1))
    fi
  fi
done <<< "$_triggers"

# ─── Early exit if no matches ────────────────────────────────────────────────

[ "$_match_count" -eq 0 ] && exit 0

# ─── Output matched rules ────────────────────────────────────────────────────

echo ""
echo "CONTEXTUAL RULES (loaded on demand):"

while IFS= read -r _rule_name; do
  [ -z "$_rule_name" ] && continue
  _rule_file="$RULES_DIR/${_rule_name}.md"
  echo "--- rules/${_rule_name}.md ---"
  cat "$_rule_file"
  echo ""
  echo "--- end ---"
  echo ""
done <<< "$_matched_rules"

# ─── Log to metrics ──────────────────────────────────────────────────────────

_metrics_dir=$(_resolve_metrics_dir)
_now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
_rules_list=$(echo "$_matched_rules" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')

_log_entry=$(jq -c -n \
  --arg ts "$_now" \
  --argjson count "$_match_count" \
  --arg rules "$_rules_list" \
  --arg prompt "$(echo "$PROMPT" | head -c 200)" \
  '{timestamp: $ts, rules_injected: $count, rules: $rules, prompt_preview: $prompt}' 2>/dev/null)

if [ -n "$_log_entry" ]; then
  safe_jsonl_append "$_metrics_dir/contextual-rules.jsonl" "$_log_entry"
fi

exit 0
