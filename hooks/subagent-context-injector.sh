#!/usr/bin/env bash
# SCOPE: both
# SubagentStart hook: Inject agent preamble + engram sidecar context into every subagent.
#
# Event: SubagentStart
# Type: command
# Async: false (must complete before subagent starts)
# Exit: always 0 (never blocks subagent launch)
# Output: JSON with additionalContext field
#
# This hook replaces the need for the orchestrator to manually compose
# agent preambles. All subagents get a consistent preamble + sidecar.

set -euo pipefail

source "$(dirname "$0")/_lib/common.sh"

# Skip in private mode
check_private_mode

# Read stdin JSON (subagent details)
read_stdin_json

# ─── Load preamble template ─────────────────────────────────────────────────

PREAMBLE_FILE="$_PROJECT_DIR/templates/agent-preamble.md"
preamble=""

if [ -f "$PREAMBLE_FILE" ]; then
  preamble=$(cat "$PREAMBLE_FILE")

  # Interpolate {{phase}} placeholder
  phase=$(get_phase "reconstruction")
  preamble="${preamble//\{\{phase\}\}/$phase}"
fi

# ─── Extract agent name/type for sidecar lookup ─────────────────────────────

# Try to extract agent name from the subagent prompt (first line or known patterns)
agent_prompt=$(echo "$_STDIN_JSON" | jq -r '.prompt // .message // .description // empty' 2>/dev/null | head -1)
agent_name=""

# Look for patterns like "SKILL: Load skills/xxx/SKILL.md" or "Identity: agent-name"
if [ -n "$agent_prompt" ]; then
  # Match "Identity: agent-name" pattern
  agent_name=$(echo "$agent_prompt" | grep -oP 'Identity:\s*(\S+)' 2>/dev/null | head -1 | sed 's/Identity:\s*//' || true)

  # Match skill invocation patterns
  if [ -z "$agent_name" ]; then
    agent_name=$(echo "$agent_prompt" | grep -oP 'skills/([^/]+)/' 2>/dev/null | head -1 | sed 's|skills/||;s|/||' || true)
  fi

  # Match sdd phase names
  if [ -z "$agent_name" ]; then
    agent_name=$(echo "$agent_prompt" | grep -oP 'sdd-(explore|propose|spec|design|tasks|apply|verify|archive|improve)' 2>/dev/null | head -1 || true)
  fi
fi

# ─── Search engram for sidecar context ───────────────────────────────────────

sidecar=""

