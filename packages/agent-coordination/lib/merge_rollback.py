# SCOPE: both
# scope: both
"""
Post-merge auto-revert — P2.2 (ADR-116).

After a fast-forward merge is pushed to main, the worker runs a second gate
stack (``verify_post_merge``).  If any gate fails, ``auto_revert`` creates a
``git revert`` commit and pushes it, then emits a ``merge_reverted`` event.

Public API
----------
verify_post_merge(merged_sha, repo_root) -> bool
    Returns True if the post-merge stack passes, False otherwise.

auto_revert(merged_sha, reason, repo_root) -> dict
    Runs ``git revert --no-edit <sha>`` + ``git push`` and emits the event.
    Returns a result dict with keys: reverted, revert_sha, error.

Python 3.9+ compatible.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DRY_RUN_ENV = "COS_MERGE_QUEUE_DRY"
_MANUAL_FLAG_FILE = ".cognitive-os/sessions/merge-revert-manual-required"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _emit_event(event_type: str, payload: dict, session_id: str) -> None:
    """Emit an event to the bus — best-effort; never raises."""
    try:
        from lib.event_bus import emit  # type: ignore[import]

        emit(event_type, payload, session_id=session_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("merge_rollback: event_bus emit failed (best-effort): %s", exc)


def _run_git(
    args: list[str],
    repo_root: Path,
    *,
    check: bool = False,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo_root)] + args,
        capture_output=True,
        text=True,
        check=check,
        timeout=60,
    )


def _set_manual_flag(repo_root: Path, reason: str) -> None:
    """Write a manual-required flag file so ops can triage the failure."""
    try:
        flag = repo_root / _MANUAL_FLAG_FILE
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text(reason + "\n", encoding="utf-8")
        logger.warning("merge_rollback: manual intervention required — see %s", flag)
    except Exception as exc:  # noqa: BLE001
        logger.warning("merge_rollback: could not write manual flag: %s", exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_post_merge(
    merged_sha: str,
    repo_root: str | Path,
    session_id: Optional[str] = None,
    *,
    dry_run: Optional[bool] = None,
) -> bool:
    """Run the standard gate stack on the post-merge state of main.

    In dry-run mode (``COS_MERGE_QUEUE_DRY=1``) this always returns True and
    prints intent without executing gates.

    Parameters
    ----------
    merged_sha:
        The SHA that was just merged; used in event payloads.
    repo_root:
        Absolute path to the repository root.
    session_id:
        Session identifier for events; defaults to env var.
    dry_run:
        Override dry-run detection; None = read ``COS_MERGE_QUEUE_DRY``.

    Returns
    -------
    bool
        True if all gates pass, False otherwise.
    """
    root = Path(repo_root).resolve()
    sid = session_id or os.environ.get("COGNITIVE_OS_SESSION_ID", "merge-rollback")
    is_dry = dry_run if dry_run is not None else os.environ.get(_DRY_RUN_ENV, "0") == "1"

    if is_dry:
        logger.info(
            "merge_rollback: [DRY-RUN] would run post-merge verify on sha=%s", merged_sha
        )
        print(f"[merge_rollback] [DRY-RUN] would run post-merge verify on sha={merged_sha}")
        return True

    # Lazy import to allow tests to patch gate_runner.run_stack at the canonical path.
    import lib.gate_runner as _gate_runner  # type: ignore[import]

    # Post-merge we run against HEAD on main (branch name doesn't matter much).
    target_branch = os.environ.get("MERGE_TARGET_BRANCH", "main")
    result = _gate_runner.run_stack(
        branch=target_branch,
        repo_root=root,
        stack=_gate_runner.STANDARD_STACK,
        fail_fast=True,
        session_id=sid,
    )

    _emit_event(
        "gate_outcome" if result.passed else "gate_failed",
        {
            "phase": "post-merge",
            "merged_sha": merged_sha,
            "passed": result.passed,
            "failed_gate": result.failed_gate,
            "evidence": result.evidence,
        },
        session_id=sid,
    )

    if not result.passed:
        logger.warning(
            "merge_rollback: post-merge verify FAILED on gate '%s' for sha=%s",
            result.failed_gate,
            merged_sha,
        )
    else:
        logger.info("merge_rollback: post-merge verify PASSED for sha=%s", merged_sha)

    return result.passed


def auto_revert(
    merged_sha: str,
    reason: str,
    repo_root: str | Path,
    remote: str = "origin",
    target_branch: str = "main",
    session_id: Optional[str] = None,
    *,
    dry_run: Optional[bool] = None,
) -> dict:
    """Revert *merged_sha* and push, then emit a ``merge_reverted`` event.

    Parameters
    ----------
    merged_sha:
        The commit SHA to revert.
    reason:
        Human-readable explanation for the revert (logged and event payload).
    repo_root:
        Absolute path to the repository root.
    remote:
        Git remote to push the revert to (default: origin).
    target_branch:
        Branch on the remote to push to (default: main).
    session_id:
        Session identifier for events.
    dry_run:
        Override dry-run detection; None = read ``COS_MERGE_QUEUE_DRY``.

    Returns
    -------
    dict
        ``{"reverted": bool, "revert_sha": str | None, "error": str | None}``
    """
    root = Path(repo_root).resolve()
    sid = session_id or os.environ.get("COGNITIVE_OS_SESSION_ID", "merge-rollback")
    is_dry = dry_run if dry_run is not None else os.environ.get(_DRY_RUN_ENV, "0") == "1"

    if is_dry:
        logger.info(
            "merge_rollback: [DRY-RUN] would auto-revert sha=%s reason=%r", merged_sha, reason
        )
        print(f"[merge_rollback] [DRY-RUN] would auto-revert sha={merged_sha}: {reason}")
        return {"reverted": False, "revert_sha": None, "error": None, "dry_run": True}

    logger.warning(
        "merge_rollback: AUTO-REVERT sha=%s reason=%r", merged_sha, reason
    )

    # Step 1: git revert --no-edit <sha>
    revert_result = _run_git(
        ["revert", "--no-edit", merged_sha],
        root,
    )
    if revert_result.returncode != 0:
        error_msg = (
            f"git revert failed (exit={revert_result.returncode}): "
            f"{revert_result.stderr.strip()}"
        )
        logger.error("merge_rollback: %s", error_msg)
        _set_manual_flag(root, f"Auto-revert of {merged_sha} failed: {error_msg}")
        _emit_event(
            "merge_reverted",
            {
                "merged_sha": merged_sha,
                "revert_sha": None,
                "reason": reason,
                "success": False,
                "error": error_msg,
                "manual_intervention_required": True,
            },
            session_id=sid,
        )
        return {"reverted": False, "revert_sha": None, "error": error_msg}

    # Capture the revert commit SHA.
    head_result = _run_git(["rev-parse", "HEAD"], root)
    revert_sha = head_result.stdout.strip() if head_result.returncode == 0 else None

    # Step 2: git push <remote> <branch>
    push_result = _run_git(
        ["push", remote, target_branch],
        root,
    )
    if push_result.returncode != 0:
        error_msg = (
            f"git push after revert failed (exit={push_result.returncode}): "
            f"{push_result.stderr.strip()}"
        )
        logger.error("merge_rollback: %s", error_msg)
        _set_manual_flag(
            root,
            f"Revert commit {revert_sha} exists locally but push failed: {error_msg}",
        )
        _emit_event(
            "merge_reverted",
            {
                "merged_sha": merged_sha,
                "revert_sha": revert_sha,
                "reason": reason,
                "success": False,
                "error": error_msg,
                "manual_intervention_required": True,
            },
            session_id=sid,
        )
        return {"reverted": False, "revert_sha": revert_sha, "error": error_msg}

    # Success.
    logger.info(
        "merge_rollback: revert SUCCESS revert_sha=%s for merged_sha=%s",
        revert_sha,
        merged_sha,
    )
    _emit_event(
        "merge_reverted",
        {
            "merged_sha": merged_sha,
            "revert_sha": revert_sha,
            "reason": reason,
            "success": True,
            "error": None,
            "manual_intervention_required": False,
        },
        session_id=sid,
    )
    return {"reverted": True, "revert_sha": revert_sha, "error": None}
