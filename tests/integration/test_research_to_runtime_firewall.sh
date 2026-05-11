#!/usr/bin/env bash
# tests/integration/test_research_to_runtime_firewall.sh
# Integration tests for hooks/research-to-runtime-firewall.sh (ADR-267 Hook #6)
#
# Usage: bash tests/integration/test_research_to_runtime_firewall.sh
# Exit:  0 if all tests pass, 1 if any fail

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$ROOT_DIR/hooks/research-to-runtime-firewall.sh"

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
# so placing the copy at $FAKE_REPO/hooks/research-to-runtime-firewall.sh is
# sufficient for ROOT_DIR to resolve to FAKE_REPO.
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

  FAKE_HOOK="$FAKE_REPO/hooks/research-to-runtime-firewall.sh"
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
TMPDIR_TEST="$(mktemp -d /tmp/test-research-to-runtime-firewall-XXXXXX)"
trap 'rm -rf "$TMPDIR_TEST"' EXIT

PAYLOAD_COMMIT='{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}'
PAYLOAD_NOOP='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'

CACHE_REF=".cognitive-os/external-source-cache"

# ── Test 1: Non-commit command → exit 0 ───────────────────────────────────────
actual=$(bash "$HOOK" <<< "$PAYLOAD_NOOP"; echo $?)
assert_exit "TC1: non-commit command exits 0" 0 "$actual"

# ── Test 2: COS_ALLOW_RESEARCH_RUNTIME_LEAK=1 → exit 0, log bypass ───────────
setup_fake_repo "$TMPDIR_TEST" "repo_bypass"
stage_file "$FAKE_REPO" "lib/foo.py" "# ref: $CACHE_REF/iFixAi/solver.py"

actual_output=$(
  cd "$FAKE_REPO"
  COS_ALLOW_RESEARCH_RUNTIME_LEAK=1 bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
exit_code=$(printf '%s' "$actual_output" | tail -1)
assert_exit "TC2: COS_ALLOW_RESEARCH_RUNTIME_LEAK=1 exits 0" 0 "$exit_code"

LOG="$FAKE_REPO/.cognitive-os/logs/research-to-runtime-firewall.jsonl"
if [ -f "$LOG" ] && grep -q '"action":"bypass"' "$LOG" 2>/dev/null; then
  echo "[PASS] TC2 (log): action:bypass logged"
  PASS=$((PASS + 1))
else
  echo "[FAIL] TC2 (log): action:bypass not found in log"
  FAIL=$((FAIL + 1))
fi

# ── Test 3: No staged files → exit 0 ─────────────────────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_no_staged"
# Empty index — nothing staged

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC3: no staged files exits 0" 0 "$actual"

# ── Test 4: Research path containing cache ref → exit 0 (scan-exempt) ─────────
# docs/research/ is not in RUNTIME_DIRS_RE (^(lib|packages|scripts)/),
# so the hook should ignore it even if it references the cache path.
setup_fake_repo "$TMPDIR_TEST" "repo_research_exempt"
stage_file "$FAKE_REPO" "docs/research/foo.md" "See $CACHE_REF/helix-db/ for study notes."

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC4: docs/research/ file with cache ref is scan-exempt, exits 0" 0 "$actual"

# ── Test 5: lib/foo.py referencing cache path → exit 1 ────────────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_lib_blocked"
stage_file "$FAKE_REPO" "lib/foo.py" "import importlib
# Load module from $CACHE_REF/iFixAi/solver.py
spec = importlib.util.spec_from_file_location('solver', '$CACHE_REF/iFixAi/solver.py')"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC5: lib/foo.py with cache ref exits 1" 1 "$exit_code"
assert_output_contains "TC5 (msg): BLOCKED message present" "RESEARCH-TO-RUNTIME-FIREWALL: BLOCKED" "$actual"

# ── Test 6: packages/x/lib/y.py containing cache path → exit 1 ───────────────
setup_fake_repo "$TMPDIR_TEST" "repo_packages_blocked"
stage_file "$FAKE_REPO" "packages/x/lib/y.py" "CACHE = '$CACHE_REF/MegaMemory/store.py'"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC6: packages/x/lib/y.py with cache ref exits 1" 1 "$exit_code"
assert_output_contains "TC6 (msg): BLOCKED message present" "RESEARCH-TO-RUNTIME-FIREWALL: BLOCKED" "$actual"

# ── Test 7: scripts/foo.sh referencing cache path → exit 1 ───────────────────
setup_fake_repo "$TMPDIR_TEST" "repo_scripts_blocked"
stage_file "$FAKE_REPO" "scripts/foo.sh" "#!/usr/bin/env bash
source \"./$CACHE_REF/some-tool/helpers.sh\""

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>&1
  echo $?
)
exit_code=$(printf '%s' "$actual" | tail -1)
assert_exit "TC7: scripts/foo.sh with cache ref exits 1" 1 "$exit_code"
assert_output_contains "TC7 (msg): BLOCKED message present" "RESEARCH-TO-RUNTIME-FIREWALL: BLOCKED" "$actual"

