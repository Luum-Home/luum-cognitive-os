#!/usr/bin/env bash
# SCOPE: os-only
# PURPOSE: Mutation proof for hooks/wrong-instrument-interceptor.sh. Breaks the hook
#          in six named ways and requires the test suite to go RED for each one. A
#          suite that stays green under mutation is decoration, not a gate.
# Read-only against the repo: every mutant is a copy under $TMPDIR, and the suite is
# pointed at it with COS_WII_HOOK_PATH. Nothing in hooks/ or tests/ is modified.
# Exit: 0 = every mutation was killed, 1 = a mutation survived, 2 = setup error.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

HOOK=""
for c in "$ROOT/hooks/wrong-instrument-interceptor.sh" \
         "$ROOT/docs/05-Methodology/runbooks/wrong-instrument-interceptor-staging/wrong-instrument-interceptor.sh"; do
  [ -f "$c" ] && { HOOK="$c"; break; }
done
[ -n "$HOOK" ] || { echo "verify-wrong-instrument-interceptor: hook not found" >&2; exit 2; }

TESTS="$ROOT/tests/hooks/test_wrong_instrument_interceptor.py"
[ -f "$TESTS" ] || { echo "verify-wrong-instrument-interceptor: tests not found" >&2; exit 2; }

PY="$ROOT/.venv/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/wii-mutants.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

run_suite() {  # $1 = hook path -> echoes "PASS"/"FAIL"
  if COS_WII_HOOK_PATH="$1" COS_ALLOW_OPERATOR_METRICS_WRITES=1 \
     "$PY" -m pytest "$TESTS" -q -p no:randomly >"$WORK/out.txt" 2>&1; then
    echo PASS
  else
    echo FAIL
  fi
}

# --- Baseline: unmutated hook must be GREEN. A suite that is already red proves
# --- nothing about the mutants below.
BASE="$(run_suite "$HOOK")"
echo "baseline (unmutated): $BASE"
if [ "$BASE" != "PASS" ]; then
  echo "verify-wrong-instrument-interceptor: BASELINE IS RED -- mutation results would be meaningless" >&2
  tail -25 "$WORK/out.txt" >&2
  exit 1
fi

SURVIVED=0
n=0
mutate() {  # $1 = name, $2 = sed program
  n=$((n + 1))
  local m="$WORK/mutant-$n.sh"
  sed "$2" "$HOOK" > "$m" || { echo "sed failed for $1" >&2; exit 2; }
  if cmp -s "$m" "$HOOK"; then
    echo "  [$n] $1 -> SETUP ERROR: mutation did not change the file"
    SURVIVED=$((SURVIVED + 1))
    return
  fi
  local r
  r="$(run_suite "$m")"
  if [ "$r" = "FAIL" ]; then
    local why
    why="$(grep -Eo '^(FAILED|E +assert).*' "$WORK/out.txt" | head -1)"
    echo "  [$n] $1 -> KILLED   ${why:-（suite red）}"
  else
    echo "  [$n] $1 -> SURVIVED  <-- the suite cannot see this bug"
    SURVIVED=$((SURVIVED + 1))
  fi
}

echo "mutations:"

# M1 -- drop the precision mechanism: accept any hyphenated token as a hook name.
mutate "M1 pattern-is-a-real-hook check removed" \
  's|^hits = \[n for n in seen if (hooks_dir / f"{n}.sh").is_file()\]$|hits = list(seen)|'

# M2 -- command-position requirement dropped: the letters "grep" anywhere count.
mutate "M2 grep matched anywhere, not at command position" \
  's|^if not TOOL_RE.search(command):$|if False:|'

# M3 -- surface requirement dropped: any haystack counts as a registration surface.
mutate "M3 registration-surface requirement removed" \
  's|^surfaces_named = SURFACE_RE.findall(command)$|surfaces_named = SURFACE_RE.findall(command) or [".claude/settings.json"]|'

# M4 -- the canonical gate-registration command is dropped from the message.
mutate "M4 audit_gate_registration.py dropped from the message" \
  's|^  \.venv/bin/python3 scripts/audit_gate_registration\.py$||'

# M5 -- verdict always negative: the hook answers "not reachable" for everything.
mutate "M5 verdict hardcoded to NOT reachable" \
  's|^    verdict = "REACHABLE" if reach else|    verdict = "REACHABLE" if False else|'

# M6 -- hook short-circuits: registered but inert, the failure mode the whole
#       exercise is about.
mutate "M6 hook exits before doing anything" \
  's|^INPUT="\$(cat 2>/dev/null \|\| true)"$|INPUT="$(cat 2>/dev/null \|\| true)"; exit 0|'

echo
if [ "$SURVIVED" -eq 0 ]; then
  echo "OK: $n/$n mutations killed."
  exit 0
fi
echo "FAIL: $SURVIVED of $n mutations survived."
exit 1
