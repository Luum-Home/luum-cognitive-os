#!/usr/bin/env bash
# SCOPE: both
# session-quality-close-gate.sh — Stop hook: block session close on explicit
# failed verification evidence from the current project/session.
#
# Design principle: fail on concrete negative evidence, never on absent optional
# infrastructure. This keeps Stop deterministic while preventing agents from
# closing a session after a feature-building or validation primitive already
# recorded a blocking/failing result.

set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

if [ "${DISABLE_HOOK_SESSION_QUALITY_CLOSE_GATE:-}" = "true" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}}"
SESSION_ID="${COGNITIVE_OS_SESSION_ID:-${CODEX_SESSION_ID:-${CLAUDE_SESSION_ID:-}}}"

# Drain Stop hook stdin to avoid broken pipe surprises in harnesses that send it.
cat >/dev/null 2>&1 || true

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

RESULT=$(python3 - "$PROJECT_DIR" "$SESSION_ID" <<'PYEOF'
import json
import sys
from pathlib import Path

project_dir = Path(sys.argv[1])
session_id = sys.argv[2]
metrics_dir = project_dir / ".cognitive-os" / "metrics"
session_metrics_dir = project_dir / ".cognitive-os" / "sessions" / session_id / "metrics" if session_id else None

CANDIDATES = [
    ("auto-verify", metrics_dir / "auto-verify.jsonl"),
    ("completion-gate", metrics_dir / "completion-gate.jsonl"),
    ("dod-gate", metrics_dir / "dod-gate.jsonl"),
    ("quality-gate", metrics_dir / "quality-gate.jsonl"),
    ("session-quality", metrics_dir / "session-quality.jsonl"),
]
if session_metrics_dir:
    CANDIDATES.extend([
        ("auto-verify", session_metrics_dir / "auto-verify.jsonl"),
        ("completion-gate", session_metrics_dir / "completion-gate.jsonl"),
        ("dod-gate", session_metrics_dir / "dod-gate.jsonl"),
        ("quality-gate", session_metrics_dir / "quality-gate.jsonl"),
        ("session-quality", session_metrics_dir / "session-quality.jsonl"),
    ])

BLOCK_STATUSES = {"fail", "failed", "failure", "block", "blocked", "error"}
BLOCK_DECISIONS = {"block", "blocked", "deny", "denied"}


def as_int(value):
    try:
        return int(value)
    except Exception:
        return None


def has_failed_counts(event):
    for key in ("failed", "failures", "errors", "blocking_failures", "blocking_issues"):
        value = as_int(event.get(key))
        if value is not None and value > 0:
            return True, f"{key}={value}"
    summary = event.get("summary")
    if isinstance(summary, dict):
        for key in ("failed", "failures", "errors", "blocking_failures", "blocking_issues"):
            value = as_int(summary.get(key))
            if value is not None and value > 0:
                return True, f"summary.{key}={value}"
    return False, ""


def event_blocks(event):
    for key in ("status", "result", "outcome", "verdict"):
        value = str(event.get(key, "")).lower()
        if value in BLOCK_STATUSES:
            return True, f"{key}={value}"
    value = str(event.get("decision", "")).lower()
    if value in BLOCK_DECISIONS:
        return True, f"decision={value}"
    count_blocks, detail = has_failed_counts(event)
    if count_blocks:
        return True, detail
    return False, ""

findings = []
for name, path in CANDIDATES:
    if not path.exists() or not path.is_file():
        continue
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
    except Exception:
        continue
    for idx, line in enumerate(lines, start=max(1, len(lines) - 199)):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        blocks, detail = event_blocks(event)
        if blocks:
            findings.append({
                "primitive": name,
                "file": str(path.relative_to(project_dir)) if path.is_relative_to(project_dir) else str(path),
                "line_tail_index": idx,
                "detail": detail,
                "hint": event.get("hint") or event.get("reason") or event.get("message") or "resolve or explicitly rerun the failing quality gate before closing the session",
            })

if findings:
    reason_lines = ["Session close blocked because quality/verification primitives recorded explicit failing evidence:"]
    for finding in findings[:5]:
        reason_lines.append(f"- {finding['primitive']} {finding['file']} ({finding['detail']}): {finding['hint']}")
    if len(findings) > 5:
        reason_lines.append(f"- plus {len(findings) - 5} more finding(s)")
    reason_lines.append("Next action: fix the failing gate, rerun validation, or remove stale failing metrics only after replacing them with passing evidence.")
    print("BLOCK:" + json.dumps({"decision": "block", "reason": "\n".join(reason_lines)}))
else:
    print("ALLOW")
PYEOF
)

case "$RESULT" in
  BLOCK:*)
    printf '%s\n' "${RESULT#BLOCK:}"
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
