#!/usr/bin/env bash
# SCOPE: both
# PreToolUse guard: blocks writes to agent control-plane config unless explicitly approved.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/common.sh"
[ -f "$(dirname "${BASH_SOURCE[0]}")/_lib/safe-jsonl.sh" ] && source "$(dirname "${BASH_SOURCE[0]}")/_lib/safe-jsonl.sh"
[ -f "$(dirname "${BASH_SOURCE[0]}")/_lib/primitive-intervention.sh" ] && source "$(dirname "${BASH_SOURCE[0]}")/_lib/primitive-intervention.sh"
[ -f "$(dirname "${BASH_SOURCE[0]}")/_lib/governance-policy.sh" ] && source "$(dirname "${BASH_SOURCE[0]}")/_lib/governance-policy.sh"
check_disabled_env "protected-config-write-guard"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
POLICY="$PROJECT_DIR/manifests/protected-config-write-policy.yaml"
APPROVAL_ENV="COS_ALLOW_PROTECTED_CONFIG_WRITE"

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0

BYPASS_LOG="$PROJECT_DIR/.cognitive-os/metrics/protected-config-bypass.jsonl"

# ── Approval, and why it is readable from the command text ───────────────────
# The variable alone was unreachable from inside a session: this is a PreToolUse
# hook, so it runs in the harness environment, not the one a Bash command sets.
# `COS_ALLOW_PROTECTED_CONFIG_WRITE=1 <cmd>` set the variable for <cmd> and never
# for the hook that had already decided. The message below told operators to do
# something that could not be done, and the practical consequence was worse than
# a permissive gate: every authorised change went through `git apply`, which this
# guard does not inspect and which leaves no trace unless the author volunteers
# one. Measured 2026-08-18: four such writes in one session, each disclosed only
# by choice.
#
# So the token is now honoured in the command text as well, matching what
# destructive-git-blocker already does with --allow-destructive, and every grant
# is appended to BYPASS_LOG. This does not widen the hole; it replaces an
# invisible bypass with a recorded one. A determined agent could already write
# through git apply, and nothing here changes that -- what changes is that the
# ordinary, authorised path now leaves a row behind.
_approval_granted() {
  [ "${COS_ALLOW_PROTECTED_CONFIG_WRITE:-0}" = "1" ] && { printf 'env'; return 0; }
  # Prefix position only, matched against the COMMAND rather than the payload.
  # Anywhere-in-the-text was the first attempt and it was wrong the same way this
  # guard's other defects were wrong: `echo COS_ALLOW_..._WRITE=1 note > hooks/x`
  # granted itself approval, so writing a report ABOUT the variable authorised a
  # write. An env assignment only means anything where the shell reads it as one.
  # Matching the raw payload was the second mistake -- there the command is nested
  # inside a JSON string, so a token at the true start of the command is preceded
  # by a quote and never matches its own anchor.
  local _cmd
  _cmd="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)" || _cmd=""
  [ -n "$_cmd" ] \
    && printf '%s' "$_cmd" \
      | grep -Eq '(^|[;&|(]|&&|\|\|)[[:space:]]*COS_ALLOW_PROTECTED_CONFIG_WRITE=1[[:space:]]' \
    && { printf 'command-token'; return 0; }
  return 1
}

if _APPROVAL_SOURCE="$(_approval_granted)"; then
  _TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // "unknown"' 2>/dev/null || echo unknown)"
  if declare -f safe_jsonl_append >/dev/null 2>&1; then
    safe_jsonl_append "$BYPASS_LOG" "$(printf '{"timestamp":"%s","source":"%s","tool":"%s","session":"%s"}' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$_APPROVAL_SOURCE" "$_TOOL" "${CLAUDE_SESSION_ID:-unknown}")" 2>/dev/null || true
  fi
  exit 0
fi

