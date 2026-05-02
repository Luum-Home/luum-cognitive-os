#!/usr/bin/env bats
# SCOPE: both
# Portability test for hooks/plan-claim-validator.sh (KD6 gate, §2.2).
#
# Contract invariants per design §2.2:
#   1. Non-SO mini-repo: tempdir uses "plans/" not ".cognitive-os/plans/"
#   2. Bilateral assertion: hook works in mini-repo, does not rely on SO paths
#   3. Falsification probe: unverified checkbox in block mode must exit 2
#   4. Documented mini-repo: names clearly indicate test structure

HOOK="hooks/plan-claim-validator.sh"

setup() {
  TMP="$(mktemp -d)"
  # Mini-repo with non-SO directory names
  mkdir -p "$TMP/plans" "$TMP/.cognitive-os/metrics" "$TMP/scripts"
}

teardown() {
  rm -rf "$TMP"
}

# ── Case 1: non-plan file is silently ignored ─────────────────────────────────
@test "non-plan file is ignored (exit 0, no output)" {
  input="{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$TMP/scripts/foo.py\",\"new_string\":\"# code\"}}"
  run bash -c "echo '$input' | COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.cognitive-os/metrics' \
    bash '$HOOK'"
  [ "$status" -eq 0 ]
}

# ── Case 2: verified checkbox passes silently ─────────────────────────────────
@test "verified checkbox (has (verified:...)) exits 0 and writes claim.passed metric" {
  local content="- [x] Deploy script archived (verified: ls scripts/deploy.sh)"
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [x] Deploy script archived (verified: ls scripts/deploy.sh)\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.cognitive-os/metrics' \
    bash '$HOOK'"
  [ "$status" -eq 0 ]
  grep -q '"decision":"claim.passed"' "$TMP/.cognitive-os/metrics/plan-claim-validator.jsonl"
}

# ── Case 3: unverified checkbox in warn mode exits 0 with warning ────────────
@test "unverified checkbox in warn mode exits 0 and emits claim.failed metric" {
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [x] Task done without any proof\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.cognitive-os/metrics' \
    COS_PLAN_VALIDATOR_MODE='warn' \
    bash '$HOOK'"
  [ "$status" -eq 0 ]
  grep -q '"decision":"claim.failed"' "$TMP/.cognitive-os/metrics/plan-claim-validator.jsonl"
}

# ── Case 4: falsification — unverified checkbox in block mode MUST exit 2 ────
# This is the falsification probe: if block mode does NOT exit 2, the hook is broken.
@test "falsification: block mode exits 2 for unverified [x] checkbox (must NOT pass)" {
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [x] Task done without proof\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.cognitive-os/metrics' \
    COS_PLAN_VALIDATOR_MODE='block' \
    bash '$HOOK'"
  # MUST exit 2 — if this passes with 0, the hook is a rubber-stamp
  [ "$status" -eq 2 ]
}

# ── Case 5: no SO path leakage ───────────────────────────────────────────────
@test "no SO path leakage: works from non-SO working directory" {
  cd "$TMP"
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [x] Task done without proof\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.cognitive-os/metrics' \
    COS_PLAN_VALIDATOR_MODE='warn' \
    bash '$HOOK'"
  [ "$status" -eq 0 ]
  [[ "$output" != *".cognitive-os/plans"* ]]
  [[ "$output" != *"hooks/self-install"* ]]
}

# ── Case 6: metrics JSONL is created in COS_METRICS_DIR ──────────────────────
@test "metrics JSONL is created in COS_METRICS_DIR on violation" {
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [x] Another unchecked task\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.cognitive-os/metrics' \
    COS_PLAN_VALIDATOR_MODE='warn' \
    bash '$HOOK'"
  [ -f "$TMP/.cognitive-os/metrics/plan-claim-validator.jsonl" ]
}

# ── Case 7: unchecked box [ ] is NOT flagged ─────────────────────────────────
@test "unchecked checkbox [ ] is not treated as a violation" {
  run bash -c "printf '%s' '{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$TMP/plans/sprint.md\",\"content\":\"- [ ] Task still pending\"}}' | \
    COS_PLAN_GLOB='plans/**/*.md' CLAUDE_PROJECT_DIR='$TMP' \
    COS_METRICS_DIR='$TMP/.cognitive-os/metrics' \
    COS_PLAN_VALIDATOR_MODE='block' \
    bash '$HOOK'"
  [ "$status" -eq 0 ]
}
