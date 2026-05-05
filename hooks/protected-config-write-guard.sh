#!/usr/bin/env bash
# SCOPE: both
# PreToolUse guard: blocks writes to agent control-plane config unless explicitly approved.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/common.sh"
check_disabled_env "protected-config-write-guard"

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${COGNITIVE_OS_PROJECT_DIR:-$(pwd)}}"
POLICY="$PROJECT_DIR/manifests/protected-config-write-policy.yaml"
APPROVAL_ENV="COS_ALLOW_PROTECTED_CONFIG_WRITE"

INPUT="$(cat 2>/dev/null || true)"
[ -z "$INPUT" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0

TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)"
case "$TOOL_NAME" in
  Edit|Write|MultiEdit) ;;
  *) exit 0 ;;
esac

if [ "${COS_ALLOW_PROTECTED_CONFIG_WRITE:-0}" = "1" ]; then
  exit 0
fi

RESULT="$({ PAYLOAD_JSON="$INPUT" PROJECT_DIR="$PROJECT_DIR" POLICY="$POLICY" python3 - <<'PY'
import fnmatch, json, os, sys
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
      'protected_globs':['.claude/**','.codex/**','.cursor/**','.windsurf/**','.continue/**','mcp.json','.mcp/**','hooks/**','rules/**','skills/*/SKILL.md','manifests/*security*.yaml','manifests/credential-safe-scripts.yaml','manifests/runtime-env-flags.yaml'],
      'allowlisted_generated_outputs':['.cognitive-os/reports/**','.cognitive-os/metrics/**','.cognitive-os/sessions/**']
    }
if yaml and policy_path.exists():
    policy=yaml.safe_load(policy_path.read_text())
else:
    policy=default_policy()
paths=[]
ti=payload.get('tool_input') or {}
if isinstance(ti, dict):
    for key in ('file_path','path','filePath'):
        if ti.get(key): paths.append(str(ti[key]))
    if isinstance(ti.get('edits'), list):
        for e in ti['edits']:
            if isinstance(e, dict) and e.get('file_path'):
                paths.append(str(e['file_path']))
blocked=[]
for raw in paths:
    p=Path(raw)
    full=(p if p.is_absolute() else project/p).resolve()
    try:
        rel=full.relative_to(project).as_posix()
    except ValueError:
        rel=raw
    allowed=any(fnmatch.fnmatch(rel, pat) for pat in policy.get('allowlisted_generated_outputs',[]))
    protected=any(fnmatch.fnmatch(rel, pat) for pat in policy.get('protected_globs',[]))
    if protected and not allowed:
        blocked.append(rel)
print(json.dumps({'blocked':blocked}, separators=(',',':')))
PY
} 2>/dev/null || printf '{"blocked":[]}')"
BLOCKED="$(printf '%s' "$RESULT" | jq -r '.blocked | join(", ")' 2>/dev/null || true)"
if [ -n "$BLOCKED" ]; then
  echo "=== PROTECTED CONFIG WRITE GUARD: BLOCKED ===" >&2
  echo "Protected control-plane path(s): $BLOCKED" >&2
  echo "Set $APPROVAL_ENV=1 only after explicit human review." >&2
  exit 2
fi
exit 0
