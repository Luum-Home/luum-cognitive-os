#!/usr/bin/env bash
# SCOPE: os-only
# @manual-trigger: invoke `bash scripts/lint-shell.sh [--new-only|--baseline]` for shellcheck gate; advisory only until CI-enforced
# lint-shell.sh — ShellCheck gate for all scripts/ and hooks/ shell files.
#
# Usage:
#   scripts/lint-shell.sh              # check all, fail on violations
#   scripts/lint-shell.sh --baseline   # regenerate shellcheck-baseline.txt
#   scripts/lint-shell.sh --new-only   # fail only if NEW violations appear (vs baseline)
#
# Install shellcheck:
#   macOS:   brew install shellcheck
#   Ubuntu:  apt-get install -y shellcheck
#   Alpine:  apk add shellcheck
#   GitHub:  uses: ludeeus/action-shellcheck@master
#
# Suppressed codes:
#   SC1091 — not following external source (sourced files unavailable at lint time)
#   SC2086 — double-quote to prevent word splitting (project style allows unquoted vars)
#
# Exit codes:
#   0  — no violations found (or all violations are in baseline when --new-only)
#   1  — violations found
#   2  — shellcheck not installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BASELINE_FILE="${PROJECT_ROOT}/scripts/shellcheck-baseline.txt"

# Severity: error|warning|info|style
SEVERITY="warning"
# Excluded codes (comma-separated)
EXCLUDE_CODES="SC1091,SC2086"

# ── helpers ──────────────────────────────────────────────────────────────────
err() { printf '%s\n' "$*" >&2; }
info() { printf '%s\n' "$*"; }

# ── check shellcheck is available ────────────────────────────────────────────
if ! command -v shellcheck >/dev/null 2>&1; then
    err "ERROR: shellcheck is not installed."
    err ""
    err "Install instructions:"
    err "  macOS:   brew install shellcheck"
    err "  Ubuntu:  sudo apt-get install -y shellcheck"
    err "  Alpine:  apk add --no-cache shellcheck"
    err "  Fedora:  sudo dnf install ShellCheck"
    err "  GitHub:  uses: ludeeus/action-shellcheck@master"
    err ""
    err "Skipping shellcheck gate (cannot enforce without the tool)."
    exit 2
fi

# ── collect files ─────────────────────────────────────────────────────────────
# Use find with -not -path for cross-platform compatibility (no -prune portability issues)
collect_files() {
    # scripts/*.sh (one level — no subdirs needed)
    find "${PROJECT_ROOT}/scripts" -maxdepth 1 -name "*.sh" -type f | sort

    # hooks/**/*.sh excluding _archived
    find "${PROJECT_ROOT}/hooks" -name "*.sh" -type f \
        | grep -v '/hooks/_archived/' \
        | sort
}

FILES=()
while IFS= read -r f; do
    FILES+=("$f")
done < <(collect_files)

if [ "${#FILES[@]}" -eq 0 ]; then
    info "No shell files found. Nothing to check."
    exit 0
fi

info "shellcheck gate: scanning ${#FILES[@]} files (severity >= ${SEVERITY}, excluded: ${EXCLUDE_CODES})"

# ── run shellcheck ─────────────────────────────────────────────────────────────
TMPOUT="$(mktemp)"
trap 'rm -f "${TMPOUT}"' EXIT

SC_ARGS=(
    --severity="${SEVERITY}"
    --exclude="${EXCLUDE_CODES}"
    --format=gcc      # file:line:col: severity: message [SCxxxx]
    --shell=bash
)

VIOLATION_COUNT=0
shellcheck "${SC_ARGS[@]}" "${FILES[@]}" > "${TMPOUT}" 2>&1 || true

if [ -s "${TMPOUT}" ]; then
    VIOLATION_COUNT="$(wc -l < "${TMPOUT}" | tr -d ' ')"
fi

# ── baseline mode ─────────────────────────────────────────────────────────────
if [ "${1:-}" = "--baseline" ]; then
    cp "${TMPOUT}" "${BASELINE_FILE}"
    info "Baseline captured: ${VIOLATION_COUNT} violations -> ${BASELINE_FILE}"
    exit 0
fi

# ── new-only mode ─────────────────────────────────────────────────────────────
if [ "${1:-}" = "--new-only" ]; then
    if [ ! -f "${BASELINE_FILE}" ]; then
        err "No baseline found at ${BASELINE_FILE}. Run with --baseline first."
        exit 1
    fi

    # Find lines in current output that are NOT in baseline
    NEW_VIOLATIONS="$(comm -23 \
        <(sort "${TMPOUT}") \
        <(sort "${BASELINE_FILE}") || true)"

    if [ -n "${NEW_VIOLATIONS}" ]; then
        err "NEW shellcheck violations (not in baseline):"
        err "${NEW_VIOLATIONS}"
        NEW_COUNT="$(printf '%s\n' "${NEW_VIOLATIONS}" | grep -c . || true)"
        err ""
        err "FAIL: ${NEW_COUNT} new violation(s) detected."
        exit 1
    fi

    info "PASS: no new shellcheck violations (${VIOLATION_COUNT} pre-existing violations in baseline)."
    exit 0
fi

# ── default mode: fail on any violation ──────────────────────────────────────
if [ "${VIOLATION_COUNT}" -gt 0 ]; then
    cat "${TMPOUT}"
    err ""
    err "FAIL: ${VIOLATION_COUNT} shellcheck violation(s) found."
    err ""
    err "Tip: run 'scripts/lint-shell.sh --baseline' to snapshot current violations,"
    err "     then 'scripts/lint-shell.sh --new-only' in CI to only fail on NEW violations."
    exit 1
fi

info "PASS: 0 shellcheck violations."
exit 0
