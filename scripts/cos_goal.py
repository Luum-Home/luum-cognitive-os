#!/usr/bin/env python3
# SCOPE: os-only
"""COS-native goal management CLI — implements T-03 of cos-native-goal-loop.

Commands:
  create    -- create a new goal (active)
  status    -- show current goal state (human-readable or JSON)
  pause     -- pause an active goal
  resume    -- resume a paused goal
  clear     -- clear (archive) an active or paused goal
  archive   -- explicitly archive a terminal goal
  doctor    -- report harness hook support level

REQ-001: goal creation with objective, checks, constraints, budget.
REQ-002: reject second active goal unless --replace is passed.
REQ-009: pause transitions active -> paused.
REQ-010: resume transitions paused -> active.
REQ-011: clear archives the goal.
REQ-012: doctor reports whether Stop-hook enforcement is available.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.goal_state import (
    GoalConflictError,
    GoalState,
    GoalStateStore,
    InvalidTransitionError,
    apply_transition,
)
from lib.goal_evidence import parse_evidence
from lib.goal_evaluator import GoalEvaluator
from lib.harness_adapter.goal_stop import detect_enforcement_level


# ---------------------------------------------------------------------------
# Harness support detection (REQ-012)
# ---------------------------------------------------------------------------


def _detect_harness_support() -> dict:
    """Return a dict describing the current harness Stop-hook support level.

    Support levels:
      native-stop-hook  -- Stop hook registered and can block continuation.
      status-only       -- State inspectable; harness cannot block Stop.
      unsupported       -- No runtime claim is made.
    """
    return detect_enforcement_level(project_dir=ROOT)


# ---------------------------------------------------------------------------
# Store resolution
# ---------------------------------------------------------------------------


def _make_store(args: argparse.Namespace) -> GoalStateStore:
    workspace_thread_id = getattr(args, "workspace_thread_id", None) or os.environ.get(
        "COS_WORKSPACE_THREAD_ID", "default"
    )
    base_dir = getattr(args, "base_dir", None)
    if base_dir is None:
        base_dir = ROOT / ".cognitive-os" / "goals"
    return GoalStateStore(base_dir=Path(base_dir), workspace_thread_id=workspace_thread_id)


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------


def cmd_create(args: argparse.Namespace) -> int:
    """Create a new active goal. Rejects a second active goal unless --replace."""
    store = _make_store(args)

    existing = store.load()
    if existing is not None and existing.status in ("active", "paused"):
        if not args.replace:
            print(
                f"ERROR: An active/paused goal already exists (id={existing.goal_id}, "
                f"status={existing.status}). "
                "Use --replace to replace it or 'clear' it first.",
                file=sys.stderr,
            )
            return 2
        # Replace: archive the existing goal as cleared first
        cleared = apply_transition(existing, "cleared")
        store.archive(cleared)

    if not args.check:
        if not args.allow_vague:
            print(
                "ERROR: At least one --check is required. "
                "Pass --allow-vague only in dry-run mode.",
                file=sys.stderr,
            )
            return 2

    workspace_thread_id = getattr(args, "workspace_thread_id", None) or os.environ.get(
        "COS_WORKSPACE_THREAD_ID", "default"
    )

    goal = GoalState.create(
        objective=args.objective,
        acceptance_checks=list(args.check or []),
        constraints=list(args.constraint or []),
        max_turns=args.max_turns,
        max_minutes=args.max_minutes,
        max_tokens=getattr(args, "max_tokens", None),
        max_cost_usd=getattr(args, "max_cost_usd", None),
        workspace_thread_id=workspace_thread_id,
    )

    try:
        store.save(goal)
    except GoalConflictError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    if getattr(args, "json", False):
        print(json.dumps(goal.to_dict(), indent=2))
    else:
        print(f"Goal created: {goal.goal_id}")
        print(f"  status:   {goal.status}")
        print(f"  checks:   {goal.acceptance_checks}")
        if goal.max_turns:
            print(f"  max_turns: {goal.max_turns}")
        if goal.max_minutes:
            print(f"  max_minutes: {goal.max_minutes}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show current goal state."""
    store = _make_store(args)
    goal = store.load()
    if goal is None:
        if getattr(args, "json", False):
            print(json.dumps({"active_goal": None}))
        else:
            print("No active goal.")
        return 0

    if getattr(args, "json", False):
        print(json.dumps(goal.to_dict(), indent=2))
    else:
        print(f"Goal: {goal.goal_id}")
        print(f"  status:     {goal.status}")
        print(f"  objective:  {goal.objective}")
        print(f"  checks:     {goal.acceptance_checks}")
        print(f"  turns_used: {goal.turns_used}")
        if goal.evaluator_history:
            last_v = goal.evaluator_history[-1]
            print(f"  last verdict: {last_v.verdict} — {last_v.reason}")
            if last_v.missing_checks:
                print(f"  missing checks: {last_v.missing_checks}")
        harness = _detect_harness_support()
        print(f"  enforcement:  {harness['support_level']}")
    return 0


