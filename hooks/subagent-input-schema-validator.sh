#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: subagent-contracts, input-validation, adr-038
# PreToolUse hook on Agent — ADR-038 Wave 2 input schema validation.
# When an orchestrator prompt contains an INPUT SCHEMA: block, extracts it,
# builds a payload from COS_AGENT_PAYLOAD or the tool_input prompt field,
# runs validate_input(), and emits ESCALATION + permissionDecision=block on failure.

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
VALIDATOR="$PROJECT_DIR/lib/agent_input_validator.py"
METRICS="$PROJECT_DIR/.cognitive-os/metrics/subagent-input-schema-validator.jsonl"

INPUT=$(cat)
[ -n "$INPUT" ] || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$VALIDATOR" ] || exit 0

# Only act on Agent tool launches.
if command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // .tool // empty' 2>/dev/null || true)
  if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "Agent" ] && [ "$TOOL_NAME" != "task" ] && [ "$TOOL_NAME" != "delegate" ]; then
    exit 0
  fi
fi

TMP_IN=$(mktemp "${TMPDIR:-/tmp}/cos-schema-validator-in.XXXXXX.json")
TMP_OUT=$(mktemp "${TMPDIR:-/tmp}/cos-schema-validator-out.XXXXXX.json")
printf '%s' "$INPUT" > "$TMP_IN"

set +e
python3 - "$TMP_IN" "$PROJECT_DIR" "$METRICS" <<'PY' > "$TMP_OUT" 2>&1
import json
import os
import sys
import datetime

hook_json_path, project_dir, metrics_path = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, os.path.join(project_dir, 'lib'))

from agent_input_validator import validate_input, format_escalation, _BLOCK_RE  # noqa: E402

try:
    hook_data = json.loads(open(hook_json_path, encoding='utf-8').read())
except Exception as exc:
    # Malformed JSON — skip validation, let the launch proceed.
    sys.exit(0)

# Extract the prompt text from the tool input.
tool_input = hook_data.get('tool_input') or hook_data.get('input') or {}
if isinstance(tool_input, str):
    try:
        tool_input = json.loads(tool_input)
    except Exception:
        tool_input = {}

prompt_text = tool_input.get('prompt') or tool_input.get('description') or ''

# Check whether the prompt contains an INPUT SCHEMA block.
if not _BLOCK_RE.search(prompt_text):
    sys.exit(0)  # No schema declared — nothing to validate.

# Build the payload dict.
# Priority: COS_AGENT_PAYLOAD env var (JSON) > tool_input fields directly.
payload_env = os.environ.get('COS_AGENT_PAYLOAD', '').strip()
if payload_env:
    try:
        payload = json.loads(payload_env)
    except Exception:
        payload = {}
else:
    # Fall back: use any non-'prompt' keys from tool_input as the payload.
    payload = {k: v for k, v in tool_input.items() if k != 'prompt'}

ok, errors = validate_input(prompt_text, payload)

# Emit metrics entry regardless of outcome.
metric = {
    'timestamp': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
    'ok': ok,
    'error_count': len([e for e in errors if not e.startswith('UNKNOWN_TYPE')]),
    'payload_keys': list(payload.keys()),
}
try:
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    with open(metrics_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(metric, sort_keys=True) + '\n')
except Exception:
    pass

if not ok:
    real_errors = [e for e in errors if not e.startswith('UNKNOWN_TYPE')]
    escalation = format_escalation(real_errors)
    result = {
        'permissionDecision': 'block',
        'message': escalation,
        'errors': real_errors,
    }
    print(json.dumps(result))
    sys.exit(2)

sys.exit(0)
PY
RC=$?
set -e

if [ "$RC" -eq 2 ]; then
  python3 - "$TMP_OUT" <<'PY' >&2
import json, sys
try:
    payload = json.loads(open(sys.argv[1], encoding='utf-8').read())
except Exception:
    print(open(sys.argv[1], encoding='utf-8').read()[:2000])
    raise SystemExit(0)
print("ADR-038 INPUT SCHEMA VALIDATION BLOCK")
print(payload.get('message', 'Sub-agent launch blocked: required input fields missing or mistyped.'))
PY
  rm -f "$TMP_IN" "$TMP_OUT"
  exit 2
fi

rm -f "$TMP_IN" "$TMP_OUT"
exit 0