# --- Fast path: pure bash, zero subprocesses ---------------------------------
# This hook is registered with an EMPTY matcher, so it runs on every tool call,
# and the analyzer below costs a python3 start plus a yaml and a cos_lib import.
# A payload that does not even contain the literal prefix of one protected glob
# cannot name a protected path, so bail out before spending any subprocess.
# Degrades safe: if the policy file cannot be read, or a glob has no literal
# prefix to match on, the prefilter declines and the full analyzer runs.
prefilter_says_skip() {
  local line item in_globs=0 found=0
  [ -r "$POLICY" ] || return 1
  # The prefilter matches the RAW payload, before jq decodes it, so a JSON
  # \u escape would hide a protected path from it while jq still hands the
  # analyzer the decoded path. Any escape at all: decline and analyse.
  case "$INPUT" in *'\u'*) return 1 ;; esac
  # A patch applier takes its destinations from the patch, not from the command,
  # so a payload free of every protected literal can still write one. The
  # prefilter only ever sees the payload text, so it cannot rule that out:
  # decline and let the analyzer open the patch. This costs one python start on
  # any payload carrying the substring (dispatch, *.patch, prose about patches);
  # correctness over a subprocess, and the analyzer's verdict is unchanged.
  case "$INPUT" in
    *patch*|*"git apply"*|*"git am"*) return 1 ;;
  esac
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      protected_globs:*) in_globs=1; continue ;;
      [a-zA-Z_]*:*) in_globs=0; continue ;;
    esac
    [ "$in_globs" -eq 1 ] || continue
    case "$line" in
      *-\ *) item="${line#*- }" ;;
      *) continue ;;
    esac
    item="${item%%[*?]*}"   # literal prefix, up to the first wildcard
    item="${item%/}"        # a trailing slash prefilters identically
    [ -n "$item" ] && found=1 || return 1
    case "$INPUT" in *"$item"*) return 1 ;; esac
  done < "$POLICY"
  [ "$found" -eq 1 ] || return 1
  return 0
}
prefilter_says_skip && exit 0

command -v jq >/dev/null 2>&1 || exit 0

TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)"
case "$TOOL_NAME" in
  Edit|Write|MultiEdit|Bash) ;;
  *) exit 0 ;;
esac

RESULT="$({ PAYLOAD_JSON="$INPUT" PROJECT_DIR="$PROJECT_DIR" POLICY="$POLICY" python3 - <<'PY'
import fnmatch, json, os, re, sys
from pathlib import Path
try:
    import yaml
except Exception:
    yaml = None
payload=json.loads(os.environ.get('PAYLOAD_JSON','{}'))
project=Path(os.environ.get('PROJECT_DIR','.')).resolve()
policy_path=Path(os.environ.get('POLICY',''))
def default_policy():
    return {
      'protected_globs':['.claude/**','.codex/**','.cursor/**','.devin/**','.continue/**','mcp.json','.mcp/**','hooks/**','rules/**','skills/*/SKILL.md','manifests/*security*.yaml','manifests/credential-safe-scripts.yaml','manifests/runtime-env-flags.yaml'],
      'allowlisted_generated_outputs':['.cognitive-os/reports/**','.cognitive-os/metrics/**','.cognitive-os/sessions/**']
    }
if yaml and policy_path.exists():
    policy=yaml.safe_load(policy_path.read_text())
else:
    policy=default_policy()
PROTECTED=policy.get('protected_globs',[]) or []
ALLOWLISTED=policy.get('allowlisted_generated_outputs',[]) or []

def normalize(raw):
    p=Path(raw)
    full=p if p.is_absolute() else project/p
    try:
        rel=full.resolve().relative_to(project).as_posix()
    except Exception:
        rel=raw
    return rel

def is_protected(rel, raw=None):
    if any(fnmatch.fnmatch(rel, pat) for pat in ALLOWLISTED):
        return False
    for pat in PROTECTED:
        if fnmatch.fnmatch(rel, pat):
            return True
        # A '/**' glob must also protect the directory node itself, otherwise a
        # write INTO the tree naming only the directory carries no token that
        # any glob matches. Requiring a slash in the raw token keeps the bare
        # English word ('-k hooks') from being read as a path.
        if pat.endswith('/**') and rel == pat[:-3] and raw is not None and '/' in raw:
            return True
    return False

# --- Bash command analysis ---------------------------------------------------
# Design: fail closed per command segment. A segment that names a protected path
# is treated as a write unless its command word is a reader we can name and
# justify. Growing a denylist of write verbs is unwinnable -- the next tool that
# ships is a hole by default. Here the next tool that ships is blocked by
# default, and the list that must stay correct is the readers list, which is
# small, boring, and changes almost never.

