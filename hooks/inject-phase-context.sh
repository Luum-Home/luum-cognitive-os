#!/usr/bin/env bash
# PreToolUse hook on Agent — injects phase context from cognitive-os.yaml into agent prompts.
# Universal hook: reads project type and phase from config, does NOT hardcode any
# project-specific architecture standards or constitutional gates.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
COGNITIVE_OS_DIR="$PROJECT_DIR/.cognitive-os"
COGNITIVE_OS_YAML="$COGNITIVE_OS_DIR/cognitive-os.yaml"

# Read input from stdin
INPUT=$(cat)

# Only process Agent tool calls
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
if [[ "$TOOL_NAME" != "Agent" && "$TOOL_NAME" != "task" && "$TOOL_NAME" != "delegate" ]]; then
  exit 0
fi

# --- Phase Context ---
PHASE="reconstruction"
if [[ -f "$COGNITIVE_OS_YAML" ]]; then
  PHASE=$(grep -E '^\s+phase:' "$COGNITIVE_OS_YAML" | head -1 | sed 's/.*phase:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]' || echo "reconstruction")
fi

# Build phase-specific rules (universal, not framework-specific)
case "$PHASE" in
  reconstruction)
    RULES="- Rewrite > patch. Do NOT preserve broken patterns.
- Follow project architecture standards strictly.
- Don't document as \"future work\" — DO IT NOW.
- Break backwards compatibility if needed.
- Architecture violations are BLOCKERS, not warnings.
- If something doesn't compile after rewriting, FIX IT in this session."
    ;;
  stabilization)
    RULES="- Follow project architecture standards strictly.
- Rewrite non-compliant code (don't just patch).
- Maintain backwards compatibility where possible.
- Architecture violations should be fixed or tracked as tasks."
    ;;
  production)
    RULES="- Do NOT break existing functionality.
- Use feature flags for all changes.
- Document risky changes as proposals, not implementations.
- Maintain backwards compatibility.
- Architecture violations are warnings — log but don't block."
    ;;
  maintenance)
    RULES="- Bug fixes and security patches ONLY.
- Minimal changes, maximum stability.
- Document improvements as future work.
- Do NOT refactor or restructure."
    ;;
  *)
    RULES="- Unknown phase ($PHASE). Default to conservative behavior."
    ;;
esac

# --- Project Type ---
PROJECT_TYPE="webapp"
PROJECT_NAME="my-project"
if [[ -f "$COGNITIVE_OS_YAML" ]]; then
  PROJECT_TYPE=$(grep -E '^\s+type:' "$COGNITIVE_OS_YAML" | head -1 | sed 's/.*type:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]' || echo "webapp")
  PROJECT_NAME=$(grep -E '^\s+name:' "$COGNITIVE_OS_YAML" | head -1 | sed 's/.*name:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]' || echo "my-project")
fi

# --- Squad Assignment (if applicable) ---
SQUAD_INFO=""
SQUADS_DIR="$COGNITIVE_OS_DIR/squads"
if [[ -d "$SQUADS_DIR" ]]; then
  ACTIVE_SQUAD=$(grep -E '^\s+active_squad:' "$COGNITIVE_OS_YAML" 2>/dev/null | head -1 | sed 's/.*active_squad:\s*//' | sed 's/\s*#.*//' | tr -d '[:space:]' || echo "")
  if [[ -n "$ACTIVE_SQUAD" && -f "$SQUADS_DIR/$ACTIVE_SQUAD.md" ]]; then
    SQUAD_INFO="ACTIVE SQUAD: $ACTIVE_SQUAD"
  fi
fi

# --- Load project-specific context from .claude/ if it exists ---
# Architecture standards and constitutional gates are project-specific
# and should be defined in {project}/.claude/rules/ not here.
PROJECT_CONTEXT=""
PROJECT_RULES_DIR="$PROJECT_DIR/.claude/rules"
if [[ -d "$PROJECT_RULES_DIR" ]]; then
  # Check for architecture rules
  if [[ -f "$PROJECT_RULES_DIR/architecture.md" ]]; then
    PROJECT_CONTEXT="${PROJECT_CONTEXT}\nSee .claude/rules/architecture.md for project architecture standards."
  fi
  # Check for constitutional gates
  if [[ -f "$PROJECT_RULES_DIR/constitutional-gates.md" ]]; then
    PROJECT_CONTEXT="${PROJECT_CONTEXT}\nSee .claude/rules/constitutional-gates.md for project constitutional gates."
  fi
fi

# --- Output all context ---
echo ""
echo "PROJECT: ${PROJECT_NAME} ($PROJECT_TYPE)"
echo "PHASE: $PHASE"
echo ""
echo "PHASE RULES:"
echo "$RULES"
if [[ -n "$PROJECT_CONTEXT" ]]; then
  echo ""
  echo -e "PROJECT CONTEXT:$PROJECT_CONTEXT"
fi
if [[ -n "$SQUAD_INFO" ]]; then
  echo ""
  echo "$SQUAD_INFO"
fi
echo ""
echo "REQUIRED: Include a Trust Report at the end of your response."
echo "Honestly assess: what you verified, what you're unsure about, what the human should check."
echo "Admitting uncertainty builds trust. Claiming perfection destroys it."
echo "See rules/trust-score.md for format and scoring."
echo ""

exit 0
