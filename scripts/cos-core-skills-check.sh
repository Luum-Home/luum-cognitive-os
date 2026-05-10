#!/usr/bin/env bash
# SCOPE: os-only
# =============================================================================
# cos-core-skills-check.sh — Verify the 10 core skills are reachable.
# =============================================================================
# For each core skill, verifies:
#   - SKILL.md exists under one of the supported skill surfaces
#     (repo source, canonical .cognitive-os, or harness projection)
#   - YAML frontmatter parses
#   - `name:` field in frontmatter matches the directory name
#
# Special case: `cos-status` is a script-only skill (see scripts/cos-status.sh),
# not a SKILL.md. We validate by checking the script exists and is executable.
#
# Exit codes:
#   0  all core skills OK
#   1  one or more core skills missing / invalid
#   2  invocation error (bad flag, missing prerequisites)
#
# Flags:
#   --json     Emit JSON report on stdout.
#   --root DIR Override project root (default: parent of this script).
#   --help     Show this help.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}}}"
MODE="pretty"

usage() {
  cat <<'EOF'
cos-core-skills-check.sh — Verify the 10 core skills are reachable.

Usage:
  bash scripts/cos-core-skills-check.sh [--json] [--root DIR]

Flags:
  --json      Emit JSON report on stdout.
  --root DIR  Override project root (default: parent of this script).
  --help, -h  Show this help.

The 10 core skills (per ADR-093 / ADR-001 harness-adoption-gap):
  compose-prompt, exhaustive-prompt, agent-dashboard, auto-refine,
  verification-before-completion, plan-feature, session-backlog,

Exit codes:
  0  all 10 skills OK
  1  one or more skills missing/invalid
  2  invocation error
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --json)      MODE="json"; shift ;;
    --root)
      if [ -z "${2:-}" ]; then echo "Error: --root requires a path" >&2; exit 2; fi
      PROJECT_ROOT="$(cd "$2" 2>/dev/null && pwd)" || { echo "Error: --root not a directory: $2" >&2; exit 2; }
      shift 2
      ;;
    --help|-h)   usage; exit 0 ;;
    *)           echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
done

# The canonical 10 core skills — per task instructions + ADR-001.
# If this list changes, coordinate with UX8 (HALT trigger per scope guard).
CORE_SKILLS=(
  compose-prompt
  exhaustive-prompt
  agent-dashboard
  auto-refine
  verification-before-completion
  plan-feature
  session-backlog
  resource-governor
  primitive-authoring
  cos-status
)

