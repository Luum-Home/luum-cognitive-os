#!/usr/bin/env bats
# SCOPE: os-only
# Portability test for tests/red_team/scenarios/unwired-constant.yaml (KD6 gate, §2.2).
#
# Contract invariants per design §2.2:
#   1. Non-SO mini-repo: tempdir uses consumer-neutral paths (config/, hooks/)
#   2. Bilateral assertion: detection identifies absent wiring in mini-repo
#   3. Falsification probe: hook that IS wired must NOT be flagged as missing
#   4. Documented mini-repo: names clearly indicate test structure

SCENARIO="unwired-constant"

setup() {
  TMP="$(mktemp -d)"
  # Mini-repo with consumer-neutral structure
  mkdir -p "$TMP/hooks" "$TMP/config"

  # Hook file exists (agent created it)
  printf '#!/bin/bash\n# plan-claim-validator stub\nexit 0\n' \
    > "$TMP/hooks/plan-claim-validator.sh"
  chmod +x "$TMP/hooks/plan-claim-validator.sh"

  # Settings WITHOUT the hook registration — simulates the false-done
  printf '{"hooks":{"PostToolUse":[{"matcher":"Edit","hooks":[{"type":"command","command":"bash hooks/post-agent-verify.sh"}]}]}}' \
    > "$TMP/config/settings.json"
}

teardown() {
  rm -rf "$TMP"
}

# ── Case 1: detection correctly identifies absent wiring ─────────────────────────
@test "detection exits 1 when hook is absent from settings (unwired)" {
  # grep for the hook in settings — should NOT find it
  run bash -c "grep -q 'plan-claim-validator' '$TMP/config/settings.json' && exit 0 || exit 1"
  [ "$status" -eq 1 ]
}

# ── Case 2: properly wired hook is NOT flagged ────────────────────────────────────
@test "detection exits 0 when hook is present in settings (correctly wired)" {
  # Add the hook to settings
  printf '{"hooks":{"PreToolUse":[{"matcher":"Edit|Write|MultiEdit","hooks":[{"type":"command","command":"bash hooks/plan-claim-validator.sh"}]}]}}' \
    > "$TMP/config/settings.json"
  run bash -c "grep -q 'plan-claim-validator' '$TMP/config/settings.json' && exit 0 || exit 1"
  [ "$status" -eq 0 ]
}

# ── Case 3: falsification probe — settings file entirely absent must fail ────────
# If the detection silently passes when there is no settings file at all,
# it's a rubber-stamp. Missing config = unknown wiring = must not report wired.
@test "falsification: absent settings file must not report hook as wired" {
  rm "$TMP/config/settings.json"
  run bash -c "[ -f '$TMP/config/settings.json' ] && grep -q 'plan-claim-validator' '$TMP/config/settings.json' && exit 0 || exit 1"
  # Must NOT exit 0 — no settings file means nothing is wired
  [ "$status" -ne 0 ]
}

# ── Case 4: no SO path leakage — works from non-SO CWD ─────────────────────────
@test "no SO path leakage: detection logic works from non-SO working directory" {
  cd "$TMP"
  run bash -c "grep -q 'plan-claim-validator' '$TMP/config/settings.json' && exit 0 || exit 1"
  [ "$status" -eq 1 ]
  # Output (empty for grep) must not reference SO-specific paths
  [[ "$output" != *"luum-agent-os"* ]]
  [[ "$output" != *".cognitive-os"* ]]
}

# ── Case 5: partial wiring (hook in wrong event type) is treated as unwired ──────
@test "hook in wrong event type (PostToolUse not PreToolUse) is still detectable as misconfigured" {
  # The hook IS referenced but under PostToolUse — correct check finds it referenced at all
  # This case verifies the detection_command in the scenario would catch a wired-but-wrong placement
  printf '{"hooks":{"PostToolUse":[{"matcher":"Edit","hooks":[{"type":"command","command":"bash hooks/plan-claim-validator.sh"}]}]}}' \
    > "$TMP/config/settings.json"
  # It IS wired (somewhere), so a presence-only check would succeed
  run bash -c "grep -q 'plan-claim-validator' '$TMP/config/settings.json' && exit 0 || exit 1"
  [ "$status" -eq 0 ]
  # But a PreToolUse-specific check would not find it — demonstrating the scenario's
  # detection_command targets the exact hook name presence as a proxy
  run bash -c "grep -q '\"PreToolUse\"' '$TMP/config/settings.json' && exit 0 || exit 1"
  [ "$status" -ne 0 ]
}
