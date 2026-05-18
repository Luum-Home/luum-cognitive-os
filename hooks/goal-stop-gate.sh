#!/usr/bin/env bash
# SCOPE: os-only
# goal-stop-gate.sh — Stop hook: enforce COS-native goal loop completion.
#
# Reads Stop event JSON from stdin (Claude Code Stop hook protocol).
# Loads the current goal state; if an active goal is incomplete, blocks
# the stop and emits continuation guidance.
#
# Exit behavior (ADR-064, Claude Code Stop hook convention):
#   exit 0 with no JSON  — allow stop (no active goal / paused / terminal)
#   exit 0 with {"decision":"block",...} — block stop, return guidance to agent
#
# Harness: Claude Code only (Stop hook is CC-specific in MVP).
# Profile: standard + paranoid (not minimal).
#
# T-09: hook gate + harness adapter
# T-10: evidence evaluation wired — incomplete → continuation guidance;
#        complete → archive + allow stop
#
# REQ-004: enforce goal loop via Stop hook
# REQ-012: harness adapter determines enforcement level

set -uo pipefail

# Respect killswitch (ADR-028 §584)
source "$(dirname "${BASH_SOURCE[0]}")/_lib/killswitch_check.sh"

_HOOK_NAME="goal-stop-gate"

# Runtime disable: DISABLE_HOOK_GOAL_STOP_GATE=true skips this hook
if [ "${DISABLE_HOOK_GOAL_STOP_GATE:-}" = "true" ]; then
  exit 0
fi

PROJECT_DIR="${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}}}"
WORKSPACE_THREAD_ID="${COS_WORKSPACE_THREAD_ID:-default}"

# Read stdin once
INPUT=$(cat)

# ── Fast path: no Python available → degrade safely ─────────────────────────
if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

