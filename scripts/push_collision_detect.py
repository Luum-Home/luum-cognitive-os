#!/usr/bin/env python3
# SCOPE: both
"""Push-time subject collision detector — ADR-116 P4.2.

Compares subjects of local unpushed commits against recent origin/main commits.
Detects exact or near-duplicate (≥80% Levenshtein similarity) subjects with
diverged SHAs, then checks patch-id overlap to distinguish already-applied
duplicates from independent re-implementations.

Exit codes (when used as CLI):
  0 — no collision
  1 — internal error
  2 — collision detected and mode=block
Stderr — human-readable warning/block message in all collision cases.

Mode controlled by ``COS_PUSH_COLLISION_MODE`` (warn | block).  Default: warn.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Levenshtein distance (pure Python, no external deps)
# ---------------------------------------------------------------------------


def levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between *a* and *b*."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    # Use two-row DP to keep memory O(min(la, lb))
    if la < lb:
        a, b, la, lb = b, a, lb, la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[lb]


def similarity(a: str, b: str) -> float:
    """Return similarity ratio in [0.0, 1.0] between subjects *a* and *b*."""
    if not a and not b:
        return 1.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    dist = levenshtein(a, b)
    return 1.0 - dist / max_len


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _run_git(root: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def unpushed_commits(root: Path, upstream: str = "origin/main") -> list[tuple[str, str]]:
    """Return list of (sha, subject) for local commits not yet on *upstream*."""
    proc = _run_git(root, ["log", f"{upstream}..HEAD", "--pretty=%H %s"])
    if proc.returncode != 0:
        return []
    results: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, _, subject = line.partition(" ")
        results.append((sha, subject))
    return results


def recent_origin_commits(
    root: Path,
    since: str = "6 hours ago",
    branch: str = "origin/main",
) -> list[tuple[str, str]]:
    """Return list of (sha, subject) from *branch* since *since*."""
    proc = _run_git(
        root,
        ["log", branch, f"--since={since}", "--pretty=%H %s"],
    )
    if proc.returncode != 0:
        return []
    results: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, _, subject = line.partition(" ")
        results.append((sha, subject))
    return results


def patch_id(root: Path, sha: str) -> str | None:
    """Return the git patch-id for the single commit *sha*, or None on failure."""
    show_proc = subprocess.run(
        ["git", "show", sha],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if show_proc.returncode != 0:
        return None
    pid_proc = subprocess.run(
        ["git", "patch-id", "--stable"],
        input=show_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(root),
    )
    if pid_proc.returncode != 0 or not pid_proc.stdout.strip():
        return None
    # output format: "<patch-id> <commit-sha>"
    return pid_proc.stdout.decode("utf-8", errors="replace").split()[0]


def diff_stats(root: Path, sha_a: str, sha_b: str) -> dict[str, int]:
    """Return insertion/deletion counts for the symmetric diff between two commits."""
    proc = _run_git(root, ["diff", "--stat", f"{sha_a}...{sha_b}"])
    if proc.returncode != 0:
        return {"insertions": 0, "deletions": 0}
    text = proc.stdout
    ins = sum(int(m) for m in re.findall(r"(\d+) insertion", text))
    dls = sum(int(m) for m in re.findall(r"(\d+) deletion", text))
    return {"insertions": ins, "deletions": dls}


def patch_overlap_pct(root: Path, sha_local: str, sha_origin: str) -> float:
    """Estimate content overlap percentage between two commits.

    Returns a value in [0.0, 100.0].  100% means the diffs are identical
    (same patch-id).  Lower values mean increasing divergence.
    """
    pid_local = patch_id(root, sha_local)
    pid_origin = patch_id(root, sha_origin)
    if pid_local and pid_origin and pid_local == pid_origin:
        return 100.0

    stats = diff_stats(root, sha_local, sha_origin)
    total_changes = stats["insertions"] + stats["deletions"]
    if total_changes == 0:
        # If the symmetric diff is empty the patches produce the same tree state
        return 90.0

    # Heuristic: the smaller the symmetric diff relative to the original commit
    # size, the higher the overlap.  We cap the "commit size" at 1 to avoid /0.
    orig_proc = _run_git(root, ["diff", "--stat", f"{sha_origin}^..{sha_origin}"])
    orig_total = 0
    if orig_proc.returncode == 0:
        orig_total = sum(int(m) for m in re.findall(r"(\d+) insertion", orig_proc.stdout))
        orig_total += sum(int(m) for m in re.findall(r"(\d+) deletion", orig_proc.stdout))

    if orig_total == 0:
        return 0.0

    overlap = max(0.0, 1.0 - total_changes / (orig_total * 2)) * 100.0
    return round(overlap, 1)


# ---------------------------------------------------------------------------
# Collision dataclass
# ---------------------------------------------------------------------------


@dataclass
class Collision:
    local_sha: str
    local_subject: str
    origin_sha: str
    origin_subject: str
    subject_similarity: float  # 0.0–1.0
    patch_overlap_pct: float   # 0.0–100.0
    match_type: str            # "exact" | "fuzzy"

    def is_already_applied(self) -> bool:
        """True when the patch overlap suggests the same change was applied."""
        return self.patch_overlap_pct >= 70.0

    def severity(self) -> str:
        """Return 'warn' for already-applied, 'block' for independent re-impl."""
        return "warn" if self.is_already_applied() else "block"

    def message(self) -> str:
        sim_pct = round(self.subject_similarity * 100)
        overlap = round(self.patch_overlap_pct)
        kind = "already-applied duplicate" if self.is_already_applied() else "independent re-implementation"
        return (
            f"Subject collision detected ({self.match_type} match, "
            f"subject similarity {sim_pct}%): "
            f"your commit {self.local_sha[:12]!r} subject {self.local_subject!r} "
            f"matches origin's {self.origin_sha[:12]!r} subject {self.origin_subject!r}. "
            f"Patch overlap: {overlap}%. "
            f"Likely {kind}."
        )


# ---------------------------------------------------------------------------
# Core detection logic
# ---------------------------------------------------------------------------

SIMILARITY_THRESHOLD = 0.80  # ≥80% subject similarity triggers a check


def detect_collisions(
    root: Path,
    upstream: str = "origin/main",
    since: str = "6 hours ago",
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[Collision]:
    """Return all collisions between unpushed commits and recent origin commits."""
    local = unpushed_commits(root, upstream)
    if not local:
        return []

    origin = recent_origin_commits(root, since, upstream)
    if not origin:
        return []

    collisions: list[Collision] = []
    for local_sha, local_subj in local:
        for origin_sha, origin_subj in origin:
            if local_sha == origin_sha:
                # Same commit — no collision
                continue
            sim = similarity(local_subj, origin_subj)
            if sim < threshold:
                continue
            match_type = "exact" if local_subj == origin_subj else "fuzzy"
            overlap = patch_overlap_pct(root, local_sha, origin_sha)
            collisions.append(
                Collision(
                    local_sha=local_sha,
                    local_subject=local_subj,
                    origin_sha=origin_sha,
                    origin_subject=origin_subj,
                    subject_similarity=sim,
                    patch_overlap_pct=overlap,
                    match_type=match_type,
                )
            )
    return collisions


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def write_metrics(root: Path, collisions: list[Collision], mode: str) -> None:
    metrics_dir = root / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "script": "push_collision_detect",
        "mode": mode,
        "collisions": [asdict(c) for c in collisions],
    }
    with (metrics_dir / "push-collision-detect.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir",
        default=(
            os.environ.get("COGNITIVE_OS_PROJECT_DIR")
            or os.environ.get("CODEX_PROJECT_DIR")
            or os.environ.get("CLAUDE_PROJECT_DIR")
            or os.getcwd()
        ),
    )
    parser.add_argument(
        "--upstream",
        default="origin/main",
        help="Remote branch to compare against (default: origin/main)",
    )
    parser.add_argument(
        "--since",
        default="6 hours ago",
        help="How far back to look in origin history (default: '6 hours ago')",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=SIMILARITY_THRESHOLD,
        help=f"Minimum subject similarity to flag (default: {SIMILARITY_THRESHOLD})",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    parser.add_argument("--metrics", action="store_true", help="Append result to metrics JSONL")
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.project_dir).resolve()
    mode = os.environ.get("COS_PUSH_COLLISION_MODE", "warn").lower()

    collisions = detect_collisions(root, args.upstream, args.since, args.threshold)

    if args.metrics:
        write_metrics(root, collisions, mode)

    if not collisions:
        if args.json:
            print(json.dumps({"ok": True, "collisions": []}, indent=2))
        else:
            print("push-collision-check: PASS — no subject collisions detected")
        return 0

    if args.json:
        print(
            json.dumps(
                {"ok": False, "collisions": [asdict(c) for c in collisions]},
                indent=2,
            )
        )

    block = False
    for c in collisions:
        print(f"push-collision-check: [{c.severity().upper()}] {c.message()}", file=sys.stderr)
        if c.severity() == "block" and mode == "block":
            block = True

    if block:
        print(
            "push-collision-check: BLOCK — independent re-implementation detected. "
            "Resolve duplicate work before pushing, or set "
            "COS_PUSH_COLLISION_MODE=warn to downgrade to advisory.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
