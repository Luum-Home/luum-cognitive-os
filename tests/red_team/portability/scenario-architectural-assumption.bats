#!/usr/bin/env bats
# SCOPE: os-only
# Portability test for scenario architectural-assumption — verifies the
# scenario YAML executes correctly in a non-SO mini-repo (tempdir) and
# that the symlink-mutation-guard catches the false-architecture pattern.
#
# 5 cases — exceeds KD6 minimum of 4. Falsification probe: ensure a
# rubber-stamp implementation (one that doesn't actually check parent
# symlink) is detected.

setup() {
  TMPREPO="$(mktemp -d)"
  mkdir -p "$TMPREPO/packages/example-pkg/lib/example_dir"
  echo "# real" > "$TMPREPO/packages/example-pkg/lib/example_dir/real.py"
  ln -s "../packages/example-pkg/lib/example_dir" "$TMPREPO/lib/example_dir" 2>/dev/null || {
    mkdir -p "$TMPREPO/lib"
    ln -s "../packages/example-pkg/lib/example_dir" "$TMPREPO/lib/example_dir"
  }
  GUARD_HOOK="$BATS_TEST_DIRNAME/../../../hooks/symlink-mutation-guard.sh"
}

teardown() {
  rm -rf "$TMPREPO"
}

@test "scenario YAML is valid: required fields present" {
  YAML="$BATS_TEST_DIRNAME/../scenarios/architectural-assumption.yaml"
  [ -f "$YAML" ]
  run python3 -c "import yaml; d=yaml.safe_load(open('$YAML')); \
    assert d['scope']=='both'; \
    assert 'replay' in d and 'initial_state' in d and 'expected_fail_mode' in d; \
    assert 'grading_rubric' in d; \
    print('OK')"
  [ "$status" -eq 0 ]
}

@test "guard hook BLOCKS rm+ln-s relative inside dir-symlink (the incident)" {
  cd "$TMPREPO"
  run bash -c "echo '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ln -s ../../packages/example-pkg/lib/example_dir/real.py lib/example_dir/real.py\"}}' | \
    COGNITIVE_OS_PROJECT_DIR=$TMPREPO bash $GUARD_HOOK"
  [ "$status" -eq 2 ]
}

@test "guard hook ALLOWS ln -s with absolute target (workaround #1)" {
  cd "$TMPREPO"
  run bash -c "echo '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ln -s /tmp/source-abs lib/example_dir/abs.py\"}}' | \
    COGNITIVE_OS_PROJECT_DIR=$TMPREPO bash $GUARD_HOOK"
  [ "$status" -eq 0 ]
}

@test "guard hook ALLOWS ln -s outside any symlink ancestor" {
  cd "$TMPREPO"
  mkdir -p "$TMPREPO/regular_dir"
  run bash -c "echo '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ln -s ../packages/example-pkg/lib/example_dir/real.py regular_dir/link.py\"}}' | \
    COGNITIVE_OS_PROJECT_DIR=$TMPREPO bash $GUARD_HOOK"
  [ "$status" -eq 0 ]
}

@test "falsification: rubber-stamp guard that just echoes 'OK' must NOT block — a real guard MUST exit 2 on the trap" {
  # Create a fake guard that always allows (rubber-stamp)
  RUBBER="$TMPREPO/rubber-guard.sh"
  cat > "$RUBBER" <<'EOF'
#!/bin/bash
# Rubber-stamp: doesn't actually check anything
cat > /dev/null
exit 0
EOF
  chmod +x "$RUBBER"

  # Rubber-stamp lets through the dangerous pattern:
  run bash -c "echo '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ln -s ../../foo lib/example_dir/x.py\"}}' | bash $RUBBER"
  [ "$status" -eq 0 ]   # rubber-stamp always allows

  # Real guard MUST block the same pattern. If they behave the same, the falsification probe failed.
  run bash -c "echo '{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ln -s ../../foo lib/example_dir/x.py\"}}' | \
    COGNITIVE_OS_PROJECT_DIR=$TMPREPO bash $GUARD_HOOK"
  [ "$status" -eq 2 ]   # real guard blocks
}
