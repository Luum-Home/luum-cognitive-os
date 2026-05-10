#!/usr/bin/env bash
# SCOPE: os-only
# CONCERNS: quality, learning-loop, audit
# PostToolUse hook: Spawn review agent after sub-agent completion (ADR-096).
#
# Fires after "Agent" tool completes. Runs a stochastic + budget gate
# (lib/review_agent.py::should_review) and, if approved, dispatches a
# reviewer agent via lib/dispatch.py with a cross-review model (ADR-096
# §Decision 3).
#
# v2: ASYNC by default — writes a pending review marker and launches the
# background sweeper. Set review.async=false or COS_REVIEW_ASYNC=0 to use the
# legacy synchronous path for diagnostics.
#
# Budget state: .cognitive-os/runtime/review-budget.json
# Findings: .cognitive-os/metrics/review-findings.jsonl + Engram

set -uo pipefail

# ADR-028 §584: respect killswitch flag — non-critical hooks early-exit when set.
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="review-spawner"
source "$(dirname "$0")/_lib/safe-jsonl.sh"
source "$(dirname "$0")/_lib/common.sh"

# Auto-disabled at capability level 4+ (review is resource-intensive)
check_capability_level "review-spawner"
# Runtime disable: DISABLE_HOOK_REVIEW_SPAWNER=true skips this hook
check_disabled_env "review-spawner"

# Gate: only process Agent tool completions
read_stdin_json
INPUT="$_STDIN_JSON"
require_tool "Agent"

PROJECT_DIR="$_PROJECT_DIR"
RUNTIME_DIR="$PROJECT_DIR/.cognitive-os/runtime"
METRICS_DIR="$PROJECT_DIR/.cognitive-os/metrics"
FINDINGS_JSONL="$METRICS_DIR/review-findings.jsonl"
BUDGET_STATE="$RUNTIME_DIR/review-budget.json"

# ── Extract producer output before expensive config loads ───────────────────
# If the agent output is absent or too short there is nothing useful to review.
# Keep this before mkdir/python config work so the common no-op path stays cheap.
AGENT_OUTPUT=$(echo "$INPUT" | jq -r '.tool_result // .output // .tool_output // empty' 2>/dev/null || true)
AGENT_PROMPT=$(echo "$INPUT" | jq -r '.tool_input.description // .tool_input.prompt // empty' 2>/dev/null || true)
PRODUCER_ID=$(echo "$INPUT" | jq -r '.tool_use_id // "unknown"' 2>/dev/null || true)

