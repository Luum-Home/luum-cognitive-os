#!/usr/bin/env bash
# SCOPE: both
# CONCERNS: safety, git-ops, adr-003-mechanism-c
# Destructive Git Op Blocker — PreToolUse Bash
#
# Intercepts bash commands about to run and blocks the destructive-git-op
# subset by default in BOTH agent and user contexts. Per ADR-055b (decision #6,
# r5-stash-residue closure), the previous warn-only behavior in user context
# was insufficient — stash-residue and other destructive ops in interactive
# orchestration caused the incident class documented in
# docs/06-Daily/reports/bug2-reset-cascade-forensics-2026-04-20.md §5.
#
# Blocked by default (exit 2):
#   - git stash pop | stash drop | stash apply
#   - git reset (any form; mutates HEAD/index/worktree state)
#   - git checkout -- <anything>  (incl. `checkout HEAD -- <path>` form)
#   - git clean -f[dx]
#   - git restore (any form)
#   - git revert (any form)
#   - git worktree (any subcommand)
#   - git branch -D (force-delete)
#   - git rebase (any form; mutates history/worktree state)
#   - git pull --rebase (shared-worktree rebase/reset hazard)
#   - git switch / git checkout branch changes (unannounced branch context changes)
#   - git commit / git push from protected main/master branches
#   - git push --force / git push -f  (force-push, 2026-05-02 extension)
#     NOTE: --force-with-lease is intentionally NOT blocked (safer alternative)
#
# Allowed always:
#   - git status, git diff, git log, git show, git blame, git rev-parse, …
#   - git push --force-with-lease (safer force push)
#   - any non-git bash command
#   - patterns appearing only inside `git commit -m "..."` message bodies
#     (false-positive fix: commit messages may document destructive ops without
#      the hook treating them as if the ops themselves were executed)
#
# Override mechanisms (ADR-055b). The per-command token goes in a trailing
# shell COMMENT, e.g.  git reset --hard HEAD~1  # --allow-destructive
# Passed as a real argument it reaches git, which rejects it: measured
# 2026-08-19, both `git commit -m x --allow-destructive` and this file's own
# former example `git reset --hard HEAD~1 --allow-destructive` exit 129,
# "unknown option" -- so the documented form could never be used. A comment is
# addressed to this hook and invisible to git, which is the point.
# The token must also sit OUTSIDE quotes: see _approval_scan_text below.
#   - Per-command: `--allow-destructive` token (general bypass)
#   - Per-command: `--allow-force-push` token (force-push-specific bypass)
#   - Per-command: `--allow-main-branch` / `--allow-branch-switch` tokens
#   - Per-session: export COS_ALLOW_DESTRUCTIVE_GIT=1
#   - Protected branch write bypass: export COS_ALLOW_MAIN_BRANCH_WRITE=1
#   - Branch context switch bypass: export COS_ALLOW_BRANCH_SWITCH=1
# The env forms must be exported in the environment that LAUNCHES the harness.
# A `VAR=1 <command>` prefix does not reach this hook: it runs as a separate
# process and never sees the assignment.
#
# Bypass contexts (SO-internal — block does not apply):
#   - CI=1 (CI environment)
#   - PYTEST_CURRENT_TEST set (running under pytest)
#   - COS_GIT_BYPASS=1 (reaper, watchdog, sandbox operations)
#
# Agent context (CLAUDE_AGENT_ID set) retains exit 1 for backwards-compat with
# existing tests; user context uses exit 2 per ADR convention.
#
# Logs every block to:
#   .cognitive-os/metrics/git-op-blocks.jsonl
#
# Reference: ADR-003 Mechanism C, ADR-055b (block elevation).

set -uo pipefail
# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="destructive-git-blocker"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/primitive-intervention.sh"
source "$(dirname "$0")/_lib/bypass-resolver.sh"
source "$(dirname "$0")/_lib/agent-context.sh"
[ -f "$(dirname "$0")/_lib/governance-policy.sh" ] && source "$(dirname "$0")/_lib/governance-policy.sh"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
BLOCKS_LOG="$PROJECT_DIR/.cognitive-os/metrics/git-op-blocks.jsonl"
# ADR-116 P3.2: WIP-guard bypass log (separate from general block log)
BYPASS_LOG="$PROJECT_DIR/.cognitive-os/metrics/destructive-git-bypass.jsonl"

# Read stdin (best-effort)
INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

# Gate to Bash tool — other tools must not be blocked
TOOL_NAME=""
if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Bash" ]; then
    exit 0
  fi
fi

# Extract the command — jq preferred, regex fallback. CLAUDE_TOOL_INPUT may
# carry the command directly (used by tests / some harness plugins).
COMMAND=""
if [ -n "${CLAUDE_TOOL_INPUT:-}" ]; then
  COMMAND="$CLAUDE_TOOL_INPUT"
elif [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
  COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
fi

# No command, nothing to do
if [ -z "$COMMAND" ]; then
  exit 0
fi

# Pattern — note: extended regex, dollar-less because we match anywhere after the git invocation.
# ADR-003 R1 fix (2026-04-20 forensic): the original regex `checkout[[:space:]]+--` matched
# `git checkout -- foo` but NOT `git checkout HEAD -- foo` (the exact form that triggered the
# Sprint-2a incident per ADR-003 §Context line 10). The checkout alternative now matches both
# direct (`checkout -- <path>`) and via-ref (`checkout <ref> -- <path>`, e.g. HEAD, HEAD~1,
# <sha>, <branch>, <tag>) forms. `<ref>` may contain letters, digits, slash, dot, underscore,
# tilde, caret, hyphen.
DESTRUCTIVE_PATTERN='^[[:space:]]*git[[:space:]]+(stash[[:space:]]+(pop|drop|apply)|reset([[:space:]]|$)|pull([^;&|]*)[[:space:]]+--rebase([[:space:]]|$)|checkout[[:space:]]+(--|[A-Za-z0-9/._~^-]+[[:space:]]+--)|clean[[:space:]]+-f|restore|revert|worktree[[:space:]]+(add|remove|move|prune|repair|lock|unlock)([[:space:]]|$)|branch[[:space:]]+-D|rebase([[:space:]]|$))'

# Force-push pattern (2026-05-02): matches `git push --force` and `git push -f` (with word
# boundary after -f to avoid matching -fast-forward or similar flags).
# INTENTIONALLY does NOT match --force-with-lease (safer alternative, allowed per ADR-055b).
FORCE_PUSH_PATTERN='^[[:space:]]*git[[:space:]]+push([[:space:]]+[^[:space:]]+)*[[:space:]]+(--force\b|-f\b)'

# ── ADR-116 P3.2: WIP-guard helpers ──────────────────────────────────────────
# WIP-guard op pattern: ops that silently wipe working-tree edits when WIP
# exists. These are a subset of DESTRUCTIVE_PATTERN; they get a richer block
# message listing the WIP files and offering the COS_ALLOW_RESET_OVER_WIP
# and COS_AUTO_STASH_BEFORE_RESET bypass paths.
WIP_GUARD_PATTERN='^[[:space:]]*git[[:space:]]+(pull([^;&|]*)[[:space:]]+--rebase([[:space:]]|$)|rebase([[:space:]]|$))'

# git fetch && git reset --hard origin/<branch> chained form detector.
# Returns 0 when the overall command string contains both patterns.
_is_fetch_reset_chain() {
  local cmd="$1"
  echo "$cmd" | grep -q 'git[[:space:]]\+fetch' \
    && echo "$cmd" | grep -Eq 'git[[:space:]]+reset[[:space:]]+--hard[[:space:]]+origin/'
}

# Returns 0 (true) when the working tree has uncommitted modifications.
_has_wip() {
  local out
  out=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null || true)
  [ -n "$out" ]
}

