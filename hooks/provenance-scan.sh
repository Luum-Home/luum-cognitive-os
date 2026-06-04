#!/usr/bin/env bash
# SCOPE: both
# provenance-scan.sh — block sensitive provenance/local-source leaks.
set -uo pipefail

[ "${COS_DISABLE_ALL_GOVERNANCE:-}" = "1" ] && exit 0
[ "${DISABLE_HOOK_PROVENANCE_SCAN:-}" = "true" ] && exit 0

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

mode="--staged"
if [ ! -d "$PROJECT_DIR/.git" ]; then
  mode=""
fi

if [ -f "$CONFIG_PATH" ]; then
  "$CLI_PATH" --config "$CONFIG_PATH" $mode >/tmp/cos-provenance-scan-hook.out 2>/tmp/cos-provenance-scan-hook.err
else
  "$CLI_PATH" $mode >/tmp/cos-provenance-scan-hook.out 2>/tmp/cos-provenance-scan-hook.err
fi
code=$?
if [ $code -ne 0 ]; then
  echo "BLOCKED: provenance-scan found sensitive provenance or local-source leakage." >&2
  cat /tmp/cos-provenance-scan-hook.err >&2 2>/dev/null || true
  cat /tmp/cos-provenance-scan-hook.out >&2 2>/dev/null || true
  exit 2
fi
exit 0
