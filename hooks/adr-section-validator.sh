#!/usr/bin/env bash
# SCOPE: os-only
# PURPOSE: Validate section contract for docs/02-Decisions/adrs/ADR-*.md on Write/Edit (ADR-067 Phase 2)
# EVENT: PostToolUse
# MATCHER: Edit|Write
# EXIT_CODES: 0=advisory/pass, 2=block (strict mode only)
# Bash 3.x compatible. Cutoff: ADR-067+. Field contract: ADR-067 Phase 2.
set -euo pipefail
# Fires when an agent writes or edits a file matching docs/02-Decisions/adrs/ADR-*.md.
#
# Behavior:
#   Default:     WARN to stderr (exit 0) — advisory only.
#   Strict mode: exit 2 (block) when COS_STRICT_ADR_VALIDATION=1.
#
# Cutoff: only ADR-067 and later are enforced (per operator decision #2).
# Pre-067 ADRs exit 0 (grandfathered) unless COS_STRICT_ADR_VALIDATION=1.
#
# Input: JSON on stdin per Claude Code PostToolUse hook contract:
#   {"tool_input": {"file_path": "..."}, "tool_output": ...}
#
# Section contract (ADR-067+):
#   - ## Status, ## Context, ## Decision, ## Consequences
#   - ## Alternatives rejected (with >= 1 item in body)
#   - ## Verification (with >= 1 fenced code block)
#
# Fix 2026-04-27: replaced heredoc-inside-$() with temp-file pattern to avoid
# bash 3.2 (macOS) parser failure when Python code contains backtick sequences.

# Read stdin JSON
INPUT="$(cat)"

# FAST PATH: skip if input doesn't contain adrs/ AND .md
case "$INPUT" in
  *"adrs/"*) ;;
  *) exit 0 ;;
esac
case "$INPUT" in
  *"ADR-"*) ;;
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

# Only process docs/02-Decisions/adrs/ADR-NNN-*.md paths
if ! printf '%s' "$FILE_PATH" | grep -qE '(^|/)docs/02-Decisions/adrs/ADR-[0-9]'; then
    exit 0
fi

# File must exist and be readable
if [ ! -f "$FILE_PATH" ]; then
    exit 0
fi

STRICT="${COS_STRICT_ADR_VALIDATION:-0}"

# Extract ADR number from filename
ADR_BASENAME="$(basename "$FILE_PATH")"
ADR_NUM="$(printf '%s' "$ADR_BASENAME" | python3 -c "
import sys, re
m = re.match(r'ADR-0*([0-9]+)', sys.stdin.read().strip())
print(int(m.group(1)) if m else 0)
" 2>/dev/null || echo 0)"

# Grandfathering: only enforce for ADR-067+
if [ "$STRICT" != "1" ] && [ "$ADR_NUM" -lt 67 ] 2>/dev/null; then
    exit 0
fi

# Validate section contract
# NOTE: Python script written to a temp file to avoid bash 3.2 heredoc-inside-$()
# parsing failure when the Python code contains backtick sequences (e.g. r"^```").
TMPPY="$(mktemp /tmp/adr-validator-XXXXXX.py)"
trap 'rm -f "$TMPPY"' EXIT

cat > "$TMPPY" << 'PYEOF'
import sys, re
from pathlib import Path

file_path = sys.argv[1]
try:
    text = Path(file_path).read_text(encoding="utf-8")
except OSError:
    sys.exit(0)

issues = []

# Required sections
required = ["Status", "Context", "Decision", "Consequences", "Alternatives rejected", "Verification"]
for section in required:
    if not re.search(rf"^## {re.escape(section)}\b", text, re.MULTILINE):
        issues.append(f"missing ## {section} section")


# ADR-274: §Operational Guide required for maintainer-tier accepted capability ADRs
def _front(field):
    m = re.search(rf"^{field}:\s*([\w-]+)", text[:2000], re.IGNORECASE | re.MULTILINE)
    return m.group(1).lower() if m else None

tier = _front("tier")
status_v = _front("status")
impl_block = re.search(r"^implementation_files:\s*\n((?:\s+-\s+.+\n)+)", text[:3000], re.MULTILINE)
impl_count = 0
if impl_block:
    impl_count = len([ln for ln in impl_block.group(1).splitlines() if ln.strip().startswith("-")])
