#!/usr/bin/env bash
# tests/integration/test_spdx_header_required.sh
# Integration tests for hooks/spdx-header-required.sh (ADR-267 Hook #4)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$ROOT_DIR/hooks/spdx-header-required.sh"

PASS=0; FAIL=0
assert_exit() {
  local n="$1" exp="$2" act="$3"
  if [ "$act" -eq "$exp" ]; then echo "[PASS] $n"; PASS=$((PASS+1)); else echo "[FAIL] $n — expected $exp got $act"; FAIL=$((FAIL+1)); fi
}

TMPBASE=$(mktemp -d /tmp/test-spdx-XXXXXX)
trap 'rm -rf "$TMPBASE"' EXIT

setup_repo() {
  local name="$1"
  REPO="$TMPBASE/$name"
  mkdir -p "$REPO/hooks" "$REPO/manifests" "$REPO/lib" "$REPO/scripts" "$REPO/.cognitive-os/logs"
  cp "$HOOK" "$REPO/hooks/spdx-header-required.sh"
  chmod +x "$REPO/hooks/spdx-header-required.sh"
  ( cd "$REPO" && git init -q && git config user.email t@t && git config user.name T )
}

PAYLOAD_COMMIT='{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}'
PAYLOAD_NOOP='{"tool_name":"Bash","tool_input":{"command":"ls"}}'

# TC1: non-commit -> exit 0
actual=$(bash "$HOOK" <<<"$PAYLOAD_NOOP"; echo $?)
assert_exit "TC1: non-commit exits 0" 0 "$actual"

# TC2: new file WITH SPDX -> exit 0
setup_repo r2
echo "# SPDX-License-Identifier: Apache-2.0" > "$REPO/lib/clean.py"
echo "x = 1" >> "$REPO/lib/clean.py"
( cd "$REPO" && git add lib/clean.py )
actual=$( cd "$REPO" && bash hooks/spdx-header-required.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $? )
exit_code=$(echo "$actual" | tail -1)
assert_exit "TC2: new file WITH SPDX exits 0" 0 "$exit_code"

# TC3: new file WITHOUT SPDX -> exit 1
setup_repo r3
echo "x = 1" > "$REPO/lib/dirty.py"
( cd "$REPO" && git add lib/dirty.py )
actual=$( cd "$REPO" && bash hooks/spdx-header-required.sh <<<"$PAYLOAD_COMMIT" 2>&1; echo $? )
exit_code=$(echo "$actual" | tail -1)
assert_exit "TC3: new file WITHOUT SPDX exits 1" 1 "$exit_code"

# TC4: modified existing file (grandfathered) WITHOUT SPDX -> exit 0
setup_repo r4
mkdir -p "$REPO/manifests"
echo "lib/legacy.py" > "$REPO/manifests/spdx-grandfather.txt"
echo "x = 1" > "$REPO/lib/legacy.py"
( cd "$REPO" && git add lib/legacy.py )
actual=$( cd "$REPO" && bash hooks/spdx-header-required.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $? )
exit_code=$(echo "$actual" | tail -1)
assert_exit "TC4: grandfathered file WITHOUT SPDX exits 0" 0 "$exit_code"

# TC5: bypass env -> exit 0 even if missing
setup_repo r5
echo "x=1" > "$REPO/lib/raw.py"
( cd "$REPO" && git add lib/raw.py )
actual=$( cd "$REPO" && COS_ALLOW_MISSING_SPDX=1 bash hooks/spdx-header-required.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $? )
exit_code=$(echo "$actual" | tail -1)
assert_exit "TC5: COS_ALLOW_MISSING_SPDX=1 bypass exits 0" 0 "$exit_code"

TOTAL=$((PASS+FAIL))
echo ""
echo "[test_spdx_header_required] $PASS passed / $TOTAL total"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
