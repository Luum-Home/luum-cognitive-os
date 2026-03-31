#!/usr/bin/env bash
# cos init — Bootstrap Cognitive OS in any project
# Usage: bash /path/to/luum-agent-os/scripts/cos-init.sh [--minimal|--standard|--full]
#
# Bash 3.x compatible (no associative arrays, no bash 4+ features).
# Author: luum
set -euo pipefail

# ── Resolve COS source directory ────────────────────────────────────
COS_SOURCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:---standard}"
PROJECT_DIR="$(pwd)"
VERSION_FILE="$COS_SOURCE_DIR/.cognitive-os/version"

# ── Self-hosting guard ──────────────────────────────────────────────
# If running inside luum-agent-os itself, refuse (use self-install.sh instead).
if [ -f "$PROJECT_DIR/hooks/self-install.sh" ] && [ "$PROJECT_DIR" = "$COS_SOURCE_DIR" ]; then
  echo "Error: Cannot run cos-init inside luum-agent-os itself."
  echo "       This repo uses self-install.sh for self-hosting."
  exit 1
fi

# ── Mode validation ─────────────────────────────────────────────────
case "$MODE" in
  --minimal|--standard|--full)
    ;;
  *)
    echo "Usage: bash $0 [--minimal|--standard|--full]"
    echo ""
    echo "  --minimal   5 core rules, 3 hooks (~500 token overhead)"
    echo "  --standard  25 rules, 15 hooks, 10 skills (~2000 token overhead)"
    echo "  --full      Everything (~5000 token overhead)"
    exit 1
    ;;
esac

echo "=== Cognitive OS Init ($MODE) ==="
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

# ── 2. Define mode components ──────────────────────────────────────

# Minimal: 5 core rules
MINIMAL_RULES="trust-score acceptance-criteria closed-loop-prompts definition-of-done agent-quality"
MINIMAL_HOOKS="error-learning session-init session-cleanup"

# Standard: minimal + more rules and hooks
STANDARD_RULES="$MINIMAL_RULES phase-aware-agents model-routing context-management fault-tolerance
  error-learning result-management responsiveness credential-management license-policy
  agent-identity agent-kpis context-optimization plan-first prompt-composition
  skill-management resource-governance doc-sync sandbox-sampling blast-radius"
STANDARD_HOOKS="$MINIMAL_HOOKS clarification-gate blast-radius scope-proportionality
  error-pattern-detector auto-refine auto-verify completeness-check dod-gate
  trust-score-validator skill-metrics-tracker inject-phase-context stack-detector
  pre-compaction-flush"
STANDARD_SKILLS="sdd-explore sdd-propose sdd-spec sdd-design sdd-tasks sdd-apply
  sdd-verify plan-feature systematic-debugging verification-before-completion"

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
  # Install all rules
  for rule in "$rules_source"/*.md; do
    [ -f "$rule" ] || continue
    cp "$rule" ".claude/rules/cos/$(basename "$rule")"
    rules_installed=$((rules_installed + 1))
  done
else
  # Install mode-specific rules
  rules_list="$MINIMAL_RULES"
  if [ "$MODE" = "--standard" ]; then
    rules_list="$STANDARD_RULES"
  fi
  for name in $rules_list; do
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
    cp "$hook" "$hooks_dest/$(basename "$hook")"
    chmod +x "$hooks_dest/$(basename "$hook")"
    hooks_installed=$((hooks_installed + 1))
  done
  # Copy hook libs if they exist
  if [ -d "$hooks_source/_lib" ]; then
    cp -r "$hooks_source/_lib" "$hooks_dest/_lib"
  fi
else
  hooks_list="$MINIMAL_HOOKS"
  if [ "$MODE" = "--standard" ]; then
    hooks_list="$STANDARD_HOOKS"
  fi
  for name in $hooks_list; do
    install_hook "$name"
  done
  # Always copy _lib if it exists (hooks depend on it)
  if [ -d "$hooks_source/_lib" ]; then
    cp -r "$hooks_source/_lib" "$hooks_dest/_lib"
  fi
fi

# ── 6. Install skills (standard and full only) ───────────────────
skills_installed=0
skills_source="$COS_SOURCE_DIR/skills"
skills_dest=".cognitive-os/skills/cos"

if [ "$MODE" != "--minimal" ] && [ -d "$skills_source" ]; then
  mkdir -p "$skills_dest"

  if [ "$MODE" = "--full" ]; then
    # Install all skills
    for skill_dir in "$skills_source"/*/; do
      [ -d "$skill_dir" ] || continue
      skill_name=$(basename "$skill_dir")
      cp -r "$skill_dir" "$skills_dest/$skill_name"
      skills_installed=$((skills_installed + 1))
    done
    # Copy CATALOG.md if exists
    if [ -f "$skills_source/CATALOG.md" ]; then
      cp "$skills_source/CATALOG.md" "$skills_dest/CATALOG.md"
    fi
  else
    # Install standard skills
    for name in $STANDARD_SKILLS; do
      if [ -d "$skills_source/$name" ]; then
        cp -r "$skills_source/$name" "$skills_dest/$name"
        skills_installed=$((skills_installed + 1))
      fi
    done
    if [ -f "$skills_source/CATALOG.md" ]; then
      cp "$skills_source/CATALOG.md" "$skills_dest/CATALOG.md"
    fi
  fi
