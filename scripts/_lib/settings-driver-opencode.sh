#!/usr/bin/env bash
# SCOPE: os-only
# settings-driver-opencode.sh — Project cognitive-os.yaml > OpenCode config.
#
# Emits:
#   - opencode.json: native OpenCode project config with COS plugin enabled.
#   - .opencode/cos-hooks.json: normalized COS hook projection consumed by
#     packages/opencode-adapter/plugins/cos-primitive-guard.js.
#   - .opencode/plugins/cos-primitive-guard.js: project-local plugin copy when
#     the COS source plugin is available.
#
# OpenCode plugin events used by COS:
#   - session.created        -> SessionStart
#   - tui.prompt.append      -> UserPromptSubmit
#   - tool.execute.before    -> PreToolUse
#   - tool.execute.after     -> PostToolUse
#   - session.idle           -> Stop
#   - session.compacted and experimental.session.compacting -> PreCompact
#
# SubagentStart remains limited: OpenCode task permissions are conceptually
# different from Claude Code SubagentStart lifecycle hooks.
set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
COS_SOURCE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -x "$COS_SOURCE_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$COS_SOURCE_DIR/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

if [ -z "${PROJECT_DIR:-}" ]; then
  if [ -f "cognitive-os.yaml" ] || [ -f "opencode.json" ] || [ -d ".opencode" ]; then
    PROJECT_DIR="$(pwd)"
  else
    PROJECT_DIR="$COS_SOURCE_DIR"
  fi
fi

CONFIG_FILE="$PROJECT_DIR/opencode.json"
HOOKS_FILE="$PROJECT_DIR/.opencode/cos-hooks.json"
PLUGIN_SOURCE="$COS_SOURCE_DIR/packages/opencode-adapter/plugins/cos-primitive-guard.js"
PLUGIN_TARGET="$PROJECT_DIR/.opencode/plugins/cos-primitive-guard.js"
PROFILE="${PROFILE:-default}"
case "$PROFILE" in
  default) PROFILE="maintainer" ;;
  core|maintainer|full) ;;
  *) PROFILE="maintainer" ;;
esac
export PROFILE

CHECK_MODE=false
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_MODE=true ;;
    --harness=*) : ;;
    *) ;;
  esac
done

_opencode_generate() {
  "$PYTHON_BIN" - "$PROJECT_DIR" "$COS_SOURCE_DIR" "$PROFILE" <<'PYEOF'
import json
import sys
from pathlib import Path

import yaml

project_dir = Path(sys.argv[1])
source_dir = Path(sys.argv[2])
profile = sys.argv[3]
config_path = project_dir / "cognitive-os.yaml"
source_config_path = source_dir / "cognitive-os.yaml"
config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
hooks = (config.get("harness") or {}).get("hooks") or {}
if not hooks and source_config_path.exists():
    source_config = yaml.safe_load(source_config_path.read_text(encoding="utf-8")) or {}
    hooks = (source_config.get("harness") or {}).get("hooks") or {}

EVENT_TO_OPENCODE = {
    "SessionStart": "session.created",
    "UserPromptSubmit": "tui.prompt.append",
    "PreToolUse": "tool.execute.before",
    "PostToolUse": "tool.execute.after",
    "Stop": "session.idle",
    "PreCompact": "session.compacted",
}
SUPPORTED_EVENTS = set(EVENT_TO_OPENCODE)

# Default/OpenCode interactive profile: run lifecycle hooks and keep Bash/tool
# runtime enforcement in the native JS guard. PROFILE=full records the complete
# supported hook projection for SO/release audits.
DEFAULT_LIFECYCLE_EVENTS = {"SessionStart", "UserPromptSubmit", "Stop", "PreCompact"}
DEFAULT_TOOL_HOT_PATH = {"hooks/bash-hot-path-dispatcher.sh"}
DEFAULT_HOOKS = {
    "hooks/error-learning.sh",
    "hooks/error-pipeline.sh",
    "hooks/result-truncator.sh",
    "hooks/session-init.sh",
    "hooks/host-tool-doctor.sh",
    "hooks/session-cleanup.sh",
    "hooks/user-prompt-capture.sh",
    "hooks/session-wrapup-trigger.sh",
    "hooks/session-heartbeat.sh",
    "hooks/memory-prefetch.sh",
    "hooks/clarification-gate.sh",
    "hooks/blast-radius.sh",
    "hooks/scope-proportionality.sh",
    "hooks/bash-hot-path-dispatcher.sh",
    "hooks/orchestrator-claim-gate.sh",
    "hooks/error-pattern-detector.sh",
    "hooks/auto-refine.sh",
    "hooks/auto-verify.sh",
    "hooks/dod-gate.sh",
    "hooks/trust-score-validator.sh",
    "hooks/skill-metrics-tracker.sh",
    "hooks/inject-phase-context.sh",
    "hooks/stack-detector.sh",
    "hooks/pre-compaction-flush.sh",
    "hooks/rate-limiter.sh",
    "hooks/large-file-advisor.sh",
    "hooks/secret-detector.sh",
    "hooks/content-policy.sh",
    "hooks/research-compliance-guard.sh",
    "hooks/doc-sync-detector.sh",
    "hooks/auto-checkpoint.sh",
    "hooks/claim-validator.sh",
    "hooks/completion-gate.sh",
    "hooks/clarification-interceptor.sh",
    "hooks/agent-checkpoint.sh",
    "hooks/session-sanity.sh",
    "hooks/confidentiality-enforcer.sh",
    "hooks/session-learning.sh",
    "hooks/crash-recovery.sh",
    "hooks/teammate-idle.sh",
    "hooks/task-created.sh",
    "hooks/task-completed.sh",
}

projected = []
for hook_id, entry in sorted(hooks.items()):
    if not isinstance(entry, dict):
        continue
    event = str(entry.get("event") or "")
    native = EVENT_TO_OPENCODE.get(event)
    script = str(entry.get("script") or "")
    if not native or not script:
        continue
    matcher = str(entry.get("matcher") or "")
    if profile != "full":
        if script not in DEFAULT_HOOKS:
            continue
        if event in {"PreToolUse", "PostToolUse"} and script not in DEFAULT_TOOL_HOT_PATH:
            continue
        if event not in DEFAULT_LIFECYCLE_EVENTS and script not in DEFAULT_TOOL_HOT_PATH:
            continue
    projected.append({
        "id": str(hook_id),
        "event": event,
        "native_event": native,
        "matcher": matcher,
        "script": script,
        "command": f"bash {script}",
    })

by_native = {}
for item in projected:
    by_native.setdefault(item["native_event"], []).append(item)

hooks_payload = {
    "schema_version": "cos-opencode-hooks.v1",
    "harness": "opencode",
    "profile": profile,
    "source": "cognitive-os.yaml:harness.hooks",
    "supported_events": sorted(SUPPORTED_EVENTS),
    "limited_events": {
        "SubagentStart": "OpenCode uses task permission semantics instead of a direct lifecycle hook",
        "PreCompact": "OpenCode docs expose session.compacted; older builds may use experimental.session.compacting",
    },
    "events": by_native,
}

opencode_config = {
    "$schema": "https://opencode.ai/config.json",
    "instructions": [
        "AGENTS.md",
        ".cognitive-os/rules/cos/RULES-COMPACT.md",
        ".cognitive-os/rules/cos/*.md",
        ".cognitive-os/skills/cos/*/SKILL.md",
    ],
    "plugin": [".opencode/plugins/cos-primitive-guard.js"],
    "mcp": {},
    "permission": {"bash": "ask", "edit": "ask"},
    "experimental": {
        "cognitive_os_hooks": ".opencode/cos-hooks.json",
    },
}

print(json.dumps({"opencode": opencode_config, "hooks": hooks_payload}, indent=2, sort_keys=True))
PYEOF
}

