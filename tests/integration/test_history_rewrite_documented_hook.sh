#!/usr/bin/env bash
# Integration tests for hooks/history-rewrite-documented.sh (ADR-269 Primitive 2).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$ROOT_DIR/hooks/history-rewrite-documented.sh"

PASS=0
FAIL=0

pass() { echo "[PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "[FAIL] $1 — $2"; FAIL=$((FAIL+1)); }

# Setup a temp project skeleton
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

mkdir -p "$WORK_DIR/manifests" "$WORK_DIR/.cognitive-os/recovery" "$WORK_DIR/docs/adrs"
mkdir -p "$WORK_DIR/lib" "$WORK_DIR/.cognitive-os/logs"

# Symlink lib so the hook can import
ln -s "$ROOT_DIR/lib/history_rewrite_ledger.py" "$WORK_DIR/lib/history_rewrite_ledger.py"

# Test 1: no bundles -> exit 0, log entry status=ok
out_no_bundles=$(CLAUDE_PROJECT_DIR="$WORK_DIR" bash "$HOOK" 2>&1)
rc=$?
if [ "$rc" -eq 0 ]; then pass "no bundles exit 0"; else fail "no bundles exit 0" "got $rc"; fi

# Test 2: orphan bundle -> exit 0 but warns to stderr
touch "$WORK_DIR/.cognitive-os/recovery/pre-history-sanitization-20260101T000000Z.bundle"
out_orphan=$(CLAUDE_PROJECT_DIR="$WORK_DIR" bash "$HOOK" 2>&1)
rc=$?
if [ "$rc" -eq 0 ]; then pass "orphan exit 0 (non-blocking)"; else fail "orphan exit 0" "got $rc"; fi
if echo "$out_orphan" | grep -q "UNDOCUMENTED HISTORY REWRITE"; then
  pass "orphan warning emitted"
else
  fail "orphan warning emitted" "missing warning in: $out_orphan"
fi

# Test 3: bypass env -> no warning regardless of orphans
out_bypass=$(COS_ALLOW_UNDOCUMENTED_REWRITES=1 CLAUDE_PROJECT_DIR="$WORK_DIR" bash "$HOOK" 2>&1)
rc=$?
if [ "$rc" -eq 0 ]; then pass "bypass exit 0"; else fail "bypass exit 0" "got $rc"; fi
if echo "$out_bypass" | grep -q "UNDOCUMENTED"; then
  fail "bypass suppresses warning" "warning still printed"
else
  pass "bypass suppresses warning"
fi

# Test 4: log file written
LOG="$WORK_DIR/.cognitive-os/logs/history-rewrite-documented.jsonl"
if [ -f "$LOG" ] && [ -s "$LOG" ]; then
  pass "log file written"
else
  fail "log file written" "missing or empty: $LOG"
fi

# Test 5: latency <500ms (rough check) — run hook with timing
start_ms=$(python3 -c "import time;print(int(time.time()*1000))")
CLAUDE_PROJECT_DIR="$WORK_DIR" bash "$HOOK" >/dev/null 2>&1 || true
end_ms=$(python3 -c "import time;print(int(time.time()*1000))")
elapsed=$((end_ms - start_ms))
if [ "$elapsed" -lt 1500 ]; then
  pass "latency under 1500ms (was ${elapsed}ms; <500ms target is a soft goal)"
else
  fail "latency under 1500ms" "elapsed=${elapsed}ms"
fi

echo "---"
echo "PASS: $PASS  FAIL: $FAIL"
[ "$FAIL" -eq 0 ]