if [ -z "$AGENT_OUTPUT" ] || [ ${#AGENT_OUTPUT} -lt 200 ]; then
  exit 0
fi

mkdir -p "$RUNTIME_DIR" "$METRICS_DIR"

# ── Read config from cognitive-os.yaml ──────────────────────────────────────

read_yaml_value() {
  local key="$1" default="$2"
  python3 -c "
import sys, os
try:
    sys.path.insert(0, '${PROJECT_DIR}')
    from lib.config_loader import load_structured
    cfg = load_structured()
    val = cfg.get('review', {}).get('${key}')
    print(val if val is not None else '${default}')
except Exception:
    print('${default}')
" 2>/dev/null || echo "$default"
}

SAMPLE_RATE=$(read_yaml_value "sample_rate" "0.2")
MAX_PER_DAY=$(read_yaml_value "max_per_day" "50")
DEFAULT_MODEL=$(read_yaml_value "default_model" "haiku")
ALWAYS_REVIEW_KINDS=$(read_yaml_value "always_review_kinds" "")
ASYNC_REVIEW=$(read_yaml_value "async" "true")
if [ -n "${COS_REVIEW_ASYNC:-}" ]; then
  ASYNC_REVIEW="$COS_REVIEW_ASYNC"
fi

# ── Producer metadata ────────────────────────────────────────────────────────

# Determine producer model (best-effort: may not be in hook input)
PRODUCER_MODEL=$(echo "$INPUT" | jq -r '.tool_input.model // "sonnet"' 2>/dev/null || true)
if [ -z "$PRODUCER_MODEL" ] || [ "$PRODUCER_MODEL" = "null" ]; then
  PRODUCER_MODEL="sonnet"
fi

# ── Stochastic + budget gate ─────────────────────────────────────────────────

SHOULD_REVIEW=$(python3 -c "
import sys, json, os
sys.path.insert(0, '${PROJECT_DIR}')
from pathlib import Path
try:
    from lib.review_agent import should_review, daily_budget_state, _save_budget_state
    state_file = Path('${BUDGET_STATE}')
    budget = daily_budget_state(state_file)
    result = should_review(
        producer_output={'producer_id': '${PRODUCER_ID}'},
        sample_rate=float('${SAMPLE_RATE}'),
        daily_budget=budget,
        max_per_day=int('${MAX_PER_DAY}'),
        state_file=state_file,
    )
    if result:
        # Persist updated budget (should_review mutates budget dict)
        _save_budget_state(budget, state_file)
    print('yes' if result else 'no')
except Exception as e:
    print('no', file=sys.stderr)
    print('no')
" 2>/dev/null || echo "no")

if [ "$SHOULD_REVIEW" != "yes" ]; then
  exit 0
fi

# ── Select reviewer model (cross-review matrix) ──────────────────────────────

REVIEWER_MODEL=$(python3 -c "
import sys
sys.path.insert(0, '${PROJECT_DIR}')
try:
    from lib.review_agent import select_reviewer_model
    print(select_reviewer_model('${PRODUCER_MODEL}'))
except Exception:
    print('sonnet')
" 2>/dev/null || echo "sonnet")

# Allow env override per ADR-096 §Decision 4
if [ -n "${COS_REVIEW_MODEL:-}" ]; then
  REVIEWER_MODEL="$COS_REVIEW_MODEL"
fi

# ── Build review prompt ───────────────────────────────────────────────────────

REVIEW_PROMPT=$(python3 -c "
import sys, json
sys.path.insert(0, '${PROJECT_DIR}')
try:
    from lib.review_agent import build_review_prompt
    producer = {
        'task_description': '''${AGENT_PROMPT:0:1000}''',
        'text': '''${AGENT_OUTPUT:0:6000}''',
        'producer_id': '${PRODUCER_ID}',
        'producer_model': '${PRODUCER_MODEL}',
    }
    print(build_review_prompt(producer, criteria=[]))
except Exception as e:
    print(f'Review audit for task: ${PRODUCER_ID}', file=sys.stderr)
    print('Review audit: could not build prompt')
" 2>/dev/null || echo "Review audit for task: ${PRODUCER_ID}")

if [ -z "$REVIEW_PROMPT" ]; then
  exit 0
fi

# ── Dispatch review (v1: synchronous) ────────────────────────────────────────

REVIEWER_ID="review-${PRODUCER_ID}-$(date +%s)"

if [ "$ASYNC_REVIEW" = "true" ] || [ "$ASYNC_REVIEW" = "1" ] || [ "$ASYNC_REVIEW" = "yes" ]; then
  REVIEW_PROMPT="$REVIEW_PROMPT" \
  PRODUCER_ID="$PRODUCER_ID" \
  PRODUCER_MODEL="$PRODUCER_MODEL" \
  REVIEWER_ID="$REVIEWER_ID" \
  REVIEWER_MODEL="$REVIEWER_MODEL" \
  AGENT_PROMPT="$AGENT_PROMPT" \
  BUDGET_STATE="$BUDGET_STATE" \
  PROJECT_DIR="$PROJECT_DIR" \
  python3 - <<'PYASYNC' 2>/dev/null || true
import os
import sys
from pathlib import Path

project = Path(os.environ["PROJECT_DIR"])
sys.path.insert(0, str(project))
from lib.review_agent import enqueue_review_request

enqueue_review_request({
    "prompt": os.environ.get("REVIEW_PROMPT", ""),
    "producer_id": os.environ.get("PRODUCER_ID", "unknown"),
    "producer_model": os.environ.get("PRODUCER_MODEL", "unknown"),
    "reviewer_id": os.environ.get("REVIEWER_ID", "unknown"),
    "reviewer_model": os.environ.get("REVIEWER_MODEL", "sonnet"),
    "task_description": os.environ.get("AGENT_PROMPT", "")[:300],
})
PYASYNC

  if [ -x "$PROJECT_DIR/scripts/review_pending_sweeper.py" ]; then
    (
      export COGNITIVE_OS_PROJECT_DIR="$PROJECT_DIR"
      python3 "$PROJECT_DIR/scripts/review_pending_sweeper.py" --project-dir "$PROJECT_DIR" --limit 1 >/dev/null 2>&1
    ) &
  fi
  exit 0
fi

REVIEW_RESPONSE=$(python3 -c "
import sys
sys.path.insert(0, '${PROJECT_DIR}')
try:
    from lib.dispatch import dispatch
    prompt = '''${REVIEW_PROMPT}'''
    result = dispatch(
        prompt=prompt,
        providers=['qwen', 'claude'],
        claude_model='${REVIEWER_MODEL}',
        task_type='review',
        skill_name='review-spawner',
    )
    if result.success:
        print(result.text)
    else:
        print(f'REVIEW_SCORE: -1', file=sys.stderr)
        print('')
except Exception as e:
    print(f'dispatch failed: {e}', file=sys.stderr)
    print('')
" 2>/dev/null || true)

if [ -z "$REVIEW_RESPONSE" ]; then
  # Dispatch failed; log minimal failure record
  TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  FAILURE_REC=$(python3 -c "import json; print(json.dumps({'timestamp': '${TS}', 'producer_id': '${PRODUCER_ID}', 'reviewer_id': '${REVIEWER_ID}', 'reviewer_model': '${REVIEWER_MODEL}', 'score': -1, 'error': 'dispatch_failed', 'gaps': ['Review dispatch failed — no response from reviewer'], 'evidence': [], 'recommendations': []}))" 2>/dev/null || echo '{"error":"dispatch_failed"}')
  echo "$FAILURE_REC" >> "$FINDINGS_JSONL" 2>/dev/null || true
  exit 0
fi

# ── Parse and persist finding ─────────────────────────────────────────────────

python3 -c "
import sys, json
sys.path.insert(0, '${PROJECT_DIR}')
from pathlib import Path
try:
    from lib.review_agent import parse_review_response, persist_finding

    response = '''${REVIEW_RESPONSE}'''
    parsed = parse_review_response(response)

    finding = {
        **parsed,
        'producer_id': '${PRODUCER_ID}',
        'producer_model': '${PRODUCER_MODEL}',
        'reviewer_id': '${REVIEWER_ID}',
        'reviewer_model': '${REVIEWER_MODEL}',
        'task_description': '${AGENT_PROMPT:0:300}',
    }

    persist_finding(
        finding,
        jsonl_path=Path('${FINDINGS_JSONL}'),
        engram_topic='review-finding',
    )

    score = parsed.get('score', -1)
    gaps = parsed.get('gaps', [])
    gap_count = len(gaps)
    print(f'[review-spawner] score={score} gaps={gap_count} reviewer={\"${REVIEWER_MODEL}\"}')
except Exception as e:
    print(f'[review-spawner] persist failed: {e}', file=sys.stderr)
" 2>/dev/null || true

exit 0
