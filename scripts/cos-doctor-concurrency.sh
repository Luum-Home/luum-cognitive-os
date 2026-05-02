#!/usr/bin/env bash
# SCOPE: both
# Read-only doctor for concurrent-agent safety primitives.
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
STRICT=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --strict) STRICT=true ;;
    --help|-h)
      cat <<'EOF'
Usage: bash scripts/cos-doctor-concurrency.sh [--strict]
Checks the local concurrent-agent safety proof surface.
EOF
      exit 0
      ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done

failures=0
warnings=0
pass(){ printf 'PASS %s\n' "$*"; }
warn(){ printf 'WARN %s\n' "$*"; warnings=$((warnings+1)); }
fail(){ printf 'FAIL %s\n' "$*"; failures=$((failures+1)); }

printf 'Project: %s\n' "$PROJECT_DIR"

for f in \
  scripts/edit-coop.sh \
  scripts/verify-plan-claims.py \
  scripts/stash-leak-alarm.sh \
  docs/adrs/ADR-108-concurrent-agent-safety-layer.md \
  docs/architecture/concurrent-agent-scenario-test-matrix.md \
  .cognitive-os/plans/architecture/concurrent-agent-safety-testbed-plan.md; do
  if [ -f "$PROJECT_DIR/$f" ]; then pass "exists: $f"; else fail "missing: $f"; fi
done

if bash -n "$PROJECT_DIR/scripts/edit-coop.sh" >/dev/null 2>&1; then pass "edit-coop syntax clean"; else fail "edit-coop syntax failed"; fi
if bash -n "$PROJECT_DIR/scripts/stash-leak-alarm.sh" >/dev/null 2>&1; then pass "stash-leak alarm syntax clean"; else fail "stash-leak alarm syntax failed"; fi
if python3 -m py_compile "$PROJECT_DIR/scripts/verify-plan-claims.py" >/dev/null 2>&1; then pass "plan claim verifier compiles"; else fail "plan claim verifier compile failed"; fi

if [ -f "$PROJECT_DIR/tests/integration/test_concurrent_agent_same_file.py" ]; then pass "scenario test exists: same-file"; else warn "scenario test missing: same-file"; fi
if [ -f "$PROJECT_DIR/tests/behavior/test_plan_false_done_gate.py" ]; then pass "scenario test exists: false-done"; else warn "scenario test missing: false-done"; fi
if [ -f "$PROJECT_DIR/tests/behavior/test_stash_leak_alarm.py" ]; then pass "scenario test exists: stash-leak"; else warn "scenario test missing: stash-leak"; fi

if [ "$STRICT" = true ] && [ "$warnings" -gt 0 ]; then
  failures=$((failures+warnings))
fi

if [ "$failures" -gt 0 ]; then
  printf 'Result: FAIL (%s failure(s), %s warning(s))\n' "$failures" "$warnings"
  exit 1
fi
printf 'Result: PASS (%s warning(s))\n' "$warnings"
