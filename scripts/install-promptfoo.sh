#!/usr/bin/env bash
# SCOPE: both
# install-promptfoo.sh — Install Promptfoo red team testing framework
set -euo pipefail

echo "Installing promptfoo (LLM red team testing)..."
echo ""

# Check Bun is available
if ! command -v bun &>/dev/null; then
  echo "ERROR: Bun is required to install or run promptfoo in Cognitive OS."
  echo "Install Bun from https://bun.sh/ and keep install.ignoreScripts=true for project installs."
  exit 1
fi

echo "Installing promptfoo globally with Bun..."
bun add -g promptfoo
echo "  promptfoo installed: $(promptfoo --version 2>/dev/null || echo 'check PATH')"

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Review the config: .promptfoo/config.yaml"
echo "  2. Run red team tests: bunx promptfoo@latest eval --config .promptfoo/config.yaml"
echo "  3. Or use the skill: /red-team"
echo ""
echo "For full LLM-based red teaming, configure a provider in .promptfoo/config.yaml:"
echo "  providers:"
echo "    - id: anthropic:messages:claude-sonnet-4-20250514"