WRAPPERS={'sudo','doas','env','command','builtin','nohup','time','nice','ionice',
          'stdbuf','xargs','exec','if','then','else','elif','while','until','do','!','{','('}

# Readers: cannot create or modify a file whatever flags they are handed.
PURE_READERS={
 'cat','head','tail','wc','nl','od','xxd','hexdump','strings','file','stat',
 'ls','tree','du','df','basename','dirname','readlink','realpath','pwd','cd',
 'echo','printf','true','false','test','[','[[',
 'cmp','diff','colordiff','less','more','column','uniq','cut','tr','rev','fold',
 'comm','join','paste','tac','base64','date','seq','which','type',
 'grep','egrep','fgrep','rg','ag','ack','jq','shasum','md5','md5sum','sha1sum',
 'sha256sum','cksum','for','select','case','in','esac','done','fi','shellcheck',
}

def veto_sed(ws):
    for t in ws:
        if t=='--in-place' or t.startswith('--in-place='):
            return True
        if t.startswith('-') and not t.startswith('--'):
            if 'i' in t[1:].split('.')[0]:   # -i, -i.bak, -ni
                return True
    return False

def veto_awk(ws):
    return any(t=='-i' or t.startswith('-i') or t=='inplace'
               or t.startswith('--in-place') or t.startswith('--include') for t in ws)

def veto_find(ws):
    bad={'-delete','-exec','-execdir','-ok','-okdir','-fprint','-fprintf','-fls'}
    return any(t in bad for t in ws)

def veto_sort(ws):
    return any(t=='-o' or t.startswith('-o') or t.startswith('--output') for t in ws)

def veto_shell(ws):
    # An interpreter can do anything, so it is never a reader -- except with -n,
    # which parses and refuses to execute. -c would smuggle a program back in.
    return not (any(t=='-n' or (t.startswith('-') and not t.startswith('--') and 'n' in t[1:]) for t in ws)
                and not any(t=='-c' for t in ws))

def veto_yq(ws):
    return any(t in ('-i','--inplace','--in-place') for t in ws)

GIT_SAFE={'log','show','diff','status','blame','grep','ls-files','ls-tree','cat-file',
          'rev-parse','rev-list','describe','shortlog','whatchanged','annotate',
          'add','commit','push','fetch','ls-remote','check-ignore','stripspace'}
GIT_OPT_VALUE={'-C','-c','--git-dir','--work-tree','--exec-path','--namespace'}

def git_subcommand(ws):
    # The first non-option word is the subcommand. Global options come before it
    # and must not be mistaken for it; a few of them take a value.
    i=0
    while i < len(ws):
        t=ws[i]
        if t in GIT_OPT_VALUE:
            i+=2; continue
        if t.startswith('-'):
            i+=1; continue
        return t, ws[i+1:]
    return None, []

def veto_git(ws):
    sub, _ = git_subcommand(ws)
    return sub is None or sub not in GIT_SAFE

VETOED={'sed':veto_sed,'awk':veto_awk,'gawk':veto_awk,'mawk':veto_awk,
        'find':veto_find,'sort':veto_sort,'yq':veto_yq,'git':veto_git,
        'bash':veto_shell,'sh':veto_shell,'zsh':veto_shell,'dash':veto_shell,'ksh':veto_shell}

def is_reader(exe, rest):
    if exe in PURE_READERS:
        return True
    veto=VETOED.get(exe)
    if veto is not None:
        return not veto(rest)
    return False

HEREDOC=re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# Commands that consume a heredoc as DATA even though they can write. tee and dd
# copy stdin to the files named in their own arguments; neither ever interprets
# it. Those arguments are still judged by the ordinary segment scan, so
# `tee hooks/y.sh <<EOF` still blocks -- what stops is reading the prose of a
# report authored with `tee docs/r.md <<MD` as a program because it mentions a
# protected path. This set is used ONLY to classify a heredoc body; adding these
# to the readers list would have allowed the write itself.
HEREDOC_DATA_CONSUMERS={'tee','dd'}


