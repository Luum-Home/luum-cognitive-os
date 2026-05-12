#!/usr/bin/env bash
# tests/integration/test_adoption_freeze_gate.sh
# Integration tests for hooks/adoption-freeze-gate.sh (ADR-267 Hook #3)
#
# Usage: bash tests/integration/test_adoption_freeze_gate.sh
# Exit:  0 if all tests pass, 1 if any fail

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$ROOT_DIR/hooks/adoption-freeze-gate.sh"

PASS=0
FAIL=0

# ── Helpers ───────────────────────────────────────────────────────────────────

assert_exit() {
  local test_name="$1"
  local expected="$2"
  local actual="$3"
  if [ "$actual" -eq "$expected" ]; then
    echo "[PASS] $test_name"
    PASS=$((PASS + 1))
  else
    echo "[FAIL] $test_name — expected exit $expected, got $actual"
    FAIL=$((FAIL + 1))
  fi
}

assert_output_contains() {
  local test_name="$1"
  local needle="$2"
  local haystack="$3"
  if printf '%s' "$haystack" | grep -q "$needle"; then
    echo "[PASS] $test_name"
    PASS=$((PASS + 1))
  else
    echo "[FAIL] $test_name — expected '$needle' in output"
    FAIL=$((FAIL + 1))
  fi
}

# Create a hermetic temp repo with its own manifests/ and .cognitive-os/logs/
# Sets FAKE_REPO, FAKE_HOOK after return.
setup_fake_repo() {
  local tmpbase="$1"
  local name="${2:-repo}"

  FAKE_REPO="$tmpbase/$name"
  mkdir -p "$FAKE_REPO/hooks" "$FAKE_REPO/manifests" "$FAKE_REPO/.cognitive-os/logs"

  cd "$FAKE_REPO"
  git init -q
  git config user.email "test@test.com"
  git config user.name "Test"

  # Patch ROOT_DIR derivation in the hook so it points at FAKE_REPO.
  # The hook computes ROOT_DIR as dirname(BASH_SOURCE)/.., so placing the
  # patched copy at $FAKE_REPO/hooks/adoption-freeze-gate.sh is sufficient.
  FAKE_HOOK="$FAKE_REPO/hooks/adoption-freeze-gate.sh"
  cp "$HOOK" "$FAKE_HOOK"
  chmod +x "$FAKE_HOOK"

  cd "$ROOT_DIR"
}

write_freeze_manifest() {
  local repo="$1"
  local frozen="${2:-false}"
  cat > "$repo/manifests/external-tool-adoption-freeze.yaml" <<YAML
schema_version: external-tool-adoption-freeze/v1
status: active
frozen: $frozen
gated_path_globs:
  - 'docs/03-PoCs/research/*-annex-*-*.md'
  - 'docs/03-PoCs/research/*-comparison-*.md'
  - 'docs/06-Daily/reports/external-tools-radar-*.md'
  - 'manifests/external-tools-adoption.yaml'
YAML
}

write_malformed_manifest() {
  local repo="$1"
  # Deliberately invalid YAML (unmatched bracket)
  printf 'frozen: [unclosed\n' > "$repo/manifests/external-tool-adoption-freeze.yaml"
}

# ── Global tmp dir ─────────────────────────────────────────────────────────────
TMPDIR_TEST="$(mktemp -d /tmp/test-adoption-freeze-gate-XXXXXX)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

PAYLOAD_COMMIT='{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}'
PAYLOAD_NOOP='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'

# ── Test 1: Non-commit command → exit 0 ───────────────────────────────────────
actual=$(bash "$HOOK" <<< "$PAYLOAD_NOOP"; echo $?)
assert_exit "TC1: non-commit command exits 0" 0 "$actual"

# ── Test 2: Manifest absent → exit 0, log action:skip ─────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_no_manifest"
# No manifest written — it's absent by default
actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC2: manifest absent exits 0" 0 "$actual"

LOG="$FAKE_REPO/.cognitive-os/logs/adoption-freeze-gate.jsonl"
if [ -f "$LOG" ] && grep -q '"action":"skip"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC2 (log): action:skip logged when manifest absent"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC2 (log): action:skip not found in log"
  FAIL=$((FAIL + 1))
fi

# ── Test 3: frozen: false → exit 0, log action:pass ───────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_not_frozen"
write_freeze_manifest "$FAKE_REPO" "false"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC3: frozen=false exits 0" 0 "$actual"

LOG="$FAKE_REPO/.cognitive-os/logs/adoption-freeze-gate.jsonl"
if [ -f "$LOG" ] && grep -q '"action":"pass"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC3 (log): action:pass logged when frozen=false"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC3 (log): action:pass not found in log"
  FAIL=$((FAIL + 1))
fi

# ── Test 4: frozen: true + no staged files → exit 0, log reason:no staged ─────
setup_fake_repo "$TMPDIR_TEST" "repo_frozen_nostaged"
write_freeze_manifest "$FAKE_REPO" "true"
# Nothing staged — empty index

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC4: frozen=true, no staged files exits 0" 0 "$actual"

LOG="$FAKE_REPO/.cognitive-os/logs/adoption-freeze-gate.jsonl"
if [ -f "$LOG" ] && grep -q '"reason":"no staged"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC4 (log): reason:no staged logged"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC4 (log): reason:no staged not found in log"
  FAIL=$((FAIL + 1))
fi

# ── Test 5: frozen: true + staged file in gated_path_globs → exit 1 ──────────
setup_fake_repo "$TMPDIR_TEST" "repo_frozen_blocked"
write_freeze_manifest "$FAKE_REPO" "true"

