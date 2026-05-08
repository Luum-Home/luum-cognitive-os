#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: safety, hallucination, verification
# Claim Validator — verifies agent claims against filesystem reality
# PostToolUse hook on Agent
# Detects file-related claims (created/modified/wrote) and verifies they exist.
# Detects test count claims and enforces structured verification evidence.
# Logs hallucinations to metrics/hallucinations.jsonl.
# File hallucination checks remain phase-aware; ADR-244 high-stakes verification blocks independently.
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="claim-validator"

# Source safe-jsonl helper if available
_LIB_DIR="$(dirname "$0")/_lib"
[ -f "$_LIB_DIR/safe-jsonl.sh" ] && source "$_LIB_DIR/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"


# Auto-disabled at capability level 5
check_capability_level "claim-validator"
# Runtime disable: DISABLE_HOOK_CLAIM_VALIDATOR=true skips this hook for the session
check_disabled_env "claim-validator"

# Fallback if safe_jsonl_append is not defined
if ! type safe_jsonl_append &>/dev/null 2>&1; then
  safe_jsonl_append() {
    local file="$1" data="$2"
    mkdir -p "$(dirname "$file")" 2>/dev/null
    echo "$data" >> "$file"
  }
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
CONFIG_FILE="$PROJECT_DIR/.cognitive-os/cognitive-os.yaml"
[ ! -f "$CONFIG_FILE" ] && CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"

# Read input from stdin
INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

# Only process if jq is available
command -v jq &>/dev/null || exit 0

# Only run on Agent completions
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)
[ "$TOOL_NAME" != "Agent" ] && exit 0

RESPONSE=$(echo "$INPUT" | jq -r '.tool_response // ""' 2>/dev/null)
if [ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ]; then
  RESPONSE=$(echo "$INPUT" | jq -r '.tool_response.result // .tool_response.output // .tool_response.content // ""' 2>/dev/null)
fi
[ -z "$RESPONSE" ] || [ "$RESPONSE" = "null" ] && exit 0

# Determine metrics directory (session-scoped if available)
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-}"
if [ -z "$SESSION_ID" ]; then
  _SESSION_FILE="$PROJECT_DIR/.cognitive-os/sessions/.current-session-$$"
  [ -f "$_SESSION_FILE" ] && SESSION_ID=$(cat "$_SESSION_FILE" 2>/dev/null)
fi
if [ -n "$SESSION_ID" ]; then
  SESSION_METRICS="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID/metrics"
  [ -d "$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID" ] && METRICS_DIR="$SESSION_METRICS"
fi
mkdir -p "$METRICS_DIR" 2>/dev/null

# ADR-244: high-stakes Trust Report claims require a structured verification: field.
# Passing shell verification allows completion; failing verification blocks and
# emits downgraded_status=partial in the JSON audit trail.
if command -v python3 >/dev/null 2>&1; then
  RESPONSE_TMP=$(mktemp 2>/dev/null || printf '/tmp/cos-claim-enforcer-response-%s' "$$")
  printf '%s' "$RESPONSE" > "$RESPONSE_TMP" 2>/dev/null || true
  ENFORCER_OUT=$(python3 "$PROJECT_DIR/scripts/claim_enforcer.py" --project-dir "$PROJECT_DIR" --response-file "$RESPONSE_TMP" --metrics --json 2>/dev/null || true)
  ENFORCER_OK=$(printf '%s' "$ENFORCER_OUT" | jq -r '.ok // true' 2>/dev/null || printf 'true')
  ENFORCER_STATUS=$(printf '%s' "$ENFORCER_OUT" | jq -r '.status // "noop"' 2>/dev/null || printf 'noop')
  rm -f "$RESPONSE_TMP" 2>/dev/null || true
  if [ "$ENFORCER_OK" = "false" ]; then
    echo "" >&2
    echo "=== ADR-244 CLAIM ENFORCER: BLOCK ($ENFORCER_STATUS) ===" >&2
    printf '%s' "$ENFORCER_OUT" | jq -r '.findings[]? | "- [" + .severity + "] " + .code + ": " + .message' >&2 2>/dev/null || true
    echo "High-stakes completed/test claims must provide verification: <command> that exits 0, or verification: manual for non-shell evidence." >&2
    echo "=== END ADR-244 CLAIM ENFORCER ===" >&2
    exit 2
  fi
