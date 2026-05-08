#!/usr/bin/env bash
# SCOPE: project
# CONCERNS: git-coordination, multi-session, adr-089-layer-1
# git-commit-scope-guard.sh — PreToolUse Bash hook
#
# ADR-089 Layer 1: enforces that every agent-driven `git commit` invocation
# specifies an explicit scope so concurrent sessions cannot co-opt each other's
# staged changes.
#
# BLOCKS (exit 2):
#   git commit -m "..."           — no pathspec, no -a/--all, no --only
#   git commit --no-edit          — same problem
#   git commit --amend            — without explicit pathspec
#
# ALLOWS:
#   git commit --only -- path/to/file ...
#   git commit -a / --all         — explicit "commit everything modified"
#   git commit path/to/file       — bare pathspec (git commit <path> form)
#   git commit -- path/to/file    — double-dash pathspec form
#   COS_BYPASS_COMMIT_GUARD=1     — emergency bypass (logged)
#   git commit --no-verify ...    — allowed only when paired with a scope flag
#
# LATENCY TARGET: < 50 ms (no external process other than optional jq)
#
# shellcheck disable=SC2155

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

# ── Read hook input ───────────────────────────────────────────────────────────

INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

# Only intercept Bash tool invocations
TOOL_NAME=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Bash" ]; then
    exit 0
  fi
fi

