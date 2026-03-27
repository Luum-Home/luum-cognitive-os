#!/usr/bin/env bash
# cognitive-os — CLI entry point
set -euo pipefail

VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"

usage() {
  cat <<EOF
cognitive-os v${VERSION} — Portable AI Agent Operating System

Usage:
  cognitive-os init           Install Cognitive OS into the current project
  cognitive-os version        Show version
  cognitive-os doctor         Check installation health
  cognitive-os help           Show this help

Examples:
  cd your-project
  cognitive-os init           # Installs .cognitive-os/ and cognitive-os.yaml
  claude                      # Open Claude Code
  > /cognitive-os-init        # Detect stack and generate project config

Documentation: https://github.com/luum-home/luum-cognitive-os
EOF
}

cmd_init() {
  local target_dir="${1:-.}"

  if [ -d "$target_dir/.cognitive-os" ]; then
    echo "Cognitive OS is already installed in $target_dir/.cognitive-os"
    read -rp "Overwrite? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
      echo "Aborted."
      exit 0
    fi
    rm -rf "$target_dir/.cognitive-os"
  fi

  echo "Installing Cognitive OS into $target_dir..."
  cp -r "$PACKAGE_DIR/.cognitive-os" "$target_dir/.cognitive-os"

  if [ ! -f "$target_dir/cognitive-os.yaml" ]; then
    cp "$PACKAGE_DIR/cognitive-os.yaml" "$target_dir/cognitive-os.yaml"
  fi

  echo ""
  echo "Cognitive OS installed!"
  echo ""
  echo "Next steps:"
  echo "  1. cd $target_dir"
  echo "  2. claude"
  echo "  3. /cognitive-os-init"
  echo ""
}

cmd_version() {
  echo "cognitive-os v${VERSION}"
}

cmd_doctor() {
  echo "=== Cognitive OS Doctor ==="
  echo ""

  local issues=0

  # Check .cognitive-os exists
  if [ -d ".cognitive-os" ]; then
    echo "[OK] .cognitive-os/ directory found"
  else
    echo "[!!] .cognitive-os/ directory NOT found — run: cognitive-os init"
    issues=$((issues + 1))
  fi

  # Check cognitive-os.yaml
  if [ -f "cognitive-os.yaml" ]; then
    echo "[OK] cognitive-os.yaml found"
  else
    echo "[!!] cognitive-os.yaml NOT found"
    issues=$((issues + 1))
  fi

  # Check hooks
  if [ -d ".cognitive-os/hooks" ]; then
    local hook_count
    hook_count=$(find .cognitive-os/hooks -name '*.sh' -not -path '*/_lib/*' | wc -l)
    echo "[OK] $hook_count hooks found"
  else
    echo "[!!] No hooks directory"
    issues=$((issues + 1))
  fi

  # Check skills
  if [ -d ".cognitive-os/skills" ]; then
    local skill_count
    skill_count=$(find .cognitive-os/skills -name 'SKILL.md' | wc -l)
    echo "[OK] $skill_count skills found"
  else
    echo "[!!] No skills directory"
    issues=$((issues + 1))
  fi

  # Check rules
  if [ -d ".cognitive-os/rules" ]; then
    local rule_count
    rule_count=$(find .cognitive-os/rules -name '*.md' | wc -l)
    echo "[OK] $rule_count rules found"
  else
    echo "[!!] No rules directory"
    issues=$((issues + 1))
  fi

  # Check .claude/settings.json
  if [ -f ".claude/settings.json" ]; then
    echo "[OK] .claude/settings.json found (hooks registered)"
  else
    echo "[--] .claude/settings.json not found — run /cognitive-os-init in Claude Code"
  fi

  # Check Docker
  if command -v docker >/dev/null 2>&1; then
    echo "[OK] Docker available"
  else
    echo "[--] Docker not available (optional — needed for observability stack)"
  fi

  echo ""
  if [ "$issues" -eq 0 ]; then
    echo "All checks passed!"
  else
    echo "$issues issue(s) found. Run 'cognitive-os init' to fix."
  fi
}

# Main
case "${1:-help}" in
  init)    cmd_init "${2:-.}" ;;
  version) cmd_version ;;
  doctor)  cmd_doctor ;;
  help)    usage ;;
  *)       echo "Unknown command: $1"; usage; exit 1 ;;
esac
