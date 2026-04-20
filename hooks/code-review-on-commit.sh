#!/usr/bin/env bash
# code-review-on-commit.sh — Git pre-commit hook that runs code review on staged files
#
# Fires as a git pre-commit hook (NOT a Claude Code hook).
# Gets staged files, runs lib/code_reviewer.py static analysis, and shows
# findings before commit. WARN only — never blocks commits.
#
# Environment variables:
#   CODE_REVIEW_SKIP  — set to "true" to skip review entirely
#
# Exit codes:
#   0 — always (advisory only, never blocks)
set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ─── Skip check ────────────────────────────────────────────────────────────

if [[ "${CODE_REVIEW_SKIP:-false}" == "true" ]]; then
  exit 0
fi

# ─── Ensure Python and lib are available ────────────────────────────────────

if ! command -v python3 &>/dev/null; then
  exit 0
fi

if [[ ! -f "$ROOT_DIR/lib/code_reviewer.py" ]]; then
  exit 0
fi

# ─── Get staged files ──────────────────────────────────────────────────────

staged_files=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null)

if [[ -z "$staged_files" ]]; then
  exit 0
fi

# Filter to source code files only
source_files=""
while IFS= read -r f; do
  case "$f" in
    *.py|*.go|*.ts|*.js|*.java|*.rs|*.rb|*.sh|*.yaml|*.yml|*.json|*.toml)
      source_files="${source_files}${f}\n"
      ;;
  esac
done <<< "$staged_files"

if [[ -z "$source_files" ]]; then
  exit 0
fi

# ─── Run code review ──────────────────────────────────────────────────────

# Build a Python one-liner that reviews the staged files
review_output=$(cd "$ROOT_DIR" && timeout 60 python3 -c "
import sys, json
sys.path.insert(0, '.')
from lib.code_reviewer import CodeReviewer

files = [f.strip() for f in '''${source_files}'''.strip().split('\n') if f.strip()]
if not files:
    sys.exit(0)

reviewer = CodeReviewer(project_root='.')
report = reviewer.review_files(files)

# Only show if there are real findings (not just adversarial fallback)
has_real = any(
    f.severity in ('BLOCKER', 'CONCERN')
    for f in report.findings
)

if not has_real and len(report.findings) <= 1:
    sys.exit(0)

print('--- Code Review (pre-commit) ---')
print(f'Status: {report.status} | Files: {report.files_reviewed} | Findings: {len(report.findings)}')
for finding in report.findings:
    line_str = f':{finding.line}' if finding.line else ''
    print(f'  [{finding.severity}] {finding.file}{line_str} — {finding.what}')
print('--- End Review ---')
" 2>/dev/null)

if [[ -n "$review_output" ]]; then
  echo "$review_output" >&2
fi

# Always exit 0 — advisory only
exit 0
