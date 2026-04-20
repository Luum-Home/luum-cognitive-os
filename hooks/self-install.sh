#!/usr/bin/env bash
# SCOPE: os-only
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
  "skills|claude|tree|"
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

# ── Helper: portable relative path from dir_of_link -> target ─────────
# Usage: rel_path <target_abs> <link_abs>
# Portable across macOS and Linux (no GNU-only flags).
rel_path() {
  local target="$1" link="$2"
  local link_dir
  link_dir=$(dirname "$link")
  python3 - "$target" "$link_dir" <<'PY'
import os, sys
target, start = sys.argv[1], sys.argv[2]
print(os.path.relpath(target, start))
PY
}

# ── Helper: create a relative symlink (replaces `ln -sf abs_src link`) ─
# Usage: ln_rel <target_abs> <link_abs>
ln_rel() {
  local target="$1" link="$2"
  local rel
  rel=$(rel_path "$target" "$link")
  ln -sf "$rel" "$link"
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
      ln_rel "$file" "$link"
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
      ln_rel "$dir" "$link"
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
      ln_rel "$file" "$link"
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

# Detect whether we are running inside the luum-agent-os repo itself.
# When self-hosting, always use the full profile so all rules are loaded.
IS_SELF_HOSTING=false
if [ -f "$PROJECT_DIR/hooks/self-install.sh" ]; then
  IS_SELF_HOSTING=true
fi

EFFICIENCY_PROFILE="standard"
if [ "$IS_SELF_HOSTING" = "true" ]; then
  EFFICIENCY_PROFILE="full"
elif [ -f "$CONFIG_FILE" ]; then
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
  "credential-management.md"
  "model-routing.md"
  "result-management.md"
)
# NOTE: rate-limiting, content-policy, blast-radius, clarification-gate were previously kept
# in CORE_RULES (proactive defence-in-depth). They are now moved to EXCLUDED_RULES so their
# hook enforcement is the sole active layer, reducing context overhead.

