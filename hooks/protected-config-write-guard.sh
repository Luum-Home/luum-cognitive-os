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

if [ "${COS_ALLOW_PROTECTED_CONFIG_WRITE:-0}" = "1" ]; then
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

def veto_git(ws):
    # The first non-option word is the subcommand. Global options come before it
    # and must not be mistaken for it.
    i=0
    while i < len(ws):
        t=ws[i]
        if t in GIT_OPT_VALUE:
            i+=2; continue
        if t.startswith('-'):
            i+=1; continue
        return t not in GIT_SAFE
    return True

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

def strip_heredocs(cmd):
    # Whether a heredoc body is data or program depends on who is being fed.
    # Fed to a reader it is data, and reading it as commands turns the most
    # ordinary operation there is -- writing a file whose text happens to
    # mention a protected path -- into a false positive. Fed to an interpreter
    # it IS the program, so it is returned separately and scanned for paths.
    # Either way the header line stays, so a heredoc aimed at a protected path
    # is still caught by redirection.
    lines=cmd.split('\n'); out=[]; programs=[]; i=0
    while i < len(lines):
        line=lines[i]; out.append(line)
        terms=[m.group(2) for m in HEREDOC.finditer(line)]
        i+=1
        if not terms:
            continue
        exe, rest = resolve_exe(split_words(line))
        body_is_program = not (exe is not None and is_reader(exe, rest))
        for term in terms:
            body=[]
            while i < len(lines) and lines[i].strip() != term:
                body.append(lines[i]); i+=1
            if i < len(lines):
                i+=1
            if body_is_program:
                programs.append('\n'.join(body))
    return '\n'.join(out), '\n'.join(programs)

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
    return SUBST.sub(' ', cmd), inner


WRITE_PRIMITIVES = (
    "open(", "write_text", "write_bytes", "writelines", ".write(", "os.replace",
    "os.rename", "os.remove", "os.unlink", "shutil.copy", "shutil.move",
    "shutil.rmtree", "mkdir", "touch", "truncate", "rmdir", "symlink_to",
    "chmod", "unlink(", "fdopen", "NamedTemporary",
)
# Deliberately absent: print() and >>. Both write to a stream rather than to a
# path, and a redirection of that stream into a protected file is already caught
# by REDIRECT on the header line. Including them made a heredoc that only prints
# -- the exact legitimate case this rule exists to admit -- block anyway.


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
    return any(tok in body for tok in WRITE_PRIMITIVES)


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
    cmd, program_body = strip_heredocs(command)
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
  echo "Set $APPROVAL_ENV=1 only after explicit human review." >&2
  if type primitive_intervention_emit >/dev/null 2>&1; then
    primitive_intervention_emit "protected-config-write-guard" "hooks/protected-config-write-guard.sh" "block" "protected_config_write" "protected-config" ".cognitive-os/metrics/protected-config-write-blocks.jsonl" "$TOOL_NAME" || true
  fi
  exit 2
fi
exit 0
