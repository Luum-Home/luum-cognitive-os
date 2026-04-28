#!/usr/bin/env bash
# SCOPE: os-only
# cos-doctor-memory-lifecycle.sh — Verify portable memory lifecycle hooks.
#
# This doctor runs a synthetic Codex/Claude session against an isolated scratch
# project. It proves that the memory lifecycle can start, recover pending work,
# capture prompt/session state, and write session artifacts without relying on
# Claude-only environment variables.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OS_SOURCE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$OS_SOURCE_ROOT}}}"
source "$OS_SOURCE_ROOT/scripts/_lib/settings-driver.sh"

HARNESS="${COGNITIVE_OS_HARNESS:-$(cos_detect_harness "$PROJECT_ROOT")}"
STRICT=false
START_ENGRAM=true
KEEP_TMP="${COS_MEMORY_DOCTOR_KEEP_TMP:-0}"

usage() {
  cat <<'EOF'
cos doctor memory lifecycle — verify cross-session memory hooks

Usage:
  bash scripts/cos-doctor-memory-lifecycle.sh [--harness codex|claude] [--strict] [--skip-engram-start]

Checks:
  - active driver projects portable memory hooks for supported events
  - Engram launcher hook can run from a new session
  - pending tasks are detected/recovered by session-resume.sh
  - user prompts can be captured asynchronously
  - session learning, git context, and changelog artifacts are written
  - pre-compaction flush can emit the mandatory memory-save reminder

Exit codes:
  0  Core lifecycle checks passed; optional checks may warn.
  1  Core lifecycle checks failed, or warnings exist under --strict.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --harness)
      [ -z "${2:-}" ] && { echo "Error: --harness requires a value" >&2; exit 2; }
      HARNESS="$2"
      shift
      ;;
    --harness=*)
      HARNESS="${1#--harness=}"
      ;;
    --strict) STRICT=true ;;
    --skip-engram-start) START_ENGRAM=false ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown flag: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

failures=0
warnings=0

pass() { printf 'PASS %s\n' "$*"; }
warn() { printf 'WARN %s\n' "$*"; warnings=$((warnings + 1)); }
fail() { printf 'FAIL %s\n' "$*"; failures=$((failures + 1)); }

run_hook() {
  local hook="$1"
  local input="${2:-}"
  if [ -n "$input" ]; then
    env -u CLAUDE_PROJECT_DIR -u CLAUDE_SESSION_ID -u CLAUDE_SESSION_DIR \
      COGNITIVE_OS_HARNESS="$HARNESS" \
      COGNITIVE_OS_PROJECT_DIR="$SCRATCH_PROJECT" \
      CODEX_PROJECT_DIR="$SCRATCH_PROJECT" \
      COGNITIVE_OS_SESSION_ID="$SESSION_ID" \
      CODEX_SESSION_ID="$SESSION_ID" \
      COGNITIVE_OS_SESSION_START="2026-04-28T00:00:00Z" \
      bash "$OS_SOURCE_ROOT/hooks/$hook" <<<"$input"
  else
    env -u CLAUDE_PROJECT_DIR -u CLAUDE_SESSION_ID -u CLAUDE_SESSION_DIR \
      COGNITIVE_OS_HARNESS="$HARNESS" \
      COGNITIVE_OS_PROJECT_DIR="$SCRATCH_PROJECT" \
      CODEX_PROJECT_DIR="$SCRATCH_PROJECT" \
      COGNITIVE_OS_SESSION_ID="$SESSION_ID" \
      CODEX_SESSION_ID="$SESSION_ID" \
      COGNITIVE_OS_SESSION_START="2026-04-28T00:00:00Z" \
      bash "$OS_SOURCE_ROOT/hooks/$hook"
  fi
}

check_driver_projection() {
  local driver_path
  driver_path="$(cos_settings_driver_path "$PROJECT_ROOT" "$HARNESS")"
  if [ ! -f "$driver_path" ]; then
    fail "settings driver missing for $HARNESS: $(cos_settings_driver_label "$HARNESS")"
    return
  fi

  if python3 - "$driver_path" "$HARNESS" <<'PYEOF'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
harness = sys.argv[2]
data = json.loads(path.read_text())
hooks = data.get("hooks", data)

required = {
    "SessionStart": ["engram-daemon-launcher.sh", "session-resume.sh"],
    "UserPromptSubmit": ["user-prompt-capture.sh"],
    "Stop": [
        "session-summary-reminder.sh",
        "session-learning.sh",
        "git-context-capture.sh",
        "session-changelog.sh",
        "engram-crystallize-on-session-end.sh",
    ],
}

missing = []
for event, scripts in required.items():
    commands = [
        hook.get("command", "")
        for group in hooks.get(event, [])
        for hook in group.get("hooks", [])
    ]
    for script in scripts:
        if not any(script in command for command in commands):
            missing.append(f"{event}:{script}")

if missing:
    print(",".join(missing), file=sys.stderr)
    raise SystemExit(1)

if harness == "claude":
    precompact = [
        hook.get("command", "")
        for group in hooks.get("PreCompact", [])
        for hook in group.get("hooks", [])
    ]
    if not any("pre-compaction-flush.sh" in command for command in precompact):
        print("Claude driver missing PreCompact memory flush", file=sys.stderr)
        raise SystemExit(1)
PYEOF
  then
    pass "memory lifecycle hooks are projected for $HARNESS supported events"
  else
    fail "memory lifecycle projection is incomplete for $HARNESS"
  fi
}

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/cos-memory-doctor.XXXXXX")"
SESSION_ID="doctor-session"
SCRATCH_PROJECT="$TMP_ROOT/project"