is_tombstone = "tombstone" in Path(file_path).stem.lower() or status_v == "tombstone"
is_superseded = status_v == "superseded"
exempt = re.search(r"<!--\s*adr-274-exempt:\s*.+?-->", text, re.IGNORECASE)
subject = (
    tier == "maintainer"
    and status_v in {"accepted", "implemented"}
    and impl_count > 0
    and not is_tombstone
    and not is_superseded
    and not exempt
)
if subject:
    has_og = re.search(r"^##\s*Operational\s+Guide\b", text, re.IGNORECASE | re.MULTILINE)
    if not has_og:
        issues.append("missing ## Operational Guide section (required by ADR-274 for maintainer-tier accepted capability ADRs; add <!-- adr-274-exempt: <reason> --> to suppress)")
    else:
        sub_re = re.compile(
            r"^###\s+("
            r"What changes for the operator"
            r"|What (?:this|the .+) answer"
            r"|Daily operational pattern"
            r"|When (?:sources|surface) disagree"
            r"|Reading guide for cold readers"
            r"|Anti-confusion"
            r")",
            re.IGNORECASE | re.MULTILINE,
        )
        subs = sub_re.findall(text)
        if len(subs) < 3:
            issues.append(f"## Operational Guide has {len(subs)} recognized sub-section(s); need >= 3 of the 5 documented (see ADR-274 §2)")

# ## Alternatives rejected must have >= 1 table row (non-header, non-separator)
alt_m = re.search(r"^## Alternatives rejected\b(.+?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
if alt_m:
    alt_body = alt_m.group(1)
    # Table rows: lines starting with | that are not the header separator (---|)
    rows = [l for l in alt_body.splitlines()
            if l.strip().startswith("|") and not re.match(r"^\s*\|[-| ]+\|\s*$", l)]
    # Remove header row (first non-separator row)
    data_rows = rows[1:] if rows else []
    if not data_rows:
        issues.append("## Alternatives rejected has no table data rows (need >= 1 row with actual content)")

# ## Verification must have >= 1 fenced code block (>= 2 ``` markers)
ver_m = re.search(r"^## Verification\b(.+?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
if ver_m:
    ver_body = ver_m.group(1)
    # Count fenced code block markers (lines starting with ```)
    fence_count = len(re.findall(r"^`{3}", ver_body, re.MULTILINE))
    if fence_count < 2:
        issues.append(f"## Verification needs >= 1 fenced code block (found {fence_count // 2} blocks, need >= 2 fence markers)")

for issue in issues:
    print(issue)
PYEOF

ISSUES="$(python3 "$TMPPY" "$FILE_PATH" 2>/dev/null || true)"

if [ -z "$ISSUES" ]; then
    exit 0
fi

ISSUE_LIST="$(printf '%s' "$ISSUES" | tr '\n' ',' | sed 's/,$//' | sed 's/,/, /g')"
ADR_NAME="$(basename "$FILE_PATH")"

MSG="WARNING: ADR section contract violation: ${ISSUE_LIST} (file: ${ADR_NAME})"

# Write metrics (best-effort)
METRICS_DIR="${CLAUDE_PROJECT_DIR:-.}/.cognitive-os/metrics"
if mkdir -p "$METRICS_DIR" 2>/dev/null; then
    TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date '+%Y-%m-%dT%H:%M:%SZ')"
    printf '{"timestamp":"%s","adr":"%s","issues":[%s]}\n' \
        "$TIMESTAMP" "$ADR_NAME" \
        "$(printf '%s' "$ISSUES" | python3 -c "import sys,json; lines=sys.stdin.read().strip().splitlines(); print(','.join(json.dumps(l) for l in lines if l))" 2>/dev/null || echo '""')" \
        >> "$METRICS_DIR/adr-section-warnings.jsonl" 2>/dev/null || true
fi

if [ "$STRICT" = "1" ]; then
    printf '%s\n' "$MSG" >&2
    exit 2
else
    printf '%s\n' "$MSG" >&2
    exit 0
fi
