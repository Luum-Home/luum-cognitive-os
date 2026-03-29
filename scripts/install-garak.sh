#!/usr/bin/env bash
# install-garak.sh — Install Garak LLM vulnerability scanner
set -euo pipefail

echo "Installing Garak (LLM vulnerability scanner)..."
echo ""

# Check Python is available
if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3 is required to install Garak."
  echo "Install Python from https://python.org or via your package manager."
  exit 1
fi

# Check pip is available
if ! python3 -m pip --version &>/dev/null; then
  echo "ERROR: pip is required to install Garak."
  echo "Install pip: python3 -m ensurepip --upgrade"
  exit 1
fi

# Install garak
echo "Installing garak via pip..."
python3 -m pip install --user garak

# Verify installation
if command -v garak &>/dev/null; then
  echo "  garak installed: $(garak --version 2>/dev/null || echo 'installed, check PATH')"
else
  echo "  garak installed but not in PATH."
  echo "  Try: python3 -m garak --version"
  echo "  Or add ~/.local/bin to your PATH."
fi

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Run a quick scan: garak --model_type openai --model_name gpt-3.5-turbo --probes probes.dan"
echo "  2. Use in COS: /vulnerability-scan --target http://localhost:4000"
echo "  3. See: skills/vulnerability-scan/SKILL.md for full usage"
