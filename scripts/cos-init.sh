#!/usr/bin/env bash
# SCOPE: os-only
# cos init — Bootstrap Cognitive OS in any project
# Usage: bash /path/to/luum-agent-os/scripts/cos-init.sh [--default|--full]
#
# ADR-002 collapsed the 3-tier profile system to 2 tiers:
#   --default (canonical) — 10 curated core skills, ~29 standard hooks, 14 core rules
#   --full                — everything
# Legacy flags (--minimal, --standard, --lean) are silently remapped to --default.
#
# Bash 3.x compatible (no associative arrays, no bash 4+ features).
# Author: luum
set -euo pipefail

# ── Resolve COS source directory ────────────────────────────────────
COS_SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RAW_MODE="${1:---default}"
PROJECT_DIR="$(pwd)"
VERSION_FILE="$COS_SOURCE_DIR/VERSION"

# ── Self-hosting guard ──────────────────────────────────────────────
# If running inside luum-agent-os itself, refuse (use self-install.sh instead).
if [ -f "$PROJECT_DIR/hooks/self-install.sh" ] && [ "$PROJECT_DIR" = "$COS_SOURCE_DIR" ]; then
  echo "Error: Cannot run cos-init inside luum-agent-os itself." >&2
  echo "       This repo uses self-install.sh for self-hosting." >&2
  exit 1
fi

# ── Mode validation + ADR-002 legacy remap ──────────────────────────
# Canonical profiles (ADR-002): --default, --full.
# Legacy values (--minimal, --standard, --lean) are silently remapped to --default
# with a stderr migration note. install.sh also normalizes at the entry point, so
# the rejection/remap path here protects direct users of cos-init.sh.
case "$RAW_MODE" in
  --default|--full)
    MODE="$RAW_MODE"
    ;;
  --minimal|--standard|--lean)
    echo "Note: ADR-002 collapsed '${RAW_MODE}' into '--default'. Using '--default'." >&2
    MODE="--default"
    ;;
  *)
    echo "Usage: bash $0 [--default|--full]" >&2
    echo "" >&2
    echo "  --default  10 curated skills, ~29 standard hooks, 14 core rules (~8K tokens/session)" >&2
    echo "  --full     Everything (~142K tokens/session)" >&2
    echo "" >&2
    echo "  Legacy (remapped to --default): --minimal, --standard, --lean" >&2
    exit 1
    ;;
esac

# ── Scope filter (A2) ───────────────────────────────────────────────
# INSTALL_SCOPE controls which SCOPE-tagged files are copied.
# Values: project (default for user projects), both (alias), all (os-only included).
# Files with no SCOPE header are always included (untagged = universal).
INSTALL_SCOPE="${COS_INSTALL_SCOPE:-both}"
case "$INSTALL_SCOPE" in
  project|both|all) ;;
  *)
    echo "Warning: unknown COS_INSTALL_SCOPE='$INSTALL_SCOPE' → treating as 'both'." >&2
    INSTALL_SCOPE="both"
    ;;
esac

# scope_allows FILE → returns 0 (allow) or 1 (skip)
scope_allows() {
  local f="$1"
  [ -f "$f" ] || return 0  # non-files always pass

  # If scope is "all", never filter
  [ "$INSTALL_SCOPE" = "all" ] && return 0

  # Extract SCOPE header (first 3 lines only — fast)
  local scope_val
  scope_val=$(head -3 "$f" 2>/dev/null | grep -m1 -oE '(# SCOPE:|<!-- SCOPE:) [a-zA-Z_/-]+' | awk '{print $NF}' | tr -d ' ' | head -1 || true)

  # No SCOPE header → include unconditionally
  [ -z "$scope_val" ] && return 0

  # project/both scopes: allow "project" or "both", block "os-only"
  case "$scope_val" in
    project|both) return 0 ;;
    os-only)      return 1 ;;
    *)            return 0 ;;  # unknown tag → include
  esac
}

