#!/usr/bin/env bash
# SCOPE: os-only
# skill-frontmatter-validator.sh — PostToolUse hook (Edit|Write)
#
# Fires when an agent writes or edits a file matching skills/*/SKILL.md.
# Validates the frontmatter field contract defined in ADR-067 §4.
#
# Behavior:
#   Default:     WARN to stderr (exit 0) — advisory only.
#   Strict mode: exit 2 (block) when COS_STRICT_SKILL_VALIDATION=1.
#
# Input: JSON on stdin per Claude Code PostToolUse hook contract:
#   {"tool_input": {"file_path": "..."}, "tool_output": ...}
#
# Field contract (ADR-067 §4):
#   - name:         non-empty
#   - description:  non-empty, not bare ">" or "|", length >= 30 chars
#   - audience:     one of {os, os-dev, os-only, project, both, adopters, human}
#   - version:      semver-ish (X.Y.Z or X.Y)
#   - last-updated: YYYY-MM-DD
#   - <!-- SCOPE: ... --> HTML comment at line 1, value in {os-only, project, both}
#
# Bash 3.x compatible.

set -euo pipefail

# Read stdin JSON
INPUT="$(cat)"

# FAST PATH: skip Python startup entirely if input doesn't contain SKILL.md.
# Most PostToolUse Edit|Write fires are NOT against SKILL.md — this saves
# ~70ms per non-skill invocation by avoiding python3 startup.
case "$INPUT" in
  *"SKILL.md"*) ;;
  *) exit 0 ;;
esac

# Possible match — parse JSON to extract exact file_path
FILE_PATH="$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    # Support both direct tool_input and nested structures
    ti = d.get('tool_input', d)
    print(ti.get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null || true)"

# Only process skills/*/SKILL.md paths
if ! printf '%s' "$FILE_PATH" | grep -qE 'skills/[^/]+/SKILL\.md$'; then
    exit 0
fi

# File must exist and be readable
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

# Validate using the real _fm() parser from lib/session_hygiene.py
ISSUES="$(python3 - "$FILE_PATH" <<'PYEOF'
import sys, re
from pathlib import Path

# Inline the _fm logic (mirrors lib/session_hygiene._fm exactly)
def _fm(text, key):
    m = re.search(r"^---\s*\n(.*?)\n^---", text, re.DOTALL | re.MULTILINE)
    if not m:
        return None
    block = m.group(1)
    km = re.search(rf"^{re.escape(key)}\s*:\s*(.*)$", block, re.MULTILINE)
    if not km:
        return None
    inline = km.group(1).strip()
    if inline and inline not in (">", "|", ">-", "|-", ">+", "|+"):
        return inline.strip('"').strip("'")
    key_line_end = km.end()
    remainder = block[key_line_end:]
    continuation_lines = []
    for line in remainder.splitlines():
        if line == "" or line[0] in (" ", "\t"):
            continuation_lines.append(line.strip())
        else:
            break
    joined = " ".join(l for l in continuation_lines if l)
    return joined if joined else None

file_path = sys.argv[1]
try:
    text = Path(file_path).read_text(encoding="utf-8")
except OSError as e:
    sys.exit(0)  # Can't read — don't block

issues = []

# --- description ---
desc = _fm(text, "description")
if not desc:
    issues.append("description missing")
elif desc.strip() in (">", "|", ""):
    issues.append("description is empty block scalar (description: > with no content)")
elif len(desc.strip()) < 30:
    issues.append(f"description too short ({len(desc.strip())} chars, minimum 30)")

# --- audience ---
valid_audiences = {"os", "os-dev", "os-only", "project", "both", "adopters", "human"}
aud = _fm(text, "audience")
if not aud:
    issues.append("audience missing")
elif aud.strip() not in valid_audiences:
    issues.append(f"audience '{aud.strip()}' not in {sorted(valid_audiences)}")

# --- version ---
ver = _fm(text, "version")
if not ver:
    issues.append("version missing")
elif not re.match(r"^\d+\.\d+(\.\d+)?$", ver.strip()):
    issues.append(f"version '{ver.strip()}' not semver-ish (expected X.Y or X.Y.Z)")

# --- last-updated ---
lu = _fm(text, "last-updated")
if not lu:
    issues.append("last-updated missing")
elif not re.match(r"^\d{4}-\d{2}-\d{2}$", lu.strip()):
    issues.append(f"last-updated '{lu.strip()}' not YYYY-MM-DD")

# --- SCOPE HTML comment at line 1 ---
valid_scopes = {"os-only", "project", "both"}
lines = text.splitlines()
first = lines[0] if lines else ""
scope_m = re.match(r"^\s*<!--\s*SCOPE:\s*([a-z-]+)\s*-->\s*$", first)
if not scope_m:
    issues.append(f"line 1 must be <!-- SCOPE: os-only|project|both --> (got: {first[:60]!r})")
elif scope_m.group(1) not in valid_scopes:
    issues.append(f"<!-- SCOPE: {scope_m.group(1)} --> value not in {sorted(valid_scopes)}")

for issue in issues:
    print(issue)
PYEOF
)"

if [ -z "$ISSUES" ]; then
    exit 0
fi

ISSUE_LIST="$(printf '%s' "$ISSUES" | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')"
SKILL_NAME="$(basename "$(dirname "$FILE_PATH")")"

MSG="WARNING: SKILL.md frontmatter incomplete: ${ISSUE_LIST} (skill: ${SKILL_NAME})"

# Write metrics (best-effort, no failure if dir missing)
METRICS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/metrics"
if mkdir -p "$METRICS_DIR" 2>/dev/null; then
    TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
    printf '{"timestamp":"%s","skill":"%s","issues":[%s]}\n' \
        "$TIMESTAMP" "$SKILL_NAME" \
        "$(printf '%s' "$ISSUES" | python3 -c "import sys,json; lines=sys.stdin.read().strip().splitlines(); print(','.join(json.dumps(l) for l in lines))" 2>/dev/null || echo '""')" \
        >> "$METRICS_DIR/skill-frontmatter-warnings.jsonl" 2>/dev/null || true
fi

if [ "${COS_STRICT_SKILL_VALIDATION:-0}" = "1" ]; then
    # Strict mode: block (exit 2)
    printf '%s\n' "$MSG" >&2
    exit 2
else
    # Default: advisory (exit 0)
    printf '%s\n' "$MSG" >&2
    exit 0
fi