# Prints the top-10 WIP entries with status prefix, indented for display.
_wip_file_list() {
  git -C "$PROJECT_DIR" status --porcelain 2>/dev/null \
    | head -10 \
    | awk '{print "  " $0}'
}

# Prints a JSON-safe bracketed array string of the top-10 WIP file paths.
_wip_files_json_array() {
  local items
  items=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null \
    | head -10 \
    | awk '{f=$NF; gsub(/"/, "\\\"", f); printf "\"%s\",", f}' \
    | sed 's/,$//')
  printf '[%s]' "$items"
}

# ── Commit-message stripping (false-positive fix 2026-05-02) ─────────────────
# When a command is `git commit ... -m "..." ...` the quoted message body may
# reference destructive ops (e.g. "feat: documents git stash pop behavior").
# Stripping the -m argument before pattern-matching prevents false positives.
# Handles: -m "text", -m 'text', --message="text", --message 'text'.
# Strips all such argument values from the raw COMMAND before scanning.
_strip_commit_message_args() {
  local cmd="$1"
  # Only strip when the command looks like a git commit invocation
  if ! echo "$cmd" | grep -Eq '^[[:space:]]*git[[:space:]]+commit[[:space:]]'; then
    echo "$cmd"
    return
  fi
  # Strip -m "quoted" or -m 'quoted' (non-greedy: stops at first matching quote)
  # Also handles --message= variants
  # Use sed with basic extended regex; loop to strip multiple -m args
  local stripped="$cmd"
  # Remove -m "..." (double-quoted)
  stripped=$(echo "$stripped" | sed 's/-m[[:space:]]*"[^"]*"//g')
  # Remove -m '...' (single-quoted)
  stripped=$(echo "$stripped" | sed "s/-m[[:space:]]*'[^']*'//g")
  # Remove --message="..." (double-quoted)
  stripped=$(echo "$stripped" | sed 's/--message=[[:space:]]*"[^"]*"//g')
  # Remove --message='...' (single-quoted)
  stripped=$(echo "$stripped" | sed "s/--message=[[:space:]]*'[^']*'//g")
  echo "$stripped"
}

