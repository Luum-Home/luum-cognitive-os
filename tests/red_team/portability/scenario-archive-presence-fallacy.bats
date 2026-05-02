#!/usr/bin/env bats
# SCOPE: both
# Portability test for tests/red_team/scenarios/archive-presence-fallacy.yaml (KD6 gate, §2.2).
#
# Contract invariants per design §2.2:
#   1. Non-SO mini-repo: tempdir uses attic/ not docs/archive/hooks/
#   2. Bilateral assertion: detection succeeds in mini-repo, no SO path reliance
#   3. Falsification probe: scenario with NO originals still live must NOT pass detection
#   4. Documented mini-repo: names clearly indicate test structure

SCENARIO="archive-presence-fallacy"
VERIFY_SCRIPT="scripts/verify-archived.sh"

setup() {
  TMP="$(mktemp -d)"
  # Mini-repo with non-SO directory names (attic/hooks, not docs/archive/hooks/)
  mkdir -p "$TMP/attic/hooks" "$TMP/active-hooks" "$TMP/.claude"

  # Seed: source files still present (the "false-done" state)
  printf '#!/bin/bash\necho live completeness\n' > "$TMP/active-hooks/completeness-check.sh"
  printf '#!/bin/bash\necho live post-verify\n'  > "$TMP/active-hooks/post-agent-verify.sh"
  printf '#!/bin/bash\necho live prompt-q\n'     > "$TMP/active-hooks/prompt-quality.sh"
  chmod +x "$TMP/active-hooks/"*.sh

  # Seed: archive copies also present (bilateral trap — both sides exist)
  printf '#!/bin/bash\necho archived completeness\n' > "$TMP/attic/hooks/completeness-check.sh"
  printf '#!/bin/bash\necho archived post-verify\n'  > "$TMP/attic/hooks/post-agent-verify.sh"
  printf '#!/bin/bash\necho archived prompt-q\n'     > "$TMP/attic/hooks/prompt-quality.sh"

  # Seed: settings with stale reference
  printf '{"hooks":{"PostToolUse":[{"matcher":"Edit","hooks":[{"type":"command","command":"bash active-hooks/post-agent-verify.sh"}]}]}}' \
    > "$TMP/.claude/settings.json"
}

teardown() {
  rm -rf "$TMP"
}

# ── Case 1: bilateral success (properly archived — source absent, archive present) ──
@test "detection passes when source absent and archive present (true archive)" {
  rm "$TMP/active-hooks/completeness-check.sh" \
     "$TMP/active-hooks/post-agent-verify.sh" \
     "$TMP/active-hooks/prompt-quality.sh"
  run "$VERIFY_SCRIPT" \
    --archive-dir "$TMP/attic/hooks" \
    --source-dir  "$TMP/active-hooks" \
    --manifest    "completeness-check.sh,post-agent-verify.sh,prompt-quality.sh"
  [ "$status" -eq 0 ]
  [[ "$output" == *"[OK]"* ]]
}

# ── Case 2: trap detection — source still present (the archive-presence fallacy) ──
@test "scenario trap: detection exits non-zero when source still present" {
  # Sources are NOT removed — this mirrors the false-done scenario state
  run "$VERIFY_SCRIPT" \
    --archive-dir "$TMP/attic/hooks" \
    --source-dir  "$TMP/active-hooks" \
    --manifest    "completeness-check.sh,post-agent-verify.sh,prompt-quality.sh"
  [ "$status" -eq 1 ]
  [[ "$output" == *"[FAIL]"* ]]
}

# ── Case 3: falsification probe — neither side exists, must NOT exit 0 ──────────
# If the script treats "both absent" as "archived", it's a rubber-stamp. This probe
# catches that: a completely empty directory must never count as "archived".
@test "falsification: all files absent on both sides must not produce exit 0" {
  rm "$TMP/active-hooks/completeness-check.sh" \
     "$TMP/active-hooks/post-agent-verify.sh" \
     "$TMP/active-hooks/prompt-quality.sh"
  rm "$TMP/attic/hooks/completeness-check.sh" \
     "$TMP/attic/hooks/post-agent-verify.sh" \
     "$TMP/attic/hooks/prompt-quality.sh"
  run "$VERIFY_SCRIPT" \
    --archive-dir "$TMP/attic/hooks" \
    --source-dir  "$TMP/active-hooks" \
    --manifest    "completeness-check.sh,post-agent-verify.sh,prompt-quality.sh"
  # MUST NOT succeed — nothing is archived if archive copies are also absent
  [ "$status" -ne 0 ]
}

# ── Case 4: no SO path leakage — works from non-SO CWD ─────────────────────────
@test "no SO path leakage: script works from non-SO working directory" {
  rm "$TMP/active-hooks/completeness-check.sh" \
     "$TMP/active-hooks/post-agent-verify.sh" \
     "$TMP/active-hooks/prompt-quality.sh"
  cd "$TMP"
  run "$OLDPWD/$VERIFY_SCRIPT" \
    --archive-dir "$TMP/attic/hooks" \
    --source-dir  "$TMP/active-hooks" \
    --manifest    "completeness-check.sh,post-agent-verify.sh,prompt-quality.sh"
  [ "$status" -eq 0 ]
  [[ "$output" != *"docs/archive/hooks"* ]]
  [[ "$output" != *"luum-agent-os"* ]]
}

# ── Case 5: partial manifest — one still present, two properly archived ──────────
@test "partial manifest: exit 1 when at least one source file remains" {
  # Only remove two of the three sources
  rm "$TMP/active-hooks/completeness-check.sh" \
     "$TMP/active-hooks/post-agent-verify.sh"
  # prompt-quality.sh still present
  run "$VERIFY_SCRIPT" \
    --archive-dir "$TMP/attic/hooks" \
    --source-dir  "$TMP/active-hooks" \
    --manifest    "completeness-check.sh,post-agent-verify.sh,prompt-quality.sh"
  [ "$status" -eq 1 ]
}