# ── Excluded rules for self-hosting (SYNC_ALL_RULES=true) ─────────────
# These rules are NOT loaded into agent context for three reasons:
#   A) Hook-enforced: the hook makes the rule file redundant in context
#   B) Package-specific: only relevant when that optional package is active
#   C) Contextual: rare/specialized; indexed in RULES-COMPACT, loads on demand
# Rule .md files remain in rules/ as human docs — only symlinks are managed.
EXCLUDED_RULES=(
  # ── A) Hook-enforced (hook is the active enforcement layer) ──────────
  "anti-hallucination.md"          # → claim-validator.sh (PostToolUse Agent)
  "blast-radius.md"                # → blast-radius.sh (PreToolUse Agent)
  "clarification-gate.md"          # → clarification-gate.sh (PreToolUse Agent)
  "content-policy.md"              # → content-policy.sh (PostToolUse Edit|Write)
  "crash-recovery.md"              # → auto-checkpoint.sh + crash-recovery.sh
  "prompt-quality.md"              # → prompt-quality.sh (PreToolUse Agent)
  "rate-limiting.md"               # → rate-limiter.sh (PreToolUse Bash|Agent|Edit|Write)
  "rate-limit-protection.md"       # → token-budget-monitor.sh (PreToolUse Agent)
  "skill-rewrite.md"               # → completion-gate.sh (PostToolUse Agent)
  "auto-skill-generation.md"       # → auto-skill-generator.sh (PostToolUse Agent)
  "auto-repair.md"                 # → auto-repair-dispatcher.sh (PostToolUse Agent)
  "pre-dev-readiness-gate.md"      # → predev-completeness-check.sh (PreToolUse Agent)
  "audit-trail.md"                 # → git-context-capture.sh + session-changelog.sh (Stop)
  "pre-commit-gate.md"             # → pre-commit-gate.sh (git hook)
  "confidentiality-protection.md"  # → confidentiality-enforcer.sh (PostToolUse Edit|Write)
  "scope-proportionality.md"       # → scope-proportionality.sh (PostToolUse Agent)
  "scope-creep-detection.md"       # → scope-proportionality.sh (PostToolUse Agent)
  "confidence-gate.md"             # → confidence-gate.sh (PostToolUse Agent)
  "consequence-system.md"          # → consequence-evaluator.sh (PostToolUse Agent)
  "auto-rollback.md"               # → auto-rollback-trigger.sh (PostToolUse Agent)
  "response-compression.md"        # agent-instruction-only (no hook — see rules/ROADMAP.md §D24)
  "assumption-tracking.md"         # → assumption-tracker.sh (PostToolUse Agent)

  # ── B) Package-specific (only relevant when package is active) ────────
  "aguara-integration.md"          # packages/aguara-security — load when aguara used
  "e2b-integration.md"             # packages/e2b-sandbox — load when E2B used
  "hcom-integration.md"            # packages/ecosystem-tools — load when hcom used
  "parry-integration.md"           # packages/ecosystem-tools — load when parry used
  "repomix-integration.md"         # packages/ecosystem-tools — load when repomix used
  "tero-integration.md"            # packages/tero-testing — load when tero used
  "trailofbits-skills.md"          # packages/ecosystem-tools — load when tob skills used
  "context7-auto-trigger.md"       # packages/ecosystem-tools — load when context7 used
  "ecosystem-tools.md"             # packages/ecosystem-tools — reference doc, not behavioral
  "private-mode.md"                # packages/privacy-mode — load when /private invoked
  "doc-sync.md"                    # packages/document-sync — load when /doc-sync invoked
  "security-scanning.md"           # packages/security — load when semgrep scan invoked

  # ── C) Contextual (indexed in RULES-COMPACT, load on demand) ─────────
  "singularity.md"                 # rare: autonomous MAPE-K loop
  "squad-protocol.md"              # contextual: squad ops trigger
  "estimation-calibration.md"      # contextual: medium+ task estimation
  "step-files.md"                  # contextual: long phase workflows
  "dry-run.md"                     # contextual: DRY_RUN=true sessions
  "session-concurrency.md"         # contextual: multi-session coordination
  "agent-communication.md"         # contextual: Valkey bus (OFF by default)
  "agent-customization.md"         # contextual: per-agent override files
  "agent-sidecars.md"              # contextual: sidecar pattern reference
  "performance-monitoring.md"      # contextual: perf dashboard invocation
  "cognitive-load.md"              # contextual: >50% context threshold
  "workload-scheduling.md"         # contextual: 4+ concurrent task batching
  "task-dag.md"                    # contextual: dependency DAG workflows
  "queue-drain.md"                 # contextual: dispatch queue draining
  "queue-advisor.md"               # contextual: dynamic queue prioritization
  "non-blocking-retry.md"          # contextual: rate-limited retry scheduling
  "hook-security-profiles.md"      # contextual: profile switching reference
  "infra-health.md"                # contextual: Docker infra health checks
  "infra-intent.md"                # contextual: infra keyword detection
  "sandbox-sampling.md"            # contextual: >100 file operations
  "impact-analysis.md"             # contextual: pre-sdd-apply blast analysis
  "scout-pattern.md"               # contextual: pre-implementation recon
  "split-and-resume.md"            # contextual: mid-task clarification
  "fault-tolerance.md"             # contextual: session recovery ops
  "capability-protection.md"       # contextual: before OS refactors/cleanup
  "capability-levels.md"           # contextual: model capability auto-disable
  "os-vs-project.md"               # contextual: OS vs project separation guide
  "dogfooding.md"                  # contextual: self-hosting requirement doc
  "plan-first.md"                  # contextual: plan-first protocol reference
  "cost-prediction.md"             # contextual: cost forecasting invocation
  "pentesting-readiness.md"        # contextual: security audit reference
  "supply-chain-defense.md"        # contextual: supply chain attack mitigations
  "dynamic-tool-creation.md"       # contextual: mid-task tool creation
  "component-classification.md"    # contextual: OS component CORE vs PACKAGE
  "skill-management.md"            # contextual: skill lifecycle management
  "reinvention-prevention.md"      # contextual: check-before-build guard
  "user-prompt-capture.md"         # contextual: prompt classifier usage
  "agent-escalation.md"            # contextual: escalation detector library
  "agent-identity.md"              # contextual: identity & audit trail reference
  "agent-security.md"              # contextual: least-privilege permission API
  "agent-kpis.md"                  # contextual: KPI calculation invocation
  "model-compatibility.md"         # contextual: model switch checklist
  "model-directive.md"             # contextual: dispatch-gate directive protocol
  "orchestrator-mode.md"           # contextual: executor mode activation
  "engram-organization.md"         # contextual: engram prefix system reference
  "cognitive-os-changes.md"        # contextual: plan-first for OS mods
  "library-selection.md"           # contextual: library evaluation checklist
  "prompt-composition.md"          # contextual: template composition protocol
  "self-improvement-protocol.md"   # contextual: weekly self-improve trigger
  "broken-window-policy.md"        # contextual: covers same ground as agent-quality
  "decomposition.md"               # contextual: covered by token-economy + model-routing
  "license-policy.md"              # contextual: license table reference
  "context-optimization.md"        # contextual: progressive loading reference
)

