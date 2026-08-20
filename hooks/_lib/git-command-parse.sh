#!/usr/bin/env bash
# SCOPE: both
# Canonical parse of a `git` invocation that carries global options.
#
# Why this file exists: `git -C <dir> commit`, `git --no-pager commit` and
# `git --git-dir=X --work-tree=Y commit` are the same operation as
# `git commit`, but a regex that demands literal adjacency between `git` and
# the subcommand sees none of them. That defect was closed once inside
# hooks/bash-hot-path-dispatcher.sh (f44556c48); the gates below it kept the
# same defect in their own regexes, so the dispatcher now reaches them and they
# exit early on their own account.
#
# Rather than copy the option list into each gate -- the repo already had three
# parsers of this grammar and a written expectation that they would diverge --
# the list and the matcher live here, once.
#
# Two consumers, one source of truth:
#   - bash gates                 -> cos_git_matches_subcommand
#   - gates with inline python   -> read $COS_GIT_GLOBAL_OPTS from the env.
#     The alternation is deliberately free of POSIX classes such as
#     [[:space:]], which python's `re` does not support, so the same string is
#     valid in both engines.
#
# Known limit, inherited from the dispatcher on purpose: the option run is
# matched as `[^|&;]*`, not parsed, so `git -C /r log --grep commit` matches the
# `commit` alternation. It over-matches (a gate runs that need not have), it
# never under-matches. Anyone who needs exactness should reuse the shlex
# tokenizer in hooks/destructive-git-blocker.sh instead of widening this.

# Git global options that may sit between `git` and the subcommand.
# Ported from hooks/git-commit-scope-guard.sh (3045f71f8) by way of
# hooks/bash-hot-path-dispatcher.sh (f44556c48); this is now the canonical copy.
COS_GIT_GLOBAL_OPTS='-C|-c|-P|--no-pager|--paginate|--git-dir|--work-tree|--namespace|--exec-path|--bare|--literal-pathspecs|--no-replace-objects|--no-optional-locks'
export COS_GIT_GLOBAL_OPTS

# cos_git_matches_subcommand <command> <subcommand-alternation>
# Returns 0 when <command> invokes `git <sub>`, with or without global options.
cos_git_matches_subcommand() {
  local cmd="$1" subs="$2"
  printf '%s' "$cmd" \
    | grep -Eq "(^|[|&;[:space:]])git[[:space:]]+($subs)([[:space:]]|$)" && return 0
  # Hot path: the second grep is only paid by a command that has a dash glued
  # to `git`. `ls -la`, `echo`, `git status` and `git commit -m x` never do.
  case "$cmd" in
    *"git -"*) ;;
    *) return 1 ;;
  esac
  printf '%s' "$cmd" \
    | grep -Eq "(^|[|&;[:space:]])git[[:space:]]+(${COS_GIT_GLOBAL_OPTS})[^|&;]*[[:space:]]($subs)([[:space:]]|$)"
}

# cos_git_commit_pathspec <command>
# Imprime, una por línea, las rutas que un `git commit` limita explícitamente
# con `-- <paths>`. Silencio (y exit 1) cuando el commit no lleva pathspec.
#
# POR QUÉ IMPORTA. `git commit -- a b` commitea *solamente* a y b: lo demás que
# esté en el índice no entra. Un gate que decide leyendo `git diff --cached`
# entero está mirando también lo que stageó la sesión de al lado, y bloquea a
# quien no tiene nada que ver. Con el pathspec, el disparador dice exactamente
# de qué se hace cargo, y el gate puede juzgarlo por eso y nada más.
#
# LÍMITE DELIBERADO. Sólo se reconoce el pathspec después de `--`, que es la
# única forma sin ambigüedad. `git commit a b` (sin `--`) existe pero se
# confunde con opciones, y adivinarlo sería peor que no atribuir: ante la duda
# el gate vuelve al índice entero, que es el comportamiento seguro. Un pathspec
# mal leído de MENOS bloquea a un inocente; leído de MÁS deja pasar algo sin
# revisar, y ese error no lo queremos.
cos_git_commit_pathspec() {
  local cmd="$1"
  printf '%s' "$cmd" | python3 -c '
import re, shlex, sys

cmd = sys.stdin.read()
# Un solo comando por vez: cortar en separadores de shell para no arrastrar el
# pathspec de un `git commit` a un comando encadenado que no lo tiene.
for seg in re.split(r"[|&;]+", cmd):
    if not re.search(r"(^|\s)git(\s|$)", seg):
        continue
    try:
        toks = shlex.split(seg)
    except ValueError:
        continue
    if "commit" not in toks or "--" not in toks:
        continue
    if toks.index("--") < toks.index("commit"):
        continue
    paths = [t for t in toks[toks.index("--") + 1:] if t]
    if paths:
        print("\n".join(paths))
        raise SystemExit(0)
raise SystemExit(1)
' 2>/dev/null
}
