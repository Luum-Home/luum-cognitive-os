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
  scripts/git-coop.sh \
  scripts/verify_plan_claims.py \
  scripts/stash-leak-alarm.sh \
  scripts/cos-doctor-preserve.sh \
  scripts/resource_lease.py \
  scripts/agent_work_ledger.py \
  scripts/approval_ledger.py \
  scripts/cross_session_reconciler.py \
  lib/concurrency_safety.py \
  docs/adrs/ADR-108-concurrent-agent-safety-layer.md \
  docs/adrs/ADR-111-core-consumer-concurrency-safety-boundary.md \
  docs/architecture/concurrent-agent-scenario-test-matrix.md \
  docs/architecture/concurrency-safety-core-consumer-contract.md \
  .cognitive-os/plans/architecture/concurrent-agent-safety-testbed-plan.md; do
  if [ -f "$PROJECT_DIR/$f" ]; then pass "exists: $f"; else fail "missing: $f"; fi
done

if bash -n "$PROJECT_DIR/scripts/edit-coop.sh" >/dev/null 2>&1; then pass "edit-coop syntax clean"; else fail "edit-coop syntax failed"; fi
if bash -n "$PROJECT_DIR/scripts/git-coop.sh" >/dev/null 2>&1; then pass "git-coop syntax clean"; else fail "git-coop syntax failed"; fi
if bash -n "$PROJECT_DIR/scripts/stash-leak-alarm.sh" >/dev/null 2>&1; then pass "stash-leak alarm syntax clean"; else fail "stash-leak alarm syntax failed"; fi
for py in \
  scripts/verify_plan_claims.py \
  scripts/resource_lease.py \
  scripts/agent_work_ledger.py \
  scripts/approval_ledger.py \
  scripts/cross_session_reconciler.py \
  lib/concurrency_safety.py; do
  if python3 -m py_compile "$PROJECT_DIR/$py" >/dev/null 2>&1; then pass "python compiles: $py"; else fail "python compile failed: $py"; fi
done

if [ -f "$PROJECT_DIR/tests/integration/test_concurrent_agent_same_file.py" ]; then pass "scenario test exists: same-file"; else warn "scenario test missing: same-file"; fi
if [ -f "$PROJECT_DIR/tests/behavior/test_plan_false_done_gate.py" ]; then pass "scenario test exists: false-done"; else warn "scenario test missing: false-done"; fi
if [ -f "$PROJECT_DIR/tests/behavior/test_stash_leak_alarm.py" ]; then pass "scenario test exists: stash-leak"; else warn "scenario test missing: stash-leak"; fi
if [ -f "$PROJECT_DIR/tests/unit/test_concurrency_safety_config.py" ]; then pass "unit test exists: consumer projection"; else warn "unit test missing: consumer projection"; fi
if [ -f "$PROJECT_DIR/tests/behavior/test_concurrency_safety_ledgers.py" ]; then pass "behavior test exists: ledgers and leases"; else warn "behavior test missing: ledgers and leases"; fi
if [ -f "$PROJECT_DIR/tests/chaos/test_cross_session_reconciler.py" ]; then pass "chaos test exists: cross-session reconciler"; else warn "chaos test missing: cross-session reconciler"; fi

if [ "$STRICT" = true ] && [ "$warnings" -gt 0 ]; then
  failures=$((failures+warnings))
fi

if [ "$failures" -gt 0 ]; then
  printf 'Result: FAIL (%s failure(s), %s warning(s))\n' "$failures" "$warnings"
  exit 1
fi
printf 'Result: PASS (%s warning(s))\n' "$warnings"
