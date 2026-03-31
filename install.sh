#!/usr/bin/env bash
# install.sh — Install Cognitive OS into the current project
set -euo pipefail

REPO_URL="https://github.com/luum-home/luum-cognitive-os.git"
VERSION="${COGNITIVE_OS_VERSION:-main}"
TARGET_DIR=".cognitive-os"
FORCE="${COGNITIVE_OS_FORCE:-false}"
TEMP_DIR=$(mktemp -d)
SOURCE_DIR=""
FROM_FLAG=""

cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

# ── Argument parsing ──────────────────────────────────────────────────
show_help() {
  cat <<'USAGE'
Usage: install.sh [OPTIONS]

Install Cognitive OS into the current project.

Options:
  --from PATH    Use a local Cognitive OS repo instead of cloning from GitHub
  --force        Overwrite existing installation without prompting
  --help         Show this help message

Environment variables:
  COGNITIVE_OS_VERSION   Git branch/tag to install (default: main)
  COGNITIVE_OS_FORCE     Set to "true" to overwrite without prompting

Source detection:
  If run from within the Cognitive OS repo (hooks/, rules/, skills/ exist
  relative to the script), the local repo is used automatically.
  Use --from to specify a different local repo path explicitly.

Examples:
  # Install from GitHub (remote)
  curl -sL https://raw.githubusercontent.com/.../install.sh | bash

  # Install from the repo you're currently in
  ./install.sh

  # Install from a specific local path
  ./install.sh --from /path/to/luum-agent-os

  # Force overwrite existing installation
  ./install.sh --force
USAGE
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from)
      if [[ -z "${2:-}" ]]; then
        echo "Error: --from requires a path argument."
        exit 1
      fi
      FROM_FLAG="$2"
      shift 2
      ;;
    --force)
      FORCE="true"
      shift
      ;;
    --help|-h)
      show_help
      ;;
    *)
      echo "Unknown option: $1"
      echo "Run 'install.sh --help' for usage."
      exit 1
      ;;
  esac
done

# ── Source detection ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$FROM_FLAG" ]; then
  # Explicit --from flag
  if [ ! -d "$FROM_FLAG" ]; then
    echo "Error: --from path does not exist: $FROM_FLAG"
    exit 1
  fi
  FROM_FLAG="$(cd "$FROM_FLAG" && pwd)"
  if [ -d "$FROM_FLAG/hooks" ] && [ -d "$FROM_FLAG/rules" ] && [ -d "$FROM_FLAG/skills" ]; then
    SOURCE_DIR="$FROM_FLAG"
  else
    echo "Error: --from path does not look like a Cognitive OS repo."
    echo "       Expected hooks/, rules/, skills/ directories in: $FROM_FLAG"
    exit 1
  fi
elif [ -d "$SCRIPT_DIR/hooks" ] && [ -d "$SCRIPT_DIR/rules" ] && [ -d "$SCRIPT_DIR/skills" ]; then
  # Running from within the repo itself
  SOURCE_DIR="$SCRIPT_DIR"
fi

echo "=== Cognitive OS Installer ==="
echo ""

if [ -n "$SOURCE_DIR" ]; then
  echo "Using local Cognitive OS from: $SOURCE_DIR"
  echo ""
fi

# Check prerequisites (git only needed for remote install)
if [ -z "$SOURCE_DIR" ] && ! command -v git >/dev/null 2>&1; then
  echo "Error: git is required but not installed."
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Warning: jq is not installed. Settings merge requires jq."
  echo "         Install jq for safe merge with existing .claude/settings.json"
  HAS_JQ=false
else
  HAS_JQ=true
fi

