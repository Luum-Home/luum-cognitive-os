#!/usr/bin/env bash
# SCOPE: os-only
# demo-first-run-onboarding.sh - prove first-run onboarding is one-pass.
#
# This script is intentionally product-facing: it installs Cognitive OS into a
# throwaway project, validates the visible next steps, checks status, and fails
# if the core first-run path exceeds its latency budget.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
KEEP=false
HARNESS="codex"

INSTALL_BUDGET_MS="${COS_ONBOARDING_INSTALL_BUDGET_MS:-30000}"
STATUS_BUDGET_MS="${COS_ONBOARDING_STATUS_BUDGET_MS:-5000}"
TOTAL_BUDGET_MS="${COS_ONBOARDING_TOTAL_BUDGET_MS:-40000}"

usage() {
  cat <<'EOF'
demo-first-run-onboarding.sh - prove Cognitive OS first-run onboarding

Usage:
  bash scripts/demo-first-run-onboarding.sh [--harness codex|claude] [--keep]

What it proves:
  - A new project can reach an installed baseline with one installer command.
  - The installer prints clear next checks and active harness settings.
  - cos-status can inspect the installed project through COGNITIVE_OS_PROJECT_DIR.
  - The core onboarding path stays inside explicit latency budgets.

Default budgets:
  install <= 30000 ms
  status  <= 5000 ms
  total   <= 40000 ms

Override budgets with:
  COS_ONBOARDING_INSTALL_BUDGET_MS
  COS_ONBOARDING_STATUS_BUDGET_MS
  COS_ONBOARDING_TOTAL_BUDGET_MS

Flags:
  --harness NAME  Harness projection target: codex or claude (default: codex)
  --keep          Keep the temp project for manual inspection
  --help, -h      Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --harness)
      if [ -z "${2:-}" ]; then
        echo "FAIL --harness requires codex or claude" >&2
        exit 2
      fi
      HARNESS="$2"
      shift 2
      ;;
    --harness=*)
      HARNESS="${1#--harness=}"
      shift
      ;;
    --keep)
      KEEP=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$HARNESS" in
  codex|claude) ;;
  *)
    echo "FAIL unsupported harness: $HARNESS" >&2
    exit 2
    ;;
esac

if ! command -v python3 >/dev/null 2>&1; then
  echo "FAIL python3 is required for portable timing." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "FAIL jq is required for settings projection and status validation." >&2
  exit 1
fi

now_ms() {
  python3 -c 'import time; print(int(time.monotonic() * 1000))'
}

pass() {
  printf 'PASS %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  exit 1
}

assert_under_budget() {
  local label="$1"
  local elapsed_ms="$2"
  local budget_ms="$3"
  if [ "$elapsed_ms" -gt "$budget_ms" ]; then
    fail "$label exceeded budget: ${elapsed_ms}ms > ${budget_ms}ms"
  fi
  pass "$label within budget: ${elapsed_ms}ms <= ${budget_ms}ms"
}

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/cos-first-run.XXXXXX")"
PROJECT_DIR="$TMP_ROOT/project"
INSTALL_LOG="$TMP_ROOT/install.log"
STATUS_JSON="$TMP_ROOT/status.json"
mkdir -p "$PROJECT_DIR"

cleanup() {
  if [ "$KEEP" = true ]; then
    echo "Keeping first-run project under: $TMP_ROOT"
  else
    rm -rf "$TMP_ROOT"
  fi
}
trap cleanup EXIT

total_start="$(now_ms)"

echo "==> Installing Cognitive OS into a fresh project"
install_start="$(now_ms)"
(
  cd "$PROJECT_DIR"
  "$COS_REPO/install.sh" \
    --from "$COS_REPO" \
    --harness="$HARNESS" \
    --force \
    --skip-manifest-check >"$INSTALL_LOG"
)
install_end="$(now_ms)"
install_ms=$((install_end - install_start))

grep -q "Cognitive OS installed successfully" "$INSTALL_LOG" || fail "installer did not report success"
grep -q "Harness:        $HARNESS" "$INSTALL_LOG" || fail "installer did not report active harness"
grep -q "Settings:" "$INSTALL_LOG" || fail "installer did not report settings driver"
grep -q "Next checks:" "$INSTALL_LOG" || fail "installer did not print next checks"
pass "Installer reports success, harness, settings, and next checks"

case "$HARNESS" in
  codex)
    [ -f "$PROJECT_DIR/.codex/hooks.json" ] || fail "missing .codex/hooks.json"
    grep -q "CODEX_PROJECT_DIR" "$PROJECT_DIR/.codex/hooks.json" || fail "Codex settings missing CODEX_PROJECT_DIR"
    ;;
  claude)
    [ -f "$PROJECT_DIR/.claude/settings.json" ] || fail "missing .claude/settings.json"
    grep -q "CLAUDE_PROJECT_DIR" "$PROJECT_DIR/.claude/settings.json" || fail "Claude settings missing CLAUDE_PROJECT_DIR"
    ;;
esac

[ -d "$PROJECT_DIR/.cognitive-os/hooks/cos" ] || fail "missing core hooks"
[ -d "$PROJECT_DIR/.cognitive-os/skills/cos" ] || fail "missing core skills"
[ -d "$PROJECT_DIR/.cognitive-os/templates/cos" ] || fail "missing core templates"
pass "Core .cognitive-os artifacts installed"
assert_under_budget "install" "$install_ms" "$INSTALL_BUDGET_MS"

echo "==> Inspecting installed state"
status_start="$(now_ms)"
COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR" bash "$COS_REPO/scripts/cos-status.sh" --json >"$STATUS_JSON"
status_end="$(now_ms)"
status_ms=$((status_end - status_start))

jq -e '.health != null' "$STATUS_JSON" >/dev/null || fail "cos-status JSON missing health"
jq -e '.skills.kernel_installed > 0' "$STATUS_JSON" >/dev/null || fail "cos-status did not see canonical skills"
jq -e '.hooks.total > 0' "$STATUS_JSON" >/dev/null || fail "cos-status did not see wired hooks"
pass "cos-status reports health, canonical skills, and wired hooks"
assert_under_budget "status" "$status_ms" "$STATUS_BUDGET_MS"

total_end="$(now_ms)"
total_ms=$((total_end - total_start))
assert_under_budget "total first-run" "$total_ms" "$TOTAL_BUDGET_MS"

echo ""
echo "First-run onboarding proof complete."
echo "Harness:        $HARNESS"
echo "Install time:   ${install_ms}ms"
echo "Status time:    ${status_ms}ms"
echo "Total time:     ${total_ms}ms"
echo "Temp project:   $PROJECT_DIR"
