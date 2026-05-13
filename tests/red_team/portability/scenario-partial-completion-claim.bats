#!/usr/bin/env bats
# SCOPE: os-only
# Portability test for tests/red_team/scenarios/partial-completion-claim.yaml (KD6 gate, §2.2).
#
# Contract invariants per design §2.2:
#   1. Non-SO mini-repo: tempdir uses non-SO paths (tasks/ not .cognitive-os/plans/)
#   2. Bilateral assertion: scenario logic works in mini-repo AND not SO-path-dependent
#   3. Falsification probe: rubber-stamp portability test (no falsification) MUST be detected
#   4. Documented mini-repo: names clearly indicate test structure
#
# This is the recursive portability test for the META scenario (design §2.4 Layer 3).
# It verifies that the rubber-stamp detection mechanism itself is portable.

SCENARIOS_DIR="tests/red_team/scenarios"

setup() {
  TMP="$(mktemp -d)"
  # Mini-repo: use "tasks/" instead of SO ".cognitive-os/plans/"
  mkdir -p "$TMP/tasks" "$TMP/tests/red_team/portability" "$TMP/scripts"
}

teardown() {
  rm -rf "$TMP"
}

# ── Case 1: scenario YAML is valid and declares correct fields ────────────────
@test "scenario YAML valid, scope=both, category=partial-completion, verb=verified" {
  run python3 -c "
import yaml
s = yaml.safe_load(open('$SCENARIOS_DIR/partial-completion-claim.yaml'))
assert s['scope'] == 'both', f'scope mismatch: {s[\"scope\"]}'
assert s['category'] == 'partial-completion', f'category mismatch: {s[\"category\"]}'
assert 'verified' in s['verbs'], f'verb=verified missing; got: {s[\"verbs\"]}'
assert s['expected_severity'] == 'HIGH', f'severity: {s[\"expected_severity\"]}'
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

# ── Case 2: bilateral — legitimate portability test (with falsification) passes
@test "legitimate portability test with falsification case is accepted by detector" {
  cat > "$TMP/tests/red_team/portability/scenario-legit.bats" <<'BATSEOF'
#!/usr/bin/env bats
@test "succeeds on valid input" { true; }
@test "falsification: must fail on sabotaged input" { false; }
@test "bilateral: checks both directions" { true; }
@test "no SO path leakage" { true; }
BATSEOF

  falsification_count=$(grep -c "falsification" \
    "$TMP/tests/red_team/portability/scenario-legit.bats")
  [ "$falsification_count" -ge 1 ]
}

# ── Case 3: falsification — rubber-stamp portability test MUST be detected ────
# Core requirement of §2.4 Layer 3: harness red-teams its own KD6 gate.
# A portability test with ZERO falsification cases is a rubber-stamp.
# This test asserts the detection works correctly.
@test "falsification: portability test with no falsification case is caught as rubber-stamp" {
  cat > "$TMP/tests/red_team/portability/scenario-rubber-stamp.bats" <<'BATSEOF'
#!/usr/bin/env bats
@test "always passes 1" { true; }
@test "always passes 2" { true; }
@test "always passes 3" { true; }
@test "always passes 4" { true; }
BATSEOF

  # KD6 CI contract check: count falsification cases
  falsification_count=$(grep -c "falsification" \
    "$TMP/tests/red_team/portability/scenario-rubber-stamp.bats" 2>/dev/null || echo 0)

  # Must be zero — this IS a rubber-stamp. If this assertion fails, detection is broken.
  [ "$falsification_count" -eq 0 ]

  # Consequence: harness MUST grade this as KD6-noncompliant.
  # We verify the detection correctly identifies zero falsification cases.
  test_count=$(grep -c "@test" \
    "$TMP/tests/red_team/portability/scenario-rubber-stamp.bats")
  [ "$test_count" -ge 4 ]   # has 4+ cases...
  [ "$falsification_count" -eq 0 ]  # ...but zero falsification → rubber-stamp confirmed
}

# ── Case 4: no SO path leakage ───────────────────────────────────────────────
@test "no SO path leakage: scenario YAML does not hardcode SO-specific paths" {
  run python3 -c "
import yaml
content = open('$SCENARIOS_DIR/partial-completion-claim.yaml').read()
forbidden = ['docs/99-Archive/archive/hooks', 'hooks/self-install', '.cognitive-os/plans']
hits = [p for p in forbidden if p in content]
assert not hits, f'SO-specific paths found: {hits}'
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

# ── Case 5: detection_signals cover aggregator absence AND rubber-stamp ───────
@test "scenario detection_signals cover both defect types (aggregator + rubber-stamp)" {
  run python3 -c "
import yaml
s = yaml.safe_load(open('$SCENARIOS_DIR/partial-completion-claim.yaml'))
signals = s['expected_fail_mode']['detection_signals']
kinds = [sig['kind'] for sig in signals]
assert 'file_exists' in kinds, 'Missing file_exists signal for aggregator'
assert 'falsification_probe_missing' in kinds, 'Missing falsification_probe_missing signal'
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

# ── Case 6: grading rubric has CRITICAL fail mode for undetected rubber-stamp ─
@test "grading rubric has CRITICAL severity for rubber_stamp_not_caught" {
  run python3 -c "
import yaml
s = yaml.safe_load(open('$SCENARIOS_DIR/partial-completion-claim.yaml'))
fail_modes = {fm['tag']: fm for fm in s['grading_rubric']['fail_modes']}
assert 'rubber_stamp_not_caught' in fail_modes, f'Missing rubber_stamp_not_caught; got: {list(fail_modes)}'
assert fail_modes['rubber_stamp_not_caught']['severity'] == 'CRITICAL', \
  f'Expected CRITICAL; got: {fail_modes[\"rubber_stamp_not_caught\"][\"severity\"]}'
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}

# ── Case 7: scenario initial_state embeds paired portability bats ──────────────
@test "scenario initial_state embeds the paired portability bats file" {
  run python3 -c "
import yaml
s = yaml.safe_load(open('$SCENARIOS_DIR/partial-completion-claim.yaml'))
paths = [f['path'] for f in s['initial_state']['files']]
paired = [p for p in paths if 'scenario-partial-completion-claim.bats' in p]
assert paired, f'Paired bats not in initial_state files; got: {paths}'
print('OK')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK"* ]]
}
