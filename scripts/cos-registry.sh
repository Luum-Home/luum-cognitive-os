#!/usr/bin/env bash
# SCOPE: os-only
# cos-registry.sh — Manage the global COS installations registry
#
# Library functions for adding/removing/querying COS installations.
# Source this file from other scripts, or run directly for CLI access.
#
# Usage as CLI:
#   bash scripts/cos-registry.sh register <path> <mode> <version> <project_name> <source>
#   bash scripts/cos-registry.sh deregister <path>
#   bash scripts/cos-registry.sh list
#   bash scripts/cos-registry.sh cleanup   # remove entries for non-existent directories
#
# Registry location: ~/.cognitive-os/installations.json
# Bash 3.x compatible (no associative arrays, no bash 4+ features).
# Author: luum
set -euo pipefail

COS_REGISTRY_FILE="${COS_REGISTRY_FILE:-$HOME/.cognitive-os/installations.json}"

# ── Ensure registry directory exists ──────────────────────────────
_ensure_registry_dir() {
  local dir
  dir=$(dirname "$COS_REGISTRY_FILE")
  if [ ! -d "$dir" ]; then
    mkdir -p "$dir"
  fi
}

# ── Ensure registry file exists ───────────────────────────────────
_ensure_registry() {
  _ensure_registry_dir
  if [ ! -f "$COS_REGISTRY_FILE" ]; then
    echo '{"installations":[]}' > "$COS_REGISTRY_FILE"
  fi
}

# ── Register a COS installation ───────────────────────────────────
# Usage: cos_registry_register <path> <mode> <version> <project_name> <source>
cos_registry_register() {
  local project_path="$1"
  local mode="$2"
  local version="$3"
  local project_name="$4"
  local source_dir="$5"

  # Skip writing to the production registry when running inside a pytest session.
  # Tests that need registry behaviour must set COS_REGISTRY_FILE to a tmp path.
  if [ -n "${PYTEST_CURRENT_TEST:-}" ] && [ "${COS_REGISTRY_FILE:-}" = "$HOME/.cognitive-os/installations.json" ]; then
    return 0
  fi

  if ! command -v jq >/dev/null 2>&1; then
    echo "Warning: jq not available, skipping registry update." >&2
    return 0
  fi

  _ensure_registry

  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  # Resolve to absolute path
  if [ -d "$project_path" ]; then
    project_path=$(cd "$project_path" && pwd)
  fi

  # Check if already registered (update if so)
  local existing
  existing=$(jq -r --arg path "$project_path" \
    '.installations[] | select(.path == $path) | .path' \
    "$COS_REGISTRY_FILE" 2>/dev/null || true)

  local tmp
  tmp=$(mktemp)

  if [ -n "$existing" ]; then
    # Update existing entry
    jq --arg path "$project_path" \
       --arg mode "$mode" \
       --arg ver "$version" \
       --arg name "$project_name" \
       --arg src "$source_dir" \
       --arg now "$now" \
       '(.installations[] | select(.path == $path)) |=
        . + {mode: $mode, version: $ver, project_name: $name, source: $src, updated_at: $now}' \
       "$COS_REGISTRY_FILE" > "$tmp" && mv "$tmp" "$COS_REGISTRY_FILE"
  else
    # Add new entry
    jq --arg path "$project_path" \
       --arg mode "$mode" \
       --arg ver "$version" \
       --arg name "$project_name" \
       --arg src "$source_dir" \
       --arg now "$now" \
       '.installations += [{
          path: $path,
          mode: $mode,
          version: $ver,
          project_name: $name,
          source: $src,
          installed_at: $now,
          updated_at: $now
        }]' \
       "$COS_REGISTRY_FILE" > "$tmp" && mv "$tmp" "$COS_REGISTRY_FILE"
  fi
  rm -f "$tmp"
}

# ── Deregister a COS installation ─────────────────────────────────
# Usage: cos_registry_deregister <path>
cos_registry_deregister() {
  local project_path="$1"

  if ! command -v jq >/dev/null 2>&1; then
    echo "Warning: jq not available, skipping registry update." >&2
    return 0
  fi

  if [ ! -f "$COS_REGISTRY_FILE" ]; then
    return 0
  fi

  # Resolve to absolute path
  if [ -d "$project_path" ]; then
    project_path=$(cd "$project_path" && pwd)
  fi

  local tmp
  tmp=$(mktemp)
  jq --arg path "$project_path" \
     '.installations |= map(select(.path != $path))' \
     "$COS_REGISTRY_FILE" > "$tmp" && mv "$tmp" "$COS_REGISTRY_FILE"
  rm -f "$tmp"
}

# ── Cleanup stale entries ─────────────────────────────────────────
cos_registry_cleanup() {
  if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq required." >&2
    return 1
  fi

  if [ ! -f "$COS_REGISTRY_FILE" ]; then
    echo "No registry file found."
    return 0
  fi

  local removed=0
  local paths
  paths=$(jq -r '.installations[].path' "$COS_REGISTRY_FILE" 2>/dev/null || true)

  while IFS= read -r path; do
    [ -n "$path" ] || continue
    if [ ! -d "$path" ]; then
      cos_registry_deregister "$path"
      echo "  Removed: $path (directory not found)"
      removed=$((removed + 1))
    fi
  done <<< "$paths"

  if [ "$removed" -eq 0 ]; then
    echo "No stale entries found."
  else
    echo "Cleaned up $removed stale entries."
  fi
}

# ── List installations ────────────────────────────────────────────
cos_registry_list() {
  if ! command -v jq >/dev/null 2>&1; then
    echo "Error: jq required." >&2
    return 1
  fi

  if [ ! -f "$COS_REGISTRY_FILE" ]; then
    echo "No installations registered."
    return 0
  fi

  local count
  count=$(jq '.installations | length' "$COS_REGISTRY_FILE" 2>/dev/null || echo 0)
  echo "Registered COS installations: $count"
  echo "Registry: $COS_REGISTRY_FILE"
  echo ""

  if [ "$count" -gt 0 ]; then
    jq -r '.installations[] | "  \(.project_name) [\(.mode)] v\(.version)\n    \(.path)\n    Source: \(.source)\n"' \
      "$COS_REGISTRY_FILE" 2>/dev/null
  fi
}

# ── CLI entry point ───────────────────────────────────────────────
# Only run if executed directly (not sourced)
if [ "${BASH_SOURCE[0]}" = "$0" ] 2>/dev/null || [ "${0##*/}" = "cos-registry.sh" ]; then
  case "${1:-list}" in
    register)
      shift
      if [ $# -lt 5 ]; then
        echo "Usage: cos-registry.sh register <path> <mode> <version> <project_name> <source>" >&2
        exit 1
      fi
      cos_registry_register "$1" "$2" "$3" "$4" "$5"
      echo "Registered: $4 at $1"
      ;;
    deregister)
      shift
      if [ $# -lt 1 ]; then
        echo "Usage: cos-registry.sh deregister <path>" >&2
        exit 1
      fi
      cos_registry_deregister "$1"
      echo "Deregistered: $1"
      ;;
    list)
      cos_registry_list
      ;;
    cleanup)
      cos_registry_cleanup
      ;;
    *)
      echo "Usage: cos-registry.sh <register|deregister|list|cleanup>" >&2
      exit 1
      ;;
  esac
fi
