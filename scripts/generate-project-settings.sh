#!/usr/bin/env bash
# SCOPE: os-only
# generate-project-settings.sh — Generate harness-aware hook settings for external projects
#
# Reads the COS source settings.json, transforms hook paths for external
# project layout, filters by mode (minimal/standard/full), removes
# self-hosting-only hooks, and projects the result into a harness-specific
# settings driver.
#
# Usage:
#   bash scripts/generate-project-settings.sh --standard > settings.json
#   bash scripts/generate-project-settings.sh --full --output /path/to/settings.json
#   bash scripts/generate-project-settings.sh --full --harness codex > hooks.json
#
# Requires: jq
# Bash 3.x compatible.
set -euo pipefail

COS_SOURCE_DIR="${COS_SOURCE_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
SOURCE_SETTINGS="$COS_SOURCE_DIR/.claude/settings.json"
# ADR-093: canonical modes are --default and --full. Legacy (--minimal,
# --standard, --lean) are silently remapped to --default.
MODE="--default"
OUTPUT=""
HARNESS="${COGNITIVE_OS_HARNESS:-claude}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --default|--full)
      MODE="$1"
      shift
      ;;
    --minimal|--standard|--lean)
      echo "Note: ADR-093 collapsed '$1' into '--default'. Using '--default'." >&2
      MODE="--default"
      shift
      ;;
    --harness)
      if [ -z "${2:-}" ]; then
        echo "Error: --harness requires a value (claude or codex)." >&2
        exit 1
      fi
      HARNESS="$2"
      shift 2
      ;;
    --harness=*)
      HARNESS="${1#--harness=}"
      shift
      ;;
    --output=*)
      OUTPUT="${1#--output=}"
      shift
      ;;
    --help|-h)
      echo "Usage: bash $0 [--default|--full] [--harness HARNESS] [--output FILE]"
      echo ""
      echo "  --default  ADR-093 default tier (curated hook set)"
      echo "  --full     Full hook coverage"
      echo "  --harness  Projection target: claude or codex (default: claude)"
      echo ""
      echo "  Legacy (remapped to --default): --minimal, --standard, --lean"
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

case "$HARNESS" in
  claude)
    DRIVER_PROJECT_EXPR='${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}'
    ;;
  codex)
    DRIVER_PROJECT_EXPR='${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$PWD}}'
    ;;
  *)
    echo "Error: unsupported harness '$HARNESS' (expected claude or codex)." >&2
    exit 1
    ;;
esac

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
INSTALL_SCOPE="${COS_INSTALL_SCOPE:-both}"

scope_allows() {
  local f="$1"
  [ -f "$f" ] || return 0
  [ "$INSTALL_SCOPE" = "all" ] && return 0

  local scope_val
  scope_val=$(head -3 "$f" 2>/dev/null | grep -m1 -oE '(# SCOPE:|<!-- SCOPE:) [a-zA-Z_/-]+' | awk '{print $NF}' | tr -d ' ' | head -1 || true)
  [ -z "$scope_val" ] && return 0

  case "$scope_val" in
    project|both) return 0 ;;
    os-only)      return 1 ;;
    *)            return 0 ;;
  esac
}

