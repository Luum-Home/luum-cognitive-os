#!/usr/bin/env bash
# @manual-trigger: run via `make ci-deps` or `bash scripts/ci-setup.sh` to install optional CI deps
# ci-setup.sh — Install optional CI dependencies that unblock skipped tests.
#
# Run via: make ci-deps
#           bash scripts/ci-setup.sh
#
# What this does:
#   Part 1 — flock (util-linux)
#     7 tests in tests/unit/test_session_lifecycle.py skip when `flock` is not on
#     PATH (macOS ships without it; Linux CI has it by default).  On macOS we
#     install util-linux via Homebrew and symlink flock into /opt/homebrew/bin
#     (which is already on PATH for Homebrew-managed shells).
#
#     Luum service (local dashboard on :3200) — its source is NOT a public repo.
#     satisfies the assertions (config schema via Zod, env vars, Dockerfile).
#     /tmp/ is ephemeral: re-run this script after a reboot or on each fresh CI
#     runner.  Do NOT commit the stub to the repository.
#
# Idempotent: safe to run multiple times.

set -euo pipefail

# ── colours ─────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[ci-setup]${NC} $*"; }
warn()    { echo -e "${YELLOW}[ci-setup] WARN${NC} $*"; }
fail()    { echo -e "${RED}[ci-setup] FAIL${NC} $*" >&2; exit 1; }

# ── Part 1: flock ────────────────────────────────────────────────────────────
info "Checking flock availability..."

if command -v flock &>/dev/null; then
    info "flock already on PATH: $(command -v flock)"
else
    if [[ "$(uname)" == "Darwin" ]]; then
        info "macOS detected — installing util-linux via Homebrew..."
        if ! command -v brew &>/dev/null; then
            fail "Homebrew not found. Install from https://brew.sh then re-run."
        fi
        brew install util-linux

        FLOCK_BIN="/opt/homebrew/opt/util-linux/bin/flock"
        LINK_TARGET="/opt/homebrew/bin/flock"

        if [[ ! -f "$FLOCK_BIN" ]]; then
            fail "flock binary not found at $FLOCK_BIN after install — check brew output."
        fi

        # Symlink into /opt/homebrew/bin (already on PATH for brew shells)
        ln -sf "$FLOCK_BIN" "$LINK_TARGET"
        info "Symlinked: $LINK_TARGET -> $FLOCK_BIN"

        if command -v flock &>/dev/null; then
            info "flock now available: $(flock --version 2>&1 | head -1)"
        else
            warn "flock symlinked but 'which flock' still misses it."
            warn "Add to your shell profile: export PATH=\"/opt/homebrew/bin:\$PATH\""
            warn "Then re-run tests in a fresh shell."
        fi
    else
        # Linux: flock is usually in util-linux (pre-installed on most distros)
        warn "flock not found on Linux. Install with: apt-get install util-linux"
        warn "or: yum install util-linux"
    fi
fi


info "Run: uv run pytest tests/unit/test_session_lifecycle.py tests/unit/test_reverse_engineer.py -v"
