#!/usr/bin/env bash
# SCOPE: os-only
# cos-project-registry-prune.sh — Remove stale entries from the COS project registry
#
# Checks each registered installation for two conditions:
#   1. The directory still exists
#   2. The directory contains a .cognitive-os/ folder (proof it's a real COS-managed project)
# Entries failing either check are removed.
#
# Usage:
#   bash scripts/cos-project-registry-prune.sh            # prune stale entries
#   bash scripts/cos-project-registry-prune.sh --dry-run  # show what would be removed
#
# Registry location: ~/.cognitive-os/installations.json (or $COS_REGISTRY_FILE)
# Bash 3.x compatible.
# Author: luum
set -euo pipefail

REGISTRY_FILE="${COS_REGISTRY_FILE:-$HOME/.cognitive-os/installations.json}"
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --help|-h)
      echo "Usage: bash scripts/cos-project-registry-prune.sh [--dry-run]"
      echo ""
      echo "  --dry-run  Show what would be removed without making changes"
      echo ""
      echo "Removes registry entries where the directory no longer exists or"
      echo "does not contain a .cognitive-os/ folder."
      echo "Registry: $REGISTRY_FILE"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

# ── Require jq ─────────────────────────────────────────────────────
if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required. Install jq and try again." >&2
  exit 1
fi

# ── Require registry ───────────────────────────────────────────────
if [ ! -f "$REGISTRY_FILE" ]; then
  echo "No registry file found at: $REGISTRY_FILE"
  exit 0
fi

total=$(jq '.installations | length' "$REGISTRY_FILE" 2>/dev/null || echo 0)
echo "=== COS Project Registry Prune ==="
echo "Registry: $REGISTRY_FILE"
echo "Total entries: $total"
echo ""

if [ "$total" -eq 0 ]; then
  echo "Registry is empty. Nothing to prune."
  exit 0
fi

# ── Collect paths to remove ────────────────────────────────────────
paths_to_remove=()
paths_to_keep=()

while IFS= read -r entry_path; do
  [ -n "$entry_path" ] || continue

  project_name=$(jq -r --arg p "$entry_path" \
    '.installations[] | select(.path == $p) | .project_name // "unknown"' \
    "$REGISTRY_FILE" 2>/dev/null || echo "unknown")

  reason=""
  if [ ! -d "$entry_path" ]; then
    reason="directory not found"
  elif [ ! -d "$entry_path/.cognitive-os" ]; then
    reason="no .cognitive-os/ folder (not a COS-managed project)"
  fi

  if [ -n "$reason" ]; then
    echo "  PRUNE  $project_name"
    echo "         Path: $entry_path"
    echo "         Reason: $reason"
    paths_to_remove+=("$entry_path")
  else
    paths_to_keep+=("$entry_path")
  fi
done < <(jq -r '.installations[].path' "$REGISTRY_FILE" 2>/dev/null || true)

pruned=${#paths_to_remove[@]}
kept=${#paths_to_keep[@]}

echo ""
echo "Would prune: $pruned  |  Would keep: $kept"

if [ "$pruned" -eq 0 ]; then
  echo "Nothing to prune."
  exit 0
fi

if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "Dry run complete. Run without --dry-run to apply."
  exit 0
fi

# ── Backup registry before writing ────────────────────────────────
timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="${REGISTRY_FILE}.bak-${timestamp}"
cp "$REGISTRY_FILE" "$backup_file"
echo ""
echo "Backup saved: $backup_file"

# ── Build jq filter to remove all stale paths in one pass ─────────
# Construct a jq select that keeps only entries whose path is in the keep list.
# We do this by removing paths in the prune list.
filter='.installations'
for p in "${paths_to_remove[@]}"; do
  filter="${filter} | map(select(.path != \"$p\"))"
done
filter="{installations: (${filter})}"

tmp=$(mktemp)
jq "$filter" "$REGISTRY_FILE" > "$tmp" && mv "$tmp" "$REGISTRY_FILE"
rm -f "$tmp"

new_total=$(jq '.installations | length' "$REGISTRY_FILE" 2>/dev/null || echo 0)
echo "Pruned $pruned entries. Registry now has $new_total entries."