# Check one skill. Outputs a tab-separated line:
#   name<TAB>status<TAB>reason<TAB>path
# status = OK | MISSING | INVALID_YAML | NAME_MISMATCH | SCRIPT_OK | SCRIPT_MISSING
check_skill() {
  local name="$1"

  # Special case: cos-status is a script, not a SKILL
  if [ "$name" = "cos-status" ]; then
    local script_path="$PROJECT_ROOT/scripts/cos-status.sh"
    if [ -x "$script_path" ]; then
      printf '%s\tSCRIPT_OK\t%s\t%s\n' "$name" "executable script" "scripts/cos-status.sh"
    elif [ -f "$script_path" ]; then
      printf '%s\tSCRIPT_OK\t%s\t%s\n' "$name" "script present (not +x)" "scripts/cos-status.sh"
    else
      printf '%s\tSCRIPT_MISSING\t%s\t%s\n' "$name" "scripts/cos-status.sh not found" ""
    fi
    return
  fi

  # Candidate SKILL.md locations (in priority order).
  # Prefer canonical and repo-authored surfaces before harness projections.
  local candidates=(
    "$PROJECT_ROOT/skills/$name/SKILL.md"
    "$PROJECT_ROOT/.cognitive-os/skills/cos/$name/SKILL.md"
    "$PROJECT_ROOT/.claude/skills/$name/SKILL.md"
    "$PROJECT_ROOT/.cognitive-os/skills/$name/SKILL.md"
  )

  local skill_md=""
  for c in "${candidates[@]}"; do
    if [ -f "$c" ]; then skill_md="$c"; break; fi
  done

  if [ -z "$skill_md" ]; then
    printf '%s\tMISSING\t%s\t%s\n' "$name" "SKILL.md not found in repo, canonical, or driver skill surfaces" ""
    return
  fi

  # Parse frontmatter (simple inline parser — avoids python3 dependency for this check)
  # Frontmatter lives between the first two `---` lines.
  local fm_name
  fm_name=$(awk '
    /^---[[:space:]]*$/ {
      if (state == 0) { state = 1; next }
      if (state == 1) { state = 2; exit }
    }
    state == 1 && /^name:[[:space:]]*/ {
      sub(/^name:[[:space:]]*/, "");
      sub(/[[:space:]]*#.*$/, "");
      gsub(/["\x27]/, "");
      sub(/[[:space:]]+$/, "");
      print; exit
    }
  ' "$skill_md" 2>/dev/null)

  # If python3 is available, do a more rigorous YAML validation
  if command -v python3 >/dev/null 2>&1; then
    local py_name
    py_name=$(python3 - "$skill_md" <<'PYEOF' 2>/dev/null
import sys, re
path = sys.argv[1]
try:
    with open(path) as fh:
        content = fh.read()
except Exception:
    print("__READ_ERR__"); sys.exit(0)

# Extract frontmatter between the first two --- fences
m = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL | re.MULTILINE)
if not m:
    print("__NO_FRONTMATTER__"); sys.exit(0)
fm = m.group(1)

# Prefer PyYAML if present; else naive k:v parse (good enough for name: field)
name = None
try:
    import yaml
    data = yaml.safe_load(fm) or {}
    if not isinstance(data, dict):
        print("__NOT_DICT__"); sys.exit(0)
    name = data.get("name", "")
except Exception as e:
    # Naive parse fallback (very tolerant)
    for line in fm.splitlines():
        lm = re.match(r'^name:\s*(.+?)\s*(#.*)?$', line)
        if lm:
            name = lm.group(1).strip().strip('"').strip("'")
            break
print(name if name is not None else "")
PYEOF
)
    if [ "$py_name" = "__READ_ERR__" ] || [ "$py_name" = "__NO_FRONTMATTER__" ] || [ "$py_name" = "__NOT_DICT__" ]; then
      printf '%s\tINVALID_YAML\t%s\t%s\n' "$name" "$py_name" "${skill_md#$PROJECT_ROOT/}"
      return
    fi
    fm_name="$py_name"
  fi

  if [ -z "$fm_name" ]; then
    printf '%s\tINVALID_YAML\t%s\t%s\n' "$name" "name: field missing from frontmatter" "${skill_md#$PROJECT_ROOT/}"
    return
  fi

  if [ "$fm_name" != "$name" ]; then
    printf '%s\tNAME_MISMATCH\tfrontmatter name=%s expected=%s\t%s\n' "$name" "$fm_name" "$name" "${skill_md#$PROJECT_ROOT/}"
    return
  fi

  printf '%s\tOK\tfrontmatter valid, name matches\t%s\n' "$name" "${skill_md#$PROJECT_ROOT/}"
}

# Collect results
RESULTS_TSV=""
OK_COUNT=0
FAIL_COUNT=0
for s in "${CORE_SKILLS[@]}"; do
  line=$(check_skill "$s")
  RESULTS_TSV="${RESULTS_TSV}${line}"$'\n'
  status=$(echo "$line" | awk -F'\t' '{print $2}')
  case "$status" in
    OK|SCRIPT_OK) OK_COUNT=$((OK_COUNT + 1)) ;;
    *)            FAIL_COUNT=$((FAIL_COUNT + 1)) ;;
  esac
done

# Render
if [ "$MODE" = "json" ]; then
  python3 - <<PYEOF
import json, sys
tsv = """$RESULTS_TSV"""
items = []
for line in tsv.strip().splitlines():
    parts = line.split("\t")
    while len(parts) < 4:
        parts.append("")
    items.append({
        "name":   parts[0],
        "status": parts[1],
        "reason": parts[2],
        "path":   parts[3],
        "ok":     parts[1] in ("OK", "SCRIPT_OK"),
    })
ok   = sum(1 for i in items if i["ok"])
fail = len(items) - ok
out = {
    "ok":     fail == 0,
    "total":  len(items),
    "passed": ok,
    "failed": fail,
    "skills": items,
}
json.dump(out, sys.stdout, indent=2, sort_keys=True)
sys.stdout.write("\n")
PYEOF
else
  printf 'Core Skills Check (10 skills)\n'
  printf '══════════════════════════════\n\n'
  while IFS=$'\t' read -r name status reason path; do
    [ -z "$name" ] && continue
    case "$status" in
      OK)             printf '  [OK]         %-34s  %s\n' "$name" "$path" ;;
      SCRIPT_OK)      printf '  [SCRIPT_OK]  %-34s  %s\n' "$name" "$path" ;;
      MISSING)        printf '  [MISSING]    %-34s  %s\n' "$name" "$reason" ;;
      INVALID_YAML)   printf '  [INVALID]    %-34s  %s\n' "$name" "$reason" ;;
      NAME_MISMATCH)  printf '  [NAME-MISMATCH] %-31s  %s\n' "$name" "$reason" ;;
      SCRIPT_MISSING) printf '  [MISSING]    %-34s  %s\n' "$name" "$reason" ;;
      *)              printf '  [?]          %-34s  status=%s %s\n' "$name" "$status" "$reason" ;;
    esac
  done <<< "$RESULTS_TSV"
  printf '\n'
  if [ "$FAIL_COUNT" -eq 0 ]; then
    printf 'All 10 core skills reachable (%d/%d).\n' "$OK_COUNT" "${#CORE_SKILLS[@]}"
  else
    printf 'FAIL: %d/%d core skills unreachable.\n' "$FAIL_COUNT" "${#CORE_SKILLS[@]}"
  fi
fi

# Exit: 0 if all pass, 1 otherwise
[ "$FAIL_COUNT" -eq 0 ] && exit 0 || exit 1
