#!/usr/bin/env bash
# auto-update-projects.sh — Update all COS installations after OS repo changes
#
# Reads the global registry of COS installations and re-syncs each project
# that was installed from THIS source directory. Designed to be called from
# the git post-merge hook or manually.
#
# Usage:
#   bash scripts/auto-update-projects.sh           # update all registered projects
#   bash scripts/auto-update-projects.sh --dry-run  # show what would be updated
#   bash scripts/auto-update-projects.sh --list     # list registered projects
#
# Registry location: ~/.cognitive-os/installations.json
# Bash 3.x compatible (no associative arrays, no bash 4+ features).
# Author: luum
set -euo pipefail

COS_SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
REGISTRY_FILE="${COS_REGISTRY_FILE:-$HOME/.cognitive-os/installations.json}"
DRY_RUN=false
LIST_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --list)    LIST_ONLY=true ;;
    --help|-h)
      echo "Usage: bash scripts/auto-update-projects.sh [--dry-run|--list]"
      echo ""
      echo "  --dry-run  Show what would be updated without making changes"
      echo "  --list     List all registered COS installations"
      echo ""
      echo "Updates all projects installed from this COS source directory."
      echo "Registry: $REGISTRY_FILE"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

# ── Ensure jq is available ─────────────────────────────────────────
if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required. Install jq and try again." >&2
  exit 1
fi

# ── Ensure registry exists ─────────────────────────────────────────
if [ ! -f "$REGISTRY_FILE" ]; then
  if [ "$LIST_ONLY" = true ]; then
    echo "No installations registered. Registry: $REGISTRY_FILE"
    exit 0
  fi
  echo "No installations registered (registry does not exist)."
  echo "Install COS in a project with: bash $COS_SOURCE_DIR/scripts/cos-init.sh"
  exit 0
fi

# ── Get current COS version ────────────────────────────────────────
# Prefer git tag (most accurate), then VERSION file, then short SHA
cos_version="unknown"
if [ -d "$COS_SOURCE_DIR/.git" ]; then
  cos_version=$(cd "$COS_SOURCE_DIR" && git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || true)
