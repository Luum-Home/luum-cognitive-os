#!/usr/bin/env bash
# SCOPE: os-only
# PURPOSE: Prove, before anyone touches the protected control plane, that promoting
#          wrong-instrument-interceptor.sh the documented way makes it REACHABLE
#          according to scripts/audit_hook_registration.py -- and prove the same
#          audit calls it an ORPHAN when only the yaml half of the promotion is done.
#          Two branches that disagree; a probe that answered the same either way
#          would be measuring nothing.
# Read-only against this repo: the promotion is applied to a throwaway copy of the
# eight reachability surfaces under $TMPDIR. hooks/** and .claude/** are never written.
# Exit: 0 = both branches behaved as designed, 1 = they did not, 2 = setup error.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="wrong-instrument-interceptor"
PY="$ROOT/.venv/bin/python3"; [ -x "$PY" ] || PY="$(command -v python3)"

W="$(mktemp -d "${TMPDIR:-/tmp}/wii-reach.XXXXXX")" || exit 2
trap 'rm -rf "$W"' EXIT

seed() {  # copy the surfaces audit_hook_registration.py actually reads
  local dst="$1" rel
  for rel in cognitive-os.yaml \
             scripts/_lib/settings-driver-claude-code.sh \
             .claude/settings.json \
             hooks/bash-hot-path-dispatcher.sh \
             .codex/hooks.json \
             .opencode/cos-hooks.json \
             .cognitive-os/cos-runner-hooks.json \
             tests/contracts/EXCLUDED_HOOKS.txt; do
    [ -e "$ROOT/$rel" ] || continue
    mkdir -p "$dst/$(dirname "$rel")"
    cp "$ROOT/$rel" "$dst/$rel"
  done
  for d in templates/security-profiles .ai/primitives/hooks; do
    [ -d "$ROOT/$d" ] || continue
    mkdir -p "$dst/$d"; cp "$ROOT/$d"/*.json "$dst/$d/" 2>/dev/null || true
  done
  mkdir -p "$dst/hooks"
}

declare_in_yaml() {  # append the harness.hooks entry, indented like its neighbours
  "$PY" - "$1/cognitive-os.yaml" "$NAME" <<'PYEOF'
import sys
from pathlib import Path
path, name = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
anchor = "    pending-truth-drift-detector:\n"
assert anchor in text, "anchor entry not found -- yaml layout changed"
entry = (
    f"    {name}:\n"
    f"      script: hooks/{name}.sh\n"
    f"      event: PostToolUse\n"
    f'      matcher: "Bash"\n'
    f"      scope: os-only\n\n"
)
path.write_text(text.replace(anchor, entry + anchor, 1), encoding="utf-8")
PYEOF
}

wire_in_driver() {  # both post_bash branches, exactly as the runbook instructs
  "$PY" - "$1/scripts/_lib/settings-driver-claude-code.sh" "$NAME" <<'PYEOF'
import sys
from pathlib import Path
path, name = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
anchor = '      "hooks/error-learning.sh"              "false" \
'
n = text.count(anchor)
assert n == 2, f"expected the anchor in both post_bash branches, found {n}"
text = text.replace(anchor, anchor + f'      "hooks/{name}.sh"    "false" \\\n')
path.write_text(text, encoding="utf-8")
PYEOF
}

verdict() {  # -> the audit's word for $NAME in the tree at $1
  "$PY" - "$1" "$NAME" <<'PYEOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
PYEOF
  "$PY" -c "
import sys
sys.path.insert(0, '$ROOT')
from cos_lib.hook_registration_audit import HookRegistrationAudit, CLAUDE_REACHABILITY_SURFACES
r = HookRegistrationAudit('$1').audit()
for bucket in ('orphans','registered','omission_declared','contradicted_omission','unreachable_but_observed'):
    for v in r[bucket]:
        if v.name == '$NAME':
            reach = [s for s in CLAUDE_REACHABILITY_SURFACES if v.surfaces.get(s)]
            print(f'{bucket}|{\",\".join(reach) or \"-\"}')
            raise SystemExit(0)
print('absent|-')
"
}

FAIL=0

# --- Branch A: yaml only. The half-promotion an agent reaches for first. -----
A="$W/a"; seed "$A"; declare_in_yaml "$A"
VA="$(verdict "$A")"
echo "A) declared in cognitive-os.yaml, not wired anywhere -> $VA"
case "$VA" in orphans\|*) ;; *) echo "   UNEXPECTED: half-promotion should read as an orphan"; FAIL=1 ;; esac

# --- Branch B: the documented promotion. -----------------------------------
B="$W/b"; seed "$B"; declare_in_yaml "$B"; wire_in_driver "$B"
cp "$ROOT/hooks/$NAME.sh" "$B/hooks/$NAME.sh" 2>/dev/null || \
  cp "$ROOT/docs/05-Methodology/runbooks/$NAME-staging/$NAME.sh" "$B/hooks/$NAME.sh"
VB="$(verdict "$B")"
echo "B) declared + wired in settings-driver-claude-code.sh  -> $VB"
case "$VB" in registered\|*driver-claude-code*) ;; *) echo "   UNEXPECTED: full promotion should read as registered"; FAIL=1 ;; esac

echo
if [ "$FAIL" -eq 0 ]; then
  echo "OK: the two branches disagree, and each disagrees the way the design says it should."
  exit 0
fi
echo "FAIL: reachability proof did not behave as designed."
exit 1
