#!/usr/bin/env bash
# SCOPE: os-only
# Upgrade Cognitive OS to latest version
# Usage: bash scripts/upgrade.sh [--force] [--merge]
#
# Reads install metadata to determine the original mode, pulls latest source,
# and re-runs cos-init with the same mode.
# Bash 3.x compatible (no associative arrays, no bash 4+ features).
# Author: luum
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_lib/settings-driver.sh"

FORCE=false
ALLOW_MERGE=false
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=true ;;
    --merge) ALLOW_MERGE=true ;;
    --help|-h)
      echo "Usage: bash scripts/upgrade.sh [--force] [--merge]"
      echo ""
      echo "  --force  Skip confirmation prompt"
      echo "  --merge  Permit an explicit merge commit if the COS source diverged"
      echo ""
      echo "Upgrades Cognitive OS to the latest version while preserving your mode."
      exit 0
      ;;
    *)
      echo "Unknown option: $arg"
      exit 1
      ;;
  esac
done

echo "=== Cognitive OS Upgrade ==="
echo ""

# ── 1. Check current installation ──────────────────────────────
META_FILE=".cognitive-os/install-meta.json"

if [ ! -f "$META_FILE" ]; then
  echo "Error: Cognitive OS is not installed in this project."
  echo "       No install-meta.json found at $META_FILE"
  echo ""
  echo "To install, run: bash /path/to/luum-agent-os/scripts/cos-init.sh"
  exit 1
fi

# Read install metadata
if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required for upgrade. Install jq and try again."
  exit 1
fi

current_version=$(jq -r '.version // "unknown"' "$META_FILE")
current_mode=$(jq -r '.mode // "standard"' "$META_FILE")
source_dir=$(jq -r '.source // ""' "$META_FILE")
installed_at=$(jq -r '.installed_at // "unknown"' "$META_FILE")
active_harness="$(cos_detect_harness "$(pwd)")"

echo "Current installation:"
echo "  Version:  $current_version"
echo "  Mode:     $current_mode"
echo "  Harness:  $active_harness"
echo "  Source:   $source_dir"
echo "  Installed: $installed_at"
echo ""

# ── 2. Validate source directory ────────────────────────────────
if [ -z "$source_dir" ] || [ ! -d "$source_dir" ]; then
  echo "Error: Source directory not found: $source_dir"
  echo "       The original luum-agent-os source must be accessible for upgrade."
  echo ""
  echo "If the source moved, reinstall:"
  echo "  bash /new/path/to/luum-agent-os/scripts/cos-init.sh --$current_mode"
  exit 1
fi

# ── 3. Check for new version ────────────────────────────────────
latest_version="unknown"
if [ -f "$source_dir/.cognitive-os/version" ]; then
  latest_version=$(cat "$source_dir/.cognitive-os/version")
elif [ -d "$source_dir/.git" ]; then
  latest_version=$(cd "$source_dir" && git rev-parse --short HEAD 2>/dev/null || echo "dev")
fi

echo "Available version: $latest_version"

if [ "$current_version" = "$latest_version" ] && [ "$FORCE" = "false" ]; then
  echo ""
  echo "Already up to date."
  exit 0
fi

# ── 4. Safely sync latest if source is a git repo ───────────────
if [ -d "$source_dir/.git" ]; then
  echo ""
  echo "Synchronizing source with safe no-rebase policy..."
  sync_args=("--repo" "$source_dir")
  if [ "$ALLOW_MERGE" = true ]; then
    sync_args+=("--merge")
  fi
  if ! bash "$SCRIPT_DIR/cos-git-sync.sh" "${sync_args[@]}"; then
    echo ""
    echo "Error: Source synchronization blocked. No rebase was performed."
    echo "       Resolve manually or re-run upgrade with --merge to allow an explicit merge commit."
    exit 1
  fi
  echo ""

  # Re-check version after sync
  if [ -f "$source_dir/.cognitive-os/version" ]; then
    latest_version=$(cat "$source_dir/.cognitive-os/version")
  else
    latest_version=$(cd "$source_dir" && git rev-parse --short HEAD 2>/dev/null || echo "dev")
  fi
fi

# ── 5. Show what will change ────────────────────────────────────
echo "Upgrade plan:"
echo "  From:  $current_version"
echo "  To:    $latest_version"
echo "  Mode:  $current_mode"
echo "  Harness: $active_harness"
echo ""

# Count available components
if [ -d "$source_dir/rules" ]; then
  available_rules=$(find "$source_dir/rules" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
  echo "  Available rules: $available_rules"
fi
if [ -d "$source_dir/hooks" ]; then
  available_hooks=$(find "$source_dir/hooks" -maxdepth 1 -name '*.sh' | wc -l | tr -d ' ')
  echo "  Available hooks: $available_hooks"
fi
if [ -d "$source_dir/skills" ]; then
  available_skills=$(find "$source_dir/skills" -maxdepth 1 -type d | wc -l | tr -d ' ')
  available_skills=$((available_skills - 1))  # subtract the skills/ dir itself
  echo "  Available skills: $available_skills"
fi

# ── 6. Confirm ──────────────────────────────────────────────────
if [ "$FORCE" = "false" ] && [ -t 0 ]; then
  echo ""
  read -rp "Proceed with upgrade? (y/N): " confirm </dev/tty
  if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Aborted."
    exit 0
  fi
fi

# ── 7. Re-run cos-init with original mode ───────────────────────
echo ""
echo "Running cos-init --$current_mode ..."
echo ""

# Remove existing COS agentic primitives (but keep project files)
if [ -d ".claude/rules/cos" ]; then
  rm -rf .claude/rules/cos
fi
if [ -d ".cognitive-os/hooks" ]; then
  rm -rf .cognitive-os/hooks
fi
if [ -d ".cognitive-os/skills" ]; then
  rm -rf .cognitive-os/skills
fi
if [ -d ".cognitive-os/templates" ]; then
  rm -rf .cognitive-os/templates
fi

# Re-run init through the active harness projection
COGNITIVE_OS_PROJECT_DIR="$(pwd)" \
COGNITIVE_OS_HARNESS="$active_harness" \
  bash "$source_dir/scripts/cos-init.sh" "--$current_mode" "--harness=$active_harness"

# ── 8. Update global registry ──────────────────────────────────
REGISTRY_SCRIPT="$source_dir/scripts/cos-registry.sh"
if [ -f "$REGISTRY_SCRIPT" ] && command -v jq >/dev/null 2>&1; then
  source "$REGISTRY_SCRIPT"
  project_name_reg=$(jq -r '.project_name // "unknown"' "$META_FILE" 2>/dev/null || echo "unknown")
  cos_registry_register "$(pwd)" "$current_mode" "$latest_version" "$project_name_reg" "$source_dir"
fi

# ── 9. Run component-lint if available ──────────────────────────
if [ -f "$source_dir/scripts/component-lint.sh" ]; then
  echo ""
  echo "Running component lint..."
  bash "$source_dir/scripts/component-lint.sh" 2>/dev/null || \
    echo "Warning: Component lint reported issues (non-fatal)."
fi

# ── 10. Summary ─────────────────────────────────────────────────
echo ""
echo "Upgrade complete: $current_version -> $latest_version"
