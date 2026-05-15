#!/usr/bin/env bash
# SCOPE: both
# @manual-trigger: run once to install Trail of Bits skills plugin; deferred until ToB security workflow is active
# install-tob-skills.sh — Install Trail of Bits security skills
set -euo pipefail

PLUGIN_DIR=".claude/plugins/trailofbits-skills"

if [ -d "$PLUGIN_DIR" ]; then
  echo "Trail of Bits skills already installed at $PLUGIN_DIR"
  echo "To update: cd $PLUGIN_DIR && git pull"
  exit 0
fi

echo "Installing Trail of Bits security skills..."
git submodule add https://github.com/trailofbits/skills.git "$PLUGIN_DIR"
echo ""
echo "Installed successfully!"
echo "Skills available in: $PLUGIN_DIR"
echo "License: CC-BY-SA-4.0 (see ATTRIBUTION.md)"
