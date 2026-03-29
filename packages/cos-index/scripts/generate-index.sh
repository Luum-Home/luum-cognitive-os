#!/usr/bin/env bash
# generate-index.sh — Generate or refresh the COS package index from local packages/
# Scans packages/*/cos-package.yaml and produces index/packages.yaml.
# Usage: bash scripts/generate-index.sh [packages_dir] [output_file]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGES_DIR="${1:-$(cd "$SCRIPT_DIR/../../.." && pwd)/packages}"
OUTPUT_FILE="${2:-$SCRIPT_DIR/../index/packages.yaml}"

if [ ! -d "$PACKAGES_DIR" ]; then
  echo "ERROR: Packages directory not found: $PACKAGES_DIR"
  exit 1
fi

# Determine the repo name (best-effort from git remote or fallback)
REPO_NAME="Luum-Home/luum-agent-os"
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  remote_url=$(git remote get-url origin 2>/dev/null || true)
  if [ -n "$remote_url" ]; then
    # Extract owner/repo from various URL formats
    parsed=$(echo "$remote_url" | sed -E 's|.*[:/]([^/]+/[^/.]+)(\.git)?$|\1|')
    [ -n "$parsed" ] && REPO_NAME="$parsed"
  fi
fi

TODAY=$(date -u +%Y-%m-%d)

# Start writing the index
cat > "$OUTPUT_FILE" << EOF
# COS Package Index — Master Registry
# Generated from packages/ directory. Run scripts/generate-index.sh to refresh.
# Last updated: $TODAY

packages:
EOF

count=0
for pkg_yaml in "$PACKAGES_DIR"/*/cos-package.yaml; do
  [ -f "$pkg_yaml" ] || continue

  pkg_dir=$(dirname "$pkg_yaml")
  pkg_name_dir=$(basename "$pkg_dir")
  rel_path="packages/$pkg_name_dir"

  # Extract fields from cos-package.yaml
  name=$(grep '^name:' "$pkg_yaml" | head -1 | sed 's/^name: *//' | tr -d '"' | tr -d "'")
  version=$(grep '^version:' "$pkg_yaml" | head -1 | sed 's/^version: *//' | tr -d '"' | tr -d "'")
  description=$(grep '^description:' "$pkg_yaml" | head -1 | sed 's/^description: *//' | tr -d '"' | tr -d "'")

  # Extract keywords/tags (first 5)
  tags=""
  in_keywords=false
  while IFS= read -r line; do
    if echo "$line" | grep -qE '^keywords:'; then
      in_keywords=true
      # Handle inline array format: keywords: ["a", "b"]
      inline=$(echo "$line" | sed -n 's/.*\[\(.*\)\].*/\1/p' | tr -d '"' | tr -d "'" | tr ',' '\n' | head -5 | tr -d ' ' | tr '\n' ',' | sed 's/,$//')
      if [ -n "$inline" ]; then
        tags="$inline"
        break
      fi
      continue
    fi
    if [ "$in_keywords" = true ]; then
      if echo "$line" | grep -qE '^\s+-'; then
        tag=$(echo "$line" | sed 's/^\s*- *//' | tr -d '"' | tr -d "'")
        tags="${tags:+$tags, }$tag"
      else
        break
      fi
    fi
  done < "$pkg_yaml"

  # Skip if missing critical fields
  if [ -z "$name" ] || [ -z "$version" ]; then
    echo "WARNING: Skipping $pkg_name_dir — missing name or version"
    continue
  fi

  # Format tags as YAML list
  tags_yaml=""
  if [ -n "$tags" ]; then
    tags_yaml="[$(echo "$tags" | sed 's/, */, /g')]"
  else
    tags_yaml="[]"
  fi

  cat >> "$OUTPUT_FILE" << EOF
  - name: "$name"
    repo: "$REPO_NAME"
    path: "$rel_path"
    version: "$version"
    description: "$description"
    tags: $tags_yaml

EOF

  count=$((count + 1))
done

echo "Generated index with $count packages: $OUTPUT_FILE"
