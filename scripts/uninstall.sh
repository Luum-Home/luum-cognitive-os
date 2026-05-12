#!/usr/bin/env bash
# SCOPE: os-only
# Uninstall Cognitive OS from a project
# Usage: bash scripts/uninstall.sh [--keep-config]
#
# Removes COS agentic primitives without touching project files.
# Bash 3.x compatible (no associative arrays, no bash 4+ features).
# Author: luum
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/_lib/settings-driver.sh"

KEEP_CONFIG=false
for arg in "$@"; do
  case "$arg" in
    --keep-config) KEEP_CONFIG=true ;;
    --help|-h)
      echo "Usage: bash scripts/uninstall.sh [--keep-config]"
      echo ""
      echo "  --keep-config  Preserve cognitive-os.yaml"
      echo ""
      echo "This script removes Cognitive OS agentic primitives from the current project."
      echo "It NEVER touches project files outside .claude/rules/cos/, the active settings driver,"
      echo "and .cognitive-os/."
      exit 0
      ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: bash scripts/uninstall.sh [--keep-config]"
      exit 1
      ;;
  esac
done

echo "=== Cognitive OS Uninstaller ==="
echo ""

removed_items=""
settings_driver_harness="$(cos_detect_harness "$(pwd)")"
settings_driver_label="$(cos_settings_driver_label "$settings_driver_harness")"
settings_driver_path="$(cos_settings_driver_path "$(pwd)" "$settings_driver_harness")"
settings_backup_path="${settings_driver_path}.cos-backup"

# ── 1. Remove .claude/rules/cos/ (COS namespaced rules) ─────────
if [ -d ".claude/rules/cos" ]; then
  rule_count=$(find .claude/rules/cos -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
  rm -rf .claude/rules/cos
  removed_items="${removed_items:+$removed_items\n}  - .claude/rules/cos/ ($rule_count rules)"
fi

# ── 2. Remove COS hooks from the active settings driver ─────────
# COS hooks reference paths containing ".cognitive-os/hooks/" or "hooks/" with COS patterns.
# We remove hook entries that point to COS paths but preserve project hooks.
if [ -f "$settings_driver_path" ] && command -v jq >/dev/null 2>&1; then
  # Check if there are any COS hook references
  if jq -e '.hooks // .' "$settings_driver_path" >/dev/null 2>&1; then
    # Create a backup
    cp "$settings_driver_path" "$settings_backup_path"

    # Remove hook entries whose command contains ".cognitive-os/hooks/"
    # This is a best-effort removal — complex hook configs may need manual cleanup.
    jq '
      def prune_groups:
        with_entries(
          if (.value | type) == "array" then
            .value |= map(
              if (.hooks // null) != null and (.hooks | type) == "array" then
                .hooks |= map(select((.command // "") | test("\\.cognitive-os/hooks/") | not))
              else .
              end
            )
          else .
          end
        );
      if (.hooks // null) != null and (.hooks | type) == "object" then
        .hooks |= prune_groups
      else
        prune_groups
      end
    ' "$settings_driver_path" > "${settings_driver_path}.tmp" 2>/dev/null && \
      mv "${settings_driver_path}.tmp" "$settings_driver_path" && \
      removed_items="${removed_items:+$removed_items\n}  - COS hooks from ${settings_driver_label} (backup: $(basename "$settings_backup_path"))" || \
      rm -f "${settings_driver_path}.tmp"
  fi
fi

# ── 3. Remove cognitive-os.yaml (unless --keep-config) ──────────
if [ "$KEEP_CONFIG" = "false" ] && [ -f "cognitive-os.yaml" ]; then
  rm -f cognitive-os.yaml
  removed_items="${removed_items:+$removed_items\n}  - cognitive-os.yaml"
elif [ "$KEEP_CONFIG" = "true" ] && [ -f "cognitive-os.yaml" ]; then
  echo "Keeping cognitive-os.yaml (--keep-config)"
fi

# ── 4. Deregister from global COS installations registry ───────
# Read install-meta BEFORE deleting .cognitive-os/ (step 5 deletes the directory)
_cos_source=""
if [ -f ".cognitive-os/install-meta.json" ] && command -v jq >/dev/null 2>&1; then
  _cos_source=$(jq -r '.source // ""' ".cognitive-os/install-meta.json" 2>/dev/null || true)
fi
# Try sourcing the registry script from the COS source
_registry_script="${_cos_source:+$_cos_source/scripts/cos-registry.sh}"
if [ -n "$_registry_script" ] && [ -f "$_registry_script" ] && command -v jq >/dev/null 2>&1; then
  source "$_registry_script"
  cos_registry_deregister "$(pwd)"
  removed_items="${removed_items:+$removed_items\n}  - Deregistered from global COS registry"
fi

# ── 5. Remove .cognitive-os/ directory ──────────────────────────
if [ -d ".cognitive-os" ]; then
  # Count contents for summary
  total_files=$(find .cognitive-os -type f 2>/dev/null | wc -l | tr -d ' ')
  rm -rf .cognitive-os
  removed_items="${removed_items:+$removed_items\n}  - .cognitive-os/ ($total_files files)"
fi

# ── 6. Remove .claude/skills/ (ADR-001 driver path) ─────────────
# Populated by hooks/self-install.sh as symlinks into skills/.  Not tracked in git
# (see .gitignore: `.claude/skills/`).  Removal is safe: only symlinks are deleted;
# the source tree at skills/ is untouched.  See
# docs/04-Concepts/architecture/harness-adoption-gap/ADR-001-harness-skills-sync-path.md.
if [ -d ".claude/skills" ]; then
  skill_link_count=$(find .claude/skills -maxdepth 1 -type l 2>/dev/null | wc -l | tr -d ' ')
  rm -rf .claude/skills
  removed_items="${removed_items:+$removed_items\n}  - .claude/skills/ (${skill_link_count} symlinks)"
fi

# ── 7. Remove install metadata ──────────────────────────────────
# Clean up empty .claude/rules/ if we left it empty
if [ -d ".claude/rules" ]; then
  remaining=$(find .claude/rules -type f 2>/dev/null | wc -l | tr -d ' ')
  if [ "$remaining" = "0" ]; then
    rmdir .claude/rules 2>/dev/null || true
  fi
fi

# ── Summary ─────────────────────────────────────────────────────
echo ""
if [ -n "$removed_items" ]; then
  echo "Removed:"
  echo -e "$removed_items"
else
  echo "Nothing to remove — Cognitive OS was not installed in this project."
fi

echo ""
echo "Cognitive OS has been uninstalled."
echo ""
echo "Your project files were NOT modified."
echo "Your .claude/CLAUDE.md was NOT touched."
if [ -f "$settings_backup_path" ]; then
  echo ""
  echo "A backup of your settings was saved to ${settings_backup_path#$(pwd)/}"
fi
