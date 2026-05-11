#!/usr/bin/env python3
# SCOPE: os-only
"""cos_evolve_tick — CLI entry point for the evolve loop spike.

ADR-262 §Decision 3: operator interface for the evolve proposal queue.

Commands:
  run               Execute one review cycle (reads last N turns, calls LLM)
  list              Print pending proposals sorted by confidence
  approve <id>      Mark a proposal approved
  reject <id>       Mark a proposal rejected (--reason required)

Kill switch: if cognitive-os.yaml evolve.enabled is false (default during spike),
`run` exits 0 with a message without calling the LLM. Also honoured via env var
COS_DISABLE_EVOLVE_TICK=1.

Usage::

    python3 scripts/cos_evolve_tick.py run
    python3 scripts/cos_evolve_tick.py list
    python3 scripts/cos_evolve_tick.py approve abc123
    python3 scripts/cos_evolve_tick.py reject abc123 --reason "Too session-specific"
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path for lib imports
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml

from lib.evolve_skill_review import EvolveSkillReview
from lib.evolve_task_queue import EvolveTaskQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(name)s  %(message)s",
)
logger = logging.getLogger("cos_evolve_tick")

CONFIG_PATH = REPO_ROOT / "cognitive-os.yaml"


def _load_evolve_config() -> dict:
    try:
        with CONFIG_PATH.open() as fh:
            cfg = yaml.safe_load(fh) or {}
        return cfg.get("evolve", {})
    except Exception as exc:
        logger.warning("Could not load cognitive-os.yaml: %s", exc)
        return {}


def _is_enabled(evolve_cfg: dict) -> bool:
    """Return True if the evolve loop is enabled."""
    if os.environ.get("COS_DISABLE_EVOLVE_TICK", "").strip() == "1":
        return False
    return bool(evolve_cfg.get("enabled", False))


# ---------------------------------------------------------------------------
# Subcommand: run
# ---------------------------------------------------------------------------

def cmd_run(args: argparse.Namespace) -> int:
    evolve_cfg = _load_evolve_config()

    if not _is_enabled(evolve_cfg):
        print(
            "Evolve loop is disabled (evolve.enabled=false in cognitive-os.yaml). "
            "Set evolve.enabled: true to activate. Exiting without calling LLM."
        )
        return 0

    session_dir = Path(args.session_dir) if getattr(args, "session_dir", None) else None
    review = EvolveSkillReview(config=evolve_cfg)
    count = review.run(session_dir=session_dir)
    print(f"Evolve review complete: {count} proposal(s) enqueued.")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: list
# ---------------------------------------------------------------------------

def cmd_list(args: argparse.Namespace) -> int:
    queue = EvolveTaskQueue()
    pending = queue.list_pending(limit=getattr(args, "limit", 50))

    if not pending:
        print("No pending proposals.")
        return 0

    print(f"Pending proposals ({len(pending)}):\n")
    for p in pending:
        print(f"  [{p.proposal_id[:8]}]  {p.confidence:.2f}  [{p.kind}]  {p.title}")
        print(f"         Rationale: {p.rationale[:100]}")
        print(f"         Created:   {p.created_at}")
        print()

    return 0


# ---------------------------------------------------------------------------
# Subcommand: approve
# ---------------------------------------------------------------------------

def cmd_approve(args: argparse.Namespace) -> int:
    queue = EvolveTaskQueue()
    reviewer = getattr(args, "reviewer", "operator")
    ok = queue.approve(args.id, reviewer=reviewer)
    if ok:
        print(f"Proposal {args.id[:8]} approved.")
        return 0
    else:
        print(f"Could not approve {args.id[:8]} — not found or not in 'pending' status.", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Subcommand: reject
# ---------------------------------------------------------------------------

def cmd_reject(args: argparse.Namespace) -> int:
    if not args.reason:
        print("--reason is required for reject.", file=sys.stderr)
        return 2

    queue = EvolveTaskQueue()
    reviewer = getattr(args, "reviewer", "operator")
    ok = queue.reject(args.id, reason=args.reason, reviewer=reviewer)
    if ok:
        print(f"Proposal {args.id[:8]} rejected. Reason stored for calibration.")
        return 0
    else:
        print(f"Could not reject {args.id[:8]} — not found or not in 'pending' status.", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cos-evolve-tick",
        description="Evolve loop spike CLI — manage skill proposal queue.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Execute one LLM review cycle")
    p_run.add_argument(
        "--session-dir",
        dest="session_dir",
        default=None,
        help="Path to session directory (defaults to most recent active session)",
    )
    p_run.set_defaults(func=cmd_run)

    # list
    p_list = sub.add_parser("list", help="List pending proposals sorted by confidence")
    p_list.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max number of proposals to show (default: 50)",
    )
    p_list.set_defaults(func=cmd_list)

    # approve
    p_approve = sub.add_parser("approve", help="Mark a proposal as approved")
    p_approve.add_argument("id", help="Proposal ID (or prefix)")
    p_approve.add_argument(
        "--reviewer",
        default="operator",
        help="Reviewer identifier (default: operator)",
    )
    p_approve.set_defaults(func=cmd_approve)

    # reject
    p_reject = sub.add_parser("reject", help="Mark a proposal as rejected")
    p_reject.add_argument("id", help="Proposal ID (or prefix)")
    p_reject.add_argument(
        "--reason",
        required=True,
        help="Reason for rejection (stored for prompt calibration)",
    )
    p_reject.add_argument(
        "--reviewer",
        default="operator",
        help="Reviewer identifier (default: operator)",
    )
    p_reject.set_defaults(func=cmd_reject)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
