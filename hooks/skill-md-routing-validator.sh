#!/usr/bin/env bash
# SCOPE: os-only
# PreToolUse Write hook: SKILL.md Routing Pattern Validator
#
# When a Write tool call targets a SKILL.md file, checks whether the new
# content includes a `routing_patterns:` frontmatter block.
# Emits a NON-BLOCKING warning (exit 0) if the block is absent, linking to
# ADR-174 for migration guidance.
#
# Event:    PreToolUse Write
# Type:     command
# Async:    true  (NEVER blocks writes)
# Exit:     always 0 (non-blocking — this hook is advisory only)
# Latency:  <100ms (pure bash, no Python subprocess)
#
# Killswitch: DISABLE_HOOK_SKILL_MD_ROUTING_VALIDATOR=1
#
# Registered in: scripts/_lib/settings-driver-claude-code.sh PreToolUse Write
# Allowlist:     hooks/_lib/registration-allowlist.txt

set -euo pipefail

# ── Killswitch ───────────────────────────────────────────────────────────────
if [[ "${DISABLE_HOOK_SKILL_MD_ROUTING_VALIDATOR:-0}" == "1" ]]; then
  exit 0
fi

# ── Read hook input from stdin ────────────────────────────────────────────────
INPUT="$(cat)"

# Fast path for non-file-writing tool calls. Avoid jq startup for the common
# Bash/Read/Grep cases exercised on every hook performance lane.
case "$INPUT" in
  *'"file_path"'*) ;;
  *) exit 0 ;;
esac

# Extract the file_path from the tool input JSON.
FILE_PATH=""
if command -v jq &>/dev/null; then
  FILE_PATH="$(echo "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || true)"
else
  FILE_PATH="$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*: *"//' | sed 's/"//' | head -1 || true)"
fi

# ── Only care about SKILL.md files ───────────────────────────────────────────
if [[ -z "$FILE_PATH" ]] || [[ "$(basename "$FILE_PATH")" != "SKILL.md" ]]; then
  exit 0
fi

# ── Extract new content being written ────────────────────────────────────────
NEW_CONTENT=""
if command -v jq &>/dev/null; then
  NEW_CONTENT="$(echo "$INPUT" | jq -r '.tool_input.content // ""' 2>/dev/null || true)"
fi

if [[ -z "$NEW_CONTENT" ]]; then
  exit 0
fi

# ── Check for routing_patterns: in frontmatter ───────────────────────────────
if echo "$NEW_CONTENT" | grep -q "routing_patterns:"; then
  exit 0
fi

# Only warn for files with YAML frontmatter
if ! echo "$NEW_CONTENT" | grep -q "^---"; then
  exit 0
fi

# ── Emit non-blocking warning ─────────────────────────────────────────────────
SKILL_NAME="$(basename "$(dirname "$FILE_PATH")")"

cat >&2 <<WARNING

[skill-md-routing-validator] ADVISORY -- ${FILE_PATH}

Skill '${SKILL_NAME}' is being written without a routing_patterns: frontmatter block.
Skills without routing patterns are invisible to the orchestrator skill suggestion
system and will not be suggested when users describe matching tasks (ADR-174).

To add routing patterns, include in frontmatter:

  routing_patterns:
    - pattern: "\\b${SKILL_NAME}\\b"
      confidence: 0.95
    - pattern: "YOUR_INTENT_PATTERN"
      confidence: 0.80

See: docs/02-Decisions/adrs/ADR-174-auto-derived-primitive-routing.md

This warning is non-blocking. The write will proceed.
WARNING

# Always exit 0 — never block writes
exit 0
