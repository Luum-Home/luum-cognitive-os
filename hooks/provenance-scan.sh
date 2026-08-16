#!/usr/bin/env bash
# SCOPE: both
# provenance-scan.sh — block sensitive provenance/local-source leaks.
#
# SCOPE OF THE SCAN (fixed 2026-08-16, see
# docs/06-Daily/reports/provenance-scan-indice-compartido-2026-08-16.md):
#
# The hook used to always run the CLI with `--staged`, i.e. it judged the WHOLE
# shared index on every invocation. Under the concurrent-writer idiom this repo
# mandates (`git commit --only -- <my paths>`) that is the wrong set: the commit
# carries only my pathspec, but the guard blocked on whatever the other agents
# had left staged. It blocked four times on 2026-08-15 (hook-timing.jsonl,
# exit_code=2) and the "obvious" fix for the blocked agent — unstaging someone
# else's files — is exactly what the concurrent-writer norm forbids. The guard
# was pushing towards the violation.
#
# It now scans WHAT WILL TRAVEL, and nothing less:
#
#   Bash + `git commit --only -- a.md`  -> scans a.md (working-tree content,
#                                          which is what `--only`/<pathspec>
#                                          actually commits). Not b.md.
#   Bash + `git commit -a -m ...`       -> scans the index AND every tracked
#                                          modification, because all of it enters.
#   Bash + `git commit -m ...`          -> scans the whole index (unchanged).
#   Bash + `git commit --amend` (no pathspec) -> whole index (unchanged).
#   Edit/Write on file X                -> scans X only. An Edit tool call
#                                          creates no commit, so another agent's
#                                          staged file cannot travel through it;
#                                          it is still scanned at commit time by
#                                          this same hook via
#                                          hooks/bash-hot-path-dispatcher.sh.
#   anything unresolvable               -> whole index (fail closed).
#
# The narrowing is deliberately one-directional: when the plan cannot be proven
# (glob pathspec that expands to nothing, `git -C` into another repo, missing
# python3, malformed payload, unknown commit flag) the hook falls back to
# `--staged`. Scanning too much is a nuisance; scanning too little is a leak.
#
# KNOWN DEBT: the `git commit` tokenizer below is a SECOND parser of the same
# command string — hooks/git-commit-scope-guard.sh (commit 3045f71f8) has the
# authoritative one. They were not unified because the scope-guard's parser is
# an inline heredoc inside that hook, and extracting it into a shared library
# means writing hooks/git-commit-scope-guard.sh, which is protected config this
# change was not authorised to touch. Two parsers of one grammar drift; if the
# scope-guard's tokenizer is ever promoted to hooks/_lib/, this one must be
# deleted and replaced by it.
set -uo pipefail

[ "${COS_DISABLE_ALL_GOVERNANCE:-}" = "1" ] && exit 0
[ "${DISABLE_HOOK_PROVENANCE_SCAN:-}" = "true" ] && exit 0

INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(cat 2>/dev/null || true)
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
CLI_PATH="${COS_PROVENANCE_SCAN_CLI:-$PROJECT_DIR/.cognitive-os/bin/provenance-scan}"
if [ ! -x "$CLI_PATH" ] && [ -x "$PROJECT_DIR/scripts/provenance-scan" ]; then
  CLI_PATH="$PROJECT_DIR/scripts/provenance-scan"
fi
CONFIG_PATH="${COS_PROVENANCE_SCAN_CONFIG:-}"
if [ -z "$CONFIG_PATH" ]; then
  if [ -f "$PROJECT_DIR/.cognitive-os/provenance-scan.yaml" ]; then
    CONFIG_PATH="$PROJECT_DIR/.cognitive-os/provenance-scan.yaml"
  else
    CONFIG_PATH="$PROJECT_DIR/manifests/provenance-scan.yaml"
  fi
fi

[ -x "$CLI_PATH" ] || exit 0

# ── Plan the scan set ────────────────────────────────────────────────────────
# PLAN is a newline-separated list. First line is the mode:
#   STAGED           — scan the whole index (fail-closed default)
#   PATHS            — scan the listed repo-relative paths only
#   STAGED_AND_PATHS — both (the `git commit -a` case)
#   WORKTREE_ALL     — not a git repo; scan the tree (previous behaviour)
# Remaining lines are repo-relative paths.

PLAN="STAGED"

if [ ! -d "$PROJECT_DIR/.git" ] && [ ! -f "$PROJECT_DIR/.git" ]; then
  PLAN="WORKTREE_ALL"