# ── Pre-install conflict detection ──────────────────────────────────
if [ -d ".claude" ]; then
  echo "Detected existing .claude/ configuration:"
  existing_hooks=0
  existing_rules=0
  existing_commands=0
  has_claude_md=false

  if [ -f ".claude/settings.json" ]; then
    existing_hooks=$(jq '[.hooks // {} | to_entries[] | .value[] | .hooks[]? ] | length' .claude/settings.json 2>/dev/null || echo "?")
    echo "  - settings.json: $existing_hooks hooks registered"
  fi

  if [ -d ".claude/rules" ]; then
    existing_rules=$(find .claude/rules -maxdepth 2 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  - rules/: $existing_rules rule files"
  fi

  if [ -d ".claude/commands" ]; then
    existing_commands=$(find .claude/commands -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  - commands/: $existing_commands command files"
  fi

  if [ -f ".claude/CLAUDE.md" ]; then
    has_claude_md=true
    echo "  - CLAUDE.md: present"
  fi

  echo ""
  echo "Cognitive OS will MERGE settings and namespace rules under cos/"
  echo "Your existing configuration will be preserved."
  echo ""
fi

# Check if already installed
if [ -d "$TARGET_DIR" ]; then
  if [ "$FORCE" = "true" ]; then
    echo "Overwriting existing installation..."
    rm -rf "$TARGET_DIR"
  elif [ -t 0 ]; then
    # Interactive terminal — ask for confirmation
    echo "Cognitive OS is already installed in $TARGET_DIR"
    read -rp "Overwrite? (y/N): " confirm </dev/tty
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
      echo "Aborted."
      exit 0
    fi
    rm -rf "$TARGET_DIR"
  else
    # Non-interactive (piped) — abort safely
    echo "Cognitive OS is already installed in $TARGET_DIR"
    echo "To overwrite, run: COGNITIVE_OS_FORCE=true bash install.sh"
    exit 0
  fi
fi

# ── Prepare source (local copy or remote clone) ──────────────────────
prepare_source() {
  if [ -n "$SOURCE_DIR" ]; then
    # Local: copy repo contents to temp dir
    echo "Copying from local source..."
    # Remove the empty temp dir and copy source into its place
    rm -rf "$TEMP_DIR"
    cp -r "$SOURCE_DIR" "$TEMP_DIR"
  else
    # Remote: git clone
    echo "Downloading Cognitive OS ($VERSION)..."
    git clone --depth 1 --branch "$VERSION" "$REPO_URL" "$TEMP_DIR" 2>/dev/null || \
      git clone --depth 1 "$REPO_URL" "$TEMP_DIR"
  fi
}

prepare_source

# ── Delegate to cos-init.sh ──────────────────────────────────────────
# cos-init.sh handles: rules, hooks, skills, templates, settings.json,
# cognitive-os.yaml, CLAUDE.md template, and registry registration.
# It uses generate-project-settings.sh for correct hook paths and
# installs to namespaced cos/ subdirectories.
COS_INIT="$TEMP_DIR/scripts/cos-init.sh"

if [ ! -f "$COS_INIT" ]; then
  echo "Error: cos-init.sh not found in source."
  exit 1
fi

echo "Running cos-init.sh..."
COS_SOURCE_DIR="$TEMP_DIR" bash "$COS_INIT" --standard

# ── Install CLAUDE.md template if not present ─────────────────────────
if [ ! -f ".claude/CLAUDE.md" ]; then
  TEMPLATE="$TEMP_DIR/templates/CLAUDE.md.template"
  if [ -f "$TEMPLATE" ]; then
    mkdir -p ".claude"
    cp "$TEMPLATE" ".claude/CLAUDE.md"
    echo "Created .claude/CLAUDE.md from template."
  fi
else
  echo "Existing .claude/CLAUDE.md preserved (not overwritten)."
fi

echo ""
echo "Cognitive OS installed successfully!"
echo ""
echo "Project structure:"
echo "  .cognitive-os/hooks/cos/     — COS hooks (namespaced)"
echo "  .cognitive-os/skills/cos/    — COS skills (namespaced)"
echo "  .cognitive-os/templates/cos/ — COS templates (namespaced)"
echo "  .claude/rules/cos/           — COS rules (namespaced)"
echo "  .claude/settings.json        — Hooks (project + COS merged)"
echo ""
echo "Your existing .claude/ configuration is preserved."
echo ""