cleanup() {
  if [ "$KEEP_TMP" != "1" ]; then
    rm -rf "$TMP_ROOT"
  else
    printf 'INFO scratch project kept at %s\n' "$SCRATCH_PROJECT"
  fi
}
trap cleanup EXIT

mkdir -p \
  "$SCRATCH_PROJECT/.cognitive-os/tasks" \
  "$SCRATCH_PROJECT/.cognitive-os/metrics" \
  "$SCRATCH_PROJECT/.cognitive-os/sessions/$SESSION_ID" \
  "$SCRATCH_PROJECT/.codex"

ln -s "$OS_SOURCE_ROOT/lib" "$SCRATCH_PROJECT/lib" 2>/dev/null || true
cat > "$SCRATCH_PROJECT/.cognitive-os/install-meta.json" <<EOF
{"source":"$OS_SOURCE_ROOT","harness":"$HARNESS","settings_driver":"$(cos_settings_driver_label "$HARNESS")"}
EOF
printf '{}\n' > "$SCRATCH_PROJECT/.codex/hooks.json"

git -C "$SCRATCH_PROJECT" init -q >/dev/null 2>&1 || true
git -C "$SCRATCH_PROJECT" config user.email "doctor@example.invalid" >/dev/null 2>&1 || true
git -C "$SCRATCH_PROJECT" config user.name "Cognitive OS Doctor" >/dev/null 2>&1 || true
printf 'doctor\n' > "$SCRATCH_PROJECT/README.md"
git -C "$SCRATCH_PROJECT" add README.md >/dev/null 2>&1 || true
git -C "$SCRATCH_PROJECT" commit -m "doctor baseline" -q >/dev/null 2>&1 || true
start_commit="$(git -C "$SCRATCH_PROJECT" rev-parse --short HEAD 2>/dev/null || true)"
printf '{"session_id":"%s","start_commit":"%s"}\n' "$SESSION_ID" "$start_commit" \
  > "$SCRATCH_PROJECT/.cognitive-os/sessions/$SESSION_ID/meta.json"

printf 'Project: %s\n' "$PROJECT_ROOT"
printf 'Harness: %s\n' "$HARNESS"
printf 'Scratch: %s\n' "$SCRATCH_PROJECT"

case "$HARNESS" in
  claude|codex) pass "memory doctor supports harness: $HARNESS" ;;
  *) fail "memory doctor does not support harness: $HARNESS" ;;
esac

check_driver_projection

if [ "$START_ENGRAM" = true ]; then
  if command -v engram >/dev/null 2>&1; then
    if run_hook "engram-daemon-launcher.sh" >/dev/null 2>&1; then
      pass "Engram launcher hook can run for a new $HARNESS session"
    else
      warn "Engram launcher hook returned non-zero"
    fi
  else
    warn "Engram binary missing; daemon startup could not be verified"
  fi
else
  warn "Engram startup check skipped by --skip-engram-start"
fi

expected_output="$SCRATCH_PROJECT/recovered.txt"
printf 'recovered\n' > "$expected_output"
python3 - "$SCRATCH_PROJECT/.cognitive-os/tasks/active-tasks.json" "$expected_output" <<'PYEOF'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(json.dumps({
    "tasks": [{
        "id": "doctor-task",
        "description": "Synthetic pending task",
        "status": "in_progress",
        "expectedOutputs": [sys.argv[2]],
    }]
}) + "\n")
PYEOF

if run_hook "session-resume.sh" >/dev/null 2>&1; then
  if python3 - "$SCRATCH_PROJECT/.cognitive-os/tasks/active-tasks.json" <<'PYEOF'
import json
import sys
from pathlib import Path

tasks = json.loads(Path(sys.argv[1]).read_text())["tasks"]
raise SystemExit(0 if tasks[0]["status"] == "completed" else 1)
PYEOF
  then
    pass "session-resume detects and recovers pending tasks"
  else
    fail "session-resume did not mark the synthetic pending task completed"
  fi
