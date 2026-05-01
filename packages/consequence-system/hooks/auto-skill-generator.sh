#!/usr/bin/env bash
# SCOPE: os-only
# PostToolUse hook: Auto-generate SKILL.md from complex agent completions
# Fires on "Agent" tool use — detects complex successful tasks and templates a reusable skill
# Must complete in <5 seconds

set -euo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 5
check_capability_level "auto-skill-generator"
# Runtime disable: DISABLE_HOOK_AUTO_SKILL_GENERATOR=true skips this hook for the session
check_disabled_env "auto-skill-generator"

SKILLS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/skills/auto-generated"
METRICS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/metrics"
LOG_FILE="$METRICS_DIR/auto-skill-generation.log"

# Ensure directories exist
mkdir -p "$SKILLS_DIR" "$METRICS_DIR"

# Read stdin (JSON with tool_name, tool_input, tool_response)
INPUT=$(cat)

# Exit early if no input
if [ -z "$INPUT" ]; then
  exit 0
fi

# Require jq
if ! command -v jq &>/dev/null; then
  exit 0
fi

# Only process Agent tool
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [ "$TOOL_NAME" != "Agent" ]; then
  exit 0
fi

# Check private mode — skip if active
if [ -f "/tmp/claude-private-mode-active" ]; then
  exit 0
fi

# Check opt-out env var
if [ "${NO_AUTO_SKILL:-}" = "true" ]; then
  exit 0
fi

# --- Complexity Detection ---

# Determine if the agent completed successfully
IS_ERROR=$(echo "$INPUT" | jq -r '
  if .tool_response.error then "true"
  elif .tool_response.is_error then "true"
  elif (.tool_response.status // "ok") == "error" then "true"
  else "false"
  end
' 2>/dev/null)

if [ "$IS_ERROR" = "true" ]; then
  exit 0
fi

# Extract tool use count from the response (heuristic: count tool_use mentions or num_tool_uses field)
TOOL_USES=$(echo "$INPUT" | jq -r '
  .tool_response.num_tool_uses //
  .tool_response.tool_use_count //
  .tool_response.stats.tool_uses //
  0
' 2>/dev/null)

# If num_tool_uses not in structured fields, estimate from response text length
RESPONSE_TEXT=$(echo "$INPUT" | jq -r '
  .tool_response.result // .tool_response.output // .tool_response.content // ""
' 2>/dev/null)
RESPONSE_LEN=${#RESPONSE_TEXT}

if [ "$TOOL_USES" = "0" ] || [ "$TOOL_USES" = "null" ]; then
  # Heuristic: estimate complexity from response length and content
  HAS_CREATED_FILES=$(echo "$RESPONSE_TEXT" | grep -cEi "(created|wrote|generated|added) .*(file|skill|component|module|service)" 2>/dev/null || echo "0")
  HAS_FIXED_BUG=$(echo "$RESPONSE_TEXT" | grep -cEi "(fixed|resolved|patched|repaired|debugged)" 2>/dev/null || echo "0")

  # Require substantial response (>8000 chars ~ roughly 10+ tool uses)
  if [ "$RESPONSE_LEN" -lt 8000 ]; then
    # Unless it clearly created files or fixed bugs with decent length
    if [ "$RESPONSE_LEN" -lt 3000 ] || { [ "$HAS_CREATED_FILES" -eq 0 ] && [ "$HAS_FIXED_BUG" -eq 0 ]; }; then
      exit 0
    fi
  fi
else
  # Structured tool_uses count available — require >= 10
  if [ "$TOOL_USES" -lt 10 ]; then
    exit 0
  fi
fi

# --- Extract Task Info ---

# Get the task description
TASK_DESCRIPTION=$(echo "$INPUT" | jq -r '
  .tool_input.description // .tool_input.prompt // "unknown task"
' 2>/dev/null | head -c 500)

# Get the result summary (truncated for SKILL.md)
RESULT_SUMMARY=$(echo "$RESPONSE_TEXT" | head -c 2000)

# --- Generate Skill Slug ---

# Create a slug from the task description
SKILL_SLUG=$(echo "$TASK_DESCRIPTION" \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's/[^a-z0-9]+/-/g' \
  | sed -E 's/^-+|-+$//g' \
  | head -c 60)

# Ensure slug is not empty
if [ -z "$SKILL_SLUG" ] || [ "$SKILL_SLUG" = "unknown-task" ]; then
  SKILL_SLUG="auto-skill-$(date +%s)"
fi

# Avoid overwriting existing skills
SKILL_PATH="$SKILLS_DIR/$SKILL_SLUG"
if [ -d "$SKILL_PATH" ]; then
  # Append timestamp to make unique
  SKILL_SLUG="${SKILL_SLUG}-$(date +%s)"
  SKILL_PATH="$SKILLS_DIR/$SKILL_SLUG"
fi

# --- Generate SKILL.md ---

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATESTAMP=$(date -u +"%Y-%m-%d")

mkdir -p "$SKILL_PATH"

# Extract key steps from the result summary (lines that look like actions taken)
STEPS=$(echo "$RESULT_SUMMARY" | grep -E '^\s*[-*]|^\s*[0-9]+\.' | head -15)
if [ -z "$STEPS" ]; then
  # Fallback: extract sentences that describe actions
  STEPS=$(echo "$RESULT_SUMMARY" | grep -Ei "(created|updated|fixed|added|configured|implemented|modified|refactored|tested|verified)" | head -10)
fi
if [ -z "$STEPS" ]; then
  STEPS="- Review the task description and result summary below for the procedure"
fi

# Extract a short name from the slug
SKILL_NAME=$(echo "$SKILL_SLUG" | sed 's/-/ /g' | head -c 80)

# Escape task description for YAML (replace quotes, newlines)
TASK_DESC_ESCAPED=$(echo "$TASK_DESCRIPTION" | head -c 200 | tr '\n' ' ' | sed 's/"/\\"/g')

cat > "$SKILL_PATH/SKILL.md" << SKILLEOF
---
name: ${SKILL_SLUG}
description: Auto-generated skill from a complex agent task. Review and refine before relying on it.
auto-generated: true
generated-from: "${TASK_DESC_ESCAPED}"
generated-at: ${TIMESTAMP}
version: 0.1.0
last-updated: ${DATESTAMP}
---

# ${SKILL_NAME}

## Overview

This skill was auto-generated from a successful complex agent task.
It captures the procedure so it can be reused in future similar tasks.

**Original task**: ${TASK_DESCRIPTION}

## When to Use

Use this skill when you encounter a similar task to the one described above.

## Procedure

${STEPS}

## Result Summary

${RESULT_SUMMARY}

## Notes

- This skill was auto-generated and may need refinement
- Run \`/optimize-skill ${SKILL_SLUG}\` to improve it based on usage feedback
- If this skill is not useful, delete the directory: \`.cognitive-os/skills/auto-generated/${SKILL_SLUG}/\`
SKILLEOF

# --- Log the generation ---

TASK_SHORT=$(echo "$TASK_DESCRIPTION" | head -c 100 | tr '\n' ' ' | sed 's/"/\\"/g')
echo "{\"timestamp\":\"$TIMESTAMP\",\"skill_slug\":\"$SKILL_SLUG\",\"task_description\":\"$TASK_SHORT\"}" >> "$LOG_FILE" 2>/dev/null || true

# --- Output message for the agent to see ---

echo "Auto-generated skill: .cognitive-os/skills/auto-generated/${SKILL_SLUG}/SKILL.md"
echo "Review and refine with /optimize-skill ${SKILL_SLUG}"

exit 0
