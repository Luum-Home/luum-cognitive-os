#!/usr/bin/env bash
# SCOPE: os-only
# PURPOSE: Validate field contract for rules/*.md on Write/Edit (ADR-067 Phase 2)
# EVENT: PostToolUse
# MATCHER: Edit|Write
# EXIT_CODES: 0=advisory/pass, 2=block (strict mode only)
# Bash 3.x compatible. Field contract: ADR-067 Phase 2.
set -euo pipefail
# Fires when an agent writes or edits a file matching rules/*.md.
#
# Behavior:
#   Default:     WARN to stderr (exit 0) — advisory only.
#   Strict mode: exit 2 (block) when COS_STRICT_RULE_VALIDATION=1.
#
# Input: JSON on stdin per Claude Code PostToolUse hook contract:
#   {"tool_input": {"file_path": "..."}, "tool_output": ...}
#
# Field contract (ADR-067 Phase 2):
#   - <!-- SCOPE: ... --> HTML comment at line 1, value in {os-only, project, both}
#   - H1 title (# Title)
#   - One of: ## Purpose | ## Rule | ## Principle | ## Mandate (opening section)
#   - If body mentions "Contextual Trigger" or has <!-- STATUS: contextual -->:
#     require ## Contextual Trigger section

# Read stdin JSON
INPUT="$(cat)"

# FAST PATH: skip if input doesn't contain rules/ AND .md
case "$INPUT" in
  *"rules/"*) ;;
  *) exit 0 ;;
esac
case "$INPUT" in
  *".md"*) ;;
  *) exit 0 ;;
esac

# Parse file_path from JSON
FILE_PATH="$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d)
    print(ti.get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null || true)"

# Only process rules/*.md paths (direct children of rules/, not subdirs)
if ! printf '%s' "$FILE_PATH" | grep -qE '(^|/)rules/[^/]+\.md$'; then
    exit 0
fi

# Skip meta-files that are not rules
BASENAME="$(basename "$FILE_PATH")"
case "$BASENAME" in
  RULES-COMPACT.md|ROADMAP.md)
    exit 0
    ;;
esac

# File must exist and be readable
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

# Validate using Python for reliable multiline processing
ISSUES="$(python3 - "$FILE_PATH" <<'PYEOF'
import sys, re
from pathlib import Path

file_path = sys.argv[1]
try:
    text = Path(file_path).read_text(encoding="utf-8")
except OSError:
    sys.exit(0)

lines = text.splitlines()
issues = []

# --- SCOPE HTML comment at line 1 ---
valid_scopes = {"os-only", "project", "both"}
first = lines[0] if lines else ""
scope_m = re.match(r"^\s*<!--\s*SCOPE:\s*([a-z-]+)\s*-->\s*$", first)
if not scope_m:
    issues.append(f"line 1 must be <!-- SCOPE: os-only|project|both --> (got: {first[:60]!r})")
elif scope_m.group(1) not in valid_scopes:
    issues.append(f"<!-- SCOPE: {scope_m.group(1)} --> value not in {sorted(valid_scopes)}")

# --- H1 title ---
if not re.search(r"^# \S", text, re.MULTILINE):
    issues.append("missing H1 title (# Title)")

# --- Opening section: Purpose | Rule | Principle | Mandate ---
opening_sections = {"Purpose", "Rule", "Principle", "Mandate"}
found_opening = any(
    re.search(rf"^## {s}\b", text, re.MULTILINE)
    for s in opening_sections
)
if not found_opening:
    issues.append("missing opening section (## Purpose | ## Rule | ## Principle | ## Mandate)")

# --- Conditional: Contextual Trigger ---
needs_trigger = (
    "Contextual Trigger" in text or
    "<!-- STATUS: contextual -->" in text
)
if needs_trigger:
    if not re.search(r"^## Contextual Trigger\b", text, re.MULTILINE):
        issues.append("body mentions 'Contextual Trigger' but ## Contextual Trigger section is missing")

for issue in issues:
    print(issue)
PYEOF
)"

if [ -z "$ISSUES" ]; then
    exit 0
fi

ISSUE_LIST="$(printf '%s' "$ISSUES" | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')"
RULE_NAME="$(basename "$FILE_PATH")"

MSG="WARNING: rules/*.md contract violation: ${ISSUE_LIST} (rule: ${RULE_NAME})"

# Write metrics (best-effort)
METRICS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/metrics"
if mkdir -p "$METRICS_DIR" 2>/dev/null; then
    TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
    printf '{"timestamp":"%s","rule":"%s","issues":[%s]}\n' \
        "$TIMESTAMP" "$RULE_NAME" \
        "$(printf '%s' "$ISSUES" | python3 -c "import sys,json; lines=sys.stdin.read().strip().splitlines(); print(','.join(json.dumps(l) for l in lines if l))" 2>/dev/null || echo '""')" \
        >> "$METRICS_DIR/rule-frontmatter-warnings.jsonl" 2>/dev/null || true
fi

if [ "${COS_STRICT_RULE_VALIDATION:-0}" = "1" ]; then
    printf '%s\n' "$MSG" >&2
    exit 2
else
    printf '%s\n' "$MSG" >&2
    exit 0
fi
