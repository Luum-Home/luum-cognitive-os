#!/usr/bin/env bash
# SCOPE: both
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

# ─── Parse + match in a single Python process ────────────────────────────────
# Performance fix: the prior implementation ran grep+sed subprocesses for EVERY
# line in cognitive-os.yaml during parsing (~800 forks), plus one grep per trigger
# during matching (~60 forks on a 60-trigger config) — totaling 2+ seconds on the
# real project config. Replaced with one Python call: parse YAML, compile regexes,
# match — all in-process. Result: < 100ms regardless of config size.

RULES_DIR="$_PROJECT_DIR/rules"
[ ! -d "$RULES_DIR" ] && exit 0
[ ! -f "$_CONFIG_FILE" ] && exit 0

MAX_RULES=3
_matched_rules=$(python3 -c "
import re, sys, os

config_path = sys.argv[1]
prompt_lower = sys.argv[2]
max_rules = int(sys.argv[3])
rules_dir = sys.argv[4]

# Parse contextual_triggers block from YAML without a full YAML parser.
# Extracts indented key: \"value\" pairs under contextual_triggers: section.
triggers = []
in_triggers = False
with open(config_path) as f:
    for line in f:
        stripped = line.rstrip()
        # Detect section start (leading spaces + contextual_triggers:, optional comment)
        if re.match(r'^\s+contextual_triggers:\s*(#.*)?$', stripped):
            in_triggers = True
            continue
        if not in_triggers:
            continue
        # Empty line or comment: skip
        if not stripped or stripped.lstrip().startswith('#'):
            continue
        # Measure indentation: trigger entries have 6-space indent; leave the
        # block when we encounter a line with indent <= 4 (same or outer level).
        indent = len(stripped) - len(stripped.lstrip())
        if indent <= 4:
            break
        # Extract rule-name: \"pattern\"
        m = re.match(r'^\s+([a-z0-9-]+)\s*:\s*\"(.+)\"\s*$', stripped)
        if m:
            triggers.append((m.group(1), m.group(2)))

# Match prompt against triggers (all in-process, no subprocess forks)
matched = []
for rule_name, pattern in triggers:
    if len(matched) >= max_rules:
        break
    rule_file = os.path.join(rules_dir, rule_name + '.md')
    if not os.path.isfile(rule_file):
        continue
    try:
        if re.search(pattern, prompt_lower, re.IGNORECASE):
            matched.append(rule_name)
    except re.error:
        pass

print('\n'.join(matched))
" "$_CONFIG_FILE" "$PROMPT_LOWER" "$MAX_RULES" "$RULES_DIR" 2>/dev/null)
_match_count=0
if [ -n "$_matched_rules" ]; then
  _match_count=$(printf '%s\n' "$_matched_rules" | grep -c '[^[:space:]]' 2>/dev/null || echo 0)
fi

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