echo "=== Cognitive OS Init ($MODE) ==="
echo "Scope filter: $INSTALL_SCOPE"
echo ""

# ── 1. Detect existing project stack ────────────────────────────────
detected_stack=""
has_claude_dir=false
has_docker=false
project_name=""

# Detect project name
if [ -f "package.json" ] && command -v jq >/dev/null 2>&1; then
  project_name=$(jq -r '.name // empty' package.json 2>/dev/null || true)
fi
if [ -z "$project_name" ] && [ -f "go.mod" ]; then
  project_name=$(head -1 go.mod | sed 's/module //' | sed 's|.*/||' || true)
fi
if [ -z "$project_name" ] && [ -f "pyproject.toml" ]; then
  project_name=$(grep '^name' pyproject.toml 2>/dev/null | head -1 | sed 's/.*= *"//' | sed 's/".*//' || true)
fi
if [ -z "$project_name" ]; then
  project_name=$(basename "$PROJECT_DIR")
fi

# Detect stack
if [ -f "package.json" ]; then
  detected_stack="${detected_stack:+$detected_stack, }node"
fi
if [ -f "go.mod" ]; then
  detected_stack="${detected_stack:+$detected_stack, }go"
fi
if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ]; then
  detected_stack="${detected_stack:+$detected_stack, }python"
fi
if [ -f "Cargo.toml" ]; then
  detected_stack="${detected_stack:+$detected_stack, }rust"
fi
if [ -f "pom.xml" ] || [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
  detected_stack="${detected_stack:+$detected_stack, }java"
fi

if [ -d ".claude" ]; then
  has_claude_dir=true
fi
if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ] || [ -f "compose.yml" ]; then
  has_docker=true
fi

echo "Project: $project_name"
if [ -n "$detected_stack" ]; then
  echo "Stack:   $detected_stack"
fi
if [ "$has_docker" = "true" ]; then
  echo "Docker:  detected"
fi
if [ "$has_claude_dir" = "true" ]; then
  echo "Claude:  existing .claude/ found (will merge)"
fi
echo ""

# ── 2. Define mode components (ADR-002: default + full) ─────────────

# DEFAULT_RULES: the 14 core rules (matches self-install.sh CORE_RULES +
# 2 extras kept for parity with the previous "standard" tier docs).
DEFAULT_RULES="trust-score acceptance-criteria closed-loop-prompts definition-of-done
  agent-quality adaptive-bypass phase-aware-agents token-economy
  responsiveness credential-management content-policy error-learning
  model-routing result-management"

# DEFAULT_HOOKS: the standard hook set (~29 hooks) — rate-limiter,
# agent-prelaunch, auto-verify, auto-refine, dod-gate, session-sanity, etc.
DEFAULT_HOOKS="error-learning error-pipeline result-truncator session-init session-cleanup
  clarification-gate blast-radius scope-proportionality
  error-pattern-detector auto-refine auto-verify completeness-check dod-gate
  trust-score-validator skill-metrics-tracker inject-phase-context stack-detector
  pre-compaction-flush rate-limiter large-file-advisor secret-detector content-policy
  doc-sync-detector auto-checkpoint claim-validator completion-gate
  clarification-interceptor agent-checkpoint session-sanity confidentiality-enforcer
  session-learning crash-recovery teammate-idle task-created task-completed"

# DEFAULT_SKILLS: the 10 curated "vanilla value" skills from ADR-002.
# These deliver the core primitives an orchestrator needs on first run.
DEFAULT_SKILLS="compose-prompt exhaustive-prompt agent-dashboard auto-refine
  verification-before-completion plan-feature session-backlog resource-governor
  paperclip-dashboard cos-status"

# Full: everything available
# (will copy all rules, all hooks, all skills)

# ── 3. Create directory structure ──────────────────────────────────