# ── Quote-aware command segmentation (false-positive fix 2026-08-16) ─────────
# WHY THIS EXISTS
#   The previous reader split the raw command with `tr '|&;' '\n'`, i.e. at the
#   CHARACTER level, with no idea whether a separator was shell syntax or text
#   inside quotes. Measured on this hook: `echo "texto con && git stash pop"`
#   exited 2. Nothing in that command runs a git op — the `&&` inside the
#   string manufactured a segment that began with `git`, and the ^-anchored
#   DESTRUCTIVE_PATTERN then matched it. Commenting an op, documenting one in
#   a commit-message body, or printing one was enough to block the command.
#
#   The verdict layer had the mirror-image defect: _semantic_git_match located
#   `git` ANYWHERE in the token list, so `ls -la  # never run git stash pop`
#   blocked too, with no separator involved at all.
#
# WHAT IT DOES
#   Tokenises the whole command with shlex (quote-aware), splits on real shell
#   operators, drops heredoc BODIES (stdin data, never commands — unless the
#   reader is an interpreter), recurses into `bash -c` / `eval` so a genuinely
#   executed op cannot hide inside a quoted argument, and strips leading
#   VAR=VAL assignments and wrapper words (`sudo`, `env`, …) so the caller can
#   anchor its verdict at the command word.
#
# DETECTION IS NOT REDUCED
#   Every op that used to block still blocks; only text that was never going
#   to be executed stops blocking. On unbalanced quotes the analyzer refuses
#   to guess and exits 3, and the caller falls back to the legacy
#   character-level split — which over-blocks. Uncertainty keeps blocking.
#
# PORTED FROM hooks/git-commit-scope-guard.sh (commit 3045f71f8), which grew
# the same shlex-tokenise-then-segment analyzer for the same class of bug.
# This is the SECOND copy of that grammar; hooks/provenance-scan.sh records
# the same divergence risk. Extracting one parser to hooks/_lib/ is the right
# end state — see docs/06-Daily/reports/guards-quoting-ciego-2026-08-16.md.
_segment_command() {
  command -v python3 >/dev/null || return 3
  python3 - "$1" <<'SEGPY'
from __future__ import annotations

import re
import shlex
import sys

# Shell control operators that end one command and begin another. `\n` is in
# the set because a newline separates commands exactly like `;` does — and
# because a newline INSIDE a quoted `-m` message must NOT, which is precisely
# what a character-level split cannot tell apart.
SEPARATORS = {"&&", "||", ";", "|", "&", "\n", "(", ")"}

# Command words whose ARGUMENT is itself a command. Without these the
# anchoring below would stop seeing `bash -c 'git reset --hard'`, which is a
# real execution and must keep blocking.
INTERPRETERS = {"bash", "sh", "zsh", "ksh", "dash", "eval", "xargs"}

# Prefix words that precede the real command word without being one.
WRAPPERS = {"sudo", "env", "command", "nohup", "time", "exec", "builtin",
            "doas", "nice", "ionice", "stdbuf", "setsid"}


def _strip_comments(cmd: str) -> str:
    """Remove `#` comments, keeping the newline that terminates each one.

    shlex's own commenter calls readline(), which swallows the newline along
    with the comment. That newline is a command separator: with it gone,
    `ls  # <op>\n<op>` collapsed into ONE segment whose command word was `ls`,
    and the real op on the next line stopped being seen. Measured while
    building this fix — a detection loss, not a false positive, which is why
    comments are stripped here instead.

    A `#` only opens a comment when unquoted and at the start of a word.
    """
    out = []
    quote = ""
    prev = ""
    i = 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            out.append(ch)
            if ch == quote and (quote == "'" or prev != "\\"):
                quote = ""
            prev = ch
            i += 1
            continue
        if ch in "\"'" and prev != "\\":
            quote = ch
            out.append(ch)
            prev = ch
            i += 1
            continue
        if ch == "#" and (prev == "" or prev in " \t\r\n;&|()"):
            while i < len(cmd) and cmd[i] != "\n":
                i += 1
            prev = ""
            continue
        out.append(ch)
        prev = ch
        i += 1
    return "".join(out)


def _lex(cmd: str) -> list[str]:
    """Quote-aware tokenisation. Raises ValueError on unbalanced quotes."""
    lx = shlex.shlex(_strip_comments(cmd), posix=True, punctuation_chars="();<>|&\n")
    lx.whitespace_split = True
    lx.whitespace = " \t\r"
    lx.commenters = ""
    return list(lx)


def _command_word(seg: list[str]) -> tuple[str, int]:
    """Return (command word, its index) skipping VAR=VAL and wrapper words."""
    for i, tok in enumerate(seg):
        if "=" in tok and not tok.startswith("-") and tok.split("=", 1)[0].isidentifier():
            continue
        if tok in WRAPPERS:
            continue
        return tok, i
    return "", -1


def _drop_heredocs(tokens: list[str]) -> list[str]:
    """Remove heredoc BODIES from the token stream.

    A heredoc body is data on stdin, never commands — unless the reader is an
    interpreter, in which case it is left in place. Dropping it is what stops
    a documented command inside `cat <<EOF ... EOF` from being judged as one.
    """
    out: list[str] = []
    line: list[str] = []
    pending: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "\n":
            out.extend(line)
            out.append(tok)
            if pending:
                word, _ = _command_word(line)
                i += 1
                if word in INTERPRETERS:
                    pending = []
                    line = []
                    continue
                # Skip forward to the terminator line.
                delims = set(pending)
                pending = []
                while i < len(tokens):
                    if tokens[i] in delims and (i + 1 >= len(tokens) or tokens[i + 1] == "\n"):
                        i += 1
                        break
                    i += 1
            else:
                i += 1
            line = []
            continue
        if tok in ("<<", "<<-") and i + 1 < len(tokens):
            pending.append(tokens[i + 1])
            i += 2
            continue
        line.append(tok)
        i += 1
    out.extend(line)
    return out


def segments(cmd: str, _depth: int = 0) -> list[list[str]]:
    """Split a command into shell segments, honouring quotes.

    Recurses into `bash -c "..."` / `eval "..."` so anchoring the verdict to a
    segment's command word cannot lose an op that is genuinely executed.
    """
    tokens = _drop_heredocs(_lex(cmd))
    segs: list[list[str]] = []
    cur: list[str] = []
    for tok in tokens:
        if tok in SEPARATORS:
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(tok)
    if cur:
        segs.append(cur)

    if _depth >= 3:
        return segs
    expanded: list[list[str]] = []
    for seg in segs:
        expanded.append(seg)
        word, idx = _command_word(seg)
        if word not in INTERPRETERS:
            continue
        rest = seg[idx + 1:]
        inner = ""
        if word == "eval":
            inner = " ".join(rest)
        elif "-c" in rest:
            j = rest.index("-c")
            if j + 1 < len(rest):
                inner = rest[j + 1]
        if inner:
            try:
                expanded.extend(segments(inner, _depth + 1))
            except ValueError:
                # Unparseable inner command: hand the raw text back as a
                # segment so the caller still judges it. Uncertainty blocks.
                expanded.append(inner.split())
    return expanded


def normalized(cmd: str) -> list[str]:
    """One printable line per segment, command word first.

    Leading VAR=VAL assignments and wrapper words are dropped so that the
    caller can anchor its verdict at the command word — `sudo git reset` and
    `FOO=1 git reset` must keep blocking. Embedded newlines/tabs (a quoted
    multi-line `-m` body) are folded to spaces so one segment stays one line
    for the shell reader downstream.
    """
    out = []
    for seg in segments(cmd):
        _, idx = _command_word(seg)
        if idx > 0:
            seg = seg[idx:]
        line = " ".join(seg)
        line = re.sub(r"[\n\t\r]+", " ", line).strip()
        if line:
            out.append(line)
    return out


if __name__ == "__main__":
    try:
        segs = normalized(sys.argv[1] if len(sys.argv) > 1 else "")
    except ValueError:
        # Unbalanced quotes: refuse to guess at boundaries. Exit 3 tells the
        # caller to fall back to the legacy character-level split, which
        # over-blocks. Uncertainty must keep blocking, never start allowing.
        sys.exit(3)
    for seg in segs:
        sys.stdout.write(seg + "\n")
SEGPY
}

_semantic_git_match() {
  command -v python3 >/dev/null || return 1
  python3 - "$1" <<'PY'
from __future__ import annotations

import shlex
import sys
from pathlib import Path

try:
    parts = shlex.split(sys.argv[1])
except ValueError:
    sys.exit(1)

# Anchored at the COMMAND WORD, not "anywhere in the token list". The old
# `next(i for i, token in ...)` form matched `git` wherever it appeared, so a
# segment that merely MENTIONED an op — a trailing `# comment`, a message
# body, an argument to another program — was judged as if it ran one.
# Callers pass segments produced by _segment_command(), which has already
# removed leading VAR=VAL assignments and wrapper words, so position 0 is the
# command word. `sudo git reset` and `FOO=1 git reset` therefore still block.
if not parts or not (parts[0] == "git" or Path(parts[0]).name == "git"):
    sys.exit(1)
git_idx = 0

i = git_idx + 1
while i < len(parts):
    token = parts[i]
    if token in {"-C", "--git-dir", "--work-tree", "-c"}:
        i += 2
        continue
    if token.startswith("--git-dir=") or token.startswith("--work-tree="):
        i += 1
        continue
    if token == "--":
        i += 1
        continue
    sub = token
    args = parts[i + 1 :]
    break
else:
    sys.exit(1)

def emit(kind: str, op: str, wip: int = 0) -> None:
    print(f"{kind}\t{op}\t{wip}")
    sys.exit(0)

if sub == "stash" and args and args[0] in {"pop", "drop", "apply"}:
    emit("destructive", f"git stash {args[0]}")
if sub == "reset":
    # `git reset [<tree-ish>] -- <paths>` never moves HEAD and never touches
    # the working tree: with a pathspec, git resets index entries only, and it
    # refuses --hard/--merge/--keep in that form outright. It is the classic
    # unstage, and the modern spelling of it (`git restore --staged`) is
    # handled below. The explicit `--` separator is what makes the pathspec
    # unambiguous, so it is required: `git reset HEAD file` without it stays
    # blocked rather than guessed at. --hard/--merge/--keep/--soft anywhere in
    # the args disqualify, belt-and-braces against a future git that permits
    # the combination.
    _tree_touching = {"--hard", "--merge", "--keep", "--soft"}
    if "--" in args and not _tree_touching.intersection(args):
        _paths = args[args.index("--") + 1 :]
        if any(a.strip() for a in _paths):
            emit("index_only", "git reset -- <pathspec>")
    emit("destructive", "git reset")
if sub == "pull" and "--rebase" in args:
    emit("destructive", "git pull --rebase", 1)
if sub == "checkout" and "--" in args:
    emit("destructive", "git checkout --")
if sub == "checkout" and "--" not in args:
    # Any non pathspec-disambiguated checkout can move HEAD/branch context or
    # discard paths without the explicit `--` form. Block so agents cannot
    # silently move commits to an unexpected branch.
    if args and not any(arg in {"--help", "-h"} for arg in args):
        emit("branch_context_change", "git checkout branch/context")
if sub == "switch":
    if not any(arg in {"--help", "-h"} for arg in args):
        emit("branch_context_change", "git switch")
if sub == "clean" and any(arg.startswith("-") and "f" in arg for arg in args):
    emit("destructive", "git clean -f")
if sub == "restore":
    # git-restore(1): "Specifying --staged will only restore the index."
    # Index-only, so nothing in the working tree is discarded — this is the
    # modern `git reset HEAD <file>`. --worktree/-W alongside it restores both
    # and stays blocked, as does plain `git restore <path>`, which is the
    # genuinely destructive form.
    _staged = any(a in {"--staged", "-S"} for a in args)
    _worktree = any(a in {"--worktree", "-W"} for a in args)
    if _staged and not _worktree:
        emit("index_only", "git restore --staged")
    emit("destructive", "git restore")
if sub == "revert":
    emit("destructive", "git revert")
if sub == "worktree" and args and args[0] in {"add", "remove", "move", "prune", "repair", "lock", "unlock"}:
    emit("destructive", "git worktree")
if sub == "branch" and any(arg == "-D" or (arg.startswith("-") and "D" in arg) for arg in args):
    emit("destructive", "git branch -D")
if sub == "rebase":
    emit("destructive", "git rebase", 1)
if sub == "push":
    has_force = any(arg == "-f" or arg == "--force" for arg in args)
    has_lease = any(arg == "--force-with-lease" or arg.startswith("--force-with-lease=") for arg in args)
    if has_force and not has_lease:
        emit("force_push", "git push --force")

sys.exit(1)
PY
}

