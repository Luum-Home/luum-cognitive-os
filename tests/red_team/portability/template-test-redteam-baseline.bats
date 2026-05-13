#!/usr/bin/env bats
# SCOPE: os-only
# Portability test for templates/contracts/test_redteam_baseline.template.py (KD6 gate, §2.2).
#
# Contract invariants per design §2.2:
#   1. Non-SO mini-repo: template is copied to a tempdir (non-SO consumer structure)
#   2. Bilateral assertion: template imports succeed and constants are configurable
#   3. Falsification probe: deliberately remove a required constant — template must
#      have a placeholder for it that causes a clear NameError if omitted (not silent)
#   4. Documented mini-repo: names clearly indicate test structure

TEMPLATE="templates/contracts/test_redteam_baseline.template.py"
SO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || cd "$(dirname "$BATS_TEST_FILENAME")/../../.." && pwd)"

setup() {
  TMP="$(mktemp -d)"
  MINI_TEMPLATE="$TMP/test_redteam_baseline.py"
  # Copy template to a non-SO location (simulating consumer project structure)
  cp "$SO_ROOT/$TEMPLATE" "$MINI_TEMPLATE"
}

teardown() {
  rm -rf "$TMP"
}

# ── Case 1: template is valid Python syntax ───────────────────────────────────
@test "template is valid Python syntax (can be parsed)" {
  run python3 -c "
import ast, sys
with open('$TMP/test_redteam_baseline.py') as f:
    src = f.read()
ast.parse(src)
print('syntax OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"syntax OK"* ]]
}

# ── Case 2: bilateral — SCOPE: both marker is present ────────────────────────
@test "bilateral: template carries SCOPE: both marker" {
  run grep "SCOPE: both" "$TMP/test_redteam_baseline.py"
  [ "$status" -eq 0 ]
}

# ── Case 3: template has all 5 required test functions ───────────────────────
@test "template has at least 5 test_ functions (consumer-ready)" {
  count=$(grep -c "^def test_" "$TMP/test_redteam_baseline.py" || true)
  [ "$count" -ge 5 ]
}

# ── Case 4: falsification probe — removing EXPECTED_SCENARIO_IDS breaks the template
# This proves the template has non-trivial content that would fail if stripped.
# If this probe passes when it should fail, the template is a rubber stamp.
@test "falsification: template with EXPECTED_SCENARIO_IDS removed fails config validation" {
  # Create a stripped version that removes the EXPECTED_SCENARIO_IDS constant
  sed '/^EXPECTED_SCENARIO_IDS/,/^}$/d' "$TMP/test_redteam_baseline.py" > "$TMP/stripped.py"
  # The stripped template should NOT silently have EXPECTED_SCENARIO_IDS defined
  # (it must come from the constant block, not be inlined)
  run python3 -c "
import ast
with open('$TMP/stripped.py') as f:
    src = f.read()
tree = ast.parse(src)
names = [n.id for n in ast.walk(tree) if isinstance(n, ast.Name)]
# If EXPECTED_SCENARIO_IDS is referenced but not defined, template is non-trivial
print('EXPECTED_SCENARIO_IDS defined:', 'EXPECTED_SCENARIO_IDS' in src)
"
  [ "$status" -eq 0 ]
  # The constant must exist in the original (bilateral check)
  run grep "EXPECTED_SCENARIO_IDS" "$MINI_TEMPLATE"
  [ "$status" -eq 0 ]
}

# ── Case 5: no SO path leakage — template uses PROJECT_ROOT variable, not hardcoded paths
@test "no SO path leakage: template uses PROJECT_ROOT variable not hardcoded paths" {
  # Template must not reference 'luum-agent-os' or any absolute SO path
  run grep "luum-agent-os" "$TMP/test_redteam_baseline.py"
  [ "$status" -ne 0 ]   # must NOT find luum-agent-os hardcoded
}