def heredoc_terms_of(line):
    """[(terminator, body_is_program)] for one line, left to right.

    A heredoc belongs to the SEGMENT carrying its << , not to the first word of
    the LINE. `mkdir -p d && cat > d/f <<MD` feeds cat, and resolving the whole
    line resolved mkdir -- so a report authored that way had its prose read as a
    program, and every protected path it mentioned became a write. The same
    mistake ran the other way and cost more: `cat f && python3 <<PY` resolved to
    cat, so a real program was read as inert data and its writes were invisible.
    """
    out=[]
    for seg in split_segments(line):
        sexe, srest = resolve_exe(split_words(seg))
        seg_is_program = not (
            sexe is not None
            and (is_reader(sexe, srest) or sexe in HEREDOC_DATA_CONSUMERS)
        )
        for m in HEREDOC.finditer(seg):
            out.append((m.group(2), seg_is_program))
    return out


def strip_heredocs(cmd):
    # Whether a heredoc body is data or program depends on who is being fed.
    # Fed to a reader it is data, and reading it as commands turns the most
    # ordinary operation there is -- writing a file whose text happens to
    # mention a protected path -- into a false positive. Fed to an interpreter
    # it IS the program, so it is returned separately and scanned for paths.
    # Either way the header line stays, so a heredoc aimed at a protected path
    # is still caught by redirection.
    # The (header, body) pairs are returned as well: a heredoc fed to a patch
    # applier is neither data nor program, it is the patch, and the segment that
    # consumes it has to be able to find its own body.
    lines=cmd.split('\n'); out=[]; programs=[]; docs=[]; i=0
    while i < len(lines):
        line=lines[i]; out.append(line)
        terms=heredoc_terms_of(line)
        i+=1
        if not terms:
            continue
        for term, body_is_program in terms:
            body=[]
            while i < len(lines) and lines[i].strip() != term:
                body.append(lines[i]); i+=1
            if i < len(lines):
                i+=1
            body='\n'.join(body)
            docs.append((line, body))
            if body_is_program:
                programs.append(body)
    return '\n'.join(out), '\n'.join(programs), docs

SEPS=set(';\n&|')

def split_segments(cmd):
    # Quote-aware, so a separator inside a quoted argument does not invent a
    # bogus segment whose first word is a fragment of that argument.
    segs=[]; cur=[]; q=None; i=0; n=len(cmd)
    while i < n:
        c=cmd[i]
        if q is not None:
            if c=='\\' and q=='"' and i+1 < n:
                cur.append(c); cur.append(cmd[i+1]); i+=2; continue
            cur.append(c)
            if c==q: q=None
            i+=1; continue
        if c in "'\"":
            q=c; cur.append(c); i+=1; continue
        if c=='\\' and i+1 < n:
            cur.append(c); cur.append(cmd[i+1]); i+=2; continue
        if c in SEPS:
            segs.append(''.join(cur)); cur=[]
            while i < n and cmd[i] in SEPS: i+=1
            continue
        cur.append(c); i+=1
    segs.append(''.join(cur))
    return [s for s in segs if s.strip()]

def split_words(seg):
    words=[]; cur=[]; q=None; i=0; n=len(seg); quoted=False
    while i < n:
        c=seg[i]
        if q is not None:
            if c=='\\' and q=='"' and i+1 < n:
                cur.append(seg[i+1]); i+=2; continue
            if c==q:
                q=None; i+=1; continue
            cur.append(c); i+=1; continue
        if c in "'\"":
            q=c; quoted=True; i+=1; continue
        if c=='\\' and i+1 < n:
            cur.append(seg[i+1]); i+=2; continue
        if c.isspace():
            if cur or quoted: words.append(''.join(cur))
            cur=[]; quoted=False; i+=1; continue
        cur.append(c); i+=1
    if cur or quoted: words.append(''.join(cur))
    return words

ASSIGN=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')
TOKEN_PATHS=re.compile(r"[A-Za-z0-9_.~/-]+")
# Redirection targets are checked independently of the command word, because a
# redirection into a protected path can be driven by a perfectly innocent
# command word.
REDIRECT=re.compile(r"(?:&|\d+)?>>?\|?\s*(['\"]?)([^\s'\"<>&;|]+)\1")

SUBST=re.compile(r'\$\(([^()]*)\)')
# Process substitution is a command too, and it was never analysed. In
# `diff <(sed -i s/a/b/ hooks/x.sh) f` the outer word is diff -- a reader -- so
# the segment was waved through while sed rewrote a protected file. Measured
# 2026-08-19: two such forms passed the guard. Lifted into its own segment,
# exactly like $(...), the inner command is judged on its own merits.
PROCSUB=re.compile(r'[<>]\(([^()]*)\)')

