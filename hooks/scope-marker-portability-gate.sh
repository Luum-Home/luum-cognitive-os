#!/usr/bin/env bash
# SCOPE: os-only
# scope-marker-portability-gate.sh — PreToolUse Bash hook for KD6 portability proof.
#
# Blocks `git commit` when a staged primitive lacks its paired portability proof,
# and when a newly added primitive declares no scope marker at all.
#
# Contract:
#   - Input: Claude/Codex PreToolUse JSON for Bash.
#   - Trigger: bash command containing `git commit`.
#   - Decision: exit 2 when a staged primitive-registry path either
#       (a) carries any SCOPE marker in its first three lines and has no paired
#           portability proof, or
#       (b) is newly added (diff-filter=A) and carries no SCOPE marker at all.
#   - Registry paths mirror cos_lib/primitive_file_inventory.SOURCE_ROOTS.
#   - Pairing mirrors cos_lib/portability_proof_paths.paired_candidates plus the
#     tests listed in manifests/primitive-behavior-evidence.yaml.
#   - Fail-open: a resolver error allows the commit and logs a warn metric.
#   - Bypass: COS_ALLOW_UNPROVEN_SCOPE_BOTH=1 (logs warning and allows).

set -uo pipefail

_HOOK_NAME="scope-marker-portability-gate"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=hooks/_lib/common.sh
source "$SCRIPT_DIR/_lib/common.sh"
# shellcheck source=hooks/_lib/git-command-parse.sh
source "$SCRIPT_DIR/_lib/git-command-parse.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}}"
METRICS_DIR="${COS_METRICS_DIR:-$PROJECT_DIR/.cognitive-os/metrics}"
METRICS_FILE="$METRICS_DIR/scope-marker-portability-gate.jsonl"

emit_metric() {
  local decision="$1" details="$2"
  mkdir -p "$METRICS_DIR" 2>/dev/null || true
  python3 - "$METRICS_FILE" "$decision" "$details" <<'PY' 2>/dev/null || true
import json, sys, time
path, decision, details = sys.argv[1:]
row = {
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "hook": "scope-marker-portability-gate",
    "decision": decision,
    "details": details,
}
with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row, sort_keys=True) + "\n")
PY
}

# Registry-shaped paths: mirrors cos_lib/primitive_file_inventory.SOURCE_ROOTS.
is_registry_path() {
  case "$1" in
    tests/red_team/portability/*) return 1 ;;
    hooks/*|rules/*|scripts/*|templates/*) return 0 ;;
    skills/*/SKILL.md|skills/*/*/SKILL.md) return 0 ;;
    packages/*/skills/*/SKILL.md) return 0 ;;
    *) return 1 ;;
  esac
}

# Resolve staged primitives that have no paired portability proof.
# The here-document lives in a function because bash 3.2 cannot parse a
# here-document nested inside a command substitution.
cos_resolve_unpaired() {
  python3 - "$PROJECT_DIR" "$@" <<'PY' 2>/dev/null
import os, sys

root = sys.argv[1]
rels = [arg for arg in sys.argv[2:] if arg]
sys.path.insert(0, root)

PD = "tests/red_team/portability"


def _fallback_candidates(rel):
    parts = rel.split("/")
    base = parts[-1]
    stem = base.rsplit(".", 1)[0]
    out = []
    if rel.startswith("skills/") and base == "SKILL.md" and len(parts) >= 3:
        slug = parts[-2].replace("-", "_")
        out.append(PD + "/test_skill_" + slug + ".py")
    if rel.startswith("packages/") and base == "SKILL.md" and len(parts) >= 5 and parts[2] == "skills":
        pkg = parts[1].replace("-", "_")
        skill = parts[3].replace("-", "_")
        out.append(PD + "/test_package_skill_" + pkg + "_" + skill + ".py")
        out.append(PD + "/test_package_skills.py")
    out.append(PD + "/" + stem + ".bats")
    out.append(PD + "/" + base + ".bats")
    out.append(PD + "/" + stem + "_test.py")
    out.append(PD + "/test_" + stem + ".py")
    return out


try:
    from cos_lib.portability_proof_paths import paired_candidates
except Exception:
    paired_candidates = _fallback_candidates

pending = []
for rel in rels:
    if not any(os.path.isfile(os.path.join(root, c)) for c in paired_candidates(rel)):
        pending.append(rel)

if pending:
    manifest_tests = {}
    manifest_path = os.path.join(root, "manifests", "primitive-behavior-evidence.yaml")
    if os.path.isfile(manifest_path):
        try:
            import yaml

            try:
                from yaml import CSafeLoader as _Loader
            except Exception:
                from yaml import SafeLoader as _Loader
            with open(manifest_path, encoding="utf-8") as fh:
                data = yaml.load(fh, Loader=_Loader) or {}
            for item in data.get("evidence", []) or []:
                if isinstance(item, dict) and item.get("primitive"):
                    manifest_tests[str(item["primitive"])] = item.get("tests") or []
        except Exception:
            # Manifest unreadable: fail open rather than block every primitive.
            print("RESOLVER_DEGRADED")
            raise SystemExit(0)
    still = []
    for rel in pending:
        tests = [
            t
            for t in manifest_tests.get(rel, [])
            if isinstance(t, str)
            and t.startswith(PD + "/")
            and os.path.isfile(os.path.join(root, t))
        ]
        if not tests:
            still.append(rel)
    pending = still

for rel in pending:
    print(rel)
PY
}