else
  fail "session-resume hook failed"
fi

prompt_payload='{"prompt":"For context, remember that this doctor validates Codex memory lifecycle portability across sessions."}'
if run_hook "user-prompt-capture.sh" "$prompt_payload" >/dev/null 2>&1; then
  if [ -s "$SCRATCH_PROJECT/.cognitive-os/metrics/prompt-captures.jsonl" ]; then
    pass "user prompt capture writes lifecycle metrics"
  else
    warn "user prompt capture ran but did not persist a capture metric"
  fi
else
  fail "user prompt capture hook failed"
fi

if run_hook "session-learning.sh" >/dev/null 2>&1 \
  && [ -s "$SCRATCH_PROJECT/.cognitive-os/metrics/session-learnings.jsonl" ]; then
  pass "session-learning saves session summary metrics"
else
  fail "session-learning did not write session-learnings.jsonl"
fi

if run_hook "git-context-capture.sh" >/dev/null 2>&1 \
  && [ -s "$SCRATCH_PROJECT/.cognitive-os/sessions/$SESSION_ID/git-context.json" ]; then
  pass "git-context-capture saves session git context"
else
  fail "git-context-capture did not write session git context"
fi

if run_hook "session-changelog.sh" >/dev/null 2>&1 \
  && [ -s "$SCRATCH_PROJECT/.cognitive-os/changelogs/$SESSION_ID.md" ]; then
  pass "session-changelog saves resumable changelog"
else
  fail "session-changelog did not write session changelog"
fi

if run_hook "engram-crystallize-on-session-end.sh" >/dev/null 2>&1 \
  && [ -s "$SCRATCH_PROJECT/.cognitive-os/metrics/crystallization-events.jsonl" ]; then
  pass "Engram crystallization records session-end lifecycle event"
else
  fail "Engram crystallization did not write session-end lifecycle event"
fi

SUMMARY_FAKE_BIN="$TMP_ROOT/summary-fake-bin"
mkdir -p "$SUMMARY_FAKE_BIN"
cat > "$SUMMARY_FAKE_BIN/curl" <<'EOF'
#!/usr/bin/env bash
args="$*"
case "$args" in
  *127.0.0.1:7437/health*) printf '%s\n' '{"status":"ok"}'; exit 0 ;;
  *127.0.0.1:7437/search*) printf '%s\n' '[]'; exit 0 ;;
  *) exit 0 ;;
esac
EOF
cat > "$SUMMARY_FAKE_BIN/engram" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
exit 0
EOF
chmod +x "$SUMMARY_FAKE_BIN/curl" "$SUMMARY_FAKE_BIN/engram"

summary_stage_a_out="$TMP_ROOT/session-summary-stage-a.out"
if PATH="$SUMMARY_FAKE_BIN:$PATH" run_hook "session-summary-reminder.sh" >"$summary_stage_a_out" 2>/dev/null \
  && grep -q "mem_session_summary" "$summary_stage_a_out" \
  && [ -f "$SCRATCH_PROJECT/.cognitive-os/sessions/$SESSION_ID/.summary-reminder-fired" ]; then
  pass "session-summary-reminder protects stop with mem_session_summary reminder"
else
  fail "session-summary-reminder did not emit the stage-A memory reminder"
fi

if PATH="$SUMMARY_FAKE_BIN:$PATH" run_hook "session-summary-reminder.sh" >/dev/null 2>&1 \
  && [ -s "$SCRATCH_PROJECT/.cognitive-os/metrics/session-summary-fallback.jsonl" ] \
  && [ -f "$SCRATCH_PROJECT/.cognitive-os/sessions/$SESSION_ID/.summary-fallback-fired" ]; then
  pass "session-summary-reminder writes fallback persistence on second stop"
else
  fail "session-summary-reminder did not write the stage-B fallback metric"
fi

if run_hook "pre-compaction-flush.sh" >/tmp/cos-memory-doctor-precompact.$$ 2>/dev/null; then
  if grep -q "mem_session_summary" /tmp/cos-memory-doctor-precompact.$$ \
    && grep -q "mem_save" /tmp/cos-memory-doctor-precompact.$$; then
    pass "pre-compaction flush emits durable memory reminder"
  else
    fail "pre-compaction flush did not emit required memory reminder"
  fi
else
  fail "pre-compaction flush hook failed"
fi
rm -f /tmp/cos-memory-doctor-precompact.$$

if [ "$failures" -gt 0 ] || { [ "$STRICT" = true ] && [ "$warnings" -gt 0 ]; }; then
  printf 'Result: FAIL (%s failure(s), %s warning(s))\n' "$failures" "$warnings"
  exit 1
fi

printf 'Result: PASS (%s warning(s))\n' "$warnings"
exit 0
