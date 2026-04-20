#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: ux, session-health, adr-001-regression-detector
# Session Sanity Hook — SessionStart
# Verifies that the .claude/ installation is intact after every session start:
#   1) .claude/skills/ contains a reasonable number of skill entries
#   2) every hook referenced by .claude/settings.json exists on disk
#
# Advisory only — always exits 0. Prints actionable guidance to stderr when
# a check fails so the user sees it at session start.
#
# Registered at the `standard` tier of scripts/apply-efficiency-profile.sh so
# every user running the default profile gets this safety net.
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="session-sanity"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
SKILLS_DIR="$PROJECT_DIR/.claude/skills"
SETTINGS_FILE="$PROJECT_DIR/.claude/settings.json"
HOOKS_DIR="$PROJECT_DIR/hooks"
MIN_SKILLS_THRESHOLD=20

FAILED=false

# Check 1: skill count
if [ -d "$SKILLS_DIR" ]; then
  # Count directory entries (skills are directories with SKILL.md)
  SKILL_COUNT=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d '[:space:]')
  # Also count symlinks to directories (skills may be linked)
  SYMLINK_COUNT=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type l 2>/dev/null | wc -l | tr -d '[:space:]')
  TOTAL_SKILLS=$((SKILL_COUNT + SYMLINK_COUNT))

  if [ "$TOTAL_SKILLS" -lt "$MIN_SKILLS_THRESHOLD" ]; then
    echo "" >&2
    echo "=== SESSION-SANITY: WARNING ===" >&2
    echo "Only $TOTAL_SKILLS skills exposed in .claude/skills/; expected $MIN_SKILLS_THRESHOLD+." >&2
    echo "Action: run 'bash hooks/self-install.sh' to repopulate the skill catalog." >&2
    echo "" >&2
    FAILED=true
  fi
else
  echo "" >&2
  echo "=== SESSION-SANITY: WARNING ===" >&2
  echo ".claude/skills/ directory is missing." >&2
  echo "Action: run 'bash hooks/self-install.sh' to set up the Cognitive OS skill catalog." >&2
  echo "" >&2
  FAILED=true
fi

# Check 2: every hook in settings.json exists on disk
if [ -f "$SETTINGS_FILE" ]; then
  # Extract every "command" line that references a .sh file, reduce to the
  # basename (e.g. self-install.sh), de-dupe, and check each one exists in
  # hooks/ or packages/*/hooks/. Works without jq via grep/sed.
  BROKEN=""
  # Collect referenced shell scripts (basename only)
  REF_SCRIPTS=$(grep -oE '[A-Za-z0-9_-]+\.sh' "$SETTINGS_FILE" 2>/dev/null | sort -u)
  if [ -n "$REF_SCRIPTS" ]; then
    while IFS= read -r script; do
      [ -z "$script" ] && continue
      # Check hooks/ first, then packages/*/hooks/
      if [ -f "$HOOKS_DIR/$script" ]; then
        continue
      fi
      # Look in packages/*/hooks/
      found=false
      if [ -d "$PROJECT_DIR/packages" ]; then
        while IFS= read -r pkg_hook; do
          [ -f "$pkg_hook" ] && found=true && break
        done < <(find "$PROJECT_DIR/packages" -type f -name "$script" 2>/dev/null)
      fi
      if [ "$found" = false ]; then
        BROKEN="${BROKEN:+$BROKEN, }$script"
      fi
    done <<< "$REF_SCRIPTS"
  fi

  if [ -n "$BROKEN" ]; then
    echo "" >&2
    echo "=== SESSION-SANITY: WARNING ===" >&2
    echo "settings.json references hooks that do not exist on disk:" >&2
    echo "  $BROKEN" >&2
    echo "Action: run 'bash hooks/self-install.sh' to reinstall the Cognitive OS harness." >&2
    echo "" >&2
    FAILED=true
  fi
fi

# Check 3: Log session metadata to session-log.jsonl (for cos-sessions history)
SESSION_LOG="$PROJECT_DIR/.cognitive-os/metrics/session-log.jsonl"
mkdir -p "$(dirname "$SESSION_LOG")" 2>/dev/null || true

SESSION_ID="${COGNITIVE_OS_SESSION_ID:-unknown}"
PROJECT_NAME="$(basename "$PROJECT_DIR")"
TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
PROFILE="$(grep -A1 '^efficiency:' "$PROJECT_DIR/cognitive-os.yaml" 2>/dev/null | grep 'profile:' | awk '{print $2}' | tr -d "'\"\r" || echo unknown)"
SELF_HOSTED="false"
[ -f "$PROJECT_DIR/hooks/self-install.sh" ] && SELF_HOSTED="true"
SKILLS_COUNT=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 \( -type d -o -type l \) 2>/dev/null | wc -l | tr -d '[:space:]')
HOOKS_WIRED=$(grep -c '"command":' "$SETTINGS_FILE" 2>/dev/null | tr -d '[:space:]')

# Append single JSONL line (best-effort; ignore failures)
printf '{"timestamp":"%s","session_id":"%s","project":"%s","project_dir":"%s","self_hosted":%s,"profile":"%s","skills_count":%s,"hooks_wired":%s}\n' \
  "$TIMESTAMP" "$SESSION_ID" "$PROJECT_NAME" "$PROJECT_DIR" "$SELF_HOSTED" "$PROFILE" "${SKILLS_COUNT:-0}" "${HOOKS_WIRED:-0}" \
  >> "$SESSION_LOG" 2>/dev/null || true

# Check 4: show COS roadmap position (surface pending work for next session)
ROADMAP_FILE="$PROJECT_DIR/docs/release/roadmap-v1.0-full-e2e.md"
if [ -f "$ROADMAP_FILE" ]; then
  # Extract "Current position" line from the pickup section
  POSITION=$(grep -m1 "^\*\*Current position\*\*" "$ROADMAP_FILE" 2>/dev/null | sed 's/^\*\*Current position\*\*: //' | sed 's/\*\*//g')
  # Extract the first pending session from the ledger table
  NEXT_SESSION=$(grep -E "^\| N\+[0-9]+ \|" "$ROADMAP_FILE" 2>/dev/null | head -1 | awk -F'|' '{gsub(/^ +| +$/, "", $2); gsub(/^ +| +$/, "", $3); print $2 " — " $3}')

  if [ -n "$POSITION" ] || [ -n "$NEXT_SESSION" ]; then
    echo "" >&2
    # Differentiate self-hosted (COS being built) vs client (COS being used)
    if [ "$SELF_HOSTED" = "true" ]; then
      echo "=== COS SELF-DEV SESSION === (this repo builds the OS)" >&2
    else
      echo "=== COS CLIENT PROJECT === $PROJECT_NAME" >&2
    fi
    echo "Session: $SESSION_ID" >&2
    echo "Profile: $PROFILE | Skills: $SKILLS_COUNT | Hooks wired: $HOOKS_WIRED" >&2
    [ -n "$POSITION" ] && echo "Roadmap: $POSITION" >&2
    [ -n "$NEXT_SESSION" ] && echo "Next:    $NEXT_SESSION" >&2
    echo "Read:    docs/release/roadmap-v1.0-full-e2e.md" >&2
    echo "Hist:    bash scripts/cos-sessions.sh --last 5" >&2
    echo "" >&2
  fi
fi

# Always advisory
exit 0
