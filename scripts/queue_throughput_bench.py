#!/usr/bin/env python3
# SCOPE: both
# scope: both
"""
Merge-queue throughput benchmark — P2.2 (ADR-116).

Creates a temporary git repo, spawns N enqueue processes concurrently, runs a
worker loop that drains the queue, and measures latency / throughput.

Metrics reported
----------------
sessions               — number of synthetic sessions
commits_per_session    — commits per session
total_enqueued         — total queue entries submitted
total_completed        — entries that reached "completed" status
total_failed           — entries that reached "failed" status (conflict or other)
p50_enqueue_ms         — 50th-percentile enqueue call latency (ms)
p95_enqueue_ms         — 95th-percentile enqueue call latency (ms)
p50_e2e_ms             — 50th-percentile end-to-end latency (ms)
p95_e2e_ms             — 95th-percentile end-to-end latency (ms)
throughput_per_sec     — completed entries per second (wall clock)
queue_depth_samples    — list of {t_sec, depth} snapshots during the run
bench_duration_sec     — total wall-clock time for the benchmark

Usage
-----
  python3 scripts/queue_throughput_bench.py \\
      --sessions 5 --commits-per-session 3 --report /tmp/bench.json

  # Conflict scenario (2 sessions write to same file):
  python3 scripts/queue_throughput_bench.py \\
      --sessions 2 --commits-per-session 1 --conflict-scenario --report /tmp/bench.json

  # Disable auto-rebase:
  COS_QUEUE_AUTO_REBASE=0 python3 scripts/queue_throughput_bench.py ...
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Use "fork" on POSIX to avoid pickle constraints on locally-defined functions.
# This is safe for test/bench environments (no pre-fork thread issues).
_MP_CTX: Any = multiprocessing.get_context("fork" if sys.platform != "win32" else "spawn")


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def _setup_repo(repo_dir: Path) -> None:
    """Initialise a bare-ish git repo with a first commit on main."""
    _git(["init", "-b", "main"], repo_dir)
    _git(["config", "user.email", "bench@cos.test"], repo_dir)
    _git(["config", "user.name", "COS Bench"], repo_dir)
    # Initial commit so main exists.
    readme = repo_dir / "README.md"
    readme.write_text("bench repo\n")
    _git(["add", "README.md"], repo_dir)
    _git(["commit", "-m", "chore: init bench repo"], repo_dir)


def _create_session_branch(
    repo_dir: Path,
    session_id: str,
    commits: int,
    conflict_file: Optional[str] = None,
) -> str:
    """Create a session branch with *commits* commits.

    If *conflict_file* is provided, every commit touches that same file
    (triggers a conflict when two sessions both modify it).
    """
    branch = f"session/{session_id}"
    _git(["checkout", "-b", branch], repo_dir)

    for i in range(commits):
        if conflict_file:
            target = repo_dir / conflict_file
        else:
            target = repo_dir / f"file_{session_id}_{i}.txt"
        target.write_text(f"session={session_id} commit={i}\n")
        _git(["add", str(target)], repo_dir)
        _git(["commit", "-m", f"feat({session_id}): commit {i}"], repo_dir)

    # Return to main so other sessions can branch from it cleanly.
    _git(["checkout", "main"], repo_dir)
    return branch


# ---------------------------------------------------------------------------
# Worker: drain the queue in a tight loop
# ---------------------------------------------------------------------------


def _worker_drain(
    queue_path: str,
    repo_dir: str,
    stop_event,
    results: list,
    depth_samples: list,
) -> None:
    """Drain the queue until *stop_event* is set and the queue is empty."""
    sys.path.insert(0, str(REPO_ROOT))
    from lib.merge_queue import peek, dequeue, list_pending  # noqa: PLC0415
    from lib.queue_rebase import is_ff_possible, rebase_onto  # noqa: PLC0415

    auto_rebase = os.environ.get("COS_QUEUE_AUTO_REBASE", "1") == "1"
    target_branch = "main"
    repo = Path(repo_dir)

    while not stop_event.is_set() or list_pending(queue_path=queue_path):
        entry = peek(queue_path=queue_path)
        if entry is None:
            time.sleep(0.005)
            # Sample queue depth.
            depth_samples.append({"t_sec": time.monotonic(), "depth": 0})
            continue

        # Sample depth.
        pending = list_pending(queue_path=queue_path)
        depth_samples.append({"t_sec": time.monotonic(), "depth": len(pending)})

        entry_id = entry["id"]
        branch = entry["session_branch"]
        enqueued_at = entry["enqueued_at"]

        start = time.monotonic()

        # Check if ff is possible; optionally rebase.
        ff_ok = is_ff_possible(branch, target_branch, repo)

        if not ff_ok:
            if auto_rebase:
                result = rebase_onto(branch, target_branch, repo)
                if not result.success:
                    notes = "failed-conflict: " + ", ".join(result.conflicts)
                    dequeue(entry_id, status="failed", notes=notes, queue_path=queue_path)
                    results.append({
                        "entry_id": entry_id,
                        "branch": branch,
                        "status": "failed-conflict",
                        "enqueued_at": enqueued_at,
                        "completed_at": time.monotonic(),
                        "duration_ms": (time.monotonic() - start) * 1000,
                    })
                    continue
                ff_ok = True
            else:
                dequeue(entry_id, status="failed", notes="behind-main:auto-rebase-disabled",
                        queue_path=queue_path)
                results.append({
                    "entry_id": entry_id,
                    "branch": branch,
                    "status": "failed-behind",
                    "enqueued_at": enqueued_at,
                    "completed_at": time.monotonic(),
                    "duration_ms": (time.monotonic() - start) * 1000,
                })
                continue

        # ff-merge.
        try:
            _git(["checkout", target_branch], repo)
            _git(["merge", "--ff-only", branch], repo)
            _git(["branch", "-d", branch], repo, check=False)
            status = "completed"
            notes = f"merged {branch} into {target_branch}"
        except subprocess.CalledProcessError as exc:
            status = "failed"
            notes = f"merge error: {exc.stderr.strip()[:200]}"

        dequeue(entry_id, status=status, notes=notes, queue_path=queue_path)
        duration_ms = (time.monotonic() - start) * 1000
        results.append({
            "entry_id": entry_id,
            "branch": branch,
            "status": status,
            "enqueued_at": enqueued_at,
            "completed_at": time.monotonic(),
            "duration_ms": duration_ms,
        })


# ---------------------------------------------------------------------------
# Enqueue worker (runs in a subprocess)
# ---------------------------------------------------------------------------


def _enqueue_session(
    queue_path: str,
    session_id: str,
    branch: str,
    result_q,
    enqueue_latencies: list,
) -> None:
    """Enqueue a single session branch and record latency."""
    sys.path.insert(0, str(REPO_ROOT))
    from lib.merge_queue import enqueue  # noqa: PLC0415

    t0 = time.monotonic()
    eid = enqueue(branch, session_id, queue_path=queue_path)
    latency_ms = (time.monotonic() - t0) * 1000
    result_q.put({"entry_id": eid, "latency_ms": latency_ms, "enqueued_mono": time.monotonic()})


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = max(0, int(len(sorted_data) * p / 100) - 1)
    return sorted_data[min(idx, len(sorted_data) - 1)]


# ---------------------------------------------------------------------------
# Main benchmark function
# ---------------------------------------------------------------------------


def run_benchmark(
    sessions: int = 5,
    commits_per_session: int = 3,
    conflict_scenario: bool = False,
    report_path: Optional[str] = None,
    repo_dir: Optional[Path] = None,
) -> dict:
    """Run the full benchmark and return the metrics dict.

    Parameters
    ----------
    sessions:
        Number of synthetic sessions (concurrent enqueues).
    commits_per_session:
        Commits per session branch.
    conflict_scenario:
        If True, all sessions modify the same file (triggers rebase conflicts).
    report_path:
        If provided, write JSON report to this path.
    repo_dir:
        Use an existing repo dir (useful in tests). If None, a tempdir is created.
    """
    own_tmpdir = None
    if repo_dir is None:
        own_tmpdir = tempfile.mkdtemp(prefix="cos-bench-")
        repo_dir = Path(own_tmpdir)

    # Set the queue path inside the temp repo.
    queue_path = str(repo_dir / "merge-queue.jsonl")
    os.environ["MERGE_QUEUE_PATH"] = queue_path

    try:
        _setup_repo(repo_dir)

        # Create session branches.
        branches: list[tuple[str, str]] = []  # (session_id, branch)
        for i in range(sessions):
            sid = f"bench-session-{i}"
            conflict_file = "shared_file.txt" if conflict_scenario else None
            branch = _create_session_branch(
                repo_dir, sid, commits_per_session, conflict_file=conflict_file
            )
            branches.append((sid, branch))

        # Shared structures for worker results.
        # Use _MP_CTX (fork) so locally-defined functions are pickleable.
        manager = _MP_CTX.Manager()
        worker_results = manager.list()
        depth_samples_raw = manager.list()
        stop_event = manager.Event()

        # Start the drain worker in a background process.
        drain_proc = _MP_CTX.Process(
            target=_worker_drain,
            args=(queue_path, str(repo_dir), stop_event, worker_results, depth_samples_raw),
            daemon=True,
        )
        drain_proc.start()

        # Concurrently enqueue all sessions.
        enqueue_result_q = _MP_CTX.Queue()
        enqueue_procs = []
        bench_start = time.monotonic()

        for sid, branch in branches:
            p = _MP_CTX.Process(
                target=_enqueue_session,
                args=(queue_path, sid, branch, enqueue_result_q, []),
            )
            enqueue_procs.append(p)

        for p in enqueue_procs:
            p.start()
        for p in enqueue_procs:
            p.join(timeout=30)

        # Collect enqueue latencies.
        enqueue_latencies: list[float] = []
        enqueue_timestamps: dict[str, float] = {}
        while not enqueue_result_q.empty():
            item = enqueue_result_q.get_nowait()
            enqueue_latencies.append(item["latency_ms"])
            enqueue_timestamps[item["entry_id"]] = item["enqueued_mono"]

        # Signal the drain worker to stop once it has drained pending entries.
        stop_event.set()
        drain_proc.join(timeout=60)

        bench_end = time.monotonic()
        bench_duration = bench_end - bench_start

        # Aggregate results.
        results_list = list(worker_results)
        completed = [r for r in results_list if r["status"] == "completed"]
        failed = [r for r in results_list if r["status"] != "completed"]

        # End-to-end latency: from enqueue_mono to completed_at.
        e2e_latencies: list[float] = []
        for r in results_list:
            eid = r["entry_id"]
            if eid in enqueue_timestamps:
                e2e_ms = (r["completed_at"] - enqueue_timestamps[eid]) * 1000
                e2e_latencies.append(e2e_ms)

        throughput = len(completed) / bench_duration if bench_duration > 0 else 0.0

        # Normalise depth samples: make t_sec relative to bench_start.
        depth_samples = [
            {"t_sec": round(s["t_sec"] - bench_start, 3), "depth": s["depth"]}
            for s in depth_samples_raw
        ]

        report = {
            "sessions": sessions,
            "commits_per_session": commits_per_session,
            "conflict_scenario": conflict_scenario,
            "total_enqueued": len(enqueue_latencies),
            "total_completed": len(completed),
            "total_failed": len(failed),
            "p50_enqueue_ms": round(_percentile(enqueue_latencies, 50), 2),
            "p95_enqueue_ms": round(_percentile(enqueue_latencies, 95), 2),
            "p50_e2e_ms": round(_percentile(e2e_latencies, 50), 2),
            "p95_e2e_ms": round(_percentile(e2e_latencies, 95), 2),
            "throughput_per_sec": round(throughput, 3),
            "queue_depth_samples": depth_samples[:50],  # cap at 50 to keep report small
            "bench_duration_sec": round(bench_duration, 3),
        }

        if report_path:
            Path(report_path).write_text(json.dumps(report, indent=2))
            print(f"[bench] report written to {report_path}", flush=True)

        return report

    finally:
        if own_tmpdir:
            import shutil
            shutil.rmtree(own_tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge-queue throughput benchmark (P2.2 ADR-116)"
    )
    parser.add_argument("--sessions", type=int, default=5,
                        help="Number of concurrent synthetic sessions (default: 5)")
    parser.add_argument("--commits-per-session", type=int, default=3,
                        help="Commits per session branch (default: 3)")
    parser.add_argument("--conflict-scenario", action="store_true",
                        help="All sessions modify the same file (triggers rebase conflicts)")
    parser.add_argument("--report", metavar="PATH", default=None,
                        help="Write JSON report to this path")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    report = run_benchmark(
        sessions=args.sessions,
        commits_per_session=args.commits_per_session,
        conflict_scenario=args.conflict_scenario,
        report_path=args.report,
    )
    print(json.dumps(report, indent=2))
