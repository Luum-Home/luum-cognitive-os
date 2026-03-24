#!/usr/bin/env bash
# Layer 1: Rules Infrastructure Tests
# Verifies rule files exist and match RULES-COMPACT.md references.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
RULES_DIR="$AOS/rules"
RULES_COMPACT="$RULES_DIR/RULES-COMPACT.md"

PASS=0
FAIL=0
WARN=0

pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  FAIL: $1"; }
warn() { WARN=$((WARN + 1)); echo "  WARN: $1"; }

echo "=== RULES INFRASTRUCTURE TESTS ==="
echo ""

# ---- Test 1: RULES-COMPACT.md exists ----
if [ -f "$RULES_COMPACT" ]; then
  pass "RULES-COMPACT.md exists"
else
  fail "RULES-COMPACT.md not found"
  echo ""
  echo "=== RULES SUMMARY ==="
  echo "  PASS: $PASS  FAIL: $FAIL  WARN: $WARN"
  exit 1
fi

# ---- Test 2: Each rule file on disk is referenced in RULES-COMPACT.md ----
echo ""
echo "--- Rules on disk vs RULES-COMPACT.md ---"
for rule in "$RULES_DIR"/*.md; do
  [ ! -f "$rule" ] && continue
  name=$(basename "$rule" .md)

  # Skip RULES-COMPACT itself
  [[ "$name" == "RULES-COMPACT" ]] && continue

  if grep -qF "$name" "$RULES_COMPACT" 2>/dev/null; then
    pass "$name.md referenced in RULES-COMPACT.md"
  else
    warn "ORPHAN rule on disk: $name.md (not in RULES-COMPACT.md)"
  fi
done

# ---- Test 3: Each rule referenced in RULES-COMPACT.md exists on disk ----
echo ""
echo "--- RULES-COMPACT.md references vs disk ---"
# Extract rule names from backtick references like [`rule-name`]
REFERENCED_RULES=$(grep -oE '\[`[a-z0-9-]+`\]' "$RULES_COMPACT" | sed 's/\[`//;s/`\]//' | sort -u)
while IFS= read -r rule_name; do
  [ -z "$rule_name" ] && continue

  if [ -f "$RULES_DIR/$rule_name.md" ]; then
    pass "$rule_name referenced and exists on disk"
  else
    # Also check .claude/rules/
    if [ -f "$PROJECT_DIR/.claude/rules/$rule_name.md" ]; then
      pass "$rule_name referenced and exists in .claude/rules/"
    else
      fail "PHANTOM rule in RULES-COMPACT.md: $rule_name (file not found)"
    fi
  fi
done <<< "$REFERENCED_RULES"

# ---- Test 4: Rule files are valid markdown (non-empty) ----
echo ""
echo "--- Rule file validity ---"
for rule in "$RULES_DIR"/*.md; do
  [ ! -f "$rule" ] && continue
  name=$(basename "$rule")
  [[ "$name" == "RULES-COMPACT.md" ]] && continue

  size=$(wc -c < "$rule" | tr -d ' ')
  if [ "$size" -gt 10 ]; then
    pass "$name is non-empty ($size bytes)"
  else
    fail "$name appears empty or too small ($size bytes)"
  fi
done

# ---- Summary ----
echo ""
echo "=== RULES SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  WARN: $WARN"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
