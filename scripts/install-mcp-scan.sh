#!/usr/bin/env bash
# install-mcp-scan.sh — Install MCP-Scan (Invariant Labs) MCP server configuration scanner
set -euo pipefail

echo "Installing mcp-scan (MCP server configuration scanner)..."
echo ""

# Try pip first, then npx
if command -v pip &>/dev/null || command -v pip3 &>/dev/null; then
  PIP_CMD=$(command -v pip3 2>/dev/null || command -v pip 2>/dev/null)
  echo "Installing via pip..."
  $PIP_CMD install mcp-scan
  echo "  mcp-scan installed: $(mcp-scan --version 2>/dev/null || echo 'check PATH')"
elif command -v npx &>/dev/null; then
  echo "pip not found. mcp-scan can be run via npx:"
  echo "  npx @invariantlabs/mcp-scan scan <settings-file>"
  echo ""
  echo "For persistent installation, install pip and run:"
  echo "  pip install mcp-scan"
else
  echo "ERROR: Neither pip nor npx found."
  echo "Install Python (pip) or Node.js (npx) first."
  exit 1
fi

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Enable in cognitive-os.yaml: security.mcp_scan.enabled = true"
echo "  2. (Optional) Register hook in .claude/settings.json:"
echo '     SessionStart: {"command": "bash \"$CLAUDE_PROJECT_DIR/hooks/mcp-scan.sh\""}'
echo "  3. Run manually: mcp-scan scan .claude/settings.json"
