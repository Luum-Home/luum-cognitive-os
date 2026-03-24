#!/usr/bin/env bash
# Layer 1: Hook Infrastructure Tests
# Verifies hooks exist, are executable, have valid syntax, and match settings.json registrations.
set -uo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../../.." && pwd)}"
AOS="$PROJECT_DIR/.cognitive-os"
HOOKS_DIR="$AOS/hooks"
SETTINGS="$PROJECT_DIR/.claude/settings.local.json"

PASS=0
FAIL=0
WARN=0
DETAILS=""

pass() { PASS=$((PASS + 1)); DETAILS="${DETAILS}  PASS: $1\n"; }
fail() { FAIL=$((FAIL + 1)); DETAILS="${DETAILS}  FAIL: $1\n"; }
warn() { WARN=$((WARN + 1)); DETAILS="${DETAILS}  WARN: $1\n"; }

echo "=== HOOK INFRASTRUCTURE TESTS ==="
echo ""

# ---- Test 1: All hooks on disk exist and are executable ----
echo "--- Hooks on disk ---"
if [ ! -d "$HOOKS_DIR" ]; then
  fail "Hooks directory missing: $HOOKS_DIR"
else
  for hook in "$HOOKS_DIR"/*.sh; do
    [ ! -f "$hook" ] && continue
    name=$(basename "$hook")

    # Check executable
    if [ -x "$hook" ]; then
      pass "$name is executable"
    else
      fail "$name is NOT executable"
    fi

    # Check valid bash syntax
    if bash -n "$hook" 2>/dev/null; then
      pass "$name has valid bash syntax"
    else
      fail "$name has INVALID bash syntax"
    fi
  done
fi

# ---- Test 2: All hooks registered in settings.json exist on disk ----
echo ""
echo "--- Settings.json hook registrations ---"
if [ ! -f "$SETTINGS" ]; then
  warn "settings.local.json not found at $SETTINGS — skipping registration checks"
else
  # Extract all hook command paths from settings.json
  REGISTERED_PATHS=$(python3 -c "
import json, re, sys
with open('$SETTINGS') as f:
    data = json.load(f)
hooks = data.get('hooks', {})
paths = set()
for event_type, entries in hooks.items():
    for entry in entries:
        if isinstance(entry, dict):
            for h in entry.get('hooks', []):
                if isinstance(h, dict):
                    cmd = h.get('command', '')
                    # Extract .sh path from command string
                    matches = re.findall(r'[\w\$\{\}/.-]+\.sh', cmd)
                    for m in matches:
                        # Resolve \$CLAUDE_PROJECT_DIR
                        m = m.replace('\$CLAUDE_PROJECT_DIR', '$PROJECT_DIR')
                        m = m.replace('\${CLAUDE_PROJECT_DIR}', '$PROJECT_DIR')
                        paths.add(m)
for p in sorted(paths):
    print(p)
" 2>/dev/null)

  while IFS= read -r path; do
    [ -z "$path" ] && continue
    # Resolve variables
    resolved=$(echo "$path" | sed "s|\\\$CLAUDE_PROJECT_DIR|$PROJECT_DIR|g" | sed "s|\\\${CLAUDE_PROJECT_DIR}|$PROJECT_DIR|g" | sed "s|\$PROJECT_DIR|$PROJECT_DIR|g")
    name=$(basename "$resolved")
    if [ -f "$resolved" ]; then
      pass "Registered hook exists: $name"
    else
      fail "PHANTOM hook (in settings.json, file missing): $name -> $resolved"
    fi
  done <<< "$REGISTERED_PATHS"
fi

# ---- Test 3: Detect orphan hooks (on disk but not in settings.json) ----
echo ""
echo "--- Orphan detection ---"
if [ -f "$SETTINGS" ]; then
  REGISTERED_NAMES=$(python3 -c "
import json, re
with open('$SETTINGS') as f:
    data = json.load(f)
hooks = data.get('hooks', {})
names = set()
for event_type, entries in hooks.items():
    for entry in entries:
        if isinstance(entry, dict):
            for h in entry.get('hooks', []):
                if isinstance(h, dict):
                    cmd = h.get('command', '')
                    matches = re.findall(r'[\w.-]+\.sh', cmd)
                    for m in matches:
                        names.add(m)
for n in sorted(names):
    print(n)
" 2>/dev/null)

  for hook in "$HOOKS_DIR"/*.sh; do
    [ ! -f "$hook" ] && continue
    name=$(basename "$hook")
    if echo "$REGISTERED_NAMES" | grep -qF "$name"; then
      pass "$name is registered"
    else
      warn "ORPHAN hook (on disk but not in settings.json): $name"
    fi
  done
else
  warn "Cannot detect orphans — settings.local.json missing"
fi

# ---- Summary ----
echo ""
echo "=== HOOKS SUMMARY ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  WARN: $WARN"
echo ""

[ "$FAIL" -gt 0 ] && exit 1
exit 0
