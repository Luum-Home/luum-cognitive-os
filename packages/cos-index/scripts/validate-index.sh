#!/usr/bin/env bash
# validate-index.sh — Validate cos-index entries against actual package metadata
# Checks: required fields, version format, path existence (when local), duplicate names.
# Exit 0 on success, 1 on validation errors.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INDEX_FILE="${1:-$SCRIPT_DIR/../index/packages.yaml}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [ ! -f "$INDEX_FILE" ]; then
  echo "ERROR: Index file not found: $INDEX_FILE"
  exit 1
fi

errors=0
warnings=0
count=0

# Check if yq is available; fall back to grep-based validation.
if command -v yq >/dev/null 2>&1; then
  USE_YQ=true
else
  USE_YQ=false
fi

validate_with_yq() {
  local total
  total=$(yq '.packages | length' "$INDEX_FILE")
  local seen_names=""

  for ((i = 0; i < total; i++)); do
    count=$((count + 1))
    local name version description path repo

    name=$(yq ".packages[$i].name" "$INDEX_FILE")
    version=$(yq ".packages[$i].version" "$INDEX_FILE")
    description=$(yq ".packages[$i].description" "$INDEX_FILE")
    path=$(yq ".packages[$i].path" "$INDEX_FILE")
    repo=$(yq ".packages[$i].repo" "$INDEX_FILE")

    # Required fields
    if [ "$name" = "null" ] || [ -z "$name" ]; then
      echo "ERROR: Entry $i missing 'name'"
      errors=$((errors + 1))
    fi

    if [ "$version" = "null" ] || [ -z "$version" ]; then
      echo "ERROR: Entry $i ($name) missing 'version'"
      errors=$((errors + 1))
    fi

    if [ "$description" = "null" ] || [ -z "$description" ]; then
      echo "ERROR: Entry $i ($name) missing 'description'"
      errors=$((errors + 1))
    fi

    if [ "$path" = "null" ] || [ -z "$path" ]; then
      echo "ERROR: Entry $i ($name) missing 'path'"
      errors=$((errors + 1))
    fi

    if [ "$repo" = "null" ] || [ -z "$repo" ]; then
      echo "ERROR: Entry $i ($name) missing 'repo'"
      errors=$((errors + 1))
    fi

    # Version format (semver-like: X.Y.Z)
    if [ "$version" != "null" ] && ! echo "$version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
      echo "ERROR: Entry $i ($name) invalid version format: $version"
      errors=$((errors + 1))
    fi

    # Duplicate name check
    if echo "$seen_names" | grep -qF "|$name|"; then
      echo "ERROR: Duplicate package name: $name"
      errors=$((errors + 1))
    fi
    seen_names="${seen_names}|$name|"

    # Local path existence (when running inside the monorepo)
    if [ "$path" != "null" ] && [ -n "$path" ]; then
      local local_path="$PROJECT_ROOT/$path"
      if [ -d "$local_path" ]; then
        # Verify cos-package.yaml exists in the package directory
        if [ ! -f "$local_path/cos-package.yaml" ]; then
          echo "WARNING: $name ($path) exists but has no cos-package.yaml"
          warnings=$((warnings + 1))
        else
          # Cross-check version
          local actual_version
          actual_version=$(grep '^version:' "$local_path/cos-package.yaml" | head -1 | sed 's/^version: *//' | tr -d '"' | tr -d "'")
          if [ -n "$actual_version" ] && [ "$actual_version" != "$version" ]; then
            echo "WARNING: $name version mismatch — index: $version, actual: $actual_version"
            warnings=$((warnings + 1))
          fi
        fi
      fi
    fi
  done
}

validate_with_grep() {
  # Fallback: basic grep-based validation for environments without yq.
  local in_entry=false
  local entry_num=0
  local has_name=false has_version=false has_desc=false has_path=false has_repo=false
  local current_name=""
  local seen_names=""

  while IFS= read -r line; do
    # Skip comments and blank lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$line" ]] && continue

    # New entry starts with "  - name:"
    if echo "$line" | grep -qE '^\s+- name:'; then
      # Validate previous entry
      if [ "$in_entry" = true ]; then
        if [ "$has_name" = false ]; then echo "ERROR: Entry $entry_num missing name"; errors=$((errors + 1)); fi
        if [ "$has_version" = false ]; then echo "ERROR: Entry $entry_num ($current_name) missing version"; errors=$((errors + 1)); fi
        if [ "$has_desc" = false ]; then echo "ERROR: Entry $entry_num ($current_name) missing description"; errors=$((errors + 1)); fi
        if [ "$has_path" = false ]; then echo "ERROR: Entry $entry_num ($current_name) missing path"; errors=$((errors + 1)); fi
        if [ "$has_repo" = false ]; then echo "ERROR: Entry $entry_num ($current_name) missing repo"; errors=$((errors + 1)); fi
      fi

      in_entry=true
      entry_num=$((entry_num + 1))
      count=$((count + 1))
      has_name=true has_version=false has_desc=false has_path=false has_repo=false
      current_name=$(echo "$line" | sed 's/.*name: *//' | tr -d '"' | tr -d "'")

      # Duplicate check
      if echo "$seen_names" | grep -qF "|$current_name|"; then
        echo "ERROR: Duplicate package name: $current_name"
        errors=$((errors + 1))
      fi
      seen_names="${seen_names}|$current_name|"
      continue
    fi

    echo "$line" | grep -qE '^\s+version:' && has_version=true
    echo "$line" | grep -qE '^\s+description:' && has_desc=true
    echo "$line" | grep -qE '^\s+path:' && has_path=true
    echo "$line" | grep -qE '^\s+repo:' && has_repo=true
  done < "$INDEX_FILE"

  # Validate last entry
  if [ "$in_entry" = true ]; then
    if [ "$has_name" = false ]; then echo "ERROR: Entry $entry_num missing name"; errors=$((errors + 1)); fi
    if [ "$has_version" = false ]; then echo "ERROR: Entry $entry_num ($current_name) missing version"; errors=$((errors + 1)); fi
    if [ "$has_desc" = false ]; then echo "ERROR: Entry $entry_num ($current_name) missing description"; errors=$((errors + 1)); fi
    if [ "$has_path" = false ]; then echo "ERROR: Entry $entry_num ($current_name) missing path"; errors=$((errors + 1)); fi
    if [ "$has_repo" = false ]; then echo "ERROR: Entry $entry_num ($current_name) missing repo"; errors=$((errors + 1)); fi
  fi
}

echo "Validating COS package index: $INDEX_FILE"
echo ""

if [ "$USE_YQ" = true ]; then
  validate_with_yq
else
  validate_with_grep
fi

echo ""
echo "Packages: $count"
echo "Errors:   $errors"
echo "Warnings: $warnings"

if [ "$errors" -gt 0 ]; then
  echo ""
  echo "VALIDATION FAILED"
  exit 1
fi

echo ""
echo "VALIDATION PASSED"
exit 0
