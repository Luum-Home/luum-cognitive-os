#!/usr/bin/env bash
# coverage-report.sh — Agent OS Coverage Report
#
# Measures 4 dimensions of coverage for an AI agent system where
# "code" includes bash hooks, markdown skills, rules, and orchestration flows.
#
# Tests are Python files under tests/. The script searches for references
# to each component using both hyphenated and underscored name variants.
#
# Usage: bash tests/coverage-report.sh
#
# This is a reporting tool — always exits 0.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ---------------------------------------------------------------------------
# Color support
# ---------------------------------------------------------------------------
if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
  GREEN=$(tput setaf 2)
  RED=$(tput setaf 1)
  CYAN=$(tput setaf 6)
  BOLD=$(tput bold)
  DIM=$(tput dim)
  RESET=$(tput sgr0)
else
  GREEN="" RED="" CYAN="" BOLD="" DIM="" RESET=""
fi

PASS="${GREEN}✅${RESET}"
FAIL="${RED}❌${RESET}"

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
TOTAL_COVERED=0
TOTAL_ITEMS=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Print a dimension header
dim_header() {
  echo ""
  echo "${BOLD}$1${RESET}"
}

# Print a coverage line: item status [details]
cov_line() {
  local item="$1" status="$2" detail="${3:-}"
  if [ "$status" = "pass" ]; then
    printf "  %-38s %s %s\n" "$item" "$PASS" "${DIM}${detail}${RESET}"
  else
    printf "  %-38s %s %s\n" "$item" "$FAIL" "${DIM}no test${RESET}"
  fi
}

# Print a dimension summary
dim_summary() {
  local covered=$1 total=$2
  local pct=0
  [ "$total" -gt 0 ] && pct=$(( covered * 100 / total ))
  echo "  ${BOLD}Coverage: ${covered}/${total} (${pct}%)${RESET}"
}

# Build a grep pattern that matches both hyphenated and underscored variants.
# E.g. "circuit-breaker" -> "circuit[-_]breaker"
flexible_pattern() {
  local name="$1"
  # Replace hyphens and underscores with [-_] character class
  echo "$name" | sed 's/[-_]/[-_]/g'
}

# Check if any Python test file references a pattern.
# Searches all .py files under tests/ (excluding conftest.py and __init__.py).
# Returns 0 if found, prints matching basenames to stdout.
tests_referencing() {
  local pattern="$1"
  grep -rlE "$pattern" \
    "$SCRIPT_DIR"/../tests/ \
    --include='*.py' \
    2>/dev/null \
  | grep -v 'conftest\.py' \
  | grep -v '__init__\.py' \
  | xargs -I{} basename {} .py 2>/dev/null \
  | sort -u || true
}

# =========================================================================
# Dimension 1: Infrastructure Coverage (hooks/_lib/ -> tests/)
# =========================================================================
dim_header "Infrastructure Coverage (hooks/_lib/ → tests/):"

d1_covered=0
d1_total=0

