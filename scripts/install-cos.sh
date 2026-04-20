#!/usr/bin/env bash
# SCOPE: os-only
# install-cos.sh — One-liner installer for Cognitive OS (cos CLI)
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Luum-Home/luum-cognitive-os/main/scripts/install-cos.sh | bash
#   bash <(curl -fsSL https://raw.githubusercontent.com/Luum-Home/luum-cognitive-os/main/scripts/install-cos.sh)
#
# Environment variables:
#   COS_VERSION   Override the version to install (default: latest)
#   COS_INSTALL   Override install directory (default: /usr/local/bin or ~/.local/bin)
#
set -euo pipefail

REPO="Luum-Home/luum-cognitive-os"

# ── Detect OS and architecture ──────────────────────────────────────
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
  x86_64)  ARCH="amd64" ;;
  aarch64) ARCH="arm64" ;;
  arm64)   ARCH="arm64" ;;
  *)
    echo "Error: Unsupported architecture: $ARCH"
    exit 1
    ;;
esac

case "$OS" in
  linux|darwin) ;;
  mingw*|msys*|cygwin*)
    OS="windows"
    ;;
  *)
    echo "Error: Unsupported OS: $OS"
    exit 1
    ;;
esac

echo "Cognitive OS Installer"
echo "  OS:   $OS"
echo "  Arch: $ARCH"
echo ""

# ── Method 1: Install via Go (preferred if available) ───────────────
if command -v go &>/dev/null; then
  echo "Go detected. Installing cos via go install..."
  go install "github.com/${REPO}/cmd/cos@latest" 2>/dev/null && {
    echo ""
    echo "+ cos installed via go install"
    COS_BIN=$(go env GOPATH)/bin/cos
    if [ -f "$COS_BIN" ]; then
      echo "  Binary: $COS_BIN"
      echo "  Version: $($COS_BIN version 2>/dev/null || echo 'installed')"
    fi
    echo ""
    echo "Quick start:"
    echo "  cos new my-project --template go    # create a new project"
    echo "  cos init                            # add COS to existing project"
    echo "  cos status                          # check installation"
    exit 0
  } || {
    echo "go install failed. Falling back to binary download..."
  }
fi

# ── Method 2: Download pre-built binary ─────────────────────────────
echo "Downloading pre-built binary..."

# Determine version.
VERSION="${COS_VERSION:-}"
if [ -z "$VERSION" ]; then
  echo "  Fetching latest release..."
  VERSION=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null | grep '"tag_name"' | head -1 | cut -d'"' -f4 || true)
  if [ -z "$VERSION" ]; then
    echo "Error: Could not determine latest version."
    echo "Set COS_VERSION manually: COS_VERSION=v0.2.0 bash install-cos.sh"
    exit 1
  fi
fi

echo "  Version: $VERSION"

# Build download URL.
BINARY_NAME="cos-${OS}-${ARCH}"
if [ "$OS" = "windows" ]; then
  BINARY_NAME="${BINARY_NAME}.exe"
fi
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${BINARY_NAME}"

echo "  Downloading: $DOWNLOAD_URL"

TMP_DIR=$(mktemp -d)
TMP_BIN="${TMP_DIR}/cos"
trap 'rm -rf "$TMP_DIR"' EXIT

if ! curl -fsSL "$DOWNLOAD_URL" -o "$TMP_BIN" 2>/dev/null; then
  echo ""
  echo "Error: Download failed."
  echo "  URL: $DOWNLOAD_URL"
  echo ""
  echo "Pre-built binaries may not be available yet."
  echo "Install from source instead:"
  echo "  git clone https://github.com/${REPO}.git"
  echo "  cd luum-cognitive-os && go install ./cmd/cos"
  exit 1
fi

chmod +x "$TMP_BIN"

# ── Install to PATH ────────────────────────────────────────────────
INSTALL_DIR="${COS_INSTALL:-}"

if [ -z "$INSTALL_DIR" ]; then
  if [ -w /usr/local/bin ]; then
    INSTALL_DIR="/usr/local/bin"
  else
    INSTALL_DIR="${HOME}/.local/bin"
    mkdir -p "$INSTALL_DIR"
  fi
fi

DEST="${INSTALL_DIR}/cos"
mv "$TMP_BIN" "$DEST"

echo ""
echo "+ cos installed to: $DEST"

# Ensure the install dir is in PATH.
case ":${PATH}:" in
  *":${INSTALL_DIR}:"*) ;;
  *)
    echo ""
    echo "Add $INSTALL_DIR to your PATH:"
    SHELL_NAME=$(basename "${SHELL:-/bin/bash}")
    case "$SHELL_NAME" in
      zsh)   echo "  echo 'export PATH=\"${INSTALL_DIR}:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
      fish)  echo "  fish_add_path ${INSTALL_DIR}" ;;
      *)     echo "  echo 'export PATH=\"${INSTALL_DIR}:\$PATH\"' >> ~/.bashrc && source ~/.bashrc" ;;
    esac
    ;;
esac

# ── Verify ──────────────────────────────────────────────────────────
echo ""
if command -v cos &>/dev/null; then
  echo "Verified: $(cos version 2>/dev/null || echo 'cos is ready')"
else
  echo "Installed. Restart your shell or add $INSTALL_DIR to PATH to use cos."
fi

echo ""
echo "Quick start:"
echo "  cos new my-project --template go    # create a new project"
echo "  cos init                            # add COS to existing project"
echo "  cos status                          # check installation"