fi

# ── 7. Install templates (standard and full only) ────────────────
if [ "$MODE" != "--minimal" ] && [ -d "$COS_SOURCE_DIR/templates" ]; then
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

# ── 8b. Apply efficiency profile filtering ──────────────────────────
# After rules are installed AND cognitive-os.yaml exists, apply profile
# filtering from cognitive-os.yaml. This mirrors the logic in self-install.sh
# so external projects get the same profile-aware rule restriction.
EFFICIENCY_PROFILE="standard"
if [ -f "cognitive-os.yaml" ]; then
  _ep=$(grep -A1 '^efficiency:' cognitive-os.yaml 2>/dev/null | grep 'profile:' | awk '{print $2}' | tr -d "'\"\r" || true)
  [ -n "$_ep" ] && EFFICIENCY_PROFILE="$_ep"
fi

# Core rules for standard profile (must match self-install.sh CORE_RULES array)
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
if [ -d "$RULES_DIR" ]; then
  if [ "$EFFICIENCY_PROFILE" = "lean" ]; then
    # Keep only RULES-COMPACT.md
    for rule in "$RULES_DIR"/*.md; do
      [ -f "$rule" ] || continue
      [ "$(basename "$rule")" = "RULES-COMPACT.md" ] || rm -f "$rule"
    done
    rules_installed=1
  elif [ "$EFFICIENCY_PROFILE" = "standard" ]; then
    # Keep only core rules
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
fi

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
cos_version="unknown"
if [ -f "$VERSION_FILE" ]; then
  cos_version=$(cat "$VERSION_FILE")
elif [ -d "$COS_SOURCE_DIR/.git" ]; then
  cos_version=$(cd "$COS_SOURCE_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "dev")
fi

cat > .cognitive-os/install-meta.json << ENDJSON
{
  "mode": "${MODE#--}",
  "version": "$cos_version",
  "source": "$COS_SOURCE_DIR",
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
  cos_registry_register "$PROJECT_DIR" "${MODE#--}" "$cos_version" "$project_name" "$COS_SOURCE_DIR"
fi

# ── 12. Add to .gitignore ────────────────────────────────────────
if [ -f ".gitignore" ]; then
  for pattern in ".cognitive-os/sessions/" ".cognitive-os/metrics/" ".cognitive-os/tasks/"; do
    if ! grep -qF "$pattern" .gitignore 2>/dev/null; then
      echo "$pattern" >> .gitignore
    fi
  done
else
  cat > .gitignore << 'ENDGI'
# Cognitive OS runtime (not committed)
.cognitive-os/sessions/
.cognitive-os/metrics/
.cognitive-os/tasks/
ENDGI
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
if [ "$MODE" = "--minimal" ]; then
  echo "Want more? Re-run with --standard or --full:"
  echo "  bash $COS_SOURCE_DIR/scripts/cos-init.sh --standard"
fi
