#!/usr/bin/env bash
# Self-Install Hook — Full framework auto-sync for self-hosted development
# Detects if running inside the luum-agent-os repo itself and syncs ALL components.
# Must complete in <1s. Idempotent and safe.
#
# Sync directories are auto-discovered: every entry in SYNC_DIRS is checked for
# existence at the project root.  Adding a new top-level directory (e.g. agents/)
# only requires adding one line to the SYNC_DIRS table below — no other changes.
#
# NOTE: rules/ is NOT in SYNC_DIRS. It is managed separately by sync_core_rules()
# which only symlinks the ~16 core rules instead of all 94, keeping session context
# overhead at ~21K tokens instead of ~94K tokens.
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

# ── Self-hosting detection ──────────────────────────────────────────────
# We are in the luum-agent-os repo if this very script exists relative to root.
if [ ! -f "$PROJECT_DIR/hooks/self-install.sh" ]; then
  exit 0
fi

added=0
removed=0
fixes=""

# ── Sync directory registry ──────────────────────────────────────────────
# FORMAT:  "src_dir|dest_base|strategy|pattern"
#   src_dir   — directory name under PROJECT_DIR
#   dest_base — destination root: "claude" (.claude/) or "cos" (.cognitive-os/)
#   strategy  — "flat" (files only) or "tree" (subdirs + top-level files)
#   pattern   — glob pattern for flat strategy (ignored for tree)
#
# To add a new directory, just append a line here.
# rules/ is intentionally excluded — managed by sync_core_rules() below.
SYNC_DIRS=(
  "skills|cos|tree|"
  "squads|cos|flat|*.yaml"
  "templates|cos|flat|*.md"
  "agents|cos|flat|*.md"
  "customizations|cos|flat|*.yaml"
  "docs|cos|tree|"
)

# ── Helper: resolve destination base path ─────────────────────────────
resolve_dest() {
  local base="$1" name="$2"
  case "$base" in
    claude)     echo "$PROJECT_DIR/.claude/$name" ;;
    claude_cos) echo "$PROJECT_DIR/.claude/$name/cos" ;;
    cos)        echo "$PROJECT_DIR/.cognitive-os/$name" ;;
    *)          echo "$PROJECT_DIR/$base/$name" ;;
  esac
}

# ── Helper: sync directory as flat symlinks ───────────────────────────
# Usage: sync_dir <src_dir> <dst_dir> <glob_pattern>
sync_dir() {
  local src="$1" dst="$2" pattern="$3"
  [ -d "$src" ] || return 0
  mkdir -p "$dst"

  # Remove stale symlinks
  for link in "$dst"/$pattern; do
    [ -L "$link" ] || continue
    if [ ! -e "$link" ]; then
      rm -f "$link"
      removed=$((removed + 1))
    fi
  done

  # Add missing symlinks
  for file in "$src"/$pattern; do
    [ -e "$file" ] || continue
    local base
    base=$(basename "$file")
    local link="$dst/$base"
    if [ ! -e "$link" ]; then
      ln -sf "$file" "$link"
      added=$((added + 1))
    fi
  done
}