# Build the effective allowed-rules list based on profile.
# In self-hosting/full mode, ALL rules in rules/ are symlinked (not just CORE_RULES).
# In standard mode, only CORE_RULES are synced. In lean mode, only RULES-COMPACT.md.
if [[ "$EFFICIENCY_PROFILE" == "lean" ]]; then
  ALLOWED_RULES=("RULES-COMPACT.md")
  SYNC_ALL_RULES=false
elif [[ "$IS_SELF_HOSTING" == "true" ]] || [[ "$EFFICIENCY_PROFILE" == "full" ]]; then
  # Self-hosting and full profile: symlink every rule file that exists
  ALLOWED_RULES=("${CORE_RULES[@]}")
  SYNC_ALL_RULES=true
else
  ALLOWED_RULES=("${CORE_RULES[@]}")
  SYNC_ALL_RULES=false
fi

cos_rules_dir="$PROJECT_DIR/.claude/rules/cos"
mkdir -p "$cos_rules_dir"

# Add missing symlinks
if [[ "$SYNC_ALL_RULES" == "true" ]]; then
  # Symlink every .md file in rules/ EXCEPT those that are hook-enforced (EXCLUDED_RULES)
  for src in "$PROJECT_DIR/rules"/*.md; do
    [ -f "$src" ] || continue
    base=$(basename "$src")
    # Skip rules that are fully enforced by registered hooks
    is_excluded=false
    for excl in "${EXCLUDED_RULES[@]}"; do
      if [[ "$base" == "$excl" ]]; then
        is_excluded=true
        break
      fi
    done
    [[ "$is_excluded" == "true" ]] && continue
    link="$cos_rules_dir/$base"
    if [ ! -e "$link" ]; then
      ln_rel "$src" "$link"
      added=$((added + 1))
    fi
  done
  # Remove symlinks for excluded rules if they were previously created
  for excl in "${EXCLUDED_RULES[@]}"; do
    link="$cos_rules_dir/$excl"
    if [ -L "$link" ]; then
      rm "$link"
      removed=$((removed + 1))
    fi
  done
else
  # Only symlink CORE_RULES (or lean subset)
  for rule in "${ALLOWED_RULES[@]}"; do
    src="$PROJECT_DIR/rules/$rule"
    link="$cos_rules_dir/$rule"
    [ -f "$src" ] || continue
    if [ ! -e "$link" ]; then
      ln_rel "$src" "$link"
      added=$((added + 1))
    fi
  done
fi

# Remove symlinks in cos_rules_dir:
# - Always remove broken symlinks (target gone)
# - In standard/lean mode: also remove symlinks not in ALLOWED_RULES
# - In self-hosting/full mode: only remove broken symlinks (all rules are valid)
if [ -d "$cos_rules_dir" ]; then
  for link in "$cos_rules_dir"/*.md; do
    [ -L "$link" ] || continue
    base=$(basename "$link")
    # Always remove broken symlinks
    if [ ! -e "$link" ]; then
      rm -f "$link"
      removed=$((removed + 1))
      continue
    fi
    # In standard/lean mode, remove symlinks not in allowed list
    if [[ "$SYNC_ALL_RULES" != "true" ]]; then
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

# ── Consistency checks (session-start enforcement) ──────────────────
# These catch problems that the pre-commit hook warns about, in case
# code entered the repo via --no-verify, direct push, or git pull.

# Check 1: lib/ symlinks integrity
broken_symlinks=0
if [ -d "$PROJECT_DIR/lib" ]; then
  while IFS= read -r link; do
    if [ ! -e "$link" ]; then
      broken_symlinks=$((broken_symlinks + 1))
    fi
  done < <(find "$PROJECT_DIR/lib" -maxdepth 1 -type l 2>/dev/null)
  if [ "$broken_symlinks" -gt 0 ]; then
    fixes="${fixes:+$fixes, }$broken_symlinks broken lib/ symlinks"
  fi
fi

# Check 2: settings.json matches current efficiency profile
if [ -f "$PROJECT_DIR/scripts/apply-efficiency-profile.sh" ] && [ -f "$PROJECT_DIR/.claude/settings.json" ]; then
  current_profile=$(grep -A1 '^efficiency:' "$PROJECT_DIR/cognitive-os.yaml" 2>/dev/null | grep 'profile:' | awk '{print $2}' | tr -d "'\"\r" || echo "standard")
  if [ "$current_profile" != "full" ]; then
    # Count hooks that should exist for this profile
    expected_hooks=$(grep -c "hook_entry\|hook_group" "$PROJECT_DIR/scripts/apply-efficiency-profile.sh" 2>/dev/null || echo 0)
    actual_hooks=$(grep -c '"command":' "$PROJECT_DIR/.claude/settings.json" 2>/dev/null || echo 0)
    # Simple sanity: if actual is 0 but expected > 0, something is wrong
    if [ "$actual_hooks" -eq 0 ] && [ "$expected_hooks" -gt 0 ]; then
      fixes="${fixes:+$fixes, }settings.json has 0 hooks — run: bash scripts/apply-efficiency-profile.sh $current_profile"
    fi
  fi
fi

# Check 3: .githooks/pre-commit exists and is executable
if [ ! -x "$PROJECT_DIR/.githooks/pre-commit" ]; then
  fixes="${fixes:+$fixes, }.githooks/pre-commit missing or not executable"
fi

# Check 4: git core.hooksPath points to .githooks
hooks_path=$(git -C "$PROJECT_DIR" config core.hooksPath 2>/dev/null || echo "")
if [ "$hooks_path" != ".githooks" ]; then
  git -C "$PROJECT_DIR" config core.hooksPath .githooks 2>/dev/null || true
  fixes="${fixes:+$fixes, }fixed core.hooksPath -> .githooks"
fi

# Check 5: workflows directory exists
if [ ! -d "$PROJECT_DIR/.cognitive-os/workflows" ]; then
  fixes="${fixes:+$fixes, }.cognitive-os/workflows/ missing"
fi

# Check 6: pipeline state directory exists
if [ ! -d "$PROJECT_DIR/.cognitive-os/pipeline-state" ]; then
  mkdir -p "$PROJECT_DIR/.cognitive-os/pipeline-state"
  fixes="${fixes:+$fixes, }created pipeline-state dir"
fi

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
