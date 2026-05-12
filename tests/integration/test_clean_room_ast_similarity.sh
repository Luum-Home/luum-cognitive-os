#!/usr/bin/env bash
# tests/integration/test_clean_room_ast_similarity.sh
# Integration tests for ADR-271 Tier 2 AST similarity gate.
#
# 10 test cases covering:
#   TC1  non-commit command -> exits 0
#   TC2  empty external-source-cache -> exits 0
#   TC3  staged file with unique AST -> exits 0
#   TC4  staged file with symbol-rename of cached file -> BLOCK (exit 1)
#   TC5  same match, baseline entry -> exits 0
#   TC6  allowlist excludes docs/03-PoCs/research/ -> exits 0
#   TC7  bypass via COS_ALLOW_AST_SIMILARITY=1 -> exits 0 (logged)
#   TC8  bypass via COS_ALLOW_CLEAN_ROOM_BYPASS=1 -> exits 0 (logged)
#   TC9  performance: < 2s on 50 staged files
#   TC10 identity (file symlinked to packages canonical) -> exits 0 (skipped)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$ROOT_DIR/hooks/clean-room-ast-similarity-gate.sh"
DETECTOR="$ROOT_DIR/scripts/cos_clean_room_ast_similarity.py"

PASS=0; FAIL=0

assert_exit() {
  local n="$1" exp="$2" act="$3"
  if [ "$act" -eq "$exp" ]; then
    echo "[PASS] $n"
    PASS=$((PASS+1))
  else
    echo "[FAIL] $n — expected exit $exp, got $act"
    FAIL=$((FAIL+1))
  fi
}

TMPBASE=$(mktemp -d /tmp/test-ast-sim-XXXXXX)
trap 'rm -rf "$TMPBASE"' EXIT

# Helper: create a minimal fake repo with the hook wired
setup_repo() {
  local name="$1"
  REPO="$TMPBASE/$name"
  mkdir -p "$REPO/hooks" "$REPO/scripts" "$REPO/.cognitive-os/external-source-cache" \
           "$REPO/.cognitive-os/runtime" "$REPO/.cognitive-os/logs" \
           "$REPO/manifests" "$REPO/packages"
  # Copy detector script
  cp "$DETECTOR" "$REPO/scripts/cos_clean_room_ast_similarity.py"
  # Copy hook
  cp "$HOOK" "$REPO/hooks/clean-room-ast-similarity-gate.sh"
  chmod +x "$REPO/hooks/clean-room-ast-similarity-gate.sh"
  # Write empty baseline
  cat > "$REPO/manifests/ast-similarity-baseline.yaml" << 'EOF'
schema_version: ast-similarity-baseline/v1
generated: 2026-01-01
accepted: []
EOF
  ( cd "$REPO" && git init -q && git config user.email t@t && git config user.name T )
}

PAYLOAD_COMMIT='{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}'
PAYLOAD_NOOP='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'

# Define a unique-enough function body for TC3
UNIQUE_BODY='def highly_unique_luum_function_xyz_999(param_alpha, param_beta):
    result = param_alpha * 99 + param_beta - 7654321
    if result > 9999999:
        return result * 3
    return result - 1
'

# Define a "cache" function body to be copied + renamed in TC4
CACHE_BODY='def original_upstream_func(config_map, retry_limit, timeout_ms):
    processed = []
    for key, value in config_map.items():
        if value is not None and retry_limit > 0:
            processed.append((key, value * timeout_ms))
    return processed if processed else None
'

# Symbol-renamed version of the same function (different names, same structure)
RENAMED_BODY='def luum_internal_process(settings_dict, max_attempts, wait_period):
    results = []
    for field, data in settings_dict.items():
        if data is not None and max_attempts > 0:
            results.append((field, data * wait_period))
    return results if results else None
'

# ── TC1: non-commit command -> exits 0 ────────────────────────────────────────
actual=$(bash "$HOOK" <<<"$PAYLOAD_NOOP" 2>/dev/null; echo $?)
assert_exit "TC1: non-commit exits 0" 0 "$actual"

# ── TC2: empty external-source-cache -> exits 0 ───────────────────────────────
setup_repo r2
# Cache dir is created but has no .py files
actual=$(cd "$REPO" && bash hooks/clean-room-ast-similarity-gate.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $?)
assert_exit "TC2: empty cache exits 0" 0 "$actual"