if [ -n "$agent_name" ] && command -v python3 >/dev/null 2>&1; then
  # Best-effort sidecar lookup with 2s timeout
  sidecar=$(timeout 2 python3 -c "
import sys, json
sys.path.insert(0, '$_PROJECT_DIR')
try:
    # Use engram MCP tools if available via subprocess
    import subprocess
    # Search engram for agent sidecar
    result = subprocess.run(
        ['python3', '-c', '''
import sys
sys.path.insert(0, \"$_PROJECT_DIR\")
try:
    from lib.engram_client import search_observations
    results = search_observations(\"agent/$agent_name/sidecar\", limit=1)
    if results:
        print(results[0].get(\"content\", \"\"))
except Exception:
    pass
'''],
        capture_output=True, text=True, timeout=2
    )
    if result.returncode == 0 and result.stdout.strip():
        print(result.stdout.strip())
except Exception:
    pass
" 2>/dev/null || true)
fi

# ─── Load mandatory project rules ──────────────────────────────────────────

RULES_FILE="$_PROJECT_DIR/templates/agent-mandatory-rules.md"
mandatory_rules=""

if [ -f "$RULES_FILE" ]; then
  mandatory_rules=$(cat "$RULES_FILE")
else
  # Inline fallback: critical rules that every sub-agent MUST follow
  mandatory_rules="## MANDATORY PROJECT RULES (injected by subagent-context-injector)

### Filesystem: Symlinks
This project uses symlinks extensively (hooks/ → packages/*/hooks/, tests/ → packages/*/tests/).
- ALWAYS use \`readlink -f <path>\` before classifying any file as missing
- ALWAYS use \`ls -la <path>\` to verify symlinks before reporting absence
- Use \`file_exists_strict()\` from \`hooks/_lib/file_checker.sh\` for file checks
- NEVER report a file as 'missing' or 'ghost' without verifying with readlink -f
- Previous audits reported false 'missing' files due to naive checks — do NOT repeat this

### Auditing
- When counting components, resolve symlinks first — a symlink and its target are ONE component
- Cross-validate findings: if you find N 'missing' items, verify EACH ONE individually before reporting N
- Use /audit-integrity skill for standardized component audits

### Code Quality
- Do NOT create tests that only verify file existence — tests MUST execute code and verify behavior
- Do NOT add metadata fields to files unless code exists to consume them
- Save important discoveries to engram via mem_save before returning"
fi

# ─── Compose additionalContext ───────────────────────────────────────────────

context=""

# Mandatory rules always go first
if [ -n "$mandatory_rules" ]; then
  context="$mandatory_rules"
fi

if [ -n "$preamble" ]; then
  if [ -n "$context" ]; then
    context="${context}

---
${preamble}"
  else
    context="$preamble"
  fi
fi

if [ -n "$sidecar" ]; then
  if [ -n "$context" ]; then
    context="${context}

---
## Sidecar Context (from previous sessions)
${sidecar}"
  else
    context="## Sidecar Context (from previous sessions)
${sidecar}"
  fi
fi

# ─── Truncate to 10K char limit ──────────────────────────────────────────────
# additionalContext has a hard cap of 10,000 chars per Claude Code spec.
MAX_CONTEXT_CHARS=10000
if [ -n "$context" ]; then
  context_len=${#context}
  if [ "$context_len" -gt "$MAX_CONTEXT_CHARS" ]; then
    if command -v python3 >/dev/null 2>&1; then
      # Use printf (no trailing newline) so truncation math stays exact
      context=$(printf '%s' "$context" | python3 -c "
import sys
buf = sys.stdin.read()
limit = ${MAX_CONTEXT_CHARS}
if len(buf) > limit:
    marker = '\n[truncated at 10K chars]'
    sys.stdout.write(buf[: limit - len(marker)] + marker)
else:
    sys.stdout.write(buf)
")
    else
      context="${context:0:9975}
[truncated at 10K chars]"
    fi
  fi
fi

# ─── Output JSON with hookSpecificOutput.additionalContext ───────────────────
# Detect Claude Code invocation by presence of stdin JSON object.
# Falls back to stderr when invoked manually (testing without Claude Code).
HAS_VALID_INPUT=0
if [ -n "$_STDIN_JSON" ] && echo "$_STDIN_JSON" | jq -e 'type == "object"' >/dev/null 2>&1; then
  HAS_VALID_INPUT=1
fi

if [ -n "$context" ]; then
  if [ "$HAS_VALID_INPUT" -eq 1 ]; then
    # Claude Code: emit hookSpecificOutput JSON on stdout
    if command -v python3 >/dev/null 2>&1; then
      printf '%s' "$context" | python3 -c "
import json, sys
ctx = sys.stdin.read()
out = {
    'hookSpecificOutput': {
        'hookEventName': 'SubagentStart',
        'additionalContext': ctx,
        'permissionDecision': 'allow',
    }
}
sys.stdout.write(json.dumps(out))
"
    else
      jq -n \
        --arg ctx "$context" \
        '{hookSpecificOutput: {hookEventName: "SubagentStart", additionalContext: $ctx, permissionDecision: "allow"}}'
    fi
  else
    # No valid Claude Code input — degrade to stderr for manual/test invocations
    echo "$context" >&2
  fi
fi

exit 0
