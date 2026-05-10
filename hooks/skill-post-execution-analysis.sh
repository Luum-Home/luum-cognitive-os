#!/usr/bin/env bash
# SCOPE: both
# skill-post-execution-analysis.sh — PostToolUse Agent hook (ADR-176)
#
# Fires after every Agent tool completion. Records execution data to SkillStore
# and (when candidate for evolution) emits a PROPOSE-ONLY artifact.
#
# DISCIPLINE GATE: this hook has NO write path to live SKILL.md files.
# All proposal output goes to docs/reports/skill-analysis-proposals/
# in compliance with ADR-133 (expansion-without-monsterization) and
# ADR-134 (propose-only doctrine).
#
# Killswitch: DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS=1
# Event: PostToolUse Agent (async)
# Latency budget: <200ms

set -euo pipefail

# --- Killswitch ---
if [ "${DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS:-0}" = "1" ]; then
  exit 0
fi

REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || pwd)}"
SOURCE_ROOT="${COS_SOURCE_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
HOOK_NAME="skill-post-execution-analysis"
ERROR_LOG="${REPO_ROOT}/.cognitive-os/metrics/error-learning.jsonl"
DB_PATH="${REPO_ROOT}/.cognitive-os/skill_store.db"
PROPOSALS_DIR="${REPO_ROOT}/docs/reports/skill-analysis-proposals"

# --- Read payload (from _HOOK_PAYLOAD env var, or stdin) ---
if [ -n "${_HOOK_PAYLOAD:-}" ]; then
  PAYLOAD="$_HOOK_PAYLOAD"
else
  PAYLOAD=$(cat 2>/dev/null || true)
fi

if [ -z "$PAYLOAD" ]; then
  exit 0
fi

# Fast path for non-Agent tool completions. The expensive Python/SQLite path is
# only relevant to Agent skill executions; generic Bash/Edit/Read performance
# tests should not pay that cost.
case "$PAYLOAD" in
  *'"tool_name"'*'"Agent"'*|*'"tool_name":"Agent"'*|*'"skill_name"'*) ;;
  *) exit 0 ;;
esac

# --- Parse and extract fields via python3 ---
FIELDS=$(python3 -c "
import json, sys, os, hashlib

payload_str = os.environ.get('_HOOK_PAYLOAD', '')
if not payload_str:
    # Try reading from stdin arg
    payload_str = sys.argv[1] if len(sys.argv) > 1 else ''
if not payload_str:
    print('{}')
    sys.exit(0)

try:
    payload = json.loads(payload_str)
except Exception:
    print('{}')
    sys.exit(0)

tool_resp = payload.get('tool_response', payload.get('result', {}))
if isinstance(tool_resp, str):
    try:
        tool_resp = json.loads(tool_resp)
    except Exception:
        tool_resp = {}

skill_name = (
    payload.get('skill_name') or
    tool_resp.get('skill_name') or
    payload.get('tool_input', {}).get('skill') or
    ''
)
tool_count = int(tool_resp.get('tool_count', 0) or 0)
duration_ms = int(tool_resp.get('duration_ms', 0) or 0)
status = str(tool_resp.get('status', tool_resp.get('exit_code', 'unknown')) or 'unknown')
agent_session_id = payload.get('session_id', os.environ.get('CLAUDE_SESSION_ID', ''))

tool_issues = tool_resp.get('tool_issues', [])
if isinstance(tool_issues, str):
    try:
        tool_issues = json.loads(tool_issues)
    except Exception:
        tool_issues = []
num_issues = len(tool_issues) if isinstance(tool_issues, list) else 0
is_error = status in ('error', 'fail', 'failed', '1')
is_slow = duration_ms > 30000
candidate = 1 if (num_issues >= 3 or (is_error and is_slow)) else 0

skill_id = hashlib.sha256(skill_name.encode()).hexdigest() if skill_name else ''

print(json.dumps({
    'skill_name': skill_name,
    'skill_id': skill_id,
    'agent_session_id': agent_session_id,
    'tool_count': tool_count,
    'duration_ms': duration_ms,
    'status': status,
    'candidate': candidate,
    'num_issues': num_issues,
}))
" "$PAYLOAD" 2>/dev/null || echo '{}')

if [ "$FIELDS" = "{}" ] || [ -z "$FIELDS" ]; then
  python3 -c "
import json, datetime, pathlib, os
entry = {'hook': '$HOOK_NAME', 'error': 'payload_parse_failed', 'ts': datetime.datetime.utcnow().isoformat()}
log = pathlib.Path('$ERROR_LOG')
log.parent.mkdir(parents=True, exist_ok=True)
with log.open('a') as f:
    f.write(json.dumps(entry) + '\n')
" 2>/dev/null || true
  exit 0
fi

# Extract individual fields using python3 (bash 3.2-compatible — no @Q)
SKILL_NAME=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('skill_name',''))" "$FIELDS" 2>/dev/null || true)
SKILL_ID=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('skill_id',''))" "$FIELDS" 2>/dev/null || true)
CANDIDATE=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('candidate',0))" "$FIELDS" 2>/dev/null || true)
STATUS=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('status','unknown'))" "$FIELDS" 2>/dev/null || true)
TOOL_COUNT=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('tool_count',0))" "$FIELDS" 2>/dev/null || true)
DURATION_MS=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('duration_ms',0))" "$FIELDS" 2>/dev/null || true)
SESSION_ID=$(python3 -c "import json,sys; d=json.loads(sys.argv[1]); print(d.get('agent_session_id',''))" "$FIELDS" 2>/dev/null || true)