# Stage a file matching 'docs/03-PoCs/research/*-annex-*-*.md'
mkdir -p "$FAKE_REPO/docs/03-PoCs/research"
echo "annex content" > "$FAKE_REPO/docs/03-PoCs/research/test-annex-z-memory.md"
cd "$FAKE_REPO"
git add "docs/03-PoCs/research/test-annex-z-memory.md"
cd "$ROOT_DIR"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC5: frozen=true + gated path staged exits 1" 1 "$exit_code"
assert_output_contains "TC5 (msg): BLOCKED message present" "ADOPTION-FREEZE-GATE: BLOCKED" "$actual"

# ── Test 6: frozen: true + staged file NOT in gated_path_globs → exit 0 ──────
setup_fake_repo "$TMPDIR_TEST" "repo_frozen_ungated"
write_freeze_manifest "$FAKE_REPO" "true"

mkdir -p "$FAKE_REPO/lib"
echo "x = 1" > "$FAKE_REPO/lib/foo.py"
cd "$FAKE_REPO"
git add "lib/foo.py"
cd "$ROOT_DIR"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC6: frozen=true + non-gated path exits 0" 0 "$actual"

LOG="$FAKE_REPO/.cognitive-os/logs/adoption-freeze-gate.jsonl"
if [ -f "$LOG" ] && grep -q '"reason":"no gated paths touched"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC6 (log): reason:no gated paths touched logged"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC6 (log): reason:no gated paths touched not found in log"
  FAIL=$((FAIL + 1))
fi

# ── Test 7: COS_ALLOW_FREEZE_TOGGLE=1 + only freeze yaml staged → exit 0 ─────
setup_fake_repo "$TMPDIR_TEST" "repo_toggle_bypass"
write_freeze_manifest "$FAKE_REPO" "true"

# Stage ONLY the freeze manifest itself
cd "$FAKE_REPO"
git add "manifests/external-tool-adoption-freeze.yaml"
cd "$ROOT_DIR"

actual=$(
  cd "$FAKE_REPO"
  COS_ALLOW_FREEZE_TOGGLE=1 bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC7: COS_ALLOW_FREEZE_TOGGLE=1 + manifest-only staged exits 0" 0 "$actual"

LOG="$FAKE_REPO/.cognitive-os/logs/adoption-freeze-gate.jsonl"
if [ -f "$LOG" ] && grep -q '"reason":"COS_ALLOW_FREEZE_TOGGLE+manifest-only"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC7 (log): bypass reason COS_ALLOW_FREEZE_TOGGLE+manifest-only logged"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC7 (log): expected bypass reason not found in log"
  FAIL=$((FAIL + 1))
fi

# ── Test 8: COS_ALLOW_ADOPTION_FREEZE_BYPASS=1 → exit 0 ─────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_generic_bypass"
write_freeze_manifest "$FAKE_REPO" "true"

mkdir -p "$FAKE_REPO/docs/03-PoCs/research"
echo "annex content" > "$FAKE_REPO/docs/03-PoCs/research/holaos-annex-q-test.md"
cd "$FAKE_REPO"
git add "docs/03-PoCs/research/holaos-annex-q-test.md"
cd "$ROOT_DIR"

actual=$(
  cd "$FAKE_REPO"
  COS_ALLOW_ADOPTION_FREEZE_BYPASS=1 bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC8: COS_ALLOW_ADOPTION_FREEZE_BYPASS=1 exits 0" 0 "$actual"

LOG="$FAKE_REPO/.cognitive-os/logs/adoption-freeze-gate.jsonl"
if [ -f "$LOG" ] && grep -q '"action":"bypass"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC8 (log): action:bypass logged"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC8 (log): action:bypass not found in log"
  FAIL=$((FAIL + 1))
fi

# ── Test 9: Malformed manifest → exit 0, log action:skip reason:parse error ───
setup_fake_repo "$TMPDIR_TEST" "repo_malformed"
write_malformed_manifest "$FAKE_REPO"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC9: malformed manifest exits 0" 0 "$actual"

LOG="$FAKE_REPO/.cognitive-os/logs/adoption-freeze-gate.jsonl"
if [ -f "$LOG" ] && grep -q '"reason":"parse error"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC9 (log): reason:parse error logged for malformed manifest"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC9 (log): reason:parse error not found in log"
  FAIL=$((FAIL + 1))
fi

# ── Test 10: Staging-no-diff edge case → STAGED="" → exit 0 ──────────────────
# When a previously-tracked file is re-added to the index without any actual
# content change, `git diff --cached --name-only` returns empty output.
# The hook checks for an empty STAGED var and exits 0 immediately.
# This is EXPECTED behaviour (no diff = nothing to gate against).
# Note: we simulate this by tracking a file, committing it, then re-adding it
# without changes — git reports nothing in the cached diff.
setup_fake_repo "$TMPDIR_TEST" "repo_no_diff"
write_freeze_manifest "$FAKE_REPO" "true"

mkdir -p "$FAKE_REPO/docs/03-PoCs/research"
echo "content" > "$FAKE_REPO/docs/03-PoCs/research/holaos-annex-z-memory.md"
cd "$FAKE_REPO"
# Commit the file so it's tracked
git add "docs/03-PoCs/research/holaos-annex-z-memory.md"
git commit -q -m "initial"
# Re-stage without changes — diff --cached will be empty
git add "docs/03-PoCs/research/holaos-annex-z-memory.md"
cd "$ROOT_DIR"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC10: staging-no-diff (STAGED=empty) exits 0 (expected behaviour)" 0 "$actual"

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL))
echo ""
echo "[test_adoption_freeze_gate] $PASS passed / $TOTAL total"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
