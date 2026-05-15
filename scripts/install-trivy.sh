#!/usr/bin/env bash
# SCOPE: both
# install-trivy.sh — Install Trivy multi-stack license + vuln scanner
#
# Trivy (Aqua Security, Apache 2.0) is the recommended cross-stack license
# audit tool for Cognitive OS pre-launch. Single binary covers Python, Go,
# Node, Rust, Java, C#, container images, and IaC.
#
# See: .cognitive-os/strategy/research/11-cross-stack-license-audit-tools.md
set -euo pipefail

echo "Installing Trivy (cross-stack license + vulnerability scanner)..."
echo ""

cat <<'WARN'
WARNING: ADR-212 treats Trivy as optional secondary scanner only.
A March 2026 supply-chain incident affected Trivy v0.69.4 and related GitHub
Actions/tags. Do not use aquasecurity/trivy-action or setup-trivy by mutable tag.
Run `scripts/cos license audit --json` after install to verify local posture.
WARN


# Detect OS and choose install path
OS="$(uname -s)"

install_via_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    return 1
  fi
  echo "Homebrew detected. Installing via brew..."
  brew install trivy
}

install_via_curl() {
  echo "Installing via official install script (Linux fallback)..."
  local install_dir="${HOME}/.local/bin"
  mkdir -p "${install_dir}"
  curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
    | sh -s -- -b "${install_dir}"
  echo ""
  echo "Trivy installed to ${install_dir}/trivy"
  echo "Ensure ${install_dir} is in your PATH."
}

install_via_go() {
  echo "Falling back to 'go install'..."
  if ! command -v go >/dev/null 2>&1; then
    echo "ERROR: Go is not installed. Cannot fall back."
    echo "Install Go from https://go.dev/dl/ or via your package manager."
    exit 1
  fi
  go install github.com/aquasecurity/trivy/cmd/trivy@latest
}

case "${OS}" in
  Darwin)
    if ! install_via_brew; then
      echo "Homebrew not available; trying curl-based install..."
      install_via_curl || install_via_go
    fi
    ;;
  Linux)
    if ! install_via_brew; then
      install_via_curl || install_via_go
    fi
    ;;
  *)
    echo "Unrecognized OS: ${OS}. Trying go install fallback..."
    install_via_go
    ;;
esac

echo ""
if command -v trivy >/dev/null 2>&1; then
  echo "Trivy installed: $(trivy --version 2>/dev/null | head -1 || echo 'check PATH')"
else
  echo "WARNING: trivy binary not on PATH after install."
  echo "Check ~/.local/bin or your Go bin path and add to PATH if needed."
fi

echo ""
echo "Installation complete."
echo ""
echo "Next steps:"
echo "  1. Run a baseline license audit:"
echo "     bash scripts/license-audit-trivy.sh"
echo ""
echo "  2. (Optional) Install Syft+Grype for cross-validation:"
echo "     bash scripts/install-syft-grype.sh"
echo ""
echo "  3. (Optional) Quick smoke test:"
echo "     trivy fs --scanners license --severity UNKNOWN,HIGH,CRITICAL ."
echo ""
echo "Reference: .cognitive-os/strategy/research/11-cross-stack-license-audit-tools.md"