fi

# ADR-108: require durable approval evidence for extracted high-stakes claims.
# In reconstruction/stabilization this is advisory; in production/maintenance it blocks.
PHASE="reconstruction"
if [ -f "$CONFIG_FILE" ]; then
  PARSED_PHASE=$(grep 'phase:' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*phase:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]')
  [ -n "$PARSED_PHASE" ] && PHASE="$PARSED_PHASE"
fi

APPROVAL_MISSING=0
APPROVAL_DETAILS=""
if command -v python3 >/dev/null 2>&1; then
  RESPONSE_TMP=$(mktemp 2>/dev/null || printf '/tmp/cos-claim-response-%s' "$$")
  printf '%s' "$RESPONSE" > "$RESPONSE_TMP" 2>/dev/null || true
  CLAIM_LINES=$(python3 - "$PROJECT_DIR" "$RESPONSE_TMP" <<'PYEOF' 2>/dev/null || true
import json, sys
project = sys.argv[1]
response_path = sys.argv[2]
sys.path.insert(0, project)
try:
    text = open(response_path, encoding="utf-8", errors="replace").read()
    from lib.orchestrator_verify import extract_high_stakes_claims
    for claim in extract_high_stakes_claims(text):
        print(json.dumps({"verb": claim.verb, "target": claim.target, "raw_text": claim.raw_text}, sort_keys=True))
except Exception:
    pass
PYEOF
)
  rm -f "$RESPONSE_TMP" 2>/dev/null || true
  if [ -n "$CLAIM_LINES" ]; then
    while IFS= read -r claim_json; do
      [ -z "$claim_json" ] && continue
      verb=$(printf '%s' "$claim_json" | jq -r '.verb // empty' 2>/dev/null)
      target=$(printf '%s' "$claim_json" | jq -r '.target // empty' 2>/dev/null)
      [ -z "$verb" ] || [ -z "$target" ] && continue
      APPROVAL_OUT=$(python3 "$PROJECT_DIR/scripts/approval_ledger.py" --project-dir "$PROJECT_DIR" \
        require --category "$verb" --scope "$target" 2>/dev/null || true)
      APPROVAL_STATUS=$(printf '%s' "$APPROVAL_OUT" | jq -r '.status // empty' 2>/dev/null || true)
      if [ "$APPROVAL_STATUS" = "missing" ]; then
        APPROVAL_MISSING=$((APPROVAL_MISSING + 1))
        APPROVAL_DETAILS="${APPROVAL_DETAILS}  - ${verb} ${target}\n"
      fi
    done <<< "$CLAIM_LINES"
  fi
fi

if [ "$APPROVAL_MISSING" -gt 0 ]; then
  echo "" >&2
  echo "=== ADR-108 APPROVAL LEDGER: $APPROVAL_MISSING missing approval(s) ===" >&2
  echo -e "$APPROVAL_DETAILS" >&2
  echo "Record approval with: python3 scripts/approval_ledger.py record --category <verb> --scope <target> --reason ..." >&2
  safe_jsonl_append "$METRICS_DIR/approval-ledger-missing.jsonl" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"missing\":$APPROVAL_MISSING}"
  if [ "$PHASE" = "production" ] || [ "$PHASE" = "maintenance" ]; then
    echo "Approval evidence required in $PHASE phase — blocking agent result." >&2
    exit 2
  fi
  echo "Phase is $PHASE — advisory path; production/maintenance block." >&2
  echo "=== END ADR-108 APPROVAL LEDGER ===" >&2
fi

