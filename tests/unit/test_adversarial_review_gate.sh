#!/usr/bin/env bash
# Unit tests for hooks/adversarial-review-gate.sh and hooks/decision-depth-gate.sh
# Both hooks are fail-silent (exit 0 always). Tests assert WARNING/no-WARNING in stdout.

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK_ARG="$PROJECT_DIR/hooks/adversarial-review-gate.sh"
HOOK_DDG="$PROJECT_DIR/hooks/decision-depth-gate.sh"

PASS=0
FAIL=0

assert_contains() {
  local label="$1" haystack="$2" needle="$3"
  if echo "$haystack" | grep -q "$needle"; then
    echo "PASS: $label"
    PASS=$((PASS+1))
  else
    echo "FAIL: $label — expected to contain: $needle"
    echo "  actual: $haystack"
    FAIL=$((FAIL+1))
  fi
}

assert_not_contains() {
  local label="$1" haystack="$2" needle="$3"
  if echo "$haystack" | grep -q "$needle"; then
    echo "FAIL: $label — expected NOT to contain: $needle"
    echo "  actual: $haystack"
    FAIL=$((FAIL+1))
  else
    echo "PASS: $label"
    PASS=$((PASS+1))
  fi
}

# adversarial-review-gate tests
OUT=$(echo '{"tool_name":"Agent","tool_input":{"prompt":"review this code"},"tool_result":"Looks good, no issues found."}' | bash "$HOOK_ARG" 2>&1)
assert_contains "ARG: review + prohibited phrase + no findings -> WARNING" "$OUT" "WARNING \[adversarial-review-gate\]"
assert_contains "ARG: prohibited-phrase severity message" "$OUT" "prohibited phrase"

OUT=$(echo '{"tool_name":"Agent","tool_input":{"prompt":"review this code"},"tool_result":"Review complete. CRITICAL: race condition at line 42."}' | bash "$HOOK_ARG" 2>&1)
assert_not_contains "ARG: review + CRITICAL finding -> silent pass" "$OUT" "WARNING"

OUT=$(echo '{"tool_name":"Agent","tool_input":{"prompt":"run a Tenth Man detractor pass on this plan"},"tool_result":"Detractor mode: Tenth Man Rule. S2 CONCERN: consensus hides rollback risk."}' | bash "$HOOK_ARG" 2>&1)
assert_not_contains "ARG: detractor + S2 concern -> silent pass" "$OUT" "WARNING"

OUT=$(echo '{"tool_name":"Agent","tool_input":{"prompt":"run a Devil'\''s Advocate review"},"tool_result":"Looks good, no issues found."}' | bash "$HOOK_ARG" 2>&1)
assert_contains "ARG: devil advocate + prohibited phrase -> WARNING" "$OUT" "WARNING \[adversarial-review-gate\]"

OUT=$(echo '{"tool_name":"Agent","tool_input":{"prompt":"implement feature X"},"tool_result":"Implemented function foo."}' | bash "$HOOK_ARG" 2>&1)
assert_not_contains "ARG: non-review context -> silent pass" "$OUT" "WARNING"

OUT=$(echo '{"tool_name":"Agent","tool_input":{"prompt":"please audit the auth flow"},"tool_result":"Audit done. All clean."}' | bash "$HOOK_ARG" 2>&1)
assert_contains "ARG: audit context with no findings -> WARNING" "$OUT" "WARNING \[adversarial-review-gate\]"

# decision-depth-gate tests
OUT=$(echo '{"tool_name":"Agent","tool_input":{},"tool_result":"Found an inconsistency between A and B. I will document this difference."}' | bash "$HOOK_DDG" 2>&1)
assert_contains "DDG: doc-resolution + no investigation -> WARNING" "$OUT" "WARNING \[decision-depth-gate\]"

OUT=$(echo '{"tool_name":"Agent","tool_input":{},"tool_result":"Found an inconsistency. Verified that the divergence exists because module A handles legacy clients (root cause: ADR-077). I will document this difference."}' | bash "$HOOK_DDG" 2>&1)
assert_not_contains "DDG: doc-resolution + investigation -> silent pass" "$OUT" "WARNING"

OUT=$(echo '{"tool_name":"Agent","tool_input":{},"tool_result":"Implemented the feature."}' | bash "$HOOK_DDG" 2>&1)
assert_not_contains "DDG: no finding context -> silent pass" "$OUT" "WARNING"

OUT=$(echo '{"tool_name":"Agent","tool_input":{},"tool_result":"Found a duplication. By design — voy a documentarlo."}' | bash "$HOOK_DDG" 2>&1)
assert_contains "DDG: 'by design' + 'documentarlo' without investigation -> WARNING" "$OUT" "WARNING \[decision-depth-gate\]"

echo ""
echo "Result: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] || exit 1
exit 0
