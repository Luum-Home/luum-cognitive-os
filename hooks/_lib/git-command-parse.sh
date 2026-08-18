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