def lift_substitutions(cmd):
    """Return (outer, [inner...]) with $(...) bodies lifted out.

    resolve_exe() skips a leading VAR= token so that `FOO=1 cmd` resolves to cmd.
    That is right for a value, and wrong for a substitution: in `n=$(wc -c < p)`
    the token is `n=$(wc`, which matches the assignment pattern, so the real
    command word is discarded and the next word (`-c`) is resolved as the
    executable. Not being a reader, the whole thing was judged a write -- which is
    how counting the bytes of a protected file came to be blocked as writing to it.

    Lifting the body out gives it its own segment, where `wc` resolves normally.
    Fails closed: an unbalanced or nested substitution is left in the outer text
    and still reaches the reader check as before.
    """
    inner = [m.group(1) for m in SUBST.finditer(cmd)]
    cmd = SUBST.sub(' ', cmd)
    inner += [m.group(1) for m in PROCSUB.finditer(cmd)]
    cmd = PROCSUB.sub(' ', cmd)
    return cmd, inner


WRITE_PRIMITIVES = (
    "write_text", "write_bytes", "writelines", ".write(", "os.replace",
    "os.rename", "os.remove", "os.unlink", "shutil.copy", "shutil.move",
    "shutil.rmtree", "mkdir", "touch", "truncate", "rmdir", "symlink_to",
    "chmod", "unlink(", "fdopen", "NamedTemporary",
)
# Deliberately absent: print() and >>. Both write to a stream rather than to a
# path, and a redirection of that stream into a protected file is already caught
# by REDIRECT on the header line. Including them made a heredoc that only prints
# -- the exact legitimate case this rule exists to admit -- block anyway.


_PAREN_OPEN=chr(40)
_GROUP_OPEN=chr(40)+chr(91)+chr(123)
_GROUP_CLOSE=chr(41)+chr(93)+chr(125)
_QUOTES=chr(34)+chr(39)
OPEN_CALL=re.compile(r'\bopen\s*' + re.escape(_PAREN_OPEN))
READ_ONLY_MODE=re.compile(r'^[rbtU]+$')
KWARG=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*\s*=[^=]')


def _balanced_args(text, start):
    """Argument text of the call whose opening bracket sits at `start`.

    None when the brackets do not balance, which the caller reads as a write:
    text this scanner cannot parse is not text it may clear.
    """
    depth=0; q=None; i=start; n=len(text)
    while i < n:
        c=text[i]
        if q is not None:
            if c=='\\':
                i+=2; continue
            if c==q:
                q=None
            i+=1; continue
        if c in _QUOTES:
            q=c; i+=1; continue
        if c in _GROUP_OPEN:
            depth+=1
        elif c in _GROUP_CLOSE:
            depth-=1
            if depth==0:
                return text[start+1:i]
        i+=1
    return None


def _split_top_level(argtext):
    """Split an argument list on commas that are not nested and not quoted."""
    out=[]; cur=[]; depth=0; q=None; i=0; n=len(argtext)
    while i < n:
        c=argtext[i]
        if q is not None:
            cur.append(c)
            if c=='\\' and i+1 < n:
                cur.append(argtext[i+1]); i+=2; continue
            if c==q:
                q=None
            i+=1; continue
        if c in _QUOTES:
            q=c; cur.append(c); i+=1; continue
        if c in _GROUP_OPEN:
            depth+=1
        elif c in _GROUP_CLOSE:
            depth-=1
        elif c==',' and depth==0:
            out.append(''.join(cur)); cur=[]; i+=1; continue
        cur.append(c); i+=1
    out.append(''.join(cur))
    return [a.strip() for a in out]


