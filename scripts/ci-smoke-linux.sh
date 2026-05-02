#!/usr/bin/env bash
# @manual-trigger: run inside ci-linux Docker container or locally as spot-check; not a Claude event hook
# ci-smoke-linux.sh — Linux smoke test for cross-platform discipline.
#
# Intended to run inside the ci-linux Docker container (Ubuntu/Debian),
# but also safe to run on macOS for local spot-checks.
#
# Stages:
#   1. Syntax check (bash -n) on every hook and script
#   2. Portable-helper smoke (if hooks/_lib/portable.sh exists)
#   3. Fast unit tests that exercise shell behaviour
#
# Exit code: 0 = all PASS, 1 = any FAIL

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── colour helpers (graceful on non-tty) ─────────────────────────────────────
if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
    RED="$(tput setaf 1)"
    GREEN="$(tput setaf 2)"
    YELLOW="$(tput setaf 3)"
    RESET="$(tput sgr0)"
else
    RED="" GREEN="" YELLOW="" RESET=""
fi

PASS=0
FAIL=0
SKIP=0

pass()  { PASS=$((PASS+1));  printf '%s[PASS]%s %s\n' "${GREEN}"  "${RESET}" "$*"; }
fail()  { FAIL=$((FAIL+1));  printf '%s[FAIL]%s %s\n' "${RED}"    "${RESET}" "$*" >&2; }
skip()  { SKIP=$((SKIP+1));  printf '%s[SKIP]%s %s\n' "${YELLOW}" "${RESET}" "$*"; }
header(){ printf '\n=== %s ===\n' "$*"; }

# ── Stage 1: bash -n syntax check ─────────────────────────────────────────────
header "Stage 1: bash -n syntax check"

SYNTAX_FAIL=0

check_syntax() {
    local dir="$1"
    local exclude_pattern="${2:-__NOMATCH__}"

    while IFS= read -r f; do
        # Skip if excluded
        if printf '%s' "${f}" | grep -q "${exclude_pattern}"; then
            continue
        fi
        if bash -n "${f}" 2>/tmp/syntax_err_$$; then
            pass "syntax ${f#"${PROJECT_ROOT}/"}"
        else
            fail "syntax ${f#"${PROJECT_ROOT}/"}: $(cat /tmp/syntax_err_$$)"
            SYNTAX_FAIL=$((SYNTAX_FAIL+1))
        fi
    done < <(find "${dir}" -name "*.sh" -type f | sort)
    rm -f /tmp/syntax_err_$$
}

check_syntax "${PROJECT_ROOT}/scripts"
check_syntax "${PROJECT_ROOT}/hooks" "/hooks/_archived/"

if [ "${SYNTAX_FAIL}" -gt 0 ]; then
    fail "Stage 1: ${SYNTAX_FAIL} file(s) failed bash -n syntax check"
else
    pass "Stage 1: all files passed bash -n"
fi

# ── Stage 2: portable.sh helper smoke ─────────────────────────────────────────
header "Stage 2: portable.sh helper smoke"

PORTABLE_SH="${PROJECT_ROOT}/hooks/_lib/portable.sh"

if [ ! -f "${PORTABLE_SH}" ]; then
    skip "hooks/_lib/portable.sh not found (Agent G has not yet created it) — skipping helper smoke"
else
    # Source the library in a subshell to avoid polluting the environment
    if ! (
        # shellcheck source=/dev/null
        . "${PORTABLE_SH}"

        # Probe: each publicly exported function should be callable without error
        # Convention: portable.sh exports functions prefixed with 'portable_' or documented in a
        # PORTABLE_HELPERS variable. We call any functions that were declared in the file.
        FUNCS="$(grep -E '^[a-zA-Z_][a-zA-Z0-9_]*\(\)' "${PORTABLE_SH}" | sed 's/().*//' || true)"
        if [ -z "${FUNCS}" ]; then
            printf '[SKIP] No exported functions detected in portable.sh\n'
            exit 0
        fi

        OK=0; BAD=0
        while IFS= read -r fn; do
            if command -v "${fn}" >/dev/null 2>&1; then
                printf '[PASS] portable function available: %s\n' "${fn}"
                OK=$((OK+1))
            else
                printf '[FAIL] portable function not callable after source: %s\n' "${fn}" >&2
                BAD=$((BAD+1))
            fi
        done <<< "${FUNCS}"
        [ "${BAD}" -eq 0 ]
    ); then
        fail "Stage 2: portable.sh helper smoke failed"
    else
        pass "Stage 2: portable.sh helpers all callable"
    fi
fi

# ── Stage 3: fast unit tests ──────────────────────────────────────────────────
header "Stage 3: pytest unit tests (cross-platform subset)"

if ! command -v python3 >/dev/null 2>&1; then
    skip "python3 not available — skipping pytest stage"
elif ! python3 -m pytest --version >/dev/null 2>&1; then
    skip "pytest not installed — skipping pytest stage (pip install pytest)"
else
    # Tests to run (space-separated, relative to PROJECT_ROOT)
    TESTS=(
        "tests/unit/test_portable_sh.py"
        "tests/unit/test_cross_platform_discipline.py"
        "tests/unit/test_session_leak_detection.py"
    )

    PYTEST_ARGS=(
        --tb=short
        -q
        --no-header
    )

    AVAILABLE_TESTS=()
    for t in "${TESTS[@]}"; do
        if [ -f "${PROJECT_ROOT}/${t}" ]; then
            AVAILABLE_TESTS+=("${t}")
        else
            skip "test file not found (expected, may be created by Agent G): ${t}"
        fi
    done

    if [ "${#AVAILABLE_TESTS[@]}" -eq 0 ]; then
        skip "Stage 3: no target test files present yet"
    else
        cd "${PROJECT_ROOT}"
        if python3 -m pytest "${PYTEST_ARGS[@]}" "${AVAILABLE_TESTS[@]}" 2>&1; then
            pass "Stage 3: pytest passed for ${#AVAILABLE_TESTS[@]} test file(s)"
        else
            fail "Stage 3: pytest failed — see output above"
        fi
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────
header "Summary"
printf 'PASS: %d  FAIL: %d  SKIP: %d\n' "${PASS}" "${FAIL}" "${SKIP}"

if [ "${FAIL}" -gt 0 ]; then
    printf '%sFAIL: CI smoke test did not pass.%s\n' "${RED}" "${RESET}" >&2
    exit 1
fi

printf '%sPASS: CI smoke test completed successfully.%s\n' "${GREEN}" "${RESET}"
exit 0
