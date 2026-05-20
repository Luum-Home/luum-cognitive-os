#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: safety, file-ops, adr-003-mechanism-c-r2
# Destructive File Op Blocker — PreToolUse Bash
#
# Intercepts bash commands about to run and blocks destructive file-erasure
# patterns when the call originates from a sub-agent (agent context detected).
#
# Blocked in agent context (exit 2):
#   - rm -rf <path>  /  rm -fr  /  rm -Rf  (recursive removal)
#   - > <tracked-file>      (stdout-redirect truncation of a project file)
#   - truncate -s 0 <file>  (explicit zero-truncation)
#   - cp /dev/null <file>   (overwrite with empty)
#   - dd of=<file> (if=/dev/zero or empty if=)  (dd-based erasure)
#
# Allowed always:
#   - rm <single-file> that is NOT recursive (non-recursive rm)
#   - Operations on /tmp/*, $TMPDIR/*, $SESSION_DIR/* (safe zones)
#   - Any non-file-erasure bash command
#
# Agent context is detected when ANY of:
#   - CLAUDE_AGENT_ID is non-empty, OR
#   - COGNITIVE_OS_SESSION_ID is non-empty, OR
#   - ORCHESTRATOR_MODE == executor, OR
#   - parent process name matches claude|claude-code (best-effort)
#
# User/orchestrator context (none of the above): warn on stderr, allow.
#
# Logs every block and every allow-with-warning to:
#   .cognitive-os/metrics/rm-op-blocks.jsonl
#
# Reference: ADR-003 Mechanism C, R2 (forensic hardening 2026-04-20).

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
# killswitch_check.sh expanded to include destructive-rm-blocker.sh in critical whitelist.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="destructive-rm-blocker"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/primitive-intervention.sh"
source "$(dirname "$0")/_lib/agent-context.sh"
[ -f "$(dirname "$0")/_lib/governance-policy.sh" ] && source "$(dirname "$0")/_lib/governance-policy.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
BLOCKS_LOG="$PROJECT_DIR/.cognitive-os/metrics/rm-op-blocks.jsonl"

# Read stdin (best-effort)
INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

# Gate to Bash tool — other tools must not be blocked
TOOL_NAME=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Bash" ]; then
    exit 0
  fi
fi

