#!/usr/bin/env bash
# SCOPE: both
# hook-python-guard.sh -- tri-state runner for lib-importing hooks (ADR: hook-lib-projection-contract §3.3).
# Contract: 0=clean, 1=result (violations), 3=infra_error, other=infra_error.
#
# Usage:
#   source "$(dirname "$0")/_lib/hook-python-guard.sh"
#   cos_run_python_guarded "$OUTFILE" "$ERRFILE" -- python3 - "$ARG" <<PYEOF
#   ...
#   PYEOF
#   case "$COS_PY_STATE" in
#     clean) ... ;;
#     result) ... ;;
#     infra_error) ... fail open ... ;;
#   esac

cos_run_python_guarded() {
  local _outfile="$1"; shift
  local _errfile="$1"; shift
  [ "$1" = "--" ] && shift
  "$@" >"$_outfile" 2>"$_errfile"
  local _rc=$?
  case "$_rc" in
    0) COS_PY_STATE="clean" ;;
    1) COS_PY_STATE="result" ;;
    *) COS_PY_STATE="infra_error" ;;
  esac
  export COS_PY_STATE
  return "$_rc"
}
