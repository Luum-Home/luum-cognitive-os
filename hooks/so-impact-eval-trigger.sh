#!/usr/bin/env bash
# SCOPE: both
# Advisory SO-wide impact evaluation trigger for lifecycle Stop.
set -uo pipefail

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

if [ "${DISABLE_HOOK_SO_IMPACT_EVAL_TRIGGER:-0}" = "1" ] || [ "${COS_SO_IMPACT_EVAL_TRIGGER_DISABLE:-0}" = "1" ]; then
  exit 0
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

if [ -x ".cognitive-os/bin/cos-so-impact-eval" ]; then
  RUNNER=".cognitive-os/bin/cos-so-impact-eval"
elif [ -x "scripts/cos-so-impact-eval" ]; then
  RUNNER="scripts/cos-so-impact-eval"
else
  exit 0
fi

if [ -f ".cognitive-os/benchmarks/so-impact-money-format-refactor.yaml" ]; then
  CONTRACT=".cognitive-os/benchmarks/so-impact-money-format-refactor.yaml"
elif [ -f "docs/08-References/benchmarks/so-impact-money-format-refactor.yaml" ]; then
  CONTRACT="docs/08-References/benchmarks/so-impact-money-format-refactor.yaml"
else
  exit 0
fi

RAW_STATUS="$({ git status --porcelain=v1 --untracked-files=all 2>/dev/null || true; })"
CHANGED_FILES="$(printf '%s\n' "$RAW_STATUS" | python3 -c '
import sys

relevant_prefixes = (
    "hooks/so-impact-eval-trigger.sh",
    ".cognitive-os/hooks/cos/so-impact-eval-trigger.sh",
    ".cognitive-os/bin/cos-so-impact-eval",
    ".cognitive-os/bin/cos_so_impact_eval.py",
    ".cognitive-os/benchmarks/so-impact-",
    ".cognitive-os/fixtures/so-impact/",
    "scripts/cos-so-impact-eval",
    "scripts/cos_so_impact_eval.py",
    "skills/so-impact-eval/",
    ".cognitive-os/skills/so-impact-eval/",
    ".cognitive-os/skills/cos/so-impact-eval/",
    ".claude/skills/so-impact-eval/",
    "docs/08-References/benchmarks/so-impact-",
    "templates/so-impact-eval.example.yaml",
    "fixtures/so-impact/",
    "tests/unit/test_cos_so_impact_eval.py",
    "tests/unit/test_so_impact_eval_skill.py",
    "tests/red_team/portability/test_cos_so_impact_eval_primitive.py",
    "docs/04-Concepts/architecture/so-wide-impact-evaluation-plane.md",
    "scripts/cos-graphify",
    "skills/graphify-query/",
    "scripts/cos-process-loop",
    "scripts/cos_process_loop.py",
    "scripts/cos-apply-progress",
    "scripts/cos-fresh-review",
    "scripts/cos-verify-report",
    "scripts/cos-skill-selection-report",
    "templates/process-contract.example.yaml",
)
ignored_prefixes = (
    ".cognitive-os/reports/so-impact-auto/",
    ".cognitive-os/runtime/so-impact-eval-trigger",
    ".cognitive-os/metrics/so-impact-eval-trigger.jsonl",
)

def parse_path(line):
    if not line:
        return None
    payload = line[3:] if len(line) >= 4 else line
    if " -> " in payload:
        payload = payload.split(" -> ", 1)[1]
    return payload.strip().strip("\"") or None

paths = []
for raw in sys.stdin.read().splitlines():
    path = parse_path(raw)
    if not path:
        continue
    if path.startswith(ignored_prefixes):
        continue
    if path.startswith(relevant_prefixes):
        paths.append(path)

for path in sorted(set(paths)):
    print(path)
')"
if [ -z "$CHANGED_FILES" ]; then
  exit 0
fi

mkdir -p .cognitive-os/runtime .cognitive-os/metrics .cognitive-os/reports/so-impact-auto
TRIGGER_KEY="$(printf '%s\n' "$CHANGED_FILES" | shasum -a 256 | awk '{print $1}')"
STATE_FILE=".cognitive-os/runtime/so-impact-eval-trigger.last"
if [ -f "$STATE_FILE" ] && [ "$(cat "$STATE_FILE" 2>/dev/null || true)" = "$TRIGGER_KEY" ]; then
  exit 0
fi

RUN_ID="auto-$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_ROOT=".cognitive-os/reports/so-impact-auto"
REPORT_PATH="$OUTPUT_ROOT/money-format-refactor/$RUN_ID/report.md"
STATUS="pass"
RUN_RC=0
TMP_OUT="$(mktemp -t cos-so-impact-eval-trigger.XXXXXX 2>/dev/null || mktemp)"
TMP_ERR="$(mktemp -t cos-so-impact-eval-trigger.XXXXXX 2>/dev/null || mktemp)"

if ! "$RUNNER" run \
  --contract "$CONTRACT" \
  --mode vanilla \
  --mode full-so \
  --run-id "$RUN_ID" \
  --output-root "$OUTPUT_ROOT" \
  --json >"$TMP_OUT" 2>"$TMP_ERR"; then
  RUN_RC=$?
  STATUS="warn"
fi

printf '%s\n' "$TRIGGER_KEY" > "$STATE_FILE"

python3 - "$STATUS" "$RUN_ID" "$REPORT_PATH" "$RUN_RC" "$CHANGED_FILES" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

status, run_id, report_path, rc, changed = sys.argv[1:6]
event = {
    "schema_version": "cos-so-impact-eval-trigger.v1",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "status": status,
    "run_id": run_id,
    "report_path": report_path,
    "exit_code": int(rc),
    "changed_files": changed.splitlines(),
}
metrics = Path(".cognitive-os/metrics/so-impact-eval-trigger.jsonl")
metrics.parent.mkdir(parents=True, exist_ok=True)
with metrics.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(event, sort_keys=True) + "\n")
PY

rm -f "$TMP_OUT" "$TMP_ERR"

if [ "$STATUS" = "pass" ]; then
  echo "so-impact-eval-trigger: ran SO impact smoke; report: $REPORT_PATH" >&2
else
  echo "so-impact-eval-trigger: advisory smoke failed; report: $REPORT_PATH" >&2
fi

exit 0
