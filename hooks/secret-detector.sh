#!/usr/bin/env bash
# PostToolUse hook on Edit|Write: detect new env var references without definitions
# Part of EnvGuard — Secret Detection tooling

set -euo pipefail

_HOOK_NAME="secret-detector"
source "$(dirname "$0")/_lib/safe-jsonl.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
METRICS_FILE="$METRICS_DIR/missing-secrets.jsonl"

# Only run on source file edits (not .md, not .cognitive-os config)
TOOL_INPUT="${TOOL_INPUT:-}"
if [ -z "$TOOL_INPUT" ]; then
  exit 0
fi

# Extract file path from tool input
FILE_PATH=$(echo "$TOOL_INPUT" | grep -oE '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"$//' 2>/dev/null || true)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Skip non-source files
case "$FILE_PATH" in
  *.md|*.json|*.yaml|*.yml|*.lock|*.sum|*.sh)
    exit 0
    ;;
  */.cognitive-os/*|*/.claude/*)
    exit 0
    ;;
esac

# Collect env var references from the edited file
ENV_VARS=()

if [ -f "$FILE_PATH" ]; then
  # Node/TypeScript: process.env.VAR_NAME
  while IFS= read -r var; do
    ENV_VARS+=("$var")
  done < <(grep -oE 'process\.env\.([A-Z_][A-Z0-9_]*)' "$FILE_PATH" 2>/dev/null | sed 's/process\.env\.//' | sort -u || true)

  # Go: os.Getenv("VAR_NAME")
  while IFS= read -r var; do
    ENV_VARS+=("$var")
  done < <(grep -oE 'os\.Getenv\("([A-Z_][A-Z0-9_]*)"\)' "$FILE_PATH" 2>/dev/null | sed 's/os\.Getenv("//;s/")//' | sort -u || true)

  # Java: System.getenv("VAR_NAME")
  while IFS= read -r var; do
    ENV_VARS+=("$var")
  done < <(grep -oE 'System\.getenv\("([A-Z_][A-Z0-9_]*)"\)' "$FILE_PATH" 2>/dev/null | sed 's/System\.getenv("//;s/")//' | sort -u || true)

  # Spring Boot: @Value("${VAR_NAME}")
  while IFS= read -r var; do
    ENV_VARS+=("$var")
  done < <(grep -oE '\$\{([A-Z_][A-Z0-9_]*)' "$FILE_PATH" 2>/dev/null | sed 's/\${//' | sort -u || true)
fi

if [ ${#ENV_VARS[@]} -eq 0 ]; then
  exit 0
fi

# Search for env var definitions across the project
MISSING=()
for VAR in "${ENV_VARS[@]}"; do
  FOUND=false

  # Check .env files
  if grep -rq "^${VAR}=" "$PROJECT_DIR"/.env* 2>/dev/null; then
    FOUND=true
  fi

  # Check .env.example files
  if [ "$FOUND" = false ] && find "$PROJECT_DIR" -name '.env.example' -exec grep -q "^${VAR}=" {} \; 2>/dev/null; then
    FOUND=true
  fi

  # Check docker-compose files
  if [ "$FOUND" = false ] && grep -rq "${VAR}" "$PROJECT_DIR"/docker-compose*.yml 2>/dev/null; then
    FOUND=true
  fi

  # Check config Go files
  if [ "$FOUND" = false ] && grep -rq "\"${VAR}\"" "$PROJECT_DIR"/**/config*.go 2>/dev/null; then
    FOUND=true
  fi

  # Check dev.env files
  if [ "$FOUND" = false ] && find "$PROJECT_DIR" -name 'dev.env' -exec grep -q "^${VAR}=" {} \; 2>/dev/null; then
    FOUND=true
  fi

  if [ "$FOUND" = false ]; then
    MISSING+=("$VAR")
  fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
  mkdir -p "$METRICS_DIR"

  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  for VAR in "${MISSING[@]}"; do
    ENTRY="{\"timestamp\":\"$TIMESTAMP\",\"file\":\"$FILE_PATH\",\"var\":\"$VAR\",\"status\":\"missing\"}"
    safe_jsonl_append "$METRICS_FILE" "$ENTRY"
  done

  # Output warning for Claude to see
  echo "WARNING: Missing env var definitions: ${MISSING[*]}"
  echo "These env vars are referenced in $FILE_PATH but not defined in .env, .env.example, docker-compose, or config files."
  echo "Add them to .env.example to maintain the secret hygiene contract."
fi

exit 0
