#!/usr/bin/env bash
# SCOPE: both
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
#   git commit --amend            — no pathspec AND the index has staged files
#
# ALLOWS:
#   git commit --only -- path/to/file ...
#   git commit -a / --all         — explicit "commit everything modified"
#   git commit path/to/file       — bare pathspec (git commit <path> form)
#   git commit -- path/to/file    — double-dash pathspec form
#   git commit --amend -- path    — pathspec IS honoured by --amend (measured)
#   git commit --amend (clean index) — cannot absorb anyone else's work
#   COS_BYPASS_COMMIT_GUARD=1     — emergency bypass (logged)
#   git commit --no-verify ...    — allowed only when paired with a scope flag
#
# WHY --amend GETS ITS OWN VERDICT (measured 2026-08-15, see
# docs/06-Daily/reports/amend-en-checkout-compartido-2026-08-15.md):
#   `git commit --amend -- <path>` DOES honour the pathspec — it is safe.
#   `git commit --amend` with no pathspec rewrites the tip using the ENTIRE
#   index, so in a checkout shared with concurrent agents it silently absorbs
#   whatever they had staged (this is how 3506e1481 swallowed five files
#   belonging to three other agents).  The mechanical discriminator is the
#   index: with nothing staged, a bare --amend can only rewrite the message
#   of the existing commit and cannot co-opt anyone.  That is the escape —
#   no env var needed for the legitimate "fix my own message" case.
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

# Match `git commit` anywhere in the command (handles pipes, &&, etc.).
# Also match global options between `git` and `commit` (`git -C <dir> commit`,
# `git --no-pager commit`), which the previous literal-adjacency regex let
# through untouched.  This is only a cheap prefilter — the Python analyzer
# below is authoritative about which invocation is actually unscoped.
if ! printf '%s' "$COMMAND" | grep -qE '(^|[|&;[:space:]])git[[:space:]]+(commit([[:space:]]|$)|(-C|-c|-P|--no-pager|--paginate|--git-dir|--work-tree|--namespace|--exec-path)[^|&;]*[[:space:]]commit([[:space:]]|$))'; then
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
# Accepted scope indicators:
#   --only      — explicit scoped commit (preferred form)
#   -a / --all  — "commit all modified" (explicit intent)
#   -- <path>   — double-dash pathspec separator
#   <path>      — bare positional pathspec after flags
#
# The analyzer tokenizes the WHOLE command with shlex (quote-aware) and splits
# it into shell segments, so that:
#   * every `git commit` in a compound command is judged on its own — a scoped
#     first commit no longer launders an unscoped `--amend` after `&&`;
#   * a commit MESSAGE that happens to contain `&&` or `git commit` cannot
#     create a phantom segment and cause a false block.
#
# Verdicts: OK | BLOCK_UNSCOPED | BLOCK_AMEND (plus the -C directory, if any).
# Falls back to "allow" if python3 is absent (never false-positive block).
VERDICT="OK"
CDIR=""
if command -v python3 >/dev/null 2>&1; then
  ANALYSIS=$(python3 - "$COMMAND" <<'PYEOF'
import sys, re, shlex

SEPARATORS = {'&&', '||', ';', '|', '&', '\n'}
VALUE_FLAGS = {
    '-m', '--message', '-C', '--reuse-message', '-F', '--file',
    '--author', '--date', '--trailer', '--cleanup', '--squash',
    '--fixup', '--pathspec-from-file', '-e', '--edit',
    '--allow-empty', '--allow-empty-message',
}
BOOL_FLAGS = {
    '--no-edit', '--amend', '--no-verify', '--signoff', '-s',
    '--verbose', '-v', '--quiet', '-q', '--dry-run', '-n',
    '--reset-author', '--no-gpg-sign', '--no-status',
    '--pathspec-file-nul', '--only', '--all', '-a',
    '--include', '-i', '--patch', '-p',
}
# git global options that may sit between `git` and `commit`.
GLOBAL_VALUE_OPTS = {'-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path'}
GLOBAL_BOOL_OPTS = {'--no-pager', '-P', '--paginate', '--bare', '--literal-pathspecs',
                    '--no-replace-objects', '--no-optional-locks'}


def scope_of(args):
    """Given the token list AFTER `commit`, report (has_scope, is_amend)."""
    is_amend = '--amend' in args
    if '--only' in args or '-a' in args or '--all' in args:
        return True, is_amend
    remaining = []
    skip_next = False
    saw_ddash = False
    for tok in args:
        if skip_next:
            skip_next = False
            continue
        if tok == '--':
            saw_ddash = True
            continue
        if saw_ddash:
            remaining.append(tok)
            continue
        if tok in BOOL_FLAGS:
            continue
        if tok in VALUE_FLAGS:
            skip_next = True
            continue
        if re.match(r'^(--[\w-]+=.*|-S.+|-C.+)', tok):
            continue
        if re.match(r'^-[a-zA-Z]{2,}$', tok):
            continue
        remaining.append(tok)
    return bool(remaining), is_amend


def segments(tokens):
    cur = []
    for tok in tokens:
        if tok in SEPARATORS:
            if cur:
                yield cur
            cur = []
        else:
            cur.append(tok)
    if cur:
        yield cur


def find_commit(seg):
    """Locate `git [globals] commit` in a segment.

    Returns (args_after_commit, cdir) or None.
    """
    for i, tok in enumerate(seg):
        if tok != 'git' and not tok.endswith('/git'):
            continue
        j = i + 1
        cdir = ''
        while j < len(seg):
            t = seg[j]
            if t in GLOBAL_VALUE_OPTS:
                if t == '-C' and j + 1 < len(seg):
                    cdir = seg[j + 1]
                j += 2
                continue
            if t in GLOBAL_BOOL_OPTS:
                j += 1
                continue
            if re.match(r'^--(git-dir|work-tree|namespace|exec-path)=', t):
                j += 1
                continue
            break
        if j < len(seg) and seg[j] == 'commit':
            return seg[j + 1:], cdir
    return None


def analyze(cmd):
    """Return (verdict, cdir). Verdict: OK | BLOCK_UNSCOPED | BLOCK_AMEND."""
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError:
        # Unbalanced quotes — fall back to the conservative single-occurrence
        # regex path rather than guessing at segment boundaries.
        body = re.sub(r'^.*?git\s+commit\s*', '', cmd.strip(), flags=re.S)
        try:
            args = shlex.split(body)
        except ValueError:
            return 'BLOCK_UNSCOPED', ''
        has_scope, is_amend = scope_of(args)
        if has_scope:
            return 'OK', ''
        return ('BLOCK_AMEND' if is_amend else 'BLOCK_UNSCOPED'), ''

    for seg in segments(tokens):
        found = find_commit(seg)
        if not found:
            continue
        args, cdir = found
        has_scope, is_amend = scope_of(args)
        if has_scope:
            continue
        return ('BLOCK_AMEND' if is_amend else 'BLOCK_UNSCOPED'), cdir
    return 'OK', ''


cmd = sys.argv[1] if len(sys.argv) > 1 else ''
verdict, cdir = analyze(cmd)
print(verdict + '\t' + cdir)
PYEOF
  )
  VERDICT="${ANALYSIS%%	*}"
  CDIR="${ANALYSIS#*	}"
  [ "$CDIR" = "$VERDICT" ] && CDIR=""
