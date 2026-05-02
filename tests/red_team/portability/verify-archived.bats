#!/usr/bin/env bats
# SCOPE: both
# Portability test for scripts/verify-archived.sh (KD6 gate, §2.2).
#
# Contract invariants per design §2.2:
#   1. Non-SO mini-repo: tempdir with non-SO structure (attic/ not docs/archive/hooks/)
#   2. Bilateral assertion: succeeds in mini-repo AND does not rely on SO paths
#   3. Falsification probe: deliberate trap causes expected failure
#   4. Documented mini-repo: names clearly indicate test structure

SCRIPT="scripts/verify-archived.sh"

setup() {
  TMP="$(mktemp -d)"
  # Mini-repo with non-SO directory names (attic/scripts, not docs/archive/hooks/)
  mkdir -p "$TMP/attic/scripts" "$TMP/scripts"
  printf '#!/bin/bash\necho original\n' > "$TMP/scripts/old.sh"
  printf '#!/bin/bash\necho archived copy\n' > "$TMP/attic/scripts/old.sh"
  chmod +x "$TMP/scripts/old.sh" "$TMP/attic/scripts/old.sh"
}

teardown() {
  rm -rf "$TMP"
}

# ── Case 1: bilateral success ─────────────────────────────────────────────────
# Archive present + source absent → exit 0
@test "succeeds bilaterally: archive present and source removed" {
  rm "$TMP/scripts/old.sh"
  run "$SCRIPT" \
    --archive-dir "$TMP/attic/scripts" \
    --source-dir  "$TMP/scripts" \
    --manifest    "old.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"[OK]"* ]]
}

# ── Case 2: Wave-C trap detection ────────────────────────────────────────────
# Source still present → exit 1 (the archive-presence fallacy)
@test "detects archive-presence fallacy: source still present (Wave C trap)" {
  # Do NOT remove source — this is the false-done scenario
  run "$SCRIPT" \
    --archive-dir "$TMP/attic/scripts" \
    --source-dir  "$TMP/scripts" \
    --manifest    "old.sh"
  [ "$status" -eq 1 ]
  [[ "$output" == *"[FAIL]"* ]]
}

# ── Case 3: falsification probe ──────────────────────────────────────────────
# Archive also missing (nothing there) → must fail, not silently pass
@test "falsification: missing archive must not be treated as archived" {
  rm "$TMP/attic/scripts/old.sh"
  rm "$TMP/scripts/old.sh"
  run "$SCRIPT" \
    --archive-dir "$TMP/attic/scripts" \
    --source-dir  "$TMP/scripts" \
    --manifest    "old.sh"
  # Must NOT exit 0 — nothing is archived if the archive copy is also absent
  [ "$status" -ne 0 ]
}

# ── Case 4: no SO path leakage ───────────────────────────────────────────────
# Component must work from a CWD completely outside the SO repo
@test "no SO path leakage: works from non-SO working directory" {
  rm "$TMP/scripts/old.sh"
  # Change CWD to TMP (non-SO dir) before invoking
  cd "$TMP"
  run "$SCRIPT" \
    --archive-dir "$TMP/attic/scripts" \
    --source-dir  "$TMP/scripts" \
    --manifest    "old.sh"
  [ "$status" -eq 0 ]
  # Output must not contain SO-specific paths
  [[ "$output" != *"docs/archive/hooks"* ]]
  [[ "$output" != *"hooks/self-install"* ]]
}

# ── Case 5: JSON mode output shape ───────────────────────────────────────────
@test "JSON mode emits valid JSON with expected keys" {
  rm "$TMP/scripts/old.sh"
  run "$SCRIPT" \
    --archive-dir "$TMP/attic/scripts" \
    --source-dir  "$TMP/scripts" \
    --manifest    "old.sh" \
    --json
  [ "$status" -eq 0 ]
  # Minimal JSON shape check without requiring jq
  [[ "$output" == *'"verified": true'* ]]
  [[ "$output" == *'"archive_present":true'* ]]
  [[ "$output" == *'"source_absent":true'* ]]
}

# ── Case 6: exit code 2 for missing archive (distinct from exit 1) ───────────
@test "exit code 2 when archive copy is missing but source was removed" {
  rm "$TMP/scripts/old.sh"
  rm "$TMP/attic/scripts/old.sh"
  run "$SCRIPT" \
    --archive-dir "$TMP/attic/scripts" \
    --source-dir  "$TMP/scripts" \
    --manifest    "old.sh"
  [ "$status" -eq 2 ]
}

# ── Case 7: missing required args → exit 4 ───────────────────────────────────
@test "exit code 4 on missing required arguments" {
  run "$SCRIPT" --archive-dir "$TMP/attic/scripts"
  [ "$status" -eq 4 ]
}
