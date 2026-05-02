#!/usr/bin/env python3
# SCOPE: both
"""Pre-commit content-hash deduplication — P4.1 (ADR-116).

Computes the ``git patch-id --stable`` fingerprint of the currently staged
diff and compares it against patch-ids of recent commits on ``origin/main``.

If a match is found the tool either blocks the commit (``block`` mode) or
emits a warning (``warn`` mode, the default), and appends a
``conflict_detected`` event to the event bus (``lib.event_bus``).

Exit codes
----------
0  — no collision (safe to commit)
2  — collision detected AND mode is ``block``

Environment
-----------
COS_DEDUPE_MODE : ``warn`` | ``block`` | ``off``  (default: ``warn``)
COS_DEDUPE_DEPTH : integer number of origin/main commits to scan (default: 200)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DEPTH = 200
_DEFAULT_MODE = "warn"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], *, cwd: Optional[str | Path] = None, stdin: Optional[bytes] = None) -> tuple[int, str, str]:
    """Run a subprocess and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.returncode, result.stdout.decode("utf-8", errors="replace"), result.stderr.decode("utf-8", errors="replace")


def get_staged_patch_id(repo_root: Optional[str | Path] = None) -> Optional[str]:
    """Return the patch-id of the currently staged diff, or None if empty."""
    rc, diff_out, _ = _run(["git", "diff", "--cached"], cwd=repo_root)
    if rc != 0 or not diff_out.strip():
        return None

    rc2, pid_out, _ = _run(
        ["git", "patch-id", "--stable"],
        cwd=repo_root,
        stdin=diff_out.encode("utf-8"),
    )
    if rc2 != 0 or not pid_out.strip():
        return None

    # patch-id outputs: "<patch-id> <commit-id>\n"
    parts = pid_out.strip().split()
    if not parts:
        return None
    return parts[0]


def get_origin_patch_ids(depth: int = _DEFAULT_DEPTH, repo_root: Optional[str | Path] = None) -> dict[str, str]:
    """Return {patch_id: commit_sha} for the last ``depth`` commits on origin/main."""
    rc, log_out, _ = _run(
        ["git", "log", f"origin/main", "--pretty=%H", f"-{depth}"],
        cwd=repo_root,
    )
    if rc != 0 or not log_out.strip():
        return {}

    commit_shas = [line.strip() for line in log_out.strip().splitlines() if line.strip()]

    patch_ids: dict[str, str] = {}
    for sha in commit_shas:
        # Get the diff for this commit and compute its patch-id
        rc_d, diff_out, _ = _run(
            ["git", "diff-tree", "--stdin", "-p", sha],
            cwd=repo_root,
        )
        if rc_d != 0 or not diff_out.strip():
            # For the very first commit diff-tree needs a special form; fall back
            rc_d, diff_out, _ = _run(
                ["git", "show", "--format=", sha],
                cwd=repo_root,
            )
        if not diff_out.strip():
            continue

        rc_p, pid_out, _ = _run(
            ["git", "patch-id", "--stable"],
            cwd=repo_root,
            stdin=diff_out.encode("utf-8"),
        )
        if rc_p != 0 or not pid_out.strip():
            continue

        parts = pid_out.strip().split()
        if len(parts) >= 2:
            pid, commit = parts[0], parts[1]
            patch_ids[pid] = commit

    return patch_ids


def emit_collision_event(
    staged_patch_id: str,
    matched_commit: str,
    mode: str,
    bus_path: Optional[str | Path] = None,
) -> None:
    """Append a ``conflict_detected`` event to the event bus."""
    try:
        # Add project root to sys.path for lib import
        _repo_root = Path(__file__).resolve().parent.parent
        if str(_repo_root) not in sys.path:
            sys.path.insert(0, str(_repo_root))
        from lib.event_bus import emit  # noqa: PLC0415

        payload = {
            "staged_patch_id": staged_patch_id,
            "matched_commit": matched_commit,
            "dedupe_mode": mode,
            "source": "pre-commit-content-hash-dedupe",
        }
        kwargs: dict = {}
        if bus_path is not None:
            kwargs["bus_path"] = bus_path
        emit("conflict_detected", payload, **kwargs)
    except Exception as exc:  # noqa: BLE001
        # Never let event bus failure block commit logic
        print(f"[dedupe] WARNING: could not emit event: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def check(
    mode: str = _DEFAULT_MODE,
    depth: int = _DEFAULT_DEPTH,
    repo_root: Optional[str | Path] = None,
    bus_path: Optional[str | Path] = None,
) -> int:
    """Run the deduplication check.

    Returns 0 (safe), 2 (blocked), or 0 with a printed warning.
    """
    if mode == "off":
        return 0

    staged_pid = get_staged_patch_id(repo_root)
    if staged_pid is None:
        # Empty or no staged changes — nothing to deduplicate
        return 0

    origin_pids = get_origin_patch_ids(depth=depth, repo_root=repo_root)
    if staged_pid not in origin_pids:
        return 0

    matched_commit = origin_pids[staged_pid]

    # Emit event to bus before deciding block vs warn
    emit_collision_event(staged_pid, matched_commit, mode, bus_path=bus_path)

    msg = (
        f"[dedupe] Staged diff matches commit {matched_commit[:12]} already on origin/main "
        f"(patch-id={staged_pid[:12]}…)"
    )

    if mode == "block":
        print(f"COMMIT BLOCKED: {msg}", file=sys.stderr)
        print(
            "[dedupe] This commit appears to be a duplicate of an existing commit on origin/main.",
            file=sys.stderr,
        )
        print("[dedupe] Set COS_DEDUPE_MODE=warn to allow, or COS_DEDUPE_MODE=off to disable.", file=sys.stderr)
        return 2

    # warn mode
    print(f"WARNING: {msg}", file=sys.stderr)
    print("[dedupe] This may be a parallel-session duplicate. Proceeding (warn mode).", file=sys.stderr)
    return 0


def main() -> int:
    mode = os.environ.get("COS_DEDUPE_MODE", _DEFAULT_MODE).lower().strip()
    try:
        depth = int(os.environ.get("COS_DEDUPE_DEPTH", str(_DEFAULT_DEPTH)))
    except ValueError:
        depth = _DEFAULT_DEPTH

    if mode not in ("warn", "block", "off"):
        print(f"[dedupe] Unknown COS_DEDUPE_MODE={mode!r}, falling back to 'warn'", file=sys.stderr)
        mode = "warn"

    return check(mode=mode, depth=depth)


if __name__ == "__main__":
    sys.exit(main())
