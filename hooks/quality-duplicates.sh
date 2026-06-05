#!/usr/bin/env bash
# SCOPE: both
# Advisory duplicate-quality trigger for harness lifecycle shutdown/Stop.
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$(pwd)}}}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Avoid expensive no-op scans when the session left no local tracked changes.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ -z "$(git status --porcelain=v1 --untracked-files=no 2>/dev/null || true)" ]; then
    exit 0
  fi
fi

if [ -x ".cognitive-os/bin/cos-quality-duplicates" ]; then
  SCANNER=".cognitive-os/bin/cos-quality-duplicates"
elif [ -x "scripts/cos-quality-duplicates" ]; then
  SCANNER="scripts/cos-quality-duplicates"
else
  exit 0
fi

BASELINE=".cognitive-os/baselines/quality-duplicates.json"
MODE_ARGS=(--project-root . --json-out .cognitive-os/reports/quality-duplicates/latest.json --markdown .cognitive-os/reports/quality-duplicates/latest.md)
if [ -f "$BASELINE" ]; then
  MODE_ARGS+=(--baseline "$BASELINE" --fail-on-new)
else
  MODE_ARGS+=(--baseline "$BASELINE")
fi

if "$SCANNER" "${MODE_ARGS[@]}" >/dev/null 2>&1; then
  exit 0
fi

if [ "${COS_QUALITY_DUPLICATES_ENFORCE:-0}" = "1" ]; then
  echo "quality-duplicates: new duplicate findings detected; see .cognitive-os/reports/quality-duplicates/latest.md" >&2
  exit 2
fi

echo "quality-duplicates: advisory findings detected; see .cognitive-os/reports/quality-duplicates/latest.md" >&2
exit 0
