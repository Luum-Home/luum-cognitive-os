#!/usr/bin/env bash
# SCOPE: both
# publication-safety.sh — project-configured public release safety bridge.
#
# No-ops unless a consumer project provides manifests/publication-safety.yaml
# or COS_PUBLICATION_SAFETY_REQUIRED=1 is set. When active, it runs the portable
# cos-publication-safety CLI and blocks risky publication commands if required
# project gates fail.
set -uo pipefail

[ "${COS_DISABLE_ALL_GOVERNANCE:-}" = "1" ] && exit 0
[ "${DISABLE_HOOK_PUBLICATION_SAFETY:-}" = "true" ] && exit 0

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
CONFIG_PATH="${COS_PUBLICATION_SAFETY_CONFIG:-$PROJECT_DIR/manifests/publication-safety.yaml}"
CLI_PATH="${COS_PUBLICATION_SAFETY_CLI:-$PROJECT_DIR/scripts/cos-publication-safety}"

input="$(cat 2>/dev/null || true)"
command=""
if command -v jq >/dev/null 2>&1; then
  command="$(printf '%s' "$input" | jq -r '.tool_input.command // .command // ""' 2>/dev/null || true)"
fi

required="${COS_PUBLICATION_SAFETY_REQUIRED:-0}"
if [ "$required" != "1" ]; then
  if [ ! -f "$CONFIG_PATH" ]; then
    exit 0
  fi
  first_line="$(printf '%s\n' "$command" | head -1)"
  case "$first_line" in
    *"gh release"*|*"goreleaser release"*|*"npm publish"*|*"twine upload"*|*"cargo publish"*|*"git push --tags"*|*"git push"*" main"*|*"git push"*" master"*)
      ;;
    *)
      exit 0
      ;;
  esac
fi

if [ ! -x "$CLI_PATH" ]; then
  # Installed consumer projects may not have copied this new primitive yet.
  exit 0
fi

"$CLI_PATH" --project-dir "$PROJECT_DIR" --config "$CONFIG_PATH" --json --strict >/tmp/cos-publication-safety-hook.json 2>/tmp/cos-publication-safety-hook.err
code=$?
if [ $code -ne 0 ]; then
  echo "BLOCKED: publication-safety gates did not pass." >&2
  if [ -s /tmp/cos-publication-safety-hook.json ]; then
    python3 - <<'PY' 2>/dev/null || cat /tmp/cos-publication-safety-hook.json >&2
import json
from pathlib import Path
payload=json.loads(Path('/tmp/cos-publication-safety-hook.json').read_text())
print(json.dumps({
  'status': payload.get('status'),
  'summary': payload.get('summary'),
  'receipt': '.cognitive-os/receipts/publication-safety/summary.json',
}, indent=2, sort_keys=True))
PY
  fi
  exit 2
fi

exit 0