for lib in "$ROOT_DIR"/hooks/_lib/*.sh; do
  [ -f "$lib" ] || continue
  lib_name=$(basename "$lib" .sh)
  d1_total=$((d1_total + 1))

  pattern=$(flexible_pattern "$lib_name")
  matches=$(tests_referencing "$pattern")
  if [ -n "$matches" ]; then
    detail=$(echo "$matches" | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
    cov_line "$lib_name.sh" "pass" "$detail"
    d1_covered=$((d1_covered + 1))
  else
    cov_line "$lib_name.sh" "fail"
  fi
done

dim_summary $d1_covered $d1_total
TOTAL_COVERED=$((TOTAL_COVERED + d1_covered))
TOTAL_ITEMS=$((TOTAL_ITEMS + d1_total))

# =========================================================================
# Dimension 2: Skill Path Coverage (skills/ -> tests/)
# =========================================================================
dim_header "Skill Coverage (skills/ → tests/):"

d2_covered=0
d2_total=0

for skill_dir in "$ROOT_DIR"/skills/*/; do
  [ -d "$skill_dir" ] || continue
  skill_name=$(basename "$skill_dir")
  # Skip non-skill entries
  [ "$skill_name" = "auto-generated" ] && continue
  [ "$skill_name" = "arena" ] && continue
  d2_total=$((d2_total + 1))

  pattern=$(flexible_pattern "$skill_name")
  matches=$(tests_referencing "$pattern")
  if [ -n "$matches" ]; then
    detail=$(echo "$matches" | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
    cov_line "$skill_name" "pass" "$detail"
    d2_covered=$((d2_covered + 1))
  else
    cov_line "$skill_name" "fail"
  fi
done

dim_summary $d2_covered $d2_total
TOTAL_COVERED=$((TOTAL_COVERED + d2_covered))
TOTAL_ITEMS=$((TOTAL_ITEMS + d2_total))

# =========================================================================
# Dimension 3: State Transition Coverage (SDD flow)
# =========================================================================
dim_header "State Transition Coverage (SDD flow):"

d3_covered=0
d3_total=0

# Each entry: "label|grep_pattern"
TRANSITIONS=(
  "proposal → spec|proposal.to.spec\|proposal.*spec\|sdd[-_]spec"
  "spec → design|spec.to.design\|spec.*design\|sdd[-_]design"
  "design → tasks|design.to.tasks\|design.*tasks\|sdd[-_]tasks"
  "tasks → apply|tasks.to.apply\|tasks.*apply\|sdd[-_]apply"
  "apply → verify|apply.to.verify\|apply.*verify\|sdd[-_]verify\|gen[-_]eval[-_]loop\|eval.*loop"
  "verify(PASS) → archive|verify.pass\|verify.*archive\|sdd[-_]archive"
  "verify(FAIL) → retry|verify.fail\|fail.*retry\|retry.*apply\|remediation\|auto[-_]repair\|gen[-_]eval[-_]loop"
  "retry(max) → escalate|retry.*max\|max.*retry\|escalat\|circuit[-_]breaker\|gen[-_]eval[-_]loop"
)

for entry in "${TRANSITIONS[@]}"; do
  label="${entry%%|*}"
  pattern="${entry##*|}"
  d3_total=$((d3_total + 1))

  matches=$(tests_referencing "$pattern")
  if [ -n "$matches" ]; then
    detail=$(echo "$matches" | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
    cov_line "$label" "pass" "$detail"
    d3_covered=$((d3_covered + 1))
  else
    cov_line "$label" "fail"
  fi
done

dim_summary $d3_covered $d3_total
TOTAL_COVERED=$((TOTAL_COVERED + d3_covered))
TOTAL_ITEMS=$((TOTAL_ITEMS + d3_total))

# =========================================================================
# Dimension 4: Hook Coverage (hooks/ -> tests/)
# =========================================================================
dim_header "Hook Coverage (hooks/ → tests/):"

d4_covered=0
d4_total=0

for hook in "$ROOT_DIR"/hooks/*.sh; do
  [ -f "$hook" ] || continue
  hook_name=$(basename "$hook" .sh)
  d4_total=$((d4_total + 1))

  pattern=$(flexible_pattern "$hook_name")
  matches=$(tests_referencing "$pattern")
  if [ -n "$matches" ]; then
    detail=$(echo "$matches" | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')
    cov_line "$hook_name.sh" "pass" "$detail"
    d4_covered=$((d4_covered + 1))
  else
    cov_line "$hook_name.sh" "fail"
  fi
done

dim_summary $d4_covered $d4_total
TOTAL_COVERED=$((TOTAL_COVERED + d4_covered))
TOTAL_ITEMS=$((TOTAL_ITEMS + d4_total))

# =========================================================================
# Summary
# =========================================================================
echo ""
echo "${BOLD}=== Summary ===${RESET}"

pct() { local c=$1 t=$2; [ "$t" -gt 0 ] && echo $(( c * 100 / t )) || echo 0; }

printf "  %-22s %3s%% (%d/%d)\n" "Infrastructure:" "$(pct $d1_covered $d1_total)" $d1_covered $d1_total
printf "  %-22s %3s%% (%d/%d)\n" "Skills:" "$(pct $d2_covered $d2_total)" $d2_covered $d2_total
printf "  %-22s %3s%% (%d/%d)\n" "State Transitions:" "$(pct $d3_covered $d3_total)" $d3_covered $d3_total
printf "  %-22s %3s%% (%d/%d)\n" "Hooks:" "$(pct $d4_covered $d4_total)" $d4_covered $d4_total
echo "  ──────────────────────────────"
printf "  %-22s %3s%% (%d/%d)\n" "${BOLD}Composite:${RESET}" "$(pct $TOTAL_COVERED $TOTAL_ITEMS)" $TOTAL_COVERED $TOTAL_ITEMS
echo ""

exit 0
