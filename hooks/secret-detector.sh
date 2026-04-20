#!/usr/bin/env bash
# SCOPE: cos
# Secret Detector — dual-mode hook (PreToolUse + PostToolUse).
#
# PreToolUse mode (Bash | Edit | Write):
#   Detects literal secret patterns in tool_input.command / .content / .new_string
#   and REDACTS them in place via hookSpecificOutput.updatedInput, allowing the
#   tool call to proceed (ADR-023). Falls back to a hard block (exit 2) only when
#   the redaction would render the command meaningless (e.g. the entire payload
#   is one secret).
#
# PostToolUse mode (Edit | Write):
#   Legacy behavior — scans the just-written file for env-var references that
#   have no matching definition in .env / .env.example / docker-compose / etc.
#   Emits stderr WARNING and logs to .cognitive-os/metrics/missing-secrets.jsonl.
#   Always exits 0 (advisory).
#
# Mode dispatch is driven by the hook_event_name field in stdin (Claude Code
# always provides it). Defaults to PostToolUse for backward compatibility when
# the field is absent.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="secret-detector"
_LIB_DIR="$(dirname "$0")/_lib"
[ -f "$_LIB_DIR/safe-jsonl.sh" ] && source "$_LIB_DIR/safe-jsonl.sh"
[ -f "$_LIB_DIR/cache.sh" ]      && source "$_LIB_DIR/cache.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
METRICS_FILE="$METRICS_DIR/missing-secrets.jsonl"
REDACTION_LOG="$METRICS_DIR/secret-redactions.jsonl"

# ─── Read stdin once ─────────────────────────────────────────────────────────
INPUT="$(cat 2>/dev/null || true)"

# Determine the hook event. Default to PostToolUse to preserve legacy behavior
# for any caller that still drives this hook via TOOL_INPUT env var.
HOOK_EVENT=""
TOOL_NAME=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  HOOK_EVENT="$(printf '%s' "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null || true)"
  TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)"
fi

# ─── Secret patterns (literal-credential detection) ─────────────────────────
# Each pattern is conservative — high-confidence prefixes/structure to minimize
# false positives. We pair them with a label for logging and a redaction token.
#
# AWS Access Key ID:    AKIA + 16 alphanumerics  (also ASIA for STS sessions)
# AWS Secret Access Key:  40-char base64-ish string assigned by AWS (we only
#                         catch it when it is paired with the literal key
#                         "aws_secret_access_key" or similar context).
# GitHub PAT:           ghp_, gho_, ghu_, ghs_, ghr_ + 36+ chars
# Slack token:          xox[abp]-...
# Stripe live key:      sk_live_ + 24+ chars
# Generic bearer:       eyJ...JWT-shaped strings 100+ chars (kept loose; only
#                       redacted when present alongside Authorization headers)
SECRET_PATTERNS=(
  "(AKIA|ASIA)[0-9A-Z]{16}"
  "ghp_[A-Za-z0-9]{36,}"
  "gho_[A-Za-z0-9]{36,}"
  "ghu_[A-Za-z0-9]{36,}"
  "ghs_[A-Za-z0-9]{36,}"
  "ghr_[A-Za-z0-9]{36,}"
  "xox[abprs]-[A-Za-z0-9-]{10,}"
  "sk_live_[A-Za-z0-9]{20,}"
  "sk-[A-Za-z0-9]{32,}"
)

# Redact every match in $1 against every pattern, printing the redacted text
# on stdout and the comma-joined list of detected secrets on fd 3.
# Sets the variable REDACTION_COUNT in the caller via subshell capture.
redact_text() {
  local text="$1"
  local pattern label match
  local hits=()
  for pattern in "${SECRET_PATTERNS[@]}"; do
    # Find every literal match for logging (truncated to first 8 chars).
    while IFS= read -r match; do
      [ -z "$match" ] && continue
      hits+=("${match:0:8}…")
    done < <(printf '%s' "$text" | grep -oE "$pattern" 2>/dev/null || true)
    # Replace via sed with extended regex.
    text="$(printf '%s' "$text" | sed -E "s#${pattern}#[REDACTED]#g")"
  done
  printf '%s' "$text"
  # Emit hit list on a sentinel line for the caller to parse.
  printf '\n__SECRET_HITS__%s\n' "$(IFS=,; echo "${hits[*]}")" >&2
}

