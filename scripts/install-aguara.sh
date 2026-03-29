#!/usr/bin/env bash
# install-aguara.sh — Install aguara AI agent security scanner and mcp-aguara MCP server
set -euo pipefail

echo "Installing aguara and mcp-aguara..."
echo ""

# Check Go is available
if ! command -v go &>/dev/null; then
  echo "ERROR: Go is required to install aguara."
  echo "Install Go from https://go.dev/dl/ or via your package manager."
  exit 1
fi

# Install aguara CLI
echo "Installing aguara (AI agent security scanner)..."
go install github.com/garagon/aguara@latest
echo "  aguara installed: $(aguara --version 2>/dev/null || echo 'check PATH')"

# Install mcp-aguara MCP server
echo "Installing mcp-aguara (MCP server)..."
go install github.com/garagon/mcp-aguara@latest
echo "  mcp-aguara installed: $(mcp-aguara --version 2>/dev/null || echo 'check PATH')"

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Enable in cognitive-os.yaml: security.aguara.enabled = true"
echo "  2. (Optional) Register aguara hook in .claude/settings.json:"
echo '     PreToolUse: {"command": "bash \"$CLAUDE_PROJECT_DIR/hooks/aguara-scan.sh\""}'
echo "  3. (Optional) Register mcp-aguara as MCP server in .claude/settings.json:"
echo '     mcpServers: {"aguara": {"command": "mcp-aguara", "args": []}}'
