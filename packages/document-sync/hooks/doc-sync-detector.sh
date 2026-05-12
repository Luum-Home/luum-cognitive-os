#!/usr/bin/env bash
# SCOPE: project
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"
# Hook: PostToolUse — Detect when code changes make documentation stale
# Triggers on Edit/Write of source files (*.go, *.ts, *.java)
# Appends stale doc entries to .cognitive-os/metrics/stale-docs.jsonl

_HOOK_NAME="doc-sync-detector"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only trigger on Edit or Write
if [ "$TOOL_NAME" != "Edit" ] && [ "$TOOL_NAME" != "Write" ]; then
  exit 0
fi

# Skip if no file path
if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Only trigger on source files
if ! echo "$FILE_PATH" | grep -qE '\.(go|ts|java)$'; then
  exit 0
fi

# Skip test files
if echo "$FILE_PATH" | grep -qE '(_test\.go|\.spec\.ts|\.test\.ts|Test\.java|IT\.java)$'; then
  exit 0
fi

# Skip mock/fixture files
if echo "$FILE_PATH" | grep -qiE '(mock|fixture|stub|fake)'; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
STALE_FILE="$METRICS_DIR/stale-docs.jsonl"

# Ensure metrics dir exists
mkdir -p "$METRICS_DIR"

# Determine change type and map to related docs
STALE_DOCS=""
CHANGE_TYPE=""

# --- Controller changes ---
if echo "$FILE_PATH" | grep -qE '(infrastructure/controllers/|controller\.go|controller\.ts|Controller\.java)'; then
  CHANGE_TYPE="controller"
  STALE_DOCS="docs/migration-audit.md docs/feature-parity-report.md"

# --- Entity / domain model changes ---
elif echo "$FILE_PATH" | grep -qE '(domain/entities/|entity\.go|_entity\.go|entity\.ts|Entity\.java)'; then
  CHANGE_TYPE="entity"
  STALE_DOCS="docs/migration-audit.md"

# --- Config changes ---
elif echo "$FILE_PATH" | grep -qE '(config/|\.config\.ts|configuration\.ts|application\.properties|application\.yml)'; then
  CHANGE_TYPE="config"
  STALE_DOCS="docs/05-Methodology/setup/"

# --- Use case changes ---
elif echo "$FILE_PATH" | grep -qE '(application/use.?cases?/|_usecase\.go|usecase\.go|\.usecase\.ts|UseCase\.java)'; then
  CHANGE_TYPE="usecase"
  STALE_DOCS="docs/migration-audit.md docs/feature-parity-report.md"

# --- Route / module changes ---
elif echo "$FILE_PATH" | grep -qE '(\.module\.ts|routes\.go|router\.go|\.routes\.ts)'; then
  CHANGE_TYPE="route"
  STALE_DOCS="docs/migration-audit.md"

# --- Cognitive OS hooks ---
elif echo "$FILE_PATH" | grep -qE '\hooks/'; then
  CHANGE_TYPE="hook"
  STALE_DOCS=".cognitive-os/docs/05-Methodology/root/hooks.md .cognitive-os/docs/00-MOCs/entrypoints/overview.md"

# --- Cognitive OS rules ---
elif echo "$FILE_PATH" | grep -qE '\.cognitive-os/rules/'; then
  CHANGE_TYPE="rule"
  STALE_DOCS=".cognitive-os/docs/05-Methodology/root/rules.md .cognitive-os/docs/00-MOCs/entrypoints/overview.md"

# --- Docker compose ---
elif echo "$FILE_PATH" | grep -qE 'docker-compose.*\.(yml|yaml)$'; then
  CHANGE_TYPE="docker"
  STALE_DOCS="docs/05-Methodology/setup/docker-architecture.md"

else
  # No doc mapping for this file type
  exit 0
fi

# Build list of stale docs that actually exist
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EXISTING_DOCS=""

for doc in $STALE_DOCS; do
  FULL_PATH="$PROJECT_DIR/$doc"
  # Check if it's a file or directory
  if [ -f "$FULL_PATH" ]; then
    EXISTING_DOCS="$EXISTING_DOCS \"$doc\","
  elif [ -d "$FULL_PATH" ]; then
    # For directories, find all .md files inside
    for md_file in "$FULL_PATH"/*.md; do
      if [ -f "$md_file" ]; then
        REL_PATH=$(echo "$md_file" | sed "s|$PROJECT_DIR/||")
        EXISTING_DOCS="$EXISTING_DOCS \"$REL_PATH\","
      fi
    done
  fi
done

# Remove trailing comma
EXISTING_DOCS=$(echo "$EXISTING_DOCS" | sed 's/,$//')

# Skip if no existing docs found
if [ -z "$EXISTING_DOCS" ]; then
  exit 0
fi

# Make file path relative to project
REL_FILE=$(echo "$FILE_PATH" | sed "s|$PROJECT_DIR/||")

# Deduplicate: skip if same file+docs combo was logged in the last 60 seconds
if [ -f "$STALE_FILE" ]; then
  CUTOFF=$(( $(date +%s) - 60 ))
  RECENT=$(tail -5 "$STALE_FILE" | jq -r --arg file "$REL_FILE" 'select(.changed_file == $file) | .timestamp' 2>/dev/null | tail -1)
  if [ -n "$RECENT" ]; then
    RECENT_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$RECENT" +%s 2>/dev/null || echo "0")
    if [ "$RECENT_EPOCH" -gt "$CUTOFF" ] 2>/dev/null; then
      exit 0
    fi
  fi
fi

# Append entry
ENTRY="{\"timestamp\": \"$TIMESTAMP\", \"changed_file\": \"$REL_FILE\", \"stale_docs\": [$EXISTING_DOCS], \"change_type\": \"$CHANGE_TYPE\"}"
safe_jsonl_append "$STALE_FILE" "$ENTRY"

echo "[doc-sync] Detected stale docs after editing $REL_FILE ($CHANGE_TYPE): $EXISTING_DOCS"

exit 0
