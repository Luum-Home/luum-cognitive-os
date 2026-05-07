#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: safety, agent-lifecycle, adr-003-mechanism-a, adr-099
# Pre-Agent Snapshot Hook — PreToolUse Agent
#
# Creates a working-tree snapshot before every Agent tool launch so that
# post-agent-verify.sh can restore out-of-scope writes without guessing.
#
# ORDERING INVARIANT (ADR-213): this hook must run after blocking Agent
# preflight hooks such as agent-prelaunch.sh. It mutates git stash; if a later
# preflight blocks and PostToolUse never fires, WIP can be hidden in stash.
#
# Snapshot strategy (ADR-099 — default):
#   1. Untracked files → copied to .cognitive-os/snapshots/<snapshot-id>/
#      They are NOT removed from the working tree.
#   2. Tracked-modified files → captured via `git stash push --keep-index`
#      WITHOUT --include-untracked.
#   3. Manifest written to .cognitive-os/snapshots/<snapshot-id>/manifest.json
#      correlating both halves for crash-recovery.sh.
#
# Legacy mode (COS_LEGACY_SNAPSHOT=1):
#   Uses original `git stash push --include-untracked --keep-index`.
#   Untracked files WILL disappear from the working tree (old behaviour).
#
# Writes metadata to:
#   .cognitive-os/sessions/<SESSION_ID>/agent-<AGENT_ID>-snapshot.json
#
# Appends event to:
#   .cognitive-os/metrics/agent-snapshots.jsonl
#
# Advisory only — always exits 0. Never blocks agent launch on snapshot failure.
#
# Reference: ADR-003 Mechanism A, ADR-099 Pre-agent snapshot copy-on-untracked.

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="pre-agent-snapshot"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
STASH_LOCK_LIB="$(dirname "$0")/_lib/stash-lock.sh"
[ -f "$STASH_LOCK_LIB" ] && source "$STASH_LOCK_LIB"

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_ROOT="$(cd "$HOOK_DIR/.." && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"

# Validation capsules must not mutate the operator worktree by taking git
# snapshots. dispatch-gate blocks Agent launch under the same lock; this is a
# second safety belt in case hook order or harness projection drifts.
VALIDATION_LOCK_LIB="$HOOK_DIR/_lib/validation-lock.sh"
if [ "${COS_SUPPRESS_AGENT_SNAPSHOT:-0}" = "1" ] || [ "${COS_VALIDATION_MODE:-0}" = "1" ]; then
  exit 0
fi
if [ -f "$VALIDATION_LOCK_LIB" ]; then
  # shellcheck source=/dev/null
  source "$VALIDATION_LOCK_LIB"
  if cos_validation_lock_active "$PROJECT_DIR"; then
    exit 0
  fi
fi

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-default-session}"
SESSIONS_DIR="$PROJECT_DIR/.cognitive-os/sessions/$SESSION_ID"
METRICS_LOG="$PROJECT_DIR/.cognitive-os/metrics/agent-snapshots.jsonl"
LEGACY_MODE="${COS_LEGACY_SNAPSHOT:-0}"

# Read stdin JSON (best-effort)
INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

# Only process Agent tool
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ]; then
    exit 0
  fi
fi

# Skip if not inside a git repo
if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

