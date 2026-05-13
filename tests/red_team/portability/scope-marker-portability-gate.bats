#!/usr/bin/env bats
# SCOPE: os-only

setup() {
  REPO="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$REPO/hooks/_lib" "$REPO/tests/red_team/portability" "$REPO/.cognitive-os/metrics"
  cp "$BATS_TEST_DIRNAME/../../../hooks/scope-marker-portability-gate.sh" "$REPO/hooks/"
  cp "$BATS_TEST_DIRNAME/../../../hooks/_lib/common.sh" "$REPO/hooks/_lib/"
  git -C "$REPO" init -q
  git -C "$REPO" config user.email test@example.com
  git -C "$REPO" config user.name Test
}

payload() {
  python3 - <<'PY'
import json
print(json.dumps({"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}))
PY
}

@test "allows git commit when no SCOPE both files are staged" {
  echo "plain" > "$REPO/plain.txt"
  git -C "$REPO" add plain.txt
  run bash "$REPO/hooks/scope-marker-portability-gate.sh" <<<"$(payload)"
  [ "$status" -eq 0 ]
}

@test "allows SCOPE both file with paired portability test" {
  cat > "$REPO/hooks/example-hook.sh" <<'SH'
#!/usr/bin/env bash
# SCOPE: os-only
echo ok
SH
  cat > "$REPO/tests/red_team/portability/example-hook.bats" <<'BT'
#!/usr/bin/env bats
@test "falsification: bad input fails" { false; }
BT
  git -C "$REPO" add hooks/example-hook.sh tests/red_team/portability/example-hook.bats
  run bash "$REPO/hooks/scope-marker-portability-gate.sh" <<<"$(payload)"
  [ "$status" -eq 0 ]
}

@test "falsification: blocks SCOPE both file without portability test" {
  cat > "$REPO/hooks/unproven-hook.sh" <<'SH'
#!/usr/bin/env bash
# SCOPE: os-only
echo unproven
SH
  git -C "$REPO" add hooks/unproven-hook.sh
  run bash "$REPO/hooks/scope-marker-portability-gate.sh" <<<"$(payload)"
  [ "$status" -eq 2 ]
  [[ "$output" == *"unproven-hook.sh"* ]]
}

@test "bypass allows unproven SCOPE both file for emergency commits" {
  cat > "$REPO/hooks/bypass-hook.sh" <<'SH'
#!/usr/bin/env bash
# SCOPE: os-only
echo bypass
SH
  git -C "$REPO" add hooks/bypass-hook.sh
  run env COS_ALLOW_UNPROVEN_SCOPE_BOTH=1 bash "$REPO/hooks/scope-marker-portability-gate.sh" <<<"$(payload)"
  [ "$status" -eq 0 ]
}