# SAFETY: if .cognitive-os or .claude is a symlink (e.g. pointing to COS source),
# mkdir -p would follow the symlink and create dirs inside the source repo.
# This is a known misconfiguration — fix it by replacing the symlink.
for dir_check in ".cognitive-os" ".claude"; do
  if [ -L "$dir_check" ]; then
    echo "WARNING: $dir_check is a symlink ($(readlink "$dir_check")) — replacing with real directory"
    rm "$dir_check"
  fi
done

mkdir -p .claude/rules/cos
mkdir -p .claude/commands
mkdir -p .cognitive-os/hooks/cos
mkdir -p .cognitive-os/skills/cos
mkdir -p .cognitive-os/templates/cos
mkdir -p .cognitive-os/metrics
mkdir -p .cognitive-os/sessions
mkdir -p .cognitive-os/tasks

# ── 4. Install rules ──────────────────────────────────────────────
rules_installed=0
rules_source="$COS_SOURCE_DIR/rules"

install_rule() {
  local name="$1"
  local src="$rules_source/${name}.md"
  if [ -f "$src" ]; then
    cp "$src" ".claude/rules/cos/${name}.md"
    rules_installed=$((rules_installed + 1))
  fi
}

if [ "$MODE" = "--full" ]; then
  # Install all rules (respecting scope filter)
  for rule in "$rules_source"/*.md; do
    [ -f "$rule" ] || continue
    scope_allows "$rule" || continue
    cp "$rule" ".claude/rules/cos/$(basename "$rule")"
    rules_installed=$((rules_installed + 1))
  done
else
  # Default mode: install the 14 core rules (ADR-002).
  for name in $DEFAULT_RULES; do
    install_rule "$name"
  done
fi

# Always install RULES-COMPACT.md if it exists
if [ -f "$rules_source/RULES-COMPACT.md" ]; then
  cp "$rules_source/RULES-COMPACT.md" ".claude/rules/cos/RULES-COMPACT.md"
fi

# ── 5. Install hooks ─────────────────────────────────────────────
hooks_installed=0
hooks_source="$COS_SOURCE_DIR/hooks"
hooks_dest=".cognitive-os/hooks/cos"
mkdir -p "$hooks_dest"

install_hook() {
  local name="$1"
  local src="$hooks_source/${name}.sh"
  if [ -f "$src" ]; then
    cp "$src" "$hooks_dest/${name}.sh"
    chmod +x "$hooks_dest/${name}.sh"
    hooks_installed=$((hooks_installed + 1))
  fi
}

if [ "$MODE" = "--full" ]; then
  for hook in "$hooks_source"/*.sh; do
    [ -f "$hook" ] || continue
    scope_allows "$hook" || continue
    cp "$hook" "$hooks_dest/$(basename "$hook")"
    chmod +x "$hooks_dest/$(basename "$hook")"
    hooks_installed=$((hooks_installed + 1))
  done
  # Copy hook libs if they exist
  if [ -d "$hooks_source/_lib" ]; then
    cp -r "$hooks_source/_lib" "$hooks_dest/_lib"
  fi
else
  # Default mode: the standard hook set (~29 hooks, ADR-002).
  for name in $DEFAULT_HOOKS; do
    install_hook "$name"
  done
  # Always copy _lib if it exists (hooks depend on it)
  if [ -d "$hooks_source/_lib" ]; then
    cp -r "$hooks_source/_lib" "$hooks_dest/_lib"
  fi
fi

# ── 6. Install skills (both default and full tiers — ADR-002) ─────
# Skills are installed to BOTH destinations with DIFFERENT layouts (see ADR-001):
#   .cognitive-os/skills/cos/<name>/  → vendor-agnostic kernel path, namespaced under `cos/` to
#                                       avoid collision when multiple OS sources populate this path
#   .claude/skills/<name>/            → Claude Code harness driver path, FLAT layout
#                                       (empirically verified by ADR-001 Experiment 1 that the
#                                       harness reads {project}/.claude/skills/<name>/SKILL.md;
#                                       the nested `cos/` wrapper would hide skills from discovery)
# Only driver-path skills count toward skills_installed (that is what the harness sees).
skills_installed=0
skills_source="$COS_SOURCE_DIR/skills"
SKILL_DEST_KERNEL=".cognitive-os/skills/cos"
SKILL_DEST_DRIVER=".claude/skills"
SKILL_DESTS=("$SKILL_DEST_KERNEL" "$SKILL_DEST_DRIVER")

if [ -d "$skills_source" ]; then
  for skills_dest in "${SKILL_DESTS[@]}"; do
    mkdir -p "$skills_dest"

    if [ "$MODE" = "--full" ]; then
      # Install all skills
      for skill_dir in "$skills_source"/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name=$(basename "$skill_dir")
        cp -r "$skill_dir" "$skills_dest/$skill_name"
        [ "$skills_dest" = "$SKILL_DEST_DRIVER" ] && skills_installed=$((skills_installed + 1))
      done
      # Copy CATALOG.md if exists
      if [ -f "$skills_source/CATALOG.md" ]; then
        cp "$skills_source/CATALOG.md" "$skills_dest/CATALOG.md"
      fi
    else
      # Default: install the 10 curated core skills (ADR-002).
      for name in $DEFAULT_SKILLS; do
        if [ -d "$skills_source/$name" ]; then
          cp -r "$skills_source/$name" "$skills_dest/$name"
          [ "$skills_dest" = "$SKILL_DEST_DRIVER" ] && skills_installed=$((skills_installed + 1))
        fi
      done
      if [ -f "$skills_source/CATALOG.md" ]; then
        cp "$skills_source/CATALOG.md" "$skills_dest/CATALOG.md"
      fi
    fi
  done
fi

# ── 7. Install templates (both default and full tiers) ──────────
if [ -d "$COS_SOURCE_DIR/templates" ]; then
  mkdir -p .cognitive-os/templates/cos
  for tmpl in "$COS_SOURCE_DIR/templates"/*.md; do
    [ -f "$tmpl" ] || continue
    cp "$tmpl" ".cognitive-os/templates/cos/$(basename "$tmpl")"
  done
fi

# ── 8. Create cognitive-os.yaml ──────────────────────────────────
if [ ! -f "cognitive-os.yaml" ]; then
  # Build stack list for YAML
  yaml_stack=""
  for s in $detected_stack; do
    s_clean=$(echo "$s" | tr -d ',')
    yaml_stack="${yaml_stack}      - ${s_clean}\n"
  done

  cat > cognitive-os.yaml << ENDYAML
# Cognitive OS Configuration — generated by cos-init ($MODE)
project:
  name: $project_name
  phase: reconstruction
  stack:
$(echo -e "$yaml_stack" | sed '/^$/d')

sessions:
  concurrency: true
  isolation: per-session
  lock_strategy: advisory
  lock_timeout_seconds: 300
  cleanup_on_exit: true

models:
  routing:
    default: sonnet
    design: opus
    implementation: sonnet
    debugging: opus
    documentation: haiku

quality:
  coverage:
    minimum: 80
  auto_verify: true
  verification_retries: 3

resources:
  budget:
    monthly_limit_usd: 200
    daily_alert_usd: 10
    per_agent_max_usd: 2.00

model_capability:
  level: 3
ENDYAML
  echo "Created cognitive-os.yaml"
else
  echo "Existing cognitive-os.yaml preserved"
fi

# ── 8b. Apply efficiency profile filtering (ADR-002) ─────────────────
# After rules are installed AND cognitive-os.yaml exists, re-apply the
# profile filter from cognitive-os.yaml. ADR-002 collapsed to 2 tiers
# (default + full); legacy values (lean/standard/minimal) map to default.
EFFICIENCY_PROFILE="default"
if [ -f "cognitive-os.yaml" ]; then
  _ep=$(grep -A1 '^efficiency:' cognitive-os.yaml 2>/dev/null | grep 'profile:' | awk '{print $2}' | tr -d "'\"\r" || true)
  case "$_ep" in
    default|full)     EFFICIENCY_PROFILE="$_ep" ;;
    lean|standard|minimal|"")
      [ -n "$_ep" ] && echo "Note: cognitive-os.yaml efficiency.profile='$_ep' → 'default' (ADR-002)." >&2
      EFFICIENCY_PROFILE="default"
      ;;
    *)
      echo "Warning: unknown efficiency.profile='$_ep' in cognitive-os.yaml → treating as 'default'." >&2
      EFFICIENCY_PROFILE="default"
      ;;
  esac
fi

# Core rules for the default profile (14 rules — must stay in sync with
# self-install.sh CORE_RULES and ADR-002 rule set).
COS_INIT_CORE_RULES=(
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

RULES_DIR=".claude/rules/cos"
if [ -d "$RULES_DIR" ] && [ "$EFFICIENCY_PROFILE" = "default" ]; then
  # Keep only core rules (default tier).
  for rule in "$RULES_DIR"/*.md; do
    [ -f "$rule" ] || continue
    base=$(basename "$rule")
    is_core=false
    for core in "${COS_INIT_CORE_RULES[@]}"; do
      [ "$base" = "$core" ] && is_core=true && break
    done
    [ "$is_core" = false ] && rm -f "$rule"
  done
  # Recount
  rules_installed=0
  for rule in "$RULES_DIR"/*.md; do
    [ -f "$rule" ] && rules_installed=$((rules_installed + 1))
  done
fi
# full profile: keep everything (no filtering)

# ── 9. Create/merge .claude/settings.json ─────────────────────────
# Generate a project-appropriate settings.json with correct hook paths.
# Self-hosting hooks (self-install.sh, release-guard.sh) are excluded.
# Hook paths use .cognitive-os/hooks/cos/ (not hooks/ which is COS source layout).
GENERATOR="$COS_SOURCE_DIR/scripts/generate-project-settings.sh"
if [ -f "$GENERATOR" ] && command -v jq >/dev/null 2>&1; then
  generated_tmp=$(mktemp)
  if bash "$GENERATOR" "$MODE" --output="$generated_tmp" 2>/dev/null; then
    if [ -f ".claude/settings.json" ]; then
      # Merge: keep project hooks, replace COS hooks
      if [ -f "$COS_SOURCE_DIR/scripts/merge-settings.sh" ]; then
        merged_tmp=$(mktemp)
        bash "$COS_SOURCE_DIR/scripts/merge-settings.sh" ".claude/settings.json" "$generated_tmp" "$merged_tmp" 2>/dev/null && \
          mv "$merged_tmp" ".claude/settings.json" && \
          echo "Merged COS hooks into existing .claude/settings.json" || \
          echo "Warning: Could not merge settings. Your .claude/settings.json preserved."
        rm -f "$merged_tmp"
      else
        echo "Warning: merge-settings.sh not found. Your .claude/settings.json preserved."
      fi
    else
      mv "$generated_tmp" ".claude/settings.json"
      echo "Created .claude/settings.json with project-appropriate hook paths"
    fi
  else
    echo "Warning: generate-project-settings.sh failed. Falling back to copy."
    cp "$COS_SOURCE_DIR/.claude/settings.json" ".claude/settings.json" 2>/dev/null || true
  fi
  rm -f "$generated_tmp"
else
  # No generator or no jq — fallback to direct copy
  if [ -f "$COS_SOURCE_DIR/.claude/settings.json" ] && [ ! -f ".claude/settings.json" ]; then
    cp "$COS_SOURCE_DIR/.claude/settings.json" ".claude/settings.json"
    echo "Warning: Created settings.json without path transformation (jq missing)"
  fi
fi

# ── 10. Save install metadata ────────────────────────────────────
# COS_ORIGINAL_SOURCE is set by install.sh to the real repo path (not the temp copy).
# If not set, fall back to COS_SOURCE_DIR (direct cos-init.sh invocation).
REGISTRY_SOURCE="${COS_ORIGINAL_SOURCE:-$COS_SOURCE_DIR}"

cos_version="unknown"
# Try git tag first (most accurate), then VERSION file, then short SHA
_ver_dir="${REGISTRY_SOURCE:-$COS_SOURCE_DIR}"
if [ -d "$_ver_dir/.git" ]; then
  cos_version=$(cd "$_ver_dir" && git describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || true)
fi
if [ -z "$cos_version" ] || [ "$cos_version" = "unknown" ]; then
  if [ -f "$VERSION_FILE" ]; then
    cos_version=$(tr -d '[:space:]' < "$VERSION_FILE")
  elif [ -d "$_ver_dir/.git" ]; then
    cos_version=$(cd "$_ver_dir" && git rev-parse --short HEAD 2>/dev/null || echo "dev")
  fi
fi

cat > .cognitive-os/install-meta.json << ENDJSON
{
  "mode": "${MODE#--}",
  "version": "$cos_version",
  "source": "$REGISTRY_SOURCE",
  "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project_name": "$project_name",
  "rules_installed": $rules_installed,
  "hooks_installed": $hooks_installed,
  "skills_installed": $skills_installed
}
ENDJSON

# ── 11. Register in global COS installations registry ───────────
REGISTRY_SCRIPT="$COS_SOURCE_DIR/scripts/cos-registry.sh"
if [ -f "$REGISTRY_SCRIPT" ] && command -v jq >/dev/null 2>&1; then
  source "$REGISTRY_SCRIPT"
  cos_registry_register "$PROJECT_DIR" "${MODE#--}" "$cos_version" "$project_name" "$REGISTRY_SOURCE"
fi

# ── 12. Add to .gitignore ────────────────────────────────────────
# Ensure all COS runtime paths are ignored in the project's .gitignore.
# This runs on both install AND update (--force), so new patterns are
# added incrementally without duplicating existing entries.

COS_GITIGNORE_PATTERNS=(
  "# Cognitive OS runtime (not committed)"
  ".cognitive-os/sessions/"
  ".cognitive-os/metrics/"
  ".cognitive-os/tasks/"
  ".cognitive-os/checkpoints/"
  ".cognitive-os/dynamic-tools/"
  ".cognitive-os/rate-limit-state.json"
  ".cognitive-os/install-meta.json"
  ""
  "# Cognitive OS local settings"
  ".claude/settings.local.json"
)

if [ -f ".gitignore" ]; then
  for pattern in "${COS_GITIGNORE_PATTERNS[@]}"; do
    # Skip comments and empty lines if they don't need dedup
    if [ -z "$pattern" ] || [[ "$pattern" == \#* ]]; then
      # Add comment/blank only if the NEXT functional pattern is missing
      continue
    fi
    if ! grep -qF "$pattern" .gitignore 2>/dev/null; then
      echo "$pattern" >> .gitignore
    fi
  done
else
  {
    for pattern in "${COS_GITIGNORE_PATTERNS[@]}"; do
      echo "$pattern"
    done
  } > .gitignore
fi

# ── Summary ──────────────────────────────────────────────────────
echo ""
echo "Cognitive OS initialized (${MODE#--} mode)"
echo "  Rules:  $rules_installed installed"
echo "  Hooks:  $hooks_installed registered"
echo "  Skills: $skills_installed available"
echo ""
echo "Next: start coding! The AI knows what to do."
echo ""
if [ "$MODE" = "--default" ]; then
  echo "Need maximum coverage? Re-run with --full:"
  echo "  bash $COS_SOURCE_DIR/scripts/cos-init.sh --full"
fi