# Build the segment list. Quote-aware analyzer first; on unbalanced quotes
# (exit 3) fall back to commit-message stripping plus the legacy
# character-level split, which over-blocks rather than under-blocks.
# Every verdict this hook can reach requires the word `git` somewhere in the
# command. Commands without it are the overwhelming majority of PreToolUse
# traffic, and this test costs no subprocess at all — it is what keeps the
# quote-aware analyzer off the hot path for `ls`, `cat`, `pytest`, and friends.
if ! printf '%s' "$COMMAND" | grep -q 'git'; then
  exit 0
fi

COMMAND_SCAN="$COMMAND"
SEGMENT_SOURCE="quote-aware"
SEGMENTS=$(_segment_command "$COMMAND")
if [ $? -ne 0 ]; then
  SEGMENT_SOURCE="legacy-split"
  COMMAND_SCAN=$(_strip_commit_message_args "$COMMAND")
  SEGMENTS=$(echo "$COMMAND_SCAN" | tr '|&;' '\n')
fi

# Test first line (commands may be multiline or pipelined — we inspect each sub-command
# crudely by splitting on shell separators).
FIRST_HIT=""
FIRST_HIT_TYPE=""
SEMANTIC_OP_NAME=""
PROTECTED_BRANCH_HIT=""
PROTECTED_BRANCH=""
# ADR-116 P3.2: track whether the matched op is a WIP-guard candidate.
IS_WIP_GUARD_OP=0
# Turn && || ; and pipe | into newlines, then test each segment
while IFS= read -r segment; do
  [ -z "$segment" ] && continue
  # strip leading whitespace
  trimmed="${segment#"${segment%%[![:space:]]*}"}"
  # _semantic_git_match spawns python3 (~40 ms CPU). It can only return a
  # verdict for a segment whose command word is git, so ask that question in
  # bash first and spend the process only when the answer is yes.
  semantic_hit=""
  case "$trimmed" in
    git|git\ *|*/git|*/git\ *) semantic_hit=$(_semantic_git_match "$trimmed" || true) ;;
  esac
  if [ -n "$semantic_hit" ]; then
    # An index_only verdict means the parser proved the segment touches the
    # index and nothing else (unstage forms). Skip the whole segment rather
    # than break: the coarse DESTRUCTIVE_PATTERN below matches `reset` and
    # `restore` unconditionally and would otherwise re-block what the parser
    # just cleared. The semantic parser is the only layer that can see flags,
    # so it is the only layer that can grant this.
    if [ "$(printf '%s' "$semantic_hit" | awk -F '\t' '{print $1}')" = "index_only" ]; then
      continue
    fi
    FIRST_HIT="$trimmed"
    FIRST_HIT_TYPE=$(printf '%s' "$semantic_hit" | awk -F '\t' '{print $1}')
    SEMANTIC_OP_NAME=$(printf '%s' "$semantic_hit" | awk -F '\t' '{print $2}')
    IS_WIP_GUARD_OP=$(printf '%s' "$semantic_hit" | awk -F '\t' '{print $3}')
    break
  fi
  if echo "$trimmed" | grep -Eq "$DESTRUCTIVE_PATTERN"; then
    FIRST_HIT="$trimmed"
    FIRST_HIT_TYPE="destructive"
    # Flag if this hit is also a WIP-guard op (pull --rebase or rebase)
    if echo "$trimmed" | grep -Eq "$WIP_GUARD_PATTERN"; then
      IS_WIP_GUARD_OP=1
    fi
    break
  fi
  # PROTECCION DE RAMA: ahora es OPT-IN. Antes bloqueaba por default.
  #
  # Medido el 2026-08-21 sobre una jornada de trabajo real:
  #
  #     19  main_branch_override   <- veces que hubo que poner el token para
  #                                   hacer un commit NORMAL
  #      3  commit / push en main bloqueados
  #     --
  #     22  eventos de friccion, 22 anulados, CERO daño evitado
  #
  # Un guard que se anula el 100% de las veces no protege: cobra peaje y entrena
  # al operador a saltearlo. Ese entrenamiento es el costo real, porque el
  # reflejo de "poner el token y seguir" se lleva puesto tambien al guard que SI
  # tenia razon.
  #
  # Lo genuinamente destructivo --reset --hard, clean -fdx, branch -D,
  # force-push sin lease-- sigue bloqueando por default y no se toco. Aquello es
  # irreversible; esto es una convencion de flujo. Commitear en main no pierde
  # trabajo, y en un repo de un solo mantenedor tampoco pisa a nadie.
  #
  # Reactivar --equipo con varios escritores, flujo de PR:
  #     export COS_PROTECT_MAIN_BRANCH=1
  if [ "${COS_PROTECT_MAIN_BRANCH:-0}" = "1" ] && \
     echo "$trimmed" | grep -Eq '^[[:space:]]*git[[:space:]]+(commit|push)([[:space:]]|$)'; then
    current_branch=$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null || true)
    if echo "$current_branch" | grep -Eq '^(main|master)$'; then
      FIRST_HIT="$trimmed"
      FIRST_HIT_TYPE="protected_branch_write"
      PROTECTED_BRANCH_HIT="$trimmed"
      PROTECTED_BRANCH="$current_branch"
      break
    fi
  fi
  # Check force-push pattern; exclude --force-with-lease explicitly
  if echo "$trimmed" | grep -Eq "$FORCE_PUSH_PATTERN"; then
    if ! echo "$trimmed" | grep -q -- '--force-with-lease'; then
      FIRST_HIT="$trimmed"
      FIRST_HIT_TYPE="force_push"
      break
    fi
  fi
