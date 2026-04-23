#!/usr/bin/env bash
# SCOPE: os-only
# demo-portability-proof.sh - prove core portability across harness drivers.
#
# This is a product demo, not a benchmark. It installs the same Cognitive OS
# source into two throwaway projects, projects different harness drivers, and
# verifies that the installed core artifacts have the same fingerprint.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COS_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
KEEP=false
RUN_PROVIDER_TESTS=true

usage() {
  cat <<'EOF'
demo-portability-proof.sh - prove Cognitive OS portability across harness drivers

Usage:
  bash scripts/demo-portability-proof.sh [--keep] [--skip-provider-tests]

What it proves:
  - The same source installs into a Codex-projected project and a Claude-projected project.
  - The core .cognitive-os artifacts are identical across both installs.
  - Driver-specific settings land in the expected driver paths.
  - Status tooling can inspect both installs through the canonical project env.
  - Provider/kernel contracts still pass when provider tests are enabled.

Flags:
  --keep                 Keep the temp projects for manual inspection.
  --skip-provider-tests  Skip Go provider/kernel tests for a faster local demo.
  --help, -h             Show this help.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --keep)
      KEEP=true
      shift
      ;;
    --skip-provider-tests)
      RUN_PROVIDER_TESTS=false
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

if ! command -v jq >/dev/null 2>&1; then
  echo "FAIL: jq is required for installer settings projection." >&2
  exit 1
fi

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/cos-portability-demo.XXXXXX")"
CODEX_PROJECT="$TMP_ROOT/codex-project"
CLAUDE_PROJECT="$TMP_ROOT/claude-project"
mkdir -p "$CODEX_PROJECT" "$CLAUDE_PROJECT"

cleanup() {
  if [ "$KEEP" = true ]; then
    echo "Keeping demo projects under: $TMP_ROOT"
  else
    rm -rf "$TMP_ROOT"
  fi
}
trap cleanup EXIT

say() {
  printf '==> %s\n' "$1"
}

pass() {
  printf 'PASS %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  exit 1
}

require_path() {
  local path="$1"
  [ -e "$path" ] || fail "missing expected path: $path"
}

fingerprint_dir() {
  local dir="$1"
  [ -d "$dir" ] || fail "cannot fingerprint missing dir: $dir"
  (
    cd "$dir"
    find . -type f -print | LC_ALL=C sort | while IFS= read -r file; do
      shasum -a 256 "$file"
    done | shasum -a 256 | awk '{print $1}'
  )
}

install_project() {
  local project="$1"
  local harness="$2"
  (
    cd "$project"
    "$COS_REPO/install.sh" \
      --from "$COS_REPO" \
      --harness="$harness" \
      --force \
      --skip-manifest-check >/tmp/cos-demo-install-"$harness".log
  )
}

say "Installing Codex-projected project"
install_project "$CODEX_PROJECT" "codex"
require_path "$CODEX_PROJECT/.cognitive-os"
require_path "$CODEX_PROJECT/.codex/hooks.json"
pass "Codex projection created .codex/hooks.json"

say "Installing Claude-projected project"
install_project "$CLAUDE_PROJECT" "claude"
require_path "$CLAUDE_PROJECT/.cognitive-os"
require_path "$CLAUDE_PROJECT/.claude/settings.json"
pass "Claude projection created .claude/settings.json"

say "Checking status tooling through canonical project env"
COGNITIVE_OS_PROJECT_DIR="$CODEX_PROJECT" bash "$COS_REPO/scripts/cos-status.sh" --json >/tmp/cos-demo-codex-status.json
COGNITIVE_OS_PROJECT_DIR="$CLAUDE_PROJECT" bash "$COS_REPO/scripts/cos-status.sh" --json >/tmp/cos-demo-claude-status.json
pass "cos-status inspected both installs"

say "Comparing installed core fingerprints"
for rel in hooks/cos skills/cos templates/cos; do
  left="$CODEX_PROJECT/.cognitive-os/$rel"
  right="$CLAUDE_PROJECT/.cognitive-os/$rel"
  require_path "$left"
  require_path "$right"
  left_hash="$(fingerprint_dir "$left")"
  right_hash="$(fingerprint_dir "$right")"
  [ "$left_hash" = "$right_hash" ] || fail "core fingerprint mismatch for .cognitive-os/$rel"
  pass ".cognitive-os/$rel matches across harnesses"
done

say "Verifying driver-specific settings remain separate"
grep -q "CODEX_PROJECT_DIR" "$CODEX_PROJECT/.codex/hooks.json" || fail "Codex hooks.json missing CODEX_PROJECT_DIR"
grep -q "CLAUDE_PROJECT_DIR" "$CLAUDE_PROJECT/.claude/settings.json" || fail "Claude settings.json missing CLAUDE_PROJECT_DIR"
pass "Driver settings use driver-specific env expressions"

if [ "$RUN_PROVIDER_TESTS" = true ]; then
  say "Running provider/kernel portability tests"
  (
    cd "$COS_REPO"
    go test ./internal/provider/... ./internal/validator/... ./pkg/hook/... -count=1
  )
  pass "Provider/kernel tests passed"
else
  say "Skipping provider/kernel tests (--skip-provider-tests)"
fi

echo ""
echo "Portability proof complete."
echo "Codex project:  $CODEX_PROJECT"
echo "Claude project: $CLAUDE_PROJECT"