def cmd_pause(args: argparse.Namespace) -> int:
    """Pause an active goal."""
    store = _make_store(args)
    goal = store.load()
    if goal is None:
        print("ERROR: No active goal to pause.", file=sys.stderr)
        return 1
    try:
        paused = apply_transition(goal, "paused")
    except InvalidTransitionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    try:
        store.save(paused)
    except GoalConflictError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    print(f"Goal {paused.goal_id} paused.")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a paused goal."""
    store = _make_store(args)
    goal = store.load()
    if goal is None:
        print("ERROR: No goal to resume.", file=sys.stderr)
        return 1
    try:
        active = apply_transition(goal, "active")
    except InvalidTransitionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    try:
        store.save(active)
    except GoalConflictError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    print(f"Goal {active.goal_id} resumed (active).")
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    """Clear (archive as cleared) the active or paused goal."""
    store = _make_store(args)
    goal = store.load()
    if goal is None:
        print("ERROR: No active or paused goal to clear.", file=sys.stderr)
        return 1
    try:
        cleared = apply_transition(goal, "cleared")
    except InvalidTransitionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    try:
        archive_path = store.archive(cleared)
    except GoalConflictError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    print(f"Goal {cleared.goal_id} cleared. Archived to {archive_path}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    """Explicitly archive the current goal (must already be terminal)."""
    store = _make_store(args)
    goal = store.load()
    if goal is None:
        print("ERROR: No current goal to archive.", file=sys.stderr)
        return 1
    if not goal.is_terminal():
        print(
            f"ERROR: Goal {goal.goal_id} is not terminal (status={goal.status}). "
            "Use 'clear' to clear an active or paused goal.",
            file=sys.stderr,
        )
        return 1
    try:
        archive_path = store.archive(goal)
    except GoalConflictError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    print(f"Goal {goal.goal_id} archived to {archive_path}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Parse and append an explicit evidence packet for the current goal.

    The Stop hook remains the authoritative enforcer. This command stores the
    packet and returns a deterministic preview verdict so operators can see
    whether the next Stop event is expected to allow, block, or budget-limit.
    """
    store = _make_store(args)
    goal = store.load()
    if goal is None:
        print("ERROR: No active goal to evaluate.", file=sys.stderr)
        return 1
    if goal.status != "active":
        print(
            f"ERROR: Goal {goal.goal_id} is not active (status={goal.status}).",
            file=sys.stderr,
        )
        return 1

    try:
        raw = Path(args.evidence_file).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: Cannot read evidence file: {exc}", file=sys.stderr)
        return 1

    parsed = parse_evidence(raw, acceptance_checks=goal.acceptance_checks)
    if not parsed.valid or parsed.packet is None:
        for err in parsed.errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 2

    goal.evidence_history.append(parsed.packet)
    evaluator = GoalEvaluator(project_dir=ROOT)
    verdict = evaluator.evaluate(goal, parsed.packet)

    # Persist the explicit packet only. The Stop hook owns lifecycle
    # transitions and turn accounting so a preflight CLI evaluation cannot
    # double-count turns or bypass hook enforcement.
    try:
        store.save(goal)
        store.append_event(
            "evidence",
            {
                "goal_id": goal.goal_id,
                "iteration": parsed.packet.iteration,
                "preview_verdict": verdict.verdict,
            },
        )
    except GoalConflictError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    payload = {
        "goal_id": goal.goal_id,
        "evidence_stored": True,
        "preview_verdict": verdict.to_dict(),
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print(f"Evidence stored for goal {goal.goal_id}.")
        print(f"Preview verdict: {verdict.verdict} — {verdict.reason}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    """Report harness Stop-hook support level (REQ-012, REQ-018)."""
    harness = _detect_harness_support()
    if getattr(args, "json", False):
        print(json.dumps(harness, indent=2))
        return 0

    support = harness["support_level"]
    print(f"Harness support level: {support}")
    if support == "native-stop-hook":
        print("  Stop-hook enforcement: ACTIVE")
        # Report per-harness registration status (S1-3: Codex visibility)
        if harness.get("claude_code"):
            sf = harness.get("settings_file", "unknown")
            print(f"  Claude Code: registered ({sf})")
        else:
            print("  Claude Code: not registered")
        if harness.get("codex"):
            cf = harness.get("codex_hooks_file", "unknown")
            print(f"  Codex:       registered ({cf})")
        else:
            print("  Codex:       not registered")
    elif support == "status-only":
        print("  Stop-hook enforcement: UNAVAILABLE")
        print(f"  Hook exists at: {harness.get('hook_path', 'unknown')}")
        print("  Action: register goal-stop-gate.sh in settings.json hooks.Stop")
        print("          and/or .codex/hooks.json Stop registrations")
    else:
        print("  Stop-hook enforcement: UNSUPPORTED")
        print("  Auto-continuation is not available in this harness.")
        print("  Goal state remains inspectable via 'cos-goal status'.")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cos-goal",
        description="COS-native goal management. Goals are evidence contracts, not motivational prompts.",
    )
    parser.add_argument(
        "--workspace-thread-id",
        default=None,
        help="Workspace/thread identifier for goal isolation (default: 'default').",
    )
    parser.add_argument(
        "--base-dir",
        default=None,
        help="Override base directory for goal state (default: .cognitive-os/goals).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = sub.add_parser("create", help="Create a new active goal.")
    p_create.add_argument("--objective", required=True, help="Goal objective text (untrusted, escaped internally).")
    p_create.add_argument(
        "--check",
        action="append",
        metavar="CHECK",
        help="Acceptance check (repeatable). At least one required unless --allow-vague.",
    )
    p_create.add_argument(
        "--constraint",
        action="append",
        metavar="CONSTRAINT",
        help="Constraint text (repeatable).",
    )
    p_create.add_argument("--max-turns", type=int, default=None, help="Maximum iteration turns.")
    p_create.add_argument("--max-minutes", type=int, default=None, help="Wall-clock budget in minutes.")
    p_create.add_argument("--max-tokens", type=int, default=None, help="Token budget (cumulative dispatch tokens).")
    p_create.add_argument("--max-cost-usd", type=float, default=None, help="Cost budget in USD.")
    p_create.add_argument(
        "--replace",
        action="store_true",
        help="Replace the current active/paused goal (archive it first).",
    )
    p_create.add_argument(
        "--allow-vague",
        action="store_true",
        help="Allow creation without --check (dry-run mode only).",
    )
    p_create.add_argument("--json", action="store_true", help="Output created goal as JSON.")

    # status
    p_status = sub.add_parser("status", help="Show current goal state.")
    p_status.add_argument("--json", action="store_true", help="Output as JSON.")

    # pause
    sub.add_parser("pause", help="Pause the active goal.")

    # resume
    sub.add_parser("resume", help="Resume the paused goal.")

    # clear
    sub.add_parser("clear", help="Clear (archive) the active or paused goal.")

    # archive
    sub.add_parser("archive", help="Archive the current terminal goal.")

    # evaluate
    p_evaluate = sub.add_parser(
        "evaluate",
        help="Parse and append an explicit evidence packet for the active goal.",
    )
    p_evaluate.add_argument(
        "--evidence-file",
        required=True,
        help="Path to a JSON or fenced-markdown JSON GOAL_EVIDENCE packet.",
    )
    p_evaluate.add_argument("--json", action="store_true", help="Output as JSON.")

    # doctor
    p_doctor = sub.add_parser("doctor", help="Report harness Stop-hook support level.")
    p_doctor.add_argument("--json", action="store_true", help="Output as JSON.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "create": cmd_create,
        "status": cmd_status,
        "pause": cmd_pause,
        "resume": cmd_resume,
        "clear": cmd_clear,
        "archive": cmd_archive,
        "evaluate": cmd_evaluate,
        "doctor": cmd_doctor,
    }
    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
