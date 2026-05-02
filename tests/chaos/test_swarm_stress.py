"""Swarm stress tests — N concurrent agents competing over a 5-resource pool.

Tests parametrized over N ∈ {10, 20, 50}.  Each worker is a real OS process
(ProcessPoolExecutor) so flock semantics apply correctly.

Metrics collected per run
-------------------------
- total_wall_s         total elapsed wall time in seconds
- mean_acq_latency_ms  mean lease-acquisition latency across all attempts
- max_queue_depth      max observed simultaneous "waiting" workers
- conflict_count       number of lease-denied (blocked) outcomes
- deadlock_count       number of acquire attempts that timed out (> DEADLOCK_THRESHOLD_S)
- throughput_ops_s     completed lease cycles per second
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.chaos

ROOT = Path(__file__).resolve().parents[2]
RESOURCE_LEASE = ROOT / "scripts" / "resource_lease.py"
COS_TASK_CLAIMS = ROOT / "scripts" / "cos_task_claims.py"

# 5 distinct domains — contention guaranteed when N > 5
DOMAINS = ["auth", "billing", "migrations", "frontend", "infra"]

# Any acquire that takes longer than this is counted as a "deadlock"
DEADLOCK_THRESHOLD_S = 30.0

# Hard timeouts per N (seconds)
TIMEOUT_BY_N: dict[int, float] = {10: 60.0, 20: 120.0, 50: 300.0}

# How long a worker holds the lease before releasing (simulates real work)
WORK_SLEEP_S = 0.05

# Retry budget for a blocked acquire: workers retry with exponential back-off.
# No fixed count — retry until DEADLOCK_THRESHOLD_S is reached.
INITIAL_BACKOFF_S = 0.05
MAX_BACKOFF_S = 1.0


# ---------------------------------------------------------------------------
# Per-worker result
# ---------------------------------------------------------------------------


@dataclass
class WorkerResult:
    agent_id: str
    domain: str
    task_id: str
    acquired: bool
    conflict_count: int   # how many times this worker was blocked before success
    acq_latency_ms: float  # time from first acquire attempt to success (ms); -1 on failure
    deadlock: bool        # True if never acquired within DEADLOCK_THRESHOLD_S


# ---------------------------------------------------------------------------
# Worker function (runs in a child process)
# ---------------------------------------------------------------------------


def _worker(
    agent_id: str,
    session_id: str,
    task_id: str,
    domain: str,
    project_dir: str,
    work_sleep_s: float,
) -> dict[str, Any]:
    """Run one complete lease-acquire → claim → sleep → release cycle."""

    def run_lease(subcmd: list[str]) -> tuple[int, dict[str, Any]]:
        cmd = [
            sys.executable,
            str(RESOURCE_LEASE),
            "--project-dir",
            project_dir,
            *subcmd,
        ]
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=DEADLOCK_THRESHOLD_S + 5,
        )
        try:
            data = json.loads(proc.stdout)
        except Exception:
            data = {"status": "error", "stderr": proc.stderr}
        return proc.returncode, data

    def run_claim(subcmd: list[str]) -> tuple[int, dict[str, Any]]:
        env = os.environ.copy()
        env["COGNITIVE_OS_PROJECT_DIR"] = project_dir
        cmd = [
            sys.executable,
            str(COS_TASK_CLAIMS),
            "--project-dir",
            project_dir,
            *subcmd,
        ]
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=30,
        )
        try:
            data = json.loads(proc.stdout)
        except Exception:
            data = {"status": "error", "stderr": proc.stderr}
        return proc.returncode, data

    acq_start = time.monotonic()
    conflict_count = 0
    deadlock = False
    acquired = False
    attempt = 0

    while True:
        elapsed = time.monotonic() - acq_start
        if elapsed >= DEADLOCK_THRESHOLD_S:
            deadlock = True
            break

        rc, data = run_lease([
            "acquire",
            domain,
            "--agent-id", agent_id,
            "--session-id", session_id,
            "--reason", f"stress-test-{task_id}",
            "--ttl-seconds", "10",
        ])

        if rc == 0:
            acquired = True
            break

        # rc == 2 → blocked; anything else → unexpected error (treat as blocked)
        conflict_count += 1
        sleep_time = min(INITIAL_BACKOFF_S * (1.3 ** attempt), MAX_BACKOFF_S)
        time.sleep(sleep_time)
        attempt += 1

    acq_latency_ms = (time.monotonic() - acq_start) * 1000.0 if acquired else -1.0

    if acquired:
        # Record a task claim (advisory)
        run_claim([
            "claim",
            "--task-id", task_id,
            "--session-id", session_id,
            "--description", f"stress worker {agent_id} on {domain}",
        ])

        # Simulate actual work
        time.sleep(work_sleep_s)

        # Release the lease
        run_lease([
            "release",
            domain,
            "--agent-id", agent_id,
        ])

        # Complete the task claim
        run_claim([
            "complete",
            "--task-id", task_id,
            "--session-id", session_id,
        ])

    result = WorkerResult(
        agent_id=agent_id,
        domain=domain,
        task_id=task_id,
        acquired=acquired,
        conflict_count=conflict_count,
        acq_latency_ms=acq_latency_ms,
        deadlock=deadlock,
    )
    return asdict(result)


# ---------------------------------------------------------------------------
# Fixture: isolated project directory per test run
# ---------------------------------------------------------------------------


@pytest.fixture
def stress_project(tmp_path: Path) -> Path:
    project = tmp_path / "stress-project"
    project.mkdir()
    (project / ".cognitive-os" / "runtime" / "resource-leases").mkdir(parents=True)
    (project / ".cognitive-os" / "tasks").mkdir(parents=True)
    (project / ".cognitive-os" / "sessions").mkdir(parents=True)
    # Minimal cognitive-os.yaml so resource_lease reads default TTL
    (project / "cognitive-os.yaml").write_text(
        "concurrency_safety:\n  resource_leases:\n    default_ttl_seconds: 10\n",
        encoding="utf-8",
    )
    return project


# ---------------------------------------------------------------------------
# Core swarm runner
# ---------------------------------------------------------------------------


def _run_swarm(n_agents: int, project: Path, timeout_s: float) -> dict[str, Any]:
    """Launch N workers, collect results, compute aggregate metrics."""
    project_dir = str(project)
    futures_meta: list[tuple[Any, str, str, str]] = []  # (future, agent_id, domain, task_id)

    wall_start = time.monotonic()

    # Track in-flight queue depth with a simple counter protected by a list
    # (no shared memory needed — we measure post-hoc from timestamps)

    with ProcessPoolExecutor(max_workers=min(n_agents, 32)) as pool:
        for i in range(n_agents):
            agent_id = f"stress-agent-{i:03d}"
            session_id = f"stress-session-{i:03d}"
            domain = DOMAINS[i % len(DOMAINS)]
            task_id = f"STRESS-{i:03d}-{domain.upper()}"
            future = pool.submit(
                _worker,
                agent_id,
                session_id,
                task_id,
                domain,
                project_dir,
                WORK_SLEEP_S,
            )
            futures_meta.append((future, agent_id, domain, task_id))

        results: list[dict[str, Any]] = []
        for future, agent_id, domain, task_id in futures_meta:
            try:
                result = future.result(timeout=timeout_s)
            except Exception as exc:
                # Worker crashed or timed out — treat as a deadlock
                result = asdict(WorkerResult(
                    agent_id=agent_id,
                    domain=domain,
                    task_id=task_id,
                    acquired=False,
                    conflict_count=0,
                    acq_latency_ms=-1.0,
                    deadlock=True,
                ))
                result["exception"] = str(exc)
            results.append(result)

    wall_elapsed = time.monotonic() - wall_start

    # Aggregate metrics
    successful = [r for r in results if r["acquired"]]
    latencies = [r["acq_latency_ms"] for r in successful]
    total_conflicts = sum(r["conflict_count"] for r in results)
    deadlock_count = sum(1 for r in results if r["deadlock"])
    throughput = len(successful) / wall_elapsed if wall_elapsed > 0 else 0.0
    mean_latency = (sum(latencies) / len(latencies)) if latencies else 0.0

    # Max contention queue depth: approximate from conflict counts
    # The domain with most contention = max conflicts across workers for that domain
    domain_conflicts: dict[str, int] = {d: 0 for d in DOMAINS}
    for r in results:
        domain_conflicts[r["domain"]] += r["conflict_count"]
    max_queue_depth = max(domain_conflicts.values()) if domain_conflicts else 0

    return {
        "n_agents": n_agents,
        "total_wall_s": round(wall_elapsed, 3),
        "mean_acq_latency_ms": round(mean_latency, 2),
        "max_queue_depth": max_queue_depth,
        "conflict_count": total_conflicts,
        "deadlock_count": deadlock_count,
        "throughput_ops_s": round(throughput, 2),
        "successful_workers": len(successful),
        "failed_workers": len(results) - len(successful),
        "per_domain_conflicts": domain_conflicts,
        "workers": results,
    }


# ---------------------------------------------------------------------------
# Parametrized stress tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_agents", [10, 20, 50])
def test_swarm_stress(n_agents: int, stress_project: Path) -> None:
    """Stress test: N concurrent agents compete over 5 resource leases."""
    timeout_s = TIMEOUT_BY_N[n_agents]

    metrics = _run_swarm(n_agents, stress_project, timeout_s=timeout_s)

    # ---- Save metrics alongside the project for debugging ----
    (stress_project / f"metrics-n{n_agents}.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # ---- Assertions ----

    assert metrics["deadlock_count"] == 0, (
        f"N={n_agents}: {metrics['deadlock_count']} deadlock(s) detected. "
        f"wall={metrics['total_wall_s']}s, conflicts={metrics['conflict_count']}, "
        f"failed={metrics['failed_workers']}"
    )

    assert metrics["total_wall_s"] < timeout_s, (
        f"N={n_agents}: wall time {metrics['total_wall_s']}s exceeded hard timeout {timeout_s}s. "
        f"Metrics: {json.dumps({k: v for k, v in metrics.items() if k != 'workers'})}"
    )

    assert metrics["successful_workers"] == n_agents, (
        f"N={n_agents}: only {metrics['successful_workers']}/{n_agents} workers acquired leases. "
        f"conflicts={metrics['conflict_count']}, deadlocks={metrics['deadlock_count']}"
    )

    # No data corruption: verify all lease files are gone (properly released)
    lease_dir = stress_project / ".cognitive-os" / "runtime" / "resource-leases"
    remaining_leases = list(lease_dir.glob("*.json"))
    assert len(remaining_leases) == 0, (
        f"N={n_agents}: {len(remaining_leases)} lease file(s) not released: "
        f"{[p.name for p in remaining_leases]}"
    )