# ── Delegate to Python helper ────────────────────────────────────────────────
# The helper returns one of:
#   ALLOW           → exit 0, no output
#   BLOCK:<json>    → exit 0, emit JSON to stdout
#   ERROR:<msg>     → exit 0 (degrade safely on errors)
RESULT=$(python3 - "$PROJECT_DIR" "$WORKSPACE_THREAD_ID" <<'PYEOF'
import sys
import json
import os
from pathlib import Path

project_dir = Path(sys.argv[1])
workspace_thread_id = sys.argv[2]

if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

try:
    from lib.goal_state import GoalStateStore, _ALLOW_STOP_STATUSES, apply_transition, EvaluatorVerdict
    from lib.goal_evaluator import GoalEvaluator
    from lib.goal_budget import check_budget
except ImportError as exc:
    print(f"ERROR:import failed: {exc}", file=sys.stderr)
    sys.exit(0)  # degrade safely

base_dir = project_dir / ".cognitive-os" / "goals"
store = GoalStateStore(base_dir=base_dir, workspace_thread_id=workspace_thread_id)

goal = store.load()

# No active goal → allow
if goal is None:
    print("ALLOW")
    sys.exit(0)

# Terminal / paused statuses → allow
if goal.status in _ALLOW_STOP_STATUSES:
    print("ALLOW")
    sys.exit(0)

def _budget_limit_and_allow(goal, reason, dimension=""):
    """Archive an active goal as budget_limited and allow Stop."""
    from datetime import datetime, timezone
    try:
        budget_goal = apply_transition(goal, "budget_limited")
        verdict = EvaluatorVerdict(
            verdict="incomplete",
            reason=reason,
            missing_checks=list(goal.acceptance_checks),
            confidence=1.0,
            evaluated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        budget_goal.evaluator_history.append(verdict)
        budget_goal.last_guidance = reason
        store.archive(budget_goal)
        store.append_event("budget_limited", {
            "goal_id": goal.goal_id,
            "dimension": dimension,
            "reason": reason,
        })
    except Exception as exc:
        print(f"ERROR:budget_limited archive failed: {exc}", file=sys.stderr)
    print("ALLOW")
    sys.exit(0)

# Budget is a hard stop condition and must be checked even when no evidence
# packet exists yet. Otherwise max_turns=0 / max_minutes=0 goals can block
# forever before evaluation starts.
budget = check_budget(goal, project_dir)
if budget.exhausted:
    _budget_limit_and_allow(
        goal,
        f"Budget exhausted ({budget.dimension}): {budget.reason}",
        budget.dimension,
    )

# Active goal — check if evidence is available to evaluate
last_evidence = None
if goal.evidence_history:
    last_evidence = goal.evidence_history[-1]

if last_evidence is None:
    # No evidence packet yet — emit basic continuation guidance
    remaining_checks = goal.acceptance_checks
    budget_info = []
    if goal.max_turns is not None:
        budget_info.append(f"turns: {goal.turns_used}/{goal.max_turns}")
    import time
    elapsed_min = (time.time() - goal.started_at_epoch) / 60
    if goal.max_minutes is not None:
        budget_info.append(f"time: {elapsed_min:.1f}/{goal.max_minutes} min")

    guidance_lines = [
        f"Goal ID: {goal.goal_id}",
        f"Objective: {goal.objective}",
        "",
        "REQUIRED: Submit an evidence packet before stopping.",
        "Use: scripts/cos-goal evaluate --evidence-file <path>",
        "",
        "Pending acceptance checks:",
    ]
    for chk in remaining_checks:
        guidance_lines.append(f"  - {chk}")
    if budget_info:
        guidance_lines.append("")
        guidance_lines.append("Budget: " + " | ".join(budget_info))
    guidance_lines.append("")
    guidance_lines.append("Next action: provide structured evidence addressing each acceptance check.")

    guidance = "\n".join(guidance_lines)
    block_payload = json.dumps({
        "decision": "block",
        "reason": (
            f"Active goal '{goal.goal_id}' is incomplete and has no evidence packet. "
            "Submit evidence before stopping.\n\n" + guidance
        ),
    })
    print(f"BLOCK:{block_payload}")
    sys.exit(0)

# Evaluate with last evidence packet
evaluator = GoalEvaluator(project_dir=project_dir)
try:
    verdict = evaluator.evaluate(goal, last_evidence)
except Exception as exc:
    # Evaluator failure — block with error context so agent can debug
    block_payload = json.dumps({
        "decision": "block",
        "reason": (
            f"Goal evaluator failed for goal '{goal.goal_id}': {exc}. "
            "Resolve the evaluator error before stopping."
        ),
    })
    print(f"BLOCK:{block_payload}")
    sys.exit(0)

if verdict.verdict == "complete":
    # Archive the completed goal and allow stop
    try:
        completed_goal = apply_transition(goal, "complete")
        # Record the verdict in evaluator history
        completed_goal.evaluator_history.append(verdict)
        completed_goal.turns_used = goal.turns_used + 1
        store.archive(completed_goal)
    except Exception:
        pass  # Archive failure should not block stop on a complete goal
    print("ALLOW")
    sys.exit(0)

if verdict.verdict == "escalate":
    # Escalation threshold crossed — transition to escalated and allow stop.
    # REQ-017: escalated goals allow stop with escalation evidence visible to operator.
    try:
        escalated_goal = apply_transition(goal, "escalated")
        escalated_goal.evaluator_history.append(verdict)
        escalated_goal.last_guidance = verdict.reason
        escalated_goal.consecutive_no_progress = goal.consecutive_no_progress
        store.archive(escalated_goal)
        store.append_event("escalated", {
            "goal_id": goal.goal_id,
            "reason": verdict.reason,
            "consecutive_no_progress": goal.consecutive_no_progress,
        })
    except Exception:
        pass
    # Emit escalation notice to stderr; exit 0 (allow stop)
    import sys as _sys
    print(
        f"GOAL ESCALATED: Goal {goal.goal_id} escalated after "
        f"{goal.consecutive_no_progress} consecutive no-progress turns. "
        f"Reason: {verdict.reason}",
        file=_sys.stderr,
    )
    print("ALLOW")
    sys.exit(0)

if verdict.reason.startswith("Budget exhausted"):
    _budget_limit_and_allow(goal, verdict.reason, "evaluator")

# Incomplete verdict — build continuation guidance
missing = verdict.missing_checks or []
reason = verdict.reason or "Acceptance checks not fully satisfied."
next_action = (last_evidence.next_action or "") if last_evidence else ""

budget_info = []
if goal.max_turns is not None:
    budget_info.append(f"turns used: {goal.turns_used}/{goal.max_turns}")
import time
elapsed_min = (time.time() - goal.started_at_epoch) / 60
if goal.max_minutes is not None:
    budget_info.append(f"time: {elapsed_min:.1f}/{goal.max_minutes} min")

guidance_parts = [
    f"Goal ID: {goal.goal_id}",
    f"Evaluator verdict: {verdict.verdict}",
    f"Reason: {reason}",
]
if missing:
    guidance_parts.append("Missing acceptance checks:")
    for chk in missing:
        guidance_parts.append(f"  - {chk}")
if next_action:
    guidance_parts.append(f"Next required action: {next_action}")
if budget_info:
    guidance_parts.append("Budget: " + " | ".join(budget_info))

guidance = "\n".join(guidance_parts)

try:
    goal.evaluator_history.append(verdict)
    goal.turns_used = goal.turns_used + 1
    goal.last_guidance = guidance
    store.save(goal)
    store.append_event("evaluate", {
        "goal_id": goal.goal_id,
        "verdict": verdict.verdict,
        "missing_checks": missing,
        "turns_used": goal.turns_used,
    })
except Exception as exc:
    block_payload = json.dumps({
        "decision": "block",
        "reason": (
            f"Goal '{goal.goal_id}' is incomplete, but persisting evaluator state "
            f"failed: {exc}. Resolve persistence before stopping."
        ),
    })
    print(f"BLOCK:{block_payload}")
    sys.exit(0)

block_payload = json.dumps({
    "decision": "block",
    "reason": (
        f"Active goal '{goal.goal_id}' is not yet complete.\n\n"
        + guidance
    ),
})
print(f"BLOCK:{block_payload}")
PYEOF
)

EXIT_CODE=$?

# Python helper exited non-zero → degrade safely
if [ $EXIT_CODE -ne 0 ]; then
  exit 0
fi

# Parse RESULT prefix
case "$RESULT" in
  ALLOW*)
    exit 0
    ;;
  BLOCK:*)
    PAYLOAD="${RESULT#BLOCK:}"
    printf '%s\n' "$PAYLOAD"
    exit 0
    ;;
  ERROR:*)
    # Degrade safely — log to stderr, allow stop
    echo "${RESULT#ERROR:}" >&2
    exit 0
    ;;
  *)
    # Unknown — degrade safely
    exit 0
    ;;
esac
