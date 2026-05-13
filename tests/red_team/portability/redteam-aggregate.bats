#!/usr/bin/env bats
# SCOPE: os-only
# Portability test for scripts/redteam_aggregate.py (KD6 gate, §2.2).
#
# Contract invariants per design §2.2:
#   1. Non-SO mini-repo: tempdir with 3 fake scenario JSONs (no SO paths)
#   2. Bilateral assertion: aggregator works from non-SO --input-dir
#   3. Falsification probe: missing schema_version in scenario JSON causes
#      the scenario to be SKIPPED — proves aggregator validates its inputs
#      and does not silently rubber-stamp bad data
#   4. Documented mini-repo: names clearly indicate test structure

SCRIPT="scripts/redteam_aggregate.py"
SO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || cd "$(dirname "$BATS_TEST_FILENAME")/../../.." && pwd)"

setup() {
  TMP="$(mktemp -d)"
  MINI_IN="$TMP/scenario-results"
  MINI_OUT_JSON="$TMP/baseline.json"
  MINI_OUT_MD="$TMP/baseline.md"
  mkdir -p "$MINI_IN"

  # Write 3 valid fake scenario JSON files (non-SO content)
  cat > "$MINI_IN/mini-archive-test.json" <<'EOF'
{
  "scenario": "mini-archive-test",
  "version": "1.0.0",
  "mode": "replay",
  "status": "pass",
  "signals_matched": 2,
  "signals_total": 2,
  "detection_exit": 1,
  "expected_exit": 1,
  "duration_seconds": 0.12,
  "verb": "archived",
  "severity": "HIGH",
  "scope": "both",
  "category": "archive-fallacy"
}
EOF

  cat > "$MINI_IN/mini-wired-test.json" <<'EOF'
{
  "scenario": "mini-wired-test",
  "version": "1.0.0",
  "mode": "replay",
  "status": "pass",
  "signals_matched": 1,
  "signals_total": 1,
  "detection_exit": 0,
  "expected_exit": 0,
  "duration_seconds": 0.08,
  "verb": "wired",
  "severity": "CRITICAL",
  "scope": "both",
  "category": "unwired-constant"
}
EOF

  cat > "$MINI_IN/mini-verified-test.json" <<'EOF'
{
  "scenario": "mini-verified-test",
  "version": "1.0.0",
  "mode": "replay",
  "status": "fail",
  "signals_matched": 0,
  "signals_total": 1,
  "detection_exit": 0,
  "expected_exit": 2,
  "duration_seconds": 0.05,
  "verb": "verified",
  "severity": "HIGH",
  "scope": "both",
  "category": "false-done"
}
EOF
}

teardown() {
  rm -rf "$TMP"
}

# ── Case 1: aggregator reads from non-SO --input-dir and produces JSON ─────────
@test "aggregates 3 fake scenario JSONs from non-SO --input-dir" {
  run python3 "$SO_ROOT/$SCRIPT" \
    --input-dir "$MINI_IN" \
    --output-json "$MINI_OUT_JSON" \
    --output-md "$MINI_OUT_MD"
  # aggregator exits 1 when fail > 0; that's expected (mini-verified-test is fail)
  [ "$status" -le 1 ]
  [ -f "$MINI_OUT_JSON" ]
}

# ── Case 2: output JSON has required schema fields ─────────────────────────────
@test "output JSON has schema_version, generated_at, harness_version, scenarios[], summary, verb_coverage" {
  python3 "$SO_ROOT/$SCRIPT" \
    --input-dir "$MINI_IN" \
    --output-json "$MINI_OUT_JSON" \
    --output-md "$MINI_OUT_MD" || true
  python3 -c "
import json, sys
d = json.load(open('$MINI_OUT_JSON'))
required = ['schema_version', 'generated_at', 'harness_version', 'scenarios', 'summary', 'verb_coverage']
for field in required:
    assert field in d, f'missing field: {field}'
assert d['schema_version'] == '1.0.0', f\"wrong schema_version: {d['schema_version']}\"
assert d['summary']['total'] == 3, f\"expected 3 scenarios, got {d['summary']['total']}\"
assert d['summary']['pass'] == 2, f\"expected 2 pass, got {d['summary']['pass']}\"
assert d['summary']['fail'] == 1, f\"expected 1 fail, got {d['summary']['fail']}\"
print('schema OK')
"
}

