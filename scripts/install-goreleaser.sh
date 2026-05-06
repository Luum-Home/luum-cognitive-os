#!/usr/bin/env bash
# SCOPE: os-only
# PURPOSE: Install and smoke-test GoReleaser for the COS binary release pipeline.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODE="check"
RUN_SNAPSHOT=false

usage() {
  cat <<'EOF'
Usage: scripts/install-goreleaser.sh [--check|--install] [--snapshot-smoke]

Modes:
  --check           Verify GoReleaser is installed and validate .goreleaser.yaml.
  --install         Install GoReleaser through the platform package manager.
  --snapshot-smoke  After check/install, run `goreleaser release --snapshot --clean --skip=publish`.

Install strategy:
  macOS + Homebrew: brew install goreleaser
  fallback with Go: go install github.com/goreleaser/goreleaser/v2@latest

The script never reads or copies credentials. Real publishing remains CI/tag-driven.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE="check" ;;
    --install) MODE="install" ;;
    --snapshot-smoke) RUN_SNAPSHOT=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

install_goreleaser() {
  if command -v goreleaser >/dev/null 2>&1; then
    echo "goreleaser already installed: $(command -v goreleaser)"
    goreleaser --version | head -5
    return 0
  fi
  if command -v brew >/dev/null 2>&1; then
    echo "Installing GoReleaser via Homebrew..."
    brew install goreleaser
    return 0
  fi
  if command -v go >/dev/null 2>&1; then
    echo "Installing GoReleaser via go install..."
    go install github.com/goreleaser/goreleaser/v2@latest
    return 0
  fi
  echo "GoReleaser install failed: neither brew nor go is available." >&2
  return 1
}

check_goreleaser() {
  if ! command -v goreleaser >/dev/null 2>&1; then
    echo "GoReleaser is not installed. Run: scripts/install-goreleaser.sh --install" >&2
    return 1
  fi
  echo "GoReleaser binary: $(command -v goreleaser)"
  goreleaser --version | head -5
  (cd "$PROJECT_ROOT" && goreleaser check)
}

run_snapshot_smoke() {
  echo "Running GoReleaser snapshot smoke (no publish)..."
  (cd "$PROJECT_ROOT" && goreleaser release --snapshot --clean --skip=publish)
}

if [ "$MODE" = "install" ]; then
  install_goreleaser
fi
check_goreleaser
if [ "$RUN_SNAPSHOT" = true ]; then
  run_snapshot_smoke
fi
