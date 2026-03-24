#!/usr/bin/env bash
# Layer 2: Phase System Behavior Tests
# Verifies inject-phase-context.sh outputs correct rules per phase.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
HOOKS_DIR="$AOS/hooks"
CONFIG="$AOS/cognitive-os.yaml"
HOOK="$HOOKS_DIR/inject-phase-context.sh"

PASS=0
FAIL=0
SKIP=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
skip() { SKIP=$((SKIP + 1)); echo "  SKIP: $1"; }

echo "=== PHASE SYSTEM BEHAVIOR TESTS ==="
echo ""

if [ ! -x "$HOOK" ]; then
  skip "inject-phase-context.sh not executable — skipping all"
  echo ""
  echo "=== PHASE SYSTEM SUMMARY ==="
  echo "  PASS: $PASS  FAIL: $FAIL  SKIP: $SKIP"
  exit 0
fi

if [ ! -f "$CONFIG" ]; then
  skip "cognitive-os.yaml not found — skipping all"
  echo ""
  echo "=== PHASE SYSTEM SUMMARY ==="
  echo "  PASS: $PASS  FAIL: $FAIL  SKIP: $SKIP"
  exit 0
fi

# Save original config
ORIGINAL_PHASE=$(grep -E '^\s+phase:' "$CONFIG" | head -1)
BACKUP_CONFIG=$(cat "$CONFIG")

restore_config() {
  echo "$BACKUP_CONFIG" > "$CONFIG"
}
trap restore_config EXIT

MOCK_INPUT='{"tool_name":"Agent","tool_input":{"prompt":"test"}}'

# ---- Test 1: Reconstruction phase includes rewrite rules ----
echo "--- Phase: reconstruction ---"
sed -i.bak "s/phase:.*/phase: reconstruction/" "$CONFIG"
OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)

if echo "$OUTPUT" | grep -qi "rewrite"; then
  pass "reconstruction phase includes rewrite rules"
else
  fail "reconstruction phase missing rewrite rules"
fi

if echo "$OUTPUT" | grep -qi "backwards\|backward"; then
  pass "reconstruction phase mentions backwards compatibility"
else
  warn "reconstruction phase may not mention backwards compatibility"
fi

# ---- Test 2: Production phase includes feature flags ----
echo ""
echo "--- Phase: production ---"
sed -i.bak "s/phase:.*/phase: production/" "$CONFIG"
OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)

if echo "$OUTPUT" | grep -qi "feature flag\|break existing\|Do NOT break"; then
  pass "production phase includes stability rules"
else
  fail "production phase missing stability/feature-flag rules"
fi

# ---- Test 3: Maintenance phase restricts to bug fixes ----
echo ""
echo "--- Phase: maintenance ---"
sed -i.bak "s/phase:.*/phase: maintenance/" "$CONFIG"
OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)

if echo "$OUTPUT" | grep -qi "bug fix\|security patch\|minimal"; then
  pass "maintenance phase restricts to bug fixes/security"
else
  fail "maintenance phase missing bug-fix-only rules"
fi

# ---- Test 4: Stabilization phase ----
echo ""
echo "--- Phase: stabilization ---"
sed -i.bak "s/phase:.*/phase: stabilization/" "$CONFIG"
OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)

if echo "$OUTPUT" | grep -qi "stabilization\|fix\|standard"; then
  pass "stabilization phase outputs relevant rules"
else
  fail "stabilization phase missing expected rules"
fi

# ---- Test 5: All phases include constitutional gates ----
echo ""
echo "--- Constitutional gates presence ---"
for phase in reconstruction stabilization production maintenance; do
  sed -i.bak "s/phase:.*/phase: $phase/" "$CONFIG"
  OUTPUT=$(echo "$MOCK_INPUT" | CLAUDE_PROJECT_DIR="$PROJECT_DIR" bash "$HOOK" 2>&1)
  if echo "$OUTPUT" | grep -qi "CONSTITUTIONAL GATES"; then
    pass "$phase phase includes constitutional gates"
  else
    fail "$phase phase missing constitutional gates"
  fi
done

# Restore
restore_config
rm -f "${CONFIG}.bak"

# ---- Summary ----
echo ""
echo "=== PHASE SYSTEM SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  SKIP: $SKIP"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