def _open_can_write(body):
    """False only when every open call in `body` provably opens for reading.

    Python's open defaults to mode r, and a mode built only from r, b, t and U
    cannot write. That is a property of the call, checkable rather than a guess
    about intent. Everything else is a write: a mode carrying w, a, x or + , a
    mode that is a variable or an expression, an os.open flag word, or a call
    whose brackets this scanner cannot balance.

    Before this, the bare substring open( counted as a write wherever it
    appeared, so json.load(open(SETTINGS)) -- reading the very file the guard
    exists to protect -- was blocked as writing to it. Measured 2026-08-19 over
    the session transcripts: that shape accounted for the largest single family
    of blocks on read-only work.
    """
    for m in OPEN_CALL.finditer(body):
        args=_balanced_args(body, m.end()-1)
        if args is None:
            return True
        parts=_split_top_level(args)
        mode=None
        if len(parts) >= 2 and not KWARG.match(parts[1]):
            mode=parts[1]
        for p in parts:
            if p.startswith('mode='):
                mode=p[5:].strip()
        if mode is None:
            if not args.strip():
                return True
            continue
        if len(mode) >= 2 and mode[0] in _QUOTES and mode[-1] == mode[0]:
            inner=mode[1:-1]
            if inner and READ_ONLY_MODE.match(inner):
                continue
        return True
    return False


def body_can_write(body):
    """True unless the program provably contains no write primitive.

    An interpreter can do anything, so naming a protected path inside one is a
    write we cannot rule out -- that is the right default and it stays. But a body
    with no write primitive at all cannot write, and the common legitimate case is
    exactly that: authoring a file under tests/ or docs/ whose text happens to
    mention a protected path. This is a property of the program, not a guess about
    intent, so it is checkable rather than heuristic. `print(` counts as a write
    because stdout can be redirected by the caller.
    """
    if any(tok in body for tok in WRITE_PRIMITIVES):
        return True
    return _open_can_write(body)


# --- Patch appliers: the destinations are inside the patch -------------------
# `git apply x.patch` names exactly one path in its text -- the patch -- while
# the paths it WRITES are two lines per hunk inside that file. Judging the
# command text alone meant any protected path could be written by a command
# whose text mentioned none; measured 2026-08-18, that was the path four
# authorised writes to hooks/** actually took, each disclosed only by choice.
#
# Deliberately not a diff parser. Three line shapes carry destinations:
#   `+++ b/PATH`   where the patch writes
#   `--- a/PATH`   where a deletion names its victim (and where -R writes)
#   `diff --git a/OLD b/NEW`  where a pure rename names both and no hunk exists
# Anything that does not carry at least one of them is not a patch we can read,
# and an unreadable patch is a block, not a guess.

# One house rule for everything below: every line inside this heredoc must
# carry an EVEN number of single and of double quotes. /bin/bash 3.2, which is
# what macOS ships and what this hook runs under, parses the body of a heredoc
# nested in a command substitution while looking for matching quotes, so an
# apostrophe in a comment is a syntax error at the END of the file -- and
# `bash -n` under a modern bash reports the file as clean. Hence QUOTE_CHARS
# below instead of the obvious literal.
QUOTE_CHARS=chr(34)+chr(39)

PATCH_APPLIERS={'patch','gpatch'}
PATCH_OPT_VALUE={'-i','--input','-o','--output','-d','--directory','-D','--ifdef',
                 '-r','--reject-file','-B','--prefix','-Y','--basename-prefix',
                 '-z','--suffix','-p','--strip','-F','--fuzz','-g','--get'}
PATCH_STDIN_ARGS={'-','/dev/stdin'}
# Double-quoted outer, escaped double quotes inside, exactly like HEREDOC
# above: a backslash does not escape anything inside single quotes, so a
# single-quoted pattern carrying \' flips the quote state of the whole heredoc
# for bash 3.2 and the command substitution never closes.
DIFF_HEADER=re.compile(r"^diff --git ['\"]?a/(.+?)['\"]? ['\"]?b/(.+?)['\"]?$")
# Plain stdin redirection only. A doubled marker is a heredoc, handled above,
# and a marker followed by an open paren is a process substitution, whose
# content is not on disk to be opened; the character class rejects both instead
# of matching them and discarding the result afterwards. It also carries an open
# AND a close paren, because of the same house rule as the quotes: parentheses
# inside this heredoc must balance or bash 3.2 loses the command substitution.
STDIN_REDIRECT=re.compile(r"(?<![<>])<(?!<)\s*(['\"]?)([^\s'\"<>&;|()]+)\1")

# Fail-closed findings that no glob can express: a patch we could not read, or
# text that is not a diff. They block on their own, with the reason attached.
FORCED_BLOCKS=[]

