#!/usr/bin/env python3
# SCOPE: os-only
"""Protected-publication policy checker for headless Cognitive OS workers.

This is a Phase 1 proof path for ADR-091. It does not push, create pull
requests, or mutate git state. It answers whether a worker may publish an
outcome to the requested target.

Exit codes:
  0 — publication is allowed or allowed with warning
  2 — publication is blocked by policy
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from typing import Literal

ActorMode = Literal["interactive", "headless"]
LandingMode = Literal["none", "merge_queue", "human_approved"]
Decision = Literal["allow", "warn", "block"]

PROTECTED_TARGETS = {"main", "master", "refs/heads/main", "refs/heads/master"}
PROTECTED_LANDING_MODES = {"merge_queue", "human_approved"}
PATCH_TARGETS = {"patch", "diff", "artifact", "branch", "feature_branch"}


@dataclass(frozen=True)
class PublicationDecision:
    decision: Decision
    allowed: bool
    branch: str
    actor_mode: ActorMode
    publication_target: str
    landing_mode: LandingMode
    reason: str
    required_landing_modes: list[str]
    recommendation: str


def _normalized_target(target: str) -> str:
    value = target.strip()
    if value.startswith("refs/heads/"):
        return value.removeprefix("refs/heads/")
    return value


def _is_protected_target(target: str) -> bool:
    return target.strip() in PROTECTED_TARGETS or _normalized_target(target) in {"main", "master"}


def _is_patch_or_branch_output(target: str) -> bool:
    normalized = _normalized_target(target)
    return normalized in PATCH_TARGETS or not _is_protected_target(target)


def check_publication_policy(
    *,
    branch: str,
    actor_mode: ActorMode,
    publication_target: str,
    landing_mode: LandingMode = "none",
) -> PublicationDecision:
    """Return the local protected-publication decision for a proposed outcome."""
    branch = branch.strip()
    publication_target = publication_target.strip()

    if landing_mode in PROTECTED_LANDING_MODES and _is_protected_target(publication_target):
        return PublicationDecision(
            decision="allow",
            allowed=True,
            branch=branch,
            actor_mode=actor_mode,
            publication_target=publication_target,
            landing_mode=landing_mode,
            reason=f"protected landing mode '{landing_mode}' is explicit for {publication_target}",
            required_landing_modes=sorted(PROTECTED_LANDING_MODES),
            recommendation="Proceed through the declared protected landing path and preserve approval evidence.",
        )

    if actor_mode == "headless" and _is_protected_target(publication_target):
        return PublicationDecision(
            decision="block",
            allowed=False,
            branch=branch,
            actor_mode=actor_mode,
            publication_target=publication_target,
            landing_mode=landing_mode,
            reason="unattended headless workers may not publish directly to main/master",
            required_landing_modes=sorted(PROTECTED_LANDING_MODES),
            recommendation="Publish a patch/feature branch artifact, or rerun with --landing-mode merge_queue or human_approved.",
        )

    if actor_mode == "interactive" and _is_protected_target(publication_target):
        return PublicationDecision(
            decision="warn",
            allowed=True,
            branch=branch,
            actor_mode=actor_mode,
            publication_target=publication_target,
            landing_mode=landing_mode,
            reason="interactive operator direct-main publication follows existing local semantics: warn, then rely on protected remote landing",
            required_landing_modes=sorted(PROTECTED_LANDING_MODES),
            recommendation="Prefer merge_queue or human_approved landing for coordinated work; remote branch protection remains authoritative.",
        )

    if _is_patch_or_branch_output(publication_target):
        return PublicationDecision(
            decision="allow",
            allowed=True,
            branch=branch,
            actor_mode=actor_mode,
            publication_target=publication_target,
            landing_mode=landing_mode,
            reason="publication target is a patch or non-protected branch output",
            required_landing_modes=sorted(PROTECTED_LANDING_MODES),
            recommendation="Proceed, then land through a protected path before advancing main/master.",
        )

    return PublicationDecision(
        decision="block",
        allowed=False,
        branch=branch,
        actor_mode=actor_mode,
        publication_target=publication_target,
        landing_mode=landing_mode,
        reason="publication target could not be classified safely",
        required_landing_modes=sorted(PROTECTED_LANDING_MODES),
        recommendation="Use publication target patch/branch, or specify merge_queue/human_approved for main/master.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", required=True, help="Current/source branch for the worker outcome.")
    parser.add_argument(
        "--actor-mode",
        required=True,
        choices=("interactive", "headless"),
        help="Whether the actor has an interactive operator attached.",
    )
    parser.add_argument(
        "--publication-target",
        required=True,
        help="Requested public target, e.g. main, master, patch, branch, or a feature branch ref.",
    )
    parser.add_argument(
        "--landing-mode",
        default="none",
        choices=("none", "merge_queue", "human_approved"),
        help="Explicit protected landing mode for main/master publication.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def _print_human(decision: PublicationDecision) -> None:
    stream = sys.stderr if decision.decision == "block" else sys.stdout
    print(f"decision: {decision.decision}", file=stream)
    print(f"allowed: {str(decision.allowed).lower()}", file=stream)
    print(f"reason: {decision.reason}", file=stream)
    print(f"recommendation: {decision.recommendation}", file=stream)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    decision = check_publication_policy(
        branch=args.branch,
        actor_mode=args.actor_mode,
        publication_target=args.publication_target,
        landing_mode=args.landing_mode,
    )
    if args.json:
        print(json.dumps(asdict(decision), sort_keys=True))
    else:
        _print_human(decision)
    return 2 if decision.decision == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