INPUT=""
if [ ! -t 0 ]; then
  INPUT="$(cat 2>/dev/null || true)"
fi
[ -n "$INPUT" ] || exit 0

if ! command -v python3 >/dev/null 2>&1; then
  emit_metric "warn_no_python" "python3 unavailable; cannot inspect Bash command"
  exit 0
fi

TOOL_NAME="$(printf '%s' "$INPUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read() or "{}"); print(d.get("tool_name", ""))' 2>/dev/null || true)"
[ "$TOOL_NAME" = "Bash" ] || exit 0

COMMAND="$(printf '%s' "$INPUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read() or "{}"); print((d.get("tool_input") or {}).get("command", ""))' 2>/dev/null || true)"
[ -n "$COMMAND" ] || exit 0

if ! cos_git_matches_subcommand "$COMMAND" 'commit'; then
  exit 0
fi

if [ "${COS_ALLOW_UNPROVEN_SCOPE_BOTH:-0}" = "1" ]; then
  emit_metric "bypass" "$COMMAND"
  exit 0
fi

if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  emit_metric "warn_not_git_repo" "$PROJECT_DIR"
  exit 0
fi

# Let amend-only metadata commits proceed when no path content is staged.
staged_files="$(git -C "$PROJECT_DIR" diff --cached --name-only --diff-filter=ACMRT 2>/dev/null || true)"
[ -n "$staged_files" ] || exit 0
added_files="$(git -C "$PROJECT_DIR" diff --cached --name-only --diff-filter=A 2>/dev/null || true)"

marked_paths=""
marked_list=()
undeclared_report=""
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  is_registry_path "$rel" || continue

  abs="$PROJECT_DIR/$rel"
  [ -f "$abs" ] || continue

  if head -3 "$abs" 2>/dev/null | grep -Eq '^[[:space:]]*(#|<!--|//)[[:space:]]*SCOPE:[[:space:]]*[A-Za-z]'; then
    marked_paths="$marked_paths$rel
"
    marked_list[${#marked_list[@]}]="$rel"
    continue
  fi

  # No scope marker at all: only newly added primitives are blocked, so the
  # policy applies forward without retro-blocking pre-existing artifacts.
  case "
$added_files
" in
    *"
$rel
"*)
      undeclared_report="$undeclared_report
- $rel is a new primitive with no SCOPE marker in its first three lines"
      ;;
  esac
done <<EOF_FILES
$staged_files
EOF_FILES

missing_report=""
resolver_status=0
if [ -n "$marked_paths" ]; then
  unpaired="$(cos_resolve_unpaired "${marked_list[@]}")"
  resolver_status=$?
  if [ "$resolver_status" -ne 0 ]; then
    emit_metric "warn_resolver_failed" "pairing resolver exited $resolver_status"
    unpaired=""
  fi
  case "$unpaired" in
    *RESOLVER_DEGRADED*)
      emit_metric "warn_resolver_degraded" "portability proof manifest unreadable"
      unpaired=""
      ;;
  esac
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    stem_base="$(basename "$rel")"
    stem="${stem_base%.*}"
    missing_report="$missing_report
- $rel declares a SCOPE marker but has no paired portability proof; expected one of: tests/red_team/portability/$stem.bats, tests/red_team/portability/$stem_base.bats, tests/red_team/portability/${stem}_test.py, tests/red_team/portability/test_${stem}.py, or an entry in manifests/primitive-behavior-evidence.yaml"
  done <<EOF_UNPAIRED
$unpaired
EOF_UNPAIRED
fi

if [ -n "$missing_report" ] || [ -n "$undeclared_report" ]; then
  decision="block_missing_portability_test"
  [ -n "$missing_report" ] || decision="block_undeclared_scope"
  emit_metric "$decision" "$missing_report$undeclared_report"
  cat >&2 <<EOF_BLOCK
[scope-marker-portability-gate] BLOCK: staged primitives fail the scope proof contract.$missing_report$undeclared_report

Every primitive must declare its scope in the first three lines (# SCOPE: os-only | both | project)
and back that claim with a portability proof carrying at least one falsification probe.
Bypass for an emergency only: COS_ALLOW_UNPROVEN_SCOPE_BOTH=1
EOF_BLOCK
  exit 2
fi

emit_metric "allow" "all staged primitives declare scope and have portability proofs"
exit 0