done <<< "$SEGMENTS"

# ADR-116 P3.2: detect fetch+reset --hard origin/<branch> chained form.
# This form bypasses the per-segment loop above because neither segment alone
# matches DESTRUCTIVE_PATTERN for the WIP-guard purpose; we need to catch the
# combination. A plain `git reset --hard ...` is already caught above; we only
# need to set IS_WIP_GUARD_OP for the fetch+reset chain.
if [ -z "$FIRST_HIT" ] && _is_fetch_reset_chain "$COMMAND_SCAN"; then
  FIRST_HIT="$COMMAND_SCAN"
  FIRST_HIT_TYPE="destructive"
  IS_WIP_GUARD_OP=1
fi

# No match → allow silently
if [ -z "$FIRST_HIT" ]; then
  exit 0
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
AGENT_ID="${CLAUDE_AGENT_ID:-}"

# ── Agent-context detection (R4 hardening) ───────────────────────────────────
# Consider "agent context" if ANY of the following is true:
#   1. CLAUDE_AGENT_ID is non-empty
#   2. COGNITIVE_OS_SESSION_ID is non-empty
#   3. ORCHESTRATOR_MODE == executor
#   4. Parent process name matches claude or claude-code (best-effort)
_git_blocker_is_agent_context() {
  cos_is_agent_context
}

# Extract the matched op name (stash pop, reset --hard, etc.) for the alert text
if [ "$FIRST_HIT_TYPE" = "force_push" ]; then
  OP_NAME="git push --force"
elif [ "$FIRST_HIT_TYPE" = "protected_branch_write" ]; then
  OP_NAME="git ${PROTECTED_BRANCH_HIT#git } on ${PROTECTED_BRANCH}"
elif [ "$FIRST_HIT_TYPE" = "branch_context_change" ] && [ -n "$SEMANTIC_OP_NAME" ]; then
  OP_NAME="$SEMANTIC_OP_NAME"
elif [ -n "$SEMANTIC_OP_NAME" ]; then
  OP_NAME="$SEMANTIC_OP_NAME"
else
  OP_NAME=$(echo "$FIRST_HIT" | awk '{
    if ($2=="stash") print "git stash " $3;
    else if ($2=="reset") print "git reset";
    else if ($2=="pull") print "git pull --rebase";
    else if ($2=="checkout") print "git checkout --";
    else if ($2=="clean") print "git clean -f";
    else if ($2=="branch") print "git branch -D";
    else if ($2=="rebase") print "git rebase";
    else print "git " $2;
  }')
fi

# One-line rationale per op (for override error message)
_op_rationale() {
  case "$1" in
    "git stash pop"|"git stash drop"|"git stash apply")
      echo "stash ops can re-enact prior state from user-context or pop the wrong entry (ADR-055b, r5)";;
    "git reset")
      echo "mutates HEAD/index/worktree state and can erase another session's staged or uncommitted work";;
    "git pull --rebase")
      echo "rebases the current worktree and can reset/overwrite another agent's in-flight edits; use scripts/cos-git-sync.sh or a session branch";;
    "git checkout --")
      echo "working-tree discard of specific paths; no recovery if changes were not committed";;
    "git clean -f")
      echo "force-delete untracked files including generated state and WIP";;
    "git restore")
      echo 'discards working-tree changes (modern equivalent of `checkout --`)';;
    "git revert")
      echo "creates new commits that may conflict unexpectedly with in-flight work";;
    "git worktree")
      echo "worktree mutations can orphan sessions / detach HEAD in ways the OS does not track";;
    "git branch -D")
      echo "force-deletes branches with unmerged commits; recovery requires reflog lookup";;
    "git rebase")
      echo "rewrites local history and mutates the worktree; use an isolated session branch/worktree and explicit approval";;
    "git switch"|"git checkout branch/context")
      echo "changes the branch context where future commits land; announce the branch change or use scripts/cos-session-branch.sh with explicit operator approval";;
    "git push --force")
      echo "force-push rewrites remote history; can permanently destroy commits other collaborators depend on; use --force-with-lease for a safer alternative";;
    *" on main"|*" on master")
      echo "committing or pushing directly from a protected shared branch bypasses per-session isolation; create a session branch first with scripts/cos-session-branch.sh";;
    *)
      echo "destructive operation; irreversible without reflog recovery";;
  esac
}

_op_owning_adr() {
  case "$1" in
    "git pull --rebase"|"git rebase")
      echo "ADR-116 P3.2";;
    "git push --force")
      echo "ADR-055b";;
    *" on main"|*" on master")
      echo "ADR-003, ADR-055b";;
    *)
      echo "ADR-003, ADR-055b";;
  esac
}

_op_repair_command() {
  case "$FIRST_HIT_TYPE" in
    force_push)
      echo "git push --force-with-lease";;
    protected_branch_write)
      echo "bash scripts/cos-session-branch.sh --slug <task>";;
    branch_context_change)
      echo "announce current branch, target branch, reason, and rerun with --allow-branch-switch if approved";;
    *)
      # `git stash push -u` was suggested here for every destructive op. On a
      # shared checkout it is strictly worse than most of what it repairs: it
      # sweeps the ENTIRE working tree, including another session's untracked
      # and unstaged work, into a single entry, and ADR-055b r5 exists because
      # restoring such an entry re-enacts state nobody asked for. Scope the
      # advice to the file at hand and prefer the non-mutating inspection.
      echo "inspect with 'git status --porcelain' and 'git diff -- <path>' first; if you must park work, scope it: git stash push -u -m 'pre-destructive-git-<reason>' -- <path>";;
  esac
}

_print_standard_block_report() {
  local context="$1"
  local reason="$2"
  local owner_adr="$(_op_owning_adr "$OP_NAME")"
  local repair_command="$(_op_repair_command)"
  echo "Primitive: destructive-git-blocker" >&2
  echo "Policy: destructive-git hard-blocking guard" >&2
  echo "Input: Bash command" >&2
  echo "Owning ADR: $owner_adr" >&2
  echo "Evidence: op='$OP_NAME' context='$context' reason='$reason' command='$COMMAND'" >&2
  echo "Repair command: $repair_command" >&2
}