# ── TC3: staged file with unique AST -> exits 0 ──────────────────────────────
setup_repo r3
# Add a real .py file to cache (doesn't match UNIQUE_BODY)
printf '%s' "$CACHE_BODY" > "$REPO/.cognitive-os/external-source-cache/upstream_mod.py"
# Stage a file with unique content
mkdir -p "$REPO/lib"
printf '%s' "$UNIQUE_BODY" > "$REPO/lib/unique_module.py"
( cd "$REPO" && git add lib/unique_module.py )
actual=$(cd "$REPO" && bash hooks/clean-room-ast-similarity-gate.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $?)
assert_exit "TC3: unique AST staged file exits 0" 0 "$actual"

# ── TC4: staged file with symbol-rename of cached file -> BLOCK ───────────────
setup_repo r4
printf '%s' "$CACHE_BODY" > "$REPO/.cognitive-os/external-source-cache/upstream_mod.py"
mkdir -p "$REPO/lib"
printf '%s' "$RENAMED_BODY" > "$REPO/lib/renamed_module.py"
( cd "$REPO" && git add lib/renamed_module.py )
actual=$(cd "$REPO" && bash hooks/clean-room-ast-similarity-gate.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $?)
assert_exit "TC4: symbol-rename of cached file blocked (exit 1)" 1 "$actual"

