#!/usr/bin/env bash
# DEPRECATED — renamed to token-budget-monitor.sh in commit 5e3c188.
# This shim keeps backward compat for any external callers that still
# invoke the old name. Produces one-time stderr warning and exits 0.
# Canonical: hooks/token-budget-monitor.sh (see also rules/rate-limit-protection.md).
_marker="${TMPDIR:-/tmp}/.cos-rate-limit-deprecation-warning"
if [ ! -f "$_marker" ]; then
  echo "[deprecated] rate-limit-protection.sh: use token-budget-monitor.sh" >&2
  touch "$_marker" 2>/dev/null || true
fi
exit 0