# ─── PreToolUse mode: redact-and-allow ──────────────────────────────────────
pre_tool_use_redact() {
  # Require jq for safe JSON manipulation.
  command -v jq >/dev/null 2>&1 || exit 0

  case "$TOOL_NAME" in
    Bash|Edit|Write|MultiEdit) ;;
    *) exit 0 ;;
  esac

  # Pull every plausible secret-bearing field from the tool_input payload.
  local original_input
  original_input="$(printf '%s' "$INPUT" | jq -c '.tool_input // {}' 2>/dev/null || echo '{}')"
  [ "$original_input" = "{}" ] && exit 0

  # Concatenate the candidate fields so we can decide once whether to redact.
  local concat
  concat="$(printf '%s' "$original_input" | jq -r '
    [ .command, .content, .new_string, .file_path ]
    | map(select(. != null))
    | join("\n")
  ' 2>/dev/null || true)"
  [ -z "$concat" ] && exit 0

  # Quick pre-check — bail without doing JSON gymnastics if no pattern matches.
  local matched=0
  for pattern in "${SECRET_PATTERNS[@]}"; do
    if printf '%s' "$concat" | grep -qE "$pattern" 2>/dev/null; then
      matched=1
      break
    fi
  done
  [ "$matched" -eq 0 ] && exit 0

  # Build the redacted tool_input by transforming each candidate field.
  local updated_input hits_csv hits_dedup
  hits_csv=""
  updated_input="$original_input"
  for field in command content new_string; do
    local field_val
    field_val="$(printf '%s' "$updated_input" | jq -r --arg f "$field" '.[$f] // empty' 2>/dev/null || true)"
    [ -z "$field_val" ] && continue

    local redacted hit_line
    {
      redacted="$(redact_text "$field_val" 2>/tmp/.secret_hits_$$)"
    } || true
    hit_line="$(grep '^__SECRET_HITS__' /tmp/.secret_hits_$$ 2>/dev/null | tail -1 | sed 's/^__SECRET_HITS__//')"
    rm -f /tmp/.secret_hits_$$

    if [ -n "$hit_line" ]; then
      hits_csv="${hits_csv}${hits_csv:+,}${hit_line}"
    fi

    # Only update the JSON if the field actually changed.
    if [ "$redacted" != "$field_val" ]; then
      updated_input="$(printf '%s' "$updated_input" | jq -c --arg f "$field" --arg v "$redacted" '.[$f] = $v' 2>/dev/null || echo "$updated_input")"
    fi
  done

  # Deduplicate hit prefixes for the operator-facing message.
  hits_dedup="$(printf '%s' "$hits_csv" | tr ',' '\n' | awk 'NF' | sort -u | paste -sd, -)"
  [ -z "$hits_dedup" ] && exit 0

  # Fallback: if redaction left the command meaningless (only "[REDACTED]" and
  # whitespace), block instead of letting Claude run a stripped-down command.
  local visible_after
  visible_after="$(printf '%s' "$updated_input" | jq -r '
    [ .command, .content, .new_string ]
    | map(select(. != null))
    | join("\n")
  ' 2>/dev/null | sed -E 's/\[REDACTED\]//g; s/[[:space:]]+//g')"

  if [ -z "$visible_after" ]; then
    # Block — there is nothing meaningful left to execute.
    echo "BLOCKED: tool input consisted entirely of secrets (${hits_dedup})." >&2
    echo "Refactor the call to read the secret from \$ENV or a config file instead." >&2
    exit 2
  fi

  # Log the redaction for auditability.
  if command -v safe_jsonl_append >/dev/null 2>&1; then
    mkdir -p "$METRICS_DIR" 2>/dev/null
    local ts
    ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    local entry
    entry="$(jq -c -n \
      --arg ts "$ts" \
      --arg tool "$TOOL_NAME" \
      --arg secrets "$hits_dedup" \
      '{timestamp: $ts, tool: $tool, secrets: $secrets, action: "redacted"}')"
    safe_jsonl_append "$REDACTION_LOG" "$entry" 2>/dev/null || true
  fi

  # Emit the hookSpecificOutput payload Claude Code understands.
  local additional_context
  additional_context="Secrets redacted before execution: ${hits_dedup}. Replace literal credentials with environment variables (e.g. \$AWS_ACCESS_KEY_ID, \$GITHUB_TOKEN) so they are not echoed into shell history or written to disk."

  jq -c -n \
    --argjson updated "$updated_input" \
    --arg ctx "$additional_context" \
    '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "allow",
        updatedInput: $updated
      },
      additionalContext: $ctx
    }'

  exit 0
}