def patch_paths(text):
    """(paths, looks_like_a_unified_diff). Both sides, because -R writes the other."""
    paths=[]; seen=False
    for line in text.split('\n'):
        m=DIFF_HEADER.match(line.strip())
        if m:
            seen=True
            paths.extend([m.group(1), m.group(2)])
            continue
        if line.startswith('+++ ') or line.startswith('--- '):
            seen=True
            raw=line[4:].split('\t')[0].strip().strip(QUOTE_CHARS)
            if not raw or raw=='/dev/null':
                continue
            paths.append(raw)
            # -p1 is the default, so a/ and b/ are strip prefixes; -p0 keeps
            # them. Both readings are kept: an extra candidate can only add a
            # block, never remove one, and guessing the -p level would.
            if raw[:2] in ('a/','b/'):
                paths.append(raw[2:])
    return paths, seen

REDIR_OPS={'<','>','>>','>|','&>','&>>','2>','2>>','1>','1>>','<>'}

def positional_args(ws, opt_value=frozenset()):
    out=[]; i=0
    while i < len(ws):
        t=ws[i]
        if t in opt_value:
            i+=2; continue
        # A redirection is not an argument. Counting it as one is how
        # `patch -p1 < evil.patch` read the bare < as the file being patched and
        # concluded the destination was already named in the command.
        if t in REDIR_OPS:
            i+=2; continue
        if t and t[0] in '<>':
            i+=1; continue
        if t.startswith('-') and t != '-':
            i+=1; continue
        out.append(t); i+=1
    return out

def opt_value_of(ws, names):
    for i, t in enumerate(ws):
        for n in names:
            if t == n and i+1 < len(ws):
                return ws[i+1]
            if t.startswith(n+'='):
                return t[len(n)+1:]
    return None

def heredoc_body_for(seg, heredocs):
    for hline, body in heredocs:
        h=hline.strip()
        if h and h in seg:
            return body
    return None

def read_patch(label):
    p=Path(label) if os.path.isabs(label) else project/label
    try:
        return p.read_text(errors='replace')
    except Exception:
        FORCED_BLOCKS.append('unreadable patch source: %s' % label)
        return None

def patch_segment_targets(exe, rest, seg, heredocs):
    """Paths a patch-applying segment writes, read out of the patch itself."""
    if exe == 'git':
        sub, args = git_subcommand(rest)
        if sub not in ('apply','am'):
            return []
        if '--check' in args:
            # The documented dry run: it parses the patch and reports whether it
            # would apply, touching neither the working tree, the index, nor the
            # targets of the patch. It is allowed because it is the question an
            # operator asks BEFORE requesting approval, and a guard that blocks
            # the rehearsal is a guard people route around. -R/--reverse gets no
            # such pass -- reverting writes -- and needs no special case, because
            # both sides of every hunk are read anyway.
            return []
        sources=[a for a in positional_args(args) if a not in PATCH_STDIN_ARGS]
    elif exe in PATCH_APPLIERS:
        pos=positional_args(rest, PATCH_OPT_VALUE)
        if pos:
            # `patch ORIGINAL [patchfile]` writes ORIGINAL and nothing else, and
            # ORIGINAL is a word in the command, already judged by the ordinary
            # path. Only the form that takes its destinations from the patch
            # needs the patch opened.
            return []
        explicit=opt_value_of(rest, ('-i','--input'))
        sources=[explicit] if explicit else []
    else:
        return []

    texts=[]
    if sources:
        for f in sources:
            text=read_patch(f)
            if text is not None:
                texts.append((f, text))
    else:
        body=heredoc_body_for(seg, heredocs)
        if body is not None:
            texts.append(('<<heredoc', body))
        else:
            redir=stdin_redirect_target(seg)
            if redir:
                text=read_patch(redir)
                if text is not None:
                    texts.append((redir, text))
            else:
                # A pipe, a process substitution, or nothing: the content is not
                # on disk, so the destinations cannot be known and the command
                # is not allowed to proceed on the strength of that ignorance.
                FORCED_BLOCKS.append(
                    'patch source not inspectable: %s' % ' '.join([exe]+rest)[:80])
    out=[]
    for label, text in texts:
        paths, looks_like_patch = patch_paths(text)
        if not looks_like_patch:
            FORCED_BLOCKS.append('not a unified diff: %s' % label)
            continue
        out.extend(paths)
    return out