# Extract the command string
COMMAND=""
if [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
  COMMAND="$CLAUDE_TOOL_INPUT"
elif [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
elif [ -n "$INPUT" ]; then
  # Regex fallback when jq is unavailable
  COMMAND=$(printf '%s' "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' | head -1)
fi

[ -z "$COMMAND" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"

_emit_commit_receipt() {
  local outcome="$1"
  local receipt_script="$PROJECT_DIR/scripts/cos-action-receipt"
  [ -x "$receipt_script" ] || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  local branch head_sha evidence_json
  branch="$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null || true)"
  head_sha="$(git -C "$PROJECT_DIR" rev-parse HEAD 2>/dev/null || true)"
  evidence_json=$(
    COS_RECEIPT_COMMAND="$COMMAND" \
    COS_RECEIPT_OUTCOME="$outcome" \
    python3 - <<'PY' 2>/dev/null || true
import json
import os
print(json.dumps({
    "hook": "git-commit-scope-guard",
    "outcome": os.environ.get("COS_RECEIPT_OUTCOME", ""),
    "command": os.environ.get("COS_RECEIPT_COMMAND", ""),
}))
PY
  )
  [ -n "$evidence_json" ] || evidence_json='{"hook":"git-commit-scope-guard"}'
  local args
  args=("$receipt_script" emit "vcs.commit" \
    --provider shell-git-hook \
    --source git-hook \
    --trust verified \
    --project-dir "$PROJECT_DIR" \
    --governed-path git-commit-scope-guard \
    --evidence-json "$evidence_json" \
    --append)
  [ -n "$branch" ] && args+=(--branch "$branch")
  [ -n "$head_sha" ] && args+=(--commit-sha "$head_sha")
  "${args[@]}" >/dev/null 2>&1 || true
}

# ── Only act on git commit invocations ───────────────────────────────────────

# Match `git commit` anywhere in the command (handles pipes, &&, etc.)
if ! printf '%s' "$COMMAND" | grep -qE '(^|[|&;[:space:]])git[[:space:]]+commit([[:space:]]|$)'; then
  exit 0
fi

# ── Emergency bypass ─────────────────────────────────────────────────────────

if type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows commit_guard; then
  AUDIT="$PROJECT_DIR/.cognitive-os/runtime/agent-audit-trail.jsonl"
  mkdir -p "$(dirname "$AUDIT")" 2>/dev/null || true
  printf '{"ts":"%s","event":"commit-guard-bypassed","session":"%s","command":%s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "${COGNITIVE_OS_SESSION_ID:-unknown}" \
    "$(printf '%s' "$COMMAND" | sed 's/"/\\"/g; s/^/"/; s/$/"/')" \
    >> "$AUDIT" 2>/dev/null || true
  _emit_commit_receipt "commit-scope-bypass"
  exit 0
fi

# ── Scope analysis ────────────────────────────────────────────────────────────
# We extract only the git commit portion for analysis.
# Strategy: look for the first `git commit` occurrence and examine what follows.

# Accepted scope indicators:
#   --only      — explicit scoped commit (preferred form)
#   -a / --all  — "commit all modified" (explicit intent)
#   -- <path>   — double-dash pathspec separator
#   <path>      — bare positional pathspec after flags
#                 (heuristic: any non-flag token that looks like a path or glob)

# Extract the portion starting from "git commit"
GIT_COMMIT_PART=$(printf '%s' "$COMMAND" | grep -oE 'git[[:space:]]+commit.*' | head -1)

# Use Python for reliable scope analysis (works on macOS and Linux without
# dependency on GNU sed extensions or jq).  Python 3 is always available
# in COS environments.  Falls back to conservative "has scope" if python3 is
# absent (never block when uncertain).
has_scope=0
if command -v python3 >/dev/null 2>&1; then
  has_scope=$(python3 - "$GIT_COMMIT_PART" <<'PYEOF'
import sys, re, shlex

def has_explicit_scope(cmd: str) -> bool:
    """Return True if git commit has an explicit scope indicator."""
    # Check for explicit scope flags (fast path — no tokenization needed)
    if re.search(r'\s--only(\s|$)', cmd):
        return True
    if re.search(r'\s(-a|--all)(\s|$)', cmd):
        return True
    # Double-dash pathspec separator: -- <non-empty>
    if re.search(r'\s--\s+\S', cmd):
        return True

    # Check for bare positional pathspec by stripping all known flags+args.
    # Flags that take a value argument (next token or =value):
    VALUE_FLAGS = {
        '-m', '--message', '-C', '--reuse-message', '-F', '--file',
        '--author', '--date', '--trailer', '--cleanup', '--squash',
        '--fixup', '--pathspec-from-file', '-e', '--edit',
        '--allow-empty', '--allow-empty-message',
    }
    # Boolean flags (take no argument):
    BOOL_FLAGS = {
        '--no-edit', '--amend', '--no-verify', '--signoff', '-s',
        '--verbose', '-v', '--quiet', '-q', '--dry-run', '-n',
        '--reset-author', '--no-gpg-sign', '--no-status',
        '--pathspec-file-nul', '--only', '--all', '-a',
        '--include', '-i', '--patch', '-p',
    }

    # Strip "git commit" prefix and tokenize
    body = re.sub(r'^git\s+commit\s*', '', cmd.strip())
    try:
        tokens = shlex.split(body)
    except ValueError:
        # Unbalanced quotes — conservative: assume no scope
        return False

    remaining = []
    skip_next = False
    for tok in tokens:
        if skip_next:
            skip_next = False
            continue
        if tok in BOOL_FLAGS:
            continue
        if tok in VALUE_FLAGS:
            skip_next = True
            continue
        # Flags with embedded = (e.g. --message="msg", --gpg-sign=KEY, -S<key>)
        if re.match(r'^(--[\w-]+=.*|-S.+|-C.+)', tok):
            continue
        # Short combined flags that don't look like paths (e.g. -sv, -nq)
        if re.match(r'^-[a-zA-Z]{2,}$', tok):
            continue
        remaining.append(tok)

    return bool(remaining)

cmd = sys.argv[1] if len(sys.argv) > 1 else ''
print('1' if has_explicit_scope(cmd) else '0')
PYEOF
  )
else
  # No python3 — cannot analyze safely; allow through (never false-positive block)
  has_scope=1
fi

# ── Decision ──────────────────────────────────────────────────────────────────

if [ "$has_scope" -eq 1 ]; then
  exit 0
fi

# No scope detected — block.
cat >&2 <<'GUARD_ERROR'
[git-commit-scope-guard] BLOCKED: bare `git commit` without explicit scope detected.

Under ADR-089 (multi-session git coordination), agent-driven commits MUST
specify an explicit commit scope to prevent co-opting staged changes from a
concurrent session.

REQUIRED — use one of:
  git commit --only -- path/to/file [path2 ...]   (preferred: scoped commit)
  git commit -a -m "..."                           (explicit: all modified files)
  git commit -- path/to/file -m "..."             (double-dash pathspec)

NOT allowed:
  git commit -m "..."                              (commits entire staged index)
  git commit --no-edit                             (no explicit scope)

EMERGENCY BYPASS (logs to agent-audit-trail.jsonl):
  COS_BYPASS_COMMIT_GUARD=1 git commit -m "..."
GUARD_ERROR

_emit_commit_receipt "unscoped-commit-blocked"
exit 2