_git_primitive_target_ref() {
  case "${FIRST_HIT_TYPE:-}" in
    protected_branch_write) echo "protected-branch-${PROTECTED_BRANCH:-unknown}" ;;
    force_push) echo "git-push-force" ;;
    branch_context_change) echo "${SEMANTIC_OP_NAME:-branch-context-change}" ;;
    *) echo "${OP_NAME:-${FIRST_HIT_TYPE:-git-op}}" ;;
  esac
}

_git_emit_intervention() {
  primitive_intervention_emit \
    "destructive-git-blocker" \
    "hooks/destructive-git-blocker.sh" \
    "$1" \
    "$2" \
    "$(_git_primitive_target_ref)" \
    "$3" \
    "Bash" 2>/dev/null || true
}

# Escape command for JSON
esc_cmd=${COMMAND//\\/\\\\}
esc_cmd=${esc_cmd//\"/\\\"}
esc_cmd=$(echo "$esc_cmd" | head -c 500 | tr '\n\r' '  ')
esc_op=${OP_NAME//\"/\\\"}

# Phase-aware governance policy can demote known low-friction categories, but
# destructive-git remains a baseline blocker in all shipped phase policies.
if type cos_governance_policy_allows_block >/dev/null 2>&1 && ! cos_governance_policy_allows_block destructive-git; then
  cos_governance_policy_advisory_message "destructive-git-blocker" "destructive-git"
  _git_emit_intervention "warn" "destructive_git_policy_advisory" ".cognitive-os/metrics/git-op-blocks.jsonl"
  exit 0
fi

# ── Override / bypass detection (ADR-055b) ───────────────────────────────────
# An approval token is a deliberate human act, so it must be BARE shell text --
# in practice a trailing comment. Scanning the raw command instead let a commit
# message grant the approval: measured 2026-08-19,
#   git commit -m "docs: usar --allow-destructive con cuidado"
# passed the guard. Writing ABOUT the flag authorised the operation, which is
# the same false-positive class _strip_commit_message_args already handles on
# the detection side -- only here it failed open instead of closed.
#
# Quoted spans are removed for the same reason: `echo "... --allow-destructive
# ..."` is text, not an approval. Stripping can only remove grants, never
# manufacture one, so the error direction is closed.
_approval_scan_text() {
  local text
  text=$(_strip_commit_message_args "$COMMAND")
  text=$(printf '%s' "$text" | sed 's/"[^"]*"//g')
  text=$(printf '%s' "$text" | sed "s/'[^']*'//g")
  printf '%s' "$text"
}

# Per-command override: `--allow-destructive` token, bare, outside quotes
_has_allow_flag() {
  # Match --allow-destructive as a whole token (surrounded by whitespace or edges)
  _approval_scan_text | grep -Eq '(^|[[:space:]])--allow-destructive($|[[:space:]])'
}

# Per-command override for force-push specifically: `--allow-force-push`
_has_allow_force_push_flag() {
  _approval_scan_text | grep -Eq '(^|[[:space:]])--allow-force-push($|[[:space:]])'
}

_has_allow_main_branch_flag() {
  _approval_scan_text | grep -Eq '(^|[[:space:]])--allow-main-branch($|[[:space:]])'
}

_has_allow_branch_switch_flag() {
  _approval_scan_text | grep -Eq '(^|[[:space:]])--allow-branch-switch($|[[:space:]])'
}

# SO-internal bypass contexts (not user-initiated destructive ops)
_is_bypass_context() {
  [ "${CI:-}" = "1" ]                      && return 0
  [ "${CI:-}" = "true" ]                   && return 0
  [ -n "${PYTEST_CURRENT_TEST:-}" ]        && return 0
  [ "${COS_GIT_BYPASS:-}" = "1" ]          && return 0
  type _cos_bypass_list_contains >/dev/null 2>&1 && _cos_bypass_list_contains destructive_git_bypass && return 0
  return 1
}

# Session-wide override
_has_session_override() {
  type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows destructive_git && return 0
  return 1
}

_has_main_branch_override() {
  type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows main_branch_write && return 0
  _has_allow_main_branch_flag && return 0
  return 1
}

_has_branch_switch_override() {
  type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows branch_switch && return 0
  _has_allow_branch_switch_flag && return 0
  return 1
}

# ── ADR-116 P3.2: WIP-guard override helpers ─────────────────────────────────
# COS_ALLOW_RESET_OVER_WIP=1 explicitly allows the op over WIP, logs the bypass
# to BYPASS_LOG with the WIP file list for forensic trail.
_has_wip_reset_override() {
  type cos_bypass_allows >/dev/null 2>&1 && cos_bypass_allows reset_over_wip && return 0
  return 1
}

# COS_AUTO_STASH_BEFORE_RESET=1 auto-stashes WIP before allowing the op.
# Off by default — operator must explicitly opt in.
_wants_auto_stash() {
  [ "${COS_AUTO_STASH_BEFORE_RESET:-}" = "1" ] && return 0
  return 1
}

# Bypass context — allow silently, log as bypassed.
# NOTE: bypass does NOT apply when an agent context is active. Agents running
# under pytest/CI must still be blocked; otherwise a malicious or buggy sub-agent
# could exploit the test harness env to destroy state.
if _is_bypass_context && ! _git_blocker_is_agent_context; then
  ENTRY=$(printf '{"timestamp":"%s","event":"bypassed","reason":"so_internal_context","op":"%s","command":"%s"}' \
    "$TIMESTAMP" "$esc_op" "$esc_cmd")
  safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
  _git_emit_intervention "allow" "so_internal_context" ".cognitive-os/metrics/git-op-blocks.jsonl"
  exit 0
fi

# Explicit override — allow with audit log
if _has_session_override || _has_allow_flag || _has_allow_force_push_flag || { [ "$FIRST_HIT_TYPE" = "protected_branch_write" ] && _has_main_branch_override; } || { [ "$FIRST_HIT_TYPE" = "branch_context_change" ] && _has_branch_switch_override; }; then
  override_reason="session_env"
  _has_allow_flag && override_reason="inline_flag"
  _has_allow_force_push_flag && override_reason="inline_flag_force_push"
  if [ "$FIRST_HIT_TYPE" = "protected_branch_write" ] && _has_main_branch_override; then
    override_reason="main_branch_override"
  fi
  if [ "$FIRST_HIT_TYPE" = "branch_context_change" ] && _has_branch_switch_override; then
    override_reason="branch_switch_override"
  fi
  echo "" >&2
  echo "=== DESTRUCTIVE-GIT-BLOCKER: OVERRIDE ACCEPTED ===" >&2
  if [ "$FIRST_HIT_TYPE" = "branch_context_change" ]; then
    echo "Branch context change '$OP_NAME' allowed via $override_reason override." >&2
  else
    echo "Destructive op '$OP_NAME' allowed via $override_reason override." >&2
  fi
  echo "Command: $COMMAND" >&2
  echo "" >&2
  ENTRY=$(printf '{"timestamp":"%s","event":"override","reason":"%s","agent_id":"%s","op":"%s","command":"%s"}' \
    "$TIMESTAMP" "$override_reason" "$AGENT_ID" "$esc_op" "$esc_cmd")
  safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
  _git_emit_intervention "allow" "destructive_git_override" ".cognitive-os/metrics/git-op-blocks.jsonl"
  exit 0
fi

# ── ADR-116 P3.2: WIP-guard check ────────────────────────────────────────────
# For WIP-guard ops (pull --rebase, rebase, fetch+reset chain), check for
# uncommitted changes and either block with diagnostics or invoke bypass paths.
if [ "$IS_WIP_GUARD_OP" = "1" ] && _has_wip; then
  WIP_FILES=$(_wip_file_list)
  WIP_JSON=$(_wip_files_json_array)
  esc_wip_json=$(echo "$WIP_JSON" | head -c 1000 | tr '\n\r' '  ')

  # Phase 2: COS_ALLOW_RESET_OVER_WIP=1 — operator explicitly accepts the risk.
  if _has_wip_reset_override; then
    echo "" >&2
    echo "=== DESTRUCTIVE-GIT-BLOCKER: WIP-GUARD BYPASS ACCEPTED ===" >&2
    echo "Op '$OP_NAME' allowed over uncommitted WIP via COS_ALLOW_RESET_OVER_WIP=1." >&2
    echo "WIP at time of bypass (top 10 files):" >&2
    echo "$WIP_FILES" >&2
    echo "Command: $COMMAND" >&2
    echo "WARNING: any unsaved changes listed above will be lost if the op runs." >&2
    echo "" >&2
    BYPASS_ENTRY=$(printf \
      '{"timestamp":"%s","event":"wip_guard_bypass","op":"%s","command":"%s","wip_files":%s,"bypass_reason":"COS_ALLOW_RESET_OVER_WIP","agent_id":"%s"}' \
      "$TIMESTAMP" "$esc_op" "$esc_cmd" "$esc_wip_json" "$AGENT_ID")
    safe_jsonl_append "$BYPASS_LOG" "$BYPASS_ENTRY" 2>/dev/null || true
    _git_emit_intervention "allow" "wip_guard_bypass" ".cognitive-os/metrics/destructive-git-bypass.jsonl"
    exit 0
  fi

  # Phase 3: COS_AUTO_STASH_BEFORE_RESET=1 — auto-stash WIP then allow.
  if _wants_auto_stash; then
    STASH_MSG="auto-pre-reset-$TIMESTAMP"
    echo "" >&2
    echo "=== DESTRUCTIVE-GIT-BLOCKER: AUTO-STASH BEFORE RESET ===" >&2
    echo "COS_AUTO_STASH_BEFORE_RESET=1 — stashing WIP before '$OP_NAME'." >&2
    echo "WIP files being stashed (top 10):" >&2
    echo "$WIP_FILES" >&2
    STASH_OUTPUT=$(git -C "$PROJECT_DIR" stash push -u -m "$STASH_MSG" 2>&1)
    STASH_RC=$?
    if [ "$STASH_RC" -eq 0 ]; then
      STASH_REF=$(git -C "$PROJECT_DIR" stash list --format='%gd' 2>/dev/null | head -1)
      echo "Stash created: $STASH_REF  (msg: $STASH_MSG)" >&2
      echo "To restore: inspect first, then git stash apply $STASH_REF; drop only after verifying restore." >&2
      echo "" >&2
      BYPASS_ENTRY=$(printf \
        '{"timestamp":"%s","event":"wip_guard_auto_stash","op":"%s","command":"%s","stash_ref":"%s","stash_msg":"%s","agent_id":"%s"}' \
        "$TIMESTAMP" "$esc_op" "$esc_cmd" "${STASH_REF:-unknown}" "$STASH_MSG" "$AGENT_ID")
      safe_jsonl_append "$BYPASS_LOG" "$BYPASS_ENTRY" 2>/dev/null || true
      _git_emit_intervention "allow" "wip_guard_auto_stash" ".cognitive-os/metrics/destructive-git-bypass.jsonl"
      exit 0
    else
      echo "ERROR: auto-stash failed (exit $STASH_RC): $STASH_OUTPUT" >&2
      echo "Blocking op to prevent data loss." >&2
      echo "" >&2
      # Fall through to WIP block below
    fi
  fi

  # No bypass — BLOCK with WIP diagnostics.
  echo "" >&2
  echo "=== DESTRUCTIVE-GIT-BLOCKER: WIP GUARD BLOCKED ===" >&2
  echo "BLOCKED: '$OP_NAME' was intercepted because the working tree has uncommitted changes." >&2
  echo "" >&2
  echo "Incident evidence (ADR-116 P3.2): a parallel session's 'git pull --rebase'" >&2
  echo "can silently wipe in-flight sub-agent edits via the reflog cascade." >&2
  echo "" >&2
  echo "Blocked command:" >&2
  echo "  $COMMAND" >&2
  echo "" >&2
  echo "Uncommitted WIP files (top 10 of $(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null | wc -l | tr -d ' ')):" >&2
  echo "$WIP_FILES" >&2
  echo "" >&2
  echo "Recovery options:" >&2
  echo "  a) Stash first:   git stash push -u -m 'pre-sync-wip-<reason>' && inspect the named stash before restore && $COMMAND" >&2
  echo "  b) Commit first:  git add -p && git commit -m 'wip: checkpoint' && $COMMAND" >&2
  # El bypass se resuelve por cos_bypass_allows, que lee COS_BYPASS del entorno Y
  # del archivo .cognitive-os/runtime/bypass.env en cada invocación. El archivo es
  # la única de las dos vías ejecutable a mitad de sesión: escribirlo y reintentar
  # funciona. Lo que este mensaje ofrecía antes era la variable como prefijo del
  # comando bloqueado —`COS_ALLOW_RESET_OVER_WIP=1 $COMMAND`— y esa forma no llega:
  # el hook es hijo del arnés y ya decidió cuando ese shell nace. Acá no se ensanchó
  # nada; la vía ya existía y el mensaje apuntaba a la otra.
  echo "  c) Allow bypass:  printf 'COS_BYPASS=reset_over_wip\\n' >> .cognitive-os/runtime/bypass.env" >&2
  echo "                    then retry: $COMMAND" >&2
  echo "     (o export COS_BYPASS=reset_over_wip antes de lanzar el arnés)" >&2
  echo "     (bypass is logged with the WIP file list to .cognitive-os/metrics/destructive-git-bypass.jsonl)" >&2
  # Esta ofrecia `COS_AUTO_STASH_BEFORE_RESET=1 $COMMAND`, y esa forma no llega:
  # el hook es hijo del arnes, no del shell del Bash tool. A diferencia de la
  # opcion c), esta NO recibe via en caliente a proposito: auto-stashear en un
  # checkout compartido por varias sesiones mueve trabajo ajeno, asi que darle
  # ruta desde adentro seria ensanchar la superficie justo donde mas duele.
  # Queda la unica vehiculo honesto: decidirlo ANTES de lanzar el arnes.
  echo "  d) Auto-stash:    export COS_AUTO_STASH_BEFORE_RESET=1, y relanzar el arnés" >&2
  echo "     (no toma efecto a mitad de sesión, y en un checkout compartido" >&2
  echo "      stashea también lo de las otras sesiones — preferí a) o b))" >&2
  echo "     (legacy opt-in; inspect the named stash and restore with explicit git stash apply <ref>)" >&2
  echo "" >&2
  echo "Reference: ADR-116 §P3.2, docs/06-Daily/reports/bug2-reset-cascade-forensics-2026-04-20.md" >&2
  if _git_blocker_is_agent_context; then
    _print_standard_block_report "agent" "wip_guard"
  else
    _print_standard_block_report "user" "wip_guard"
  fi
  echo "" >&2

  if _git_blocker_is_agent_context; then
    ENTRY=$(printf \
      '{"timestamp":"%s","event":"blocked","context":"agent","reason":"wip_guard","agent_id":"%s","op":"%s","command":"%s","wip_files":%s}' \
      "$TIMESTAMP" "$AGENT_ID" "$esc_op" "$esc_cmd" "$esc_wip_json")
    safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
    _git_emit_intervention "block" "wip_guard" ".cognitive-os/metrics/git-op-blocks.jsonl"
    exit 1
  fi

  ENTRY=$(printf \
    '{"timestamp":"%s","event":"blocked","context":"user","reason":"wip_guard","agent_id":"","op":"%s","command":"%s","wip_files":%s}' \
    "$TIMESTAMP" "$esc_op" "$esc_cmd" "$esc_wip_json")
  safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
  _git_emit_intervention "block" "wip_guard" ".cognitive-os/metrics/git-op-blocks.jsonl"
  exit 2
fi

# No override + no bypass → BLOCK (both agent and user context)
RATIONALE=$(_op_rationale "$OP_NAME")

if _git_blocker_is_agent_context; then
  # Agent context → BLOCK exit 1 (backward compat with existing tests)
  echo "" >&2
  echo "=== DESTRUCTIVE-GIT-BLOCKER: BLOCKED (agent context) ===" >&2
  if [ "$FIRST_HIT_TYPE" = "branch_context_change" ]; then
    echo "BLOCKED: branch context change '$OP_NAME' requires explicit user approval." >&2
  else
    echo "BLOCKED: destructive git op '$OP_NAME' requires explicit user approval." >&2
  fi
  echo "Rationale: $RATIONALE" >&2
  _print_standard_block_report "agent" "destructive_git_op"
  echo "Use Edit tool to revert specific lines manually, or escalate to the user." >&2
  echo "Agent: $AGENT_ID" >&2
  echo "Command: $COMMAND" >&2
  if [ "$FIRST_HIT_TYPE" = "branch_context_change" ]; then
    echo "Override: set COS_ALLOW_BRANCH_SWITCH=1 or append --allow-branch-switch to the command." >&2
  else
    echo "Override: set COS_ALLOW_DESTRUCTIVE_GIT=1 or append --allow-destructive to the command." >&2
  fi
  echo "Reference: ADR-003, ADR-055b (hooks/destructive-git-blocker.sh)" >&2
  echo "" >&2

  ENTRY=$(printf '{"timestamp":"%s","event":"blocked","context":"agent","agent_id":"%s","op":"%s","command":"%s"}' \
    "$TIMESTAMP" "$AGENT_ID" "$esc_op" "$esc_cmd")
  safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
  _git_emit_intervention "block" "destructive_git_op" ".cognitive-os/metrics/git-op-blocks.jsonl"

  exit 1
fi

# User context → BLOCK exit 2 (ADR-055b — elevation from warn-only)
echo "" >&2
echo "=== DESTRUCTIVE-GIT-BLOCKER: BLOCKED (user context) ===" >&2
if [ "$FIRST_HIT_TYPE" = "branch_context_change" ]; then
  echo "BLOCKED: branch context change '$OP_NAME' is blocked by default; silent switches make commits land on unexpected branches." >&2
else
  echo "BLOCKED: destructive git op '$OP_NAME' is blocked by default (ADR-055b, r5-stash-residue)." >&2
fi
echo "Rationale: $RATIONALE" >&2
_print_standard_block_report "user" "destructive_git_op"
echo "Command: $COMMAND" >&2
echo "" >&2
echo "To proceed, use ONE of:" >&2
echo "  1. Inline token:  append it as a trailing shell COMMENT, outside quotes:" >&2
echo "                      git reset --hard HEAD~1  # --allow-destructive" >&2
echo "                    Passed as a real argument git rejects it (exit 129)," >&2
echo "                    and one inside a -m message or any quoted string is" >&2
echo "                    text, not approval: it does NOT grant." >&2
if [ "$FIRST_HIT_TYPE" = "force_push" ]; then
  echo "     OR:           append --allow-force-push (force-push-specific bypass)" >&2
  echo "     SAFER:        use --force-with-lease instead of --force / -f" >&2
fi
if [ "$FIRST_HIT_TYPE" = "protected_branch_write" ]; then
  echo "     OR:           append --allow-main-branch, or export COS_ALLOW_MAIN_BRANCH_WRITE=1" >&2
  echo "     SAFER:        bash scripts/cos-session-branch.sh --slug <task>" >&2
  echo "                   Creates session/<id>-<task> without moving HEAD." >&2
  echo "                   Do NOT add --switch on a checkout shared by several" >&2
  echo "                   sessions: it runs git switch on the whole working" >&2
  echo "                   tree, so every other session changes branch too." >&2
fi
if [ "$FIRST_HIT_TYPE" = "branch_context_change" ]; then
  echo "     OR:           append --allow-branch-switch, or export COS_ALLOW_BRANCH_SWITCH=1" >&2
  echo "     SAFER:        announce previous branch, target branch, reason, and expected commit destination first" >&2
fi
echo "  2. Session env:   export COS_ALLOW_DESTRUCTIVE_GIT=1 in the environment" >&2
echo "                    that LAUNCHES the harness. A VAR=1 <command> prefix" >&2
echo "                    does not reach this hook -- it runs as its own process." >&2
echo "" >&2
echo "Reference: docs/02-Decisions/adrs/ADR-055b-destructive-git-block.md" >&2
echo "" >&2

ENTRY=$(printf '{"timestamp":"%s","event":"blocked","context":"user","agent_id":"","op":"%s","command":"%s"}' \
  "$TIMESTAMP" "$esc_op" "$esc_cmd")
safe_jsonl_append "$BLOCKS_LOG" "$ENTRY" 2>/dev/null || true
_git_emit_intervention "block" "destructive_git_op" ".cognitive-os/metrics/git-op-blocks.jsonl"

exit 2
