#!/usr/bin/env bash
# SCOPE: os-only
# legal-review-required-on-runtime-import.sh — Pre-commit gate (ADR-270 primitive #8)
#
# Scans staged .py files in lib/, packages/*/lib/, scripts/ for attribution
# headers ("# Ported from <tool>" / "# Adapted from <tool>" / similar). If the
# tool's entry in manifests/legal-review-ledger.yaml is not approved, the
# commit is blocked.
#
# Event:    PreToolUse
# Matcher:  Bash
# Trigger:  command contains `git commit`
# Exit:     0 - clean or bypass | 1 - blocked
# Bypass:   COS_ALLOW_PRE_LEGAL_REVIEW_IMPORT=1 (logged)
# Log:      .cognitive-os/logs/legal-review-required.jsonl
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

LOG_DIR="$ROOT_DIR/.cognitive-os/logs"
LOG_FILE="$LOG_DIR/legal-review-required.jsonl"
LEDGER="$ROOT_DIR/manifests/legal-review-ledger.yaml"

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

_log() {
  mkdir -p "$LOG_DIR"
  printf '%s\n' "$1" >> "$LOG_FILE"
}

INPUT="$(cat 2>/dev/null || true)"
COMMAND="$(printf '%s' "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null || true)"

if [[ "$COMMAND" != *"git commit"* ]]; then
  exit 0
fi

if [ "${COS_ALLOW_PRE_LEGAL_REVIEW_IMPORT:-0}" = "1" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"bypass\",\"reason\":\"COS_ALLOW_PRE_LEGAL_REVIEW_IMPORT=1\"}"
  exit 0
fi

if [ ! -f "$LEDGER" ]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"skip\",\"reason\":\"ledger absent\"}"
  exit 0
fi

cd "$ROOT_DIR" || exit 0

STAGED_FILES="$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | \
  grep -E '^(lib/|scripts/|packages/[^/]+/lib/)' | grep -E '\.py$' || true)"

if [ -z "$STAGED_FILES" ]; then
  exit 0
fi

RESULT="$(STAGED_FILES_TSV="$STAGED_FILES" LEDGER_PATH="$LEDGER" python3 <<'PY'
import os, re, sys
from pathlib import Path
try:
    import yaml
except Exception:
    print("SKIP no-yaml"); sys.exit(0)

ROOT = Path(os.environ.get("PWD") or os.getcwd())
LEDGER = Path(os.environ["LEDGER_PATH"])

try:
    data = yaml.safe_load(LEDGER.read_text(encoding="utf-8")) or {}
except Exception as exc:
    print(f"SKIP ledger-unreadable {exc}"); sys.exit(0)

known = {}
for entry in data.get("entries", []) or []:
    tool = entry.get("tool", "")
    decision = str(entry.get("decision", "")).lower()
    if tool:
        known[tool.lower()] = decision

PATTERN = re.compile(
    r"^\s*#\s*(?:Ported|Adapted|Derived|Inspired by|Inspired from|Based on)\s+(?:from\s+)?[\"'`]?([A-Za-z0-9_\-]+)[\"'`]?",
    re.IGNORECASE,
)
LICENSE_PATTERN = re.compile(
    r"^\s*#\s*(?:SPDX-License-Identifier|Upstream-License|License)\s*[:=]\s*([A-Za-z0-9\-\.]+)",
    re.IGNORECASE,
)

violations = []
staged = [s.strip() for s in os.environ.get("STAGED_FILES_TSV", "").splitlines() if s.strip()]
for rel in staged:
    p = ROOT / rel
    if not p.exists():
        continue
    try:
        head = p.read_text(encoding="utf-8", errors="ignore").splitlines()[:30]
    except Exception:
        continue
    tool = None
    upstream_lic = None
    for line in head:
        m = PATTERN.match(line)
        if m and not tool:
            tool = m.group(1).strip().lower()
        m2 = LICENSE_PATTERN.match(line)
        if m2 and not upstream_lic:
            upstream_lic = m2.group(1).strip().upper()
    if not tool:
        continue
    decision = known.get(tool, "missing")
    if decision not in ("approved", "approved-with-conditions"):
        violations.append((rel, tool, decision, upstream_lic or "unknown"))

if not violations:
    print("OK")
else:
    print("BLOCK")
    for rel, tool, decision, lic in violations:
        print(f"  {rel} :: tool={tool} decision={decision} license={lic}")
PY
)"

STATUS="$(printf '%s' "$RESULT" | head -1)"

if [ "$STATUS" = "OK" ] || [ -z "$STATUS" ] || [[ "$STATUS" == SKIP* ]]; then
  _log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"pass\",\"detail\":\"$STATUS\"}"
  exit 0
fi

DETAIL_JSON="$(printf '%s' "$RESULT" | tail -n +2 | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")"
_log "{\"timestamp\":\"$TIMESTAMP\",\"action\":\"block\",\"detail\":$DETAIL_JSON}"

cat >&2 <<EOF
ERROR: legal-review-required gate (ADR-270 primitive #8) blocked the commit.
Staged files import code attributed to a tool lacking an approved ledger entry:
$(printf '%s' "$RESULT" | tail -n +2)

Resolution:
  - Run cos-counsel-packet, get counsel review, then cos-legal-approve.
  - Or bypass (logged): COS_ALLOW_PRE_LEGAL_REVIEW_IMPORT=1 git commit ...
EOF
exit 1
