#!/usr/bin/env bash
# tests/integration/test_dependency_license_classifier.sh
# Integration tests for hooks/dependency-license-classifier.sh (ADR-267 Hook #1)
#
# Usage: bash tests/integration/test_dependency_license_classifier.sh
# Exit:  0 if all tests pass, 1 if any fail

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$ROOT_DIR/hooks/dependency-license-classifier.sh"

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

# Create a hermetic temp repo. The hook computes ROOT_DIR as dirname(BASH_SOURCE)/..,
# so placing the patched copy at $FAKE_REPO/hooks/dependency-license-classifier.sh
# is sufficient for ROOT_DIR to resolve correctly.
# Sets FAKE_REPO, FAKE_HOOK after return.
setup_fake_repo() {
  local tmpbase="$1"
  local name="${2:-repo}"

  FAKE_REPO="$tmpbase/$name"
  mkdir -p "$FAKE_REPO/hooks" "$FAKE_REPO/.cognitive-os/logs"

  cd "$FAKE_REPO"
  git init -q
  git config user.email "test@test.com"
  git config user.name "Test"

  FAKE_HOOK="$FAKE_REPO/hooks/dependency-license-classifier.sh"
  cp "$HOOK" "$FAKE_HOOK"
  chmod +x "$FAKE_HOOK"

  cd "$ROOT_DIR"
}

# Stage a file in the fake repo with the given content.
# $1 = FAKE_REPO, $2 = relative path, $3 = content
stage_file() {
  local repo="$1"
  local rel_path="$2"
  local content="$3"
  mkdir -p "$repo/$(dirname "$rel_path")"
  printf '%s\n' "$content" > "$repo/$rel_path"
  git -C "$repo" add "$rel_path"
}

# ── Global tmp dir ─────────────────────────────────────────────────────────────
TMPDIR_TEST="$(mktemp -d /tmp/test-dependency-license-classifier-XXXXXX)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

PAYLOAD_COMMIT='{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}'
PAYLOAD_NOOP='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'

# ── Test 1: Non-commit command → exit 0 ───────────────────────────────────────
actual=$(bash "$HOOK" <<< "$PAYLOAD_NOOP"; echo $?)
assert_exit "TC1: non-commit command exits 0" 0 "$actual"

# ── Test 2: No dep manifests staged → exit 0 ─────────────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_no_dep_manifests"
# Stage a regular file that is not a dep manifest
stage_file "$FAKE_REPO" "lib/helper.py" "def help(): pass"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC2: no dep manifests staged exits 0" 0 "$actual"

# ── Test 3: COS_ALLOW_LICENSE_CLASSIFIER_BYPASS=1 → exit 0, log bypass ────────
setup_fake_repo "$TMPDIR_TEST" "repo_bypass"
stage_file "$FAKE_REPO" "requirements.txt" "langchain-postgres ; license = AGPL-3.0"

actual_output=$(
  cd "$FAKE_REPO"
  COS_ALLOW_LICENSE_CLASSIFIER_BYPASS=1 bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
exit_code=$(printf '%s' "$actual_output" | tail -1)
assert_exit "TC3: COS_ALLOW_LICENSE_CLASSIFIER_BYPASS=1 exits 0" 0 "$exit_code"

LOG="$FAKE_REPO/.cognitive-os/logs/dependency-license-classifier.jsonl"
if [ -f "$LOG" ] && grep -q '"action":"bypass"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC3 (log): action:bypass logged"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC3 (log): action:bypass not found in log"
  FAIL=$((FAIL + 1))
fi

# ── Test 4: requirements.txt with no BLOCKER strings → exit 0 ────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_clean_requirements"
stage_file "$FAKE_REPO" "requirements.txt" "requests==2.31.0
flask==3.0.0
pydantic>=2.0"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC4: requirements.txt without BLOCKER licenses exits 0" 0 "$actual"

# ── Test 5: requirements.txt with AGPL line → exit 1, error mentions AGPL ─────
setup_fake_repo "$TMPDIR_TEST" "repo_agpl_requirements"
stage_file "$FAKE_REPO" "requirements.txt" "requests==2.31.0
langchain-postgres ; license = AGPL-3.0"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC5: AGPL in requirements.txt exits 1" 1 "$exit_code"
assert_output_contains "TC5 (msg): error mentions AGPL" "AGPL" "$actual"

# ── Test 6: pyproject.toml with AGPL classifier on + line → exit 1 ────────────
setup_fake_repo "$TMPDIR_TEST" "repo_agpl_pyproject"
stage_file "$FAKE_REPO" "pyproject.toml" '[project]
name = "evil-lib"
classifiers = [
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
]'

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC6: AGPL classifier in pyproject.toml exits 1" 1 "$exit_code"
assert_output_contains "TC6 (msg): BLOCKED message present" "DEPENDENCY-LICENSE-CLASSIFIER: BLOCKED" "$actual"

# ── Test 7: package.json with SSPL-1.0 → exit 1 ───────────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_sspl_package"
stage_file "$FAKE_REPO" "package.json" '{
  "name": "sspl-lib",
  "version": "1.0.0",
  "license": "SSPL-1.0",
  "dependencies": {}
}'

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC7: SSPL-1.0 in package.json exits 1" 1 "$exit_code"
assert_output_contains "TC7 (msg): SSPL mentioned in error" "SSPL" "$actual"

# ── Test 8: Cargo.toml with BSL-1.1 → exit 1 ─────────────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_bsl_cargo"
stage_file "$FAKE_REPO" "Cargo.toml" '[package]
name = "bsl-crate"
version = "0.1.0"
license = "BSL-1.1"'

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC8: BSL-1.1 in Cargo.toml exits 1" 1 "$exit_code"
assert_output_contains "TC8 (msg): BSL mentioned in error" "BSL" "$actual"

# ── Test 9: Case-insensitive AGPL match → exit 1 ─────────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_agpl_lowercase"
stage_file "$FAKE_REPO" "requirements.txt" 'flask==3.0.0
# some-pkg ; license = "agpl-3.0"'

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC9: lowercase agpl case-insensitive match exits 1" 1 "$exit_code"

# ── Test 10: Only deletions in staged diff → exit 0 ──────────────────────────
# Removing a dep with a blocker license is fine — no new dep introduced.
setup_fake_repo "$TMPDIR_TEST" "repo_deletions_only"
# Track a requirements.txt with AGPL content first
stage_file "$FAKE_REPO" "requirements.txt" "langchain-postgres ; license = AGPL-3.0"
git -C "$FAKE_REPO" commit -q -m "initial"
# Now remove the AGPL line (deletion only)
printf 'requests==2.31.0\n' > "$FAKE_REPO/requirements.txt"
git -C "$FAKE_REPO" add "requirements.txt"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC10: only deletions in staged diff exits 0" 0 "$actual"

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL))
echo ""
echo "[test_dependency_license_classifier] $PASS passed / $TOTAL total"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
