#!/usr/bin/env bash
# tests/integration/test_external_cache_content_leak.sh
# Integration tests for hooks/external-cache-content-leak.sh (ADR-267 Hook #2)
# and scripts/cos_verbatim_copy_detector.py
#
# Usage: bash tests/integration/test_external_cache_content_leak.sh
# Exit:  0 if all tests pass, 1 if any fail

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$ROOT_DIR/hooks/external-cache-content-leak.sh"
DETECTOR="$ROOT_DIR/scripts/cos_verbatim_copy_detector.py"

PASS=0
FAIL=0

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

setup_fake_repo() {
  local tmpbase="$1"
  local name="${2:-repo}"

  FAKE_REPO="$tmpbase/$name"
  mkdir -p "$FAKE_REPO/hooks" \
           "$FAKE_REPO/scripts" \
           "$FAKE_REPO/manifests" \
           "$FAKE_REPO/.cognitive-os/logs" \
           "$FAKE_REPO/.cognitive-os/external-source-cache"

  cd "$FAKE_REPO"
  git init -q
  git config user.email "test@test.com"
  git config user.name "Test"

  FAKE_HOOK="$FAKE_REPO/hooks/external-cache-content-leak.sh"
  FAKE_DETECTOR="$FAKE_REPO/scripts/cos_verbatim_copy_detector.py"
  FAKE_CACHE="$FAKE_REPO/.cognitive-os/external-source-cache"

  cp "$HOOK" "$FAKE_HOOK"
  chmod +x "$FAKE_HOOK"
  cp "$DETECTOR" "$FAKE_DETECTOR"

  cat > "$FAKE_REPO/manifests/verbatim-detection-baseline.yaml" << 'YAML'
schema_version: verbatim-detection-baseline/v1
generated: 2026-05-11
note: |
  Test baseline.
accepted:
YAML

  cd "$ROOT_DIR"
}

stage_file() {
  local repo="$1"
  local rel_path="$2"
  local content="$3"
  mkdir -p "$repo/$(dirname "$rel_path")"
  printf '%s\n' "$content" > "$repo/$rel_path"
  git -C "$repo" add "$rel_path"
}

make_verbatim_block() {
  cat << 'BLOCK'
def alpha_one(x):
    return x + 1

def alpha_two(x):
    return x + 2

def alpha_three(x):
    return x + 3

def alpha_four(x):
    return x + 4

def alpha_five(x):
    return x + 5

def alpha_six(x):
    return x + 6
BLOCK
}

TMPDIR_TEST="$(mktemp -d /tmp/test-external-cache-content-leak-XXXXXX)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

PAYLOAD_COMMIT='{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}'
PAYLOAD_NOOP='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'

# ── TC1: Non-commit command → exit 0 ─────────────────────────────────────────
actual=$(bash "$HOOK" <<< "$PAYLOAD_NOOP"; echo $?)
assert_exit "TC1: non-commit command exits 0" 0 "$actual"

# ── TC2: COS_ALLOW_VERBATIM_LEAK=1 bypass → exit 0, log bypass ───────────────
setup_fake_repo "$TMPDIR_TEST" "repo_bypass"
BLOCK_CONTENT="$(make_verbatim_block)"
printf '%s\n' "$BLOCK_CONTENT" > "$FAKE_CACHE/upstream.py"
stage_file "$FAKE_REPO" "lib/foo.py" "$BLOCK_CONTENT"

