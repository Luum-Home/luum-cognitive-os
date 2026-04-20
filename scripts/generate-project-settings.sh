#!/usr/bin/env bash
# SCOPE: os-only
# generate-project-settings.sh — Generate a clean settings.json for external projects
#
# Reads the COS source settings.json, transforms hook paths for external project layout,
# and filters by mode (minimal/standard/full). Removes self-hosting-only hooks.
#
# Usage:
#   bash scripts/generate-project-settings.sh --standard > settings.json
#   bash scripts/generate-project-settings.sh --full --output /path/to/settings.json
#
# Requires: jq
# Bash 3.x compatible.
set -euo pipefail

COS_SOURCE_DIR="${COS_SOURCE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
SOURCE_SETTINGS="$COS_SOURCE_DIR/.claude/settings.json"
# ADR-002: canonical modes are --default and --full. Legacy (--minimal,
# --standard, --lean) are silently remapped to --default.
MODE="--default"
OUTPUT=""

for arg in "$@"; do
  case "$arg" in
    --default|--full) MODE="$arg" ;;
    --minimal|--standard|--lean)
      echo "Note: ADR-002 collapsed '$arg' into '--default'. Using '--default'." >&2
      MODE="--default"
      ;;
    --output=*) OUTPUT="${arg#--output=}" ;;
    --help|-h)
      echo "Usage: bash $0 [--default|--full] [--output FILE]"
      echo ""
      echo "  --default  ADR-002 default tier (curated hook set)"
      echo "  --full     Full hook coverage"
      echo ""
      echo "  Legacy (remapped to --default): --minimal, --standard, --lean"
      exit 0
      ;;
  esac
done

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required" >&2
  exit 1
fi

if [ ! -f "$SOURCE_SETTINGS" ]; then
  echo "Error: COS source settings.json not found: $SOURCE_SETTINGS" >&2
  exit 1
fi

# ── Hook lists ──────────────────────────────────────────────────────
# Self-hosting-only hooks: never included in external projects
SELF_HOSTING_ONLY="self-install.sh release-guard.sh"

# ADR-002 default tier hook set (~29 hooks). Includes the regression guards:
# auto-verify, auto-refine, dod-gate, session-sanity, confidentiality-enforcer.
DEFAULT_HOOKS="error-pipeline.sh session-init.sh session-cleanup.sh result-truncator.sh
  clarification-gate.sh blast-radius.sh scope-proportionality.sh
  error-pattern-detector.sh auto-refine.sh auto-verify.sh completeness-check.sh dod-gate.sh
  trust-score-validator.sh skill-metrics-tracker.sh inject-phase-context.sh stack-detector.sh
  pre-compaction-flush.sh rate-limiter.sh large-file-advisor.sh secret-detector.sh content-policy.sh
  confidentiality-enforcer.sh
  doc-sync-detector.sh auto-checkpoint.sh claim-validator.sh completion-gate.sh
  clarification-interceptor.sh agent-checkpoint.sh session-sanity.sh
  session-learning.sh crash-recovery.sh teammate-idle.sh task-created.sh task-completed.sh"

# ── Step 1: Transform paths ─────────────────────────────────────────
# $CLAUDE_PROJECT_DIR/hooks/X.sh -> $CLAUDE_PROJECT_DIR/.cognitive-os/hooks/cos/X.sh
transformed=$(jq '
  .hooks |= (
    to_entries | map(
      .value |= map(
        .hooks |= map(
          if (.command | test("\\$CLAUDE_PROJECT_DIR/hooks/")) then
            .command |= gsub("\\$CLAUDE_PROJECT_DIR/hooks/"; "$CLAUDE_PROJECT_DIR/.cognitive-os/hooks/cos/")
          else
            .
          end
        )
      )
    ) | from_entries
  )
' "$SOURCE_SETTINGS")

# ── Step 2: Build jq filter for allowed hooks ───────────────────────
build_jq_filter() {
  local hook_list="$1"

  # Build JSON array of allowed filenames
  local arr="["
  local first=true
  for h in $hook_list; do
    [ "$first" = true ] && first=false || arr="$arr,"
    arr="$arr\"$h\""
  done
  arr="$arr]"

  # Build JSON array of blocked filenames
  local blocked="["
  first=true
  for h in $SELF_HOSTING_ONLY; do
    [ "$first" = true ] && first=false || blocked="$blocked,"
    blocked="$blocked\"$h\""
  done
  blocked="$blocked]"

  echo "$transformed" | jq --argjson allowed "$arr" --argjson blocked "$blocked" '
    .hooks |= (
      to_entries | map(
        .value |= [
          .[] |
          .hooks |= [
            .[] |
            # Extract filename: split by /, take last, strip trailing \"
            (.command | split("/") | last | rtrimstr("\"") | rtrimstr("\\\"")) as $fname |
            # Keep project-specific hooks (.claude/hooks/) always
            if (.command | test("\\.claude/hooks/")) then .
            # Block self-hosting-only
            elif ($fname | IN($blocked[])) then empty
            # For non-full mode, only allow listed hooks
            elif ($allowed | length > 0) then
              if ($fname | IN($allowed[])) then . else empty end
            else .
            end
          ] |
          select(.hooks | length > 0)
        ] |
        select(length > 0)
      ) | from_entries
    )
  '
}

# ── Step 3: Apply mode filter ───────────────────────────────────────
case "$MODE" in
  --default)
    result=$(build_jq_filter "$DEFAULT_HOOKS")
    ;;
  --full)
    # Full: include all except self-hosting-only
    result=$(build_jq_filter "")
    ;;
esac

# ── Output ──────────────────────────────────────────────────────────
if [ -n "$OUTPUT" ]; then
  echo "$result" > "$OUTPUT"
else
  echo "$result"
fi