def stdin_redirect_target(seg):
    m=STDIN_REDIRECT.search(seg)
    return m.group(2) if m else None

def resolve_exe(ws):
    i=0
    while i < len(ws):
        t=ws[i]
        if ASSIGN.match(t):
            i+=1; continue
        base=os.path.basename(t)
        if base in WRAPPERS:
            i+=1; continue
        return base, ws[i+1:]
    return None, []

def bash_write_targets(command):
    if not isinstance(command, str) or not command.strip():
        return []
    cmd, program_body, heredocs = strip_heredocs(command)
    cmd, substituted = lift_substitutions(cmd)
    targets=[]
    for match in REDIRECT.finditer(cmd):
        targets.append(match.group(2))
    # A heredoc handed to an interpreter is code that runs with full authority;
    # any protected path named inside it is a write we cannot rule out.
    if body_can_write(program_body):
        for tok in program_body.split():
            for cand in TOKEN_PATHS.findall(tok):
                if is_protected(normalize(cand), cand):
                    targets.append(cand)
    for seg in list(split_segments(cmd)) + substituted:
        ws=split_words(seg)
        exe, rest = resolve_exe(ws)
        if exe is None:
            continue
        # Out-of-band destinations first: a patch applier writes targets that
        # are not among the words of this segment at all, so `hits` stays empty
        # and the segment gets waved through on the strength of naming nothing.
        targets.extend(patch_segment_targets(exe, rest, seg, heredocs))
        hits=[]
        for tok in rest:
            for cand in TOKEN_PATHS.findall(tok):
                if is_protected(normalize(cand), cand):
                    hits.append(cand)
        if not hits:
            continue
        if is_reader(exe, rest):
            continue
        targets.extend(hits)
    return targets

paths=[]
ti=payload.get('tool_input') or {}
if isinstance(ti, dict):
    for key in ('file_path','path','filePath'):
        if ti.get(key): paths.append(str(ti[key]))
    if isinstance(ti.get('edits'), list):
        for e in ti['edits']:
            if isinstance(e, dict) and e.get('file_path'):
                paths.append(str(e['file_path']))
    if payload.get('tool_name') == 'Bash':
        paths.extend(bash_write_targets(ti.get('command')))
blocked=[]
try:
    from cos_lib.policy_eval import evaluate_action
except Exception:
    evaluate_action=None
for raw in paths:
    rel=normalize(raw)
    if evaluate_action is not None:
        decision=evaluate_action(project, {'tool': payload.get('tool_name',''), 'file_path': rel})
        if decision.decision in {'block','deny'}:
            blocked.append(rel)
            continue
    if is_protected(rel, raw):
        blocked.append(rel)
blocked.extend(FORCED_BLOCKS)
seen=[]
for b in blocked:
    if b not in seen: seen.append(b)
print(json.dumps({'blocked':seen}, separators=(',',':')))
PY
} 2>/dev/null || printf '{"blocked":[]}')"
BLOCKED="$(printf '%s' "$RESULT" | jq -r '.blocked | join(", ")' 2>/dev/null || true)"
if [ -n "$BLOCKED" ]; then
  # Protected control-plane writes remain hard blocks in every phase.
  # Reconstruction can demote low-risk process gates, but not config mutation
  # that changes agent permissions/hooks/settings.
  echo "=== PROTECTED CONFIG WRITE GUARD: BLOCKED ===" >&2
  echo "Protected control-plane path(s): $BLOCKED" >&2
  echo "Approve, only after explicit human review, with either:" >&2
  echo "  $APPROVAL_ENV=1 <command>        (recorded in ${BYPASS_LOG#"$PROJECT_DIR"/})" >&2
  echo "  export $APPROVAL_ENV=1           (before launching the harness)" >&2
  if type primitive_intervention_emit >/dev/null 2>&1; then
    primitive_intervention_emit "protected-config-write-guard" "hooks/protected-config-write-guard.sh" "block" "protected_config_write" "protected-config" ".cognitive-os/metrics/protected-config-write-blocks.jsonl" "$TOOL_NAME" || true
  fi
  exit 2
fi
exit 0