# Extract the command — jq preferred, env fallback
COMMAND=""
if [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
  COMMAND="$CLAUDE_TOOL_INPUT"
elif [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
fi

# No command, nothing to do
if [ -z "$COMMAND" ]; then
  exit 0
fi
# ADR-234 policy-as-code migration: evaluate declarative destructive Bash
# policies first. Legacy parser below remains as a defense-in-depth fallback for
# richer erasure patterns not yet expressible in the small YAML evaluator.
if [ -x "$PROJECT_DIR/scripts/cos-policy-eval" ]; then
  POLICY_DECISION=$("$PROJECT_DIR/scripts/cos-policy-eval" --project-dir "$PROJECT_DIR" --tool Bash --command "$COMMAND" --json 2>/dev/null || true)
  if [ -n "$POLICY_DECISION" ] && command -v jq >/dev/null 2>&1; then
    POLICY_VERDICT=$(printf '%s' "$POLICY_DECISION" | jq -r '.decision // empty' 2>/dev/null || true)
    if [ "$POLICY_VERDICT" = "block" ] || [ "$POLICY_VERDICT" = "deny" ]; then
      echo "=== DESTRUCTIVE RM BLOCKER: BLOCKED BY POLICY-AS-CODE ===" >&2
      printf '%s\n' "$POLICY_DECISION" >&2
      exit 2
    fi
  fi
fi


# ── Safe-zone check ──────────────────────────────────────────────────────────
# Returns 0 (safe) if a path falls inside /tmp, $TMPDIR, or $SESSION_DIR.
_is_safe_zone() {
  local path="$1"
  local tmpdir_val="${TMPDIR:-/tmp}"
  local session_dir_val="${SESSION_DIR:-}"

  # Normalise: strip leading whitespace, quotes
  path="${path#"${path%%[![:space:]]*}"}"
  path="${path//\"/}"
  path="${path//\'/}"

  case "$path" in
    /tmp/*|/tmp) return 0 ;;
    "$tmpdir_val"/*|"$tmpdir_val") return 0 ;;
  esac
  if [ -n "$session_dir_val" ]; then
    case "$path" in
      "$session_dir_val"/*|"$session_dir_val") return 0 ;;
    esac
  fi
  return 1
}

# ── Pattern matching ─────────────────────────────────────────────────────────
# We parse each shell-separated segment of COMMAND and match against the
# blocked patterns below. A single match triggers the block / warn logic.

# Pattern 1: rm with recursive flag (any ordering of flags that include r/R)
# Matches: rm -rf, rm -fr, rm -Rf, rm -rRf, rm -r, rm -R, rm --recursive, etc.
# Does NOT match: rm -f (no recursion flag)
RM_RECURSIVE_PATTERN='^[[:space:]]*rm[[:space:]]+'
RM_RECURSIVE_FLAG_PATTERN='-[a-zA-Z]*[rR][a-zA-Z]*'

# Pattern 2: stdout redirect truncation: "> path" or "> 'path'" (not >> which is append)
# Heuristic: only block if the target file exists under the project dir
REDIRECT_TRUNC_PATTERN='^[[:space:]]*>[[:space:]]*[^>]'

# Pattern 3: truncate -s 0
TRUNCATE_ZERO_PATTERN='^[[:space:]]*truncate[[:space:]].*-s[[:space:]]*0'

# Pattern 4: cp /dev/null
CP_DEVNULL_PATTERN='^[[:space:]]*cp[[:space:]].*[[:space:]]/dev/null[[:space:]]'
# Also catch: cp /dev/null file (source is /dev/null)
CP_DEVNULL_SRC_PATTERN='^[[:space:]]*cp[[:space:]]+/dev/null[[:space:]]'

# Pattern 5: dd of=<file> with no if= or if=/dev/zero
DD_ERASE_PATTERN='^[[:space:]]*dd[[:space:]]'

# ── Per-segment analysis ─────────────────────────────────────────────────────

FIRST_HIT=""
HIT_TYPE=""

# Split on shell separators (&& || ; | and newlines)
while IFS= read -r segment; do
  [ -z "$segment" ] && continue
  trimmed="${segment#"${segment%%[![:space:]]*}"}"

  # --- rm recursive ---
  if echo "$trimmed" | grep -Eq "$RM_RECURSIVE_PATTERN"; then
    # Check for recursive flags
    # Extract the flags portion (everything between rm and first non-flag arg)
    flags_part=$(echo "$trimmed" | sed -n 's/^[[:space:]]*rm[[:space:]]\+\([[:space:]]*-[^ ]*[[:space:]]*\)*.*/\1/p' || true)
    if echo "$trimmed" | grep -oE -- '-[a-zA-Z]*' | grep -qE '[rR]'; then
      # Found recursive flag — check if target is in safe zone
      # Extract the path argument (last non-flag token, crude heuristic)
      target=$(echo "$trimmed" | awk '{for(i=NF;i>=1;i--) if($i!~/^-/) {print $i; break}}')
      if _is_safe_zone "$target"; then
        continue
      fi
      FIRST_HIT="$trimmed"
      HIT_TYPE="rm-recursive"
      break
    fi
    # Also catch: rm --recursive
    if echo "$trimmed" | grep -qE -- '--recursive'; then
      target=$(echo "$trimmed" | awk '{for(i=NF;i>=1;i--) if($i!~/^-/) {print $i; break}}')
      if _is_safe_zone "$target"; then
        continue
      fi
      FIRST_HIT="$trimmed"
      HIT_TYPE="rm-recursive"
      break
    fi
  fi

  # --- stdout redirect truncation ---
  if echo "$trimmed" | grep -Eq "$REDIRECT_TRUNC_PATTERN"; then
    # Extract the target path
    target=$(echo "$trimmed" | sed -n 's/^[[:space:]]*>[[:space:]]*//p' | awk '{print $1}' || true)
    if [ -n "$target" ] && ! _is_safe_zone "$target"; then
      # Only block if the file exists under project root (tracked-file heuristic)
      # Resolve relative paths against PROJECT_DIR
      case "$target" in
        /*) full_path="$target" ;;
        *)  full_path="$PROJECT_DIR/$target" ;;
      esac
      if [ -f "$full_path" ]; then
        FIRST_HIT="$trimmed"
        HIT_TYPE="redirect-truncate"
        break
      fi
    fi
  fi

  # --- truncate -s 0 ---
  if echo "$trimmed" | grep -Eq "$TRUNCATE_ZERO_PATTERN"; then
    target=$(echo "$trimmed" | awk '{print $NF}')
    if ! _is_safe_zone "$target"; then
      FIRST_HIT="$trimmed"
      HIT_TYPE="truncate-zero"
      break
    fi
  fi

  # --- cp /dev/null <file> ---
  if echo "$trimmed" | grep -Eq "$CP_DEVNULL_SRC_PATTERN"; then
    # cp /dev/null <target>
    target=$(echo "$trimmed" | awk '{print $NF}')
    if ! _is_safe_zone "$target"; then
      FIRST_HIT="$trimmed"
      HIT_TYPE="cp-devnull"
      break
    fi
  elif echo "$trimmed" | grep -Eq "$CP_DEVNULL_PATTERN"; then
    # cp <something> /dev/null (writing TO /dev/null is fine — it's a sink)
    # This pattern only matches "cp ... /dev/null target" which is unusual;
    # do a position check: /dev/null must be the SOURCE (first positional arg)
    src=$(echo "$trimmed" | awk '{
      for(i=1;i<=NF;i++) {
        if($i=="cp") { print $(i+1); break }
      }
    }')
    if [ "$src" = "/dev/null" ]; then
      target=$(echo "$trimmed" | awk '{print $NF}')
      if ! _is_safe_zone "$target"; then
        FIRST_HIT="$trimmed"
        HIT_TYPE="cp-devnull"
        break
      fi
    fi
  fi

  # --- dd of=<file> with blank/zero input ---
  if echo "$trimmed" | grep -Eq "$DD_ERASE_PATTERN"; then
    # Only block if: no if= argument, OR if=/dev/zero
    has_if_devzero=false
    has_no_if=true
    if echo "$trimmed" | grep -qE 'if='; then
      has_no_if=false
      if echo "$trimmed" | grep -qE 'if=/dev/zero'; then
        has_if_devzero=true
      fi
    fi
    if $has_no_if || $has_if_devzero; then
      # Extract of= target
      target=$(echo "$trimmed" | grep -oE 'of=[^ ]+' | sed 's/of=//' || true)
      if [ -n "$target" ] && ! _is_safe_zone "$target"; then
        FIRST_HIT="$trimmed"
        HIT_TYPE="dd-erase"
        break
      fi
    fi
  fi

done <<< "$(echo "$COMMAND" | tr '|&;' '\n')"

# No match → allow silently
if [ -z "$FIRST_HIT" ]; then
  exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ── Agent-context detection (R4 hardening) ───────────────────────────────────
# Consider "agent context" if ANY of the following is true:
#   1. CLAUDE_AGENT_ID is non-empty
#   2. COGNITIVE_OS_SESSION_ID is non-empty
#   3. ORCHESTRATOR_MODE == executor
#   4. Parent process name matches claude or claude-code (best-effort)
_is_agent_context() {
  cos_is_agent_context
}

AGENT_ID="${CLAUDE_AGENT_ID:-${COGNITIVE_OS_SESSION_ID:-}}"

# Escape command for JSON
esc_cmd=${COMMAND//\\/\\\\}
esc_cmd=${esc_cmd//\"/\\\"}
esc_cmd=$(echo "$esc_cmd" | head -c 500 | tr '\n\r' '  ')
esc_type=${HIT_TYPE//\"/\\\"}

_rm_emit_intervention() {
  primitive_intervention_emit \
    "destructive-rm-blocker" \
    "hooks/destructive-rm-blocker.sh" \
    "$1" \
    "destructive_file_op" \
    "${HIT_TYPE:-file-erasure}" \
    ".cognitive-os/metrics/rm-op-blocks.jsonl" \
    "Bash" 2>/dev/null || true
}

if _is_agent_context; then
  if type cos_governance_policy_allows_block >/dev/null 2>&1 && ! cos_governance_policy_allows_block destructive-file; then
    cos_governance_policy_advisory_message "destructive-rm-blocker" "destructive-file"
    _rm_emit_intervention "warn"
    exit 0
  fi
  # Agent context → BLOCK
  echo "" >&2
  echo "=== DESTRUCTIVE-RM-BLOCKER: BLOCKED ===" >&2
  echo "BLOCKED: destructive file-erasure op '$HIT_TYPE' requires explicit user approval." >&2
  echo "Use Edit tool to modify file contents, or escalate to the user." >&2
  if [ -n "${CLAUDE_AGENT_ID:-}" ]; then
    echo "Agent: ${CLAUDE_AGENT_ID}" >&2
  fi
  echo "Command: $COMMAND" >&2
  echo "Reference: ADR-003 R2 (hooks/destructive-rm-blocker.sh)" >&2
  echo "" >&2

  ENTRY=$(printf '{"timestamp":"%s","event":"blocked","agent_id":"%s","op":"%s","command":"%s"}' \
    "$TIMESTAMP" "$AGENT_ID" "$esc_type" "$esc_cmd")
  safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
  _rm_emit_intervention "block"

  exit 2
fi

# Orchestrator / user context → WARN but allow
echo "" >&2
echo "=== DESTRUCTIVE-RM-BLOCKER: WARN ===" >&2
echo "Destructive file op detected ('$HIT_TYPE'). Allowed because no agent context is active." >&2
echo "Command: $COMMAND" >&2
echo "" >&2

ENTRY=$(printf '{"timestamp":"%s","event":"warned","agent_id":"","op":"%s","command":"%s"}' \
  "$TIMESTAMP" "$esc_type" "$esc_cmd")
safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
_rm_emit_intervention "warn"

exit 0