# ── Case 3: output Markdown contains table and verb matrix ────────────────────
@test "output Markdown contains scenario table and verb coverage matrix" {
  python3 "$SO_ROOT/$SCRIPT" \
    --input-dir "$MINI_IN" \
    --output-json "$MINI_OUT_JSON" \
    --output-md "$MINI_OUT_MD" || true
  [ -f "$MINI_OUT_MD" ]
  grep -q "Scenario Results" "$MINI_OUT_MD"
  grep -q "Verb Coverage Matrix" "$MINI_OUT_MD"
  grep -q "archived" "$MINI_OUT_MD"
  grep -q "wired" "$MINI_OUT_MD"
}

# ── Case 4 (falsification): scenario JSON missing schema_version is SKIPPED ────
# This is the falsification probe: aggregator must validate inputs, not rubber-stamp.
# A JSON file missing 'scenario' field should be skipped (warning emitted, not counted).
@test "falsification: scenario JSON missing 'scenario' field is skipped (not counted)" {
  # Write a bad JSON file missing required 'scenario' and 'status' fields
  cat > "$MINI_IN/bad-no-schema-version.json" <<'BEOF'
{
  "schema_version_is_missing": "this file is malformed",
  "some_other_field": 42
}
BEOF

  python3 "$SO_ROOT/$SCRIPT" \
    --input-dir "$MINI_IN" \
    --output-json "$MINI_OUT_JSON" \
    --output-md "$MINI_OUT_MD" || true

  # Should still have exactly 3 scenarios (bad file skipped)
  python3 -c "
import json
d = json.load(open('$MINI_OUT_JSON'))
assert d['summary']['total'] == 3, f\"expected 3 after skip, got {d['summary']['total']}\"
print('falsification OK: bad JSON skipped')
"
}

# ── Case 5: --baseline-compare produces diff section ─────────────────────────
@test "--baseline-compare adds Baseline Diff section to Markdown" {
  python3 "$SO_ROOT/$SCRIPT" \
    --input-dir "$MINI_IN" \
    --output-json "$MINI_OUT_JSON" \
    --output-md "$MINI_OUT_MD" || true

  # Now create a prior baseline with different statuses
  PRIOR_JSON="$TMP/prior-baseline.json"
  python3 -c "
import json
prior = {
    'schema_version': '1.0.0',
    'generated_at': '2026-01-01T00:00:00Z',
    'harness_version': '1.0.0',
    'scenarios': [
        {'id': 'mini-archive-test', 'version': '1.0.0', 'status': 'fail',
         'verb': 'archived', 'severity': 'HIGH', 'duration_seconds': 0.1,
         'scope': 'both', 'category': 'archive-fallacy',
         'signals_matched': 1, 'signals_total': 2}
    ],
    'summary': {'total': 1, 'pass': 0, 'fail': 1, 'partial': 0, 'xfail': 0, 'error': 0},
    'verb_coverage': {'archived': 1}
}
with open('$PRIOR_JSON', 'w') as f:
    json.dump(prior, f)
print('prior baseline written')
"
  DIFF_MD="$TMP/baseline-diff.md"
  python3 "$SO_ROOT/$SCRIPT" \
    --input-dir "$MINI_IN" \
    --output-json "$MINI_OUT_JSON" \
    --output-md "$DIFF_MD" \
    --baseline-compare "$PRIOR_JSON" || true

  grep -q "Baseline Diff" "$DIFF_MD"
}