fi
if [ -z "$cos_version" ] || [ "$cos_version" = "unknown" ]; then
  if [ -f "$COS_SOURCE_DIR/VERSION" ]; then
    cos_version=$(tr -d '[:space:]' < "$COS_SOURCE_DIR/VERSION")
  elif [ -d "$COS_SOURCE_DIR/.git" ]; then
    cos_version=$(cd "$COS_SOURCE_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "dev")
  fi
fi

# ── List mode ──────────────────────────────────────────────────────
if [ "$LIST_ONLY" = true ]; then
  count=$(jq '.installations | length' "$REGISTRY_FILE" 2>/dev/null || echo 0)
  echo "=== Cognitive OS Installations ==="
  echo "Source: $COS_SOURCE_DIR (v$cos_version)"
  echo "Registry: $REGISTRY_FILE"
  echo "Total: $count"
  echo ""

  if [ "$count" -gt 0 ]; then
    jq -r '.installations[] | "  \(.project_name) (\(.mode))\n    Path: \(.path)\n    Version: \(.version)\n    Source: \(.source)\n    Installed: \(.installed_at)\n"' "$REGISTRY_FILE" 2>/dev/null
  fi
  exit 0
fi

# ── Filter installations from THIS source ──────────────────────────
# Only update projects installed from this exact COS source directory.
projects=$(jq -r --arg src "$COS_SOURCE_DIR" \
  '.installations[] | select(.source == $src) | .path' \
  "$REGISTRY_FILE" 2>/dev/null || true)

if [ -z "$projects" ]; then
  echo "No projects installed from $COS_SOURCE_DIR"
  exit 0
fi

# ── Count projects ─────────────────────────────────────────────────
project_count=0
while IFS= read -r _p; do
  project_count=$((project_count + 1))
done <<< "$projects"

echo "=== COS Auto-Update (v$cos_version) ==="
echo "Source: $COS_SOURCE_DIR"
echo "Projects to update: $project_count"
echo ""

# ── Update each project ───────────────────────────────────────────
updated=0
skipped=0
failed=0

while IFS= read -r project_path; do
  [ -n "$project_path" ] || continue

  project_name=$(jq -r --arg path "$project_path" \
    '.installations[] | select(.path == $path) | .project_name // "unknown"' \
    "$REGISTRY_FILE" 2>/dev/null || echo "unknown")
  project_mode=$(jq -r --arg path "$project_path" \
    '.installations[] | select(.path == $path) | .mode // "standard"' \
    "$REGISTRY_FILE" 2>/dev/null || echo "standard")
  project_version=$(jq -r --arg path "$project_path" \
    '.installations[] | select(.path == $path) | .version // "unknown"' \
    "$REGISTRY_FILE" 2>/dev/null || echo "unknown")

  # ── Check if project directory exists ───────────────────────────
  if [ ! -d "$project_path" ]; then
    echo "  SKIP $project_name — directory not found: $project_path"
    skipped=$((skipped + 1))
    continue
  fi

  # ── Check if already up to date ────────────────────────────────
  if [ "$project_version" = "$cos_version" ] && [ "$DRY_RUN" = false ]; then
    echo "  OK   $project_name — already at v$cos_version"
    skipped=$((skipped + 1))
    continue
  fi

  # ── Dry run mode ───────────────────────────────────────────────
  if [ "$DRY_RUN" = true ]; then
    echo "  WOULD UPDATE $project_name (v$project_version -> v$cos_version, mode: $project_mode)"
    echo "    Path: $project_path"
    updated=$((updated + 1))
    continue
  fi

  # ── Run the update ─────────────────────────────────────────────
  echo "  UPDATING $project_name (v$project_version -> v$cos_version, mode: $project_mode)..."

  (
    cd "$project_path" || { echo "    ERROR: cannot cd to $project_path"; exit 1; }

    # SAFETY: never run destructive ops on the COS source itself
    if [ "$(pwd -P)" = "$(cd "$COS_SOURCE_DIR" && pwd -P)" ]; then
      echo "    SKIPPED: project path is the COS source itself"
      exit 0
    fi

    # SAFETY: if .cognitive-os is a symlink (e.g. pointing to COS source),
    # rm -rf on subdirectories would follow the symlink and destroy the source.
    # Fix: replace the symlink with a real directory.
    if [ -L ".cognitive-os" ]; then
      symlink_target=$(readlink ".cognitive-os")
      echo "    WARNING: .cognitive-os is a symlink to $symlink_target — replacing with real directory"
      rm ".cognitive-os"
      mkdir -p ".cognitive-os"
    fi

    # Same check for .claude
    if [ -L ".claude" ]; then
      symlink_target=$(readlink ".claude")
      echo "    WARNING: .claude is a symlink to $symlink_target — replacing with real directory"
      rm ".claude"
      mkdir -p ".claude"
    fi

    # Remove ONLY COS-managed components (namespaced under cos/).
    # Project-specific hooks/skills/templates outside cos/ are preserved.
    [ -d ".claude/rules/cos" ] && rm -rf .claude/rules/cos
    [ -d ".cognitive-os/hooks/cos" ] && rm -rf .cognitive-os/hooks/cos
    [ -d ".cognitive-os/skills/cos" ] && rm -rf .cognitive-os/skills/cos
    [ -d ".cognitive-os/templates/cos" ] && rm -rf .cognitive-os/templates/cos

    # Migration: if old flat layout exists (no cos/ subfolder), clean it.
    # Detect by checking for install-meta.json which indicates a COS installation.
    if [ -f ".cognitive-os/install-meta.json" ]; then
      # Old layout: hooks directly in .cognitive-os/hooks/ (not namespaced)
      # Only clean if cos/ subfolder doesn't exist (hasn't been migrated yet)
      if [ -d ".cognitive-os/hooks" ] && [ ! -d ".cognitive-os/hooks/cos" ]; then
        rm -rf .cognitive-os/hooks
      fi
      if [ -d ".cognitive-os/skills" ] && [ ! -d ".cognitive-os/skills/cos" ]; then
        rm -rf .cognitive-os/skills
      fi
      if [ -d ".cognitive-os/templates" ] && [ ! -d ".cognitive-os/templates/cos" ]; then
        rm -rf .cognitive-os/templates
      fi
    fi

    # Re-run cos-init with original mode
    COS_SOURCE_DIR="$COS_SOURCE_DIR" bash "$COS_SOURCE_DIR/scripts/cos-init.sh" "--$project_mode" > /dev/null 2>&1
  )

  if [ $? -eq 0 ]; then
    echo "    Done."
    updated=$((updated + 1))
  else
    echo "    FAILED — manual upgrade may be needed."
    failed=$((failed + 1))
  fi

done <<< "$projects"

# ── Summary ───────────────────────────────────────────────────────
echo ""
if [ "$DRY_RUN" = true ]; then
  echo "Dry run complete. Would update $updated project(s)."
else
  echo "Update complete: $updated updated, $skipped skipped, $failed failed."
fi