actual_output=$(
  cd "$FAKE_REPO"
  COS_ALLOW_VERBATIM_LEAK=1 bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
exit_code=$(printf '%s' "$actual_output" | tail -1)
assert_exit "TC2: COS_ALLOW_VERBATIM_LEAK=1 exits 0" 0 "$exit_code"

LOG="$FAKE_REPO/.cognitive-os/logs/external-cache-content-leak.jsonl"
if [ -f "$LOG" ] && grep -q '"action":"bypass"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC2 (log): action:bypass logged"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC2 (log): action:bypass not found in log"
  FAIL=$((FAIL + 1))
fi

# ── TC3: Empty cache → exit 0 ─────────────────────────────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_empty_cache"
# Leave cache empty — no files placed
BLOCK_CONTENT="$(make_verbatim_block)"
stage_file "$FAKE_REPO" "lib/foo.py" "$BLOCK_CONTENT"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC3: empty cache exits 0" 0 "$actual"

# ── TC4: Staged file with NO matching content → exit 0 ────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_no_match"
printf 'def completely_different_zeta():\n    pass\n' > "$FAKE_CACHE/cache_file.py"
stage_file "$FAKE_REPO" "lib/bar.py" "def unrelated_function_xyz_abc():\n    return 99\n"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC4: staged file with no matching content exits 0" 0 "$actual"

# ── TC5: Verbatim block matching cache + no baseline entry → BLOCK ─────────────
setup_fake_repo "$TMPDIR_TEST" "repo_block"
BLOCK_CONTENT="$(make_verbatim_block)"
printf '%s\n' "$BLOCK_CONTENT" > "$FAKE_CACHE/upstream_module.py"
stage_file "$FAKE_REPO" "lib/stolen.py" "$BLOCK_CONTENT"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC5: verbatim block with no baseline exits 1" 1 "$exit_code"
assert_output_contains "TC5 (msg): BLOCKED message present" "EXTERNAL-CACHE-CONTENT-LEAK: BLOCKED" "$actual"

# ── TC6: Same match but baseline entry present → exit 0 ──────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_baseline"
BLOCK_CONTENT="$(make_verbatim_block)"
printf '%s\n' "$BLOCK_CONTENT" > "$FAKE_CACHE/upstream_module.py"
stage_file "$FAKE_REPO" "lib/approved.py" "$BLOCK_CONTENT"

# Compute fingerprint, add to baseline
FP="$(
  cd "$FAKE_REPO"
  python3 "$FAKE_DETECTOR" --quick --format json 2>/dev/null \
  | python3 -c 'import json,sys; hits=json.load(sys.stdin).get("hits",[]); print(hits[0]["fingerprint"] if hits else "")'
)"

if [ -n "$FP" ]; then
  cat >> "$FAKE_REPO/manifests/verbatim-detection-baseline.yaml" << ENTRY
  - cos_file: lib/approved.py
    cache_file: upstream_module.py
    fingerprint: $FP
    note: TC6 accepted
ENTRY
  actual=$(
    cd "$FAKE_REPO"
    bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
    echo $?
  )
  exit_code=$(printf '%s' "$actual" | tail -1)
  assert_exit "TC6: match with baseline entry exits 0" 0 "$exit_code"
else
  echo "[SKIP] TC6: could not extract fingerprint — skipping"
fi

# ── TC7: Allowlist excludes file → exit 0 ─────────────────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_allowlist"
BLOCK_CONTENT="$(make_verbatim_block)"
printf '%s\n' "$BLOCK_CONTENT" > "$FAKE_CACHE/upstream_module.py"
stage_file "$FAKE_REPO" "vendor/allowed_copy.py" "$BLOCK_CONTENT"
printf 'vendor/\n' > "$FAKE_REPO/verbatim-allowlist.txt"

actual=$(
  cd "$FAKE_REPO"
  python3 "$FAKE_DETECTOR" --quick --allowlist "$FAKE_REPO/verbatim-allowlist.txt" --format json 2>/dev/null
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC7: allowlisted prefix exits 0 from detector" 0 "$exit_code"

# ── TC8: --quick mode only scans staged files ─────────────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_quick"
BLOCK_CONTENT="$(make_verbatim_block)"
printf '%s\n' "$BLOCK_CONTENT" > "$FAKE_CACHE/upstream.py"

# Write matching file but do NOT stage it
mkdir -p "$FAKE_REPO/lib" && printf '%s\n' "$BLOCK_CONTENT" > "$FAKE_REPO/lib/unstaged_match.py"
# Stage only a clean file
stage_file "$FAKE_REPO" "lib/clean_file.py" "# clean file\nx = 42\n"

actual=$(
  cd "$FAKE_REPO"
  python3 "$FAKE_DETECTOR" --quick --format json 2>/dev/null
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC8: --quick ignores unstaged matching file, exits 0" 0 "$exit_code"

# ── TC9: Legacy bypass env-var also works ─────────────────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_legacy_bypass"
BLOCK_CONTENT="$(make_verbatim_block)"
printf '%s\n' "$BLOCK_CONTENT" > "$FAKE_CACHE/upstream.py"
stage_file "$FAKE_REPO" "lib/foo.py" "$BLOCK_CONTENT"

actual=$(
  cd "$FAKE_REPO"
  COS_ALLOW_EXTERNAL_CACHE_LEAK=1 bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC9: legacy COS_ALLOW_EXTERNAL_CACHE_LEAK=1 exits 0" 0 "$exit_code"

# ── TC10: Missing cache dir → hook exits 0 gracefully ─────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_no_cache"
rm -rf "$FAKE_REPO/.cognitive-os/external-source-cache"
BLOCK_CONTENT="$(make_verbatim_block)"
stage_file "$FAKE_REPO" "lib/foo.py" "$BLOCK_CONTENT"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC10: missing cache dir exits 0 gracefully" 0 "$exit_code"

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL))
echo ""
echo "[test_external_cache_content_leak] $PASS passed / $TOTAL total"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