# Resolve agent ID. Prefer explicit harness IDs, then deterministic tool-use IDs.
# Random IDs make PostToolUse exact-match impossible when the harness does not
# echo CLAUDE_AGENT_ID back to post hooks; that is how pre-agent markers become
# orphaned after long-running agents. The payload hash fallback is intentionally
# derived only from tool_input so PostToolUse payloads that add tool_response still
# resolve to the same marker.
AGENT_ID="${CLAUDE_AGENT_ID:-}"
if [ -z "$AGENT_ID" ] && [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  AGENT_ID=$(echo "$INPUT" | jq -r '
    .tool_input.agent_id
    // .tool_use_id
    // .tool_input.tool_use_id
    // .tool_input.id
    // empty
  ' 2>/dev/null || true)
fi
if [ -z "$AGENT_ID" ] && [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_INPUT_CANONICAL=$(echo "$INPUT" | jq -cS '.tool_input // {}' 2>/dev/null || true)
  if [ -n "$TOOL_INPUT_CANONICAL" ]; then
    if command -v shasum >/dev/null 2>&1; then
      AGENT_ID="payload-$(printf '%s' "$TOOL_INPUT_CANONICAL" | shasum -a 256 | awk '{print substr($1,1,16)}')"
    elif command -v sha256sum >/dev/null 2>&1; then
      AGENT_ID="payload-$(printf '%s' "$TOOL_INPUT_CANONICAL" | sha256sum | awk '{print substr($1,1,16)}')"
    fi
  fi
fi
if [ -z "$AGENT_ID" ]; then
  if command -v uuidgen >/dev/null 2>&1; then
    AGENT_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
  else
    AGENT_ID="agent-$(date +%s)-$$-$RANDOM"
  fi
fi

# ADR-223 Slice A: write-capable agents launched in dedicated worktrees do not
# need an operator-worktree stash snapshot. The safety boundary is the linked
# worktree prepared by agent-prelaunch.sh. This prevents auto-pre-agent stashes
# from hiding operator WIP in the worktree lifecycle lane.
SUPPRESS_MARKER="$PROJECT_DIR/.cognitive-os/runtime/suppress-agent-snapshot-${AGENT_ID}.json"
if [ "${COS_AGENT_LIFECYCLE_MODE:-}" = "worktree" ] && [ -f "$SUPPRESS_MARKER" ]; then
  exit 0
fi

# Extract a short prompt summary (first 200 chars) for the metadata file
PROMPT_SUMMARY=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  PROMPT_SUMMARY=$(echo "$INPUT" | jq -r '
    (.tool_input.description // .tool_input.prompt // .tool_input.task // "")
  ' 2>/dev/null | head -c 200 | tr '\n\r' '  ' || true)
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$SESSIONS_DIR" 2>/dev/null || true
mkdir -p "$(dirname "$METRICS_LOG")" 2>/dev/null || true

SNAPSHOT_FILE="$SESSIONS_DIR/agent-${AGENT_ID}-snapshot.json"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
MARKER_FILE="$RUNTIME_DIR/pre-agent-snapshot-${AGENT_ID}.json"

# ─── Legacy mode ─────────────────────────────────────────────────────────────
if [ "$LEGACY_MODE" = "1" ]; then
  STASH_MSG="auto-pre-agent-${AGENT_ID}"
  STASH_REF=""
  STASH_SHA=""
  SNAPSHOT_STATUS="skipped"
  ERROR_MSG=""

  # Determine if working tree has changes
  STATUS_OUT=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null || true)
  FILTERED_STATUS=$(echo "$STATUS_OUT" | grep -v -E '(^\?\? |^.. )\.cognitive-os/' || true)
  TREE_DIRTY=false
  if [ -n "$FILTERED_STATUS" ]; then
    TREE_DIRTY=true
  fi

  if [ "$TREE_DIRTY" = true ]; then
    if command -v cos_stash_lock_acquire >/dev/null 2>&1; then
      cos_stash_lock_acquire "pre-agent-snapshot" || {
        SNAPSHOT_STATUS="stash_lock_failed"
        ERROR_MSG="could not acquire stash lock"
      }
      if [ -z "$ERROR_MSG" ]; then
        trap 'cos_stash_lock_release' EXIT INT TERM
      fi
    fi
  fi

  if [ "$TREE_DIRTY" = true ] && [ -z "$ERROR_MSG" ]; then
    if git -C "$PROJECT_DIR" stash push --include-untracked --keep-index \
          -m "$STASH_MSG" \
          -- ':(exclude).cognitive-os' ':(exclude).cognitive-os/**' '.' \
          >/dev/null 2>&1; then
      STASH_REF=$(git -C "$PROJECT_DIR" stash list --max-count=1 2>/dev/null | head -1 | cut -d: -f1 || true)
      STASH_SHA=$(git -C "$PROJECT_DIR" rev-parse --verify "stash@{0}" 2>/dev/null || true)
      if [ -n "$STASH_REF" ] && [ -n "$STASH_SHA" ]; then
        SNAPSHOT_STATUS="stashed_legacy"
        # ADR-116 P4.3: record stash provenance for auto-reapply on next SessionStart
        _PROV_FILES=$(git -C "$PROJECT_DIR" stash show --name-only "$STASH_REF" 2>/dev/null | tr '\n' '\n' || true)
        COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" python3 -m stash_provenance record \
          --stash-ref "$STASH_REF" \
          --session-id "$SESSION_ID" \
          --agent-id "$AGENT_ID" \
          --original-files "$_PROV_FILES" \
          --created-at "$TIMESTAMP" 2>/dev/null || true
      else
        SNAPSHOT_STATUS="stash_created_no_ref"
        ERROR_MSG="stash push succeeded but ref could not be read"
      fi
    else
      SNAPSHOT_STATUS="stash_failed"
      ERROR_MSG="git stash push returned non-zero"
    fi

    if command -v cos_stash_lock_release >/dev/null 2>&1; then
      cos_stash_lock_release
      trap - EXIT INT TERM
    fi
  else
    if [ -z "$ERROR_MSG" ]; then
      SNAPSHOT_STATUS="skip_clean"
    fi
  fi

  mkdir -p "$SESSIONS_DIR" 2>/dev/null || true

  {
    printf '{'
    printf '"timestamp":"%s",' "$TIMESTAMP"
    printf '"agent_id":"%s",' "$AGENT_ID"
    printf '"session_id":"%s",' "$SESSION_ID"
    printf '"mode":"legacy_stash",'
    printf '"stash_ref":"%s",' "${STASH_REF//\"/\\\"}"
    printf '"stash_sha":"%s",' "${STASH_SHA//\"/\\\"}"
    printf '"stash_message":"%s",' "$STASH_MSG"
    printf '"status":"%s",' "$SNAPSHOT_STATUS"
    printf '"tree_dirty":%s,' "$TREE_DIRTY"
    escaped_prompt=${PROMPT_SUMMARY//\\/\\\\}
    escaped_prompt=${escaped_prompt//\"/\\\"}
    printf '"prompt_summary":"%s"' "$escaped_prompt"
    if [ -n "$ERROR_MSG" ]; then
      printf ',"error":"%s"' "${ERROR_MSG//\"/\\\"}"
    fi
    printf '}\n'
  } > "$SNAPSHOT_FILE" 2>/dev/null || true

  METRICS_LINE=$(printf '{"timestamp":"%s","event":"agent_snapshot","agent_id":"%s","session_id":"%s","status":"%s","stash_ref":"%s","stash_sha":"%s","tree_dirty":%s,"mode":"legacy_stash"}' \
    "$TIMESTAMP" "$AGENT_ID" "$SESSION_ID" "$SNAPSHOT_STATUS" "${STASH_REF}" "${STASH_SHA}" "$TREE_DIRTY")
  safe_jsonl_append "$METRICS_LOG" "$METRICS_LINE" 2>/dev/null || true

  # Write runtime marker so post-agent-snapshot-restore.sh can find the exact stash
  if [ -n "$STASH_REF" ]; then
    mkdir -p "$RUNTIME_DIR" 2>/dev/null || true
    printf '{"schema_version":"pre-agent-snapshot/v2","stash_sha":"%s","stash_ref_at_capture":"%s","stash_ref":"%s","agent_id":"%s","session_id":"%s","timestamp":"%s","snapshot_id":"","mode":"legacy_stash"}\n' \
      "${STASH_SHA//\"/\\\"}" "${STASH_REF//\"/\\\"}" "${STASH_REF//\"/\\\"}" "$AGENT_ID" "$SESSION_ID" "$TIMESTAMP" \
      > "$MARKER_FILE" 2>/dev/null || true
  fi

  exit 0
fi

# ─── New copy-on-untracked mode (ADR-099) ───────────────────────────────────
SNAPSHOT_RESULT=""
SNAPSHOT_STATUS="skipped"
SNAPSHOT_ID=""
STASH_REF=""
STASH_SHA=""
TREE_DIRTY=false
UNTRACKED_COUNT=0
SKIPPED_UNTRACKED_COUNT=0

if command -v python3 >/dev/null 2>&1; then
  if command -v cos_stash_lock_acquire >/dev/null 2>&1; then
    cos_stash_lock_acquire "pre-agent-snapshot" || SNAPSHOT_RESULT='{"status":"stash_lock_failed","error":"could not acquire stash lock","snapshot_id":"","tracked_stash_ref":null,"untracked_files":[],"skipped_untracked_files":[]}'
    if [ -z "$SNAPSHOT_RESULT" ]; then
      trap 'cos_stash_lock_release' EXIT INT TERM
    fi
  fi

  if [ -z "$SNAPSHOT_RESULT" ]; then
  SNAPSHOT_RESULT=$(python3 - <<PYEOF 2>/dev/null
import sys, json
sys.path.insert(0, '$OS_ROOT')
try:
    from lib.snapshot_manager import create_snapshot
    from pathlib import Path

    def _read_snapshot_int(key, default):
        config = Path('$PROJECT_DIR') / 'cognitive-os.yaml'
        if not config.exists():
            return default
        in_snapshots = False
        for line in config.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith('snapshots:'):
                in_snapshots = True
                continue
            if not in_snapshots:
                continue
            if stripped and not line.startswith((' ', '\t')) and ':' in stripped:
                break
            if stripped.startswith(f'{key}:'):
                raw = stripped.split(':', 1)[1].split('#', 1)[0].strip()
                if raw in ('', 'null', 'none', 'unlimited'):
                    return None
                return int(raw)
        return default

    manifest = create_snapshot(
        Path('$PROJECT_DIR'),
        '$AGENT_ID',
        max_file_mb=_read_snapshot_int('max_file_mb', 50),
        max_total_mb=_read_snapshot_int('max_total_mb', 1024),
    )
    print(json.dumps(manifest))
except Exception as exc:
    print(json.dumps({"status": "error", "error": str(exc), "snapshot_id": "", "tracked_stash_ref": None, "untracked_files": [], "skipped_untracked_files": []}))
PYEOF
)
  fi
  if command -v cos_stash_lock_release >/dev/null 2>&1; then
    cos_stash_lock_release
    trap - EXIT INT TERM
  fi
  if [ -n "$SNAPSHOT_RESULT" ] && command -v jq >/dev/null 2>&1; then
    SNAPSHOT_STATUS=$(echo "$SNAPSHOT_RESULT" | jq -r '.status // "error"' 2>/dev/null || echo "error")
    SNAPSHOT_ID=$(echo "$SNAPSHOT_RESULT" | jq -r '.snapshot_id // ""' 2>/dev/null || true)
    STASH_REF=$(echo "$SNAPSHOT_RESULT" | jq -r '.tracked_stash_ref // ""' 2>/dev/null || true)
    STASH_SHA=$(echo "$SNAPSHOT_RESULT" | jq -r '.tracked_stash_sha // ""' 2>/dev/null || true)
    UNTRACKED_COUNT=$(echo "$SNAPSHOT_RESULT" | jq -r '(.untracked_files // []) | length' 2>/dev/null || echo 0)
    SKIPPED_UNTRACKED_COUNT=$(echo "$SNAPSHOT_RESULT" | jq -r '(.skipped_untracked_files // []) | length' 2>/dev/null || echo 0)
    TREE_DIRTY=false
    if [ -n "$STASH_SHA" ] || [ -n "$STASH_REF" ] || [ "${UNTRACKED_COUNT:-0}" -gt 0 ] 2>/dev/null || [ "${SKIPPED_UNTRACKED_COUNT:-0}" -gt 0 ] 2>/dev/null; then
      TREE_DIRTY=true
    fi
    if [ "$SNAPSHOT_STATUS" = "ok" ] && [ "$TREE_DIRTY" = false ]; then
      SNAPSHOT_STATUS="skip_clean"
    elif [ "$SNAPSHOT_STATUS" = "ok" ] && { [ -n "$STASH_SHA" ] || [ -n "$STASH_REF" ]; }; then
      SNAPSHOT_STATUS="stashed"
      # ADR-116 P4.3: record stash provenance for auto-reapply on next SessionStart
      _PROV_FILES=$(git -C "$PROJECT_DIR" stash show --name-only "$STASH_REF" 2>/dev/null | tr '\n' '\n' || true)
      COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" python3 -m stash_provenance record \
        --stash-ref "$STASH_REF" \
        --session-id "$SESSION_ID" \
        --agent-id "$AGENT_ID" \
        --original-files "$_PROV_FILES" \
        --created-at "$TIMESTAMP" 2>/dev/null || true
    fi
  elif [ -n "$SNAPSHOT_RESULT" ]; then
    SNAPSHOT_STATUS="ok"
  fi
else
  # Python unavailable — fall back to bash-only copy approach
  SNAPSHOT_STATUS="python_unavailable"
fi

# Re-create SESSIONS_DIR in case stash swallowed it
mkdir -p "$SESSIONS_DIR" 2>/dev/null || true
mkdir -p "$(dirname "$METRICS_LOG")" 2>/dev/null || true

# Write session snapshot metadata JSON
{
  printf '{'
  printf '"timestamp":"%s",' "$TIMESTAMP"
  printf '"agent_id":"%s",' "$AGENT_ID"
  printf '"session_id":"%s",' "$SESSION_ID"
  printf '"mode":"copy",'
  printf '"snapshot_id":"%s",' "${SNAPSHOT_ID//\"/\\\"}"
  printf '"stash_ref":"%s",' "${STASH_REF//\"/\\\"}"
  printf '"stash_sha":"%s",' "${STASH_SHA//\"/\\\"}"
  printf '"status":"%s",' "$SNAPSHOT_STATUS"
  printf '"tree_dirty":%s,' "$TREE_DIRTY"
  escaped_prompt=${PROMPT_SUMMARY//\\/\\\\}
  escaped_prompt=${escaped_prompt//\"/\\\"}
  printf '"prompt_summary":"%s"' "$escaped_prompt"
  printf '}\n'
} > "$SNAPSHOT_FILE" 2>/dev/null || true

# Append to metrics JSONL
METRICS_LINE=$(printf '{"timestamp":"%s","event":"agent_snapshot","agent_id":"%s","session_id":"%s","status":"%s","snapshot_id":"%s","stash_ref":"%s","stash_sha":"%s","tree_dirty":%s,"untracked_count":%s,"skipped_untracked_count":%s,"mode":"copy"}' \
  "$TIMESTAMP" "$AGENT_ID" "$SESSION_ID" "$SNAPSHOT_STATUS" "${SNAPSHOT_ID}" "${STASH_REF}" "${STASH_SHA}" "$TREE_DIRTY" "${UNTRACKED_COUNT:-0}" "${SKIPPED_UNTRACKED_COUNT:-0}")
safe_jsonl_append "$METRICS_LOG" "$METRICS_LINE" 2>/dev/null || true

# Write runtime marker so post-agent-snapshot-restore.sh can find the exact stash/snapshot
if [ -n "$STASH_SHA" ] || [ -n "$STASH_REF" ] || [ -n "$SNAPSHOT_ID" ]; then
  mkdir -p "$RUNTIME_DIR" 2>/dev/null || true
  printf '{"schema_version":"pre-agent-snapshot/v2","stash_sha":"%s","stash_ref_at_capture":"%s","stash_ref":"%s","agent_id":"%s","session_id":"%s","timestamp":"%s","snapshot_id":"%s","mode":"copy"}\n' \
    "${STASH_SHA//\"/\\\"}" "${STASH_REF//\"/\\\"}" "${STASH_REF//\"/\\\"}" "$AGENT_ID" "$SESSION_ID" "$TIMESTAMP" "${SNAPSHOT_ID//\"/\\\"}" \
    > "$MARKER_FILE" 2>/dev/null || true
fi

# Always advisory — never block
exit 0
