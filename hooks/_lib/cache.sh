#!/usr/bin/env bash
# cache.sh — SHA-256 file cache for hook scans
#
# Skips re-scanning files that have not changed since last scan.
# Cache key = SHA-256(file_path:rules_hash), stored value = SHA-256(file_content).
# When rules/config change, rules_hash changes, invalidating all entries for that hook.
#
# Usage:
#   source "$(dirname "$0")/_lib/cache.sh"
#   RULES_HASH=$(shasum -a 256 "$CONFIG_FILE" 2>/dev/null | cut -d' ' -f1 || echo "none")
#   if cache_hit "$FILE_PATH" "$RULES_HASH"; then exit 0; fi
#   ... do scanning work ...
#   cache_update "$FILE_PATH" "$RULES_HASH"
#
# Functions:
#   cache_hit <file_path> <rules_hash>       — returns 0 if file unchanged, 1 otherwise
#   cache_update <file_path> <rules_hash>    — store current file hash in cache
#   cache_invalidate_all                     — remove entire cache directory

# Guard: only load once
[ "${_CACHE_SH_LOADED:-}" = "true" ] && return 0
_CACHE_SH_LOADED="true"

CACHE_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/cache/hook-scans"

# cache_hit — check if file content matches cached hash
# Returns 0 (hit) if the file has not changed since last cache_update.
# Returns 1 (miss) if no cache entry, file missing, or content differs.
cache_hit() {
  local file_path="$1"
  local rules_hash="${2:-none}"

  # No file, no cache
  [ ! -f "$file_path" ] && return 1

  local cache_key
  cache_key=$(printf '%s:%s' "$file_path" "$rules_hash" | shasum -a 256 | cut -d' ' -f1)
  local cache_file="$CACHE_DIR/$cache_key"

  # No cached entry
  [ ! -f "$cache_file" ] && return 1

  # Compare stored hash with current file hash
  local stored_hash current_hash
  stored_hash=$(cat "$cache_file" 2>/dev/null)
  current_hash=$(shasum -a 256 "$file_path" 2>/dev/null | cut -d' ' -f1)

  [ "$stored_hash" = "$current_hash" ]
}

# cache_update — store the current file hash
cache_update() {
  local file_path="$1"
  local rules_hash="${2:-none}"

  [ ! -f "$file_path" ] && return 0

  local cache_key
  cache_key=$(printf '%s:%s' "$file_path" "$rules_hash" | shasum -a 256 | cut -d' ' -f1)

  mkdir -p "$CACHE_DIR" 2>/dev/null
  shasum -a 256 "$file_path" 2>/dev/null | cut -d' ' -f1 > "$CACHE_DIR/$cache_key"
}

# cache_invalidate_all — wipe all cached entries
cache_invalidate_all() {
  rm -rf "$CACHE_DIR" 2>/dev/null
}