elif [ -n "$INPUT" ] && command -v python3 >/dev/null 2>&1; then
  PLAN=$(HOOK_INPUT_JSON="$INPUT" COS_PS_ROOT="$PROJECT_DIR" python3 - <<'PYEOF' 2>/dev/null || printf 'STAGED\n'
import json, os, re, shlex, subprocess, sys

ROOT = os.environ.get("COS_PS_ROOT", ".")

try:
    data = json.loads(os.environ.get("HOOK_INPUT_JSON", "") or "{}")
except Exception:
    print("STAGED"); sys.exit(0)
if not isinstance(data, dict):
    print("STAGED"); sys.exit(0)

tool = str(data.get("tool_name") or "")
tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}


def rel(p):
    """Repo-relative path, or None when the path escapes the repo."""
    if not p:
        return None
    ap = p if os.path.isabs(p) else os.path.join(ROOT, p)
    try:
        r = os.path.relpath(os.path.realpath(ap), os.path.realpath(ROOT))
    except Exception:
        return None
    return None if r.startswith("..") else r


# ── Edit / Write: only the file being written can carry my leak ──────────────
if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
    fp = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    r = rel(str(fp))
    if r:
        print("PATHS"); print(r); sys.exit(0)
    print("STAGED"); sys.exit(0)

command = str(tool_input.get("command") or data.get("command") or "")
if tool and tool != "Bash":
    print("STAGED"); sys.exit(0)
if not command:
    print("STAGED"); sys.exit(0)

# ── Bash: tokenize the command and find every `git commit` invocation ────────
# NOTE: duplicated grammar — see the KNOWN DEBT note in the file header.
SEPARATORS = {"&&", "||", ";", "|", "&", "\n"}
VALUE_FLAGS = {
    "-m", "--message", "-C", "--reuse-message", "-F", "--file",
    "--author", "--date", "--trailer", "--cleanup", "--squash",
    "--fixup", "--pathspec-from-file", "-e", "--edit",
    "--allow-empty", "--allow-empty-message",
}
BOOL_FLAGS = {
    "--no-edit", "--amend", "--no-verify", "--signoff", "-s",
    "--verbose", "-v", "--quiet", "-q", "--dry-run", "-n",
    "--reset-author", "--no-gpg-sign", "--no-status",
    "--pathspec-file-nul", "--only", "--all", "-a",
    "--include", "-i", "--patch", "-p",
}
GLOBAL_VALUE_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
GLOBAL_BOOL_OPTS = {
    "--no-pager", "-P", "--paginate", "--bare", "--literal-pathspecs",
    "--no-replace-objects", "--no-optional-locks",
}


def pathspec_of(args):
    """(pathspec_tokens|None, commits_everything) for the tokens after `commit`."""
    everything = "-a" in args or "--all" in args
    out, skip_next, saw_ddash = [], False, False
    for tok in args:
        if skip_next:
            skip_next = False
            continue
        if tok == "--":
            saw_ddash = True
            continue
        if saw_ddash:
            out.append(tok)
            continue
        if tok in BOOL_FLAGS:
            continue
        if tok in VALUE_FLAGS:
            skip_next = True
            continue
        if re.match(r"^(--[\w-]+=.*|-S.+|-C.+)", tok):
            continue
        if re.match(r"^-[a-zA-Z]{2,}$", tok):
            continue
        if tok.startswith("-"):
            # Unknown flag: cannot tell whether it consumes the next token,
            # so the pathspec cannot be trusted. Fail closed.
            return None, everything
        out.append(tok)
    return out, everything


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
    for i, tok in enumerate(seg):
        if tok != "git" and not tok.endswith("/git"):
            continue
        j, cdir = i + 1, ""
        while j < len(seg):
            t = seg[j]
            if t in GLOBAL_VALUE_OPTS:
                if t == "-C" and j + 1 < len(seg):
                    cdir = seg[j + 1]
                j += 2
                continue
            if t in GLOBAL_BOOL_OPTS:
                j += 1
                continue
            if re.match(r"^--(git-dir|work-tree|namespace|exec-path)=", t):
                j += 1
                continue
            break
        if j < len(seg) and seg[j] == "commit":
            return seg[j + 1:], cdir
    return None