# Extract file-related claims from response
# Patterns: "Created <path>", "Modified <path>", "Wrote <path>", "Updated <path>", "Edited <path>"
FILE_CLAIMS=$(echo "$RESPONSE" | grep -oiE '(created|modified|wrote|updated|edited|generated|added) ["`'"'"']?[a-zA-Z0-9_./-]+\.(go|py|ts|tsx|js|jsx|sh|md|yaml|yml|json|toml|html|css|sql|java|kt|rs|rb|c|cpp|h)["`'"'"']?' | sed 's/^[a-zA-Z]* //' | tr -d '`"'"'" | sort -u || true)

HALLUCINATIONS=0
VERIFIED=0
DETAILS=""

if [ -n "$FILE_CLAIMS" ]; then
  while IFS= read -r file; do
    [ -z "$file" ] && continue
    # Try relative to project dir first, then absolute
    if [ -f "$PROJECT_DIR/$file" ]; then
      VERIFIED=$((VERIFIED + 1))
    elif [ -f "$file" ]; then
      VERIFIED=$((VERIFIED + 1))
    else
      HALLUCINATIONS=$((HALLUCINATIONS + 1))
      DETAILS="${DETAILS}  - $file\n"
      echo "HALLUCINATION: Agent claims '$file' exists but it does NOT." >&2
    fi
  done <<< "$FILE_CLAIMS"
fi

# Check test count claims (ADR-244 enforcer handles structured verification)
TEST_CLAIM=$(echo "$RESPONSE" | grep -oiE '[0-9]+ tests? (pass|collect|succeed|ran)' | head -1 || true)
if [ -n "$TEST_CLAIM" ]; then
  CLAIMED_COUNT=$(echo "$TEST_CLAIM" | grep -oE '[0-9]+')
  echo "CLAIM: Agent says '$TEST_CLAIM' — ADR-244 expects verification: <command> in the Trust Report." >&2
fi

# Report results
if [ "$HALLUCINATIONS" -gt 0 ]; then
  echo "" >&2
  echo "=== CLAIM VALIDATOR: $HALLUCINATIONS hallucination(s) detected, $VERIFIED file(s) verified ===" >&2
  echo -e "Missing files:\n$DETAILS" >&2

  # Log to metrics
  AGENT_DESC=$(echo "$INPUT" | jq -r '.tool_input.prompt // .tool_input.description // "unknown"' 2>/dev/null | head -c 100)
  safe_jsonl_append "$METRICS_DIR/hallucinations.jsonl" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"hallucinations\":$HALLUCINATIONS,\"verified\":$VERIFIED,\"agent\":$(echo "$AGENT_DESC" | jq -Rs .)}"

  # Phase-aware response
  PHASE="reconstruction"
  if [ -f "$CONFIG_FILE" ]; then
    PARSED_PHASE=$(grep 'phase:' "$CONFIG_FILE" 2>/dev/null | head -1 | sed 's/.*phase:[[:space:]]*//' | sed 's/[[:space:]]*#.*//' | tr -d '[:space:]')
    [ -n "$PARSED_PHASE" ] && PHASE="$PARSED_PHASE"
  fi

  if [ "$PHASE" = "production" ] || [ "$PHASE" = "maintenance" ]; then
    echo "HALLUCINATION DETECTED in $PHASE phase — blocking agent result." >&2
    echo "=== END CLAIM VALIDATOR ===" >&2
    echo ""
    if type external_notify &>/dev/null 2>&1; then
      external_notify "Safety Mesh BLOCK: Hallucination" "Hook: claim-validator, Phase: $PHASE, Hallucinations: $HALLUCINATIONS" "warning"
    fi
    exit 2
  else
    echo "Phase is $PHASE — advisory path; production/maintenance block." >&2
    echo "=== END CLAIM VALIDATOR ===" >&2
    echo ""
  fi
elif [ "$VERIFIED" -gt 0 ]; then
  # Log successful verification too (for metrics)
  safe_jsonl_append "$METRICS_DIR/hallucinations.jsonl" "{\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"hallucinations\":0,\"verified\":$VERIFIED}"
fi

exit 0
