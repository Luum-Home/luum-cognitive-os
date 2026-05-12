#!/usr/bin/env bash
# Integration tests for scripts/cos-history-rewrite-audit (ADR-269 Primitive 3).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLI="$ROOT_DIR/scripts/cos-history-rewrite-audit"

PASS=0
FAIL=0
pass() { echo "[PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "[FAIL] $1 — $2"; FAIL=$((FAIL+1)); }

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

mkdir -p "$WORK_DIR/manifests" "$WORK_DIR/.cognitive-os/recovery" "$WORK_DIR/docs/02-Decisions/adrs" "$WORK_DIR/lib" "$WORK_DIR/scripts"
ln -s "$ROOT_DIR/lib/history_rewrite_ledger.py" "$WORK_DIR/lib/history_rewrite_ledger.py"
ln -s "$ROOT_DIR/scripts/cos-history-rewrite-audit" "$WORK_DIR/scripts/cos-history-rewrite-audit"

# Seed accepted ADR
cat > "$WORK_DIR/docs/02-Decisions/adrs/ADR-777-test.md" <<'EOF'
---
adr: 777
title: Test ADR
status: accepted
---
# ADR-777
EOF

# Test 1: empty list
out=$("$CLI" --project-dir "$WORK_DIR" --list 2>&1)
if echo "$out" | grep -q "no ledger entries"; then
  pass "empty list shows placeholder"
else
  fail "empty list shows placeholder" "$out"
fi

# Test 2: orphans on empty -> exit 0
"$CLI" --project-dir "$WORK_DIR" --orphans >/dev/null 2>&1
if [ "$?" -eq 0 ]; then pass "orphans empty exit 0"; else fail "orphans empty exit 0" "non-zero"; fi

# Test 3: orphan bundle -> exit 1
touch "$WORK_DIR/.cognitive-os/recovery/pre-history-sanitization-20260101T000000Z.bundle"
out=$("$CLI" --project-dir "$WORK_DIR" --orphans 2>&1)
rc=$?
if [ "$rc" -eq 1 ]; then pass "orphan bundle exit 1"; else fail "orphan bundle exit 1" "got rc=$rc"; fi
if echo "$out" | grep -q "Orphan bundles"; then
  pass "orphan output mentions orphan bundles"
else
  fail "orphan output" "$out"
fi

# Test 4: register the bundle
bundle="$WORK_DIR/.cognitive-os/recovery/pre-history-sanitization-20260101T000000Z.bundle"
out=$("$CLI" --project-dir "$WORK_DIR" --register "$bundle" --adr ADR-777 --reason "test" --json 2>&1)
rc=$?
if [ "$rc" -eq 0 ]; then pass "register exit 0"; else fail "register exit 0" "rc=$rc out=$out"; fi
if echo "$out" | grep -q '"status": "ok"'; then
  pass "register reports ok"
else
  fail "register reports ok" "$out"
fi

# Test 5: orphans now empty -> exit 0
"$CLI" --project-dir "$WORK_DIR" --orphans >/dev/null 2>&1
if [ "$?" -eq 0 ]; then pass "after register orphans empty"; else fail "after register orphans empty" "non-zero"; fi

# Test 6: list shows entry
out=$("$CLI" --project-dir "$WORK_DIR" --list 2>&1)
if echo "$out" | grep -q "ADR-777"; then
  pass "list shows registered entry"
else
  fail "list shows registered entry" "$out"
fi

# Test 7: re-register same bundle fails
out=$("$CLI" --project-dir "$WORK_DIR" --register "$bundle" --adr ADR-777 --reason "test" 2>&1)
rc=$?
if [ "$rc" -ne 0 ]; then pass "duplicate register rejected"; else fail "duplicate register rejected" "got rc=0"; fi

# Test 8: register with non-accepted ADR fails
cat > "$WORK_DIR/docs/02-Decisions/adrs/ADR-778-proposed.md" <<'EOF'
---
adr: 778
title: Proposed
status: proposed
---
EOF
touch "$WORK_DIR/.cognitive-os/recovery/pre-history-sanitization-20260202T000000Z.bundle"
out=$("$CLI" --project-dir "$WORK_DIR" --register "$WORK_DIR/.cognitive-os/recovery/pre-history-sanitization-20260202T000000Z.bundle" --adr ADR-778 --reason "x" 2>&1)
rc=$?
if [ "$rc" -ne 0 ]; then pass "proposed ADR rejected"; else fail "proposed ADR rejected" "got rc=0"; fi

# Test 9: --list --json well-formed
out=$("$CLI" --project-dir "$WORK_DIR" --list --json 2>&1)
echo "$out" | python3 -c "import json,sys; json.loads(sys.stdin.read())" 2>/dev/null
if [ "$?" -eq 0 ]; then pass "--list --json parseable"; else fail "--list --json parseable" "$out"; fi

echo "---"
echo "PASS: $PASS  FAIL: $FAIL"
[ "$FAIL" -eq 0 ]
