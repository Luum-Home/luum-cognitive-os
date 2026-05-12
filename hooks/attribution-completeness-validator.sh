#!/usr/bin/env bash
# SCOPE: os-only
# attribution-completeness-validator.sh — ADR-267 Hook #5.
#
# Pre-commit gate. For staged files matching docs/03-PoCs/research/*-annex-*.md:
#   1. The first 30 lines (or YAML frontmatter) MUST mention:
#        Source-Pattern:, License:, Clean-Room-Protocol:
#      (any markdown-recognizable form — frontmatter, list, comment).
#   2. Every fenced code block with a language tag (```py, ```python, ```ts,
#      ```typescript, ```js, ```javascript, ```sh, ```bash, ```go, ```rust)
#      MUST be preceded (within the prior 3 lines) by — or contain in its
#      first line — a source attribution token: `from <path>`, `Source:`,
#      `**Source**`, `# from`, `// from`.
#
# Event:    PreToolUse
# Matcher:  Bash
# Trigger:  command contains `git commit`
# Exit:     0 = allow / 1 = block
# Bypass:   COS_ALLOW_INCOMPLETE_ATTRIBUTION=1 (logged)
# Log:      .cognitive-os/logs/attribution-completeness.jsonl
#
# Latency: typical <80ms per annex file, scaling linearly. Cap: scan only
# staged annex files; one Python pass per file.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/attribution-completeness.jsonl"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_log() { mkdir -p "$LOG_DIR"; printf '%s\n' "$1" >> "$LOG_FILE"; }

INPUT="$(cat 2>/dev/null || true)"
CMD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except: pass' 2>/dev/null || true)"

[[ "$CMD" != *"git commit"* ]] && exit 0

if [ "${COS_ALLOW_INCOMPLETE_ATTRIBUTION:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_INCOMPLETE_ATTRIBUTION=1\"}"
  exit 0
fi

STAGED="$(git -C "$ROOT_DIR" diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)"
[ -z "$STAGED" ] && exit 0

ANNEX=()
while IFS= read -r f; do
  case "$f" in
    docs/03-PoCs/research/*-annex-*.md) ANNEX+=("$f") ;;
  esac
done <<< "$STAGED"

[ ${#ANNEX[@]} -eq 0 ] && exit 0

# Run Python validator on each annex file; collect findings
FINDINGS=""
for f in "${ANNEX[@]}"; do
  abs="$ROOT_DIR/$f"
  [ -f "$abs" ] || continue
  result="$(python3 - "$abs" "$f" <<'PYEOF'
import re, sys
abs_path, rel_path = sys.argv[1], sys.argv[2]
try:
    text = open(abs_path, encoding="utf-8", errors="replace").read()
except Exception as e:
    print(f"{rel_path}: read error: {e}")
    sys.exit(0)

lines = text.splitlines()
header_blob = "\n".join(lines[:30])

required = ("Source-Pattern:", "License:", "Clean-Room-Protocol:")
missing = [k for k in required if k not in header_blob]
problems = []
if missing:
    problems.append(f"missing header fields: {', '.join(missing)}")

# Walk code fences with language tags
attr_re = re.compile(r"(from\s+\S+|Source:|\*\*Source\*\*|# from|// from)", re.IGNORECASE)
lang_re = re.compile(r"^```(py|python|ts|typescript|js|javascript|sh|bash|go|rust)\b", re.IGNORECASE)
in_block = False
block_start = None
block_lang = None
for i, line in enumerate(lines):
    if not in_block:
        m = lang_re.match(line.strip())
        if m:
            in_block = True
            block_start = i
            block_lang = m.group(1)
            # check 3 lines above OR first content line of block
            preceding = "\n".join(lines[max(0, i-3):i])
            inner = lines[i+1] if i+1 < len(lines) else ""
            if not attr_re.search(preceding) and not attr_re.search(inner):
                problems.append(f"line {i+1}: fence-tag {block_lang} block missing source attribution")
    else:
        if line.strip().startswith("```"):
            in_block = False

if problems:
    for p in problems:
        print(f"{rel_path}: {p}")
PYEOF
)"
  if [ -n "$result" ]; then
    FINDINGS="${FINDINGS}${result}"$'\n'
  fi
done

if [ -z "$FINDINGS" ]; then
  _log "{\"timestamp\":\"$TS\",\"action\":\"pass\",\"files\":${#ANNEX[@]}}"
  exit 0
fi

payload=$(printf '%s' "$FINDINGS" | python3 -c 'import json,sys; print(json.dumps([l.rstrip() for l in sys.stdin.read().splitlines() if l.strip()]))')
_log "{\"timestamp\":\"$TS\",\"action\":\"block\",\"findings\":$payload}"

echo "=== ATTRIBUTION-COMPLETENESS-VALIDATOR: BLOCKED ===" >&2
echo "Annex-F files must declare clean-room attribution and per-block sources." >&2
printf '%s' "$FINDINGS" | while IFS= read -r line; do
  [ -z "$line" ] && continue
  echo "  - $line" >&2
done
echo "" >&2
echo "Required header fields (first 30 lines): Source-Pattern, License, Clean-Room-Protocol." >&2
echo "Code fences need '# from <path>' / '// from <path>' / 'Source:' / '**Source**' line." >&2
echo "Bypass (logged): COS_ALLOW_INCOMPLETE_ATTRIBUTION=1 git commit ..." >&2
echo "Reference: docs/02-Decisions/adrs/ADR-267-license-compliance-enforcement-architecture.md" >&2
exit 1
