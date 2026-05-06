#!/usr/bin/env bash
# SCOPE: project
# install-credibility-tools.sh — Install optional credibility-audit scanners
#
# These tools enhance scripts/credibility-audit.sh when installed:
#   - codespell  — typo detection in code + docs
#   - vale       — weasel-word + style detection in user-facing copy
#   - lychee     — broken-link detection in markdown
#
# All are Apache 2.0 / MIT, no API keys, local-only.
set -euo pipefail

OS="$(uname -s)"

install_codespell() {
  if command -v codespell >/dev/null 2>&1; then
    echo "  ✓ codespell already installed"
    return 0
  fi
  if [ "${OS}" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    brew install codespell
  elif command -v pip >/dev/null 2>&1; then
    pip install --user codespell
  else
    echo "  ✗ install codespell manually: pip install codespell"
    return 1
  fi
}

install_vale() {
  if command -v vale >/dev/null 2>&1; then
    echo "  ✓ vale already installed"
    return 0
  fi
  if [ "${OS}" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    brew install vale
  else
    echo "  ✗ install vale from https://vale.sh/docs/vale-cli/installation/"
    return 1
  fi
}

install_lychee() {
  if command -v lychee >/dev/null 2>&1; then
    echo "  ✓ lychee already installed"
    return 0
  fi
  if [ "${OS}" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    brew install lychee
  elif command -v cargo >/dev/null 2>&1; then
    cargo install lychee
  else
    echo "  ✗ install lychee from https://github.com/lycheeverse/lychee"
    return 1
  fi
}

echo "Installing credibility-audit optional scanners..."
echo ""
install_codespell || true
install_vale || true
install_lychee || true

echo ""
echo "Installation summary:"
command -v codespell >/dev/null 2>&1 && echo "  ✓ codespell" || echo "  ✗ codespell"
command -v vale >/dev/null 2>&1      && echo "  ✓ vale"      || echo "  ✗ vale"
command -v lychee >/dev/null 2>&1    && echo "  ✓ lychee"    || echo "  ✗ lychee"
echo ""
echo "Run audit: bash scripts/credibility-audit.sh"
