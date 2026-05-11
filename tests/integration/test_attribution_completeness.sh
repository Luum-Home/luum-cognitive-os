#!/usr/bin/env bash
# tests/integration/test_attribution_completeness.sh
# Integration tests for hooks/attribution-completeness-validator.sh (ADR-267 Hook #5)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="$ROOT_DIR/hooks/attribution-completeness-validator.sh"

PASS=0; FAIL=0
assert_exit() {
  local n="$1" exp="$2" act="$3"
  if [ "$act" -eq "$exp" ]; then echo "[PASS] $n"; PASS=$((PASS+1)); else echo "[FAIL] $n — expected $exp got $act"; FAIL=$((FAIL+1)); fi
}

TMPBASE=$(mktemp -d /tmp/test-attr-XXXXXX)
trap 'rm -rf "$TMPBASE"' EXIT

setup_repo() {
  local name="$1"
  REPO="$TMPBASE/$name"
  mkdir -p "$REPO/hooks" "$REPO/docs/research" "$REPO/.cognitive-os/logs"
  cp "$HOOK" "$REPO/hooks/attribution-completeness-validator.sh"
  chmod +x "$REPO/hooks/attribution-completeness-validator.sh"
  ( cd "$REPO" && git init -q && git config user.email t@t && git config user.name T )
}

PAYLOAD_COMMIT='{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}'
PAYLOAD_NOOP='{"tool_name":"Bash","tool_input":{"command":"ls"}}'

# TC1: non-commit -> exit 0
actual=$(bash "$HOOK" <<<"$PAYLOAD_NOOP"; echo $?)
assert_exit "TC1: non-commit exits 0" 0 "$actual"

# TC2: annex with full header + per-block attribution -> exit 0
setup_repo r2
cat > "$REPO/docs/research/foo-annex-f-bar.md" <<'MDEOF'
# Annex F

- Source-Pattern: foo-pattern
- License: Apache-2.0
- Clean-Room-Protocol: derived

## Code

# from upstream/foo.py:10-20
```python
def hello(): pass
```
MDEOF
( cd "$REPO" && git add docs/research/foo-annex-f-bar.md )
actual=$( cd "$REPO" && bash hooks/attribution-completeness-validator.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $? )
exit_code=$(echo "$actual" | tail -1)
assert_exit "TC2: complete annex exits 0" 0 "$exit_code"

# TC3: annex missing header fields -> exit 1
setup_repo r3
cat > "$REPO/docs/research/foo-annex-f-bar.md" <<'MDEOF'
# Annex F
just some text
MDEOF
( cd "$REPO" && git add docs/research/foo-annex-f-bar.md )
actual=$( cd "$REPO" && bash hooks/attribution-completeness-validator.sh <<<"$PAYLOAD_COMMIT" 2>&1; echo $? )
exit_code=$(echo "$actual" | tail -1)
assert_exit "TC3: missing header exits 1" 1 "$exit_code"

# TC4: annex with header but code block without attribution -> exit 1
setup_repo r4
cat > "$REPO/docs/research/foo-annex-f-bar.md" <<'MDEOF'
# Annex F

- Source-Pattern: x
- License: MIT
- Clean-Room-Protocol: derived

Some prose.

```python
def hello(): pass
```
MDEOF
( cd "$REPO" && git add docs/research/foo-annex-f-bar.md )
actual=$( cd "$REPO" && bash hooks/attribution-completeness-validator.sh <<<"$PAYLOAD_COMMIT" 2>&1; echo $? )
exit_code=$(echo "$actual" | tail -1)
assert_exit "TC4: code-block without attribution exits 1" 1 "$exit_code"

# TC5: bypass -> exit 0
setup_repo r5
cat > "$REPO/docs/research/foo-annex-f-bar.md" <<'MDEOF'
# bad annex
MDEOF
( cd "$REPO" && git add docs/research/foo-annex-f-bar.md )
actual=$( cd "$REPO" && COS_ALLOW_INCOMPLETE_ATTRIBUTION=1 bash hooks/attribution-completeness-validator.sh <<<"$PAYLOAD_COMMIT" 2>/dev/null; echo $? )
exit_code=$(echo "$actual" | tail -1)
assert_exit "TC5: bypass exits 0" 0 "$exit_code"

TOTAL=$((PASS+FAIL))
echo ""
echo "[test_attribution_completeness] $PASS passed / $TOTAL total"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