# ── Test 8: lib/foo.py referencing different cache path → exit 0 ──────────────
# .cognitive-os/runtime/ is NOT the guarded path (.cognitive-os/external-source-cache/)
setup_fake_repo "$TMPDIR_TEST" "repo_different_cache"
stage_file "$FAKE_REPO" "lib/foo.py" "# load from .cognitive-os/runtime/artifacts/model.pkl"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC8: lib file referencing .cognitive-os/runtime/ (not external-source-cache) exits 0" 0 "$actual"

# ── Test 9: Staged binary/non-scannable extension → exit 0 ───────────────────
# The hook's SCAN_EXT_RE allows only .py|.ts|.tsx|.js|.jsx|.sh|.rs|.go|.toml|.yaml|.yml|.json
# A .png file is excluded even if it happens to have the cache string in the filename.
setup_fake_repo "$TMPDIR_TEST" "repo_binary_exempt"
# Create a minimal PNG (1×1 pixel) with the cache ref embedded — extension filter wins
CACHE_FILE="$FAKE_REPO/lib/foo.png"
mkdir -p "$FAKE_REPO/lib"
printf '\x89PNG\r\n\x1a\n' > "$CACHE_FILE"
# Append the forbidden string in the binary payload
printf '%s' "$CACHE_REF/tool/x.py" >> "$CACHE_FILE"
git -C "$FAKE_REPO" add "lib/foo.png"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC9: non-scannable extension (.png) is skipped, exits 0" 0 "$actual"

# ── Test 10: Very large staged file → exit 0 (size-skip defensive behaviour) ──
# The hook skips files larger than 524288 bytes (512 KiB) as a defensive measure.
# We create a 530 KiB file that contains the cache reference, staged in lib/.
setup_fake_repo "$TMPDIR_TEST" "repo_large_file"
mkdir -p "$FAKE_REPO/lib"
LARGE_FILE="$FAKE_REPO/lib/big.py"
# Write 530 KiB of padding, then append the forbidden string
python3 -c "
import sys
sys.stdout.write('# padding\n' * 60000)  # ~600 KiB > 524288
sys.stdout.write('# $CACHE_REF/some-tool/x.py\n')
" > "$LARGE_FILE"
git -C "$FAKE_REPO" add "lib/big.py"

actual=$(
  cd "$FAKE_REPO"
  bash "$FAKE_HOOK" <<< "$PAYLOAD_COMMIT" 2>/dev/null
  echo $?
)
assert_exit "TC10: file >524288 bytes with cache ref is size-skipped, exits 0" 0 "$actual"

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL=$((PASS + FAIL))
echo ""
echo "[test_research_to_runtime_firewall] $PASS passed / $TOTAL total"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
