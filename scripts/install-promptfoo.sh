#!/usr/bin/env bash
# install-promptfoo.sh — Install Promptfoo red team testing framework
set -euo pipefail

echo "Installing promptfoo (LLM red team testing)..."
echo ""

# Check Node.js is available
if ! command -v node &>/dev/null; then
  echo "ERROR: Node.js is required to install promptfoo."
  echo "Install Node.js from https://nodejs.org/ or via your package manager."
  exit 1
fi

# Install globally or inform about npx usage
if command -v npm &>/dev/null; then
  echo "Installing promptfoo globally..."
  npm install -g promptfoo
  echo "  promptfoo installed: $(promptfoo --version 2>/dev/null || echo 'check PATH')"
else
  echo "npm not found. promptfoo can be run via npx:"
  echo "  npx promptfoo@latest eval --config .promptfoo/config.yaml"
fi

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Review the config: .promptfoo/config.yaml"
echo "  2. Run red team tests: npx promptfoo@latest eval --config .promptfoo/config.yaml"
echo "  3. Or use the skill: /red-team"
echo ""
echo "For full LLM-based red teaming, configure a provider in .promptfoo/config.yaml:"
echo "  providers:"
echo "    - id: anthropic:messages:claude-sonnet-4-20250514"