def expand(tokens):
    """Resolve pathspec tokens to repo-relative paths, or None if unprovable."""
    resolved = []
    for tok in tokens:
        r = rel(tok)
        if r and os.path.exists(os.path.join(ROOT, r)):
            resolved.append(r)
            continue
        # Glob / pathspec magic / deleted path: ask git what it matches.
        try:
            res = subprocess.run(
                ["git", "ls-files", "--cached", "--others", "--exclude-standard",
                 "-z", "--", tok],
                cwd=ROOT, capture_output=True, check=False, timeout=20,
            )
        except Exception:
            return None
        if res.returncode != 0:
            return None
        matched = [m for m in res.stdout.decode("utf-8", "replace").split("\0") if m]
        if not matched:
            # Nothing matched: either a deleted path (no content travels) or a
            # pathspec we failed to understand. Cannot prove it is the former.
            return None
        resolved.extend(matched)
    return resolved


try:
    tokens = shlex.split(command, posix=True)
except ValueError:
    print("STAGED"); sys.exit(0)

paths, saw_commit, everything = [], False, False
for seg in segments(tokens):
    found = find_commit(seg)
    if not found:
        continue
    saw_commit = True
    args, cdir = found
    if cdir and rel(cdir) not in ("", "."):
        print("STAGED"); sys.exit(0)   # commit into another repo: unprovable here
    spec, seg_everything = pathspec_of(args)
    if seg_everything:
        everything = True
    if spec is None:
        print("STAGED"); sys.exit(0)
    if not spec:
        if not seg_everything:
            print("STAGED"); sys.exit(0)   # bare commit: the whole index enters
        continue
    resolved = expand(spec)
    if resolved is None:
        print("STAGED"); sys.exit(0)
    paths.extend(resolved)

if not saw_commit:
    print("STAGED"); sys.exit(0)

if everything:
    # `git commit -a` takes the index PLUS every tracked modification.
    try:
        res = subprocess.run(["git", "diff", "--name-only", "-z"], cwd=ROOT,
                             capture_output=True, check=False, timeout=20)
        if res.returncode != 0:
            print("STAGED"); sys.exit(0)
        paths.extend(m for m in res.stdout.decode("utf-8", "replace").split("\0") if m)
    except Exception:
        print("STAGED"); sys.exit(0)
    print("STAGED_AND_PATHS")
else:
    print("PATHS")

seen = set()
for p in paths:
    if p not in seen and os.path.isfile(os.path.join(ROOT, p)):
        seen.add(p)
        print(p)
PYEOF
  )
  [ -n "$PLAN" ] || PLAN="STAGED"
fi

MODE_LINE="${PLAN%%$'\n'*}"
PLAN_REST=""
case "$PLAN" in
  *$'\n'*) PLAN_REST="${PLAN#*$'\n'}" ;;
esac

SCAN_PATHS=()
if [ "$MODE_LINE" = "PATHS" ] || [ "$MODE_LINE" = "STAGED_AND_PATHS" ]; then
  if [ -n "$PLAN_REST" ]; then
    while IFS= read -r line; do
      [ -n "$line" ] && SCAN_PATHS+=("$line")
    done <<< "$PLAN_REST"
  fi
  # A PATHS plan with nothing left to scan means nothing with content travels.
  if [ "$MODE_LINE" = "PATHS" ] && [ ${#SCAN_PATHS[@]} -eq 0 ]; then
    exit 0
  fi
fi

# ── Run the scan ─────────────────────────────────────────────────────────────

OUT_FILE=/tmp/cos-provenance-scan-hook.out
ERR_FILE=/tmp/cos-provenance-scan-hook.err
: >"$OUT_FILE" 2>/dev/null || true
: >"$ERR_FILE" 2>/dev/null || true
code=0

_run_cli() {
  local cli_args=()
  [ -f "$CONFIG_PATH" ] && cli_args+=(--config "$CONFIG_PATH")
  cli_args+=("$@")
  "$CLI_PATH" ${cli_args[@]+"${cli_args[@]}"} >>"$OUT_FILE" 2>>"$ERR_FILE"
}

case "$MODE_LINE" in
  WORKTREE_ALL)
    _run_cli || code=$?
    ;;
  PATHS)
    _run_cli "${SCAN_PATHS[@]}" || code=$?
    ;;
  STAGED_AND_PATHS)
    _run_cli --staged || code=$?
    if [ ${#SCAN_PATHS[@]} -gt 0 ]; then
      _run_cli "${SCAN_PATHS[@]}" || code=$?
    fi
    ;;
  *)
    _run_cli --staged || code=$?
    ;;
esac

if [ $code -ne 0 ]; then
  echo "BLOCKED: provenance-scan found sensitive provenance or local-source leakage." >&2
  cat "$ERR_FILE" >&2 2>/dev/null || true
  cat "$OUT_FILE" >&2 2>/dev/null || true
  exit 2
fi
exit 0