project_scoped_hooks() {
  local hook_file
  for hook_file in "$COS_SOURCE_DIR/hooks"/*.sh; do
    [ -f "$hook_file" ] || continue
    scope_allows "$hook_file" || continue
    basename "$hook_file"
  done
}

filter_hook_list_by_scope() {
  local hook_name
  for hook_name in $1; do
    scope_allows "$COS_SOURCE_DIR/hooks/$hook_name" || continue
    printf '%s\n' "$hook_name"
  done
}

# ADR-093 default tier hook set (~29 hooks). Includes the regression guards:
# auto-verify, auto-refine, dod-gate, session-sanity, confidentiality-enforcer.
DEFAULT_HOOKS="error-pipeline.sh session-init.sh host-tool-doctor.sh session-cleanup.sh result-truncator.sh
  user-prompt-capture.sh session-wrapup-trigger.sh session-heartbeat.sh memory-prefetch.sh
  clarification-gate.sh blast-radius.sh scope-proportionality.sh
  error-pattern-detector.sh auto-refine.sh auto-verify.sh dod-gate.sh
  trust-score-validator.sh skill-metrics-tracker.sh inject-phase-context.sh stack-detector.sh
  pre-compaction-flush.sh rate-limiter.sh large-file-advisor.sh secret-detector.sh content-policy.sh ai-provider-identity-guard.sh
  confidentiality-enforcer.sh
  doc-sync-detector.sh auto-checkpoint.sh claim-validator.sh direct-main-guard.sh orchestrator-claim-gate.sh plan-claim-validator.sh completion-gate.sh
  clarification-interceptor.sh agent-checkpoint.sh session-sanity.sh
  session-learning.sh engram-obsidian-export-on-stop.sh crash-recovery.sh teammate-idle.sh task-created.sh task-completed.sh"

# ── Step 1: Transform paths ─────────────────────────────────────────
# $CLAUDE_PROJECT_DIR/hooks/X.sh -> ${driver_project_expr}/.cognitive-os/hooks/cos/X.sh
# $CLAUDE_PROJECT_DIR/scripts/hook-timing-wrapper.sh ->
#   ${driver_project_expr}/.cognitive-os/hooks/cos/_lib/hook-timing-wrapper.sh
#
# The wrapper is runtime-critical once settings.json is wrapped. Consumer
# projects do not own the source repo's scripts/ directory, so generated
# drivers must point to the canonical installed copy under .cognitive-os/.
transformed=$(jq --arg project_expr "$DRIVER_PROJECT_EXPR" '
  .hooks |= (
    to_entries | map(
      .value |= map(
        .hooks |= map(
          .command |= gsub("\\$CLAUDE_PROJECT_DIR/hooks/"; ($project_expr + "/.cognitive-os/hooks/cos/")) |
          .command |= gsub("\\$CLAUDE_PROJECT_DIR/scripts/hook-timing-wrapper\\.sh"; ($project_expr + "/.cognitive-os/hooks/cos/_lib/hook-timing-wrapper.sh")) |
          .command |= gsub("\\$CLAUDE_PROJECT_DIR/scripts/"; ($project_expr + "/scripts/")) |
          .command |= gsub("\\$CLAUDE_PROJECT_DIR/\\.claude/hooks/"; ($project_expr + "/.claude/hooks/"))
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
    # Default is still an external-project install surface: curated hooks must
    # pass the same SCOPE filter as full installs so generated settings never
    # reference hooks that were intentionally not copied.
    result=$(build_jq_filter "$(filter_hook_list_by_scope "$DEFAULT_HOOKS")")
    ;;
  --full)
    # Full: include every hook installable under the active scope, then remove
    # self-hosting-only hooks inside build_jq_filter. Do not append the default
    # set here: default contains self-hosting os-only hooks that full external
    # installs intentionally do not copy, and projecting them creates dangling
    # driver commands.
    result=$(build_jq_filter "$(project_scoped_hooks)")
    ;;
esac

# ── Output ──────────────────────────────────────────────────────────
if [ "$HARNESS" = "codex" ]; then
  # Codex hooks.json uses lifecycle events at the top level and has a narrower
  # proven hook contract than Claude.  Project only lifecycle hooks plus
  # Bash-scoped tool hooks, and translate matcher names to Codex-native values.
  # Do not copy unsupported Claude events into Codex just to make counts match.
  result=$(echo "$result" | jq '{
    SessionStart: ((.hooks.SessionStart // []) | map(.matcher = "startup")),
    UserPromptSubmit: ((.hooks.UserPromptSubmit // []) | map(.matcher = "prompt")),
    PreToolUse: ((.hooks.PreToolUse // []) | map(select(.matcher == "Bash") | .matcher = "bash")),
    PostToolUse: ((.hooks.PostToolUse // []) | map(select(.matcher == "Bash") | .matcher = "bash")),
    Stop: ((.hooks.Stop // []) | map(.matcher = "shutdown"))
  }')
fi

if [ -n "$OUTPUT" ]; then
  echo "$result" > "$OUTPUT"
else
  echo "$result"
fi