fi

# ── Decision ──────────────────────────────────────────────────────────────────

if [ "$VERDICT" = "OK" ]; then
  exit 0
fi

# --amend without a pathspec: the danger is not the amend itself, it is the
# index.  With nothing staged, the rewrite cannot absorb another session's
# work, so the common "fix my own commit message" case is allowed through.
# Anything uncertain (git failure, no repo, detached state) keeps the previous
# behaviour and blocks.
if [ "$VERDICT" = "BLOCK_AMEND" ]; then
  INDEX_REPO="${CDIR:-$PROJECT_DIR}"
  if git -C "$INDEX_REPO" diff --cached --quiet >/dev/null 2>&1; then
    _emit_commit_receipt "amend-clean-index-allowed"
    exit 0
  fi
  STAGED=$(git -C "$INDEX_REPO" diff --cached --name-only 2>/dev/null | head -20)
  {
    echo "[git-commit-scope-guard] BLOCKED: \`git commit --amend\` without a pathspec, with a non-empty index."
    echo
    echo "--amend rewrites the tip commit using the ENTIRE index, so it will"
    echo "absorb every file staged right now — including files staged by the"
    echo "other sessions sharing this checkout. That is exactly how commit"
    echo "3506e1481 ended up with five files belonging to three other agents"
    echo "under a message that describes none of them."
    echo
    echo "Currently staged (would be swallowed):"
    printf '%s\n' "$STAGED" | sed 's/^/  /'
    echo
    echo "INSTEAD — do not rewrite shared history (see rules/merge-sobre-rebase):"
    echo "  git commit --only -m \"...\" -- path/to/file    (new corrective commit)"
    echo "  git commit --amend -m \"...\" -- path/to/file   (amend, pathspec IS honoured)"
    echo
    echo "A bare --amend is allowed automatically once the index is clean:"
    echo "  git restore --staged <other-agents-paths>   then retry"
    echo
    echo "EMERGENCY BYPASS (logs to agent-audit-trail.jsonl):"
    echo "  COS_BYPASS_COMMIT_GUARD=1 git commit --amend --no-edit"
  } >&2
  _emit_commit_receipt "amend-dirty-index-blocked"
  exit 2
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