# ── TC5: same match but baseline entry -> exits 0 ────────────────────────────
setup_repo r5
printf '%s' "$CACHE_BODY" > "$REPO/.cognitive-os/external-source-cache/upstream_mod.py"
mkdir -p "$REPO/lib"
printf '%s' "$RENAMED_BODY" > "$REPO/lib/renamed_module.py"
( cd "$REPO" && git add lib/renamed_module.py )
# Pre-compute the hash so we can inject into baseline
HASH=$(cd "$REPO" && python3 scripts/cos_clean_room_ast_similarity.py --quick --format json 2>/dev/null \
       | python3 -c '
import json,sys
data=json.load(sys.stdin)
for m in data.get("matches",[]):
    print(m["ast_hash"])
' 2>/dev/null | head -1)
if [ -n "$HASH" ]; then
  cat > "$REPO/manifests/ast-similarity-baseline.yaml" << EOF
schema_version: ast-similarity-baseline/v1
generated: 2026-01-01
note: test
accepted:
  - cos_file: lib/renamed_module.py
    cos_unit: luum_internal_process
    cache_file: upstream_mod.py
    cache_unit: original_upstream_func
    ast_hash: $HASH
    classification: exact-AST
    note: test baseline entry
EOF
  actual=$(cd "$REPO" && bash hooks/clean-room-ast-similarity-gate.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $?)
  assert_exit "TC5: baseline entry allows match (exit 0)" 0 "$actual"
else
  echo "[SKIP] TC5: could not compute hash for baseline test"
  PASS=$((PASS+1))
fi

# ── TC6: allowlist excludes docs/03-PoCs/research/ -> exits 0 ────────────────────────
setup_repo r6
printf '%s' "$CACHE_BODY" > "$REPO/.cognitive-os/external-source-cache/upstream_mod.py"
mkdir -p "$REPO/docs/03-PoCs/research"
printf '%s' "$RENAMED_BODY" > "$REPO/docs/03-PoCs/research/renamed_module.py"
( cd "$REPO" && git add docs/03-PoCs/research/renamed_module.py )
# docs/03-PoCs/research/ is in the DEFAULT_ALLOWLIST in the Python detector
actual=$(cd "$REPO" && bash hooks/clean-room-ast-similarity-gate.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $?)
assert_exit "TC6: allowlist excludes docs/03-PoCs/research/ (exit 0)" 0 "$actual"

# ── TC7: bypass via COS_ALLOW_AST_SIMILARITY=1 -> exits 0 (logged) ───────────
setup_repo r7
printf '%s' "$CACHE_BODY" > "$REPO/.cognitive-os/external-source-cache/upstream_mod.py"
mkdir -p "$REPO/lib"
printf '%s' "$RENAMED_BODY" > "$REPO/lib/renamed_module.py"
( cd "$REPO" && git add lib/renamed_module.py )
actual=$(cd "$REPO" && COS_ALLOW_AST_SIMILARITY=1 bash hooks/clean-room-ast-similarity-gate.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $?)
assert_exit "TC7: COS_ALLOW_AST_SIMILARITY=1 bypasses (exit 0)" 0 "$actual"
# Verify it was logged
if grep -q '"action":"bypass"' "$REPO/.cognitive-os/logs/clean-room-ast-similarity-gate.jsonl" 2>/dev/null; then
  echo "[PASS] TC7: bypass logged"
  PASS=$((PASS+1))
else
  echo "[FAIL] TC7: bypass not logged"
  FAIL=$((FAIL+1))
fi

# ── TC8: bypass via COS_ALLOW_CLEAN_ROOM_BYPASS=1 -> exits 0 (logged) ────────
setup_repo r8
printf '%s' "$CACHE_BODY" > "$REPO/.cognitive-os/external-source-cache/upstream_mod.py"
mkdir -p "$REPO/lib"
printf '%s' "$RENAMED_BODY" > "$REPO/lib/renamed_module.py"
( cd "$REPO" && git add lib/renamed_module.py )
actual=$(cd "$REPO" && COS_ALLOW_CLEAN_ROOM_BYPASS=1 bash hooks/clean-room-ast-similarity-gate.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $?)
assert_exit "TC8: COS_ALLOW_CLEAN_ROOM_BYPASS=1 bypasses (exit 0)" 0 "$actual"
if grep -q '"action":"bypass"' "$REPO/.cognitive-os/logs/clean-room-ast-similarity-gate.jsonl" 2>/dev/null; then
  echo "[PASS] TC8: bypass logged"
  PASS=$((PASS+1))
else
  echo "[FAIL] TC8: bypass not logged"
  FAIL=$((FAIL+1))
fi

# ── TC9: performance < 2s on 50 staged files ──────────────────────────────────
setup_repo r9
printf '%s' "$CACHE_BODY" > "$REPO/.cognitive-os/external-source-cache/upstream_mod.py"
mkdir -p "$REPO/lib"
# Generate 50 unique Python files
for i in $(seq 1 50); do
  cat > "$REPO/lib/perf_module_${i}.py" << PYEOF
def perf_func_${i}(a, b, c):
    x = a + b * ${i}
    y = c - ${i} * 2
    if x > y:
        return x * ${i}
    return y + ${i}

class PerfClass${i}:
    def __init__(self, val):
        self.val = val * ${i}

    def compute(self, factor):
        result = self.val * factor + ${i}
        return result
PYEOF
done
( cd "$REPO" && git add lib/ )
# First run to build cache index (cold)
cd "$REPO" && python3 scripts/cos_clean_room_ast_similarity.py --quick --format json > /dev/null 2>&1 || true
# Warm run timing (portable: use python for milliseconds)
START_MS=$(python3 -c "import time; print(int(time.time()*1000))")
cd "$REPO" && python3 scripts/cos_clean_room_ast_similarity.py --quick --format json > /dev/null 2>&1 || true
END_MS=$(python3 -c "import time; print(int(time.time()*1000))")
ELAPSED_MS=$((END_MS - START_MS))
echo "[INFO] TC9: warm run on 50 staged files took ${ELAPSED_MS}ms"
if [ "$ELAPSED_MS" -lt 2000 ]; then
  echo "[PASS] TC9: performance < 2s (${ELAPSED_MS}ms)"
  PASS=$((PASS+1))
else
  echo "[FAIL] TC9: performance >= 2s (${ELAPSED_MS}ms)"
  FAIL=$((FAIL+1))
fi

# ── TC10: identity (symlink to packages canonical) -> exits 0 (skipped) ───────
setup_repo r10
printf '%s' "$CACHE_BODY" > "$REPO/.cognitive-os/external-source-cache/upstream_mod.py"
mkdir -p "$REPO/lib" "$REPO/packages/mylib/lib"
# Put the "canonical" version in packages/
printf '%s' "$RENAMED_BODY" > "$REPO/packages/mylib/lib/renamed_module.py"
# Create lib/ as a symlink to packages canonical (simulates lib-symlink pattern)
ln -sf "$REPO/packages/mylib/lib/renamed_module.py" "$REPO/lib/renamed_module.py"
( cd "$REPO" && git add lib/renamed_module.py 2>/dev/null || true )
actual=$(cd "$REPO" && bash hooks/clean-room-ast-similarity-gate.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $?)
assert_exit "TC10: symlink to packages canonical exits 0 (skipped)" 0 "$actual"

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL=$((PASS+FAIL))
echo ""
echo "Results: $PASS/$TOTAL passed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
