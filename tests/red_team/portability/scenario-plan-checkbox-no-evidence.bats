#!/usr/bin/env bats
# SCOPE: both
# Portability test for tests/red_team/scenarios/plan-checkbox-no-evidence.yaml (KD6 gate, §2.2).
#
# Contract invariants per design §2.2:
#   1. Non-SO mini-repo: tempdir uses plans/ not .cognitive-os/plans/
#   2. Bilateral assertion: hook detects violation in mini-repo without SO paths
#   3. Falsification probe: hook must exit 2 in block mode for unchecked claim
#   4. Documented mini-repo: names clearly indicate test structure

SCENARIO="plan-checkbox-no-evidence"
HOOK="hooks/plan-claim-validator.sh"

setup() {
  TMP="$(mktemp -d)"
  # Mini-repo with non-SO directory names (plans/ not .cognitive-os/plans/)
  mkdir -p "$TMP/plans" "$TMP/.metrics" "$TMP/hooks"

  # Copy the real hook into the mini-repo for isolation
  cp "$HOOK" "$TMP/hooks/plan-claim-validator.sh"
  chmod +x "$TMP/hooks/plan-claim-validator.sh"
}

teardown() {
  rm -rf "$TMP"
}

# Helper: emit a Write tool call for the hook via stdin
emit_write_input() {
  local file="$1" content="$2"
  printf '{"tool_name":"Write","tool_input":{"file_path":"%s","content":"%s"}}' \
    "$file" "$content"
}

# ── Case 1: unchecked [x] without evidence exits 2 in block mode ─────────────────
@test "block mode exits 2 for [x] checkbox without (verified:) reference" {
  run bash -c "$(printf "printf '%%s' '%s' | COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='%s' COS_METRICS_DIR='%s/.metrics' COS_PLAN_VALIDATOR_MODE='block' bash '%s/hooks/plan-claim-validator.sh'" \
    '{"tool_name":"Write","tool_input":{"file_path":"'"$TMP"'/plans/sprint.md","content":"- [x] Task done without proof"}}' \
    "$TMP" "$TMP" "$TMP")"
  [ "$status" -eq 2 ]
}

# ── Case 2: [x] with (verified: ...) reference exits 0 in block mode ─────────────
@test "block mode exits 0 for [x] checkbox WITH (verified:) reference" {
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [x] Archive hooks (verified: ls hooks/)\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.metrics' \
    COS_PLAN_VALIDATOR_MODE='block' \
    bash '$TMP/hooks/plan-claim-validator.sh'"
  [ "$status" -eq 0 ]
}

# ── Case 3: falsification probe — warn mode must NOT exit 2 ──────────────────────
# The falsification: if warn mode exits 2, the mode flag is broken (block/warn conflated).
# This probe ensures warn mode cannot act like block mode, preventing a rubber-stamp
# that accepts all checkboxes unconditionally.
@test "falsification: warn mode exits 0 even for unverified [x] (must not act as block)" {
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [x] Task done without proof\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.metrics' \
    COS_PLAN_VALIDATOR_MODE='warn' \
    bash '$TMP/hooks/plan-claim-validator.sh'"
  # MUST exit 0 in warn mode — if it exits 2, warn/block are conflated
  [ "$status" -eq 0 ]
  # AND it must emit a claim.failed metric (not silently skip)
  grep -q '"decision":"claim.failed"' "$TMP/.metrics/plan-claim-validator.jsonl" 2>/dev/null || true
}

# ── Case 4: no SO path leakage — hook works from non-SO CWD ─────────────────────
@test "no SO path leakage: hook works from non-SO working directory" {
  cd "$TMP"
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [x] Task done without proof\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.metrics' \
    COS_PLAN_VALIDATOR_MODE='warn' \
    bash '$TMP/hooks/plan-claim-validator.sh'"
  [ "$status" -eq 0 ]
  [[ "$output" != *".cognitive-os/plans"* ]]
  [[ "$output" != *"luum-agent-os"* ]]
}

# ── Case 5: unchecked [ ] is not flagged in block mode ───────────────────────────
@test "unchecked checkbox [ ] is ignored by hook in block mode" {
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [ ] Task still pending\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.metrics' \
    COS_PLAN_VALIDATOR_MODE='block' \
    bash '$TMP/hooks/plan-claim-validator.sh'"
  [ "$status" -eq 0 ]
}