# ─── PostToolUse mode: legacy env-var hygiene scan ──────────────────────────
post_tool_use_envvar_scan() {
  # The legacy code path read TOOL_INPUT from env. Preserve that contract first
  # (so older entries in settings.json keep working), then fall back to stdin
  # for callers that pass the modern JSON payload.
  local TI="${TOOL_INPUT:-}"
  if [ -z "$TI" ] && [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
    TI="$(printf '%s' "$INPUT" | jq -c '.tool_input // empty' 2>/dev/null || true)"
  fi
  [ -z "$TI" ] && exit 0

  local FILE_PATH
  FILE_PATH="$(echo "$TI" | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"$//' 2>/dev/null || true)"
  [ -z "$FILE_PATH" ] && exit 0

  case "$FILE_PATH" in
    *.md|*.json|*.yaml|*.yml|*.lock|*.sum|*.sh) exit 0 ;;
    */.cognitive-os/*|*/.claude/*) exit 0 ;;
  esac

  # SHA-256 cache: skip files that haven't changed since last scan.
  local _SD_RULES_HASH
  _SD_RULES_HASH=$(shasum -a 256 "$PROJECT_DIR/.gitignore" 2>/dev/null | cut -d' ' -f1 || echo "none")
  if command -v cache_hit >/dev/null 2>&1 && cache_hit "$FILE_PATH" "$_SD_RULES_HASH"; then
    exit 0
  fi

  local ENV_VARS=()
  if [ -f "$FILE_PATH" ]; then
    while IFS= read -r var; do
      ENV_VARS+=("$var")
    done < <(grep -oE 'process\.env\.([A-Z_][A-Z0-9_]*)' "$FILE_PATH" 2>/dev/null | sed 's/process\.env\.//' | sort -u || true)
    while IFS= read -r var; do
      ENV_VARS+=("$var")
    done < <(grep -oE 'os\.Getenv\("([A-Z_][A-Z0-9_]*)"\)' "$FILE_PATH" 2>/dev/null | sed 's/os\.Getenv("//;s/")//' | sort -u || true)
    while IFS= read -r var; do
      ENV_VARS+=("$var")
    done < <(grep -oE 'System\.getenv\("([A-Z_][A-Z0-9_]*)"\)' "$FILE_PATH" 2>/dev/null | sed 's/System\.getenv("//;s/")//' | sort -u || true)
    while IFS= read -r var; do
      ENV_VARS+=("$var")
    done < <(grep -oE '\$\{([A-Z_][A-Z0-9_]*)' "$FILE_PATH" 2>/dev/null | sed 's/\${//' | sort -u || true)
  fi

  [ ${#ENV_VARS[@]} -eq 0 ] && exit 0

  local MISSING=()
  for VAR in "${ENV_VARS[@]}"; do
    local FOUND=false
    grep -rq "^${VAR}=" "$PROJECT_DIR"/.env* 2>/dev/null && FOUND=true
    [ "$FOUND" = false ] && [ -f "$PROJECT_DIR/.env.example" ] && grep -q "^${VAR}=" "$PROJECT_DIR/.env.example" 2>/dev/null && FOUND=true
    [ "$FOUND" = false ] && grep -rq "${VAR}" "$PROJECT_DIR"/docker-compose*.yml 2>/dev/null && FOUND=true
    [ "$FOUND" = false ] && grep -rq "\"${VAR}\"" "$PROJECT_DIR"/**/config*.go 2>/dev/null && FOUND=true
    [ "$FOUND" = false ] && [ -f "$PROJECT_DIR/dev.env" ] && grep -q "^${VAR}=" "$PROJECT_DIR/dev.env" 2>/dev/null && FOUND=true
    [ "$FOUND" = false ] && MISSING+=("$VAR")
  done

  if [ ${#MISSING[@]} -gt 0 ]; then
    mkdir -p "$METRICS_DIR" 2>/dev/null
    local TIMESTAMP
    TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    for VAR in "${MISSING[@]}"; do
      local ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"file\":\"$FILE_PATH\",\"var\":\"$VAR\",\"status\":\"missing\"}"
      if command -v safe_jsonl_append >/dev/null 2>&1; then
        safe_jsonl_append "$METRICS_FILE" "$ENTRY" 2>/dev/null || true
      fi
    done

    echo "WARNING: Missing env var definitions: ${MISSING[*]}"
    echo "These env vars are referenced in $FILE_PATH but not defined in .env, .env.example, docker-compose, or config files."
    echo "Add them to .env.example to maintain the secret hygiene contract."
  fi

  if command -v cache_update >/dev/null 2>&1; then
    cache_update "$FILE_PATH" "$_SD_RULES_HASH"
  fi

  exit 0
}

# ─── Dispatch ───────────────────────────────────────────────────────────────
case "$HOOK_EVENT" in
  PreToolUse)  pre_tool_use_redact ;;
  PostToolUse) post_tool_use_envvar_scan ;;
  "")          # Legacy callers (no hook_event_name on stdin).
               post_tool_use_envvar_scan ;;
  *)           exit 0 ;;
esac