# Skip if no skill_name identified
if [ -z "$SKILL_NAME" ]; then
  exit 0
fi

# --- Write execution record to SkillStore ---
python3 - "$SKILL_NAME" "$SESSION_ID" "$TOOL_COUNT" "$DURATION_MS" "$STATUS" "$REPO_ROOT" "$SOURCE_ROOT" <<'PYEOF' 2>/dev/null || true
import sys
from pathlib import Path

skill_name, session_id, tool_count, duration_ms, status, repo_root, source_root = sys.argv[1:8]
sys.path.insert(0, source_root)
from lib.skill_store import SkillStore

store = SkillStore(Path(repo_root) / '.cognitive-os' / 'skill_store.db')
store.record_execution(
    skill_name=skill_name,
    agent_session_id=session_id,
    tool_count=int(tool_count),
    duration_ms=int(duration_ms),
    status=status,
    output_hash=None,
)
store.close()
PYEOF

# --- Discipline gate: propose-only when candidate for evolution ---
# ADR-133/134: NO write to live SKILL.md. Output goes to proposals only.
if [ "${CANDIDATE:-0}" = "1" ]; then
  DATE_DIR=$(python3 -c "import datetime; print(datetime.date.today().isoformat())" 2>/dev/null || date +%Y-%m-%d)
  PROPOSAL_DIR="${PROPOSALS_DIR}/${DATE_DIR}"
  # Sanitize skill_name for filename (bash 3.2-compatible)
  SAFE_NAME=$(python3 -c "
import sys, re
name = sys.argv[1]
safe = re.sub(r'[^A-Za-z0-9_-]', '_', name)[:60]
print(safe)
" "$SKILL_NAME" 2>/dev/null || echo "skill")
  PROPOSAL_FILE="${PROPOSAL_DIR}/${SAFE_NAME}.md"

  mkdir -p "$PROPOSAL_DIR"

  # Write propose-only artifact.
  # DISCIPLINE GATE: this python block has NO import of any path under:
  #   packages/*/SKILL.md or .claude/skills/
  # It only writes to PROPOSALS_DIR.
  python3 - "$SKILL_NAME" "$SKILL_ID" "$STATUS" "$TOOL_COUNT" "$DURATION_MS" \
            "${FIELDS}" "$PROPOSAL_FILE" <<'PYEOF' 2>/dev/null || true
import json, sys, pathlib
from datetime import datetime, timezone

skill_name, skill_id, status, tool_count, duration_ms, fields_json, proposal_path = sys.argv[1:8]
fields = json.loads(fields_json)
num_issues = fields.get('num_issues', 0)
ts = datetime.now(timezone.utc).isoformat()

# DISCIPLINE GATE assertion: we write to proposal file only.
# No write path to packages/*/SKILL.md or .claude/skills/ exists here.
content = f"""---
generated: {ts}
skill_name: {skill_name!r}
skill_id: {skill_id}
trigger: post_execution_analysis
candidate_for_evolution: true
discipline_gate: propose_only
adr: ADR-176
---

# Skill Evolution Proposal: {skill_name}

**Generated**: {ts}
**Discipline gate**: propose-only (ADR-133, ADR-134) — this file must be reviewed by
a human before any changes are applied to the live SKILL.md.

## Execution Context

| Field | Value |
|---|---|
| Status | {status} |
| Tool count | {tool_count} |
| Duration | {duration_ms}ms |
| Tool issues detected | {num_issues} |

## Why Flagged

This execution was flagged as a candidate for evolution because it met one or more
of the heuristics defined in ADR-176:
- 3+ tool issues detected, OR
- status=error AND duration > 30s

## Observations

Review the execution trace and consider whether the skill's acceptance criteria,
tool list, or prompt need updating.

## Next Steps (Human Review Required)

1. Review this proposal against the live skill at `.claude/skills/{skill_name}.md`
   (or `packages/*/SKILL.md`).
2. If changes are warranted, open a PR with the skill update.
3. Delete this proposal file after review.

**DO NOT auto-apply this proposal.** The discipline gate requires human review
per ADR-133 (expansion-without-monsterization) and ADR-134 (propose-only doctrine).
"""
pathlib.Path(proposal_path).write_text(content, encoding='utf-8')
PYEOF

fi

exit 0
