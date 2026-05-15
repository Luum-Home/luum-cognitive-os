#!/usr/bin/env bash
# SCOPE: both
# install-syft-grype.sh — Install Syft (SBOM generator) + Grype (vuln/license scanner)
#
# Anchore tools (Apache 2.0) used as OPTIONAL cross-validation against Trivy.
# If Trivy and Syft+Grype agree, confidence is high. If they differ,
# investigate the discrepancy.
#
# See: .cognitive-os/strategy/research/11-cross-stack-license-audit-tools.md
set -euo pipefail

echo "Installing Syft (SBOM generator) and Grype (scanner)..."
echo ""

OS="$(uname -s)"
INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "${INSTALL_DIR}"

install_via_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    return 1
  fi
  echo "Homebrew detected. Installing via brew..."
  brew install syft grype
}

install_via_curl() {
  echo "Installing Syft via Anchore install script..."
  curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh \
    | sh -s -- -b "${INSTALL_DIR}"
  echo ""
  echo "Installing Grype via Anchore install script..."
  curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh \
    | sh -s -- -b "${INSTALL_DIR}"
  echo ""
  echo "Tools installed to ${INSTALL_DIR}"
  echo "Ensure ${INSTALL_DIR} is in your PATH."
}

case "${OS}" in
  Darwin|Linux)
    if ! install_via_brew; then
      install_via_curl
    fi
    ;;
  *)
    echo "ERROR: Unsupported OS: ${OS}. Syft/Grype support macOS and Linux."
    exit 1
    ;;
esac

echo ""
if command -v syft >/dev/null 2>&1; then
  echo "Syft installed: $(syft version 2>/dev/null | head -1 || echo 'check PATH')"
fi
if command -v grype >/dev/null 2>&1; then
  echo "Grype installed: $(grype version 2>/dev/null | head -1 || echo 'check PATH')"
fi

echo ""
echo "Installation complete."
echo ""
echo "Next steps:"
echo "  1. Generate SBOM for the repo:"
echo "     syft . -o spdx-json=.cognitive-os/audit/sbom.spdx.json"
echo ""
echo "  2. Scan SBOM for vulns/license risk:"
echo "     grype sbom:.cognitive-os/audit/sbom.spdx.json -o json"
echo ""
echo "  3. Cross-validate against Trivy output:"
echo "     diff <(jq -r '...' trivy-output.json) <(jq -r '...' grype-output.json)"
echo ""
echo "Reference: .cognitive-os/strategy/research/11-cross-stack-license-audit-tools.md"
