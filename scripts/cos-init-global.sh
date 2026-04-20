#!/usr/bin/env bash
# SCOPE: os-only
# cos-init-global.sh — Install universal COS rules to ~/.claude/rules/cos/
# These rules apply to ALL projects on this machine.
# Does NOT install hooks (they need project context via $CLAUDE_PROJECT_DIR).
#
# Usage: bash scripts/cos-init-global.sh [--dry-run]
#
# Bash 3.x compatible (no associative arrays, no bash 4+ features).
set -euo pipefail

COS_SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --help|-h)
      echo "Usage: bash $0 [--dry-run]"
      echo ""
      echo "Install universal COS rules to ~/.claude/rules/cos/."
      echo "These rules apply to ALL projects on this machine."
      echo ""
      echo "Options:"
      echo "  --dry-run   Show what would be installed without writing files"
      echo ""
      echo "What gets installed:"
      echo "  ~/.claude/rules/cos/     14 core universal rules"
      echo ""
      echo "What does NOT get installed (requires project context):"
      echo "  Hooks (need \$CLAUDE_PROJECT_DIR)"
      echo "  cognitive-os.yaml (project-specific)"
      echo "  Phase-dependent rules (read from project config)"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: bash $0 [--dry-run]"
      exit 1
      ;;
  esac
done

GLOBAL_RULES_DIR="$HOME/.claude/rules/cos"

# The 14 core rules that are universal across all projects.
# These define COS behavioral protocol and apply regardless of project.
# Must match the CORE_RULES array in hooks/self-install.sh exactly.
# See docs/global-vs-project-config.md and docs/rules-loading-architecture.md.
CORE_RULES=(
  "RULES-COMPACT.md"
  "adaptive-bypass.md"
  "acceptance-criteria.md"
  "agent-quality.md"
  "trust-score.md"
  "definition-of-done.md"
  "phase-aware-agents.md"
  "closed-loop-prompts.md"
  "token-economy.md"
  "responsiveness.md"
  "agent-security.md"
  "credential-management.md"
  "content-policy.md"
  "error-learning.md"
)

echo "=== Cognitive OS Global Install ==="
echo ""
echo "Source: $COS_SOURCE_DIR/rules/"
echo "Target: $GLOBAL_RULES_DIR/"
echo ""

# Verify source rules exist
missing=0
for rule in "${CORE_RULES[@]}"; do
  if [ ! -f "$COS_SOURCE_DIR/rules/$rule" ]; then
    echo "WARNING: Source rule not found: rules/$rule"
    missing=$((missing + 1))
  fi
done

if [ "$missing" -gt 0 ]; then
  echo ""
  echo "WARNING: $missing rule(s) not found in $COS_SOURCE_DIR/rules/"
  echo "         Continuing with available rules."
  echo ""
fi

if [ "$DRY_RUN" = true ]; then
  echo "DRY RUN — would install:"
  for rule in "${CORE_RULES[@]}"; do
    if [ -f "$COS_SOURCE_DIR/rules/$rule" ]; then
      echo "  $GLOBAL_RULES_DIR/$rule"
    fi
  done
  echo ""
  echo "Total: ${#CORE_RULES[@]} rules"
  exit 0
fi

# Create target directory
mkdir -p "$GLOBAL_RULES_DIR"

# Install rules
installed=0
updated=0
skipped=0

for rule in "${CORE_RULES[@]}"; do
  src="$COS_SOURCE_DIR/rules/$rule"
  dst="$GLOBAL_RULES_DIR/$rule"

  if [ ! -f "$src" ]; then
    skipped=$((skipped + 1))
    continue
  fi

  if [ -f "$dst" ]; then
    # Check if content differs
    if diff -q "$src" "$dst" >/dev/null 2>&1; then
      skipped=$((skipped + 1))
      continue
    fi
    updated=$((updated + 1))
  else
    installed=$((installed + 1))
  fi

  cp "$src" "$dst"
done

# Save install metadata
META_DIR="$HOME/.cognitive-os"
mkdir -p "$META_DIR"

cos_version="unknown"
if [ -f "$COS_SOURCE_DIR/.cognitive-os/version" ]; then
  cos_version=$(cat "$COS_SOURCE_DIR/.cognitive-os/version")
elif [ -d "$COS_SOURCE_DIR/.git" ]; then
  cos_version=$(cd "$COS_SOURCE_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "dev")
fi

cat > "$META_DIR/global-install-meta.json" << ENDJSON
{
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "cos_version": "$cos_version",
  "cos_source": "$COS_SOURCE_DIR",
  "rules_dir": "$GLOBAL_RULES_DIR",
  "rules_count": $((installed + updated + skipped)),
  "rules_installed": $installed,
  "rules_updated": $updated,
  "rules_skipped": $skipped
}
ENDJSON

# Summary
echo "Installed ${installed} new rule(s) to $GLOBAL_RULES_DIR"
if [ "$updated" -gt 0 ]; then
  echo "Updated  ${updated} existing rule(s)"
fi
if [ "$skipped" -gt 0 ]; then
  echo "Skipped  ${skipped} unchanged rule(s)"
fi
echo ""
echo "Total: $((installed + updated + skipped)) / ${#CORE_RULES[@]} core rules"
echo ""
echo "These rules now apply to ALL projects on this machine."
echo "Project-specific rules (phase-aware, infrastructure) are installed per-project via 'cos setup'."
echo ""
echo "Metadata saved to: $META_DIR/global-install-meta.json"