_write_outputs() {
  local payload="$1"
  mkdir -p "$(dirname "$CONFIG_FILE")" "$(dirname "$HOOKS_FILE")" "$(dirname "$PLUGIN_TARGET")"
  local payload_file
  payload_file="$(mktemp)"
  printf '%s\n' "$payload" > "$payload_file"
  "$PYTHON_BIN" - "$payload_file" "$CONFIG_FILE" "$HOOKS_FILE" <<'PYEOF'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
Path(sys.argv[2]).write_text(json.dumps(payload["opencode"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
Path(sys.argv[3]).write_text(json.dumps(payload["hooks"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
PYEOF
  rm -f "$payload_file"
  if [ -f "$PLUGIN_SOURCE" ]; then
    cp "$PLUGIN_SOURCE" "$PLUGIN_TARGET"
  fi
}

if [ "$SCRIPT_SOURCE" = "$0" ]; then
  generated="$(_opencode_generate)"
  if [ "$CHECK_MODE" = "true" ]; then
    if [ ! -f "$CONFIG_FILE" ] || [ ! -f "$HOOKS_FILE" ]; then
      echo "DRIFT: OpenCode projection missing ($CONFIG_FILE or $HOOKS_FILE)." >&2
      exit 1
    fi
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' EXIT
    tmp_config="$tmpdir/opencode.json"
    tmp_hooks="$tmpdir/cos-hooks.json"
    payload_file="$tmpdir/payload.json"
    printf '%s\n' "$generated" > "$payload_file"
    "$PYTHON_BIN" - "$payload_file" "$tmp_config" "$tmp_hooks" <<'PYEOF'
import json
import sys
from pathlib import Path
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
Path(sys.argv[2]).write_text(json.dumps(payload["opencode"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
Path(sys.argv[3]).write_text(json.dumps(payload["hooks"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
PYEOF
    "$PYTHON_BIN" - "$tmp_config" "$CONFIG_FILE" "$tmp_hooks" "$HOOKS_FILE" <<'PYEOF'
import json
import sys
from pathlib import Path
pairs = [(Path(sys.argv[1]), Path(sys.argv[2])), (Path(sys.argv[3]), Path(sys.argv[4]))]
for expected, actual in pairs:
    if json.loads(expected.read_text(encoding="utf-8")) != json.loads(actual.read_text(encoding="utf-8")):
        print(f"DRIFT detected: {actual}", file=sys.stderr)
        raise SystemExit(1)
print("OK: OpenCode projection is in sync with canonical harness.hooks")
PYEOF
    exit 0
  fi
  _write_outputs "$generated"
  hook_count=$("$PYTHON_BIN" -c "import json; print(sum(len(v) for v in json.load(open('$HOOKS_FILE'))['events'].values()))")
  echo "settings-driver-opencode: wrote $CONFIG_FILE and $HOOKS_FILE ($hook_count hook commands)"
fi
