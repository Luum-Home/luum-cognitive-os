#!/usr/bin/env bash
# SCOPE: both
# install-obsidian-local.sh — Install or validate local Obsidian on macOS.
#
# Uses Homebrew Cask because the official Obsidian download is a macOS app and
# Homebrew tracks the same cask-managed application plus the `obsidian` CLI shim.
#
# Usage:
#   bash scripts/install-obsidian-local.sh            # install if absent; validate if present
#   bash scripts/install-obsidian-local.sh --status   # report current state only
#   bash scripts/install-obsidian-local.sh --force    # overwrite an existing unmanaged Obsidian.app
#   bash scripts/install-obsidian-local.sh --open     # open Obsidian after install/validation

set -uo pipefail

APP_PATH="/Applications/Obsidian.app"
BREW_BIN="${BREW:-brew}"
PLIST_BUDDY="/usr/libexec/PlistBuddy"
OPEN_AFTER=false
STATUS_ONLY=false
FORCE_INSTALL=false

usage() {
  cat <<'EOF'
Usage: bash scripts/install-obsidian-local.sh [--status] [--force] [--open]

Options:
  --status   Report current local Obsidian state without installing.
  --force    Pass --force to Homebrew Cask, replacing an existing Obsidian.app.
  --open     Open Obsidian after installation/validation.
  --help     Show this help.

Install path:
  /Applications/Obsidian.app

Homebrew cask:
  brew install --cask obsidian
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --status)
      STATUS_ONLY=true
      ;;
    --force)
      FORCE_INSTALL=true
      ;;
    --open)
      OPEN_AFTER=true
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "[obsidian-local] Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

_is_macos() {
  [ "$(uname -s)" = "Darwin" ]
}

_have_brew() {
  command -v "$BREW_BIN" >/dev/null 2>&1
}

_app_version() {
  if [ -d "$APP_PATH" ] && [ -x "$PLIST_BUDDY" ]; then
    "$PLIST_BUDDY" -c 'Print :CFBundleShortVersionString' "$APP_PATH/Contents/Info.plist" 2>/dev/null || true
  fi
}

_cask_installed() {
  _have_brew && "$BREW_BIN" list --cask obsidian >/dev/null 2>&1
}

_print_status() {
  local app_state="missing"
  local cask_state="not-installed"
  local cli_state="missing"
  local version=""

  if [ -d "$APP_PATH" ]; then
    app_state="present"
    version="$(_app_version)"
  fi
  if _cask_installed; then
    cask_state="installed"
  fi
  if command -v obsidian >/dev/null 2>&1; then
    cli_state="$(command -v obsidian)"
  fi

  echo "[obsidian-local] app=${app_state} path=${APP_PATH} version=${version:-unknown}"
  echo "[obsidian-local] homebrew-cask=${cask_state}"
  echo "[obsidian-local] cli=${cli_state}"
}

if ! _is_macos; then
  echo "[obsidian-local] This installer currently supports macOS only." >&2
  exit 2
fi

if [ "$STATUS_ONLY" = true ]; then
  _print_status
  exit 0
fi

if ! _have_brew; then
  echo "[obsidian-local] Homebrew is required for managed installation." >&2
  echo "[obsidian-local] Install Homebrew first: https://brew.sh/" >&2
  exit 2
fi

if _cask_installed; then
  echo "[obsidian-local] Obsidian Homebrew cask already installed. Upgrading if needed..." >&2
  "$BREW_BIN" upgrade --cask obsidian || true
elif [ -d "$APP_PATH" ] && [ "$FORCE_INSTALL" != true ]; then
  echo "[obsidian-local] Found existing unmanaged ${APP_PATH}." >&2
  echo "[obsidian-local] Leaving it untouched. Re-run with --force to replace it via Homebrew Cask." >&2
else
  args=(install --cask obsidian)
  if [ "$FORCE_INSTALL" = true ]; then
    args+=(--force)
  fi
  "$BREW_BIN" "${args[@]}"
fi

_print_status

if [ "$OPEN_AFTER" = true ]; then
  open -a Obsidian
fi
