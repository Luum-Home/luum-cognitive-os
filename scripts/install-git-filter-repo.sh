#!/usr/bin/env bash
# SCOPE: os-only
# install-git-filter-repo.sh — Install git-filter-repo for ADR-218 history sanitization
#
# git-filter-repo (MIT) is the modern replacement for the deprecated
# git-filter-branch. It is the canonical tool for ADR-218
# `cos history sanitize --execute` and is required only when the operator
# runs the destructive rewrite path; the dry-run path does NOT need it.
#
# Install order (first available wins):
#   1. brew (macOS / Linux Homebrew)
#   2. apt-get (Debian / Ubuntu)
#   3. pip --user (cross-platform fallback; ships the `git-filter-repo` script)
#
# References:
#   - ADR-218 §"Implementation slices" — slice 3 calls for this script
#   - upstream: https://github.com/newren/git-filter-repo
#
set -euo pipefail

echo "Installing git-filter-repo (ADR-218 history-sanitize execute path)..."
echo ""

OS="$(uname -s)"

if command -v git-filter-repo >/dev/null 2>&1; then
  echo "  ✓ git-filter-repo already installed"
  git-filter-repo --version 2>&1 | sed 's/^/    /'
  exit 0
fi

install_via_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    return 1
  fi
  echo "Homebrew detected. Installing via brew..."
  brew install git-filter-repo
}

install_via_apt() {
  if ! command -v apt-get >/dev/null 2>&1; then
    return 1
  fi
  echo "apt-get detected. Installing via apt-get..."
  sudo apt-get update
  sudo apt-get install -y git-filter-repo
}

install_via_pip() {
  if ! command -v pip3 >/dev/null 2>&1 && ! command -v pip >/dev/null 2>&1; then
    return 1
  fi
  PIP_BIN="$(command -v pip3 || command -v pip)"
  echo "pip detected (${PIP_BIN}). Installing via pip --user..."
  "${PIP_BIN}" install --user git-filter-repo
  USER_BIN="$(python3 -m site --user-base 2>/dev/null)/bin"
  if [ -d "${USER_BIN}" ]; then
    echo ""
    echo "  Note: ensure ${USER_BIN} is in your PATH."
    case ":${PATH}:" in
      *":${USER_BIN}:"*) ;;
      *)
        echo "  Add to your shell rc:"
        echo "    export PATH=\"${USER_BIN}:\$PATH\""
        ;;
    esac
  fi
}

case "${OS}" in
  Darwin)
    install_via_brew || install_via_pip || {
      echo "  ✗ install git-filter-repo manually: https://github.com/newren/git-filter-repo#installation"
      exit 1
    }
    ;;
  Linux)
    install_via_brew || install_via_apt || install_via_pip || {
      echo "  ✗ install git-filter-repo manually: https://github.com/newren/git-filter-repo#installation"
      exit 1
    }
    ;;
  *)
    echo "ERROR: Unsupported OS: ${OS}. git-filter-repo supports macOS, Linux, and Windows (manual)."
    exit 1
    ;;
esac

echo ""
if command -v git-filter-repo >/dev/null 2>&1; then
  echo "  ✓ git-filter-repo installed: $(git-filter-repo --version 2>&1 | head -1)"
else
  echo "  ⚠ git-filter-repo not on PATH — check installation output above."
  exit 1
fi

echo ""
echo "Installation complete."
echo ""
echo "Next steps:"
echo "  1. Run dry-run with env vars seeded:"
echo "     export COS_HISTORY_SANITIZE_OPERATOR_EMAIL=...  # email to redact"
echo "     export COS_HISTORY_SANITIZE_HOME_PREFIX=...     # /home or /Users prefix"
echo "     export COS_HISTORY_SANITIZE_REPO_PATH=...       # absolute repo path"
echo "     bash scripts/cos history sanitize --dry-run --json | jq ."
echo ""
echo "  2. Inspect counts and preserve_conflicts (must be empty)."
echo ""
echo "  3. Execute (destructive, requires COS_ALLOW_DESTRUCTIVE_GIT=1):"
echo "     COS_ALLOW_DESTRUCTIVE_GIT=1 \\"
echo "       bash scripts/cos history sanitize --execute --json"
echo ""
echo "Reference: docs/02-Decisions/adrs/ADR-218-history-sanitization-toolchain.md"