# ── Helper: sync directory tree (subdirs + top-level files) ───────────
# Usage: sync_tree <src_dir> <dst_dir>
sync_tree() {
  local src="$1" dst="$2"
  [ -d "$src" ] || return 0
  mkdir -p "$dst"

  # Remove stale symlinks (broken symlinks to dirs/files that no longer exist)
  for link in "$dst"/*; do
    [ -L "$link" ] || continue
    if [ ! -e "$link" ]; then
      rm -f "$link"
      removed=$((removed + 1))
    fi
  done

  # Add missing symlinks for each subdirectory
  for dir in "$src"/*/; do
    [ -d "$dir" ] || continue
    local base
    base=$(basename "$dir")
    local link="$dst/$base"
    if [ ! -e "$link" ]; then
      ln -sf "$dir" "$link"
      added=$((added + 1))
    fi
  done

  # Sync top-level files (CATALOG.md, INDEX.md, README.md, etc.)
  for file in "$src"/*; do
    [ -f "$file" ] || continue
    local base
    base=$(basename "$file")
    local link="$dst/$base"
    if [ ! -e "$link" ]; then
      ln -sf "$file" "$link"
      added=$((added + 1))
    fi
  done
}

# ── Auto-sync all registered directories ─────────────────────────────
synced_dirs=()
for entry in "${SYNC_DIRS[@]}"; do
  IFS='|' read -r src_name dest_base strategy pattern <<< "$entry"
  src="$PROJECT_DIR/$src_name"
  [ -d "$src" ] || continue
  dst=$(resolve_dest "$dest_base" "$src_name")

  case "$strategy" in
    flat) sync_dir "$src" "$dst" "$pattern" ;;
    tree) sync_tree "$src" "$dst" ;;
  esac
  synced_dirs+=("$src_name")
done

# ── Core rules sync ──────────────────────────────────────────────────
# Only ~16 core rules are symlinked into .claude/rules/cos/ — NOT all 94.
# Loading all 94 rules costs ~93,700 tokens (~2,677% of the 3,500 token target).
# The 16 core rules cover all essential always-active governance hooks and
# protocols. All 94 rule files remain in rules/ as reference — only symlinks
# are managed here.
#
# Efficiency profile controls which subset is active:
#   lean     — RULES-COMPACT.md only
#   standard/full/self-hosting — the 16 CORE_RULES below
#
# See docs/rules-loading-architecture.md for the rationale.

CONFIG_FILE="$PROJECT_DIR/cognitive-os.yaml"
EFFICIENCY_PROFILE="standard"
if [ -f "$CONFIG_FILE" ]; then
  _ep=$(grep -A1 '^efficiency:' "$CONFIG_FILE" 2>/dev/null | grep 'profile:' | awk '{print $2}' | tr -d "'\"\r" || true)
  [ -n "$_ep" ] && EFFICIENCY_PROFILE="$_ep"
fi

CORE_RULES=(
  "RULES-COMPACT.md"
  "adaptive-bypass.md"
  "acceptance-criteria.md"
  "agent-quality.md"
  "trust-score.md"
  "token-economy.md"
  "phase-aware-agents.md"
  "closed-loop-prompts.md"
  "error-learning.md"
  "rate-limiting.md"
  "credential-management.md"
  "content-policy.md"
  "result-management.md"
  "blast-radius.md"
  "clarification-gate.md"
  "model-routing.md"
)

# Build the effective allowed-rules list based on profile
if [[ "$EFFICIENCY_PROFILE" == "lean" ]]; then
  ALLOWED_RULES=("RULES-COMPACT.md")
else
  ALLOWED_RULES=("${CORE_RULES[@]}")
fi

cos_rules_dir="$PROJECT_DIR/.claude/rules/cos"
mkdir -p "$cos_rules_dir"

# Add missing core-rule symlinks
for rule in "${ALLOWED_RULES[@]}"; do
  src="$PROJECT_DIR/rules/$rule"
  link="$cos_rules_dir/$rule"
  [ -f "$src" ] || continue
  if [ ! -e "$link" ]; then
    ln -sf "$src" "$link"
    added=$((added + 1))
  fi
done

# Remove symlinks that are NOT in the allowed list (stale or previously full set)
if [ -d "$cos_rules_dir" ]; then
  for link in "$cos_rules_dir"/*.md; do
    [ -L "$link" ] || continue
    base=$(basename "$link")
    # Check if broken (target gone)
    if [ ! -e "$link" ]; then
      rm -f "$link"
      removed=$((removed + 1))
      continue
    fi
    # Check if not in allowed list
    is_allowed=false
    for allowed in "${ALLOWED_RULES[@]}"; do
      if [ "$base" = "$allowed" ]; then
        is_allowed=true
        break
      fi
    done
    if [ "$is_allowed" = false ]; then
      rm -f "$link"
      removed=$((removed + 1))
    fi
  done
fi

# ── Migration: clean up old flat symlinks in .claude/rules/ ──────────
# Before namespacing, COS rules were symlinked flat into .claude/rules/.
# Now they go to .claude/rules/cos/. Remove old flat symlinks that point
# to our rules/ directory, but NEVER remove non-symlinks (project files).
old_rules_dir="$PROJECT_DIR/.claude/rules"
if [ -d "$old_rules_dir" ]; then
  for link in "$old_rules_dir"/*.md; do
    [ -L "$link" ] || continue
    target=$(readlink "$link" 2>/dev/null || true)
    # Check if symlink points into our rules/ directory (absolute or relative).
    # Relative symlinks like ../../rules/X.md may chain through to packages/,
    # so realpath would miss them.  Match both forms explicitly.
    case "$target" in
      "$PROJECT_DIR/rules/"* | ../../rules/*)
        rm -f "$link"
        removed=$((removed + 1))
        ;;
    esac
  done
fi

# ── Verify infrastructure ────────────────────────────────────────────
if [ ! -f "$PROJECT_DIR/.claude/settings.json" ]; then
  fixes="${fixes:+$fixes, }settings.json missing"
fi

if [ ! -f "$PROJECT_DIR/cognitive-os.yaml" ] && [ ! -f "$PROJECT_DIR/.cognitive-os/cognitive-os.yaml" ]; then
  fixes="${fixes:+$fixes, }cognitive-os.yaml missing"
fi

# ── Ensure runtime directories exist ─────────────────────────────────
for dir in sessions metrics tasks; do
  if [ ! -d "$PROJECT_DIR/.cognitive-os/$dir" ]; then
    mkdir -p "$PROJECT_DIR/.cognitive-os/$dir"
    fixes="${fixes:+$fixes, }created $dir dir"
  fi
done

# ── Counts for status ────────────────────────────────────────────────
rule_count=0;  [ -d "$PROJECT_DIR/.claude/rules/cos" ]      && rule_count=$(find "$PROJECT_DIR/.claude/rules/cos" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
hook_count=0;  [ -d "$PROJECT_DIR/hooks" ]                  && hook_count=$(find "$PROJECT_DIR/hooks" -maxdepth 1 -name '*.sh' | wc -l | tr -d ' ')
skill_count=0; [ -d "$PROJECT_DIR/.cognitive-os/skills" ]   && skill_count=$(find "$PROJECT_DIR/.cognitive-os/skills" -maxdepth 1 -type l | wc -l | tr -d ' ')
squad_count=0; [ -d "$PROJECT_DIR/.cognitive-os/squads" ]   && squad_count=$(find "$PROJECT_DIR/.cognitive-os/squads" -maxdepth 1 -name '*.yaml' | wc -l | tr -d ' ')
agent_count=0; [ -d "$PROJECT_DIR/.cognitive-os/agents" ]   && agent_count=$(find "$PROJECT_DIR/.cognitive-os/agents" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
doc_count=0;   [ -d "$PROJECT_DIR/.cognitive-os/docs" ]     && doc_count=$(find "$PROJECT_DIR/.cognitive-os/docs" -maxdepth 1 -type l | wc -l | tr -d ' ')

# ── Status output ────────────────────────────────────────────────────
status="${rule_count} rules, ${hook_count} hooks, ${skill_count} skills, ${squad_count} squads, ${agent_count} agents, ${doc_count} docs"

if [ "$added" -gt 0 ] || [ "$removed" -gt 0 ] || [ -n "$fixes" ]; then
  changes=""
  [ "$added" -gt 0 ] && changes="added $added"
  [ "$removed" -gt 0 ] && changes="${changes:+$changes, }removed $removed stale"
  [ -n "$fixes" ] && changes="${changes:+$changes, }$fixes"
  echo "Self-hosting: FIXED ($changes) | $status"
else
  echo "Self-hosting: OK ($status)"
fi

exit 0
